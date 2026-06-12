import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, FetchedValue, Integer, Numeric,
    String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SubscriptionPlan(str, enum.Enum):
    Free       = "Free"
    Basic      = "Basic"
    Pro        = "Pro"
    Enterprise = "Enterprise"


class SubscriptionStatus(str, enum.Enum):
    Trialing  = "Trialing"
    Active    = "Active"
    PastDue   = "PastDue"
    Cancelled = "Cancelled"
    Expired   = "Expired"


class UserRole(str, enum.Enum):
    Admin = "Admin"
    Cashier = "Cashier"
    Waiter = "Waiter"
    Chef = "Chef"


class TableStatus(str, enum.Enum):
    Empty = "Empty"
    Occupied = "Occupied"
    Reserved = "Reserved"


class ReservationStatus(str, enum.Enum):
    Pending = "Pending"
    Confirmed = "Confirmed"
    Cancelled = "Cancelled"


class OrderStatus(str, enum.Enum):
    Pending = "Pending"
    Preparing = "Preparing"
    Ready = "Ready"
    Delivered = "Delivered"
    Cancelled = "Cancelled"


class OrderType(str, enum.Enum):
    DineIn = "Dine-In"
    Takeaway = "Takeaway"
    Delivery = "Delivery"


class DiscountType(str, enum.Enum):
    Percentage = "Percentage"
    FixedAmount = "FixedAmount"


class PaymentMethod(str, enum.Enum):
    Cash = "Cash"
    Card = "Card"
    Online = "Online"


class StockUnit(str, enum.Enum):
    KG = "KG"
    Liters = "Liters"
    Pieces = "Pieces"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Tenant(Base):
    """
    SaaS root entity — every restaurant is one Tenant.
    All other models carry a tenant_id FK for row-level data isolation.
    """
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    subdomain: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan), default=SubscriptionPlan.Free, nullable=False
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.Trialing, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
    categories: Mapped[list["Category"]] = relationship("Category", back_populates="tenant")
    menu_items: Mapped[list["MenuItem"]] = relationship("MenuItem", back_populates="tenant")
    tables: Mapped[list["Table"]] = relationship("Table", back_populates="tenant")
    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="tenant")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="tenant")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="tenant")
    inventory: Mapped[list["Inventory"]] = relationship("Inventory", back_populates="tenant")
    coupons: Mapped[list["DiscountCoupon"]] = relationship("DiscountCoupon", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="waiter")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="categories")
    menu_items: Mapped[list["MenuItem"]] = relationship("MenuItem", back_populates="category")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(512))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="menu_items")
    category: Mapped["Category"] = relationship("Category", back_populates="menu_items")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="menu_item")
    recipe_items: Mapped[list["RecipeItem"]] = relationship("RecipeItem", back_populates="menu_item")


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TableStatus] = mapped_column(Enum(TableStatus), default=TableStatus.Empty, nullable=False)
    qr_code_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="tables")
    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="table")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="table")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False)
    reservation_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus), default=ReservationStatus.Pending, nullable=False
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="reservations")
    table: Mapped["Table"] = relationship("Table", back_populates="reservations")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    table_id: Mapped[int | None] = mapped_column(ForeignKey("tables.id"), nullable=True)
    waiter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.Pending, nullable=False)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), default=OrderType.DineIn, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        server_onupdate=FetchedValue(),
        nullable=False,
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="orders")
    table: Mapped["Table | None"] = relationship("Table", back_populates="orders")
    waiter: Mapped["User | None"] = relationship("User", back_populates="orders")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    invoice: Mapped["Invoice | None"] = relationship("Invoice", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    special_notes: Mapped[str | None] = mapped_column(Text)
    ordered_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="order_items")


class DiscountCoupon(Base):
    __tablename__ = "discount_coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    discount_type: Mapped[DiscountType] = mapped_column(Enum(DiscountType), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="coupons")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="coupon")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    coupon_id: Mapped[int | None] = mapped_column(ForeignKey("discount_coupons.id"), nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="invoices")
    order: Mapped["Order"] = relationship("Order", back_populates="invoice")
    coupon: Mapped["DiscountCoupon | None"] = relationship("DiscountCoupon", back_populates="invoices")


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    ingredient_name: Mapped[str] = mapped_column(String(128), nullable=False)
    current_stock: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[StockUnit] = mapped_column(Enum(StockUnit), nullable=False)
    min_alert_level: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="inventory")
    recipe_items: Mapped[list["RecipeItem"]] = relationship("RecipeItem", back_populates="ingredient")


class RecipeItem(Base):
    """
    Maps a MenuItem to an Inventory ingredient with the quantity consumed per one unit sold.
    Example: MenuItem 'Cheeseburger' → Inventory 'Beef'  required_quantity=0.150 (kg)
             MenuItem 'Cheeseburger' → Inventory 'Bun'   required_quantity=1.000 (Pieces)
             MenuItem 'Cheeseburger' → Inventory 'Cheese' required_quantity=1.000 (Pieces)
    """
    __tablename__ = "recipe_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"), nullable=False, index=True)
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)

    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="recipe_items")
    ingredient: Mapped["Inventory"] = relationship("Inventory", back_populates="recipe_items")
