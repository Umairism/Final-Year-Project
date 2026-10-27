"""
IoT Device management endpoints - Database version
Supports both hardware IoT devices and mobile phone sensors
"""
import secrets

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from api.models.schemas import DeviceStatus
from api.models.database import Device, DeviceType, Patient, User, get_db
from api.routes.auth import get_current_user
from api.services.realtime import realtime_manager
from api.services.telemetry_service import hash_api_key
from api.services.device_presence import compute_device_presence
from api.config import get_settings

router = APIRouter()


def _device_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Device not found",
    )


def _own_patient_id(current_user: User) -> str:
    if not current_user.patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "patient_not_linked",
                "message": "This account is not linked to a patient record",
            },
        )
    return current_user.patient_id


def _require_own_patient(current_user: User, patient_id: str) -> str:
    own_patient_id = _own_patient_id(current_user)
    if patient_id != own_patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this patient's devices",
        )
    return own_patient_id


def _get_owned_device(db: Session, device_id: str, current_user: User) -> Device:
    own_patient_id = _own_patient_id(current_user)
    device = (
        db.query(Device)
        .filter(Device.device_id == device_id, Device.patient_id == own_patient_id)
        .first()
    )
    if not device:
        raise _device_not_found()
    return device


def _get_assignable_device(db: Session, device_id: str, current_user: User):
    own_patient_id = _own_patient_id(current_user)
    patient = db.query(Patient).filter(Patient.id == own_patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked patient not found",
        )
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if device and device.patient_id not in (None, own_patient_id):
        raise _device_not_found()
    return device, own_patient_id


def _device_summary(device: Device):
    return {
        "device_id": device.device_id,
        "patient_id": device.patient_id,
        "device_type": device.device_type.value if device.device_type else None,
        "connected": device.connected,
        "battery_level": device.battery_level,
        "signal_strength": device.signal_strength,
        "last_heartbeat": device.last_heartbeat,
    }



# Pydantic schemas for phone device registration
class PhoneDeviceRegister(BaseModel):
    """Schema for registering a phone as a device"""
    patient_id: str
    phone_model: str
    phone_os: str
    sensors: List[str]  # ["heart_rate", "spo2", "accelerometer", "gps"]


class PhoneVitalsInput(BaseModel):
    """Schema for vitals data from phone sensors"""
    device_id: str
    heart_rate: float
    spo2: float
    temperature: Optional[float] = 37.0
    activity_context: Optional[str] = "resting"
    accuracy: Optional[float] = 0.9
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None


@router.get("/{device_id}/status", response_model=DeviceStatus)
async def get_device_status(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status for a device assigned to the authenticated user."""
    device = _get_owned_device(db, device_id, current_user)
    
    return {**{c.name: getattr(device, c.name) for c in Device.__table__.columns}, **compute_device_presence(device, online_window_seconds=get_settings().DEVICE_ONLINE_WINDOW_SECONDS)}


@router.post("/{device_id}/connect")
async def connect_device(
    device_id: str,
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Connect a device to the authenticated user's own patient."""
    _require_own_patient(current_user, patient_id)
    device, _ = _get_assignable_device(db, device_id, current_user)
    
    if not device:
        # Create new device
        device = Device(
            device_id=device_id,
            patient_id=patient_id,
            connected=True,
            battery_level=100,
            signal_strength=95,
            last_heartbeat=datetime.utcnow()
        )
        db.add(device)
    else:
        # Update existing device
        device.patient_id = patient_id
        device.connected = True
        device.last_heartbeat = datetime.utcnow()
    
    db.commit()
    db.refresh(device)

    await realtime_manager.broadcast_device(
        device_id,
        "device.connected",
        {
            "patient_id": patient_id,
            "connected": True,
            "last_heartbeat": device.last_heartbeat,
        },
    )
    
    return {
        "message": f"Device {device_id} connected to patient {patient_id}",
        "device": _device_summary(device)
    }


@router.post("/{device_id}/disconnect")
async def disconnect_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect a device assigned to the authenticated user."""
    device = _get_owned_device(db, device_id, current_user)
    
    device.connected = False
    device.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(device)

    await realtime_manager.broadcast_device(
        device_id,
        "device.disconnected",
        {
            "patient_id": device.patient_id,
            "connected": False,
            "updated_at": device.updated_at,
        },
    )
    
    return {
        "message": f"Device {device_id} disconnected",
        "device": _device_summary(device)
    }



@router.post("/{device_id}/api-key")
async def issue_device_api_key(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Provision or rotate a hardware device API key.

    The raw key is returned only in this response. Only its SHA-256 hash
    is stored in the database.
    """
    device, own_patient_id = _get_assignable_device(db, device_id, current_user)

    if device and device.device_type != DeviceType.IOT_HARDWARE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API keys can only be issued to IoT hardware devices",
        )

    if not device:
        device = Device(
            device_id=device_id,
            patient_id=own_patient_id,
            device_type=DeviceType.IOT_HARDWARE,
            connected=True,
        )
        db.add(device)

    raw_api_key = secrets.token_urlsafe(32)
    device.patient_id = own_patient_id
    device.api_key_hash = hash_api_key(raw_api_key)
    device.connected = True
    device.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(device)

    return {
        "message": "Device API key issued. Store it now; it will not be shown again.",
        "device_id": device.device_id,
        "patient_id": device.patient_id,
        "device_api_key": raw_api_key,
    }


