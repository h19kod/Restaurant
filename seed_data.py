"""
Seed script to insert initial demo data into the database.
Run this after the database is created.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import (
    Tenant, User, Category, MenuItem, Table, Inventory, RecipeItem,
    SubscriptionPlan, SubscriptionStatus, UserRole, TableStatus, StockUnit
)
from app.auth import hash_password
from app.config import settings

async_engine = create_async_engine(
    "sqlite+aiosqlite:///./restaurant.db",
    echo=False,
)

AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def seed():
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        result = await db.execute(select(Tenant).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            print("Database already seeded!")
            return

        # Create tenant
        tenant = Tenant(
            name="Star Restaurant",
            subdomain="star",
            plan=SubscriptionPlan.Free,
            subscription_status=SubscriptionStatus.Trialing,
            is_active=True,
        )
        db.add(tenant)
        await db.flush()
        print(f"Created tenant: ID {tenant.id}")

        # Create users
        users_data = [
            ("admin", "admin123", "System Administrator", UserRole.Admin),
            ("cashier", "cashier123", "Cashier Ahmed", UserRole.Cashier),
            ("waiter", "waiter123", "Waiter Khaled", UserRole.Waiter),
            ("chef", "chef123", "Chef Mohamed", UserRole.Chef),
        ]

        for username, password, full_name, role in users_data:
            user = User(
                tenant_id=tenant.id,
                username=username,
                password_hash=hash_password(password),
                full_name=full_name,
                role=role,
                is_active=True,
            )
            db.add(user)

        await db.flush()
        print(f"Created {len(users_data)} users")

        # Create categories
        categories_data = [
            ("Appetizers", "Starters and small dishes"),
            ("Main Courses", "Primary dishes"),
            ("Desserts", "Sweet dishes"),
            ("Beverages", "Drinks"),
        ]

        categories = []
        for name, desc in categories_data:
            cat = Category(
                tenant_id=tenant.id,
                name=name,
                description=desc,
            )
            db.add(cat)
            categories.append(cat)

        await db.flush()
        print(f"Created {len(categories)} categories")

        # Create menu items
        menu_items_data = [
            ("Chicken Burger", categories[0].id, 35.00, True),
            ("Beef Steak", categories[1].id, 85.00, True),
            ("Margherita Pizza", categories[1].id, 45.00, True),
            ("Caesar Salad", categories[0].id, 28.00, True),
            ("Chocolate Cake", categories[2].id, 25.00, True),
            ("Fresh Juice", categories[3].id, 15.00, True),
        ]

        for name, cat_id, price, available in menu_items_data:
            item = MenuItem(
                tenant_id=tenant.id,
                category_id=cat_id,
                name=name,
                description=f"Delicious {name}",
                price=price,
                is_available=available,
            )
            db.add(item)

        await db.flush()
        print(f"Created {len(menu_items_data)} menu items")

        # Create tables
        for i in range(1, 11):
            table = Table(
                tenant_id=tenant.id,
                capacity=4 if i <= 6 else 6,
                status=TableStatus.Empty,
                qr_code_token=f"table-token-{i}",
            )
            db.add(table)

        await db.flush()
        print("Created 10 tables")

        # Create inventory items
        inventory_data = [
            ("Chicken Breast", StockUnit.KG, 50.0, 10.0),
            ("Beef Meat", StockUnit.KG, 30.0, 5.0),
            ("Bread", StockUnit.Pieces, 100.0, 20.0),
            ("Cheese", StockUnit.KG, 15.0, 3.0),
            ("Tomatoes", StockUnit.KG, 40.0, 8.0),
            ("Lettuce", StockUnit.KG, 20.0, 5.0),
            ("Flour", StockUnit.KG, 100.0, 20.0),
            ("Sugar", StockUnit.KG, 50.0, 10.0),
        ]

        for name, unit, stock, min_level in inventory_data:
            inv = Inventory(
                tenant_id=tenant.id,
                ingredient_name=name,
                unit=unit,
                current_stock=stock,
                min_alert_level=min_level,
            )
            db.add(inv)

        await db.flush()
        print(f"Created {len(inventory_data)} inventory items")

        await db.commit()
        print("\n✅ Seed data inserted successfully!")
        print("\nLogin credentials:")
        print("  admin / admin123")
        print("  cashier / cashier123")
        print("  waiter / waiter123")
        print("  chef / chef123")


if __name__ == "__main__":
    asyncio.run(seed())
