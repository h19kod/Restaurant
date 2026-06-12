"""
Tables & Reservations Router  —  Layer 1: API / Presentation Layer
==================================================================
Handles table management, reservation lifecycle, and the public QR menu
endpoint on /api/v1/tables.

Cross-module integration — Workflow A: QR-Code Customer Ordering
-----------------------------------------------------------------
  1. Customer scans QR code on Table 4 → opens web app.

  2. App calls GET /api/v1/tables/{qr_token}/menu  (no JWT required).
       ├─ Tables module: decodes qr_code_token → validates Table row exists
       └─ Menu module: fetches all available MenuItem rows with categories
            └─ Returns PublicMenuOut (table_id, capacity, categories, items)

  3. Customer submits order via POST /api/v1/orders/
       ├─ Payload includes table_id (auto-tagged from QR scan) + order_type=Dine-In
       ├─ Order is committed with waiter_id (or null for self-service future flow)
       └─ Kitchen WebSocket broadcast fires immediately — no staff intervention needed

Reservations cross-module integration:
  POST /tables/reservations
    └─ After DB commit: send_reservation_confirmation.delay(reservation.id)
         └─ Celery background task sends email/SMS to the customer
"""
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import RequireAdmin, RequireWaiter, get_current_tenant, get_current_user
from app.database import get_db
from app.models import Category, MenuItem, Reservation, Table, Tenant, User
from app.schemas import (
    PublicMenuOut, ReservationCreate, ReservationOut, ReservationUpdate,
    TableCreate, TableOut, TableUpdate,
)
from app.tasks import send_reservation_confirmation

router = APIRouter(prefix="/tables", tags=["Tables & Reservations"])


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[TableOut])
async def list_tables(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(Table).where(Table.tenant_id == tenant.id))
    return result.scalars().all()


@router.post("/", response_model=TableOut, status_code=status.HTTP_201_CREATED)
async def create_table(
    payload: TableCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    token = payload.qr_code_token or secrets.token_urlsafe(24)
    table = Table(tenant_id=tenant.id, capacity=payload.capacity, qr_code_token=token)
    db.add(table)
    await db.flush()
    await db.refresh(table)
    return table


@router.post("/generate-token", response_model=dict)
async def generate_qr_token(_: Annotated[User, RequireAdmin]) -> dict:
    """Generate a unique QR code token for assignment to a new table."""
    return {"qr_code_token": secrets.token_urlsafe(24)}


@router.patch("/{table_id}", response_model=TableOut)
async def update_table(
    table_id: int,
    payload: TableUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireWaiter],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(Table).where(Table.id == table_id, Table.tenant_id == tenant.id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(table, field, value)
    await db.flush()
    await db.refresh(table)
    return table


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(Table).where(Table.id == table_id, Table.tenant_id == tenant.id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    await db.delete(table)


# ---------------------------------------------------------------------------
# Public QR menu — no auth required
# ---------------------------------------------------------------------------

@router.get("/{qr_token}/menu", response_model=PublicMenuOut, tags=["Public"])
async def get_table_menu(qr_token: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Public endpoint scanned by customers via table QR code.
    Returns the full available menu grouped with table context.
    No JWT required.
    """
    result = await db.execute(select(Table).where(Table.qr_code_token == qr_token))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid QR code")

    categories_result = await db.execute(select(Category).where(Category.tenant_id == table.tenant_id))
    categories = categories_result.scalars().all()

    items_result = await db.execute(
        select(MenuItem)
        .options(selectinload(MenuItem.category))
        .where(MenuItem.tenant_id == table.tenant_id, MenuItem.is_available.is_(True))
    )
    items = items_result.scalars().all()

    return PublicMenuOut(
        table_id=table.id,
        table_capacity=table.capacity,
        categories=categories,
        items=items,
    )


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------

@router.get("/reservations", response_model=list[ReservationOut])
async def list_reservations(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    result = await db.execute(select(Reservation).where(Reservation.tenant_id == tenant.id))
    return result.scalars().all()


@router.post("/reservations", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    payload: ReservationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireWaiter],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    tbl_r = await db.execute(select(Table).where(Table.id == payload.table_id, Table.tenant_id == tenant.id))
    if not tbl_r.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    reservation = Reservation(tenant_id=tenant.id, **payload.model_dump())
    db.add(reservation)
    await db.flush()
    await db.refresh(reservation)
    send_reservation_confirmation.delay(reservation.id)
    return reservation


@router.patch("/reservations/{res_id}", response_model=ReservationOut)
async def update_reservation(
    res_id: int,
    payload: ReservationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireWaiter],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    res_r = await db.execute(select(Reservation).where(Reservation.id == res_id, Reservation.tenant_id == tenant.id))
    reservation = res_r.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(reservation, field, value)
    await db.flush()
    await db.refresh(reservation)
    return reservation


@router.delete("/reservations/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation(
    res_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireAdmin],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    res_r = await db.execute(select(Reservation).where(Reservation.id == res_id, Reservation.tenant_id == tenant.id))
    reservation = res_r.scalar_one_or_none()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    await db.delete(reservation)
