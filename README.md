# ANHA Trading - FastAPI + HTMX

Arabic-first maintenance booking app for ANHA Trading (شركة انها التجارية). Uses SQLite for development and PostgreSQL for production.

## Quick Start

1. Create venv and install deps:
   ```bash
   uv venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure env (optional):
   ```bash
   cp .env.example .env
   ```

3. Run:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

Open http://localhost:8000

## Production

Set `DATABASE_URL` to PostgreSQL (asyncpg), for example:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/anha
```

## Migrations (Alembic)

Create or upgrade the schema with:
```
alembic upgrade head
```

If you change models, create a new migration:
```
alembic revision --autogenerate -m "describe change"
```

## Deployment Checklist

1. Set env vars: `DATABASE_URL`, `SECRET_KEY`, `AUTO_CREATE_DB=false`.
2. Run migrations: `alembic upgrade head`.
3. Create the first admin user:
   ```
   python scripts/create_admin.py
   ```
4. Start the server:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop uvloop --http h11
   ```

## Roles

- client
- employee
- driver
- technical

## Booking Statuses

- requested
- assigned
- in_progress
- completed
- cancelled

## Notes

- Password reset is demo-based: it shows a reset link on screen after requesting.
- Maps use Leaflet + OpenStreetMap tiles and browser geolocation.
