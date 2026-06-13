"""
Tenants Router — SaaS onboarding, subscription management, Stripe webhooks.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_tenant, hash_password
from app.config import settings
from app.database import get_db
from app.models import SubscriptionPlan, SubscriptionStatus, Tenant, User, UserRole
from app.services.stripe_service import (
    PLANS,
    construct_webhook_event,
    create_checkout_session,
    create_customer,
    create_portal_session,
    parse_subscription_update,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tenants", tags=["Tenants & Subscriptions"])

_FRONTEND_URL = "http://localhost:8501"


# ---------------------------------------------------------------------------
# Inline schemas
# ---------------------------------------------------------------------------

class TenantRegisterRequest(BaseModel):
    restaurant_name: str
    subdomain: str
    admin_username: str
    admin_password: str
    admin_full_name: str
    admin_email: EmailStr

    @field_validator("subdomain")
    @classmethod
    def subdomain_slug(cls, v: str) -> str:
        slug = re.sub(r"[^a-z0-9-]", "-", v.lower()).strip("-")
        if not slug:
            raise ValueError("subdomain must contain alphanumeric characters")
        return slug

    @field_validator("admin_password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TenantOut(BaseModel):
    id: int
    name: str
    subdomain: str
    plan: str
    subscription_status: str
    is_active: bool
    created_at: datetime
    current_period_end: datetime | None = None
    model_config = {"from_attributes": True}


class TenantRegisterResponse(BaseModel):
    tenant: TenantOut
    access_token: str
    token_type: str = "bearer"
    message: str


class SubscribeRequest(BaseModel):
    plan: str

    @field_validator("plan")
    @classmethod
    def valid_plan(cls, v: str) -> str:
        if v not in PLANS:
            raise ValueError(f"Plan must be one of: {list(PLANS.keys())}")
        return v


class SubscriptionStatusOut(BaseModel):
    plan: str
    status: str
    current_period_end: datetime | None
    max_users: int
    max_tables: int
    is_active: bool


# ---------------------------------------------------------------------------
# POST /tenants/register — public, no auth needed
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=TenantRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_tenant(
    payload: TenantRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Onboard a new restaurant. Creates Tenant + Admin user + Stripe customer.
    Returns a ready-to-use JWT token for the new admin so they can log in immediately.
    """
    # Subdomain uniqueness check
    existing = await db.execute(
        select(Tenant).where(Tenant.subdomain == payload.subdomain)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subdomain '{payload.subdomain}' is already taken",
        )

    # Create tenant with 14-day free trial
    from datetime import timedelta
    trial_end = datetime.now(timezone.utc) + timedelta(days=14)
    tenant = Tenant(
        name=payload.restaurant_name,
        subdomain=payload.subdomain,
        plan=SubscriptionPlan.Free,
        subscription_status=SubscriptionStatus.Trialing,
        trial_ends_at=trial_end,
        is_active=True,
    )
    db.add(tenant)
    await db.flush()  # get tenant.id

    # Create first admin user scoped to this tenant
    admin = User(
        tenant_id=tenant.id,
        username=payload.admin_username,
        password_hash=hash_password(payload.admin_password),
        full_name=payload.admin_full_name,
        role=UserRole.Admin,
        is_active=True,
    )
    db.add(admin)
    await db.flush()

    # Register with Stripe (non-blocking — skip if Stripe not configured)
    if settings.STRIPE_SECRET_KEY:
        try:
            stripe_customer_id = create_customer(
                tenant_name=payload.restaurant_name,
                admin_email=payload.admin_email,
                tenant_id=tenant.id,
            )
            tenant.stripe_customer_id = stripe_customer_id
        except Exception as exc:
            logger.warning("[STRIPE] Customer creation failed: %s — continuing without Stripe", exc)

    await db.flush()

    token = create_access_token(
        user_id=admin.id,
        username=admin.username,
        role=admin.role.value,
        tenant_id=tenant.id,
    )

    return TenantRegisterResponse(
        tenant=TenantOut.model_validate(tenant),
        access_token=token,
        message=(
            f"Welcome to Restaurant Management System! "
            f"Your 14-day free trial has started. "
            f"Access your dashboard at {_FRONTEND_URL}"
        ),
    )


