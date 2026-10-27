import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app import app
from api.models.database import Base, get_db
from api.models.database.models import Alert, AlertSeverity, BpSource, Device, HealthStatus, Patient, VitalSigns
from api.routes import ai
from api.routes.auth import get_current_user
from api.services import fusion_engine, gemini_service, patient_assistant
from api.services.patient_assistant import ASSISTANT_SYSTEM_PROMPT, build_patient_context, build_user_prompt

LATEST = datetime(2026, 10, 20, 12)
NOW = LATEST + timedelta(days=3)
PRIVATE = ('SecretFirst', 'SecretLast', 'secret@example.com', 'PRIVATE_PHONE',
           'CONTACT_NAME_SENTINEL', 'CONTACT_PHONE_SENTINEL', 'CONTACT_RELATION_SENTINEL')


@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id='assistant-test-user', email='assistant@example.com', patient_id='PA1',
        is_active=True, is_email_verified=True)
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        session.close()
        engine.dispose()


def seed(db, with_vitals=True):
    patient = Patient(id='PA1', first_name=PRIVATE[0], last_name=PRIVATE[1],
                      email=PRIVATE[2], phone=PRIVATE[3], age=45, gender='female',
                      blood_type='A+', diabetes='unknown', smoking_status='unknown',
                      medications=['example medication'], past_conditions=['example condition'],
                      emergency_contacts=[{'name': PRIVATE[4], 'phone': PRIVATE[5], 'relation': PRIVATE[6], 'type': kind}
                                          for kind in ('doctor', 'family')])
    db.add(patient)
    db.add(Device(device_id='D1', patient_id='PA1', connected=True,
                  last_heartbeat=LATEST, battery_level=80))
    if with_vitals:
        # Older BP rows prove BP history is independent of the 24-hour window.
        for index in range(12):
            db.add(VitalSigns(id=f'OLD{index:02}', patient_id='PA1', device_id='D1',
                             timestamp=LATEST - timedelta(hours=25 + index),
                             heart_rate=200, spo2=80, temperature=40,
                             systolic_bp=120 + index, diastolic_bp=80,
                             bp_source=BpSource.MANUAL_ENTRY, data_origin='old_only',
                             status=HealthStatus.NORMAL))
        for index, (hours, hr, spo2, temp, systolic, diastolic) in enumerate([
            (24, 80, 98, 36, 120, 80), (12, 90, 97, 36.5, None, None),
            (6, 100, 96, 37, 140, 90), (3, 110, 95, 38, None, None),
            (0, 121, 93, 38.7, 185, 120),
        ]):
            db.add(VitalSigns(id=f'V{index}', patient_id='PA1', device_id='D1',
                             timestamp=LATEST - timedelta(hours=hours), heart_rate=hr,
                             spo2=spo2, temperature=temp, systolic_bp=systolic, diastolic_bp=diastolic,
                             bp_source=BpSource.MANUAL_ENTRY if systolic else BpSource.NONE,
                             status=HealthStatus.CRITICAL if hours == 0 else HealthStatus.NORMAL,
                             risk_score=.9 if hours == 0 else .2, prediction_confidence=.6,
                             full_probability_distribution={'normal': .1, 'warning': .3, 'critical': .6},
                             model_version='v1.0.2', data_origin='simulated' if hours == 0 else 'device'))
        for index in range(12):
            db.add(Alert(id=f'A{index:02}', patient_id='PA1', message=f'active alert {index}',
                         severity=AlertSeverity.CRITICAL, vital_type='spo2',
                         timestamp=LATEST - timedelta(minutes=index), acknowledged=False, dismissed=False))
        for name in ('acknowledged', 'dismissed'):
            db.add(Alert(id=name, patient_id='PA1', message=name, severity=AlertSeverity.HIGH,
                         timestamp=LATEST, acknowledged=name == 'acknowledged', dismissed=name == 'dismissed'))
    db.commit()
    return patient


def assert_private_absent(text):
    for value in PRIVATE:
        assert value not in text


