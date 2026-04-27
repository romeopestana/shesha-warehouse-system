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
   - This project uses host port `5433` to avoid conflicts with other local Postgres services.
5. Run API:
   - `uvicorn app.main:app --reload --port 8010`

## Authentication

- `POST /auth/token` (OAuth2 password flow)
- Demo users:
  - `admin` / `admin123` (role: `admin`)
  - `clerk` / `clerk123` (role: `clerk`)
- These credentials are in-memory demo data for scaffolding only.
- Protected stock endpoints:
  - `POST /stock-movements` requires `admin`
  - `GET /stock-movements` requires `admin` or `clerk`

## API Endpoints

- `GET /health`
- `POST /auth/token`
- `POST /warehouses`
- `GET /warehouses`
- `POST /products`
- `GET /products`
- `POST /stock-movements` (`IN` or `OUT`)
- `GET /stock-movements`

Interactive docs are available at `http://127.0.0.1:8010/docs`.
