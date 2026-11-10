"""
WebSocket Connection Manager
Manages real-time connections partitioned by organization for live alerts and notifications.
"""
import json
import logging
from typing import Any, Dict, List
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # org_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, org_id: str):
        await websocket.accept()
        if org_id not in self.active_connections:
            self.active_connections[org_id] = []
        self.active_connections[org_id].append(websocket)
        logger.info("WebSocket connected for org=%s (total active: %d)", org_id, len(self.active_connections[org_id]))

    def disconnect(self, websocket: WebSocket, org_id: str):
        if org_id in self.active_connections:
            if websocket in self.active_connections[org_id]:
                self.active_connections[org_id].remove(websocket)
            if not self.active_connections[org_id]:
                del self.active_connections[org_id]
        logger.info("WebSocket disconnected for org=%s", org_id)

    async def broadcast_to_org(self, org_id: str | UUID, message: Dict[str, Any]):
        """Sends a JSON message to all clients connected within an organization."""
        key = str(org_id)
        if key not in self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections[key]:
            try:
                await connection.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.warning("Failed to send WebSocket message to client in org=%s: %s", key, e)
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead, key)

    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcasts a message to all connected clients across all organizations."""
        for org_id in list(self.active_connections.keys()):
            await self.broadcast_to_org(org_id, message)


ws_manager = ConnectionManager()

