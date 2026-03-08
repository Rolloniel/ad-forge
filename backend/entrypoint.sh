#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding database..."
python -c "from app.seed import main; main()" || echo "Seed already applied or skipped."

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
