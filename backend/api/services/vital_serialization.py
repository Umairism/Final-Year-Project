"""
Vital signs serialization helper for API responses and WebSocket broadcasts.
Shared across telemetry and BP ingestion paths to guarantee a canonical schema
without circular imports.
"""
from typing import Any, Dict
from api.models.database.models import VitalSigns


def serialize_vital(vital: VitalSigns) -> Dict[str, Any]:
    """Serialize a VitalSigns DB model to canonical dictionary format."""
    bp_source_val = None
    if vital.bp_source is not None:
        bp_source_val = vital.bp_source.value if hasattr(vital.bp_source, "value") else str(vital.bp_source)

    status_val = None
    if vital.status is not None:
        status_val = vital.status.value if hasattr(vital.status, "value") else str(vital.status)

    iso_timestamp = None
    if vital.timestamp is not None:
        iso_timestamp = vital.timestamp.isoformat()

    return {
        "id": vital.id,
        "patient_id": vital.patient_id,
        "device_id": vital.device_id,
        "heart_rate": vital.heart_rate,
        "spo2": vital.spo2,
        "temperature": vital.temperature,
        "systolic_bp": vital.systolic_bp,
        "diastolic_bp": vital.diastolic_bp,
        "respiratory_rate": vital.respiratory_rate,
        "bp_source": bp_source_val,
        "delayed_sync": bool(vital.delayed_sync),
        "timestamp": iso_timestamp,
        "status": status_val,
        "risk_score": vital.risk_score,
        "prediction_confidence": vital.prediction_confidence,
        "full_probability_distribution": vital.full_probability_distribution,
        "model_version": vital.model_version,
        "data_origin": vital.data_origin or "device",
    }

