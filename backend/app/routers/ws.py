"""
WebSocket Router
Provides real-time event streaming for authenticated clients.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_token
from app.core.websocket import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time security events (alerts, logs, notifications).
    Authenticates via JWT token query parameter.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token required")
        return

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    org_id = payload.get("org_id")
    user_id = payload.get("sub")
    if not org_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="No org scope")
        return

    await ws_manager.connect(websocket, org_id)
    try:
        # Send initial connection acknowledgment
        await websocket.send_json({
            "type": "connection_ack",
            "message": "Connected to CyberSentinel Real-time Stream",
            "org_id": org_id,
            "user_id": user_id,
        })

        while True:
            # Keep connection open and receive any client heartbeats
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, org_id)
    except Exception as e:
        logger.error("WebSocket error for org=%s: %s", org_id, e)
        ws_manager.disconnect(websocket, org_id)

