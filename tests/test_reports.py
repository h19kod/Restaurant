"""
Tests — Reports & Analytics
Covers: sales summary (daily/monthly/custom), daily breakdown, trending items, RBAC
"""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Invoice, Order, OrderItem, OrderType, PaymentMethod, User
from tests.conftest import _auth, _make_menu_item, _make_table


async def _seed_paid_invoice(db: AsyncSession, menu_item, table) -> None:
    from app.models import OrderStatus, User
    order = Order(table_id=table.id, order_type=OrderType.DineIn, status=OrderStatus.Delivered)
    db.add(order)
    await db.flush()
    oi = OrderItem(
        order_id=order.id,
        menu_item_id=menu_item.id,
        quantity=1,
        ordered_price=menu_item.price,
    )
    db.add(oi)
    await db.flush()
    inv = Invoice(
        order_id=order.id,
        subtotal=menu_item.price,
        tax_amount=Decimal("1.50"),
        discount_amount=Decimal("0"),
        total_amount=menu_item.price + Decimal("1.50"),
        payment_method=PaymentMethod.Cash,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(inv)
    await db.flush()


@pytest.mark.asyncio
async def test_sales_summary_daily(
    client: AsyncClient, admin: User,
    db: AsyncSession, category, menu_item, table,
):
    await _seed_paid_invoice(db, menu_item, table)
    resp = await client.get("/api/v1/reports/sales/summary?range=daily", headers=_auth(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert "total_revenue" in body
    assert "total_invoices" in body
    assert body["total_invoices"] >= 1


@pytest.mark.asyncio
async def test_sales_summary_monthly(client: AsyncClient, admin: User):
    resp = await client.get("/api/v1/reports/sales/summary?range=monthly", headers=_auth(admin))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sales_summary_custom_range(client: AsyncClient, admin: User):
    resp = await client.get(
        "/api/v1/reports/sales/summary?start=2020-01-01T00:00:00Z&end=2030-01-01T00:00:00Z",
        headers=_auth(admin),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sales_summary_bad_range(client: AsyncClient, admin: User):
    resp = await client.get("/api/v1/reports/sales/summary", headers=_auth(admin))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sales_summary_requires_admin(client: AsyncClient, waiter: User):
    resp = await client.get("/api/v1/reports/sales/summary?range=daily", headers=_auth(waiter))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_daily_breakdown(client: AsyncClient, admin: User):
    resp = await client.get(
        "/api/v1/reports/sales/daily?start=2020-01-01T00:00:00Z&end=2030-01-01T00:00:00Z",
        headers=_auth(admin),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_trending_items(
    client: AsyncClient, admin: User,
    db: AsyncSession, category, menu_item, table,
):
    await _seed_paid_invoice(db, menu_item, table)
    resp = await client.get("/api/v1/reports/items/trending?limit=5", headers=_auth(admin))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    if resp.json():
        assert "total_quantity_ordered" in resp.json()[0]
        assert "total_revenue" in resp.json()[0]
