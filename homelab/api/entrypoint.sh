#!/bin/sh
set -e

echo "=== NOOP Home Lab API Starting ==="

# Wait for PostgreSQL to become reachable
echo "Checking database connection..."
max_retries=30
counter=0

until python -c "
import sys
from app.config import settings
from sqlalchemy import create_engine, text
try:
    engine = create_engine(settings.sync_database_url, connect_args={'connect_timeout': 2})
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
    counter=$((counter + 1))
    if [ $counter -ge $max_retries ]; then
        echo "Warning: Database not ready after $max_retries attempts. Proceeding..."
        break
    fi
    echo "Database unavailable, retrying in 2 seconds ($counter/$max_retries)..."
    sleep 2
done

# Run Alembic migrations automatically
echo "Applying database migrations..."
if [ -f /app/migrations/alembic.ini ]; then
    alembic -c /app/migrations/alembic.ini upgrade head || echo "Warning: Alembic migration failed or already up to date."
else
    alembic upgrade head || echo "Warning: Alembic migration failed or already up to date."
fi

echo "Database ready. Launching application..."
exec "$@"
