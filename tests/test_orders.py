"""
Tests — Orders
Covers: create, price locking, active list, status workflow engine,
        Cancellation Guard, role-gating, item update, delete
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, MenuItem, Order, OrderStatus, Table, User
from tests.conftest import _auth, _make_category, _make_menu_item, _make_table


async def _seed_order(client: AsyncClient, waiter: User, menu_item: MenuItem, table: Table) -> dict:
    resp = await client.post(
        "/api/v1/orders/",
        json={
            "table_id": table.id,
            "order_type": "Dine-In",
            "items": [{"menu_item_id": menu_item.id, "quantity": 2}],
        },
        headers=_auth(waiter),
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_order_price_lock(
    client: AsyncClient, waiter: User, menu_item: MenuItem, table: Table
):
    order = await _seed_order(client, waiter, menu_item, table)
    item = order["order_items"][0]
    assert float(item["ordered_price"]) == float(menu_item.price)


@pytest.mark.asyncio
async def test_create_order_unavailable_item(
    client: AsyncClient, admin: User, waiter: User,
    db: AsyncSession, category: Category,
):
    unavailable = await _make_menu_item(db, category.id, "Unavailable Dish", "8.00", tenant_id=category.tenant_id)
    unavailable.is_available = False
    await db.flush()

    tbl = await _make_table(db, tenant_id=category.tenant_id)
    resp = await client.post(
        "/api/v1/orders/",
        json={
            "table_id": tbl.id,
            "order_type": "Dine-In",
            "items": [{"menu_item_id": unavailable.id, "quantity": 1}],
        },
        headers=_auth(waiter),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_order_invalid_table(client: AsyncClient, waiter: User, menu_item: MenuItem):
    resp = await client.post(
        "/api/v1/orders/",
        json={
            "table_id": 99999,
            "order_type": "Dine-In",
            "items": [{"menu_item_id": menu_item.id, "quantity": 1}],
        },
        headers=_auth(waiter),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_order_requires_waiter(client: AsyncClient, cashier: User, menu_item: MenuItem, table: Table):
    resp = await client.post(
        "/api/v1/orders/",
        json={
            "table_id": table.id,
            "order_type": "Dine-In",
            "items": [{"menu_item_id": menu_item.id, "quantity": 1}],
        },
        headers=_auth(cashier),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_active_orders(client: AsyncClient, waiter: User, menu_item: MenuItem, table: Table):
    await _seed_order(client, waiter, menu_item, table)
    resp = await client.get("/api/v1/orders/active", headers=_auth(waiter))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_order_by_id(client: AsyncClient, waiter: User, menu_item: MenuItem, table: Table):
    order = await _seed_order(client, waiter, menu_item, table)
    resp = await client.get(f"/api/v1/orders/{order['id']}", headers=_auth(waiter))
    assert resp.status_code == 200
    assert resp.json()["id"] == order["id"]


@pytest.mark.asyncio
async def test_get_order_not_found(client: AsyncClient, waiter: User):
    resp = await client.get("/api/v1/orders/99999", headers=_auth(waiter))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Status Workflow Engine
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow_pending_to_preparing_by_chef(
    client: AsyncClient, waiter: User, chef: User, menu_item: MenuItem, table: Table
):
    order = await _seed_order(client, waiter, menu_item, table)
    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "Preparing"},
        headers=_auth(chef),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Preparing"


@pytest.mark.asyncio
async def test_workflow_preparing_to_ready_by_chef(
    client: AsyncClient, waiter: User, chef: User, menu_item: MenuItem, table: Table
):
    order = await _seed_order(client, waiter, menu_item, table)
    await client.patch(f"/api/v1/orders/{order['id']}/status", json={"status": "Preparing"}, headers=_auth(chef))
    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "Ready"},
        headers=_auth(chef),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Ready"


@pytest.mark.asyncio
async def test_workflow_ready_to_delivered_by_waiter(
    client: AsyncClient, waiter: User, chef: User, menu_item: MenuItem, table: Table
):
    order = await _seed_order(client, waiter, menu_item, table)
    await client.patch(f"/api/v1/orders/{order['id']}/status", json={"status": "Preparing"}, headers=_auth(chef))
    await client.patch(f"/api/v1/orders/{order['id']}/status", json={"status": "Ready"}, headers=_auth(chef))
    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "Delivered"},
        headers=_auth(waiter),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Delivered"


@pytest.mark.asyncio
async def test_workflow_invalid_transition_rejected(
    client: AsyncClient, waiter: User, chef: User, menu_item: MenuItem, table: Table
):
    order = await _seed_order(client, waiter, menu_item, table)
    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "Delivered"},
        headers=_auth(chef),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_workflow_wrong_role_rejected(
    client: AsyncClient, waiter: User, menu_item: MenuItem, table: Table
):
    """Waiter cannot push Pending → Preparing (Chef only)"""
    order = await _seed_order(client, waiter, menu_item, table)
    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "Preparing"},
        headers=_auth(waiter),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Cancellation Guard Rule
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_via_patch_returns_400(
    client: AsyncClient, waiter: User, chef: User, menu_item: MenuItem, table: Table
):
    """PATCH /status to Cancelled must be blocked — use DELETE instead."""
    order = await _seed_order(client, waiter, menu_item, table)
    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "Cancelled"},
        headers=_auth(chef),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_cancel_pending_via_delete(
    client: AsyncClient, waiter: User, menu_item: MenuItem, table: Table
):
    order = await _seed_order(client, waiter, menu_item, table)
    resp = await client.delete(f"/api/v1/orders/{order['id']}", headers=_auth(waiter))
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_cannot_cancel_preparing_via_delete(
    client: AsyncClient, waiter: User, chef: User, menu_item: MenuItem, table: Table
):
    order = await _seed_order(client, waiter, menu_item, table)
    await client.patch(f"/api/v1/orders/{order['id']}/status", json={"status": "Preparing"}, headers=_auth(chef))
    resp = await client.delete(f"/api/v1/orders/{order['id']}", headers=_auth(waiter))
    assert resp.status_code == 400
