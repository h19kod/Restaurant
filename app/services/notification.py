"""
WebSocket Notification Service  —  Layer 4: Real-Time Worker Layer
==================================================================
Manages all live, persistent WebSocket connections between the server
and client devices (kitchen screens, waiter tablets).

Architecture role:
  This component operates outside the standard HTTP request-response cycle.
  Once a client connects, the channel stays open indefinitely, allowing the
  server to push data to the client at any moment without the client polling.

ConnectionManager internals:
  _kitchen : list[WebSocket]
      Broadcast pool — a new order event is pushed to EVERY connected
      kitchen device simultaneously.
  _waiters : dict[waiter_id, list[WebSocket]]
      Targeted pool — an order_ready event is pushed ONLY to the specific
      waiter who owns that order ticket (identified by waiter_id).

Phase B — Kitchen dispatch (triggered from orders.py after DB commit):
  notify_kitchen(order_id)
    └─ broadcast_kitchen({event: "new_order", order_id})
         └─ Ticket appears on chef's screen in milliseconds, no page refresh

Phase C — Waiter notification (triggered when order status → Ready):
  notify_waiter(order_id, waiter_id)
    └─ broadcast_waiter(waiter_id, {event: "order_ready", order_id})
         └─ Private push ONLY to the responsible waiter's device

Dead connection cleanup:
  Both broadcast methods silently remove stale sockets from their pools
  when a send fails, preventing memory leaks from disconnected clients.
"""
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSockets"])


class ConnectionManager:
    """Maintains active WebSocket connections grouped by role/identity."""

    def __init__(self):
        self._kitchen: list[WebSocket] = []
        self._waiters: dict[int, list[WebSocket]] = {}

    async def connect_kitchen(self, ws: WebSocket) -> None:
        await ws.accept()
        self._kitchen.append(ws)

    def disconnect_kitchen(self, ws: WebSocket) -> None:
        if ws in self._kitchen:
            self._kitchen.remove(ws)

    async def connect_waiter(self, ws: WebSocket, waiter_id: int) -> None:
        await ws.accept()
        self._waiters.setdefault(waiter_id, []).append(ws)

    def disconnect_waiter(self, ws: WebSocket, waiter_id: int) -> None:
        connections = self._waiters.get(waiter_id, [])
        if ws in connections:
            connections.remove(ws)

    async def broadcast_kitchen(self, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._kitchen):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_kitchen(ws)

    async def broadcast_waiter(self, waiter_id: int, message: dict) -> None:
        connections = list(self._waiters.get(waiter_id, []))
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_waiter(ws, waiter_id)


manager = ConnectionManager()


async def notify_kitchen(order_id: int) -> None:
    """Fire a new_order event to all connected kitchen displays."""
    await manager.broadcast_kitchen({"event": "new_order", "order_id": order_id})


async def notify_waiter(order_id: int, waiter_id: Optional[int]) -> None:
    """Fire an order_ready event to the specific waiter's connected devices."""
    if waiter_id is not None:
        await manager.broadcast_waiter(
            waiter_id, {"event": "order_ready", "order_id": order_id}
        )


# ---------------------------------------------------------------------------
# WebSocket endpoints
# ---------------------------------------------------------------------------

@router.websocket("/ws/kitchen")
async def kitchen_ws(websocket: WebSocket):
    await manager.connect_kitchen(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_kitchen(websocket)


@router.websocket("/ws/waiter/{waiter_id}")
async def waiter_ws(websocket: WebSocket, waiter_id: int):
    await manager.connect_waiter(websocket, waiter_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_waiter(websocket, waiter_id)
