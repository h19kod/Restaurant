@echo off
echo Starting Backend Server...
cd /d "E:\New folder (3)\project\Restaurant"
set DATABASE_URL=sqlite+aiosqlite:///./restaurant.db
set SYNC_DATABASE_URL=sqlite:///./restaurant.db
set REDIS_URL=redis://localhost:6379/0
set SECRET_KEY=dev-secret-key-change-in-production
python -m uvicorn app.main:app --reload --port 8000
pause
