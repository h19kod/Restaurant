"""
Tests — Billing (Invoice preview, settle, coupon CRUD)
Covers: preview calculation, settle creates invoice, duplicate invoice rejected,
        coupon percentage discount, coupon fixed discount, expired coupon
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Category, DiscountCoupon, DiscountType, MenuItem,
    Order, OrderItem, OrderStatus, Table, User,
)
from tests.conftest import _auth, _make_category, _make_menu_item, _make_table


async def _create_delivered_order(
    db: AsyncSession, waiter: User, menu_item: MenuItem, table: Table, client: AsyncClient, chef: User
) -> int:
    """Helper: create a Pending order and advance it to Delivered state."""
    order = Order(table_id=table.id, waiter_id=waiter.id, order_type="Dine-In")
    db.add(order)
    await db.flush()

    oi = OrderItem(
        order_id=order.id,
        menu_item_id=menu_item.id,
        quantity=3,
        ordered_price=menu_item.price,
    )
    db.add(oi)
    await db.flush()

    order.status = OrderStatus.Preparing
    await db.flush()
    order.status = OrderStatus.Ready
    await db.flush()
    order.status = OrderStatus.Delivered
    await db.flush()
    await db.commit()

    return order.id


@pytest.mark.asyncio
async def test_invoice_preview_calculates_correctly(
    client: AsyncClient, cashier: User, waiter: User, chef: User,
    db: AsyncSession, category: Category, table: Table,
):
    item = await _make_menu_item(db, category.id, "PrevItem", "20.00")
    order_id = await _create_delivered_order(db, waiter, item, table, client, chef)

    resp = await client.post(
        f"/api/v1/billing/invoices/preview/{order_id}",
        headers=_auth(cashier),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert float(body["subtotal"]) == pytest.approx(60.0)
    assert float(body["tax_amount"]) > 0
    assert float(body["total_amount"]) == pytest.approx(float(body["subtotal"]) + float(body["tax_amount"]))


@pytest.mark.asyncio
async def test_invoice_settle_creates_invoice(
    client: AsyncClient, cashier: User, waiter: User, chef: User,
    db: AsyncSession, category: Category, table: Table,
):
    item = await _make_menu_item(db, category.id, "SettleItem", "10.00")
    order_id = await _create_delivered_order(db, waiter, item, table, client, chef)

    resp = await client.post(
        f"/api/v1/billing/invoices/settle/{order_id}",
        json={"payment_method": "Cash"},
        headers=_auth(cashier),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["order_id"] == order_id
    assert body["payment_method"] == "Cash"
    assert float(body["subtotal"]) == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_invoice_duplicate_rejected(
    client: AsyncClient, cashier: User, waiter: User, chef: User,
    db: AsyncSession, category: Category, table: Table,
):
    item = await _make_menu_item(db, category.id, "DupItem", "5.00")
    order_id = await _create_delivered_order(db, waiter, item, table, client, chef)

    await client.post(
        f"/api/v1/billing/invoices/settle/{order_id}",
        json={"payment_method": "Cash"},
        headers=_auth(cashier),
    )
    resp = await client.post(
        f"/api/v1/billing/invoices/settle/{order_id}",
        json={"payment_method": "Card"},
        headers=_auth(cashier),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_coupon_percentage_discount(
    client: AsyncClient, cashier: User, waiter: User, chef: User, admin: User,
    db: AsyncSession, category: Category, table: Table,
):
    coupon = DiscountCoupon(
        code="SAVE10PCT",
        discount_type=DiscountType.Percentage,
        value=Decimal("10"),
        is_active=True,
    )
    db.add(coupon)
    await db.flush()

    item = await _make_menu_item(db, category.id, "PctItem", "100.00")
    order_id = await _create_delivered_order(db, waiter, item, table, client, chef)

    resp = await client.post(
        f"/api/v1/billing/invoices/preview/{order_id}?coupon_code=SAVE10PCT",
        headers=_auth(cashier),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert float(body["discount_amount"]) == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_coupon_fixed_discount(
    client: AsyncClient, cashier: User, waiter: User, chef: User,
    db: AsyncSession, category: Category, table: Table,
):
    coupon = DiscountCoupon(
        code="SAVE5FLAT",
        discount_type=DiscountType.FixedAmount,
        value=Decimal("5"),
        is_active=True,
    )
    db.add(coupon)
    await db.flush()

    item = await _make_menu_item(db, category.id, "FixedItem", "50.00")
    order_id = await _create_delivered_order(db, waiter, item, table, client, chef)

    resp = await client.post(
        f"/api/v1/billing/invoices/preview/{order_id}?coupon_code=SAVE5FLAT",
        headers=_auth(cashier),
    )
    assert resp.status_code == 200
    assert float(resp.json()["discount_amount"]) == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_expired_coupon_rejected(
    client: AsyncClient, cashier: User, waiter: User, chef: User,
    db: AsyncSession, category: Category, table: Table,
):
    coupon = DiscountCoupon(
        code="EXPIRED",
        discount_type=DiscountType.Percentage,
        value=Decimal("20"),
        is_active=True,
        expiry_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(coupon)
    await db.flush()

    item = await _make_menu_item(db, category.id, "ExpItem", "30.00")
    order_id = await _create_delivered_order(db, waiter, item, table, client, chef)

    resp = await client.post(
        f"/api/v1/billing/invoices/preview/{order_id}?coupon_code=EXPIRED",
        headers=_auth(cashier),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_coupon_admin_only(client: AsyncClient, admin: User, waiter: User):
    resp = await client.post(
        "/api/v1/billing/coupons",
        json={"code": "ADMINONLY", "discount_type": "Percentage", "value": 5},
        headers=_auth(admin),
    )
    assert resp.status_code == 201

    resp2 = await client.post(
        "/api/v1/billing/coupons",
        json={"code": "NOWAY", "discount_type": "Percentage", "value": 5},
        headers=_auth(waiter),
    )
    assert resp2.status_code == 403
