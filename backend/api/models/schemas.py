"""
Pydantic schemas for API request/response models
"""
from pydantic import BaseModel, Field, model_validator, field_validator, BeforeValidator, StringConstraints, EmailStr
from typing import Optional, List, Literal, Annotated
from datetime import datetime
from enum import Enum


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(..., min_length=2, max_length=120)
    age: int = Field(..., ge=1, le=150)
    blood_type: Optional[str] = None
    gender: str = "Unspecified"

    @field_validator("blood_type")
    @classmethod
    def validate_blood_type(cls, value):
        if value is not None and value.upper() not in {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}:
            raise ValueError("Invalid blood type")
        return value.upper() if value else value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class HealthStatus(str, Enum):
    """Health status classification"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class BpSource(str, Enum):
    """Blood pressure measurement acquisition source"""
    MANUAL_ENTRY = "manual_entry"
    BLE_CUFF = "ble_cuff"
    HARDWARE_UART = "hardware_uart"
    NONE = "none"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Vital Signs Models
class VitalSignsBase(BaseModel):
    """Base vital signs model"""
    heart_rate: float = Field(..., ge=0, le=300)
    spo2: float = Field(..., ge=0, le=100)
    temperature: float = Field(..., ge=30, le=45)
    systolic_bp: Optional[float] = Field(None, ge=0, le=300)
    diastolic_bp: Optional[float] = Field(None, ge=0, le=200)
    respiratory_rate: Optional[float] = Field(None, ge=0, le=60)
    bp_source: BpSource = Field(BpSource.NONE, description="Acquisition source mechanism for BP reading")
    delayed_sync: bool = Field(False, description="Flag indicating historical sync from offline ESP32 NVS buffer")


class VitalSignsCreate(VitalSignsBase):
    """Model for creating vital signs"""
    patient_id: str
    device_id: Optional[str] = None


class VitalSigns(VitalSignsBase):
    """Vital signs response model"""
    id: str
    patient_id: str
    device_id: Optional[str] = None
    timestamp: datetime
    status: HealthStatus
    risk_score: Optional[float] = None
    prediction_confidence: Optional[float] = None
    full_probability_distribution: Optional[dict] = None
    model_version: Optional[str] = None
    data_origin: str = "device"
    
    class Config:
        from_attributes = True


# Patient Models
Diabetes = Literal['true', 'false', 'unknown']
SmokingStatus = Literal['non_smoker', 'former_smoker', 'current_smoker', 'unknown']


def normalize_clinical_items(value):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError('Expected a list of text items')
    return [item.strip() for item in value if item.strip()]


ClinicalItems = Annotated[
    list[Annotated[str, StringConstraints(max_length=100)]],
    BeforeValidator(normalize_clinical_items), Field(max_length=20),
]


class EmergencyContact(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    phone: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=32)]
    relation: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    type: Literal['doctor', 'family', 'other']


class PatientBase(BaseModel):
    """Base patient model"""
    first_name: str
    last_name: str
    age: int = Field(..., ge=0, le=150)
    gender: str
    blood_type: Optional[str] = None
    diabetes: Diabetes = 'unknown'
    smoking_status: SmokingStatus = 'unknown'
    medications: ClinicalItems = Field(default_factory=list)
    past_conditions: ClinicalItems = Field(default_factory=list)
    emergency_contacts: list[EmergencyContact] = Field(default_factory=list, max_length=5)


class PatientCreate(PatientBase):
    """Model for creating patient"""
    email: Optional[str] = None
    phone: Optional[str] = None


class PatientUpdate(BaseModel):
    """Model for updating patient"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    diabetes: Optional[Diabetes] = None
    smoking_status: Optional[SmokingStatus] = None
    medications: Optional[ClinicalItems] = None
    past_conditions: Optional[ClinicalItems] = None
    emergency_contacts: Optional[list[EmergencyContact]] = Field(None, max_length=5)

    @field_validator('age', 'diabetes', 'smoking_status', 'medications', 'past_conditions', 'emergency_contacts')
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError('Omit this field instead of supplying null')
        return value


class Patient(PatientBase):
    """Patient response model"""
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PatientProfile(Patient):
    """Extended patient profile with latest vitals"""
    latest_vitals: Optional[VitalSigns] = None
    device_connected: bool = False
    last_sync: Optional[datetime] = None


class CanonicalClinicalFeatureSchema(BaseModel):
    """Single contract schema for ML and Deterministic pipelines"""
    # Core Vitals (Critical) - Ranges based on extreme physiological limits
    heart_rate: float = Field(..., ge=0, le=300, description="Beats per minute (bpm)")
    spo2: float = Field(..., ge=0, le=100, description="Blood oxygen percentage (%)")
    temperature: float = Field(..., ge=30.0, le=45.0, description="Body temperature (°C)")
    systolic_bp: Optional[float] = Field(None, ge=0, le=300, description="Optional Systolic blood pressure (mmHg)")
    diastolic_bp: Optional[float] = Field(None, ge=0, le=200, description="Optional Diastolic blood pressure (mmHg)")
    bp_source: BpSource = Field(BpSource.NONE, description="Source mechanism for blood pressure reading")
    delayed_sync: bool = Field(False, description="Flag for historical offline syncs")

    # Medical History (Categoricals with Explicit Missingness)
    age: Optional[int] = Field(None, ge=0, le=150, description="Patient age in years")
    age_missing: bool = Field(False, description="Explicit flag for missing age")
    
    diabetes: str = Field("unknown", description="true, false, or unknown")
    smoking_status: str = Field("unknown", description="non_smoker, former_smoker, current_smoker, unknown")
    
    # Contextual History
    medications: List[str] = Field(default_factory=list)
    past_conditions: List[str] = Field(default_factory=list)

    # Context Metadata
    timestamp: datetime
    source: str = Field(..., description="iot, mobile, manual, or dataset")


