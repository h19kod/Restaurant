"""Tests for the stock manager service (app/services/stock_manager.py)."""
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Category, Inventory, MenuItem, Order, OrderItem,
    OrderStatus, OrderType, RecipeItem, StockUnit, User,
)
from app.services.stock_manager import (
    deduct_stock_for_order,
    get_low_stock_items,
    restock_ingredient,
)
from tests.conftest import _make_category, _make_menu_item, _make_tenant, _uid


async def _make_inventory(db, name, stock, min_level, tenant_id):
    item = Inventory(
        tenant_id=tenant_id,
        ingredient_name=name,
        current_stock=Decimal(stock),
        unit=StockUnit.KG,
        min_alert_level=Decimal(min_level),
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@pytest.mark.asyncio
async def test_get_low_stock_items(db: AsyncSession, tenant):
    low = await _make_inventory(db, "LowItem_" + _uid(), "1.0", "5.0", tenant.id)
    ok = await _make_inventory(db, "OkItem_" + _uid(), "10.0", "5.0", tenant.id)

    result = await get_low_stock_items(db, tenant.id)
    ids = [i.id for i in result]
    assert low.id in ids
    assert ok.id not in ids


@pytest.mark.asyncio
async def test_get_low_stock_items_empty(db: AsyncSession, tenant):
    result = await get_low_stock_items(db, tenant.id)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_restock_ingredient(db: AsyncSession, tenant):
    item = await _make_inventory(db, "RestockTarget_" + _uid(), "5.0", "2.0", tenant.id)
    result = await restock_ingredient(db, item.id, Decimal("3.0"))
    assert result.current_stock == Decimal("8.0")


@pytest.mark.asyncio
async def test_restock_ingredient_not_found(db: AsyncSession):
    with pytest.raises(ValueError, match="not found"):
        await restock_ingredient(db, 99999, Decimal("1.0"))


@pytest.mark.asyncio
async def test_deduct_stock_for_order(db: AsyncSession, tenant):
    cat = await _make_category(db, "DeductCat_" + _uid(), tenant_id=tenant.id)
    item = await _make_menu_item(db, cat.id, "DeductItem_" + _uid(), "10.00", tenant_id=tenant.id)
    flour = await _make_inventory(db, "Flour_" + _uid(), "10.0", "2.0", tenant.id)

    recipe = RecipeItem(
        menu_item_id=item.id,
        ingredient_id=flour.id,
        required_quantity=Decimal("0.5"),
    )
    db.add(recipe)
    await db.flush()

    order = Order(
        tenant_id=tenant.id,
        order_type=OrderType.DineIn,
        status=OrderStatus.Pending,
    )
    db.add(order)
    await db.flush()
    oi = OrderItem(
        order_id=order.id,
        menu_item_id=item.id,
        quantity=3,
        ordered_price=item.price,
    )
    db.add(oi)
    await db.flush()

    low_stock = await deduct_stock_for_order(db, order.id)
    await db.refresh(flour)

    # 10.0 - (0.5 * 3) = 8.5
    assert flour.current_stock == Decimal("8.5")
    assert isinstance(low_stock, list)


@pytest.mark.asyncio
async def test_deduct_stock_triggers_low_stock_alert(db: AsyncSession, tenant):
    cat = await _make_category(db, "AlertCat_" + _uid(), tenant_id=tenant.id)
    item = await _make_menu_item(db, cat.id, "AlertItem_" + _uid(), "5.00", tenant_id=tenant.id)
    ing = await _make_inventory(db, "ScareIng_" + _uid(), "2.0", "5.0", tenant.id)

    recipe = RecipeItem(
        menu_item_id=item.id,
        ingredient_id=ing.id,
        required_quantity=Decimal("1.0"),
    )
    db.add(recipe)
    await db.flush()

    order = Order(
        tenant_id=tenant.id,
        order_type=OrderType.DineIn,
        status=OrderStatus.Pending,
    )
    db.add(order)
    await db.flush()
    oi = OrderItem(
        order_id=order.id,
        menu_item_id=item.id,
        quantity=1,
        ordered_price=item.price,
    )
    db.add(oi)
    await db.flush()

    low_stock = await deduct_stock_for_order(db, order.id)
    assert any(i.id == ing.id for i in low_stock)


@pytest.mark.asyncio
async def test_deduct_stock_no_recipe_mapping(db: AsyncSession, tenant):
    """Items without recipe mappings should be skipped (no error)."""
    cat = await _make_category(db, "NoRecipeCat_" + _uid(), tenant_id=tenant.id)
    item = await _make_menu_item(db, cat.id, "NoRecipe_" + _uid(), "5.00", tenant_id=tenant.id)

    order = Order(
        tenant_id=tenant.id,
        order_type=OrderType.DineIn,
        status=OrderStatus.Pending,
    )
    db.add(order)
    await db.flush()
    oi = OrderItem(
        order_id=order.id,
        menu_item_id=item.id,
        quantity=2,
        ordered_price=item.price,
    )
    db.add(oi)
    await db.flush()

    low_stock = await deduct_stock_for_order(db, order.id)
    assert low_stock == []


@pytest.mark.asyncio
async def test_deduct_stock_clamps_at_zero(db: AsyncSession, tenant):
    """Stock should never go below zero — clamped to 0."""
    cat = await _make_category(db, "ClampCat_" + _uid(), tenant_id=tenant.id)
    item = await _make_menu_item(db, cat.id, "ClampItem_" + _uid(), "5.00", tenant_id=tenant.id)
    ing = await _make_inventory(db, "TinyIng_" + _uid(), "0.1", "1.0", tenant.id)

    recipe = RecipeItem(
        menu_item_id=item.id,
        ingredient_id=ing.id,
        required_quantity=Decimal("1.0"),
    )
    db.add(recipe)
    await db.flush()

    order = Order(
        tenant_id=tenant.id,
        order_type=OrderType.DineIn,
        status=OrderStatus.Pending,
    )
    db.add(order)
    await db.flush()
    oi = OrderItem(
        order_id=order.id,
        menu_item_id=item.id,
        quantity=5,
        ordered_price=item.price,
    )
    db.add(oi)
    await db.flush()

    await deduct_stock_for_order(db, order.id)
    await db.refresh(ing)
    assert ing.current_stock == Decimal("0")
