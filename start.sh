#!/bin/bash
# Start both API and Celery worker in a single container (Railway production)
# This ensures both processes share the same filesystem for ledger/image files.

# Start Celery worker in background
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 &

# Start API server in foreground
uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
