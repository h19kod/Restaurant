"""Tests for Redis cache service (app/services/cache.py)."""
import json

import pytest
from fakeredis.aioredis import FakeRedis

from app.services.cache import (
    ACTIVE_ORDERS_TTL,
    _active_key,
    evict_active_orders,
    get_cached_active_orders,
    set_cached_active_orders,
)


@pytest.fixture
async def redis():
    async with FakeRedis() as r:
        yield r


@pytest.mark.asyncio
async def test_active_key_format():
    assert _active_key("Chef", 1) == "active_orders:1:Chef"
    assert _active_key("Waiter", 42) == "active_orders:42:Waiter"


@pytest.mark.asyncio
async def test_cache_miss_returns_none(redis):
    result = await get_cached_active_orders(redis, "Chef", tenant_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_set_and_get_cached_orders(redis):
    orders = [{"id": 1, "status": "Pending"}, {"id": 2, "status": "Preparing"}]
    await set_cached_active_orders(redis, "Chef", tenant_id=1, data=orders)
    result = await get_cached_active_orders(redis, "Chef", tenant_id=1)
    assert result == orders


@pytest.mark.asyncio
async def test_cache_ttl_is_set(redis):
    await set_cached_active_orders(redis, "Waiter", tenant_id=1, data=[{"id": 3}])
    ttl = await redis.ttl(_active_key("Waiter", 1))
    assert 0 < ttl <= ACTIVE_ORDERS_TTL


@pytest.mark.asyncio
async def test_evict_active_orders_specific_tenant(redis):
    await set_cached_active_orders(redis, "Chef", tenant_id=1, data=[{"id": 1}])
    await set_cached_active_orders(redis, "Waiter", tenant_id=1, data=[{"id": 2}])
    await set_cached_active_orders(redis, "Chef", tenant_id=2, data=[{"id": 3}])

    await evict_active_orders(redis, tenant_id=1)

    assert await get_cached_active_orders(redis, "Chef", tenant_id=1) is None
    assert await get_cached_active_orders(redis, "Waiter", tenant_id=1) is None
    result = await get_cached_active_orders(redis, "Chef", tenant_id=2)
    assert result == [{"id": 3}]


@pytest.mark.asyncio
async def test_evict_active_orders_all(redis):
    await set_cached_active_orders(redis, "Chef", tenant_id=1, data=[{"id": 1}])
    await set_cached_active_orders(redis, "Chef", tenant_id=2, data=[{"id": 2}])

    await evict_active_orders(redis, tenant_id=None)

    assert await get_cached_active_orders(redis, "Chef", tenant_id=1) is None
    assert await get_cached_active_orders(redis, "Chef", tenant_id=2) is None


@pytest.mark.asyncio
async def test_evict_noop_when_no_keys(redis):
    """evict should succeed even with no matching keys."""
    await evict_active_orders(redis, tenant_id=999)
