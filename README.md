# shesha-warehouse-system

FastAPI + PostgreSQL starter for the Shesha Warehouse System project.

## Stack

- FastAPI
- SQLAlchemy ORM
- PostgreSQL (via Docker Compose)

## Setup

1. Create and activate a virtual environment:
   - Windows PowerShell:
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy environment file:
   - `copy .env.example .env`
4. Start PostgreSQL:
   - `docker compose up -d`
   - Postgres is exposed on host port `5433`
5. Run migrations:
   - `alembic upgrade head`
6. Run API:
   - `uvicorn app.main:app --reload`

## Seed Data

Run:

- `python scripts/seed.py`

This inserts:
- warehouse: `Main Warehouse`
- product: `SKU-1001` with quantity `100`

## API Endpoints

- `GET /health`
- `POST /warehouses`
- `GET /warehouses`
- `POST /products`
- `GET /products`
- `POST /stock-movements` (`IN` or `OUT`)
- `GET /stock-movements`

Interactive docs are available at `http://127.0.0.1:8000/docs`.
