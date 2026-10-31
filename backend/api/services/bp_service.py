"""
Blood Pressure Entry Service
============================

Handles *intermittent* blood-pressure measurements — the kind produced by an
upper-arm oscillometric cuff such as the Braun ExactFit 1, by a BLE cuff, or by
a clinician typing numbers into the app.

Why this is a separate path from ``telemetry_service``
------------------------------------------------------
The ESP32 wrist node streams HR / SpO2 / temperature every 10 s. A cuff is
pressed once, gives one reading, and then goes quiet. Forcing that reading into
a brand-new ``VitalSigns`` row would require inventing the other three vitals.

Instead the reading is **attached** to the most recent wearable row that falls
inside ``attach_window_minutes`` (default 60). This is also the clinically
correct semantics: a BP belongs to the physiological state measured moments
before it.

If no wearable row exists (device not running), the caller may supply
``heart_rate`` / ``spo2`` / ``temperature`` to create a standalone row. If they
do not, the request is rejected with HTTP 409 and the assessment is still
returned — a reading is never silently fabricated.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.models.database import Alert, Device, Patient, VitalSigns
from api.models.database.models import (
    AlertSeverity,
    BpSource as DBBpSource,
    DeviceType,
    HealthStatus as DBHealthStatus,
)
from api.models.schemas import BpEntryRequest, BpEntryResponse, HealthStatus
from api.services.fusion_engine import fusion_engine
from api.services.prediction_service import prediction_service
from api.services.realtime import realtime_manager
from api.services.vital_serialization import serialize_vital

logger = logging.getLogger(__name__)

# Maps the fusion engine's string output onto the DB enum.
_STATUS_MAP = {
    "normal": DBHealthStatus.NORMAL,
    "warning": DBHealthStatus.WARNING,
    "critical": DBHealthStatus.CRITICAL,
}

# Same three-way mapping for the Pydantic response schema.
_RESPONSE_STATUS_MAP = {
    "normal": HealthStatus.NORMAL,
    "warning": HealthStatus.WARNING,
    "critical": HealthStatus.CRITICAL,
}

BP_CATEGORY_LABELS = {
    "normal": "Normal",
    "elevated": "Elevated",
    "stage_1_hypertension": "Stage 1 hypertension",
    "stage_2_hypertension": "Stage 2 hypertension",
    "hypertensive_crisis": "Hypertensive crisis",
    "hypotension": "Hypotension",
}


def classify_bp(systolic: float, diastolic: float) -> str:
    """
    AHA/ACC 2017 category for a single reading.

    Order matters: crisis and stage-2 are checked before hypotension so an
    absurd 185/55 is never labelled "hypotension". The engine's CRITICAL rule
    only fires at >= 180/120; lower stages are informational and are left to
    the fusion layer so the system does not cry wolf on a single 135/86.
    """
    if systolic >= 180 or diastolic >= 120:
        return "hypertensive_crisis"
    if systolic >= 140 or diastolic >= 90:
        return "stage_2_hypertension"
    if systolic < 90 or diastolic < 60:
        return "hypotension"
    if systolic >= 130 or diastolic >= 80:
        return "stage_1_hypertension"
    if systolic >= 120:
        return "elevated"
    return "normal"


def _serialize_vital(vital: VitalSigns) -> Dict[str, Any]:
    """Shape a VitalSigns row using the shared canonical vital serializer."""
    return serialize_vital(vital)


def _ensure_device(db: Session, patient_id: str, device_id: Optional[str]) -> Device:
    """Return (creating if needed) a manual-entry device for the patient."""
    resolved_id = device_id or f"DEV_MANUAL_{patient_id}"
    device = db.query(Device).filter(Device.device_id == resolved_id).first()
    if device:
        device.last_heartbeat = datetime.utcnow()
        return device

    device = Device(
        device_id=resolved_id,
        patient_id=patient_id,
        device_type=DeviceType.MANUAL,
        connected=True,
        last_heartbeat=datetime.utcnow(),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def _create_crisis_alert(
    db: Session,
    patient_id: str,
    entry: BpEntryRequest,
    triggered_rules: List[str],
) -> Optional[str]:
    """
    Raise a CRITICAL alert for a hypertensive crisis, deduplicated to one alert
    per 10 minutes so a repeated reading does not spam the dashboard.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    existing = (
        db.query(Alert)
        .filter(
            Alert.patient_id == patient_id,
            Alert.vital_type == "blood_pressure",
            Alert.timestamp >= cutoff,
        )
        .first()
    )
    if existing:
        return existing.id

    alert = Alert(
        id=f"A_{uuid.uuid4().hex[:16]}",
        patient_id=patient_id,
        message=(
            f"Hypertensive crisis: {entry.systolic_bp:.0f}/{entry.diastolic_bp:.0f} mmHg "
            f"({'; '.join(triggered_rules) or 'BP >= 180/120'}). "
            f"Seek medical attention if the reading is confirmed on repeat measurement."
        ),
        severity=AlertSeverity.CRITICAL,
        vital_type="blood_pressure",
        timestamp=datetime.utcnow(),
        acknowledged=False,
        dismissed=False,
    )
    db.add(alert)
    db.commit()
    return alert.id


