from fastapi.testclient import TestClient
from api.app import app
from api.models.database import get_db
from api.models.database.models import Base, Patient, Emergency
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest
engine=create_engine('sqlite:///./test_emergency.db',connect_args={'check_same_thread':False}); Session=sessionmaker(bind=engine)
def override():
    db=Session()
    try: yield db
    finally: db.close()
app.dependency_overrides[get_db]=override
client=TestClient(app)
@pytest.fixture(autouse=True)
def clear_override():
    app.dependency_overrides[get_db]=override
    yield
    app.dependency_overrides.clear()
def setup():
    Base.metadata.create_all(engine); db=Session(); db.query(Emergency).delete(); db.query(Patient).delete(); db.add(Patient(id='P001',first_name='A',last_name='B',age=1,gender='x')); db.commit(); db.close()
def test_emergency_recorded():
    setup(); r=client.post('/api/v1/patients/P001/emergency'); assert r.status_code==200; assert r.json()['status']=='recorded'; db=Session(); assert db.query(Emergency).filter_by(patient_id='P001',status='recorded').count()==1; db.close()
def test_emergency_missing_patient():
    setup(); assert client.post('/api/v1/patients/MISSING/emergency').status_code==404