# ---------------------------------------------------------------------------
# GET /tenants/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=TenantOut)
async def get_tenant_info(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    return TenantOut.model_validate(tenant)


# ---------------------------------------------------------------------------
# GET /tenants/billing/status
# ---------------------------------------------------------------------------

@router.get("/billing/status", response_model=SubscriptionStatusOut)
async def billing_status(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    plan_data = PLANS.get(tenant.plan.value, PLANS["Free"])
    return SubscriptionStatusOut(
        plan=tenant.plan.value,
        status=tenant.subscription_status.value,
        current_period_end=tenant.current_period_end,
        max_users=plan_data["max_users"],
        max_tables=plan_data["max_tables"],
        is_active=tenant.is_active,
    )


# ---------------------------------------------------------------------------
# POST /tenants/billing/subscribe — upgrade to paid plan
# ---------------------------------------------------------------------------

@router.post("/billing/subscribe")
async def subscribe(
    payload: SubscribeRequest,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured on this server",
        )
    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer found for this tenant. Contact support.",
        )
    try:
        checkout_url = create_checkout_session(
            stripe_customer_id=tenant.stripe_customer_id,
            plan=payload.plan,
            success_url=f"{_FRONTEND_URL}?payment=success",
            cancel_url=f"{_FRONTEND_URL}?payment=cancelled",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("[STRIPE] Checkout session creation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stripe error")

    return {"checkout_url": checkout_url}


# ---------------------------------------------------------------------------
# POST /tenants/billing/portal — self-service billing management
# ---------------------------------------------------------------------------

@router.post("/billing/portal")
async def billing_portal(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured on this server",
        )
    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer linked to this tenant",
        )
    try:
        portal_url = create_portal_session(
            stripe_customer_id=tenant.stripe_customer_id,
            return_url=f"{_FRONTEND_URL}",
        )
    except Exception as exc:
        logger.error("[STRIPE] Portal session creation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stripe error")
    return {"portal_url": portal_url}


# ---------------------------------------------------------------------------
# POST /tenants/webhook/stripe — Stripe event processor
# ---------------------------------------------------------------------------

@router.post("/webhook/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    stripe_signature: str | None = None,
):
    """
    Receives Stripe webhook events and updates the corresponding Tenant row.
    Must be called with raw body — FastAPI must NOT parse it as JSON.
    Verified via STRIPE_WEBHOOK_SECRET.
    """
    raw_body = await request.body()
    sig = stripe_signature or request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(raw_body, sig)
    except ValueError as exc:
        logger.warning("[STRIPE WEBHOOK] Rejected: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    event_type: str = event["type"]
    logger.info("[STRIPE WEBHOOK] Received event: %s", event_type)

    handled = {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
    }

    if event_type not in handled:
        return {"status": "ignored", "event_type": event_type}

    # Resolve tenant from Stripe customer_id
    customer_id: str | None = None
    obj = event["data"]["object"]
    if event_type.startswith("customer.subscription"):
        customer_id = obj.get("customer")
    elif event_type.startswith("invoice"):
        customer_id = obj.get("customer")

    if not customer_id:
        return {"status": "skipped", "reason": "no customer_id in event"}

    result = await db.execute(
        select(Tenant).where(Tenant.stripe_customer_id == customer_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        logger.warning("[STRIPE WEBHOOK] No tenant found for customer %s", customer_id)
        return {"status": "skipped", "reason": "tenant_not_found"}

    # Apply updates from subscription events
    if event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        updates = parse_subscription_update(event)
        for field, value in updates.items():
            setattr(tenant, field, value)
        if event_type == "customer.subscription.deleted":
            tenant.subscription_status = SubscriptionStatus.Cancelled

    elif event_type == "invoice.payment_failed":
        tenant.subscription_status = SubscriptionStatus.PastDue

    elif event_type == "invoice.payment_succeeded":
        if tenant.subscription_status == SubscriptionStatus.PastDue:
            tenant.subscription_status = SubscriptionStatus.Active

    await db.flush()
    logger.info(
        "[STRIPE WEBHOOK] Tenant #%d updated: plan=%s status=%s",
        tenant.id, tenant.plan.value, tenant.subscription_status.value,
    )
    return {"status": "ok", "tenant_id": tenant.id}
