import asyncio, json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from api.app import app
from api.models.database import Base, get_db
from api.models.database.models import Patient, Device, VitalSigns, Alert, HealthStatus, AlertSeverity, BpSource
from api.services.patient_assistant import build_patient_context
from api.services import gemini_service
from api.services import fusion_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

engine=create_engine('sqlite:///./test_patient_assistant.db',connect_args={'check_same_thread':False}); Session=sessionmaker(bind=engine)
def override_db():
 db=Session()
 try: yield db
 finally: db.close()
app.dependency_overrides[get_db]=override_db
client=TestClient(app)
@pytest.fixture(autouse=True)
def restore_overrides():
    app.dependency_overrides[get_db]=override_db
    yield
    app.dependency_overrides.clear()
def seed(with_vitals=True):
 Base.metadata.drop_all(engine); Base.metadata.create_all(engine); db=Session(); p=Patient(id='PA1',first_name='SecretFirst',last_name='SecretLast',email='secret@example.com',phone='555',age=45,gender='female',medications=['x'],past_conditions=['y']); db.add(p); db.add(Device(device_id='D1',patient_id='PA1',connected=True,last_heartbeat=datetime.utcnow()));
 if with_vitals:
  for i in range(3): db.add(VitalSigns(id=f'V{i}',patient_id='PA1',device_id='D1',heart_rate=80+i*20,spo2=98-i*2,temperature=37+i*.8,systolic_bp=(185 if i==2 else None),diastolic_bp=(120 if i==2 else None),status=HealthStatus.CRITICAL if i==2 else HealthStatus.NORMAL,risk_score=.9 if i==2 else .2,prediction_confidence=.6,full_probability_distribution={'normal':.1,'warning':.3,'critical':.6},model_version='v1.0.2',data_origin='simulated',timestamp=datetime.utcnow()-timedelta(hours=2-i)))
  db.add(Alert(id='A1',patient_id='PA1',message='active',severity=AlertSeverity.CRITICAL,acknowledged=False,dismissed=False,timestamp=datetime.utcnow()))
 db.commit(); return db,p
def test_context_privacy_and_latest():
 db,p=seed(); c=build_patient_context(db,p,datetime.utcnow()); raw=json.dumps(c,default=str); assert c['latest']['heart_rate']==120; assert c['latest']['systolic_bp']==185; assert c['is_simulated_data']; assert 'SecretFirst' not in raw and 'secret@example.com' not in raw and '555' not in raw; assert len(c['alerts'])==1; assert c['devices'][0]['presence_status'] in ('online','stale')
def test_missing_patient():
    seed(False); r=client.post('/api/v1/ai/patient-assistant',json={'patient_id':'missing','message':'hi'}); assert r.status_code==404 and r.json()['error']=='patient_not_found'
def test_no_vitals():
 seed(False); r=client.post('/api/v1/ai/patient-assistant',json={'patient_id':'PA1','message':'hi'}); assert r.status_code==409 and r.json()['detail']['error']=='no_vitals'
def test_not_configured():
 seed(); old=gemini_service.generate_text
 async def f(*a,**k): raise gemini_service.GeminiNotConfiguredError()
 gemini_service.generate_text=f; r=client.post('/api/v1/ai/patient-assistant',json={'patient_id':'PA1','message':'hi'}); gemini_service.generate_text=old; assert r.status_code==503
def test_upstream_sanitized():
 seed(); old=gemini_service.generate_text
 async def f(*a,**k): raise gemini_service.GeminiUpstreamError('SENTINEL_SECRET')
 gemini_service.generate_text=f; r=client.post('/api/v1/ai/patient-assistant',json={'patient_id':'PA1','message':'hi'}); gemini_service.generate_text=old; assert r.status_code==502 and 'SENTINEL_SECRET' not in r.text

def test_fusion_gemini_fallbacks(monkeypatch):
    db,p=seed(); result={'final_risk_level':'warning','confidence_score':.5,'deterministic_flags':[],'ml_risk_probability':.2,'fusion_method':'weighted_fusion'}
    async def ok(*a,**k): return 'explanation'
    monkeypatch.setattr(fusion_engine,'generate_text',ok); assert asyncio.run(fusion_engine.fusion_engine.generate_explanation(p,result))=='explanation'
    async def missing(*a,**k): raise gemini_service.GeminiNotConfiguredError()
    monkeypatch.setattr(fusion_engine,'generate_text',missing); assert 'not configured' in asyncio.run(fusion_engine.fusion_engine.generate_explanation(p,result))
    async def upstream(*a,**k): raise gemini_service.GeminiUpstreamError()
    monkeypatch.setattr(fusion_engine,'generate_text',upstream); assert 'API error' in asyncio.run(fusion_engine.fusion_engine.generate_explanation(p,result))


def test_context_and_response_use_enum_values(monkeypatch):
    db, patient = seed()
    try:
        latest = db.query(VitalSigns).filter_by(id='V2').one()
        latest.bp_source = BpSource.MANUAL_ENTRY
        db.commit()
        context = build_patient_context(db, patient)
        assert context is not None
        assert type(context['latest']['status']) is str
        assert context['latest']['status'] == 'critical'
        assert type(context['latest']['bp_source']) is str
        assert context['latest']['bp_source'] == 'manual_entry'
        assert context['rows'][-1]['status'] == 'critical'
        assert context['rows'][-1]['bp_source'] == 'manual_entry'

        async def generate(system, prompt, **kwargs):
            assert 'HealthStatus.CRITICAL' not in prompt
            assert 'BpSource.MANUAL_ENTRY' not in prompt
            assert '"status": "critical"' in prompt
            assert '"bp_source": "manual_entry"' in prompt
            return 'Mocked response'

        monkeypatch.setattr(gemini_service, 'generate_text', generate)
        response = client.post('/api/v1/ai/patient-assistant', json={'patient_id': 'PA1', 'message': 'status'})
        assert response.status_code == 200
        assert response.json()['latest_status'] == 'critical'
    finally:
        db.close()
