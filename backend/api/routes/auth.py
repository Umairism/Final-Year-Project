import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.models.database import EmailVerificationToken, Patient, User, get_db
from api.models.schemas import LoginRequest, RegisterRequest, ResendVerificationRequest, VerifyEmailRequest
from api.services.auth_service import (create_access_token, decode_access_token, ensure_demo_user, hash_password,
    new_verification_token, send_verification_email, token_hash, validate_password, verify_password, _secret_or_503)

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


def err(code: str, message: str):
    return HTTPException(status_code=400, detail={"error": code, "message": message})


def safe_user(user: User):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "patient_id": user.patient_id, "is_email_verified": user.is_email_verified, "is_active": user.is_active}


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    _secret_or_503()
    try: validate_password(payload.password)
    except ValueError as exc: raise HTTPException(422, detail=str(exc))
    email = str(payload.email).lower()
    patient_id = "P_" + uuid.uuid4().hex
    first, _, last = payload.full_name.strip().partition(" ")
    patient = Patient(id=patient_id, first_name=first, last_name=last or first, age=payload.age, gender=payload.gender, blood_type=payload.blood_type, email=email, diabetes="unknown", smoking_status="unknown", medications=[], past_conditions=[], emergency_contacts=[])
    user = User(id=str(uuid.uuid4()), email=email, password_hash=hash_password(payload.password), full_name=payload.full_name.strip(), patient_id=patient_id)
    db.add_all([patient, user]); raw = new_verification_token(db, user)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, detail={"error": "email_already_registered", "message": "An account with this email already exists"})
    try: delivery = await send_verification_email(email, raw)
    except Exception:
        raise HTTPException(502, detail={"error": "email_delivery_failed", "message": "Verification email could not be sent"})
    return {"user": {**safe_user(user), "is_email_verified": False}, "verification_required": True, "email_delivery": delivery}


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    row = db.query(EmailVerificationToken).filter(EmailVerificationToken.token_hash == token_hash(payload.token), EmailVerificationToken.used_at.is_(None)).first()
    if not row or row.expires_at <= datetime.utcnow(): raise err("invalid_or_expired_token", "The verification token is invalid or expired")
    row.used_at = datetime.utcnow(); row.user.is_email_verified = True; db.commit()
    return {"verified": True, "email": row.user.email}


@router.post("/resend-verification")
async def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(payload.email).lower()).first()
    if user and not user.is_email_verified and user.is_active:
        db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id, EmailVerificationToken.used_at.is_(None)).update({EmailVerificationToken.used_at: datetime.utcnow()})
        raw = new_verification_token(db, user); db.commit()
        try: await send_verification_email(user.email, raw)
        except Exception: pass
    return {"message": "If an unverified account exists for this email, a new verification link has been sent."}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(payload.email).lower()).first()
    if not user:
        # Trigger the same sanitized config failure for missing SECRET_KEY.
        from api.config import get_settings
        if not get_settings().SECRET_KEY: create_access_token(User(id="", email="", patient_id=None))
        raise HTTPException(401, detail={"error": "invalid_credentials", "message": "Invalid email or password"})
    if not verify_password(payload.password, user.password_hash): raise HTTPException(401, detail={"error": "invalid_credentials", "message": "Invalid email or password"})
    if not user.is_active: raise HTTPException(403, detail={"error": "account_disabled", "message": "This account is disabled"})
    if not user.is_email_verified: raise HTTPException(403, detail={"error": "email_not_verified", "message": "Please verify your email before logging in"})
    token, expires = create_access_token(user); user.last_login_at = datetime.utcnow(); db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_in": expires, "user": safe_user(user)}


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Authentication is required"},
        )

    payload = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == payload["sub"]).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Invalid or inactive access token"},
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=403,
            detail={"error": "email_not_verified", "message": "Email verification is required"},
        )

    return user


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return safe_user(user)
