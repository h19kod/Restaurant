"""saas multi tenancy stripe

Revision ID: 0001
Revises:
Create Date: 2026-06-12

Full initial schema for the SaaS multi-tenant restaurant management system.
Creates all tables with tenant_id foreign keys for row-level data isolation.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # tenants
    # ------------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("subdomain", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column(
            "plan",
            sa.Enum("Free", "Basic", "Pro", "Enterprise", name="subscriptionplan"),
            nullable=False,
            server_default="Free",
        ),
        sa.Column(
            "subscription_status",
            sa.Enum("Trialing", "Active", "PastDue", "Cancelled", "Expired", name="subscriptionstatus"),
            nullable=False,
            server_default="Trialing",
        ),
        sa.Column("stripe_customer_id", sa.String(128), unique=True, nullable=True),
        sa.Column("stripe_subscription_id", sa.String(128), unique=True, nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("username", sa.String(64), nullable=False, index=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column(
            "role",
            sa.Enum("Admin", "Cashier", "Waiter", "Chef", name="userrole"),
            nullable=False,
        ),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # ------------------------------------------------------------------
    # categories
    # ------------------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # ------------------------------------------------------------------
    # menu_items
    # ------------------------------------------------------------------
    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # ------------------------------------------------------------------
    # tables
    # ------------------------------------------------------------------
    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("Empty", "Occupied", "Reserved", name="tablestatus"),
            nullable=False,
            server_default="Empty",
        ),
        sa.Column("qr_code_token", sa.String(128), nullable=False, unique=True),
    )

    # ------------------------------------------------------------------
    # reservations
    # ------------------------------------------------------------------
    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("customer_name", sa.String(128), nullable=False),
        sa.Column("customer_phone", sa.String(32), nullable=False),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id"), nullable=False),
        sa.Column("reservation_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("Pending", "Confirmed", "Cancelled", name="reservationstatus"),
            nullable=False,
            server_default="Pending",
        ),
    )

    # ------------------------------------------------------------------
    # orders
    # ------------------------------------------------------------------
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id"), nullable=True),
        sa.Column("waiter_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "status",
            sa.Enum("Pending", "Preparing", "Ready", "Delivered", "Cancelled", name="orderstatus"),
            nullable=False,
            server_default="Pending",
        ),
        sa.Column(
            "order_type",
            sa.Enum("Dine-In", "Takeaway", "Delivery", name="ordertype"),
            nullable=False,
            server_default="Dine-In",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ------------------------------------------------------------------
    # order_items
    # ------------------------------------------------------------------
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("special_notes", sa.Text(), nullable=True),
        sa.Column("ordered_price", sa.Numeric(10, 2), nullable=False),
    )

    # ------------------------------------------------------------------
    # discount_coupons
    # ------------------------------------------------------------------
    op.create_table(
        "discount_coupons",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("code", sa.String(64), nullable=False, index=True),
        sa.Column(
            "discount_type",
            sa.Enum("Percentage", "FixedAmount", name="discounttype"),
            nullable=False,
        ),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_coupon_tenant_code"),
    )

    # ------------------------------------------------------------------
    # invoices
    # ------------------------------------------------------------------
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False, unique=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("coupon_id", sa.Integer(), sa.ForeignKey("discount_coupons.id"), nullable=True),
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "payment_method",
            sa.Enum("Cash", "Card", "Online", name="paymentmethod"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------
    # inventory
    # ------------------------------------------------------------------
    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("ingredient_name", sa.String(128), nullable=False),
        sa.Column("current_stock", sa.Numeric(10, 3), nullable=False),
        sa.Column(
            "unit",
            sa.Enum("KG", "Liters", "Pieces", name="stockunit"),
            nullable=False,
        ),
        sa.Column("min_alert_level", sa.Numeric(10, 3), nullable=False),
    )

    # ------------------------------------------------------------------
    # recipe_items
    # ------------------------------------------------------------------
    op.create_table(
        "recipe_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=False, index=True),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("inventory.id"), nullable=False, index=True),
        sa.Column("required_quantity", sa.Numeric(10, 3), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("recipe_items")
    op.drop_table("inventory")
    op.drop_table("invoices")
    op.drop_table("discount_coupons")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("reservations")
    op.drop_table("tables")
    op.drop_table("menu_items")
    op.drop_table("categories")
    op.drop_table("users")
    op.drop_table("tenants")
    # Drop custom enum types
    for name in [
        "subscriptionplan", "subscriptionstatus", "userrole", "tablestatus",
        "reservationstatus", "orderstatus", "ordertype", "discounttype",
        "paymentmethod", "stockunit",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
