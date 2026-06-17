"""Realtime websocket connection manager and broadcast helpers."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, DefaultDict, Dict, Optional, Set

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class RealtimeManager:
    """Track websocket clients and broadcast live events."""

    def __init__(self) -> None:
        self._global_connections: Set[WebSocket] = set()
        self._patient_connections: DefaultDict[str, Set[WebSocket]] = defaultdict(set)
        self._device_connections: DefaultDict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        *,
        patient_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> None:
        await websocket.accept()
        async with self._lock:
            self._global_connections.add(websocket)
            if patient_id:
                self._patient_connections[patient_id].add(websocket)
            if device_id:
                self._device_connections[device_id].add(websocket)

    async def disconnect(
        self,
        websocket: WebSocket,
        *,
        patient_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> None:
        async with self._lock:
            self._global_connections.discard(websocket)
            if patient_id and patient_id in self._patient_connections:
                self._patient_connections[patient_id].discard(websocket)
                if not self._patient_connections[patient_id]:
                    self._patient_connections.pop(patient_id, None)
            if device_id and device_id in self._device_connections:
                self._device_connections[device_id].discard(websocket)
                if not self._device_connections[device_id]:
                    self._device_connections.pop(device_id, None)

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        message = jsonable_encoder(
            {
                "event_type": event_type,
                "timestamp": datetime.utcnow(),
                "payload": payload,
            }
        )

        async with self._lock:
            connections = list(self._global_connections)

        await self._broadcast_to(connections, message)

    async def broadcast_patient(self, patient_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        message = jsonable_encoder(
            {
                "event_type": event_type,
                "timestamp": datetime.utcnow(),
                "patient_id": patient_id,
                "payload": payload,
            }
        )

        async with self._lock:
            connections = list(self._patient_connections.get(patient_id, set()))

        await self._broadcast_to(connections, message)
        await self.broadcast(event_type, {"patient_id": patient_id, **payload})

    async def broadcast_device(self, device_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        message = jsonable_encoder(
            {
                "event_type": event_type,
                "timestamp": datetime.utcnow(),
                "device_id": device_id,
                "payload": payload,
            }
        )

        async with self._lock:
            connections = list(self._device_connections.get(device_id, set()))

        await self._broadcast_to(connections, message)
        await self.broadcast(event_type, {"device_id": device_id, **payload})

    async def _broadcast_to(self, connections: list[WebSocket], message: Dict[str, Any]) -> None:
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(websocket)


realtime_manager = RealtimeManager()