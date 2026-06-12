# Restaurant Management System - Installation Guide

## Overview
Multi-tenant SaaS restaurant management system with FastAPI backend and React frontend.

---

## Prerequisites

### Required Software
- **Python 3.11+** (https://python.org)
- **Node.js 18+** (https://nodejs.org)
- **Git** (optional, for cloning)

---

## Quick Start (Windows)

### Step 1: Clone/Navigate to Project
```powershell
cd "E:\New folder (3)\project\Restaurant"
```

### Step 2: Backend Setup

#### Install Python Dependencies
```powershell
pip install fastapi uvicorn sqlalchemy asyncpg aiosqlite redis python-jose passlib pydantic pydantic-settings stripe requests python-multipart
```

Or use requirements.txt:
```powershell
pip install -r requirements.txt
```

#### Seed Database (First Time Only)
```powershell
$env:DATABASE_URL="sqlite+aiosqlite:///./restaurant.db"
python seed_data.py
```

#### Start Backend Server
```powershell
$env:DATABASE_URL="sqlite+aiosqlite:///./restaurant.db"
$env:SECRET_KEY="your-secret-key"
python -m uvicorn app.main:app --reload --port 8000
```

Backend will be available at: **http://localhost:8000**

---

### Step 3: Frontend Setup

#### Install Node.js Dependencies
```powershell
cd frontend
npm install
```

#### Start Frontend Development Server
```powershell
npm run dev
```

Frontend will be available at: **http://localhost:5173**

---

## Alternative: Using Batch Scripts

### Option 1: Start Backend
Double-click `start_backend.bat` or run:
```powershell
.\start_backend.bat
```

### Option 2: Start Frontend  
Double-click `start_frontend.bat` or run:
```powershell
.\start_frontend.bat
```

---

## Configuration

### Environment Variables (.env file)

Create `.env` file in project root:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./restaurant.db
SYNC_DATABASE_URL=sqlite:///./restaurant.db

# Security
SECRET_KEY=change-this-to-a-secure-key-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Redis (Optional - for caching)
REDIS_URL=redis://localhost:6379/0

# Stripe (Optional - for payments)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Tax Rate
TAX_RATE=0.15
```

---

## Production Deployment

### Using Docker

```bash
# Build and start all services
docker-compose up --build

# Services:
# - API: http://localhost:8000
# - Frontend: http://localhost:5173
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

### Manual Production Setup

1. **Use PostgreSQL** instead of SQLite
2. **Set secure SECRET_KEY**
3. **Enable HTTPS**
4. **Configure CORS** properly
5. **Set up Redis** for caching

---

## Default Login Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Administrator |
| cashier | cashier123 | Cashier |
| waiter | waiter123 | Waiter |
| chef | chef123 | Chef |

---

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'app'"
**Solution:** Run from project root directory
```powershell
cd "E:\New folder (3)\project\Restaurant"
```

#### "npm not recognized"
**Solution:** Install Node.js or add to PATH
```powershell
$env:PATH="C:\Program Files\nodejs;$env:PATH"
```

#### "Port already in use"
**Solution:** Kill existing processes or use different port
```powershell
# Kill processes
taskkill /F /IM python.exe
taskkill /F /IM node.exe

# Or change port
python -m uvicorn app.main:app --port 8001
```

#### CORS errors in browser
**Solution:** Backend CORS is configured to allow all origins in development. For production, update `app/main.py`:
```python
allow_origins=["https://yourdomain.com"]
```

---

## API Testing

### Using Swagger UI
Visit: http://localhost:8000/docs

### Using curl
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

# Get current user
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Project Structure

```
Restaurant/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Settings & configuration
│   ├── database.py          # SQLAlchemy setup
│   ├── models.py            # Database models
│   ├── auth.py              # JWT & authentication
│   ├── routers/             # API endpoints
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── menu.py
│   │   ├── orders.py
│   │   ├── tables.py
│   │   ├── billing.py
│   │   ├── inventory.py
│   │   ├── reports.py
│   │   └── tenants.py
│   ├── schemas/             # Pydantic models
│   └── services/            # Business logic
├── frontend/                # React application
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # Reusable components
│   │   └── context/        # React contexts
│   └── package.json
├── alembic/                 # Database migrations
├── seed_data.py            # Initial data script
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker configuration
└── README.md
```

---

## Support

For issues or questions:
1. Check API docs: http://localhost:8000/docs
2. Review error logs in terminal
3. Verify environment variables
