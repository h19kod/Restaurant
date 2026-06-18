"""Tests for the tenants router (app/routers/tenants.py)."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SubscriptionPlan, SubscriptionStatus, Tenant, User
from tests.conftest import _auth, _make_tenant, _uid


@pytest.mark.asyncio
async def test_register_tenant(client: AsyncClient):
    subdomain = "pizza-" + _uid()
    resp = await client.post(
        "/api/v1/tenants/register",
        json={
            "restaurant_name": "Pizza Palace",
            "subdomain": subdomain,
            "admin_username": "admin_" + _uid(),
            "admin_password": "securepass123",
            "admin_full_name": "Test Admin",
            "admin_email": "admin@example.com",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["tenant"]["subdomain"] == subdomain
    assert body["tenant"]["plan"] == "Free"
    assert body["access_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_subdomain(client: AsyncClient, db: AsyncSession):
    tenant = await _make_tenant(db, subdomain="dup-" + _uid())
    await db.commit()

    resp = await client.post(
        "/api/v1/tenants/register",
        json={
            "restaurant_name": "Another Place",
            "subdomain": tenant.subdomain,
            "admin_username": "admin_" + _uid(),
            "admin_password": "securepass123",
            "admin_full_name": "Dup Admin",
            "admin_email": "dup@example.com",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password_rejected(client: AsyncClient):
    resp = await client.post(
        "/api/v1/tenants/register",
        json={
            "restaurant_name": "Fail",
            "subdomain": "short-" + _uid(),
            "admin_username": "admin_" + _uid(),
            "admin_password": "1234",
            "admin_full_name": "Short Pass",
            "admin_email": "short@example.com",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_tenant_me(client: AsyncClient, admin: User):
    resp = await client.get("/api/v1/tenants/me", headers=_auth(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == admin.tenant_id
    assert "name" in body


@pytest.mark.asyncio
async def test_get_tenant_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/tenants/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_billing_status(client: AsyncClient, admin: User):
    resp = await client.get("/api/v1/tenants/billing/status", headers=_auth(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert "plan" in body
    assert "max_users" in body
    assert "max_tables" in body
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_subscribe_no_stripe_key(client: AsyncClient, admin: User):
    resp = await client.post(
        "/api/v1/tenants/billing/subscribe",
        json={"plan": "Pro"},
        headers=_auth(admin),
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_billing_portal_no_stripe(client: AsyncClient, admin: User):
    resp = await client.post(
        "/api/v1/tenants/billing/portal",
        headers=_auth(admin),
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_stripe_webhook_unhandled_event(client: AsyncClient):
    resp = await client.post(
        "/api/v1/tenants/webhook/stripe",
        content=b'{"type": "charge.succeeded", "data": {"object": {}}}',
        headers={"content-type": "application/json"},
    )
    assert resp.status_code in (200, 400)


@pytest.mark.asyncio
async def test_stripe_webhook_subscription_event(
    client: AsyncClient, db: AsyncSession,
):
    tenant = await _make_tenant(db)
    tenant.stripe_customer_id = "cus_test_" + _uid()
    await db.commit()

    event_payload = (
        b'{"type": "invoice.payment_failed",'
        b'"data": {"object": {"customer": "' + tenant.stripe_customer_id.encode() + b'"}}}'
    )
    resp = await client.post(
        "/api/v1/tenants/webhook/stripe",
        content=event_payload,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code in (200, 400)
