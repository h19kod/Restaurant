"""
Shared pytest fixtures for the Restaurant API test suite.

Uses an in-memory SQLite database (via aiosqlite) so tests run
without any external PostgreSQL or Redis instance.
"""
import uuid
from decimal import Decimal
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.dependencies import get_redis
from app.main import app
from app.models import (
    Category, Inventory, MenuItem,
    Order, OrderItem, OrderStatus, OrderType,
    PaymentMethod, RecipeItem, StockUnit, Table, TableStatus,
    User, UserRole,
)


async def override_get_redis():
    async with FakeRedis() as r:
        yield r


app.dependency_overrides[get_redis] = override_get_redis


def _uid() -> str:
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# In-memory SQLite engine shared across the whole test session
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Session-scoped table creation
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Function-scoped DB session (each test gets its own session)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Seed helpers  (all use _uid() so names are always unique)
# ---------------------------------------------------------------------------

async def _make_user(db, username, role, password="pass123"):
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=username.title(),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_category(db, name=None):
    cat = Category(name=name if name else "Cat_" + _uid())
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


async def _make_menu_item(db, category_id, name=None, price="10.00"):
    item = MenuItem(
        category_id=category_id,
        name=name if name else "Item_" + _uid(),
        price=Decimal(price),
        is_available=True,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def _make_table(db, capacity=4):
    import secrets
    table = Table(capacity=capacity, qr_code_token=secrets.token_urlsafe(16))
    db.add(table)
    await db.flush()
    await db.refresh(table)
    return table


def _token(user):
    return create_access_token(user_id=user.id, username=user.username, role=user.role.value)


def _auth(user):
    return {"Authorization": "Bearer " + _token(user)}


# ---------------------------------------------------------------------------
# Pre-seeded fixtures  (unique names per test via _uid())
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def admin(db):
    return await _make_user(db, "admin_" + _uid(), UserRole.Admin)


@pytest_asyncio.fixture
async def waiter(db):
    return await _make_user(db, "waiter_" + _uid(), UserRole.Waiter)


@pytest_asyncio.fixture
async def chef(db):
    return await _make_user(db, "chef_" + _uid(), UserRole.Chef)


@pytest_asyncio.fixture
async def cashier(db):
    return await _make_user(db, "cashier_" + _uid(), UserRole.Cashier)


@pytest_asyncio.fixture
async def category(db):
    return await _make_category(db, "Category_" + _uid())


@pytest_asyncio.fixture
async def menu_item(db, category):
    return await _make_menu_item(db, category.id, "Item_" + _uid(), "12.00")


@pytest_asyncio.fixture
async def table(db):
    return await _make_table(db)


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
