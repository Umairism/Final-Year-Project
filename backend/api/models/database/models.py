"""  
SQLAlchemy database models for HealSense
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class DeviceType(str, enum.Enum):
    """Device type classification"""
    IOT_HARDWARE = "iot_hardware"  # Dedicated IoT device (ESP32, Arduino)
    MOBILE_APP = "mobile_app"      # Phone sensors via mobile app
    WEARABLE = "wearable"          # Smartwatch (Apple Watch, Galaxy Watch)
    MANUAL = "manual"              # Manual entry


class HealthStatus(str, enum.Enum):
    """Health status classification"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Patient(Base):
    """Patient model"""
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    blood_type = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True, index=True)
    phone = Column(String, nullable=True)
    
    # Medical History Context
    diabetes = Column(String, default="unknown")  # "true", "false", "unknown"
    smoking_status = Column(String, default="unknown") # "non_smoker", "former_smoker", "current_smoker", "unknown"
    medications = Column(JSON, default=list)
    past_conditions = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vital_signs = relationship("VitalSigns", back_populates="patient", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="patient", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="patient")


class VitalSigns(Base):
    """Vital signs model"""
    __tablename__ = "vital_signs"
    
    id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=True)
    
    # Vital measurements
    heart_rate = Column(Float, nullable=False)
    spo2 = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    systolic_bp = Column(Float, nullable=True)
    diastolic_bp = Column(Float, nullable=True)
    respiratory_rate = Column(Float, nullable=True)
    
    # Data source tracking (NEW)
    data_source = Column(SQLEnum(DeviceType), default=DeviceType.IOT_HARDWARE)
    sensor_accuracy = Column(Float, nullable=True)  # Confidence score 0-1
    
    # Phone-specific context (NEW)
    activity_context = Column(String, nullable=True)  # "resting", "walking", "exercising"
    location_lat = Column(Float, nullable=True)  # GPS latitude
    location_lng = Column(Float, nullable=True)  # GPS longitude
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(SQLEnum(HealthStatus), default=HealthStatus.NORMAL)
    risk_score = Column(Float, nullable=True)
    
    # AI Metadata (NEW)
    prediction_confidence = Column(Float, nullable=True)
    full_probability_distribution = Column(JSON, nullable=True)
    model_version = Column(String, nullable=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="vital_signs")
    device = relationship("Device", back_populates="vital_readings")


class Alert(Base):
    """Alert model"""
    __tablename__ = "alerts"
    
    id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    
    message = Column(String, nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    vital_type = Column(String, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    dismissed = Column(Boolean, default=False)
    dismissed_at = Column(DateTime, nullable=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="alerts")


class Device(Base):
    """IoT Device model (supports hardware devices and phone sensors)"""
    __tablename__ = "devices"
    
    device_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True, index=True)
    
    # Device type and metadata (NEW)
    device_type = Column(SQLEnum(DeviceType), default=DeviceType.IOT_HARDWARE)
    phone_model = Column(String, nullable=True)  # "Samsung Galaxy S8+"
    phone_os = Column(String, nullable=True)     # "Android 11"
    sensor_capabilities = Column(JSON, nullable=True)  # ["heart_rate", "spo2"]
    
    # Connection status
    connected = Column(Boolean, default=False)
    battery_level = Column(Integer, nullable=True)
    signal_strength = Column(Integer, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="devices")
    vital_readings = relationship("VitalSigns", back_populates="device")


class Emergency(Base):
    """Emergency event model"""
    __tablename__ = "emergencies"
    
    id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False, index=True)
    
    location = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    status = Column(String, default="dispatched")
    
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
