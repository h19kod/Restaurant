"""
Shared FastAPI dependencies — avoids circular imports between main.py and routers.
"""
from fastapi import Request
from redis.asyncio import Redis


async def get_redis(request: Request) -> Redis:
    """Yields the shared Redis client initialised in the lifespan (app.state.redis)."""
    return request.app.state.redis
