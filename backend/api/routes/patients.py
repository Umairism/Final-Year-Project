"""
Patient management endpoints - Database version
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from api.models.schemas import (
    Patient as PatientSchema,
    PatientProfile,
    PatientCreate,
    PatientUpdate,
    VitalSigns as VitalSignsSchema,
    Alert as AlertSchema,
)
from api.models.database import (
    Patient,
    VitalSigns,
    Alert,
    Device,
    Emergency,
    get_db,
    HealthStatus,
    DeviceType,
)
from api.services.realtime import realtime_manager
from api.services.prediction_service import prediction_service
from api.services.fusion_engine import fusion_engine

router = APIRouter()


@router.get("/{patient_id}", response_model=PatientSchema)
async def get_patient(patient_id: str, db: Session = Depends(get_db)):
    """Get patient by ID"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    return patient


@router.get("/{patient_id}/profile", response_model=PatientProfile)
async def get_patient_profile(patient_id: str, db: Session = Depends(get_db)):
    """Get patient profile with latest vitals"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Get latest vitals
    latest_vitals = (
        db.query(VitalSigns)
        .filter(VitalSigns.patient_id == patient_id)
        .order_by(VitalSigns.timestamp.desc())
        .first()
    )
    
    # Check device connection
    device = db.query(Device).filter(Device.patient_id == patient_id).first()
    device_connected = device.connected if device else False
    last_sync = device.last_heartbeat if device else None
    
    # Convert to dict and add extra fields
    patient_dict = {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "age": patient.age,
        "gender": patient.gender,
        "blood_type": patient.blood_type,
        "email": patient.email,
        "phone": patient.phone,
        "created_at": patient.created_at,
        "updated_at": patient.updated_at,
        "latest_vitals": latest_vitals,
        "device_connected": device_connected,
        "last_sync": last_sync
    }
    
    return patient_dict


@router.get("/{patient_id}/vitals/latest", response_model=VitalSignsSchema)
async def get_latest_vitals(patient_id: str, db: Session = Depends(get_db)):
    """Get latest vital signs for a patient"""
    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Get latest vitals
    vitals = (
        db.query(VitalSigns)
        .filter(VitalSigns.patient_id == patient_id)
        .order_by(VitalSigns.timestamp.desc())
        .first()
    )
    
    if not vitals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No vitals found for patient {patient_id}"
        )
    
    return vitals


@router.get("/{patient_id}/vitals/history", response_model=List[VitalSignsSchema])
async def get_vital_history(
    patient_id: str,
    minutes: int = 60,
    db: Session = Depends(get_db)
):
    """Get vital signs history for a patient"""
    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Calculate time window
    time_threshold = datetime.utcnow() - timedelta(minutes=minutes)
    
    # Get vitals within time window
    vitals = (
        db.query(VitalSigns)
        .filter(
            VitalSigns.patient_id == patient_id,
            VitalSigns.timestamp >= time_threshold
        )
        .order_by(VitalSigns.timestamp.desc())
        .all()
    )
    
    return vitals


@router.get("/{patient_id}/fusion_risk")
async def get_fusion_risk(patient_id: str, db: Session = Depends(get_db)):
    """Evaluate patient risk using the Hybrid Fusion Engine"""
    # 1. Fetch Patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
        
    # 2. Fetch Latest Vitals
    latest_vitals = (
        db.query(VitalSigns)
        .filter(VitalSigns.patient_id == patient_id)
        .order_by(VitalSigns.timestamp.desc())
        .first()
    )
    if not latest_vitals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No vitals found for patient {patient_id}"
        )
        
    # 3. Create Canonical Feature Vector
    features = fusion_engine.create_canonical_feature_vector(patient, latest_vitals)
    
    # 4. Layer 2: Deterministic Rules
    deterministic_output = fusion_engine.evaluate_deterministic_rules(features)
    
    # 5. Layer 3: ML Model Prediction (Fetch 60 history sequence)
    vitals_history_records = (
        db.query(VitalSigns)
        .filter(VitalSigns.patient_id == patient_id)
        .order_by(VitalSigns.timestamp.desc())
        .limit(60)
        .all()
    )
    
    ml_prediction = None
    if len(vitals_history_records) == 60:
        vitals_history = [
            {
                "heart_rate": v.heart_rate,
                "spo2": v.spo2,
                "temperature": v.temperature,
                "systolic_bp": v.systolic_bp or 120.0,
                "diastolic_bp": v.diastolic_bp or 80.0
            }
            for v in reversed(vitals_history_records)
        ]
        ml_prediction = prediction_service.predict_risk(vitals_history)
        
    # 6. Layer 4: Pure Code Fusion
    fusion_result = fusion_engine.fuse_risk(deterministic_output, ml_prediction)
    
    # 7. Layer 5: LLM Clinical Explanation
    explanation = await fusion_engine.generate_explanation(patient, fusion_result)
    
    return {
        "canonical_features": features.dict(),
        "deterministic_evaluation": deterministic_output,
        "ml_evaluation": ml_prediction,
        "fused_decision": fusion_result,
        "clinical_reasoning": explanation
    }


@router.get("/{patient_id}/alerts", response_model=List[AlertSchema])
async def get_patient_alerts(patient_id: str, db: Session = Depends(get_db)):
    """Get alerts for a patient"""
    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Get alerts
    alerts = (
        db.query(Alert)
        .filter(Alert.patient_id == patient_id)
        .order_by(Alert.timestamp.desc())
        .all()
    )
    
    return alerts


@router.post("/{patient_id}/vitals", response_model=VitalSignsSchema, status_code=status.HTTP_201_CREATED)
async def create_vital_signs(
    patient_id: str,
    vitals: VitalSignsSchema,
    db: Session = Depends(get_db)
):
    """Create new vital signs entry"""
    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Create new vitals record
    db_vitals = VitalSigns(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        heart_rate=vitals.heart_rate,
        spo2=vitals.spo2,
        temperature=vitals.temperature,
        systolic_bp=vitals.systolic_bp,
        diastolic_bp=vitals.diastolic_bp,
        respiratory_rate=vitals.respiratory_rate,
        timestamp=datetime.utcnow(),
        status=vitals.status,
        risk_score=vitals.risk_score
    )
    
    db.add(db_vitals)
    db.commit()
    db.refresh(db_vitals)

    # Secondary Layer: LSTM Prediction
    vitals_history_records = (
        db.query(VitalSigns)
        .filter(VitalSigns.patient_id == patient_id)
        .order_by(VitalSigns.timestamp.desc())
        .limit(60)
        .all()
    )
    vitals_history = [
        {
            "heart_rate": v.heart_rate,
            "spo2": v.spo2,
            "temperature": v.temperature,
            "systolic_bp": v.systolic_bp or 120.0,
            "diastolic_bp": v.diastolic_bp or 80.0
        }
        for v in reversed(vitals_history_records)
    ]
    
    prediction = prediction_service.predict_risk(vitals_history)
    ai_analysis = None
    if prediction:
        db_vitals.prediction_confidence = prediction["probability"]
        db_vitals.full_probability_distribution = prediction["full_probability_distribution"]
        db_vitals.model_version = prediction["model_version"]
        db.commit()
        db.refresh(db_vitals)
        ai_analysis = prediction

    await realtime_manager.broadcast_patient(
        patient_id,
        "patient.vitals.created",
        {
            "vital": {
                "id": db_vitals.id,
                "heart_rate": db_vitals.heart_rate,
                "spo2": db_vitals.spo2,
                "temperature": db_vitals.temperature,
                "systolic_bp": db_vitals.systolic_bp,
                "diastolic_bp": db_vitals.diastolic_bp,
                "respiratory_rate": db_vitals.respiratory_rate,
                "status": db_vitals.status.value if db_vitals.status else None,
                "timestamp": db_vitals.timestamp,
            },
            "ai_analysis": ai_analysis
        },
    )
    
    return db_vitals


@router.post("/{patient_id}/vitals/phone", status_code=status.HTTP_201_CREATED)
async def create_vitals_from_phone(
    patient_id: str,
    device_id: str,
    heart_rate: float,
    spo2: float,
    temperature: Optional[float] = 37.0,
    activity_context: Optional[str] = "resting",
    accuracy: Optional[float] = 0.9,
    location_lat: Optional[float] = None,
    location_lng: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Record vitals from phone sensors (Samsung Health, Apple HealthKit)
    
    Accepts data from smartphone health monitoring sensors as an 
    alternative to dedicated IoT hardware devices.
    """
    # Validate patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Determine health status based on vitals
    health_status = HealthStatus.NORMAL
    if heart_rate > 120 or heart_rate < 50 or spo2 < 92:
        health_status = HealthStatus.WARNING
    if heart_rate > 150 or heart_rate < 40 or spo2 < 85:
        health_status = HealthStatus.CRITICAL
    
    # Create vital signs record with phone data
    vital_id = f"V_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    db_vitals = VitalSigns(
        id=vital_id,
        patient_id=patient_id,
        device_id=device_id,
        heart_rate=heart_rate,
        spo2=spo2,
        temperature=temperature,
        data_source=DeviceType.MOBILE_APP,
        sensor_accuracy=accuracy,
        activity_context=activity_context,
        location_lat=location_lat,
        location_lng=location_lng,
        timestamp=datetime.utcnow(),
        status=health_status
    )
    
    db.add(db_vitals)
    
    # Create alert if vitals are abnormal
    if health_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
        alert_message = f"Abnormal vitals detected from phone sensors: "
        if heart_rate > 120:
            alert_message += f"High HR ({heart_rate} bpm). "
        elif heart_rate < 50:
            alert_message += f"Low HR ({heart_rate} bpm). "
        if spo2 < 92:
            alert_message += f"Low SpO2 ({spo2}%). "
        
        alert = Alert(
            id=f"A_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            patient_id=patient_id,
            message=alert_message,
            severity="CRITICAL" if health_status == HealthStatus.CRITICAL else "MEDIUM",
            vital_type="combined",
            timestamp=datetime.utcnow(),
            acknowledged=False,
            dismissed=False
        )
        db.add(alert)
    
    db.commit()
    db.refresh(db_vitals)

    # Secondary Layer: LSTM Prediction
    vitals_history_records = (
        db.query(VitalSigns)
        .filter(VitalSigns.patient_id == patient_id)
        .order_by(VitalSigns.timestamp.desc())
        .limit(60)
        .all()
    )
    vitals_history = [
        {
            "heart_rate": v.heart_rate,
            "spo2": v.spo2,
            "temperature": v.temperature,
            "systolic_bp": v.systolic_bp or 120.0,
            "diastolic_bp": v.diastolic_bp or 80.0
        }
        for v in reversed(vitals_history_records)
    ]
    
    prediction = prediction_service.predict_risk(vitals_history)
    ai_analysis = None
    if prediction:
        db_vitals.prediction_confidence = prediction["probability"]
        db_vitals.full_probability_distribution = prediction["full_probability_distribution"]
        db_vitals.model_version = prediction["model_version"]
        db.commit()
        db.refresh(db_vitals)
        ai_analysis = prediction

    await realtime_manager.broadcast_patient(
        patient_id,
        "patient.vitals.phone_created",
        {
            "device_id": device_id,
            "heart_rate": heart_rate,
            "spo2": spo2,
            "temperature": temperature,
            "activity_context": activity_context,
            "accuracy": accuracy,
            "status": health_status.value,
            "alert_created": health_status != HealthStatus.NORMAL,
            "ai_analysis": ai_analysis
        },
    )

    if health_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
        await realtime_manager.broadcast_patient(
            patient_id,
            "patient.alert.created",
            {
                "device_id": device_id,
                "heart_rate": heart_rate,
                "spo2": spo2,
                "status": health_status.value,
                "ai_analysis": ai_analysis
            },
        )
    
    return {
        "message": "Phone vitals recorded successfully",
        "vital_id": vital_id,
        "status": health_status.value,
        "data_source": "mobile_app",
        "activity_context": activity_context,
        "alert_created": health_status != HealthStatus.NORMAL,
        "ai_analysis": ai_analysis
    }


