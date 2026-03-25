#!/bin/sh
# Run database migrations before starting the application server.
set -e

echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

exec "$@"