class BpEntryService:
    """Service encapsulating intermittent blood-pressure ingestion."""

    async def record_bp(
        self,
        patient_id: str,
        entry: BpEntryRequest,
        db: Session,
    ) -> BpEntryResponse:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found",
            )

        measured_at = entry.measured_at or datetime.utcnow()
        window_start = measured_at - timedelta(minutes=entry.attach_window_minutes)
        db_bp_source = DBBpSource(entry.bp_source.value)

        # ---- 1. Look for a wearable reading to attach this BP to -----------
        anchor = (
            db.query(VitalSigns)
            .filter(
                VitalSigns.patient_id == patient_id,
                VitalSigns.timestamp >= window_start,
            )
            .order_by(VitalSigns.timestamp.desc())
            .first()
        )

        attached = anchor is not None

        if attached:
            # Update the newest row in place: the BP describes the physiological
            # state that row captured, so it must not create a parallel record.
            anchor.systolic_bp = entry.systolic_bp
            anchor.diastolic_bp = entry.diastolic_bp
            anchor.bp_source = db_bp_source
            vital_row = anchor
        else:
            # ---- 2. Standalone fallback ------------------------------------
            missing = [
                name
                for name, value in (
                    ("heart_rate", entry.heart_rate),
                    ("spo2", entry.spo2),
                    ("temperature", entry.temperature),
                )
                if value is None
            ]
            category = classify_bp(entry.systolic_bp, entry.diastolic_bp)
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "no_anchor_reading",
                        "message": (
                            "No wearable reading found within "
                            f"{entry.attach_window_minutes} min, so this BP has nothing to "
                            "attach to. Start the ESP32 wrist node, or resend the request "
                            "with heart_rate, spo2 and temperature filled in."
                        ),
                        "missing_fields": missing,
                        "systolic_bp": entry.systolic_bp,
                        "diastolic_bp": entry.diastolic_bp,
                        "category": category,
                        "category_label": BP_CATEGORY_LABELS.get(category, category),
                        "urgent": category in ("hypertensive_crisis", "stage_2_hypertension"),
                    },
                )

            device = _ensure_device(db, patient_id, entry.device_id)
            vital_row = VitalSigns(
                id=str(uuid.uuid4()),
                patient_id=patient_id,
                device_id=device.device_id,
                heart_rate=entry.heart_rate,
                spo2=entry.spo2,
                temperature=entry.temperature,
                systolic_bp=entry.systolic_bp,
                diastolic_bp=entry.diastolic_bp,
                bp_source=db_bp_source,
                delayed_sync=False,
                data_source=DeviceType.MANUAL,
                sensor_accuracy=0.9,
                activity_context="resting",
                timestamp=measured_at,
                status=DBHealthStatus.NORMAL,
                data_origin="manual",
            )
            db.add(vital_row)
            db.commit()
            db.refresh(vital_row)

        # ---- 3. Re-run rules + LSTM + fusion on the updated state ----------
        canonical = fusion_engine.create_canonical_feature_vector(patient, vital_row)
        deterministic = fusion_engine.evaluate_deterministic_rules(canonical)

        history_rows = (
            db.query(VitalSigns)
            .filter(VitalSigns.patient_id == patient_id)
            .order_by(VitalSigns.timestamp.desc())
            .limit(60)
            .all()
        )
        history = [
            {
                "heart_rate": row.heart_rate,
                "spo2": row.spo2,
                "temperature": row.temperature,
                # None is intentional: PredictionService imputes it with the
                # training medians and flags it as missing. Substituting 120/80
                # here would fabricate a normal reading.
                "systolic_bp": row.systolic_bp,
                "diastolic_bp": row.diastolic_bp,
            }
            for row in reversed(history_rows)
        ]

        ml_prediction = prediction_service.predict_risk(history)
        fused = fusion_engine.fuse_risk(deterministic, ml_prediction)

        vital_row.status = _STATUS_MAP.get(fused["final_risk_level"], DBHealthStatus.NORMAL)
        vital_row.risk_score = fused.get("confidence_score")
        if ml_prediction:
            vital_row.prediction_confidence = ml_prediction.get("probability")
            vital_row.full_probability_distribution = ml_prediction.get("full_probability_distribution")
            vital_row.model_version = ml_prediction.get("model_version")

        db.commit()
        db.refresh(vital_row)

        # ---- 4. Alert on hypertensive crisis -------------------------------
        alert_id = None
        if fused["final_risk_level"] == "critical":
            alert_id = _create_crisis_alert(db, patient_id, entry, deterministic["triggered_rules"])

        # ---- 5. Push to dashboards / mobile --------------------------------
        await realtime_manager.broadcast_patient(
            patient_id,
            "patient.vitals.created",
            {
                "vital": serialize_vital(vital_row),
                "device_id": vital_row.device_id,
                "fused_decision": fused,
            },
        )
        await realtime_manager.broadcast_patient(
            patient_id,
            "patient.bp.recorded",
            {
                "vital_id": vital_row.id,
                "systolic_bp": entry.systolic_bp,
                "diastolic_bp": entry.diastolic_bp,
                "pulse": entry.pulse,
                "bp_source": entry.bp_source.value,
                "category": classify_bp(entry.systolic_bp, entry.diastolic_bp),
                "attached": attached,
                "fused_decision": fused,
                "alert_id": alert_id,
            },
        )

        category = classify_bp(entry.systolic_bp, entry.diastolic_bp)
        logger.info(
            "BP recorded for patient %s: %.0f/%.0f (%s, attached=%s, status=%s)",
            patient_id,
            entry.systolic_bp,
            entry.diastolic_bp,
            category,
            attached,
            fused["final_risk_level"],
        )

        return BpEntryResponse(
            success=True,
            attached=attached,
            vital_id=vital_row.id,
            patient_id=patient_id,
            systolic_bp=entry.systolic_bp,
            diastolic_bp=entry.diastolic_bp,
            pulse=entry.pulse,
            bp_source=entry.bp_source,
            category=category,
            triggered_rules=deterministic["triggered_rules"],
            status=_RESPONSE_STATUS_MAP.get(fused["final_risk_level"], HealthStatus.NORMAL),
            fused_decision=fused,
            alert_id=alert_id,
            message=(
                f"{entry.systolic_bp:.0f}/{entry.diastolic_bp:.0f} mmHg recorded and "
                f"{'attached to the latest wearable reading' if attached else 'stored as a standalone reading'}. "
                f"Category: {BP_CATEGORY_LABELS.get(category, category)}."
            ),
        )


bp_service = BpEntryService()
