"""WebSocket endpoint for real-time live data streaming."""

import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Live Stream"])


class LiveConnectionManager:
    """Manages active browser WebSocket connections for live HR streaming."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast live measurement to all connected clients."""
        payload = json.dumps(message)
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.add(connection)

        for dead in dead_connections:
            self.active_connections.discard(dead)


live_manager = LiveConnectionManager()


@router.websocket("/ws/live")
async def live_websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time dashboard updates."""
    await live_manager.connect(websocket)
    try:
        while True:
            # Keep connection open; receive ping or client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        live_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        live_manager.disconnect(websocket)
