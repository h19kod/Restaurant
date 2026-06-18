"""Tests for the WebSocket notification service (app/services/notification.py)."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.notification import ConnectionManager, notify_kitchen, notify_waiter


def _fake_ws(*, fail=False):
    ws = AsyncMock()
    if fail:
        ws.send_text.side_effect = RuntimeError("closed")
    return ws


@pytest.mark.asyncio
async def test_connect_and_broadcast_kitchen():
    mgr = ConnectionManager()
    ws = _fake_ws()
    await mgr.connect_kitchen(ws)
    ws.accept.assert_awaited_once()
    assert ws in mgr._kitchen

    await mgr.broadcast_kitchen({"event": "new_order", "order_id": 1})
    ws.send_text.assert_awaited_once()
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload == {"event": "new_order", "order_id": 1}


@pytest.mark.asyncio
async def test_disconnect_kitchen():
    mgr = ConnectionManager()
    ws = _fake_ws()
    await mgr.connect_kitchen(ws)
    mgr.disconnect_kitchen(ws)
    assert ws not in mgr._kitchen


@pytest.mark.asyncio
async def test_disconnect_kitchen_not_present():
    """disconnect_kitchen on unknown ws should not raise."""
    mgr = ConnectionManager()
    mgr.disconnect_kitchen(_fake_ws())


@pytest.mark.asyncio
async def test_broadcast_kitchen_removes_dead_connections():
    mgr = ConnectionManager()
    good_ws = _fake_ws()
    dead_ws = _fake_ws(fail=True)
    await mgr.connect_kitchen(good_ws)
    await mgr.connect_kitchen(dead_ws)

    await mgr.broadcast_kitchen({"event": "test"})

    assert good_ws in mgr._kitchen
    assert dead_ws not in mgr._kitchen


@pytest.mark.asyncio
async def test_connect_and_broadcast_waiter():
    mgr = ConnectionManager()
    ws = _fake_ws()
    await mgr.connect_waiter(ws, waiter_id=7)
    ws.accept.assert_awaited_once()
    assert ws in mgr._waiters[7]

    await mgr.broadcast_waiter(7, {"event": "order_ready", "order_id": 42})
    ws.send_text.assert_awaited_once()
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload == {"event": "order_ready", "order_id": 42}


@pytest.mark.asyncio
async def test_disconnect_waiter():
    mgr = ConnectionManager()
    ws = _fake_ws()
    await mgr.connect_waiter(ws, waiter_id=3)
    mgr.disconnect_waiter(ws, waiter_id=3)
    assert ws not in mgr._waiters.get(3, [])


@pytest.mark.asyncio
async def test_disconnect_waiter_not_present():
    mgr = ConnectionManager()
    mgr.disconnect_waiter(_fake_ws(), waiter_id=99)


@pytest.mark.asyncio
async def test_broadcast_waiter_removes_dead():
    mgr = ConnectionManager()
    good_ws = _fake_ws()
    dead_ws = _fake_ws(fail=True)
    await mgr.connect_waiter(good_ws, waiter_id=5)
    await mgr.connect_waiter(dead_ws, waiter_id=5)

    await mgr.broadcast_waiter(5, {"event": "order_ready"})

    assert good_ws in mgr._waiters[5]
    assert dead_ws not in mgr._waiters[5]


@pytest.mark.asyncio
async def test_broadcast_waiter_no_connections():
    """broadcast_waiter should be a no-op for unknown waiter_id."""
    mgr = ConnectionManager()
    await mgr.broadcast_waiter(999, {"event": "order_ready"})


@pytest.mark.asyncio
async def test_notify_kitchen_delegates(monkeypatch):
    mock_broadcast = AsyncMock()
    from app.services import notification
    monkeypatch.setattr(notification.manager, "broadcast_kitchen", mock_broadcast)
    await notify_kitchen(42)
    mock_broadcast.assert_awaited_once_with({"event": "new_order", "order_id": 42})


@pytest.mark.asyncio
async def test_notify_waiter_delegates(monkeypatch):
    mock_broadcast = AsyncMock()
    from app.services import notification
    monkeypatch.setattr(notification.manager, "broadcast_waiter", mock_broadcast)
    await notify_waiter(10, waiter_id=3)
    mock_broadcast.assert_awaited_once_with(3, {"event": "order_ready", "order_id": 10})


@pytest.mark.asyncio
async def test_notify_waiter_none_id(monkeypatch):
    """notify_waiter with waiter_id=None should be a no-op."""
    mock_broadcast = AsyncMock()
    from app.services import notification
    monkeypatch.setattr(notification.manager, "broadcast_waiter", mock_broadcast)
    await notify_waiter(10, waiter_id=None)
    mock_broadcast.assert_not_awaited()