def test_context_privacy_and_latest(db):
    patient = seed(db)
    context = build_patient_context(db, patient, NOW)
    assert context is not None
    assert context['latest']['heart_rate'] == 121
    assert context['latest']['systolic_bp'] == 185
    assert context['is_simulated_data'] is True
    assert set(context['patient']) == set(patient_assistant.PATIENT_FIELDS)
    assert_private_absent(json.dumps(context, default=str))
    assert len(context['alerts']) == 10
    assert [a['message'] for a in context['alerts']] == [f'active alert {i}' for i in range(10)]
    assert context['alerts'][0]['severity'] == 'critical'
    assert context['devices'][0]['presence_status'] == 'stale'
    assert context['devices'][0]['last_seen_seconds_ago'] == 259200
    assert context['emergency_support'] == {'configured': True, 'contact_count': 2, 'contact_types': ['doctor', 'family']}


def test_missing_patient(db):
    seed(db, False)
    response = TestClient(app).post('/api/v1/ai/patient-assistant', json={'patient_id': 'missing', 'message': 'hi'})
    assert response.status_code == 404
    assert response.json()['error'] == 'patient_not_found'


def test_no_vitals(db):
    patient = seed(db, False)
    assert build_patient_context(db, patient) is None
    response = TestClient(app).post('/api/v1/ai/patient-assistant', json={'patient_id': 'PA1', 'message': 'hi'})
    assert response.status_code == 409
    assert response.json()['detail']['error'] == 'no_vitals'


def test_not_configured(db, monkeypatch):
    seed(db)

    async def generate(*args, **kwargs):
        raise gemini_service.GeminiNotConfiguredError()

    monkeypatch.setattr(gemini_service, 'generate_text', generate)
    response = TestClient(app).post('/api/v1/ai/patient-assistant', json={'patient_id': 'PA1', 'message': 'hi'})
    assert response.status_code == 503
    assert response.json()['detail']['error'] == 'gemini_not_configured'


def test_upstream_sanitized(db, monkeypatch):
    seed(db)

    async def generate(*args, **kwargs):
        raise gemini_service.GeminiUpstreamError('SENTINEL_SECRET')

    monkeypatch.setattr(gemini_service, 'generate_text', generate)
    response = TestClient(app).post('/api/v1/ai/patient-assistant', json={'patient_id': 'PA1', 'message': 'hi'})
    assert response.status_code == 502
    assert response.json()['detail']['error'] == 'gemini_upstream_error'
    assert 'SENTINEL_SECRET' not in response.text


def test_fusion_gemini_fallbacks(db, monkeypatch):
    patient = seed(db)
    result = {'final_risk_level': 'warning', 'confidence_score': .5, 'deterministic_flags': [],
              'ml_risk_probability': .2, 'fusion_method': 'weighted_fusion'}

    async def ok(*args, **kwargs):
        return 'explanation'

    monkeypatch.setattr(fusion_engine, 'generate_text', ok)
    assert asyncio.run(fusion_engine.fusion_engine.generate_explanation(patient, result)) == 'explanation'

    async def missing(*args, **kwargs):
        raise gemini_service.GeminiNotConfiguredError()

    monkeypatch.setattr(fusion_engine, 'generate_text', missing)
    assert 'not configured' in asyncio.run(fusion_engine.fusion_engine.generate_explanation(patient, result))

    async def upstream(*args, **kwargs):
        raise gemini_service.GeminiUpstreamError()

    monkeypatch.setattr(fusion_engine, 'generate_text', upstream)
    assert 'API error' in asyncio.run(fusion_engine.fusion_engine.generate_explanation(patient, result))


def test_context_and_response_use_enum_values(db, monkeypatch):
    patient = seed(db)
    context = build_patient_context(db, patient, NOW)
    assert context is not None
    for reading in (context['latest'], context['recent_readings'][-1]):
        assert type(reading['status']) is str and reading['status'] == 'critical'
        assert type(reading['bp_source']) is str and reading['bp_source'] == 'manual_entry'

    async def generate(system, prompt, **kwargs):
        assert 'HealthStatus.CRITICAL' not in prompt
        assert 'BpSource.MANUAL_ENTRY' not in prompt
        assert '"status": "critical"' in prompt
        assert '"bp_source": "manual_entry"' in prompt
        return 'Mocked response'

    monkeypatch.setattr(gemini_service, 'generate_text', generate)
    response = TestClient(app).post('/api/v1/ai/patient-assistant', json={'patient_id': 'PA1', 'message': 'status'})
    assert response.status_code == 200
    assert response.json()['latest_status'] == 'critical'


