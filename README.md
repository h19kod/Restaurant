# Restaurant Management System — Backend API

A production-ready, fully asynchronous **FastAPI** backend for a complete restaurant management platform. Handles real-time kitchen alerts via WebSockets, dynamic QR menus, RBAC-secured staff workflows, financial invoice aggregation, and background inventory management via Celery.

---

## System Architecture

### The 4-Layer Component Model

Data flows sequentially through four independent layers, maximising security, modularity, and testability:

```
[Client Request]
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — API Router / Presentation Layer                  │
│  • Listens to HTTP verbs on /api/v1/* URL routes            │
│  • Pydantic schemas validate every payload before execution  │
│  • Delegates auth to the Security Middleware (auth.py)       │
│  Files: routers/orders.py, billing.py, menu.py, ...         │
└─────────────────────┬───────────────────────────────────────┘
                      │  validated data objects
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  SECURITY MIDDLEWARE (Cross-cutting)                        │
│  • Decodes JWT, verifies HS256 signature + expiry           │
│  • Loads live User row, cross-checks username + role claims  │
│  • require_roles() → HTTP 403 on unauthorized access        │
│  File: auth.py                                              │
└─────────────────────┬───────────────────────────────────────┘
                      │  authenticated User object
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — Service / Business Logic Layer                   │
│  • Knows nothing about HTTP — pure restaurant business rules │
│  • Calculates taxes, validates coupons, enforces order       │
│    workflow state machine, locks historical prices           │
│  • Fires WebSocket events and dispatches Celery tasks        │
│  Files: services/notification.py, services/stock_manager.py │
│         _compute_invoice_figures() in billing.py            │
└─────────────────────┬───────────────────────────────────────┘
                      │  Python model objects
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — Data Access / ORM Layer                          │
│  • SQLAlchemy AsyncSession translates Python objects to SQL  │
│  • Handles relationships, eager loading, index optimisation  │
│  • Alembic manages schema migrations non-destructively       │
│  Files: models.py, database.py, alembic/                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
               [ PostgreSQL ]

┌─────────────────────────────────────────────────────────────┐
│  LAYER 4 — Background & Real-Time Worker Layer              │
│                                                             │
│  WebSocket Manager (synchronous, in-process)                │
│  • ConnectionManager maintains open channels to devices     │
│  • Broadcast pool for kitchen screens (all devices)         │
│  • Targeted pool for waiter tablets (by waiter_id)          │
│                                                             │
│  Celery Worker (async, separate process via Redis)          │
│  • Inventory deduction using RecipeItem mappings            │
│  • Low-stock alerts when stock < min_alert_level            │
│  • Reservation emails and nightly sales reports             │
│  Files: tasks.py, celery_app.py, services/notification.py   │
└─────────────────────────────────────────────────────────────┘
```

---

### Full Order Lifecycle Data Flow

#### Phase A — Order Placement (Ingestion)
```
Waiter App  →  POST /api/v1/orders/
                 │
                 ├─ 1. JWT decoded → RequireWaiter RBAC check
                 ├─ 2. Pydantic OrderCreate validates payload structure
                 ├─ 3. Service layer: per-item DB query → price snapshot
                 │      menu_item.price  ──▶  OrderItem.ordered_price  (locked)
                 ├─ 4. Order + OrderItems committed to PostgreSQL
                 └─ 5. notify_kitchen(order.id) fired immediately
```

#### Phase B — Real-Time Kitchen Dispatch
```
notify_kitchen(order_id)
  └─ ConnectionManager.broadcast_kitchen()
       └─ JSON push to ALL /ws/kitchen connected devices
            {"event": "new_order", "order_id": 42}
            ← Ticket appears on chef's screen in milliseconds
               No refresh, no polling
```

