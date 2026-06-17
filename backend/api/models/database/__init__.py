"""Database models package"""
from api.models.database.models import (
    Base,
    Patient,
    VitalSigns,
    Alert,
    Device,
    Emergency,
    HealthStatus,
    AlertSeverity,
    DeviceType  # NEW: Phone sensor support
)
from api.models.database.database import (
    engine,
    SessionLocal,
    get_db,
    get_db_context,
    create_tables,
    init_db
)

__all__ = [
    "Base",
    "Patient",
    "VitalSigns",
    "Alert",
    "Device",
    "Emergency",
    "HealthStatus",
    "AlertSeverity",
    "DeviceType",  # NEW
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_context",
    "create_tables",
    "init_db",
]
