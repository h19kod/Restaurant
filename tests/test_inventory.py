"""
Tests — Inventory & Recipe Mappings
Covers: CRUD inventory, restock, low-stock filter, recipe CRUD
"""
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Inventory, MenuItem, RecipeItem, StockUnit, User
from tests.conftest import _auth, _make_menu_item


async def _make_ingredient(db: AsyncSession, name: str, stock: str = "10.000", min_level: str = "2.000", tenant_id: int = None) -> Inventory:
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
async def test_list_inventory_admin_only(client: AsyncClient, admin: User, waiter: User, db: AsyncSession):
    await _make_ingredient(db, "InventoryListTest", tenant_id=admin.tenant_id)
    resp = await client.get("/api/v1/inventory/", headers=_auth(admin))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp2 = await client.get("/api/v1/inventory/", headers=_auth(waiter))
    assert resp2.status_code == 403


@pytest.mark.asyncio
async def test_create_inventory_item(client: AsyncClient, admin: User):
    resp = await client.post(
        "/api/v1/inventory/",
        json={"ingredient_name": "Tomato", "current_stock": 20.0, "unit": "KG", "min_alert_level": 3.0},
        headers=_auth(admin),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["ingredient_name"] == "Tomato"
    assert body["is_low_stock"] is False


@pytest.mark.asyncio
async def test_low_stock_flag(client: AsyncClient, admin: User, db: AsyncSession):
    item = await _make_ingredient(db, "LowStockIngredient", stock="1.000", min_level="5.000", tenant_id=admin.tenant_id)
    resp = await client.get(f"/api/v1/inventory/{item.id}", headers=_auth(admin))
    assert resp.status_code == 200
    assert resp.json()["is_low_stock"] is True


@pytest.mark.asyncio
async def test_low_stock_filter(client: AsyncClient, admin: User, db: AsyncSession):
    await _make_ingredient(db, "FilterLow", stock="0.500", min_level="5.000", tenant_id=admin.tenant_id)
    resp = await client.get("/api/v1/inventory/?low_stock_only=true", headers=_auth(admin))
    assert resp.status_code == 200
    for item in resp.json():
        assert item["is_low_stock"] is True


@pytest.mark.asyncio
async def test_restock_increases_stock(client: AsyncClient, admin: User, db: AsyncSession):
    item = await _make_ingredient(db, "RestockIngredient", stock="5.000", tenant_id=admin.tenant_id)
    resp = await client.patch(
        f"/api/v1/inventory/{item.id}/restock",
        json={"quantity_to_add": 10.0},
        headers=_auth(admin),
    )
    assert resp.status_code == 200
    assert float(resp.json()["current_stock"]) == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_restock_not_found(client: AsyncClient, admin: User):
    resp = await client.patch(
        "/api/v1/inventory/99999/restock",
        json={"quantity_to_add": 5.0},
        headers=_auth(admin),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_recipe_mapping(
    client: AsyncClient, admin: User,
    db: AsyncSession, menu_item: MenuItem,
):
    ingredient = await _make_ingredient(db, "RecipeIngredient", tenant_id=admin.tenant_id)
    resp = await client.post(
        "/api/v1/inventory/recipes",
        json={
            "menu_item_id": menu_item.id,
            "ingredient_id": ingredient.id,
            "required_quantity": 0.15,
        },
        headers=_auth(admin),
    )
    assert resp.status_code == 201
    assert float(resp.json()["required_quantity"]) == pytest.approx(0.15)


@pytest.mark.asyncio
async def test_duplicate_recipe_mapping_rejected(
    client: AsyncClient, admin: User,
    db: AsyncSession, menu_item: MenuItem,
):
    ingredient = await _make_ingredient(db, "DupRecipeIngredient", tenant_id=admin.tenant_id)
    payload = {
        "menu_item_id": menu_item.id,
        "ingredient_id": ingredient.id,
        "required_quantity": 0.1,
    }
    await client.post("/api/v1/inventory/recipes", json=payload, headers=_auth(admin))
    resp = await client.post("/api/v1/inventory/recipes", json=payload, headers=_auth(admin))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_recipes_filter_by_menu_item(
    client: AsyncClient, admin: User,
    db: AsyncSession, category: Category, menu_item: MenuItem,
):
    other_item = await _make_menu_item(db, category.id, "OtherItem", "7.00", tenant_id=category.tenant_id)
    ing1 = await _make_ingredient(db, "FilterIng1", tenant_id=admin.tenant_id)
    ing2 = await _make_ingredient(db, "FilterIng2", tenant_id=admin.tenant_id)

    await client.post(
        "/api/v1/inventory/recipes",
        json={"menu_item_id": menu_item.id, "ingredient_id": ing1.id, "required_quantity": 0.1},
        headers=_auth(admin),
    )
    await client.post(
        "/api/v1/inventory/recipes",
        json={"menu_item_id": other_item.id, "ingredient_id": ing2.id, "required_quantity": 0.2},
        headers=_auth(admin),
    )

    resp = await client.get(
        f"/api/v1/inventory/recipes?menu_item_id={menu_item.id}",
        headers=_auth(admin),
    )
    assert resp.status_code == 200
    assert all(r["menu_item_id"] == menu_item.id for r in resp.json())
