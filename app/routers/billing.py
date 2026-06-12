"""
Billing Router  —  Layer 1 (Router) + Layer 2 (Service Logic)
=============================================================
Handles invoice generation and coupon management on /api/v1/billing.

Phase D — Checkout, Invoicing & Inventory (Background Queue):

  Step 1  Cashier hits POST /billing/invoices/settle/{order_id}
            ├─ RequireCashier RBAC guard
            ├─ Duplicate invoice guard (HTTP 409 if already settled)
            └─ _compute_invoice_figures() — Service Logic:
                 ├─ Aggregates locked OrderItem prices (subtotal)
                 ├─ Applies regional TAX_RATE from config
                 └─ Validates & applies coupon (expiry check, percentage/fixed)

  Step 2  Invoice row written to PostgreSQL with payment_method + paid_at
            └─ Linked Table.status reset to Empty

  Step 3  Main thread dispatches two Celery tasks via Redis broker:
            ├─ print_receipt.delay(invoice.id)            ← non-blocking
            └─ adjust_inventory_on_invoice.delay(invoice.id) ← non-blocking

  Step 4  Cashier's response returns instantly (main thread released)
           Background worker (separate process):
            ├─ Loads RecipeItem mappings for each sold MenuItem
            ├─ Deducts required_quantity from Inventory.current_stock
            └─ Flags low-stock alert if current_stock < min_alert_level

Endpoints:
  POST /billing/invoices/preview/{order_id}  — dry-run calculation, no DB write
  POST /billing/invoices/settle/{order_id}   — finalize payment, dispatch tasks
  GET  /billing/invoices                     — list all invoices
  GET  /billing/invoices/{invoice_id}        — single invoice
  CRUD /billing/coupons                      — coupon management [Admin]
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import RequireAdmin, RequireCashier, get_current_tenant, get_current_user
from app.config import settings
from app.database import get_db
from app.models import (
    DiscountCoupon, DiscountType, Invoice, Order, OrderItem,
    OrderStatus, Table, TableStatus, Tenant, User,
)
from app.schemas import (
    CouponCreate, CouponOut, CouponUpdate,
    InvoiceOut, InvoicePreview, InvoiceSettle,
)
from app.tasks import adjust_inventory_on_invoice, print_receipt

router = APIRouter(prefix="/billing", tags=["Billing & Finance"])


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def _compute_invoice_figures(
    db: AsyncSession,
    order_id: int,
    coupon_code: str | None,
    tenant_id: int,
) -> tuple[Decimal, Decimal, Decimal, Decimal, DiscountCoupon | None]:
    """
    Returns (subtotal, tax_amount, discount_amount, total_amount, coupon_or_None).
    Used by both preview and settle to guarantee identical calculation logic.
    """
    result = await db.execute(
        select(Order).options(selectinload(Order.order_items)).where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status == OrderStatus.Cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot bill a cancelled order")

    subtotal: Decimal = sum(item.ordered_price * item.quantity for item in order.order_items)
    tax_amount = (subtotal * Decimal(str(settings.TAX_RATE))).quantize(Decimal("0.01"))
    discount_amount = Decimal("0.00")
    coupon = None

    if coupon_code:
        coupon_result = await db.execute(
            select(DiscountCoupon).where(
                DiscountCoupon.code == coupon_code,
                DiscountCoupon.tenant_id == tenant_id,
                DiscountCoupon.is_active.is_(True),
            )
        )
        coupon = coupon_result.scalar_one_or_none()
        if not coupon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found or inactive")
        now = datetime.now(timezone.utc)
        if coupon.expiry_date and coupon.expiry_date < now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon has expired")
        if coupon.discount_type == DiscountType.Percentage:
            discount_amount = (subtotal * coupon.value / Decimal("100")).quantize(Decimal("0.01"))
        else:
            discount_amount = min(coupon.value, subtotal)

    total_amount = (subtotal + tax_amount - discount_amount).quantize(Decimal("0.01"))
    return subtotal, tax_amount, discount_amount, total_amount, coupon


# ---------------------------------------------------------------------------
# Invoice preview (no DB write)
# ---------------------------------------------------------------------------

@router.post("/invoices/preview/{order_id}", response_model=InvoicePreview)
async def preview_invoice(
    order_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireCashier],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    coupon_code: str | None = None,
):
    """
    Real-time pre-checkout receipt summary.
    Calculates exact prices, dynamic tax, and any valid promotional discount
    without writing anything to the database — safe to call multiple times.
    """
    subtotal, tax_amount, discount_amount, total_amount, coupon = await _compute_invoice_figures(
        db, order_id, coupon_code, tenant.id
    )
    return InvoicePreview(
        order_id=order_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        coupon_code=coupon.code if coupon else None,
        coupon_applied=coupon is not None,
    )


# ---------------------------------------------------------------------------
# Settle (finalize payment)
# ---------------------------------------------------------------------------

@router.post("/invoices/settle/{order_id}", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def settle_invoice(
    order_id: int,
    payload: InvoiceSettle,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireCashier],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    """
    Finalizes and closes out an active order ticket:
    - Locks in calculated financial totals
    - Records payment method and timestamp
    - Resets linked table status to Empty
    - Dispatches background Celery tasks (receipt print, inventory deduction)
    """
    existing = await db.execute(select(Invoice).where(Invoice.order_id == order_id, Invoice.tenant_id == tenant.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invoice already exists for this order")

    subtotal, tax_amount, discount_amount, total_amount, coupon = await _compute_invoice_figures(
        db, order_id, payload.coupon_code, tenant.id
    )

    invoice = Invoice(
        tenant_id=tenant.id,
        order_id=order_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        coupon_id=coupon.id if coupon else None,
        discount_amount=discount_amount,
        total_amount=total_amount,
        payment_method=payload.payment_method,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(invoice)
    await db.flush()

    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one()
    if order.table_id:
        table = await db.get(Table, order.table_id)
        if table:
            table.status = TableStatus.Empty

    await db.refresh(invoice)

    print_receipt.delay(invoice.id)
    adjust_inventory_on_invoice.delay(invoice.id)

    return invoice


# ---------------------------------------------------------------------------
# Invoice read endpoints
# ---------------------------------------------------------------------------

@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(Invoice).where(Invoice.tenant_id == tenant.id))
    return result.scalars().all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant.id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


# ---------------------------------------------------------------------------
# Coupon management
# ---------------------------------------------------------------------------

@router.get("/coupons", response_model=list[CouponOut])
async def list_coupons(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(DiscountCoupon).where(DiscountCoupon.tenant_id == tenant.id))
    return result.scalars().all()


@router.get("/coupons/{coupon_id}", response_model=CouponOut)
async def get_coupon(
    coupon_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(DiscountCoupon).where(DiscountCoupon.id == coupon_id, DiscountCoupon.tenant_id == tenant.id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    return coupon


@router.post("/coupons", response_model=CouponOut, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    payload: CouponCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    existing = await db.execute(select(DiscountCoupon).where(DiscountCoupon.code == payload.code, DiscountCoupon.tenant_id == tenant.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coupon code already exists")
    coupon = DiscountCoupon(tenant_id=tenant.id, **payload.model_dump())
    db.add(coupon)
    await db.flush()
    await db.refresh(coupon)
    return coupon


@router.patch("/coupons/{coupon_id}", response_model=CouponOut)
async def update_coupon(
    coupon_id: int,
    payload: CouponUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(DiscountCoupon).where(DiscountCoupon.id == coupon_id, DiscountCoupon.tenant_id == tenant.id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(coupon, field, value)
    await db.flush()
    await db.refresh(coupon)
    return coupon


@router.delete("/coupons/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(
    coupon_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(DiscountCoupon).where(DiscountCoupon.id == coupon_id, DiscountCoupon.tenant_id == tenant.id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    await db.delete(coupon)
