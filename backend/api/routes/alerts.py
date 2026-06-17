"""
Alert management endpoints - Database version
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from api.models.database import Alert, get_db
from api.services.realtime import realtime_manager

router = APIRouter()


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    """Acknowledge an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    
    db.commit()
    db.refresh(alert)

    await realtime_manager.broadcast_patient(
        alert.patient_id,
        "alert.acknowledged",
        {
            "alert_id": alert_id,
            "acknowledged": True,
            "acknowledged_at": alert.acknowledged_at,
        },
    )
    
    return {
        "alert_id": alert_id,
        "acknowledged": True,
        "acknowledged_at": alert.acknowledged_at,
        "message": "Alert acknowledged"
    }


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str, db: Session = Depends(get_db)):
    """Dismiss an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    alert.dismissed = True
    alert.dismissed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(alert)

    await realtime_manager.broadcast_patient(
        alert.patient_id,
        "alert.dismissed",
        {
            "alert_id": alert_id,
            "dismissed": True,
            "dismissed_at": alert.dismissed_at,
        },
    )
    
    return {
        "alert_id": alert_id,
        "dismissed": True,
        "dismissed_at": alert.dismissed_at,
        "message": "Alert dismissed"
    }
