from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models import DiscountType, OrderStatus, OrderType, PaymentMethod
from app.schemas.menu import CategoryOut, MenuItemOut


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., gt=0)
    special_notes: Optional[str] = None


class OrderItemUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, gt=0)
    special_notes: Optional[str] = None


class OrderItemOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    menu_item_id: int
    quantity: int
    special_notes: Optional[str]
    ordered_price: Decimal
    menu_item: MenuItemOut


class OrderCreate(BaseModel):
    table_id: Optional[int] = None
    order_type: OrderType = OrderType.DineIn
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderItemsUpdate(BaseModel):
    add_items: list[OrderItemCreate] = Field(default_factory=list)
    update_items: dict[int, OrderItemUpdate] = Field(default_factory=dict)
    remove_item_ids: list[int] = Field(default_factory=list)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    table_id: Optional[int]
    waiter_id: Optional[int]
    status: OrderStatus
    order_type: OrderType
    created_at: datetime
    updated_at: datetime
    order_items: list[OrderItemOut]


class CouponCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=64)
    discount_type: DiscountType
    value: Decimal = Field(..., gt=0)
    expiry_date: Optional[datetime] = None
    is_active: bool = True


class CouponUpdate(BaseModel):
    is_active: Optional[bool] = None
    expiry_date: Optional[datetime] = None
    value: Optional[Decimal] = Field(default=None, gt=0)


class CouponOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    code: str
    discount_type: DiscountType
    value: Decimal
    expiry_date: Optional[datetime]
    is_active: bool


class InvoicePreview(BaseModel):
    order_id: int
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    coupon_code: Optional[str]
    coupon_applied: bool


class InvoiceSettle(BaseModel):
    coupon_code: Optional[str] = None
    payment_method: PaymentMethod


class InvoiceOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    order_id: int
    subtotal: Decimal
    tax_amount: Decimal
    coupon_id: Optional[int]
    discount_amount: Decimal
    total_amount: Decimal
    payment_method: PaymentMethod
    paid_at: Optional[datetime]
