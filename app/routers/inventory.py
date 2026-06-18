from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import RequireAdmin, get_current_tenant, get_current_user
from app.database import get_db
from app.models import Inventory, MenuItem, RecipeItem, Tenant, User
from app.schemas import InventoryCreate, InventoryOut, InventoryRestock, InventoryUpdate, RecipeItemCreate, RecipeItemOut
from app.services.crud_helpers import apply_partial_update, check_unique_or_409, create_and_refresh, get_or_404
from app.services.stock_manager import restock_ingredient

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.patch("/{item_id}/restock", response_model=InventoryOut)
async def restock_item(
    item_id: int,
    payload: InventoryRestock,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    """Adjust stock upward when a new shipment arrives."""
    await get_or_404(
        db, Inventory, Inventory.id == item_id, Inventory.tenant_id == tenant.id,
        detail="Inventory item not found",
    )
    try:
        item = await restock_ingredient(db, item_id, payload.quantity_to_add)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return InventoryOut.from_model(item)


@router.get("/", response_model=list[InventoryOut])
async def list_inventory(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    low_stock_only: bool = False,
):
    result = await db.execute(select(Inventory).where(Inventory.tenant_id == tenant.id))
    items = result.scalars().all()
    if low_stock_only:
        items = [i for i in items if i.current_stock < i.min_alert_level]
    return [InventoryOut.from_model(i) for i in items]


@router.get("/{item_id}", response_model=InventoryOut)
async def get_inventory_item(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    item = await get_or_404(
        db, Inventory, Inventory.id == item_id, Inventory.tenant_id == tenant.id,
        detail="Inventory item not found",
    )
    return InventoryOut.from_model(item)


@router.post("/", response_model=InventoryOut, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    payload: InventoryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    await check_unique_or_409(
        db, Inventory,
        Inventory.ingredient_name == payload.ingredient_name, Inventory.tenant_id == tenant.id,
        detail="Ingredient already exists",
    )
    item = Inventory(tenant_id=tenant.id, **payload.model_dump())
    await create_and_refresh(db, item)
    return InventoryOut.from_model(item)


@router.patch("/{item_id}", response_model=InventoryOut)
async def update_inventory_item(
    item_id: int,
    payload: InventoryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    item = await get_or_404(
        db, Inventory, Inventory.id == item_id, Inventory.tenant_id == tenant.id,
        detail="Inventory item not found",
    )
    await apply_partial_update(db, item, payload)
    return InventoryOut.from_model(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    item = await get_or_404(
        db, Inventory, Inventory.id == item_id, Inventory.tenant_id == tenant.id,
        detail="Inventory item not found",
    )
    await db.delete(item)


# ---------------------------------------------------------------------------
# Recipe mappings: MenuItem → Inventory ingredients
# ---------------------------------------------------------------------------

@router.get("/recipes", response_model=list[RecipeItemOut])
async def list_recipes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    menu_item_id: int | None = None,
):
    """List all recipe mappings. Filter by menu_item_id to get a single dish's ingredients."""
    query = select(RecipeItem).join(MenuItem).where(MenuItem.tenant_id == tenant.id)
    if menu_item_id is not None:
        query = query.where(RecipeItem.menu_item_id == menu_item_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/recipes", response_model=RecipeItemOut, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    payload: RecipeItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    """Map a MenuItem to an Inventory ingredient with a required quantity per unit sold."""
    await get_or_404(
        db, MenuItem, MenuItem.id == payload.menu_item_id, MenuItem.tenant_id == tenant.id,
        detail="MenuItem not found",
    )
    await get_or_404(
        db, Inventory, Inventory.id == payload.ingredient_id, Inventory.tenant_id == tenant.id,
        detail="Inventory ingredient not found",
    )
    await check_unique_or_409(
        db, RecipeItem,
        RecipeItem.menu_item_id == payload.menu_item_id,
        RecipeItem.ingredient_id == payload.ingredient_id,
        detail="Recipe mapping already exists",
    )
    recipe = RecipeItem(**payload.model_dump())
    await create_and_refresh(db, recipe)
    return recipe


@router.patch("/recipes/{recipe_id}", response_model=RecipeItemOut)
async def update_recipe(
    recipe_id: int,
    required_quantity: float,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
):
    """Update the required_quantity for an existing recipe mapping."""
    recipe = await db.get(RecipeItem, recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe mapping not found")
    recipe.required_quantity = required_quantity
    await db.flush()
    await db.refresh(recipe)
    return recipe


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
):
    recipe = await db.get(RecipeItem, recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe mapping not found")
    await db.delete(recipe)