@router.post("/{patient_id}/emergency")
async def trigger_emergency(patient_id: str, db: Session = Depends(get_db)):
    """Trigger emergency alert for a patient"""
    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Create emergency record
    emergency = Emergency(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        status="dispatched",
        triggered_at=datetime.utcnow()
    )
    
    db.add(emergency)
    db.commit()

    await realtime_manager.broadcast_patient(
        patient_id,
        "patient.emergency.triggered",
        {
            "emergency_id": emergency.id,
            "status": emergency.status,
            "triggered_at": emergency.triggered_at,
        },
    )
    
    return {
        "emergency_id": emergency.id,
        "patient_id": patient_id,
        "triggered_at": emergency.triggered_at,
        "status": emergency.status,
        "message": "Emergency services have been notified"
    }


@router.post("/", response_model=PatientSchema, status_code=status.HTTP_201_CREATED)
async def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    """Create a new patient"""
    # Generate patient ID
    # Get count of existing patients
    count = db.query(Patient).count()
    patient_id = f"P{str(count + 1).zfill(3)}"
    
    # Check if email already exists
    if patient.email:
        existing = db.query(Patient).filter(Patient.email == patient.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create new patient
    db_patient = Patient(
        id=patient_id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        age=patient.age,
        gender=patient.gender,
        blood_type=patient.blood_type,
        email=patient.email,
        phone=patient.phone,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)

    await realtime_manager.broadcast(
        "patient.created",
        {
            "patient_id": db_patient.id,
            "first_name": db_patient.first_name,
            "last_name": db_patient.last_name,
            "created_at": db_patient.created_at,
        },
    )
    
    return db_patient


@router.put("/{patient_id}", response_model=PatientSchema)
async def update_patient(
    patient_id: str,
    patient_update: PatientUpdate,
    db: Session = Depends(get_db)
):
    """Update patient information"""
    # Get patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Update fields
    update_data = patient_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    
    patient.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(patient)
    
    return patient


@router.delete("/{patient_id}")
async def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    """Delete a patient"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    db.delete(patient)
    db.commit()
    
    return {"message": f"Patient {patient_id} deleted successfully"}
