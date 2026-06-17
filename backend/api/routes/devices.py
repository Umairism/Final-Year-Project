"""
IoT Device management endpoints - Database version
Supports both hardware IoT devices and mobile phone sensors
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from api.models.schemas import DeviceStatus
from api.models.database import Device, DeviceType, get_db
from api.services.realtime import realtime_manager

router = APIRouter()


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
async def get_device_status(device_id: str, db: Session = Depends(get_db)):
    """Get device status"""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    
    return device


@router.post("/{device_id}/connect")
async def connect_device(device_id: str, patient_id: str, db: Session = Depends(get_db)):
    """Connect device to a patient"""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    
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
        "device": device
    }


@router.post("/{device_id}/disconnect")
async def disconnect_device(device_id: str, db: Session = Depends(get_db)):
    """Disconnect device"""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    
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
        "device": device
    }


@router.post("/register/phone")
async def register_phone_device(
    data: PhoneDeviceRegister,
    db: Session = Depends(get_db)
):
    """
    Register a patient's smartphone as a monitoring device
    
    Enables using phone sensors (Samsung Health, Apple HealthKit) 
    as an alternative to dedicated IoT hardware.
    """
    # Generate unique device ID for phone
    device_id = f"PHONE_{data.patient_id}"
    
    # Check if phone device already exists
    existing = db.query(Device).filter(Device.device_id == device_id).first()
    
    if existing:
        # Update existing phone device
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
async def get_patient_data_sources(patient_id: str, db: Session = Depends(get_db)):
    """
    Get all active data sources (IoT devices + phone sensors) for a patient
    
    Returns priority-ordered list showing which devices are available.
    """
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
    primary = next((d for d in devices if d.connected), None)
    
    return {
        "patient_id": patient_id,
        "data_sources": [
            {
                "device_id": d.device_id,
                "device_type": d.device_type.value,
                "phone_model": d.phone_model,
                "connected": d.connected,
                "battery_level": d.battery_level,
                "last_seen": d.last_heartbeat
            }
            for d in devices
        ],
        "primary_source": primary.device_id if primary else None,
        "total_devices": len(devices)
    }
