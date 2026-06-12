from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    RequireAdmin,
    create_access_token,
    get_current_tenant,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import Tenant, User
from app.schemas import Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
        tenant_id=user.tenant_id,
    )
    return Token(access_token=token)


@router.post("/token", response_model=Token, include_in_schema=False)
async def login_compat(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """OAuth2 compatibility alias — same as /login. Required by OAuth2PasswordBearer flow."""
    return await login(form_data, db)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    existing = await db.execute(
        select(User).where(User.username == payload.username, User.tenant_id == tenant.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    user = User(
        tenant_id=tenant.id,
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        phone=payload.phone,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
