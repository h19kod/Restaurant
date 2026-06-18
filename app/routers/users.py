from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import RequireAdmin, get_current_tenant
from app.database import get_db
from app.models import Tenant, User
from app.schemas import UserOut, UserUpdate
from app.services.crud_helpers import apply_partial_update, get_or_404

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserOut])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(User).where(User.tenant_id == tenant.id))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    return await get_or_404(
        db, User, User.id == user_id, User.tenant_id == tenant.id,
        detail="User not found",
    )


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    user = await get_or_404(
        db, User, User.id == user_id, User.tenant_id == tenant.id,
        detail="User not found",
    )
    await apply_partial_update(db, user, payload)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    user = await get_or_404(
        db, User, User.id == user_id, User.tenant_id == tenant.id,
        detail="User not found",
    )
    await db.delete(user)
