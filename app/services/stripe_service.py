"""
Stripe Service — SaaS subscription billing integration.
========================================================
Wraps the stripe-python SDK to keep all Stripe logic in one place.

Supported operations:
  - create_customer()       → registers a new tenant in Stripe
  - create_checkout_session() → starts a hosted payment page
  - create_portal_session()  → opens Stripe's self-service billing portal
  - handle_webhook_event()   → processes subscription lifecycle events

Webhook events handled:
  customer.subscription.created  → Trialing → Active
  customer.subscription.updated  → plan/status changes
  customer.subscription.deleted  → Active → Cancelled
  invoice.payment_failed         → Active → PastDue
  invoice.payment_succeeded      → PastDue → Active
"""
import logging
from datetime import datetime, timezone

import stripe

from app.config import settings
from app.models import SubscriptionPlan, SubscriptionStatus

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# ---------------------------------------------------------------------------
# Subscription plans — map internal plan names to Stripe Price IDs
# ---------------------------------------------------------------------------

PLANS: dict[str, dict] = {
    "Free": {
        "price_id": None,
        "max_users": 3,
        "max_tables": 5,
        "trial_days": 14,
    },
    "Basic": {
        "price_id": settings.STRIPE_PRICE_BASIC,
        "max_users": 10,
        "max_tables": 20,
        "trial_days": 0,
    },
    "Pro": {
        "price_id": settings.STRIPE_PRICE_PRO,
        "max_users": 50,
        "max_tables": 100,
        "trial_days": 0,
    },
    "Enterprise": {
        "price_id": settings.STRIPE_PRICE_ENTERPRISE,
        "max_users": -1,
        "max_tables": -1,
        "trial_days": 0,
    },
}


# ---------------------------------------------------------------------------
# Customer management
# ---------------------------------------------------------------------------

def create_customer(tenant_name: str, admin_email: str, tenant_id: int) -> str:
    """Create a Stripe Customer for a new tenant. Returns stripe_customer_id."""
    customer = stripe.Customer.create(
        name=tenant_name,
        email=admin_email,
        metadata={"tenant_id": str(tenant_id)},
    )
    logger.info("[STRIPE] Created customer %s for tenant #%d", customer.id, tenant_id)
    return customer.id


# ---------------------------------------------------------------------------
# Checkout & Portal sessions
# ---------------------------------------------------------------------------

def create_checkout_session(
    stripe_customer_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout session for upgrading to a paid plan.
    Returns the hosted checkout URL to redirect the user to.
    """
    price_id = PLANS[plan]["price_id"]
    if not price_id:
        raise ValueError(f"Plan '{plan}' has no Stripe Price ID configured")

    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"plan": plan},
    )
    logger.info("[STRIPE] Checkout session %s created for customer %s", session.id, stripe_customer_id)
    return session.url


def create_portal_session(stripe_customer_id: str, return_url: str) -> str:
    """
    Opens Stripe's self-service portal where the tenant can update their
    payment method, upgrade/downgrade plan, or cancel.
    Returns the portal URL.
    """
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return session.url


# ---------------------------------------------------------------------------
# Webhook event processor
# ---------------------------------------------------------------------------

def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify webhook signature and return parsed event. Raises ValueError on bad sig."""
    try:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError as exc:
        raise ValueError(f"Invalid Stripe webhook signature: {exc}") from exc


def parse_subscription_update(event: stripe.Event) -> dict:
    """
    Extract the fields we care about from a subscription event.
    Returns a dict ready to apply to the Tenant row.
    """
    sub = event["data"]["object"]
    status_map = {
        "trialing":        "Trialing",
        "active":          "Active",
        "past_due":        "PastDue",
        "canceled":        "Cancelled",
        "unpaid":          "Expired",
        "incomplete_expired": "Expired",
    }
    stripe_status = sub.get("status", "")
    internal_status = status_map.get(stripe_status, "Active")

    current_period_end = sub.get("current_period_end")
    period_end_dt = (
        datetime.fromtimestamp(current_period_end, tz=timezone.utc)
        if current_period_end else None
    )

    # Determine plan from price metadata
    plan = "Basic"
    items = sub.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")
        for plan_name, plan_data in PLANS.items():
            if plan_data.get("price_id") == price_id:
                plan = plan_name
                break

    return {
        "stripe_subscription_id": sub.get("id"),
        "subscription_status": SubscriptionStatus(internal_status),
        "plan": SubscriptionPlan(plan),
        "current_period_end": period_end_dt,
    }