#### Phase C — Cooking & Waiter Notification
```
Chef UI  →  PATCH /api/v1/orders/{id}/status  {status: "Ready"}
               │
               ├─ Workflow engine: Preparing → Ready  ✓
               ├─ RequireChef RBAC check  ✓
               ├─ OrderStatus updated in PostgreSQL
               └─ notify_waiter(order_id, waiter_id)
                    └─ ConnectionManager.broadcast_waiter(waiter_id, ...)
                         └─ Private push ONLY to that waiter's device
                              {"event": "order_ready", "order_id": 42}
```

#### Phase D — Checkout, Invoicing & Background Inventory
```
Cashier App  →  POST /api/v1/billing/invoices/settle/{order_id}
                   │
                   ├─ RequireCashier RBAC check
                   ├─ Duplicate invoice guard (HTTP 409)
                   ├─ _compute_invoice_figures():
                   │     subtotal  =  Σ (OrderItem.ordered_price × quantity)
                   │     tax       =  subtotal × TAX_RATE
                   │     discount  =  coupon validation (expiry + type)
                   │     total     =  subtotal + tax − discount
                   ├─ Invoice committed to PostgreSQL (paid_at timestamped)
                   ├─ Table.status  →  Empty
                   │
                   ├─ print_receipt.delay(invoice.id)            ← Redis queue
                   └─ adjust_inventory_on_invoice.delay(invoice.id) ← Redis queue
                                │
                                │  (main thread returns response immediately)
                                │
                   ┌────────────▼─────────────────────────────────────┐
                   │  Celery Worker  (background, separate process)   │
                   │                                                   │
                   │  For each OrderItem in the invoice:              │
                   │    RecipeItem mappings  →  Inventory rows        │
                   │    current_stock -= required_quantity × qty      │
                   │                                                   │
                   │  If current_stock < min_alert_level:             │
                   │    Log warning + send low-stock alert email      │
                   └───────────────────────────────────────────────────┘
```

---

## Global Integration

### main.py — The Central Nervous System

`main.py` is the single file that binds all isolated modules under one application instance.

**Boot sequence:**
```
uvicorn starts
    │
    ├─ 1. lifespan() fires
    │       ├─ PostgreSQL engine pool initialised
    │       ├─ Redis client pool created → app.state.redis
    │       └─ WebSocket ConnectionManager ready (module-level singleton)
    │
    ├─ 2. CORSMiddleware mounted
    │       └─ Allows frontend (web/mobile) cross-origin requests
    │
    └─ 3. Router switchboard mounted under /api/v1
            ├─ /api/v1/auth      → auth module
            ├─ /api/v1/orders    → orders module + FSM + Redis cache
            ├─ /api/v1/billing   → billing module + Celery dispatch
            ├─ /api/v1/tables    → tables module + QR public menu
            ├─ /api/v1/inventory → inventory module + stock manager
            ├─ /api/v1/reports   → reports module
            ├─ /ws/kitchen       → WebSocket broadcast channel
            └─ /ws/waiter/{id}   → WebSocket targeted channel
```

### Request Lifecycle (Step-by-Step)

Exact mechanical steps when a Waiter submits a new order:

```
POST /api/v1/orders/  {items: [...], table_id: 4}
  │
  ├─ Step 1 — Middleware & Security
  │     oauth2_scheme extracts Bearer token from header
  │     get_current_user() → JWT decode → DB lookup → role check
  │     RequireWaiter: Chef/Cashier rejected with HTTP 403 here
  │
  ├─ Step 2 — Pydantic Validation
  │     OrderCreate schema validates payload:
  │       quantity must be int > 0, menu_item_id must be int, etc.
  │     Malformed payload → HTTP 422 returned, no DB touched
  │
  ├─ Step 3 — DB Session Injection
  │     Depends(get_db) carves one AsyncSession from the pool
  │     Session travels with the request through all downstream logic
  │
  ├─ Step 4 — Service Layer Execution
  │     State Machine: order.status locked to Pending on creation
  │     Pricing Component: per-item DB query →
  │       menu_item.price copied → OrderItem.ordered_price (historical lock)
  │     Order + OrderItems flushed to PostgreSQL
  │
  └─ Step 5 — Commit & Event Dispatching
        AsyncSession commits transaction to PostgreSQL
        ├─ notify_kitchen(order.id)
        │     └─ WebSocket broadcast → kitchen screens (milliseconds)
        └─ evict_active_orders(redis)
              └─ Stale cache cleared; next GET /active re-queries DB
```

