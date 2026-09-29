# Phase 1: Database Alignment Report & Proposal

**Project Title**: HealSense Cloud-Native Migration  
**Subsystem**: Database Schema & Pydantic Data Models  
**Status**: PROPOSAL FOR USER REVIEW (NO CODE MODIFIED YET)  
**Date**: August 2, 2026  

---

> [!IMPORTANT]
> **Phase 1 Objective**:  
> Align the database schema and Pydantic schemas with the approved Cloud-Native Architecture. Introduce explicit tracking for Blood Pressure sources (`bp_source`), offline NVS retry flags (`delayed_sync`), and device API key authentication (`api_key_hash`). Verify that missing Blood Pressure fields are handled as optional/nullable without forced data imputation.

---

## 1. Analysis of Current Database & Schema State

### Current Implementation Overview
* **SQLAlchemy ORM Models**: Located in [models.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/backend/api/models/database/models.py). The `VitalSigns` model stores `heart_rate`, `spo2`, `temperature`, `systolic_bp`, `diastolic_bp`, `timestamp`, `status`, `risk_score`, and `prediction_confidence`.
* **Pydantic Schemas**: Located in [schemas.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/backend/api/models/schemas.py). `VitalSignsBase` and `CanonicalClinicalFeatureSchema` represent vital sign payloads.
* **Alembic Migration Infrastructure**: Active migration setup in `backend/alembic`.

### Identified Gaps
1. **Missing `bp_source`**: Neither the database `vital_signs` table nor Pydantic schemas record the acquisition mechanism for Blood Pressure.
2. **Missing `delayed_sync`**: Neither table nor schema records whether telemetry was received live or uploaded from local ESP32 NVS memory after a Wi-Fi outage.
3. **Missing `api_key_hash`**: The `devices` table does not store hash credentials required to verify direct hardware HTTP headers (`X-Device-API-Key`).
4. **Data Imputation Bug**: `CanonicalClinicalFeatureSchema` marks BP as required floats (`systolic_bp: float`, `diastolic_bp: float`), forcing service layers to impute fake defaults (`120.0/80.0 mmHg`) when BP is absent.

---

## 2. Proposed Changes

### Change 1: Add `BpSource` Enum and Update `VitalSigns` SQLAlchemy Model
In `backend/api/models/database/models.py`:
```python
import enum

class BpSource(str, enum.Enum):
    MANUAL_ENTRY = "manual_entry"
    BLE_CUFF = "ble_cuff"
    HARDWARE_UART = "hardware_uart"
    NONE = "none"

# Update VitalSigns class:
class VitalSigns(Base):
    __tablename__ = "vital_signs"
    # ... existing fields ...
    bp_source = Column(Enum(BpSource), default=BpSource.NONE, nullable=False)
    delayed_sync = Column(Boolean, default=False, nullable=False)
```

### Change 2: Update `Device` SQLAlchemy Model
In `backend/api/models/database/models.py`:
```python
class Device(Base):
    __tablename__ = "devices"
    # ... existing fields ...
    api_key_hash = Column(String(128), nullable=True)
```

### Change 3: Update Pydantic Schemas
In `backend/api/models/schemas.py`:
```python
class BpSource(str, Enum):
    MANUAL_ENTRY = "manual_entry"
    BLE_CUFF = "ble_cuff"
    HARDWARE_UART = "hardware_uart"
    NONE = "none"

class VitalSignsBase(BaseModel):
    heart_rate: float = Field(..., ge=0, le=300)
    spo2: float = Field(..., ge=0, le=100)
    temperature: float = Field(..., ge=30, le=45)
    systolic_bp: Optional[float] = Field(None, ge=0, le=300)
    diastolic_bp: Optional[float] = Field(None, ge=0, le=200)
    bp_source: BpSource = Field(BpSource.NONE, description="Source mechanism for blood pressure reading")
    delayed_sync: bool = Field(False, description="Flag indicating historical upload from offline NVS buffer")

class CanonicalClinicalFeatureSchema(BaseModel):
    heart_rate: float = Field(..., ge=0, le=300)
    spo2: float = Field(..., ge=0, le=100)
    temperature: float = Field(..., ge=30.0, le=45.0)
    systolic_bp: Optional[float] = Field(None, ge=0, le=300, description="Optional Systolic BP")
    diastolic_bp: Optional[float] = Field(None, ge=0, le=200, description="Optional Diastolic BP")
    bp_source: BpSource = Field(BpSource.NONE)
    delayed_sync: bool = Field(False)
    # ... medical history & timestamp fields ...
```

---

## 3. Migration Plan (Alembic Script)

A new Alembic migration script will be generated under `backend/alembic/versions/`:

```python
"""add_bp_source_delayed_sync_and_api_key_hash

Revision ID: c8f92a104b91
Revises: previous_revision
Create Date: 2026-08-02

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create enum type for BpSource
    bp_source_enum = sa.Enum('manual_entry', 'ble_cuff', 'hardware_uart', 'none', name='bpsource')
    bp_source_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('vital_signs', sa.Column('bp_source', bp_source_enum, server_default='none', nullable=False))
    op.add_column('vital_signs', sa.Column('delayed_sync', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('devices', sa.Column('api_key_hash', sa.String(length=128), nullable=True))

def downgrade():
    op.drop_column('devices', 'api_key_hash')
    op.drop_column('vital_signs', 'delayed_sync')
    op.drop_column('vital_signs', 'bp_source')
    
    bp_source_enum = sa.Enum(name='bpsource')
    bp_source_enum.drop(op.get_bind(), checkfirst=True)
```

---

## 4. Risk Assessment & Mitigations

* **Risk 1: Database Migration Failure on Existing PostgreSQL Data**
  * *Impact*: Low. Default values (`server_default='none'` and `server_default='false'`) ensure existing rows populate automatically without null constraint violations.
* **Risk 2: Breaking Existing API Consumers**
  * *Impact*: None. Pydantic fields use default values (`BpSource.NONE`, `delayed_sync=False`), maintaining backwards compatibility for existing frontend clients.

---

## 5. File Impact List

1. [models.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/backend/api/models/database/models.py) (Add `BpSource` Enum, update `VitalSigns` and `Device` models).
2. [schemas.py](file:///e:/Study%20Material/FYP/FYP-Project/healsense/backend/api/models/schemas.py) (Update `VitalSignsBase` and `CanonicalClinicalFeatureSchema` to make BP optional and add source/sync flags).
3. `backend/alembic/versions/<new_hash>_add_bp_source_and_delayed_sync.py` (New migration script).

---

## 6. Validation Checklist

- [ ] Verify Alembic upgrade executes cleanly against PostgreSQL.
- [ ] Verify Alembic downgrade executes cleanly and rolls back schema additions.
- [ ] Test Pydantic parsing of telemetry JSON payloads without Blood Pressure (`systolic_bp: null`).
- [ ] Verify `bp_source` and `delayed_sync` default parameters in test suite.

---

**Status**: Phase 0 and Phase 1 Reports are complete and awaiting user review. No codebase refactoring has been performed.
