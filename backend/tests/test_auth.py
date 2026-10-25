import os
from datetime import datetime, timedelta

os.environ["SECRET_KEY"] = "test-auth-secret"
os.environ["DATABASE_URL"] = "sqlite:///./_auth_test.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app import app
from api.models.database.models import Base, EmailVerificationToken, User
from api.models.database.database import get_db
from api.services import auth_service
from api.routes import auth as auth_routes

engine = create_engine("sqlite:///./_auth_test.db", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def clean_db(monkeypatch):
    app.dependency_overrides[get_db] = override_db
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    monkeypatch.setattr(auth_service, "send_verification_email", capture_email)
    monkeypatch.setattr(auth_routes, "send_verification_email", capture_email)
    captured.clear()
    yield


captured = {}
async def capture_email(email, raw_token):
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