### Cross-Module Workflow Integration

#### Workflow A — QR-Code Customer Ordering
```
Customer scans QR on Table 4
  │
  ▼
GET /api/v1/tables/{qr_token}/menu           (no JWT — public)
  ├─ Tables module: qr_code_token → validates Table row
  └─ Menu module: fetches available items with categories
       └─ Returns PublicMenuOut {table_id, capacity, categories, items}

Customer places order:
POST /api/v1/orders/  {table_id: 4, order_type: "Dine-In", items: [...]}
  └─ table_id auto-tagged → Table.status → Occupied
     Kitchen WebSocket fires → no waiter physical intervention needed
```

#### Workflow B — Order Fulfillment & Real-Time Alerting
```
Chef UI: PATCH /api/v1/orders/{id}/status  {status: "Ready"}
  │
  ├─ Orders module FSM: Preparing → Ready  ✓  (validates transition + role)
  ├─ PostgreSQL updated
  ├─ evict_active_orders(redis)  ← waiter's next poll gets fresh state
  └─ notify_waiter(order_id, waiter_id)
       └─ ConnectionManager looks up waiter_id in _waiters pool
            └─ Private WebSocket push to that waiter's device only
                 {"event": "order_ready", "order_id": 42}
```

#### Workflow C — Settlement, Accounting & Stock Controls
```
Cashier: POST /api/v1/billing/invoices/settle/{order_id}
  │
  ├─ Billing module: subtotal + tax + coupon → Invoice committed
  ├─ Table.status → Empty
  │
  ├─ print_receipt.delay(invoice.id)            → Redis queue (non-blocking)
  └─ adjust_inventory_on_invoice.delay(invoice.id) → Redis queue (non-blocking)
       │
       │  Cashier receives HTTP 201 immediately ← main thread free
       │
       └─ Celery Worker (background):
            Inventory module:
              RecipeItem mappings → ingredient rows
              current_stock -= required_quantity × qty_sold
              current_stock < min_alert_level → log + email alert
```

---

## State Management

### 1. Application Lifecycle State (Lifespan Events)

Stateful global resources are initialised **once** at server boot and torn down cleanly on shutdown — managed by FastAPI's `lifespan` context in `app/main.py`.

| Event | What happens | File |
|---|---|---|
| **Startup** | PostgreSQL async engine pool created | `database.py` |
| **Startup** | Redis client pool created → attached to `app.state.redis` | `main.py` |
| **Startup** | WebSocket `ConnectionManager` ready (module-level singleton) | `services/notification.py` |
| **Shutdown** | `redis_client.aclose()` — drains Redis connection pool | `main.py` |
| **Shutdown** | `engine.dispose()` — closes all PostgreSQL pool connections | `main.py` |

### 2. Request-Level State (Dependency Injection)

Each HTTP request gets its own scoped resources, injected automatically by FastAPI:

| Dependency | Scope | Behaviour |
|---|---|---|
| `get_db()` | Per-request | Carves one `AsyncSession` from the pool; auto-commits on success, auto-rolls back on exception, closes on response |
| `get_redis()` | Per-request (shared client) | Returns the single `app.state.redis` instance — no new connection allocated |

### 3. Business Object State Machine (Order FSM)

The Order model implements a **Finite State Machine** enforced in `routers/orders.py`:

