"""Realtime websocket endpoints for live updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.services.realtime import realtime_manager

router = APIRouter()


@router.websocket("/ws/live")
async def live_stream(websocket: WebSocket):
    """Global realtime stream for dashboards."""
    await realtime_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket)


@router.websocket("/ws/patients/{patient_id}")
async def patient_stream(websocket: WebSocket, patient_id: str):
    """Realtime stream for a single patient."""
    await realtime_manager.connect(websocket, patient_id=patient_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket, patient_id=patient_id)


@router.websocket("/ws/devices/{device_id}")
async def device_stream(websocket: WebSocket, device_id: str):
    """Realtime stream for a single device."""
    await realtime_manager.connect(websocket, device_id=device_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket, device_id=device_id)