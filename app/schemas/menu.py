from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models import TableStatus, ReservationStatus


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CategoryOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    description: Optional[str]


class MenuItemCreate(BaseModel):
    category_id: int
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    image_url: Optional[str] = None
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None


class MenuItemOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    category_id: int
    name: str
    description: Optional[str]
    price: Decimal
    image_url: Optional[str]
    is_available: bool
    category: CategoryOut


class TableCreate(BaseModel):
    capacity: int = Field(..., gt=0)
    qr_code_token: str = Field(..., min_length=8)


class TableUpdate(BaseModel):
    capacity: Optional[int] = Field(default=None, gt=0)
    status: Optional[TableStatus] = None
    qr_code_token: Optional[str] = None


class TableOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    capacity: int
    status: TableStatus
    qr_code_token: str


class PublicMenuOut(BaseModel):
    table_id: int
    table_capacity: int
    categories: list[CategoryOut]
    items: list[MenuItemOut]


from datetime import datetime


class ReservationCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=128)
    customer_phone: str
    table_id: int
    reservation_datetime: datetime


class ReservationUpdate(BaseModel):
    status: Optional[ReservationStatus] = None
    reservation_datetime: Optional[datetime] = None


class ReservationOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    customer_name: str
    customer_phone: str
    table_id: int
    reservation_datetime: datetime
    status: ReservationStatus