```
         ┌──────────────────────────────────────────┐
         │           ORDER STATE MACHINE             │
         │                                           │
         │   Pending ──► Preparing ──► Ready ──► Delivered
         │      │                                    (final)
         │      └──► Cancelled                       (final)
         │           (DELETE only; blocked after Preparing)
         │                                           │
         │   Three-step validation on every PATCH:  │
         │   1. Fetch current state from PostgreSQL │
         │   2. Check against VALID_TRANSITIONS map │
         │   3. Check role in _TRANSITION_ROLES map │
         └──────────────────────────────────────────┘
```

Any invalid transition raises `HTTP 400`; any unauthorised role raises `HTTP 403`.

### 4. Real-Time State Synchronisation

Every state change fires two side-effects immediately after the DB write:

```
[Staff triggers PATCH /orders/{id}/status]
         │
         ├─► DB write (order.status updated)
         │
         ├─► evict_active_orders(redis)        ← invalidates stale cache for all roles
         │
         └─► WebSocket broadcast (if status == Ready)
               └─ notify_waiter(order_id, waiter_id)
                    └─ private push to assigned waiter's device only
```

### 5. In-Memory State Cache (Redis)

Active orders are cached to protect PostgreSQL from high-frequency polling by kitchen and waiter devices:

| Operation | Cache behaviour |
|---|---|
| `GET /orders/active` | Read `active_orders:<role>` from Redis first; on miss → query PostgreSQL → populate cache (TTL 30s) |
| `POST /orders/` | `evict_active_orders()` — clears all `active_orders:*` keys |
| `PATCH /orders/{id}/status` | `evict_active_orders()` — ensures next read reflects new state |
| `DELETE /orders/{id}` | `evict_active_orders()` — removes cancelled order from cache |
| Redis down | Silent fallback — all operations degrade to direct PostgreSQL reads with no error thrown |

Cache implementation: `app/services/cache.py`

---

## 1. Core Technology Stack

### Web Framework — FastAPI
Built on **ASGI**, FastAPI handles concurrent connections seamlessly. This is essential for maintaining constant, open WebSocket channels for real-time kitchen and waiter updates without blocking the server. Powered by **Pydantic**, it automatically validates and structures every incoming data packet before it reaches business logic, and self-generates interactive Swagger documentation at `/docs`.

### Database Layer — PostgreSQL + SQLAlchemy + Alembic

| Component | Role |
|---|---|
| **PostgreSQL** | ACID-compliant relational database, ideal for interconnected financial transactions (`Orders → OrderItems → Invoices`) and heavy aggregate queries for sales trend reports |
| **SQLAlchemy 2 (async)** | Python ORM — translates class definitions into SQL queries using `AsyncSession` and `asyncpg` |
| **Alembic** | Migration engine — tracks model changes and modifies the live database schema without touching existing order histories |

### Worker & Communication — Redis + Celery + WebSockets

| Component | Role |
|---|---|
| **WebSockets** | Native to FastAPI — instant two-way data streaming. New orders flash on the chef's monitor immediately, no polling required |
| **Celery + Redis** | Offloads heavy background processing (inventory deduction, email confirmations, nightly P&L aggregation) from the main application thread |

---

## 2. Database Schema & Data Models

### Strict Data Enums

All status fields are locked to predefined states to prevent invalid data entry:

| Enum | Values |
|---|---|
| `UserRole` | `Admin`, `Cashier`, `Waiter`, `Chef` |
| `TableStatus` | `Empty`, `Occupied`, `Reserved` |
| `OrderStatus` | `Pending`, `Preparing`, `Ready`, `Delivered`, `Cancelled` |
| `OrderType` | `Dine-In`, `Takeaway`, `Delivery` |
| `DiscountType` | `Percentage`, `FixedAmount` |
| `PaymentMethod` | `Cash`, `Card`, `Online` |
| `StockUnit` | `KG`, `Liters`, `Pieces` |

### Relational Table Blueprint