# Alert Models
class AlertBase(BaseModel):
    """Base alert model"""
    message: str
    severity: AlertSeverity
    vital_type: Optional[str] = None


class Alert(AlertBase):
    """Alert response model"""
    id: str
    patient_id: str
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    dismissed: bool = False
    
    class Config:
        from_attributes = True


# Device Models
class DeviceStatus(BaseModel):
    """Device status model"""
    device_id: str
    patient_id: Optional[str] = None
    connected: bool
    battery_level: Optional[int] = Field(None, ge=0, le=100)
    signal_strength: Optional[int] = Field(None, ge=0, le=100)
    last_heartbeat: Optional[datetime] = None
    presence_status: Optional[str] = None
    is_online: Optional[bool] = None
    last_seen_at: Optional[datetime] = None
    last_seen_seconds_ago: Optional[int] = None


# Emergency Models
class EmergencyRequest(BaseModel):
    """Emergency trigger request"""
    patient_id: str
    location: Optional[str] = None
    notes: Optional[str] = None


class EmergencyResponse(BaseModel):
    """Emergency response"""
    emergency_id: str
    patient_id: str
    triggered_at: datetime
    status: str
    message: str


# API Response Wrappers
class TelemetryPayload(BaseModel):
    """Payload schema for direct ESP32 telemetry ingestion"""
    device_id: str = Field(..., description="Unique hardware identifier of the ESP32 IoT gateway")
    patient_id: str = Field(..., description="Unique ID of the linked patient")
    heart_rate: float = Field(..., ge=0, le=300, description="Heart rate reading in bpm")
    spo2: float = Field(..., ge=0, le=100, description="SpO2 percentage reading")
    temperature: float = Field(..., ge=30, le=45, description="Body temperature in °C")
    systolic_bp: Optional[float] = Field(None, ge=0, le=300, description="Optional Systolic BP in mmHg")
    diastolic_bp: Optional[float] = Field(None, ge=0, le=200, description="Optional Diastolic BP in mmHg")
    bp_source: Optional[BpSource] = Field(BpSource.NONE, description="Blood pressure measurement acquisition origin")
    delayed_sync: bool = Field(False, description="Flag indicating offline sync upload from NVS buffer")
    timestamp: Optional[datetime] = Field(None, description="Hardware reading timestamp")
    data_origin: Optional[str] = Field(None, pattern="^(device|simulated)$")


class TelemetryResponse(BaseModel):
    """Response payload returned upon successful telemetry ingestion and evaluation"""
    success: bool = True
    message: str
    vital_id: str
    patient_id: str
    device_id: str
    status: HealthStatus
    fused_decision: dict
    explanation: Optional[str] = None


# Blood Pressure Entry Models (intermittent cuff measurements)
class BpEntryRequest(BaseModel):
    """
    A single blood-pressure measurement taken with an *intermittent* cuff
    (Braun ExactFit 1, a BLE cuff, or clinician manual entry).

    Blood pressure is measured episodically, while the wearable streams
    HR / SpO2 / temperature continuously. A BP reading is therefore attached to
    the most recent wearable row inside ``attach_window_minutes`` instead of
    creating a new row that would have to invent the other three vitals.
    """
    systolic_bp: float = Field(..., ge=60, le=260, description="Systolic pressure (mmHg)")
    diastolic_bp: float = Field(..., ge=30, le=200, description="Diastolic pressure (mmHg)")
    pulse: Optional[float] = Field(None, ge=30, le=220,
                                   description="Pulse rate shown by the cuff (bpm)")
    measured_at: Optional[datetime] = Field(None,
                                            description="When the measurement was taken (defaults to now)")
    attach_window_minutes: int = Field(60, ge=1, le=720,
                                       description="How far back to look for a wearable reading to attach to")
    bp_source: BpSource = Field(BpSource.MANUAL_ENTRY,
                                description="How the BP was obtained")
    device_id: Optional[str] = Field(None,
                                     description="Optional device id for standalone entries")
    note: Optional[str] = Field(None,
                                description="Free text, e.g. 'left arm, seated, 5 min rest'")

    # Standalone fallback — only used when no wearable reading exists in the window.
    heart_rate: Optional[float] = Field(None, ge=0, le=300)
    spo2: Optional[float] = Field(None, ge=0, le=100)
    temperature: Optional[float] = Field(None, ge=30, le=45)

    @model_validator(mode="after")
    def _validate_pulse_pressure(self):
        if self.systolic_bp - self.diastolic_bp < 10:
            raise ValueError("systolic_bp must be at least 10 mmHg higher than diastolic_bp")
        return self


class BpEntryResponse(BaseModel):
    """Result of recording a BP measurement and re-running the risk pipeline."""
    success: bool = True
    attached: bool = Field(..., description="True when the BP was attached to an existing wearable reading")
    vital_id: str
    patient_id: str
    systolic_bp: float
    diastolic_bp: float
    pulse: Optional[float] = None
    bp_source: BpSource
    category: str = Field(..., description="AHA/ACC blood-pressure category")
    triggered_rules: List[str] = Field(default_factory=list)
    status: HealthStatus
    fused_decision: Optional[dict] = None
    alert_id: Optional[str] = None
    message: str


class ApiResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[dict] = None


class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: List[dict]
    total: int
    page: int
    page_size: int
    has_more: bool
