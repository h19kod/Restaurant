"""
Security Middleware & RBAC  —  Cross-cutting Layer
===================================================
This module sits between Layer 1 (Router) and Layer 2 (Service).

Responsibilities:
  1. JWT decoding: verifies the HS256 signature and expiry on every request.
  2. Identity hydration: loads the live User row from PostgreSQL and cross-checks
     the token claims (user_id, username, role) against the database to prevent
     stale or tampered tokens from passing through.
  3. RBAC enforcement: require_roles() returns a FastAPI dependency that raises
     HTTP 403 if the authenticated user's role is not in the permitted set.

Data flow position:
  [HTTP Request]
       │
       ▼
  oauth2_scheme  ←──  Authorization: Bearer <token>
       │
       ▼
  get_current_user()  →  JWT decode → DB lookup → role check
       │
       ▼
  [Router handler receives validated User object]
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import SubscriptionStatus, Tenant, User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, username: str, role: str, tenant_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "tid": tenant_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        username: str | None = payload.get("username")
        role: str | None = payload.get("role")
        tenant_id: int | None = payload.get("tid")
        if not user_id or not username or not role or not tenant_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == int(user_id), User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    if user.username != username or user.role.value != role:
        raise credentials_exception
    return user


async def get_current_tenant(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant:
    """Extract tenant from JWT and verify it is active and not expired."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        tenant_id: int | None = payload.get("tid")
        if not tenant_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    tenant = await db.get(Tenant, tenant_id)
    if tenant is None or not tenant.is_active:
        raise credentials_exception

    if tenant.subscription_status in (SubscriptionStatus.Expired, SubscriptionStatus.Cancelled):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription expired. Please renew at /api/v1/tenants/billing/portal",
        )
    return tenant


def require_roles(*roles: UserRole):
    async def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return role_checker


RequireAdmin = Depends(require_roles(UserRole.Admin))
RequireCashier = Depends(require_roles(UserRole.Admin, UserRole.Cashier))
RequireWaiter = Depends(require_roles(UserRole.Admin, UserRole.Waiter))
RequireChef = Depends(require_roles(UserRole.Admin, UserRole.Chef))
RequireAnyStaff = Depends(require_roles(UserRole.Admin, UserRole.Cashier, UserRole.Waiter, UserRole.Chef))