| Entity | Description |
|---|---|
| **User** | Stores employee usernames, hashed passwords, full names, phone numbers, active status, and role. `1:N` relationship with Orders to track which waiter manages each ticket. |
| **Category** | Classification groups (e.g., Starters, Main Course, Drinks) that organise the menu layout. |
| **MenuItem** | Linked to `Category` via Foreign Key. Contains base price, description, image URL, and an availability toggle. |
| **Table** | Holds physical table number, guest capacity, current status, and a unique cryptographic `qr_code_token` for generating customer-facing QR menus. |
| **Reservation** | Maps a `Table` to a customer name, phone number, and target booking timestamp. |
| **Order** | Transactional parent container. Tracks creation time, last-modified time, current lifecycle status, and the assigned `Table` (nullable for Takeaway/Delivery). |
| **OrderItem** | Many-to-many bridge between `Order` and `MenuItem`. Tracks quantity, special notes (e.g., "No onions"), and **records a historical price lock** (`ordered_price`). If a manager raises a burger's price tomorrow, past invoices are never retroactively altered. |
| **DiscountCoupon** | Tracks promotional codes, discount type (percentage or fixed), expiry date, and active status. |
| **Invoice** | Strict `1:1` with a completed `Order`. Aggregates subtotal, calculates regional tax, applies coupon deductions, logs payment method, and timestamps the successful settlement. |
| **Inventory** | Monitors raw ingredient stockpiles (meat kg, vegetable pieces, dairy liters). Has a `min_alert_level` safety threshold that triggers a low-stock alert when supplies drop below the configured minimum. |
| **RecipeItem** | Maps each `MenuItem` to one or more `Inventory` ingredients with a `required_quantity` per unit sold. Used by the Celery task to automatically deduct stock on invoice settlement. |

### Entity Relationships

```
Category ──< MenuItem >──< RecipeItem >── Inventory
                │
User ──────── Order ──────< OrderItem
                │
             Table ──────< Reservation
                │
             Invoice ──── DiscountCoupon
```

---

## 3. Project Structure

```
app/
├── main.py                   # FastAPI app, CORS, /api/v1 router registration
├── config.py                 # Settings loaded from .env (pydantic-settings)
├── database.py               # Async engine, session factory, Base, get_db
├── models.py                 # All SQLAlchemy ORM models & Enums
├── auth.py                   # JWT lifecycle, bcrypt hashing, RBAC dependency factories
├── celery_app.py             # Celery instance, Redis broker, Beat schedule
├── tasks.py                  # Background tasks: inventory, receipts, emails, reports
├── websockets.py             # Backward-compat shim → services/notification.py
│
├── schemas/                  # Pydantic request/response schemas
│   ├── __init__.py           # Flat re-export of all schemas
│   ├── auth.py               # Token, UserCreate, UserOut, UserUpdate
│   ├── menu.py               # Category*, MenuItem*, Table*, Reservation*, PublicMenuOut
│   ├── orders.py             # Order*, OrderItem*, Coupon*, Invoice*
│   └── inventory.py          # Inventory*, RecipeItem*, SalesReport, TopMenuItem, DailySales
│
├── routers/                  # API route handlers
│   ├── auth.py               # POST /auth/login  POST /auth/register  GET /auth/me
│   ├── users.py              # CRUD /users  [Admin]
│   ├── menu.py               # CRUD /categories  CRUD /menu-items
│   ├── tables.py             # CRUD /tables  GET /tables/{token}/menu (public)
│   │                         #   CRUD /tables/reservations
│   ├── orders.py             # POST /orders  GET /orders/active
│   │                         #   PATCH /orders/{id}/status  PATCH /orders/{id}/items
│   │                         #   DELETE /orders/{id}
│   ├── billing.py            # POST /billing/invoices/preview/{id}
│   │                         #   POST /billing/invoices/settle/{id}
│   │                         #   GET  /billing/invoices  CRUD /billing/coupons
│   ├── inventory.py          # CRUD /inventory  PATCH /inventory/{id}/restock
│   │                         #   CRUD /inventory/recipes  [Admin]
│   └── reports.py            # GET /reports/sales/summary|daily  /items/trending  [Admin]
│
└── services/
    ├── notification.py       # WebSocket ConnectionManager + notify_kitchen/notify_waiter
    └── stock_manager.py      # Async inventory deduction via RecipeItem mappings

tests/
├── conftest.py               # SQLite in-memory fixtures, HTTP client, seed helpers
├── test_auth.py              # Login, register, RBAC, JWT validation
├── test_menu.py              # Category & MenuItem CRUD, availability filter
├── test_orders.py            # Workflow engine, cancellation guard, role-gating
├── test_billing.py           # Invoice preview/settle, coupon discounts, expiry
├── test_inventory.py         # CRUD, restock, low-stock flag, recipe mappings
├── test_tables.py            # Tables, QR public menu, reservation lifecycle
└── test_reports.py           # Sales summary, daily breakdown, trending items

Dockerfile
docker-compose.yml            # FastAPI + PostgreSQL + Redis + Celery Worker + Beat
Makefile                      # make run | test | migrate | docker-up
.env.example
requirements.txt
```

