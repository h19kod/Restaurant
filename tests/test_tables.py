"""
Tests — Tables & Reservations
Covers: CRUD tables, QR token generation, public QR menu, reservation lifecycle
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, MenuItem, Table, User
from tests.conftest import _auth, _make_menu_item


@pytest.mark.asyncio
async def test_list_tables(client: AsyncClient, waiter: User, table: Table):
    resp = await client.get("/api/v1/tables/", headers=_auth(waiter))
    assert resp.status_code == 200
    assert any(t["id"] == table.id for t in resp.json())


@pytest.mark.asyncio
async def test_create_table_admin(client: AsyncClient, admin: User):
    resp = await client.post(
        "/api/v1/tables/",
        json={"capacity": 6},
        headers=_auth(admin),
    )
    assert resp.status_code == 201
    assert resp.json()["capacity"] == 6
    assert "qr_code_token" in resp.json()


@pytest.mark.asyncio
async def test_create_table_non_admin_forbidden(client: AsyncClient, waiter: User):
    resp = await client.post("/api/v1/tables/", json={"capacity": 2}, headers=_auth(waiter))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_public_qr_menu(
    client: AsyncClient, table: Table,
    db: AsyncSession, category: Category, menu_item: MenuItem,
):
    """GET /tables/{qr_token}/menu must return menu without auth."""
    resp = await client.get(f"/api/v1/tables/{table.qr_code_token}/menu")
    assert resp.status_code == 200
    body = resp.json()
    assert "table" in body
    assert "menu" in body


@pytest.mark.asyncio
async def test_public_qr_menu_invalid_token(client: AsyncClient):
    resp = await client.get("/api/v1/tables/invalid-token-xyz/menu")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_qr_token(client: AsyncClient, admin: User, table: Table):
    resp = await client.post(
        "/api/v1/tables/generate-token",
        json={"table_id": table.id},
        headers=_auth(admin),
    )
    assert resp.status_code == 200
    assert "qr_code_token" in resp.json()


@pytest.mark.asyncio
async def test_create_reservation(client: AsyncClient, waiter: User, table: Table):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = await client.post(
        "/api/v1/tables/reservations",
        json={
            "table_id": table.id,
            "customer_name": "John Doe",
            "customer_phone": "0500000000",
            "reservation_datetime": future,
        },
        headers=_auth(waiter),
    )
    assert resp.status_code == 201
    assert resp.json()["customer_name"] == "John Doe"
    assert resp.json()["status"] == "Pending"


@pytest.mark.asyncio
async def test_list_reservations(client: AsyncClient, waiter: User, table: Table):
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    await client.post(
        "/api/v1/tables/reservations",
        json={
            "table_id": table.id,
            "customer_name": "Jane",
            "customer_phone": "0511111111",
            "reservation_datetime": future,
        },
        headers=_auth(waiter),
    )
    resp = await client.get("/api/v1/tables/reservations", headers=_auth(waiter))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_reservation(client: AsyncClient, waiter: User, admin: User, table: Table):
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    create_resp = await client.post(
        "/api/v1/tables/reservations",
        json={
            "table_id": table.id,
            "customer_name": "Alice",
            "customer_phone": "0522222222",
            "reservation_datetime": future,
        },
        headers=_auth(waiter),
    )
    res_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/tables/reservations/{res_id}",
        json={"status": "Confirmed"},
        headers=_auth(waiter),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Confirmed"


@pytest.mark.asyncio
async def test_delete_reservation_admin_only(
    client: AsyncClient, waiter: User, admin: User, table: Table
):
    future = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    create_resp = await client.post(
        "/api/v1/tables/reservations",
        json={
            "table_id": table.id,
            "customer_name": "Bob",
            "customer_phone": "0533333333",
            "reservation_datetime": future,
        },
        headers=_auth(waiter),
    )
    res_id = create_resp.json()["id"]

    resp_waiter = await client.delete(f"/api/v1/tables/reservations/{res_id}", headers=_auth(waiter))
    assert resp_waiter.status_code == 403

    resp_admin = await client.delete(f"/api/v1/tables/reservations/{res_id}", headers=_auth(admin))
    assert resp_admin.status_code == 204
