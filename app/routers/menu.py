from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import RequireAdmin, get_current_tenant, get_current_user
from app.database import get_db
from app.models import Category, MenuItem, Tenant, User
from app.schemas import (
    CategoryCreate, CategoryOut, CategoryUpdate,
    MenuItemCreate, MenuItemOut, MenuItemUpdate,
)
from app.services.crud_helpers import apply_partial_update, create_and_refresh, get_or_404

router = APIRouter(tags=["Menu"])


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(Category).where(Category.tenant_id == tenant.id))
    return result.scalars().all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    category = Category(tenant_id=tenant.id, **payload.model_dump())
    await create_and_refresh(db, category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    category = await get_or_404(
        db, Category, Category.id == category_id, Category.tenant_id == tenant.id,
        detail="Category not found",
    )
    await apply_partial_update(db, category, payload)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    category = await get_or_404(
        db, Category, Category.id == category_id, Category.tenant_id == tenant.id,
        detail="Category not found",
    )
    await db.delete(category)


# ---------------------------------------------------------------------------
# Menu Items
# ---------------------------------------------------------------------------

@router.get("/menu-items", response_model=list[MenuItemOut])
async def list_menu_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    available_only: bool = False,
):
    query = select(MenuItem).options(selectinload(MenuItem.category)).where(MenuItem.tenant_id == tenant.id)
    if available_only:
        query = query.where(MenuItem.is_available.is_(True))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/menu-items/{item_id}", response_model=MenuItemOut)
async def get_menu_item(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    return await get_or_404(
        db, MenuItem, MenuItem.id == item_id, MenuItem.tenant_id == tenant.id,
        detail="Menu item not found",
        options=[selectinload(MenuItem.category)],
    )


@router.post("/menu-items", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    payload: MenuItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    await get_or_404(
        db, Category, Category.id == payload.category_id, Category.tenant_id == tenant.id,
        detail="Category not found",
    )
    item = MenuItem(tenant_id=tenant.id, **payload.model_dump())
    db.add(item)
    await db.flush()
    result = await db.execute(
        select(MenuItem).options(selectinload(MenuItem.category)).where(MenuItem.id == item.id)
    )
    return result.scalar_one()


@router.patch("/menu-items/{item_id}", response_model=MenuItemOut)
async def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    item = await get_or_404(
        db, MenuItem, MenuItem.id == item_id, MenuItem.tenant_id == tenant.id,
        detail="Menu item not found",
        options=[selectinload(MenuItem.category)],
    )
    await apply_partial_update(db, item, payload)
    result = await db.execute(
        select(MenuItem).options(selectinload(MenuItem.category)).where(MenuItem.id == item_id)
    )
    return result.scalar_one()


@router.delete("/menu-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    item = await get_or_404(
        db, MenuItem, MenuItem.id == item_id, MenuItem.tenant_id == tenant.id,
        detail="Menu item not found",
    )
    await db.delete(item)
