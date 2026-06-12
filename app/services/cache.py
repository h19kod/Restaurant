"""
Redis Cache Service  —  In-Memory State Cache
==============================================
Manages active-order state caching to reduce PostgreSQL query load.

Architecture role (State Management):
  Instead of hitting PostgreSQL on every GET /orders/active request
  from kitchen screens and waiter tablets, active order states are
  cached in Redis with a short TTL.

Eviction Policy:
  Any write that changes order state (create, status update, cancel)
  triggers an immediate cache invalidation via evict_active_orders().
  The next read re-queries PostgreSQL and repopulates the cache.

Cache key strategy:
  "active_orders:<role>"  →  serialised JSON of the order list
  TTL: 30 seconds (short enough to self-heal, long enough to absorb bursts)

Fallback:
  All cache operations are wrapped in try/except. If Redis is unavailable,
  the system degrades gracefully and reads directly from PostgreSQL without
  raising an error.
"""
import json
import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

ACTIVE_ORDERS_TTL = 30  # seconds


def _active_key(role: str, tenant_id: int) -> str:
    return f"active_orders:{tenant_id}:{role}"


async def get_cached_active_orders(redis: Redis, role: str, tenant_id: int) -> list[dict] | None:
    """
    Return cached active orders for *role* scoped to *tenant_id*, or None on cache miss / Redis error.
    """
    try:
        raw = await redis.get(_active_key(role, tenant_id))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("[CACHE] Redis read failed (%s) — falling back to DB", exc)
        return None


async def set_cached_active_orders(redis: Redis, role: str, tenant_id: int, data: list[dict]) -> None:
    """
    Persist the serialised order list into Redis with a 30-second TTL.
    """
    try:
        await redis.set(_active_key(role, tenant_id), json.dumps(data, default=str), ex=ACTIVE_ORDERS_TTL)
    except Exception as exc:
        logger.warning("[CACHE] Redis write failed (%s) — skipping cache", exc)


async def evict_active_orders(redis: Redis, tenant_id: int | None = None) -> None:
    """
    Invalidate active-order cache keys for a specific tenant (or all if tenant_id is None).
    Called by: create_order, update_order_status, cancel_order.
    """
    try:
        pattern = f"active_orders:{tenant_id}:*" if tenant_id else "active_orders:*"
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            logger.debug("[CACHE] Evicted %d active_orders cache keys", len(keys))
    except Exception as exc:
        logger.warning("[CACHE] Redis eviction failed (%s) — cache may be stale", exc)