---

## 4. Setup & Database Initialization Lifecycle

### Step 1 — Environment Sync
```bash
cp .env.example .env
# Set DATABASE_URL, SYNC_DATABASE_URL, SECRET_KEY, TAX_RATE, REDIS_URL
```
The `config.py` reads all settings from `.env` via `pydantic-settings`. This is the **single source of truth** — both Alembic and the FastAPI app read from it.

### Step 2 — Install Dependencies
```bash
pip install -r requirements.txt
# or: make install
```

### Step 3 — Alembic Schema Upgrade
```bash
# Generate migration script (Alembic scans your Python models vs the empty DB)
alembic revision --autogenerate -m "initial schema"

# Execute: creates all tables, constraints, indexes, and foreign keys in PostgreSQL
alembic upgrade head
# or: make migrate
```

### Step 4 — Run the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# or: make run
```

### Step 5 — Start Background Workers
```bash
# Celery worker (inventory deduction, emails, receipts)
celery -A app.celery_app worker --loglevel=info
# or: make worker

# Celery Beat (nightly sales report)
celery -A app.celery_app beat --loglevel=info
# or: make beat
```

### One-Command Docker Setup
```bash
docker-compose up --build -d
# or: make docker-up
```
Starts PostgreSQL, Redis, FastAPI API, Celery Worker, and Celery Beat — all wired together with health checks.

---

## 5. API Reference (`/api/v1`)

| Module | Prefix | Access |
|---|---|---|
| Authentication | `/auth` | Public (login) / Admin (register) |
| Users | `/users` | Admin |
| Menu | `/categories`, `/menu-items` | Public GET / Admin write |
| Tables & Reservations | `/tables` | Public QR GET / Staff write |
| Orders | `/orders` | Waiter (create) / Role-filtered (read/update) |
| Billing | `/billing` | Cashier / Admin |
| Inventory & Recipes | `/inventory` | Admin |
| Reports | `/reports` | Admin |
| WebSockets | `ws://.../ws/kitchen`, `ws://.../ws/waiter/{id}` | Internal |

### Key Endpoints

| Method | URL | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Staff login → JWT (8-hour expiry) |
| `POST` | `/api/v1/auth/register` | Create staff account `[Admin]` |
| `GET` | `/api/v1/tables/{qr_token}/menu` | **Public** — customer QR scan → live menu |
| `POST` | `/api/v1/orders/` | Create order → instantly notifies kitchen WS |
| `GET` | `/api/v1/orders/active` | Role-filtered live order queue |
| `PATCH` | `/api/v1/orders/{id}/status` | Advance workflow (role-gated per transition) |
| `DELETE` | `/api/v1/orders/{id}` | Cancel — Pending only (Cancellation Guard) |
| `POST` | `/api/v1/billing/invoices/preview/{id}` | Dry-run receipt with coupon calculation |
| `POST` | `/api/v1/billing/invoices/settle/{id}` | Finalize payment → dispatches Celery tasks |
| `PATCH` | `/api/v1/inventory/{id}/restock` | Add stock from incoming shipment |
| `POST` | `/api/v1/inventory/recipes` | Map MenuItem → Ingredient + quantity |
| `GET` | `/api/v1/reports/sales/summary` | Revenue summary `?range=daily\|monthly` |
| `GET` | `/api/v1/reports/items/trending` | Top-selling items chart data |

