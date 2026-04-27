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
5. Run migrations:
   - `alembic upgrade head`
6. Run API:
   - `uvicorn app.main:app --reload --port 8010`

## Authentication

- `POST /auth/token` (OAuth2 password flow)
- Users are now loaded from the database.
- Seed initial admin user:
  - `python -m scripts.seed_admin_user`
  - default credentials: `admin` / `admin123`
- Seed initial clerk user:
  - `python -m scripts.seed_clerk_user`
  - default credentials: `clerk` / `clerk123`
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
- `GET /products/{product_id}/lots`
- `POST /stock-movements` (`IN` or `OUT`)
- `GET /stock-movements` (supports `product_id`, `date_from`, `date_to` filters)
- `POST /stock-transfers` (admin-only warehouse-to-warehouse transfers)
- `GET /stock-transfers` (admin/clerk, supports `source_warehouse_id`, `destination_warehouse_id`, `date_from`, `date_to`)
- `GET /alerts/low-stock` (admin/clerk, optional `warehouse_id` filter)
- `POST /reorders/suggested` (admin-only bulk restock from low-stock alerts)

Interactive docs are available at `http://127.0.0.1:8010/docs`.

## Automated Tests

- Run tests locally:
  - `pytest -q`
- CI runs on pull requests and `main` pushes:
  - applies migrations
  - seeds admin user
  - executes API tests (auth, roles, FIFO, and audit filters)

## API Usage Examples

- End-to-end `curl` examples:
  - `docs/api-examples.md`
- Windows smoke test script:
  - `scripts/smoke_test.ps1`
  - run with: `.\scripts\smoke_test.ps1`
- Windows role guard smoke test:
  - `scripts/smoke_test_roles.ps1`
  - run with: `.\scripts\smoke_test_roles.ps1`
- OpenAPI schema:
  - `http://127.0.0.1:8010/openapi.json`
