"""Authenticated realtime websocket endpoints for live updates."""

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from sqlalchemy.orm import Session

from api.models.database import Device, User, get_db
from api.services.auth_service import decode_access_token
from api.services.realtime import realtime_manager

router = APIRouter()


def _policy_violation() -> WebSocketException:
    return WebSocketException(code=status.WS_1008_POLICY_VIOLATION)


def get_websocket_user(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate a browser WebSocket using the existing JWT.

    Browsers cannot set an Authorization header on WebSocket handshakes,
    so the web client sends the same access token as a query parameter.
    Non-browser clients may use the normal Bearer header instead.
    """
    candidate = token
    if not candidate:
        authorization = websocket.headers.get("authorization", "")
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value:
            candidate = value

    if not candidate:
        raise _policy_violation()

    try:
        payload = decode_access_token(candidate)
    except Exception:
        raise _policy_violation() from None

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active or not user.is_email_verified:
        raise _policy_violation()
    return user


def _require_patient_access(user: User, patient_id: str) -> None:
    if not user.patient_id or user.patient_id != patient_id:
        raise _policy_violation()


def _require_device_access(user: User, device_id: str, db: Session) -> None:
    if not user.patient_id:
        raise _policy_violation()
    device = (
        db.query(Device)
        .filter(Device.device_id == device_id, Device.patient_id == user.patient_id)
        .first()
    )
    if not device:
        raise _policy_violation()


@router.websocket("/ws/live")
async def live_stream(
    websocket: WebSocket,
    user: User = Depends(get_websocket_user),
):
    """Legacy global stream.

    HealSense currently has patient accounts but no clinician/admin role,
    so there is no safe audience for an all-patients stream. Keep the
    route explicit but refuse every subscription; patient/device streams
    below are the supported realtime paths.
    """
    raise _policy_violation()


@router.websocket("/ws/patients/{patient_id}")
async def patient_stream(
    websocket: WebSocket,
    patient_id: str,
    user: User = Depends(get_websocket_user),
):
    """Realtime stream restricted to the authenticated user's patient."""
    _require_patient_access(user, patient_id)
    await realtime_manager.connect(websocket, patient_id=patient_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket, patient_id=patient_id)


@router.websocket("/ws/devices/{device_id}")
async def device_stream(
    websocket: WebSocket,
    device_id: str,
    user: User = Depends(get_websocket_user),
    db: Session = Depends(get_db),
):
    """Realtime stream restricted to devices assigned to the user."""
    _require_device_access(user, device_id, db)
    await realtime_manager.connect(websocket, device_id=device_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket, device_id=device_id)
