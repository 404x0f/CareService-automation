#!/bin/sh

set -e

echo "Waiting for database migrations..."

alembic upgrade head

echo "Migrations applied successfully."

exec "$@"