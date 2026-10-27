"""
Telemetry Ingestion & Processing Service
Handles device authentication, schema validation, persistence, prediction execution, and decision fusion.
"""
import uuid
import logging
import hashlib
import hmac
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
from api.config import get_settings

def resolve_data_origin(requested, allow_simulated):
    return "simulated" if requested == "simulated" and allow_simulated else "device"

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

        # External hardware must have a provisioned API key. A missing
        # stored hash is a provisioning failure, never a bypass.
        if not device.api_key_hash:
            logger.warning(f"Telemetry submission rejected: No API key configured for device {device_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid device credentials or unregistered device"
            )

        if not hmac.compare_digest(hash_api_key(x_device_api_key), device.api_key_hash):
            logger.warning(f"Telemetry submission rejected: Invalid API key hash for device {device_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid X-Device-API-Key"
            )

        logger.info(f"Device authenticated successfully: {device_id}")
        return device

    def _get_patient_or_404(self, patient_id: str, device_id: str, db: Session) -> Patient:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            logger.error(f"Telemetry ingestion failed: Patient {patient_id} not found for device {device_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )
        return patient

    async def process_telemetry(
        self,
        payload: TelemetryPayload,
        x_device_api_key: Optional[str],
        db: Session
    ) -> TelemetryResponse:
        """Process external ESP32 telemetry after strict device authentication."""
        device = self.authenticate_device(payload.device_id, x_device_api_key, db)
        patient = self._get_patient_or_404(payload.patient_id, payload.device_id, db)

        if device.patient_id != payload.patient_id:
            logger.warning(
                "Telemetry submission rejected: Device %s is not assigned to patient %s",
                payload.device_id,
                payload.patient_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid device credentials or unregistered device"
            )

        return await self._process_validated_telemetry(payload, device, patient, db)

    async def process_internal_telemetry(
        self,
        payload: TelemetryPayload,
        db: Session,
        *,
        authorized_patient_id: str,
    ) -> TelemetryResponse:
        """Process telemetry from an already owner-authenticated patient route.

        This trusted internal path must only be called after the route has
        authenticated the user and verified ownership of the patient. It
        deliberately does not accept or compare a hardware API key.
        """
        if payload.patient_id != authorized_patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to submit telemetry for this patient"
            )

        patient = self._get_patient_or_404(payload.patient_id, payload.device_id, db)
        device = db.query(Device).filter(Device.device_id == payload.device_id).first()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        if device.patient_id not in (None, authorized_patient_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device is not assigned to this patient"
            )

        if not device.connected:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device is currently disabled or disconnected"
            )

        if device.patient_id is None:
            device.patient_id = authorized_patient_id

        return await self._process_validated_telemetry(payload, device, patient, db)

    async def _process_validated_telemetry(
        self,
        payload: TelemetryPayload,
        device: Device,
        patient: Patient,
        db: Session
    ) -> TelemetryResponse:
        """Shared persistence/prediction/broadcast pipeline for validated telemetry."""
        timestamp = payload.timestamp or datetime.utcnow()
        device.connected = True
        device.last_heartbeat = datetime.utcnow()

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
            status=HealthStatus.NORMAL,
            data_origin=resolve_data_origin(payload.data_origin, get_settings().ALLOW_SIMULATED_TELEMETRY)
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
                # Pass through None when BP was not measured; PredictionService
                # imputes these with the training medians. Do NOT substitute
                # 120/80 here — that would fabricate data at serve time.
                "systolic_bp": v.systolic_bp,
                "diastolic_bp": v.diastolic_bp
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
