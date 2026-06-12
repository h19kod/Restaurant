"""
Tests — Menu (Categories + Menu Items)
Covers: CRUD, public read access, admin-only write, availability filter
"""
import pytest
from httpx import AsyncClient

from app.models import Category, MenuItem, User
from tests.conftest import _auth


@pytest.mark.asyncio
async def test_list_categories_public(client: AsyncClient, category: Category):
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    assert any(c["name"] == category.name for c in resp.json())


@pytest.mark.asyncio
async def test_create_category_admin(client: AsyncClient, admin: User):
    resp = await client.post(
        "/api/v1/categories",
        json={"name": "Desserts", "description": "Sweet treats"},
        headers=_auth(admin),
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Desserts"


@pytest.mark.asyncio
async def test_create_category_non_admin_forbidden(client: AsyncClient, waiter: User):
    resp = await client.post(
        "/api/v1/categories",
        json={"name": "Should Fail"},
        headers=_auth(waiter),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_category(client: AsyncClient, admin: User, category: Category):
    resp = await client.patch(
        f"/api/v1/categories/{category.id}",
        json={"description": "Updated desc"},
        headers=_auth(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated desc"


@pytest.mark.asyncio
async def test_delete_category_not_found(client: AsyncClient, admin: User):
    resp = await client.delete("/api/v1/categories/99999", headers=_auth(admin))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_menu_items_public(client: AsyncClient, menu_item: MenuItem):
    resp = await client.get("/api/v1/menu-items")
    assert resp.status_code == 200
    assert any(m["name"] == menu_item.name for m in resp.json())


@pytest.mark.asyncio
async def test_list_menu_items_available_only(client: AsyncClient, menu_item: MenuItem):
    resp = await client.get("/api/v1/menu-items?available_only=true")
    assert resp.status_code == 200
    for item in resp.json():
        assert item["is_available"] is True


@pytest.mark.asyncio
async def test_get_menu_item_by_id(client: AsyncClient, menu_item: MenuItem):
    resp = await client.get(f"/api/v1/menu-items/{menu_item.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == menu_item.id


@pytest.mark.asyncio
async def test_get_menu_item_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/menu-items/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_menu_item_admin(client: AsyncClient, admin: User, category: Category):
    resp = await client.post(
        "/api/v1/menu-items",
        json={"category_id": category.id, "name": "Fries", "price": "4.50", "is_available": True},
        headers=_auth(admin),
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Fries"
    assert resp.json()["category"]["id"] == category.id


@pytest.mark.asyncio
async def test_create_menu_item_invalid_category(client: AsyncClient, admin: User):
    resp = await client.post(
        "/api/v1/menu-items",
        json={"category_id": 99999, "name": "Ghost Item", "price": "5.00", "is_available": True},
        headers=_auth(admin),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_menu_item_price(client: AsyncClient, admin: User, menu_item: MenuItem):
    resp = await client.patch(
        f"/api/v1/menu-items/{menu_item.id}",
        json={"price": "15.99"},
        headers=_auth(admin),
    )
    assert resp.status_code == 200
    assert float(resp.json()["price"]) == 15.99