def test_trends_are_anchored_to_latest_not_now(db):
    context = build_patient_context(db, seed(db), NOW.replace(tzinfo=timezone.utc))
    assert context is not None
    assert context['data_as_of'] == LATEST
    assert context['data_freshness_seconds'] == 259200
    assert context['is_stale'] is True
    assert context['trends']['6h']['row_count'] == 3
    assert context['trends']['24h']['row_count'] == 5
    for window, expected in {
        '6h': {'heart_rate': (110.33, 21, 100, 121), 'spo2': (94.67, -3, 96, 93), 'temperature': (37.9, 1.7, 37, 38.7)},
        '24h': {'heart_rate': (100.2, 41, 80, 121), 'spo2': (95.8, -5, 98, 93), 'temperature': (37.24, 2.7, 36, 38.7)},
    }.items():
        for field, (average, delta, first, last) in expected.items():
            stats = context['trends'][window][field]
            assert (stats['average'], stats['delta_last_minus_first'], stats['first'], stats['last']) == (average, delta, first, last)
            assert stats['count'] == context['trends'][window]['row_count']
            assert stats['min'] == min(first, last)
            assert stats['max'] == max(first, last)
    assert context['origin_counts'] == {'device': 4, 'simulated': 1}
    assert context['rows_considered'] == 5
    assert context['rows_truncated'] is False
    assert context['data_quality'] == {
        'readings_6h': 3, 'readings_24h': 5, 'readings_with_bp_24h': 3,
        'readings_without_bp_24h': 2, 'has_sufficient_trend_data': True,
    }


def test_bp_history_and_null_stats(db):
    context = build_patient_context(db, seed(db), NOW)
    assert context is not None
    bp = context['trends']['24h']['systolic_bp']
    assert bp == {'count': 3, 'min': 120, 'max': 185, 'average': 148.33,
                  'first': 120, 'last': 185, 'delta_last_minus_first': 65}
    assert context['trends']['24h']['respiratory_rate'] == {
        'count': 0, 'min': None, 'max': None, 'average': None, 'first': None,
        'last': None, 'delta_last_minus_first': None,
    }
    history = context['bp_history']
    assert len(history) == 10
    assert [r['timestamp'] for r in history] == sorted((r['timestamp'] for r in history), reverse=True)
    assert history[-1]['timestamp'] < LATEST - timedelta(hours=24)
    assert all(r['systolic_bp'] is not None and r['diastolic_bp'] is not None for r in history)
    assert history[0]['bp_source'] == 'manual_entry'
    assert 'rows' not in context
    assert len(context['recent_readings']) <= 12
    timestamps = [r['timestamp'] for r in context['recent_readings']]
    assert timestamps == sorted(timestamps)


def test_mocked_api_success_and_captured_prompts(db, monkeypatch):
    seed(db)
    captured = {}
    original_builder = build_patient_context
    monkeypatch.setattr(ai, 'build_patient_context', lambda db, patient: original_builder(db, patient, NOW))
    monkeypatch.setattr(ai, 'get_settings', lambda: SimpleNamespace(GEMINI_MODEL='test-flash-lite'))

    async def generate(system, user, **kwargs):
        captured.update(system=system, user=user)
        return 'Grounded mocked answer'

    monkeypatch.setattr(gemini_service, 'generate_text', generate)
    turns = [{'role': 'user' if i % 2 == 0 else 'assistant', 'content': f'TURN_{i:02}_MARKER'} for i in range(12)]
    response = TestClient(app).post('/api/v1/ai/patient-assistant', json={
        'patient_id': 'PA1', 'message': 'What changed?', 'conversation': turns,
    })
    assert response.status_code == 200
    data = response.json()
    assert data['answer'] == 'Grounded mocked answer'
    assert data['patient_id'] == 'PA1'
    assert datetime.fromisoformat(data['data_as_of']) == LATEST
    assert data['data_freshness_seconds'] == 259200
    assert data['latest_status'] == 'critical'
    assert data['is_simulated_data'] is True
    assert data['model'] == 'test-flash-lite'
    assert 'not a diagnosis' in data['disclaimer']
    assert captured['system'] == ASSISTANT_SYSTEM_PROMPT
    prompt = captured['user']
    assert_private_absent(prompt + captured['system'])
    for value in ('121', '185', '120', '"trends"', '"average": 110.33', 'active alert 0',
                  'simulated', 'What changed?', '"is_stale": true', 'example medication',
                  'example condition', '"contact_count": 2', '"contact_types": ["doctor", "family"]'):
        assert value in prompt
    for i in range(12):
        assert (f'TURN_{i:02}_MARKER' in prompt) == (i >= 6)
    assert '"rows":' not in prompt


