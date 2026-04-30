# Release Checklist

Use this checklist for every change before promoting to production.

## 1) Sync and Dependencies

- Pull latest `main`.
- Ensure Docker/Postgres is running locally:
  - `docker compose up -d`
- Ensure dependencies are installed:
  - `python -m pip install -r requirements.txt`

## 2) Database Migrations (Local)

- Apply latest migrations:
  - `python -m alembic upgrade head`
- If needed, seed local users:
  - `python -m scripts.seed_admin_user`
  - `python -m scripts.seed_clerk_user`

## 3) Automated Tests

- Run full test suite:
  - `python -m pytest -q`
- Confirm all tests pass before continuing.

## 4) Manual Smoke Test (Local)

- Start API:
  - `python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload`
- Verify key routes:
  - `http://127.0.0.1:8010/docs`
  - `http://127.0.0.1:8010/alerts/low-stock`
- Run a quick happy path:
  - login
  - create warehouse/product
  - create stock movement(s)
  - verify low-stock alerts and notifications

## 5) Version Control

- Review changes:
  - `git status`
  - `git diff`
- Commit with clear message.
- Push to remote:
  - `git push origin main`

## 6) Production Deploy

- Trigger/confirm deployment (Render auto-deploy or manual).
- Confirm migrations are applied in production startup.

## 7) Production Smoke Test

- Verify:
  - `/health`
  - `/docs`
  - `/alerts/low-stock`
- Run a minimal operational flow and confirm expected behavior.

## 8) Post-Deploy Checks

- Confirm no unexpected errors in logs.
- Confirm notifications and low-stock alert flows are functioning.

