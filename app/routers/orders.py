"""
Orders Router  —  Layer 1: API / Presentation Layer
====================================================
Entry point for all order-related HTTP traffic on /api/v1/orders.

Layer responsibilities:
  - Listens to HTTP verbs (POST, GET, PATCH, DELETE) on specific URL patterns.
  - Delegates JWT verification and RBAC to the Security Middleware layer (auth.py).
  - Validates incoming request payloads via Pydantic schemas (OrderCreate,
    OrderStatusUpdate, OrderItemsUpdate) before any business logic executes.
  - Calls the Service / notification layer for WebSocket dispatch.
  - Returns serialised Pydantic response models to the client.

Order lifecycle data flow (Phase A → C):

  Phase A — Order Placement:
    POST /orders/
      ├─ JWT check  (auth.py → RequireWaiter)
      ├─ Pydantic validation  (OrderCreate schema)
      ├─ Per-item price lock  (menu_item.price → OrderItem.ordered_price)
      ├─ DB commit  (AsyncSession.flush)
      └─ WebSocket dispatch  → notify_kitchen(order.id)

  Phase B — Kitchen Dispatch:
    notify_kitchen() → ConnectionManager.broadcast_kitchen()
      └─ Pushes {event: "new_order", order_id} to all /ws/kitchen connections

  Phase C — Ready Notification:
    PATCH /orders/{id}/status  (Preparing → Ready)
      └─ notify_waiter(order.id, waiter_id)
           └─ Pushes {event: "order_ready"} to the specific waiter's device only
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from redis.asyncio import Redis

from app.auth import RequireChef, RequireWaiter, get_current_tenant, get_current_user
from app.database import get_db
from app.dependencies import get_redis
from app.models import MenuItem, Order, OrderItem, OrderStatus, Table, TableStatus, Tenant, User, UserRole
from app.schemas import OrderCreate, OrderItemsUpdate, OrderOut, OrderStatusUpdate
from app.services.cache import evict_active_orders, get_cached_active_orders, set_cached_active_orders
from app.services.notification import notify_kitchen, notify_waiter

router = APIRouter(prefix="/orders", tags=["Orders"])

_ORDER_LOAD = [
    selectinload(Order.order_items).selectinload(OrderItem.menu_item).selectinload(MenuItem.category)
]


async def _get_order_or_404(db: AsyncSession, order_id: int, tenant_id: int) -> Order:
    result = await db.execute(
        select(Order).options(*_ORDER_LOAD).where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.get("/", response_model=list[OrderOut])
async def list_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    order_status: OrderStatus | None = None,
):
    query = select(Order).options(*_ORDER_LOAD).where(Order.tenant_id == tenant.id)
    if order_status:
        query = query.where(Order.status == order_status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/active", response_model=list[OrderOut])
async def list_active_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    """
    Role-filtered active orders:
    - Chef: Pending + Preparing (kitchen queue)
    - Waiter: Ready (items to collect and deliver)
    - Cashier / Admin: all non-terminal orders

    Cache strategy:
      1. Try Redis cache first (key: active_orders:<role>, TTL 30s)
      2. On miss: query PostgreSQL, populate cache
      3. Cache is evicted immediately on any order state change
    """
    role_key = current_user.role.value

    cached = await get_cached_active_orders(redis, role_key, tenant.id)
    if cached is not None:
        return cached

    if current_user.role == UserRole.Chef:
        active_statuses = [OrderStatus.Pending, OrderStatus.Preparing]
    elif current_user.role == UserRole.Waiter:
        active_statuses = [OrderStatus.Ready]
    else:
        active_statuses = [OrderStatus.Pending, OrderStatus.Preparing, OrderStatus.Ready]

    query = select(Order).options(*_ORDER_LOAD).where(
        Order.tenant_id == tenant.id, Order.status.in_(active_statuses)
    )
    result = await db.execute(query)
    orders = result.scalars().all()

    serialised = [OrderOut.model_validate(o).model_dump(mode="json") for o in orders]
    await set_cached_active_orders(redis, role_key, tenant.id, serialised)

    return orders


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    return await _get_order_or_404(db, order_id, tenant.id)


@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, RequireWaiter],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    if payload.table_id:
        result = await db.execute(select(Table).where(Table.id == payload.table_id, Table.tenant_id == tenant.id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    order = Order(
        tenant_id=tenant.id,
        table_id=payload.table_id,
        waiter_id=current_user.id,
        order_type=payload.order_type,
    )
    db.add(order)
    await db.flush()

    for item_data in payload.items:
        mi_result = await db.execute(select(MenuItem).where(MenuItem.id == item_data.menu_item_id, MenuItem.tenant_id == tenant.id))
        menu_item = mi_result.scalar_one_or_none()
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MenuItem id={item_data.menu_item_id} not found",
            )
        if not menu_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{menu_item.name}' is currently unavailable",
            )
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=item_data.quantity,
            special_notes=item_data.special_notes,
            ordered_price=menu_item.price,
        )
        db.add(order_item)

    if payload.table_id:
        table = await db.get(Table, payload.table_id)
        if table:
            table.status = TableStatus.Occupied

    await db.flush()
    await notify_kitchen(order.id)
    await evict_active_orders(redis, tenant.id)

    return await _get_order_or_404(db, order.id, tenant.id)


@router.patch("/{order_id}/items", response_model=OrderOut)
async def update_order_items(
    order_id: int,
    payload: OrderItemsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, RequireWaiter],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    """
    Waiter-only: modify an open ticket while it is still Pending.
    - add_items: append new dishes to the order
    - update_items: {order_item_id: {quantity, special_notes}}
    - remove_item_ids: delete specific line items by their id
    """
    order = await _get_order_or_404(db, order_id, tenant.id)
    if order.status != OrderStatus.Pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Pending orders can be modified",
        )

    for item_id in payload.remove_item_ids:
        result = await db.execute(
            select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OrderItem id={item_id} not found on this order",
            )
        await db.delete(item)

    for item_id, update_data in payload.update_items.items():
        result = await db.execute(
            select(OrderItem).where(OrderItem.id == int(item_id), OrderItem.order_id == order_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OrderItem id={item_id} not found on this order",
            )
        for field, value in update_data.model_dump(exclude_none=True).items():
            setattr(item, field, value)

    for item_data in payload.add_items:
        mi_r = await db.execute(select(MenuItem).where(MenuItem.id == item_data.menu_item_id, MenuItem.tenant_id == tenant.id))
        menu_item = mi_r.scalar_one_or_none()
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MenuItem id={item_data.menu_item_id} not found",
            )
        if not menu_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{menu_item.name}' is currently unavailable",
            )
        db.add(OrderItem(
            order_id=order_id,
            menu_item_id=menu_item.id,
            quantity=item_data.quantity,
            special_notes=item_data.special_notes,
            ordered_price=menu_item.price,
        ))

    await db.flush()
    return await _get_order_or_404(db, order_id, tenant.id)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    """Cancel an order. Only allowed while status is still Pending."""
    result = await db.execute(select(Order).where(Order.id == order_id, Order.tenant_id == tenant.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != OrderStatus.Pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Pending orders can be cancelled via DELETE. Use PATCH /status for other transitions.",
        )
    order.status = OrderStatus.Cancelled
    await evict_active_orders(redis, tenant.id)


# ---------------------------------------------------------------------------
# Order status transitions
# ---------------------------------------------------------------------------

# Cancellation Guard Rule: Cancelled is NOT reachable via PATCH /status.
# The only path to Cancelled is DELETE /orders/{id} (Pending only).
VALID_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.Pending:   [OrderStatus.Preparing],
    OrderStatus.Preparing: [OrderStatus.Ready],
    OrderStatus.Ready:     [OrderStatus.Delivered],
    OrderStatus.Delivered: [],
    OrderStatus.Cancelled: [],
}

# Which roles may drive each transition.
_TRANSITION_ROLES: dict[tuple[OrderStatus, OrderStatus], list[UserRole]] = {
    (OrderStatus.Pending,   OrderStatus.Preparing): [UserRole.Chef,   UserRole.Admin],
    (OrderStatus.Preparing, OrderStatus.Ready):     [UserRole.Chef,   UserRole.Admin],
    (OrderStatus.Ready,     OrderStatus.Delivered): [UserRole.Waiter, UserRole.Cashier, UserRole.Admin],
}


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    order = await _get_order_or_404(db, order_id, tenant.id)

    allowed = VALID_TRANSITIONS.get(order.status, [])
    if payload.status not in allowed:
        if payload.status == OrderStatus.Cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use DELETE /orders/{id} to cancel a Pending order.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{order.status.value}' to '{payload.status.value}'.",
        )

    transition_key = (order.status, payload.status)
    permitted_roles = _TRANSITION_ROLES.get(transition_key, [])
    if current_user.role not in permitted_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Role '{current_user.role.value}' cannot move an order from "
                f"'{order.status.value}' to '{payload.status.value}'. "
                f"Required: {[r.value for r in permitted_roles]}"
            ),
        )

    order.status = payload.status
    await db.flush()
    await evict_active_orders(redis, tenant.id)

    if payload.status == OrderStatus.Ready:
        await notify_waiter(order.id, order.waiter_id)

    if payload.status == OrderStatus.Delivered and order.table_id:
        table = await db.get(Table, order.table_id)
        if table:
            table.status = TableStatus.Empty

    return await _get_order_or_404(db, order_id, tenant.id)
