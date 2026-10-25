import asyncio
import hashlib
import logging
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from api.config import get_settings
from api.models.database.models import EmailVerificationToken, Patient, User

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def validate_password(password: str) -> None:
    if not 8 <= len(password) <= 128 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("Password must be 8-128 characters and contain a letter and a digit")


def _secret_or_503() -> str:
    secret = get_settings().SECRET_KEY
    if not secret:
        raise HTTPException(status_code=503, detail={"error": "auth_not_configured", "message": "Authentication is not configured"})
    return secret


def create_access_token(user: User) -> tuple[str, int]:
    settings = get_settings()
    expires = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = datetime.utcnow()
    payload = {"sub": user.id, "email": user.email, "patient_id": user.patient_id, "type": "access", "iat": now, "exp": now + timedelta(seconds=expires)}
    return jwt.encode(payload, _secret_or_503(), algorithm=settings.ALGORITHM), expires


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, _secret_or_503(), algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise JWTError
        return payload
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail={"error": "invalid_token", "message": "Invalid or expired access token"})


def new_verification_token(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(id=str(uuid.uuid4()), user_id=user.id, token_hash=hashlib.sha256(raw.encode()).hexdigest(), expires_at=datetime.utcnow() + timedelta(hours=get_settings().EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)))
    return raw


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def ensure_demo_user(db: Session) -> User:
    user = db.query(User).filter(User.email == "umair@healsense.com").first()
    patient = db.query(Patient).filter(Patient.id == "P001").first()
    if not user:
        user = User(id=str(uuid.uuid4()), email="umair@healsense.com", password_hash=hash_password("password123"), full_name="Muhammad Umair", patient_id=patient.id if patient else None, is_email_verified=True, is_active=True)
        db.add(user)
    else:
        if not user.is_email_verified: user.is_email_verified = True
        if not user.patient_id and patient: user.patient_id = patient.id
    return user


def _smtp_send(email: str, link: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["Subject"] = "Verify your HealSense email"
    message["From"] = settings.MAIL_DEFAULT_SENDER or settings.MAIL_USERNAME
    message["To"] = email
    message.set_content(f"Verify your HealSense account by opening this link:\n{link}\n")
    with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=15) as smtp:
        if settings.MAIL_USE_TLS: smtp.starttls()
        if settings.MAIL_USERNAME and settings.MAIL_PASSWORD: smtp.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        smtp.send_message(message)


async def send_verification_email(email: str, raw_token: str) -> dict:
    settings = get_settings()
    link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={raw_token}"
    configured = all([settings.MAIL_SERVER, settings.MAIL_USERNAME, settings.MAIL_PASSWORD, settings.MAIL_DEFAULT_SENDER])
    if configured:
        await asyncio.to_thread(_smtp_send, email, link)
        return {"mode": "smtp", "sent": True}
    if settings.ENV != "production":
        logger.info("DEV EMAIL (SMTP not configured) verification link for %s: %s", email, link)
        return {"mode": "dev_log", "sent": True}
    raise RuntimeError("Email delivery is not configured")
