.PHONY: install run migrate migrate-auto worker beat test docker-up docker-down

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

migrate-auto:
	alembic revision --autogenerate -m "$(msg)"

worker:
	celery -A app.celery_app worker --loglevel=info

beat:
	celery -A app.celery_app beat --loglevel=info

test:
	pytest tests/ -v --tb=short

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down -v

docker-logs:
	docker-compose logs -f api