@router.post("/register/phone")
async def register_phone_device(
    data: PhoneDeviceRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a patient's smartphone as a monitoring device
    
    Enables using phone sensors (Samsung Health, Apple HealthKit) 
    as an alternative to dedicated IoT hardware.
    """
    _require_own_patient(current_user, data.patient_id)
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked patient not found",
        )

    # Generate unique device ID for phone
    device_id = f"PHONE_{data.patient_id}"
    
    # Check if phone device already exists
    existing = db.query(Device).filter(Device.device_id == device_id).first()
    
    if existing:
        if existing.patient_id not in (None, data.patient_id):
            raise _device_not_found()
        # Update existing phone device
        existing.patient_id = data.patient_id
        existing.device_type = DeviceType.MOBILE_APP
        existing.phone_model = data.phone_model
        existing.phone_os = data.phone_os
        existing.sensor_capabilities = data.sensors
        existing.connected = True
        existing.last_heartbeat = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
        device = existing
        message = "Phone device updated successfully"
    else:
        # Create new phone device
        device = Device(
            device_id=device_id,
            device_type=DeviceType.MOBILE_APP,
            patient_id=data.patient_id,
            phone_model=data.phone_model,
            phone_os=data.phone_os,
            sensor_capabilities=data.sensors,
            connected=True,
            battery_level=100,  # Phone manages its own battery
            signal_strength=100,  # Assume good connectivity
            last_heartbeat=datetime.utcnow()
        )
        db.add(device)
        message = "Phone device registered successfully"
    
    db.commit()
    db.refresh(device)

    await realtime_manager.broadcast_device(
        device_id,
        "device.phone_registered",
        {
            "patient_id": data.patient_id,
            "phone_model": data.phone_model,
            "phone_os": data.phone_os,
            "sensors": data.sensors,
            "connected": True,
        },
    )
    
    return {
        "message": message,
        "device_id": device_id,
        "device_type": "mobile_app",
        "phone_model": data.phone_model,
        "sensors": data.sensors,
        "connected": True
    }


@router.get("/patient/{patient_id}/sources")
async def get_patient_data_sources(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all active data sources (IoT devices + phone sensors) for a patient
    
    Returns priority-ordered list showing which devices are available.
    """
    _require_own_patient(current_user, patient_id)
    devices = db.query(Device).filter(
        Device.patient_id == patient_id
    ).order_by(
        # Priority: IoT_HARDWARE > WEARABLE > MOBILE_APP > MANUAL
        Device.device_type
    ).all()
    
    if not devices:
        return {
            "patient_id": patient_id,
            "data_sources": [],
            "primary_source": None,
            "message": "No devices registered"
        }
    
    # Find primary (currently connected) source
    presence = {d.device_id: compute_device_presence(d, online_window_seconds=get_settings().DEVICE_ONLINE_WINDOW_SECONDS) for d in devices}
    online = [d for d in devices if presence[d.device_id]["is_online"]]
    enabled = [d for d in devices if d.connected]
    primary = max(online or enabled, key=lambda d: d.last_heartbeat or datetime.min, default=None)
    
    return {
        "patient_id": patient_id,
        "data_sources": [
            {
                "device_id": d.device_id,
                "device_type": d.device_type.value,
                "phone_model": d.phone_model,
                "connected": d.connected,
                "enabled": d.connected,
                **presence[d.device_id],
                "battery_level": d.battery_level,
                "last_seen": d.last_heartbeat
            }
            for d in devices
        ],
        "primary_source": primary.device_id if primary else None,
        "total_devices": len(devices)
    }
