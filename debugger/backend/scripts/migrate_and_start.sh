#!/bin/sh
# Run database migrations before starting the application server.
# Uses a lock file to prevent concurrent migration runs when the container
# is started with multiple workers (e.g. uvicorn --workers 2).
set -e

LOCK_FILE="/tmp/alembic_migrate.lock"

# Only the process that acquires the lock runs migrations.
# All others wait until the lock is released, then proceed directly to exec.
(
  flock -x 200
  echo "Running Alembic migrations..."
  alembic upgrade head
  echo "Migrations complete."
) 200>"$LOCK_FILE"

exec "$@"
