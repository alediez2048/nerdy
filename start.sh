#!/bin/bash
# Start both API and Celery worker in a single container (Railway production)
# This ensures both processes share the same filesystem for ledger/image files.

# Export all environment variables so background processes inherit them
export GEMINI_API_KEY="${GEMINI_API_KEY}"
export FAL_KEY="${FAL_KEY}"
export DATABASE_URL="${DATABASE_URL}"
export REDIS_URL="${REDIS_URL}"
export SECRET_KEY="${SECRET_KEY}"

echo "Starting Celery worker (background)..."
echo "GEMINI_API_KEY set: $([ -n "$GEMINI_API_KEY" ] && echo 'yes' || echo 'NO')"
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'yes' || echo 'NO')"
echo "REDIS_URL set: $([ -n "$REDIS_URL" ] && echo 'yes' || echo 'NO')"

# Start Celery worker in background
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 &

echo "Starting API server..."
# Start API server in foreground
exec uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
