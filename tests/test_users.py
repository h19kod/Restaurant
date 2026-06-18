"""Tests for the users router (app/routers/users.py)."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole
from tests.conftest import _auth, _make_tenant, _make_user, _uid


@pytest.mark.asyncio
async def test_list_users_admin(client: AsyncClient, admin: User):
    resp = await client.get("/api/v1/users/", headers=_auth(admin))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert any(u["id"] == admin.id for u in resp.json())


@pytest.mark.asyncio
async def test_list_users_non_admin_forbidden(client: AsyncClient, waiter: User):
    resp = await client.get("/api/v1/users/", headers=_auth(waiter))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient, admin: User, waiter: User):
    resp = await client.get(f"/api/v1/users/{waiter.id}", headers=_auth(admin))
    assert resp.status_code == 200
    assert resp.json()["id"] == waiter.id
    assert resp.json()["role"] == "Waiter"


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient, admin: User):
    resp = await client.get("/api/v1/users/99999", headers=_auth(admin))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, admin: User, waiter: User):
    resp = await client.patch(
        f"/api/v1/users/{waiter.id}",
        json={"full_name": "Updated Name", "phone": "+1234567890"},
        headers=_auth(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"
    assert resp.json()["phone"] == "+1234567890"


@pytest.mark.asyncio
async def test_update_user_not_found(client: AsyncClient, admin: User):
    resp = await client.patch(
        "/api/v1/users/99999",
        json={"full_name": "Ghost"},
        headers=_auth(admin),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_user_non_admin_forbidden(client: AsyncClient, waiter: User):
    resp = await client.patch(
        f"/api/v1/users/{waiter.id}",
        json={"full_name": "Hack"},
        headers=_auth(waiter),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, admin: User, db: AsyncSession, tenant):
    victim = await _make_user(db, "victim_" + _uid(), UserRole.Waiter, tenant.id)
    await db.commit()
    resp = await client.delete(f"/api/v1/users/{victim.id}", headers=_auth(admin))
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/v1/users/{victim.id}", headers=_auth(admin))
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient, admin: User):
    resp = await client.delete("/api/v1/users/99999", headers=_auth(admin))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_users(
    client: AsyncClient, admin: User, db: AsyncSession,
):
    """Admin of tenant A should not see users in tenant B."""
    other_tenant = await _make_tenant(db)
    await _make_user(db, "alien_" + _uid(), UserRole.Admin, other_tenant.id)
    await db.commit()

    resp = await client.get("/api/v1/users/", headers=_auth(admin))
    assert resp.status_code == 200
    for u in resp.json():
        assert u["tenant_id"] == admin.tenant_id
