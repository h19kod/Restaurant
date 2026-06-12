"""
Stock manager service.

Provides async helpers for inventory deduction and low-stock detection,
called directly from routers or dispatched via Celery tasks.
"""
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inventory, OrderItem, RecipeItem

logger = logging.getLogger(__name__)


async def get_low_stock_items(db: AsyncSession, tenant_id: int) -> list[Inventory]:
    """Return all inventory rows where current_stock < min_alert_level for a given tenant."""
    result = await db.execute(select(Inventory).where(Inventory.tenant_id == tenant_id))
    all_items = result.scalars().all()
    return [item for item in all_items if item.current_stock < item.min_alert_level]


async def restock_ingredient(
    db: AsyncSession,
    ingredient_id: int,
    quantity_to_add: Decimal,
) -> Inventory:
    """
    Add stock to an inventory row.
    Returns the updated Inventory object.
    Raises ValueError if ingredient not found.
    """
    item = await db.get(Inventory, ingredient_id)
    if not item:
        raise ValueError(f"Inventory item id={ingredient_id} not found")
    item.current_stock = item.current_stock + quantity_to_add
    await db.flush()
    await db.refresh(item)
    logger.info(
        "[STOCK] Restocked '%s': +%.3f %s → %.3f",
        item.ingredient_name,
        float(quantity_to_add),
        item.unit.value,
        float(item.current_stock),
    )
    return item


async def deduct_stock_for_order(db: AsyncSession, order_id: int) -> list[Inventory]:
    """
    Deducts ingredient stock for all items in an order using RecipeItem mappings.
    Returns a list of Inventory rows that have fallen below min_alert_level.

    Raises no errors for missing recipe mappings — logs a warning and skips instead,
    so partial recipes don't block invoice settlement.
    """
    order_items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    order_items = order_items_result.scalars().all()

    deductions: dict[int, Decimal] = {}

    for order_item in order_items:
        recipe_result = await db.execute(
            select(RecipeItem).where(RecipeItem.menu_item_id == order_item.menu_item_id)
        )
        recipe_rows = recipe_result.scalars().all()

        if not recipe_rows:
            logger.warning(
                "[STOCK] No recipe mapping for MenuItem #%d — skipping deduction.",
                order_item.menu_item_id,
            )
            continue

        for recipe in recipe_rows:
            amount = recipe.required_quantity * Decimal(str(order_item.quantity))
            deductions[recipe.ingredient_id] = (
                deductions.get(recipe.ingredient_id, Decimal("0")) + amount
            )

    low_stock: list[Inventory] = []

    for ingredient_id, total_deducted in deductions.items():
        ingredient = await db.get(Inventory, ingredient_id)
        if not ingredient:
            logger.error("[STOCK] Ingredient #%d not found — skipping.", ingredient_id)
            continue

        before = ingredient.current_stock
        ingredient.current_stock = max(Decimal("0"), ingredient.current_stock - total_deducted)
        await db.flush()

        logger.info(
            "[STOCK] '%s': %.3f → %.3f %s (deducted %.3f for Order #%d)",
            ingredient.ingredient_name,
            float(before), float(ingredient.current_stock),
            ingredient.unit.value, float(total_deducted), order_id,
        )

        if ingredient.current_stock < ingredient.min_alert_level:
            logger.warning(
                "[STOCK ALERT] '%s' below minimum: %.3f / %.3f %s",
                ingredient.ingredient_name,
                float(ingredient.current_stock),
                float(ingredient.min_alert_level),
                ingredient.unit.value,
            )
            low_stock.append(ingredient)

    return low_stock
