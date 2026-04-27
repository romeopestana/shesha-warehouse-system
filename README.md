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

## Deploy to Render

1. Push latest `main` to GitHub.
2. In Render, choose **New +** -> **Blueprint**.
3. Select this repository; Render will detect `render.yaml`.
4. Confirm resources:
   - web service: `shesha-warehouse-api`
   - postgres database: `shesha-warehouse-db`
5. Deploy the Blueprint.
6. After deploy completes:
   - open `<your-render-url>/health`
   - open `<your-render-url>/docs`
7. Use your deployed base URL as GitHub secret:
   - `API_BASE_URL=https://<your-render-url>`

Notes:
- Startup runs migrations and seeds admin user automatically via `scripts/render_start.sh`.
- Default admin remains `admin` / `admin123` until you change it.

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
  - supports `dry_run` preview mode
- `GET /reorders/proposals` (admin/clerk, optional `status` filter)
- `POST /reorders/proposals/{id}/approve` (admin, supports `force=true` for stock-level drift override)
- `POST /reorders/proposals/{id}/reject` (admin)
- `GET /notifications` (admin/clerk, supports `unread_only`, `event_type`, `date_from`, `date_to`)
- `POST /notifications/{id}/read` (admin/clerk)
- `POST /jobs/daily-reorder-scan` (admin, idempotent per day/warehouse)

Interactive docs are available at `http://127.0.0.1:8010/docs`.

## Automated Tests

- Run tests locally:
  - `pytest -q`
- CI runs on pull requests and `main` pushes:
  - applies migrations
  - seeds admin user
  - executes API tests (auth, roles, FIFO, and audit filters)

## Scheduled Daily Reorder Scan

- Workflow file:
  - `.github/workflows/daily-reorder-scan.yml`
- Trigger options:
  - daily schedule at `04:00 UTC`
  - manual trigger via GitHub Actions `workflow_dispatch`
- Required repository secrets:
  - `API_BASE_URL` (example: `https://your-api-host`)
  - `ADMIN_USERNAME`
  - `ADMIN_PASSWORD`
- Job action:
  - obtains JWT from `/auth/token`
  - calls `POST /jobs/daily-reorder-scan`

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
