"""
Telemetry Ingestion & Processing Service
Handles device authentication, schema validation, persistence, prediction execution, and decision fusion.
"""
import uuid
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Header, Depends

from api.models.database import Device, Patient, VitalSigns, get_db
from api.models.database.models import BpSource as DBBpSource
from api.models.schemas import (
    TelemetryPayload,
    TelemetryResponse,
    BpSource,
    HealthStatus
)
from api.services.prediction_service import prediction_service
from api.services.fusion_engine import fusion_engine
from api.services.realtime import realtime_manager

logger = logging.getLogger(__name__)


def hash_api_key(api_key: str) -> str:
    """Hashes an API key using SHA-256 for secure lookup."""
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


class TelemetryIngestionService:
    """Service encapsulating direct hardware telemetry ingestion logic."""

    def authenticate_device(
        self,
        device_id: str,
        x_device_api_key: Optional[str],
        db: Session
    ) -> Device:
        """
        Validates presence and authenticity of X-Device-API-Key header against DB records.
        Returns the authenticated Device object.
        """
        if not x_device_api_key:
            logger.warning(f"Telemetry submission rejected: Missing X-Device-API-Key header for device {device_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Device-API-Key header"
            )

        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            logger.warning(f"Telemetry submission rejected: Unregistered device {device_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid device credentials or unregistered device"
            )

        if not device.connected:
            logger.warning(f"Telemetry submission rejected: Disabled device {device_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Device is currently disabled or disconnected"
            )

        # Check API key hash match if device has a configured key
        if device.api_key_hash:
            key_hash = hash_api_key(x_device_api_key)
            if key_hash != device.api_key_hash:
                logger.warning(f"Telemetry submission rejected: Invalid API key hash for device {device_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid X-Device-API-Key"
                )

        logger.info(f"Device authenticated successfully: {device_id}")
        return device

    async def process_telemetry(
        self,
        payload: TelemetryPayload,
        x_device_api_key: Optional[str],
        db: Session
    ) -> TelemetryResponse:
        """
        Processes ingested telemetry payload:
        1. Authenticate device
        2. Verify patient link
        3. Store vital signs in DB
        4. Execute prediction pipeline (LSTM)
        5. Execute fusion engine
        6. Broadcast real-time events
        """
        # 1. Device Authentication
        device = self.authenticate_device(payload.device_id, x_device_api_key, db)

        # 2. Patient Link Verification
        patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
        if not patient:
            logger.error(f"Telemetry ingestion failed: Patient {payload.patient_id} not found for device {payload.device_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {payload.patient_id} not found"
            )

        timestamp = payload.timestamp or datetime.utcnow()

        # 3. Create & Persist VitalSigns DB Record
        db_bp_source = DBBpSource(payload.bp_source.value) if payload.bp_source else DBBpSource.NONE

        db_vitals = VitalSigns(
            id=str(uuid.uuid4()),
            patient_id=payload.patient_id,
            device_id=payload.device_id,
            heart_rate=payload.heart_rate,
            spo2=payload.spo2,
            temperature=payload.temperature,
            systolic_bp=payload.systolic_bp,
            diastolic_bp=payload.diastolic_bp,
            bp_source=db_bp_source,
            delayed_sync=payload.delayed_sync,
            timestamp=timestamp,
            status=HealthStatus.NORMAL
        )

        db.add(db_vitals)
        device.last_heartbeat = timestamp
        db.commit()
        db.refresh(db_vitals)

        # 4. Trigger Prediction & Fusion Pipeline
        vitals_history_records = (
            db.query(VitalSigns)
            .filter(VitalSigns.patient_id == payload.patient_id)
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

        ml_prediction = prediction_service.predict_risk(vitals_history)
        if ml_prediction:
            db_vitals.prediction_confidence = ml_prediction.get("probability")
            db_vitals.full_probability_distribution = ml_prediction.get("full_probability_distribution")
            db_vitals.model_version = ml_prediction.get("model_version")

        # Create Canonical Features for Fusion Engine
        canonical_features = fusion_engine.create_canonical_feature_vector(patient, db_vitals)
        deterministic_eval = fusion_engine.evaluate_deterministic_rules(canonical_features)
        fused_decision = fusion_engine.fuse_risk(deterministic_eval, ml_prediction)

        # Update Vitals status & risk score based on fused decision
        status_mapping = {
            "normal": HealthStatus.NORMAL,
            "warning": HealthStatus.WARNING,
            "critical": HealthStatus.CRITICAL
        }
        db_vitals.status = status_mapping.get(fused_decision["final_risk_level"], HealthStatus.NORMAL)
        db_vitals.risk_score = fused_decision.get("confidence_score")

        db.commit()
        db.refresh(db_vitals)

        # 5. Generate Gemini Explanation if Warning or Critical
        explanation = None
        if fused_decision["final_risk_level"] in ["warning", "critical"]:
            explanation = await fusion_engine.generate_explanation(patient, fused_decision)

        # 6. Realtime WebSocket Broadcast
        await realtime_manager.broadcast_patient(
            payload.patient_id,
            "telemetry.ingested",
            {
                "vital_id": db_vitals.id,
                "device_id": payload.device_id,
                "status": db_vitals.status.value,
                "fused_decision": fused_decision,
                "delayed_sync": payload.delayed_sync,
                "timestamp": timestamp.isoformat()
            }
        )

        logger.info(f"Telemetry stored and evaluated successfully for device {payload.device_id}, patient {payload.patient_id}. Status: {db_vitals.status.value}")

        return TelemetryResponse(
            success=True,
            message="Telemetry ingested and evaluated successfully",
            vital_id=db_vitals.id,
            patient_id=payload.patient_id,
            device_id=payload.device_id,
            status=db_vitals.status,
            fused_decision=fused_decision,
            explanation=explanation
        )


telemetry_service = TelemetryIngestionService()
