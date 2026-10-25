import os
from datetime import datetime, timedelta

os.environ["SECRET_KEY"] = "test-auth-secret"
os.environ["DATABASE_URL"] = "sqlite:///./_auth_test.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from api.app import app
from api.models.database.models import Base, EmailVerificationToken, User, Patient
from api.models.database.database import get_db
from api.services import auth_service
from api.routes import auth as auth_routes

engine = create_engine("sqlite:///./_auth_test.db", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def clean_db(monkeypatch):
    from api.config import get_settings
    monkeypatch.setattr(get_settings(), "SECRET_KEY", "test-auth-secret")
    app.dependency_overrides[get_db] = override_db
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    monkeypatch.setattr(auth_service, "send_verification_email", capture_email)
    monkeypatch.setattr(auth_routes, "send_verification_email", capture_email)
    captured.clear()
    email_calls.clear()
    yield


captured = {}
email_calls = []
async def capture_email(email, raw_token):
    email_calls.append(email)
    captured["email"] = email; captured["token"] = raw_token
    return {"mode": "dev_log", "sent": True}


def override_db():
    Base.metadata.create_all(engine)
    db = TestingSession()
    try: yield db
    finally: db.close()

app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def register():
    return client.post("/api/v1/auth/register", json={"email": "Test@Example.com", "password": "Strong123", "full_name": "Test User", "age": 30})


def test_register_verify_login_me_and_token_safety():
    response = register(); assert response.status_code == 201
    body = response.json(); assert "password_hash" not in str(body) and "token" not in body
    db = TestingSession(); user = db.query(User).one(); row = db.query(EmailVerificationToken).one(); assert user.password_hash != "Strong123"; assert row.token_hash != captured["token"]
    assert client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "Strong123"}).status_code == 403
    assert client.post("/api/v1/auth/verify-email", json={"token": "bad"}).status_code == 400
    assert client.post("/api/v1/auth/verify-email", json={"token": captured["token"]}).status_code == 200
    assert client.post("/api/v1/auth/verify-email", json={"token": captured["token"]}).status_code == 400
    login = client.post("/api/v1/auth/login", json={"email": "TEST@example.com", "password": "Strong123"}); assert login.status_code == 200
    token = login.json()["access_token"]; assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_validation_duplicate_and_identical_credentials_error():
    assert register().status_code == 201; assert register().status_code == 409
    assert client.post("/api/v1/auth/register", json={"email": "bad", "password": "Strong123", "full_name": "Test User", "age": 30}).status_code == 422
    assert client.post("/api/v1/auth/register", json={"email": "x@y.com", "password": "weak", "full_name": "Test User", "age": 30}).status_code == 422
    a=client.post("/api/v1/auth/login",json={"email":"none@example.com","password":"bad"}); b=client.post("/api/v1/auth/login",json={"email":"test@example.com","password":"bad"}); assert a.status_code==b.status_code==401 and a.json()==b.json()


def test_resend_expiry_and_auth_failures():
    assert register().status_code == 201; old=captured["token"]
    assert client.post("/api/v1/auth/resend-verification",json={"email":"TEST@example.com"}).status_code==200; assert captured["token"] != old
    db=TestingSession(); row=db.query(EmailVerificationToken).filter_by(used_at=None).one(); row.expires_at=datetime.utcnow()-timedelta(minutes=1); db.commit(); db.close()
    assert client.post("/api/v1/auth/verify-email",json={"token":captured["token"]}).status_code==400
    assert client.post("/api/v1/auth/resend-verification",json={"email":"unknown@example.com"}).status_code==200
    assert client.get("/api/v1/auth/me").status_code==401


def test_registration_boundaries_and_existing_patient_rollback():
    assert client.post("/api/v1/auth/register", json={"email":"mixed@x.com","password":"Strong123","full_name":"Single","age":25}).status_code == 201
    assert client.post("/api/v1/auth/register", json={"email":"MIXED@X.COM","password":"Strong123","full_name":"Other User","age":25}).status_code == 409
    for password in ["short", "NoDigitPass", "12345678"]:
        assert client.post("/api/v1/auth/register", json={"email":f"{password}@x.com","password":password,"full_name":"Valid User","age":25}).status_code == 422
    db=TestingSession(); db.add(Patient(id="P_EXIST",first_name="Existing",last_name="Patient",age=40,gender="Unspecified",email="existing@x.com")); db.commit(); db.close()
    assert client.post("/api/v1/auth/register", json={"email":"existing@x.com","password":"Strong123","full_name":"Existing User","age":25}).status_code == 409
    db=TestingSession(); assert db.query(User).filter_by(email="existing@x.com").count() == 0; db.close()


