from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models import StockUnit


class InventoryCreate(BaseModel):
    ingredient_name: str = Field(..., min_length=1, max_length=128)
    current_stock: Decimal = Field(..., ge=0)
    unit: StockUnit
    min_alert_level: Decimal = Field(..., ge=0)


class InventoryUpdate(BaseModel):
    current_stock: Optional[Decimal] = Field(default=None, ge=0)
    min_alert_level: Optional[Decimal] = Field(default=None, ge=0)
    unit: Optional[StockUnit] = None


class InventoryRestock(BaseModel):
    quantity_to_add: Decimal = Field(..., gt=0)


class InventoryOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    ingredient_name: str
    current_stock: Decimal
    unit: StockUnit
    min_alert_level: Decimal
    is_low_stock: bool = False

    @classmethod
    def from_model(cls, obj) -> "InventoryOut":
        return cls(
            id=obj.id,
            ingredient_name=obj.ingredient_name,
            current_stock=obj.current_stock,
            unit=obj.unit,
            min_alert_level=obj.min_alert_level,
            is_low_stock=obj.current_stock < obj.min_alert_level,
        )


class RecipeItemCreate(BaseModel):
    menu_item_id: int
    ingredient_id: int
    required_quantity: Decimal = Field(..., gt=0)


class RecipeItemOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    menu_item_id: int
    ingredient_id: int
    required_quantity: Decimal


class SalesReport(BaseModel):
    period_start: datetime
    period_end: datetime
    total_revenue: Decimal
    total_invoices: int
    average_order_value: Decimal


class TopMenuItem(BaseModel):
    menu_item_id: int
    name: str
    total_quantity_ordered: int
    total_revenue: Decimal


class DailySales(BaseModel):
    date: str
    revenue: Decimal
    invoice_count: int
