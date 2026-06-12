"""
Reports & Analytics module — /api/v1/reports

Admin-only aggregation queries over existing Invoice and OrderItem tables.
No standalone reporting tables are required — all metrics are computed on demand.

GET /reports/sales/summary   — revenue totals with ?range=daily|monthly|custom
GET /reports/items/trending  — top-selling menu items by quantity
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import RequireAdmin, get_current_tenant
from app.database import get_db
from app.models import Invoice, MenuItem, Order, OrderItem, Tenant, User
from app.schemas import DailySales, SalesReport, TopMenuItem

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


def _resolve_date_range(
    range_preset: str | None,
    start: datetime | None,
    end: datetime | None,
) -> tuple[datetime, datetime]:
    """
    Resolve query boundaries from either a named preset or explicit datetimes.
    Presets: 'daily' = today, 'monthly' = current calendar month.
    """
    now = datetime.now(timezone.utc)
    if range_preset == "daily":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)
    elif range_preset == "monthly":
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            period_end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            period_end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        if not start or not end:
            raise ValueError("Provide ?range=daily|monthly or explicit ?start= and ?end= datetimes")
        period_start, period_end = start, end
    return period_start, period_end


@router.get("/sales/summary", response_model=SalesReport)
async def sales_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    range: str | None = Query(None, description="Preset range: 'daily' or 'monthly'"),
    start: datetime | None = Query(None, description="Custom range start (UTC ISO-8601)"),
    end: datetime | None = Query(None, description="Custom range end (UTC ISO-8601)"),
):
    """
    Computes absolute monetary performance for a date range.
    Accepts ?range=daily, ?range=monthly, or explicit ?start + ?end boundaries.
    Aggregates SUM(total_amount) and COUNT(id) from the Invoice table.
    """
    try:
        period_start, period_end = _resolve_date_range(range, start, end)
    except ValueError as exc:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.total_amount), 0).label("revenue"),
            func.count(Invoice.id).label("count"),
        ).where(Invoice.tenant_id == tenant.id, Invoice.paid_at.between(period_start, period_end))
    )
    row = result.one()
    revenue = Decimal(str(row.revenue))
    count = int(row.count)
    avg = (revenue / count).quantize(Decimal("0.01")) if count else Decimal("0.00")

    return SalesReport(
        period_start=period_start,
        period_end=period_end,
        total_revenue=revenue,
        total_invoices=count,
        average_order_value=avg,
    )


@router.get("/sales/daily", response_model=list[DailySales])
async def daily_sales_breakdown(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    start: datetime = Query(..., description="Range start (UTC ISO-8601)"),
    end: datetime = Query(..., description="Range end (UTC ISO-8601)"),
):
    """
    Day-by-day revenue breakdown within a date range.
    Groups Invoice rows by calendar date, ordered chronologically.
    """
    result = await db.execute(
        select(
            cast(Invoice.paid_at, Date).label("day"),
            func.sum(Invoice.total_amount).label("revenue"),
            func.count(Invoice.id).label("invoice_count"),
        )
        .where(Invoice.tenant_id == tenant.id, Invoice.paid_at.between(start, end))
        .group_by(cast(Invoice.paid_at, Date))
        .order_by(cast(Invoice.paid_at, Date))
    )
    return [
        DailySales(
            date=str(r.day),
            revenue=Decimal(str(r.revenue)),
            invoice_count=int(r.invoice_count),
        )
        for r in result.all()
    ]


@router.get("/items/trending", response_model=list[TopMenuItem])
async def trending_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    limit: int = Query(10, ge=1, le=100, description="Number of top items to return"),
):
    """
    Identifies high-performing items by total quantity sold.
    Groups OrderItem by menu_item_id, sums quantity and revenue,
    sorted descending — ideal for rendering frontend bar/pie charts.
    """
    result = await db.execute(
        select(
            OrderItem.menu_item_id,
            MenuItem.name,
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.ordered_price * OrderItem.quantity).label("total_revenue"),
        )
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.tenant_id == tenant.id)
        .group_by(OrderItem.menu_item_id, MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )
    return [
        TopMenuItem(
            menu_item_id=r.menu_item_id,
            name=r.name,
            total_quantity_ordered=int(r.total_qty),
            total_revenue=Decimal(str(r.total_revenue)),
        )
        for r in result.all()
    ]