---

## 6. Security & RBAC

Passwords are hashed with **bcrypt** via Passlib. JWT tokens are signed with HS256 and carry `user_id`, `username`, and `role` in the payload. On every protected request, the token is decoded and cross-checked against the live database row — a tampered role claim is rejected with **401**.

Role enforcement via `require_roles()` dependency returns **403 Forbidden** with a clear message listing required roles.

| Action | Admin | Cashier | Waiter | Chef |
|---|:---:|:---:|:---:|:---:|
| Manage users & menu | ✅ | | | |
| Create / view orders | ✅ | | ✅ | |
| Push `Pending → Preparing → Ready` | ✅ | | | ✅ |
| Push `Ready → Delivered` | ✅ | ✅ | ✅ | |
| Settle invoices | ✅ | ✅ | | |
| Manage inventory & recipes | ✅ | | | |
| View analytics & reports | ✅ | | | |

---

## 7. Order Workflow Engine

```
             [Chef / Admin]            [Chef / Admin]         [Waiter / Cashier / Admin]
Pending  ──────────────────▶  Preparing ──────────────▶  Ready ──────────────────────▶  Delivered
   │
   └──▶  Cancelled  (DELETE /orders/{id} — Pending state only)
```

- Invalid transitions → **HTTP 400** with clear error message
- Wrong role for transition → **HTTP 403** listing permitted roles
- PATCH to `Cancelled` is always blocked → redirect to DELETE endpoint

---

## 8. Real-Time WebSockets

| Endpoint | Audience | Trigger |
|---|---|---|
| `ws://host/ws/kitchen` | Kitchen screens | Every new order created |
| `ws://host/ws/waiter/{waiter_id}` | Waiter tablet/mobile | Order status reaches `Ready` |

The `ConnectionManager` in `app/services/notification.py` maintains all active connections and broadcasts JSON payloads asynchronously.

---

## 9. Background Tasks (Celery + Redis)

| Task | Trigger | Action |
|---|---|---|
| `print_receipt` | Invoice settled | Log/send receipt to POS printer |
| `adjust_inventory_on_invoice` | Invoice settled | Load `RecipeItem` mappings → deduct `current_stock` → fire low-stock alerts |
| `send_reservation_confirmation` | Reservation created | Email confirmation to customer |
| `send_reservation_reminder` | Celery Beat (1h before) | Reminder email/SMS |
| `generate_daily_sales_report` | Celery Beat (nightly) | Aggregate yesterday's revenue + invoice count |

> Celery workers use a **synchronous** SQLAlchemy session (`psycopg2`) via `SYNC_DATABASE_URL` — separate from the async FastAPI session, since Celery runs outside the async event loop.

---

## 10. Testing

```bash
make test
# or: python -m pytest tests/ -v
```

**69 tests** covering all modules using an **in-memory SQLite** database — no external PostgreSQL or Redis required to run the suite.

| Test Module | Coverage |
|---|---|
| `test_auth.py` | Login, JWT validation, register, RBAC |
| `test_menu.py` | Category & MenuItem CRUD, availability filter |
| `test_orders.py` | Workflow transitions, cancellation guard, role-gating, price lock |
| `test_billing.py` | Preview/settle, percentage & fixed coupons, expired coupon |
| `test_inventory.py` | CRUD, restock, low-stock flag, recipe mapping CRUD |
| `test_tables.py` | Table CRUD, QR public menu, reservation lifecycle |
| `test_reports.py` | Sales summary, daily breakdown, trending items |

---

## Interactive Docs
Start the server, then open: **http://localhost:8000/docs**
