"""
Tests for the intermittent blood-pressure entry path (Braun ExactFit 1 / cuffs).

Run from backend/:
    python -m pytest tests/test_bp_entry.py -v
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models.database.models import (  # noqa: E402
    Base,
    Device,
    DeviceType,
    Patient,
    VitalSigns,
)
from api.models.schemas import BpEntryRequest, BpSource  # noqa: E402
from api.services.bp_service import bp_service, classify_bp  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _make_patient(db, patient_id="P900"):
    patient = Patient(
        id=patient_id,
        first_name="Test",
        last_name="Patient",
        age=52,
        gender="male",
        diabetes="false",
        smoking_status="non_smoker",
        medications=[],
        past_conditions=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(patient)
    db.commit()
    return patient


def _make_wearable_row(db, patient_id="P900", hours_ago=0.0, bp=None):
    device = db.query(Device).filter(Device.device_id == "DEV_TEST").first()
    if not device:
        device = Device(
            device_id="DEV_TEST",
            patient_id=patient_id,
            device_type=DeviceType.IOT_HARDWARE,
            connected=True,
        )
        db.add(device)
        db.commit()

    row = VitalSigns(
        id=f"V_{datetime.utcnow().timestamp()}",
        patient_id=patient_id,
        device_id=device.device_id,
        heart_rate=78.0,
        spo2=97.0,
        temperature=36.9,
        systolic_bp=bp[0] if bp else None,
        diastolic_bp=bp[1] if bp else None,
        data_source=DeviceType.IOT_HARDWARE,
        timestamp=datetime.utcnow() - timedelta(hours=hours_ago),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Classification (pure) ────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "sys_,dia,expected",
    [
        (115, 75, "normal"),
        (125, 78, "elevated"),
        (132, 84, "stage_1_hypertension"),
        (128, 86, "stage_1_hypertension"),   # diastolic alone drives stage 1
        (150, 95, "stage_2_hypertension"),
        (185, 120, "hypertensive_crisis"),
        (118, 68, "normal"),                 # wide pulse pressure but normal band
        (88, 58, "hypotension"),
        (185, 55, "hypertensive_crisis"),    # crisis beats hypotension
    ],
)
def test_classify_bp(sys_, dia, expected):
    assert classify_bp(sys_, dia) == expected


# ── Validation ───────────────────────────────────────────────────────────────

def test_rejects_systolic_not_above_diastolic():
    with pytest.raises(ValidationError):
        BpEntryRequest(systolic_bp=80, diastolic_bp=85)


def test_rejects_narrow_pulse_pressure():
    with pytest.raises(ValidationError):
        BpEntryRequest(systolic_bp=100, diastolic_bp=95)


def test_accepts_braun_typical_reading():
    entry = BpEntryRequest(systolic_bp=128, diastolic_bp=82, pulse=74)
    assert entry.bp_source == BpSource.MANUAL_ENTRY


# ── Attach path ──────────────────────────────────────────────────────────────

def test_bp_attaches_to_recent_wearable_reading(db):
    _make_patient(db)
    row = _make_wearable_row(db, hours_ago=0.05)  # 3 minutes ago

    result = asyncio.run(
        bp_service.record_bp(
            "P900",
            BpEntryRequest(systolic_bp=128, diastolic_bp=82, pulse=74),
            db,
        )
    )

    assert result.attached is True
    assert result.vital_id == row.id  # same row, not a duplicate
    assert row.systolic_bp == 128
    assert row.diastolic_bp == 82
    assert row.bp_source.value == "manual_entry"
    # The wearable's own vitals are untouched — nothing was invented.
    assert row.heart_rate == 78.0
    assert row.spo2 == 97.0


def test_bp_ignores_wearable_rows_outside_window(db):
    _make_patient(db)
    _make_wearable_row(db, hours_ago=3)  # older than the 60 min default

    result = asyncio.run(
        bp_service.record_bp(
            "P900",
            BpEntryRequest(
                systolic_bp=122,
                diastolic_bp=78,
                heart_rate=70,
                spo2=98,
                temperature=36.8,
            ),
            db,
        )
    )

    assert result.attached is False
    assert len(db.query(VitalSigns).all()) == 2


def test_crisis_creates_alert_and_status(db):
    _make_patient(db)
    _make_wearable_row(db, hours_ago=0.05)

    result = asyncio.run(
        bp_service.record_bp(
            "P900",
            BpEntryRequest(systolic_bp=188, diastolic_bp=124),
            db,
        )
    )

    assert result.category == "hypertensive_crisis"
    assert result.status.value == "critical"
    assert "Hypertensive Crisis" in result.triggered_rules
    assert result.alert_id is not None


def test_crisis_alert_is_deduplicated(db):
    _make_patient(db)
    _make_wearable_row(db, hours_ago=0.05)

    first = asyncio.run(
        bp_service.record_bp("P900", BpEntryRequest(systolic_bp=190, diastolic_bp=121), db)
    )
    second = asyncio.run(
        bp_service.record_bp("P900", BpEntryRequest(systolic_bp=192, diastolic_bp=123), db)
    )

    assert first.alert_id == second.alert_id


# ── Standalone / rejection paths ─────────────────────────────────────────────

def test_no_anchor_without_other_vitals_is_rejected(db):
    from fastapi import HTTPException

    _make_patient(db)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            bp_service.record_bp("P900", BpEntryRequest(systolic_bp=130, diastolic_bp=85), db)
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["error"] == "no_anchor_reading"
    assert set(exc.value.detail["missing_fields"]) == {"heart_rate", "spo2", "temperature"}


def test_unknown_patient_is_404(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            bp_service.record_bp(
                "NOPE",
                BpEntryRequest(
                    systolic_bp=120,
                    diastolic_bp=80,
                    heart_rate=70,
                    spo2=98,
                    temperature=36.8,
                ),
                db,
            )
        )
    assert exc.value.status_code == 404


def test_standalone_reading_uses_cuff_pulse_as_heart_rate(db):
    _make_patient(db)

    result = asyncio.run(
        bp_service.record_bp(
            "P900",
            BpEntryRequest(
                systolic_bp=134,
                diastolic_bp=88,
                pulse=76,
                heart_rate=76,
                spo2=97,
                temperature=36.7,
            ),
            db,
        )
    )

    row = db.query(VitalSigns).filter(VitalSigns.id == result.vital_id).first()
    assert row.heart_rate == 76
    assert row.bp_source.value == "manual_entry"
    assert result.attached is False
