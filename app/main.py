"""
Application Entry Point  —  Lifespan & Application State
=========================================================
Manages the server lifecycle for all stateful global resources.

ON STARTUP (initialised once, shared across all requests):
  1. PostgreSQL engine connection pool  — AsyncSession pool via SQLAlchemy
  2. Redis client                       — aioredis pool attached to app.state.redis
  3. WebSocket ConnectionManager        — already a module-level singleton in
                                          services/notification.py

ON SHUTDOWN (clean teardown to prevent memory leaks / data corruption):
  1. Redis connection pool closed
  2. SQLAlchemy async engine disposed   — drains and closes all pool connections

Dependency injection (request-level state):
  get_db()    — yields a scoped AsyncSession per request (auto-commit/rollback)
  get_redis() — defined in app/dependencies.py; yields the shared Redis client
                from app.state.redis (no per-request allocation)

Router Switchboard (mounted at startup under /api/v1):
  auth        → login, register, /me
  users       → Admin: full user CRUD
  menu        → categories, items, public GET
  tables      → CRUD, QR public menu, reservations
  orders      → create, active queue, FSM transitions, Redis cache
  billing     → preview, settle, coupons
  inventory   → stock CRUD, restock, recipe items
  reports     → sales summary, daily breakdown, trending items
  ws_router   → /ws/kitchen (broadcast), /ws/waiter/{id} (targeted push)

CORS Middleware:
  Configured via CORS_ORIGINS env var (comma-separated).
  Defaults to localhost dev ports; override in production.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings
from app.database import engine, Base
from app.routers import auth, users, menu, tables, orders, inventory, billing, reports, tenants
from app.services.notification import router as ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[STARTUP] Initialising application state...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[STARTUP] PostgreSQL connection pool ready.")

    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.redis = redis_client
    try:
        await redis_client.ping()
        logger.info("[STARTUP] Redis connection established at %s.", settings.REDIS_URL)
    except Exception as exc:
        logger.warning("[STARTUP] Redis unavailable (%s) — cache disabled.", exc)

    logger.info("[STARTUP] Application ready.")
    yield

    logger.info("[SHUTDOWN] Closing Redis connection pool...")
    await redis_client.aclose()

    logger.info("[SHUTDOWN] Disposing SQLAlchemy engine pool...")
    await engine.dispose()

    logger.info("[SHUTDOWN] Clean shutdown complete.")


app = FastAPI(
    title="Restaurant Management System (SaaS)",
    description=(
        "Multi-tenant SaaS backend for restaurant operations. "
        "Covers tenant onboarding, Stripe subscriptions, RBAC auth, "
        "real-time order workflow, dynamic billing, inventory management, "
        "reservations, and analytics reporting."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

V1 = "/api/v1"

app.include_router(auth.router,      prefix=V1)  # /api/v1/auth/*
app.include_router(users.router,     prefix=V1)  # /api/v1/users/*
app.include_router(menu.router,      prefix=V1)  # /api/v1/menu/*
app.include_router(tables.router,    prefix=V1)  # /api/v1/tables/* + public QR
app.include_router(orders.router,    prefix=V1)  # /api/v1/orders/* + FSM
app.include_router(billing.router,   prefix=V1)  # /api/v1/billing/*
app.include_router(inventory.router, prefix=V1)  # /api/v1/inventory/*
app.include_router(reports.router,   prefix=V1)  # /api/v1/reports/*
app.include_router(tenants.router,   prefix=V1)  # /api/v1/tenants/* + Stripe webhook
app.include_router(ws_router)                    # /ws/kitchen, /ws/waiter/{id}


@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "Restaurant Management System", "version": "2.0.0"}
