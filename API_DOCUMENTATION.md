# Restaurant Management System - API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication

### Login
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
username=admin&password=admin123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Get Current User
```http
GET /auth/me
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "tenant_id": 1,
  "username": "admin",
  "full_name": "System Administrator",
  "role": "Admin",
  "is_active": true
}
```

---

## Tenants (Restaurants)

### Register New Tenant
```http
POST /tenants/register
Content-Type: application/json
```

**Request Body:**
```json
{
  "restaurant_name": "My Restaurant",
  "subdomain": "my-restaurant",
  "admin_username": "admin",
  "admin_password": "securepassword123",
  "admin_full_name": "John Doe",
  "admin_email": "admin@example.com"
}
```

**Response:**
```json
{
  "tenant": {
    "id": 1,
    "name": "My Restaurant",
    "subdomain": "my-restaurant",
    "plan": "Free",
    "subscription_status": "Trialing",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "message": "Welcome! Your 14-day free trial has started."
}
```

### Get Subscription Status
```http
GET /tenants/subscription
Authorization: Bearer {token}
```

---

## Users

### List Users
```http
GET /users
Authorization: Bearer {token}
```

**Query Parameters:**
- `role` (optional): Filter by role (Admin, Cashier, Waiter, Chef)

### Create User
```http
POST /users
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "newuser",
  "password": "password123",
  "full_name": "New User",
  "role": "Waiter",
  "phone": "+966501234567"
}
```

### Get User
```http
GET /users/{user_id}
Authorization: Bearer {token}
```

### Update User
```http
PUT /users/{user_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "full_name": "Updated Name",
  "role": "Cashier",
  "is_active": true
}
```

### Delete User
```http
DELETE /users/{user_id}
Authorization: Bearer {token}
```

---

## Menu

### Categories

#### List Categories
```http
GET /menu/categories
Authorization: Bearer {token}
```

#### Create Category
```http
POST /menu/categories
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Appetizers",
  "description": "Starters and small dishes"
}
```

### Menu Items

#### List Menu Items
```http
GET /menu/items
Authorization: Bearer {token}
```

**Query Parameters:**
- `category_id`: Filter by category
- `available_only`: true/false

#### Create Menu Item
```http
POST /menu/items
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "category_id": 1,
  "name": "Chicken Burger",
  "description": "Delicious grilled chicken",
  "price": 35.00,
  "is_available": true
}
```

#### Update Menu Item
```http
PUT /menu/items/{item_id}
Authorization: Bearer {token}
Content-Type: application/json
```

#### Delete Menu Item
```http
DELETE /menu/items/{item_id}
Authorization: Bearer {token}
```

---

## Orders

### Create Order
```http
POST /orders
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "table_id": 1,
  "order_type": "Dine-In",
  "items": [
    {
      "menu_item_id": 1,
      "quantity": 2,
      "special_requests": "No onions"
    }
  ]
}
```

### List Active Orders
```http
GET /orders/active
Authorization: Bearer {token}
```

Returns orders based on user role:
- **Chef**: Pending + Preparing
- **Waiter**: Ready
- **Admin/Cashier**: All active

### Get Order Details
```http
GET /orders/{order_id}
Authorization: Bearer {token}
```

### Update Order Status
```http
PATCH /orders/{order_id}/status
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "status": "Preparing"
}
```

**Valid Transitions:**
- `Pending` → `Preparing` (Chef)
- `Preparing` → `Ready` (Chef)
- `Ready` → `Delivered` (Waiter)

### Cancel Order
```http
DELETE /orders/{order_id}
Authorization: Bearer {token}
```

**Note:** Only `Pending` orders can be cancelled via DELETE. Use PATCH for other transitions.

---

## Tables

### List Tables
```http
GET /tables
Authorization: Bearer {token}
```

### Create Table
```http
POST /tables
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "table_number": 5,
  "capacity": 4
}
```

### Get QR Menu (Public)
```http
GET /tables/{table_id}/menu
```

Returns public menu for customers scanning QR code.

---

## Inventory

### List Inventory
```http
GET /inventory
Authorization: Bearer {token}
```

### Create Inventory Item
```http
POST /inventory
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "ingredient_name": "Chicken Breast",
  "unit": "KG",
  "current_stock": 50.0,
  "min_alert_level": 10.0
}
```

### Restock Item
```http
POST /inventory/{item_id}/restock
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "quantity": 25.0
}
```

### Get Low Stock Items
```http
GET /inventory/low-stock
Authorization: Bearer {token}
```

---

## Billing

### Create Invoice Preview
```http
POST /billing/preview
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "order_id": 123,
  "discount_code": "SUMMER10",
  "payment_method": "Card"
}
```

### Settle Invoice
```http
POST /billing/settle
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "invoice_id": 456,
  "amount_received": 150.00
}
```

### Get Invoice
```http
GET /billing/invoices/{invoice_id}
Authorization: Bearer {token}
```

---

## Reports

### Sales Summary
```http
GET /reports/sales-summary
Authorization: Bearer {token}
```

**Query Parameters:**
- `start_date`: YYYY-MM-DD
- `end_date`: YYYY-MM-DD

### Daily Sales
```http
GET /reports/daily-sales
Authorization: Bearer {token}
```

### Trending Items
```http
GET /reports/trending
Authorization: Bearer {token}
```

**Query Parameters:**
- `limit`: Number of items (default: 10)

---

## WebSocket (Real-time)

### Kitchen Display
```javascript
ws://localhost:8000/ws/kitchen
```

Receives notifications when new orders are created.

### Waiter Notifications
```javascript
ws://localhost:8000/ws/waiter/{waiter_id}
```

Receives notifications when orders are ready.

---

## Error Responses

### 400 - Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 401 - Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 - Forbidden
```json
{
  "detail": "Access restricted. Required roles: ['Admin']"
}
```

### 404 - Not Found
```json
{
  "detail": "Order not found"
}
```

### 409 - Conflict
```json
{
  "detail": "Username already taken"
}
```

### 422 - Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "price"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

---

## Role Permissions

| Endpoint | Admin | Cashier | Waiter | Chef |
|----------|-------|---------|--------|------|
| Users CRUD | ✅ | ❌ | ❌ | ❌ |
| Menu Management | ✅ | ❌ | ❌ | ❌ |
| Create Orders | ✅ | ✅ | ✅ | ❌ |
| Update Order Status | ✅ | ❌ | Ready→Delivered | Pending→Preparing→Ready |
| Billing | ✅ | ✅ | ❌ | ❌ |
| Inventory | ✅ | ❌ | ❌ | ✅ |
| Reports | ✅ | ❌ | ❌ | ❌ |
| View Active Orders | ✅ | ✅ | Ready only | Pending+Preparing |

---

## Testing with Swagger UI

Visit: **http://localhost:8000/docs**

1. Click "Authorize" button
2. Enter: `Bearer YOUR_TOKEN`
3. Test endpoints interactively

---

## Postman Collection

### Environment Variables
```json
{
  "base_url": "http://localhost:8000/api/v1",
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Example Request
```http
GET {{base_url}}/orders/active
Authorization: Bearer {{token}}
```