@pytest.mark.parametrize('conversation', [
    [{'role': 'system', 'content': 'bad'}], [{'role': 'user', 'content': ''}],
    [{'role': 'assistant', 'content': 'x' * 4001}], [{'role': 'user'}],
    [{'role': 'user', 'content': 'ok'}] * 13,
])
def test_invalid_conversation_rejected(db, monkeypatch, conversation):
    async def forbidden(*args, **kwargs):
        pytest.fail('Invalid input must not call Gemini')

    monkeypatch.setattr(gemini_service, 'generate_text', forbidden)
    response = TestClient(app).post('/api/v1/ai/patient-assistant', json={
        'patient_id': 'PA1', 'message': 'hi', 'conversation': conversation,
    })
    assert response.status_code == 422


@pytest.mark.parametrize('seconds,stale', [(-60, False), (300, False), (301, True)])
def test_freshness_clamp_and_boundary(db, seconds, stale):
    context = build_patient_context(db, seed(db), LATEST + timedelta(seconds=seconds))
    assert context is not None
    assert context['data_freshness_seconds'] == max(0, seconds)
    assert context['is_stale'] is stale


def test_safety_cap_keeps_newest_and_recent_twelve(db):
    patient = seed(db, False)
    db.bulk_insert_mappings(VitalSigns, [
        dict(id=f'CAP{i:05}', patient_id='PA1', device_id='D1', timestamp=LATEST - timedelta(seconds=i),
             heart_rate=80 + (i % 10), spo2=98, temperature=37, data_origin='device', status=HealthStatus.NORMAL)
        for i in range(10001)
    ])
    db.commit()
    context = build_patient_context(db, patient, NOW)
    assert context is not None
    assert context['rows_considered'] == 10000
    assert context['rows_truncated'] is True
    assert context['trends']['24h']['row_count'] == 10000
    assert context['trends']['24h']['heart_rate']['first'] == 89
    assert len(context['recent_readings']) == 12
    assert context['recent_readings'][0]['timestamp'] == LATEST - timedelta(seconds=11)
    assert context['recent_readings'][-1]['timestamp'] == LATEST
    assert context['is_simulated_data'] is False


def test_one_row_and_other_patient_isolation(db):
    patient = seed(db, False)
    db.add(VitalSigns(id='single', patient_id='PA1', device_id='D1', timestamp=LATEST,
                     heart_rate=80, spo2=98, temperature=37, data_origin='seed'))
    db.add(Patient(id='other', first_name='other', last_name='patient', age=30, gender='female'))
    db.add(VitalSigns(id='other', patient_id='other', timestamp=LATEST + timedelta(days=1),
                     heart_rate=250, spo2=70, temperature=40, data_origin='simulated'))
    db.commit()
    context = build_patient_context(db, patient, NOW)
    assert context is not None
    assert context['data_as_of'] == LATEST
    assert context['rows_considered'] == 1
    assert context['data_quality']['has_sufficient_trend_data'] is False
    assert context['trends']['24h']['heart_rate']['delta_last_minus_first'] == 0
    assert context['origin_counts'] == {'seed': 1}
    assert context['is_simulated_data'] is True


@pytest.mark.parametrize('recorded', [False, True])
def test_profile_completeness_and_support(db, recorded):
    patient = seed(db)
    patient.medications = ['Metformin'] if recorded else []
    patient.past_conditions = ['Type 2 diabetes'] if recorded else []
    patient.blood_type = 'A+' if recorded else ''
    patient.diabetes = 'false' if recorded else 'unknown'
    patient.smoking_status = 'non_smoker' if recorded else 'unknown'
    patient.emergency_contacts = patient.emergency_contacts if recorded else []
    db.commit()
    context = build_patient_context(db, patient, NOW)
    assert all(value is recorded for value in context['profile_completeness'].values())
    assert context['emergency_support']['configured'] is recorded
    assert context['emergency_support']['contact_count'] == (2 if recorded else 0)
    assert 'not recorded' in ASSISTANT_SYSTEM_PROMPT
    assert 'pharmacist' in ASSISTANT_SYSTEM_PROMPT
    assert 'changing a\nmedication or dose' in ASSISTANT_SYSTEM_PROMPT
    assert_private_absent(build_user_prompt(context, 'question', []))
