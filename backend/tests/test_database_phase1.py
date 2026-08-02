import pytest
from datetime import datetime
from api.models.schemas import (
    VitalSignsBase,
    VitalSignsCreate,
    VitalSigns,
    CanonicalClinicalFeatureSchema,
    BpSource,
    HealthStatus
)
from api.models.database.models import VitalSigns as DBVitalSigns, BpSource as DBBpSource, Device as DBDevice

def test_pydantic_vitals_without_bp():
    """Case 1: Telemetry without BP (systolic_bp: null, diastolic_bp: null)"""
    vitals_data = {
        "heart_rate": 75.0,
        "spo2": 98.0,
        "temperature": 36.7,
        "systolic_bp": None,
        "diastolic_bp": None
    }
    schema = VitalSignsBase(**vitals_data)
    assert schema.heart_rate == 75.0
    assert schema.spo2 == 98.0
    assert schema.temperature == 36.7
    assert schema.systolic_bp is None
    assert schema.diastolic_bp is None
    assert schema.bp_source == BpSource.NONE
    assert schema.delayed_sync is False


def test_pydantic_vitals_delayed_sync():
    """Case 2: Delayed sync metadata tracking"""
    vitals_data = {
        "heart_rate": 82.0,
        "spo2": 96.0,
        "temperature": 37.1,
        "delayed_sync": True,
        "bp_source": "hardware_uart"
    }
    schema = VitalSignsBase(**vitals_data)
    assert schema.delayed_sync is True
    assert schema.bp_source == BpSource.HARDWARE_UART


def test_pydantic_bp_sources():
    """Case 3: Validation of allowed BP sources"""
    allowed_sources = ["manual_entry", "ble_cuff", "hardware_uart", "none"]
    for src in allowed_sources:
        vitals = VitalSignsBase(
            heart_rate=70,
            spo2=99,
            temperature=36.6,
            bp_source=src
        )
        assert vitals.bp_source == src

    with pytest.raises(ValueError):
        VitalSignsBase(
            heart_rate=70,
            spo2=99,
            temperature=36.6,
            bp_source="invalid_source"
        )


def test_canonical_schema_nullable_bp():
    """Verify CanonicalClinicalFeatureSchema allows nullable BP without defaults"""
    canonical = CanonicalClinicalFeatureSchema(
        heart_rate=80.0,
        spo2=97.0,
        temperature=36.8,
        systolic_bp=None,
        diastolic_bp=None,
        bp_source=BpSource.NONE,
        delayed_sync=False,
        timestamp=datetime.utcnow(),
        source="iot"
    )
    assert canonical.systolic_bp is None
    assert canonical.diastolic_bp is None
    assert canonical.bp_source == BpSource.NONE


def test_db_model_defaults():
    """Verify SQLAlchemy DB Model field mapping"""
    db_vitals = DBVitalSigns(
        id="v_123",
        patient_id="p_123",
        heart_rate=75.0,
        spo2=98.0,
        temperature=36.5,
        bp_source=DBBpSource.NONE,
        delayed_sync=False
    )
    assert db_vitals.bp_source == DBBpSource.NONE
    assert db_vitals.delayed_sync is False

    db_device = DBDevice(
        device_id="d_123",
        api_key_hash="hash_123456"
    )
    assert db_device.api_key_hash == "hash_123456"
