#!/usr/bin/env bash
set -euo pipefail

python -m alembic upgrade head
python -m scripts.seed_admin_user

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"
