"""
Telemetry ingestion router for hardware IoT devices (ESP32)
"""
from fastapi import APIRouter, Header, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from api.models.database import get_db
from api.models.schemas import TelemetryPayload, TelemetryResponse
from api.services.telemetry_service import telemetry_service

router = APIRouter()


@router.post(
    "",
    response_model=TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Telemetry from IoT Devices",
    description="Direct endpoint for ESP32 hardware devices to push real-time or offline-synced vital signs telemetry."
)
async def ingest_telemetry(
    payload: TelemetryPayload,
    x_device_api_key: Optional[str] = Header(None, alias="X-Device-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Ingest direct HTTP telemetry payload from an authenticated ESP32 device.
    Executes Pydantic schema validation, device authentication, vitals persistence,
    LSTM prediction analysis, decision fusion evaluation, and Gemini LLM reasoning.
    """
    return await telemetry_service.process_telemetry(payload, x_device_api_key, db)
