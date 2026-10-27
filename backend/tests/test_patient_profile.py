import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from alembic.migration import MigrationContext
from alembic.operations import Operations

from api.app import app
from api.models.database import Base, get_db
from api.routes.auth import get_current_user
from api.models.database.models import Patient

CONTACT = {'name': 'CONTACT_NAME_SENTINEL', 'phone': 'CONTACT_PHONE_SENTINEL',
           'relation': 'CONTACT_RELATION_SENTINEL', 'type': 'doctor'}


@pytest.fixture
def profile_db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Patient(id='PROFILE', first_name='Private', last_name='Patient', age=45, gender='Female',
                   diabetes='true', smoking_status='former_smoker', medications=['Metformin'],
                   past_conditions=['Type 2 diabetes'], emergency_contacts=[CONTACT]))
    db.commit()
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id='profile-test-user', email='profile@example.com', patient_id='PROFILE',
        is_active=True, is_email_verified=True)
    try:
        yield db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db.close()
        engine.dispose()


def test_profile_returns_stored_values(profile_db):
    response = TestClient(app).get('/api/v1/patients/PROFILE/profile')
    assert response.status_code == 200
    data = response.json()
    assert data['diabetes'] == 'true'
    assert data['smoking_status'] == 'former_smoker'
    assert data['medications'] == ['Metformin']
    assert data['past_conditions'] == ['Type 2 diabetes']
    assert data['emergency_contacts'] == [CONTACT]


def test_partial_update_persists_normalized_clinical_values_and_contacts(profile_db):
    client = TestClient(app)
    payload = {'diabetes': 'false', 'smoking_status': 'non_smoker',
               'medications': [' Amlodipine ', '', '  '], 'past_conditions': [' Hypertension '],
               'emergency_contacts': [{**CONTACT, 'type': 'other'}]}
    response = client.put('/api/v1/patients/PROFILE', json=payload)
    assert response.status_code == 200
    profile_db.expire_all()
    stored = profile_db.query(Patient).filter_by(id='PROFILE').one()
    assert stored.first_name == 'Private' and stored.age == 45
    assert stored.medications == ['Amlodipine']
    assert stored.past_conditions == ['Hypertension']
    assert isinstance(stored.emergency_contacts[0], dict)
    data = client.get('/api/v1/patients/PROFILE/profile').json()
    assert data['diabetes'] == 'false' and data['smoking_status'] == 'non_smoker'
    assert data['medications'] == ['Amlodipine'] and data['past_conditions'] == ['Hypertension']
    assert data['emergency_contacts'] == [{**CONTACT, 'type': 'other'}]
    assert client.put('/api/v1/patients/PROFILE', json={'emergency_contacts': []}).status_code == 200
    assert client.get('/api/v1/patients/PROFILE/profile').json()['emergency_contacts'] == []


@pytest.mark.parametrize('payload', [
    {'diabetes': 'yes'}, {'smoking_status': 'sometimes'}, {'age': -1}, {'age': 151}, {'age': None},
    {'emergency_contacts': [{**CONTACT, 'type': 'friend'}]},
    {'emergency_contacts': [{**CONTACT, 'phone': ''}]},
    {'emergency_contacts': [{**CONTACT, 'name': '  '}]},
    {'emergency_contacts': [{**CONTACT, 'relation': ''}]},
    {'emergency_contacts': [CONTACT] * 6}, {'emergency_contacts': None},
    {'medications': ['x'] * 21}, {'past_conditions': ['x' * 101]},
])
def test_invalid_profile_updates_are_422(profile_db, payload):
    assert TestClient(app).put('/api/v1/patients/PROFILE', json=payload).status_code == 422


@pytest.mark.parametrize('method,path,payload', [
    ('get', '/api/v1/patients/missing/profile', None),
    ('put', '/api/v1/patients/missing', {'diabetes': 'true'}),
])
def test_other_or_unknown_profile_is_forbidden_for_profile_user(profile_db, method, path, payload):
    response = TestClient(app).request(method, path, **({'json': payload} if payload else {}))
    assert response.status_code == 403


def test_contact_migration_backfills_existing_rows():
    path = Path(__file__).parents[1] / 'alembic/versions/e34a20261026_patient_emergency_contacts.py'
    spec = importlib.util.spec_from_file_location('contact_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == 'c8f92a104b91'
    engine = create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE patients (id TEXT PRIMARY KEY)'))
        connection.execute(text("INSERT INTO patients (id) VALUES ('existing')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(text('SELECT emergency_contacts FROM patients')).scalar_one() == '[]'
            migration.downgrade()
            assert connection.execute(text('SELECT id FROM patients')).scalar_one() == 'existing'
    engine.dispose()