def test_resend_sender_rules_and_delivery_failure_recovery(monkeypatch):
    assert register().status_code == 201; old=captured["token"]
    email_calls.clear(); assert client.post("/api/v1/auth/resend-verification",json={"email":"unknown@example.com"}).status_code == 200; assert email_calls == []
    assert client.post("/api/v1/auth/verify-email",json={"token":old}).status_code == 200
    assert client.post("/api/v1/auth/resend-verification",json={"email":"test@example.com"}).status_code == 200; assert email_calls == []
    async def failing(email, token): raise RuntimeError("smtp failure")
    monkeypatch.setattr(auth_routes, "send_verification_email", failing)
    response=client.post("/api/v1/auth/register",json={"email":"delivery@example.com","password":"Strong123","full_name":"Delivery User","age":25}); assert response.status_code == 502
    db=TestingSession(); user=db.query(User).filter_by(email="delivery@example.com").one(); assert not user.is_email_verified; db.close()
    monkeypatch.setattr(auth_routes, "send_verification_email", capture_email)
    assert client.post("/api/v1/auth/resend-verification",json={"email":"delivery@example.com"}).status_code == 200


def test_jwt_claims_me_failures_and_deactivated_user():
    register(); client.post("/api/v1/auth/verify-email",json={"token":captured["token"]}); login=client.post("/api/v1/auth/login",json={"email":"test@example.com","password":"Strong123"}); data=login.json(); payload=jwt.decode(data["access_token"],"test-auth-secret",algorithms=["HS256"])
    assert payload["sub"] and payload["patient_id"] and payload["type"] == "access" and payload["exp"] > payload["iat"]
    assert data["expires_in"] == 720*60
    assert "password_hash" not in client.get("/api/v1/auth/me",headers={"Authorization":"Bearer "+data["access_token"]}).json()
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me",headers={"Authorization":"Bearer "+data["access_token"][:-1]+"x"}).status_code == 401
    expired=jwt.encode({"sub":payload["sub"],"email":payload["email"],"patient_id":payload["patient_id"],"type":"access","iat":1,"exp":2},"test-auth-secret",algorithm="HS256")
    assert client.get("/api/v1/auth/me",headers={"Authorization":"Bearer "+expired}).status_code == 401
    db=TestingSession(); db.query(User).filter_by(id=payload["sub"]).update({User.is_active:False}); db.commit(); db.close(); assert client.get("/api/v1/auth/me",headers={"Authorization":"Bearer "+data["access_token"]}).status_code == 401


def test_demo_user_is_idempotent_and_enforcement_off():
    from api.services.auth_service import ensure_demo_user
    db=TestingSession(); db.add(Patient(id="P001",first_name="Muhammad",last_name="Umair",age=24,gender="Male",email="umair@healsense.com")); db.commit(); user=ensure_demo_user(db); db.commit(); first_hash=user.password_hash; first_count=db.query(User).count(); ensure_demo_user(db); db.commit(); assert db.query(User).count()==first_count and db.query(User).one().password_hash==first_hash and user.is_email_verified and user.patient_id=="P001"; db.close()
    assert client.post("/api/v1/auth/login",json={"email":"umair@healsense.com","password":"password123"}).status_code == 200
    assert client.get("/api/v1/patients/P001/profile").status_code == 200


def test_missing_secret_is_sanitized_and_restored(monkeypatch):
    from api.config import get_settings
    settings=get_settings(); original=settings.SECRET_KEY; monkeypatch.setattr(settings,"SECRET_KEY",None)
    assert client.post("/api/v1/auth/register",json={"email":"nosecret@example.com","password":"Strong123","full_name":"No Secret","age":25}).status_code == 503
    assert client.post("/api/v1/auth/login",json={"email":"none@example.com","password":"Strong123"}).status_code == 503
    monkeypatch.setattr(settings,"SECRET_KEY",original)
