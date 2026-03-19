#!/bin/sh
# Run database migrations before starting the application server.
# This script is executed as a Docker ENTRYPOINT pre-command or init container.
set -e
echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete. Starting server..."
exec "$@"
