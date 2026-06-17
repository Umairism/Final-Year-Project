"""
Pydantic schemas for API request/response models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    """Health status classification"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


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


class VitalSignsCreate(VitalSignsBase):
    """Model for creating vital signs"""
    patient_id: str
    device_id: Optional[str] = None


class VitalSigns(VitalSignsBase):
    """Vital signs response model"""
    id: str
    patient_id: str
    timestamp: datetime
    status: HealthStatus
    risk_score: Optional[float] = None
    prediction_confidence: Optional[float] = None
    full_probability_distribution: Optional[dict] = None
    model_version: Optional[str] = None
    
    class Config:
        from_attributes = True


# Patient Models
class PatientBase(BaseModel):
    """Base patient model"""
    first_name: str
    last_name: str
    age: int = Field(..., ge=0, le=150)
    gender: str
    blood_type: Optional[str] = None
    diabetes: str = Field("unknown", description="true, false, or unknown")
    smoking_status: str = Field("unknown", description="non_smoker, former_smoker, current_smoker, or unknown")
    medications: List[str] = Field(default_factory=list)
    past_conditions: List[str] = Field(default_factory=list)


class PatientCreate(PatientBase):
    """Model for creating patient"""
    email: Optional[str] = None
    phone: Optional[str] = None


class PatientUpdate(BaseModel):
    """Model for updating patient"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    diabetes: Optional[str] = None
    smoking_status: Optional[str] = None
    medications: Optional[List[str]] = None
    past_conditions: Optional[List[str]] = None


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
    systolic_bp: float = Field(..., ge=0, le=300, description="Systolic blood pressure (mmHg)")
    diastolic_bp: float = Field(..., ge=0, le=200, description="Diastolic blood pressure (mmHg)")

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
