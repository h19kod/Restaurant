"""
Tests — Authentication & RBAC
Covers: login, register, /me, invalid credentials, role enforcement
"""
import pytest
from httpx import AsyncClient

from app.models import User, UserRole
from tests.conftest import _auth, _make_user


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin: User):
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": admin.username, "password": "pass123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin: User):
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": admin.username, "password": "wrongpass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "ghost", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient, waiter: User):
    resp = await client.get("/api/v1/auth/me", headers=_auth(waiter))
    assert resp.status_code == 200
    assert resp.json()["username"] == waiter.username
    assert resp.json()["role"] == waiter.role.value


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_by_admin(client: AsyncClient, admin: User):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": "new_chef", "password": "secure123", "full_name": "New Chef", "role": "Chef"},
        headers=_auth(admin),
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "new_chef"
    assert resp.json()["role"] == "Chef"


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, admin: User):
    unique_name = "dup_" + admin.username
    r1 = await client.post(
        "/api/v1/auth/register",
        json={"username": unique_name, "password": "pass123", "full_name": "Dup", "role": "Waiter"},
        headers=_auth(admin),
    )
    assert r1.status_code == 201
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": unique_name, "password": "pass123", "full_name": "Dup2", "role": "Waiter"},
        headers=_auth(admin),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_requires_admin(client: AsyncClient, waiter: User):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": "x_user", "password": "pass123", "full_name": "X User", "role": "Chef"},
        headers=_auth(waiter),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_invalid_jwt_rejected(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally.fake.token"},
    )
    assert resp.status_code == 401
