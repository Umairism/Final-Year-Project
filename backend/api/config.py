"""
HealSense Backend API - Configuration Management
Handles environment variables and application settings
"""
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # App Configuration
    PROJECT_NAME: str = "HealSense"
    ENV: str = Field(default="development", validation_alias=AliasChoices("ENV", "FLASK_ENV"))
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    
    # Security
    SECRET_KEY: str = "b104b3038eb465125547dd2080b770baedfe37dc78d18822d20ad14c46895814"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: str = "*"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/healsense"

    # Email / SMTP
    MAIL_SERVER: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_USE_TLS: bool = True
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_DEFAULT_SENDER: Optional[str] = None
    
    # Cache/Queue
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    
    # MQTT (IoT Communication)
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_TOPIC: str = "healsense/vitals"
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    
    # Firebase (Optional)
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None

    # AI Engines (Optional)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # ML Model Paths
    MODEL_VERSION: str = "v1.0.1"
    LSTM_MODEL_PATH: str = f"../data/models/{MODEL_VERSION}/lstm_best.h5"
    SCALER_PATH: str = f"../data/models/{MODEL_VERSION}/scaler.pkl"
    ENCODER_PATH: str = f"../data/models/{MODEL_VERSION}/label_encoder.pkl"
    
    # Fusion Engine Hyperparameters
    DETERMINISTIC_WEIGHT: float = 0.6
    ML_WEIGHT: float = 0.4
    
    # Alert Thresholds
    HEART_RATE_MIN: int = 50
    HEART_RATE_MAX: int = 120
    SPO2_MIN: int = 92
    TEMP_MAX: float = 38.0
    SYSTOLIC_BP_MIN: int = 90
    SYSTOLIC_BP_MAX: int = 140
    
    # WhatsApp Business API (Optional)
    WHATSAPP_API_URL: Optional[str] = None
    WHATSAPP_API_TOKEN: Optional[str] = None
    WHATSAPP_TEMPLATE_ALERT: str = "health_alert"
    
    # Twilio SMS (Optional)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid recreating settings on every call.
    """
    return Settings()
