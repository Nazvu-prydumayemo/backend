#!/bin/bash

set -e

BACKEND_DIR="${1:-.}"
cd "$BACKEND_DIR"

echo "Backend Deployment"
echo "Working directory: $(pwd)"

if [ ! -f .env ]; then
    echo "ERROR: .env file not found at $BACKEND_DIR/.env"
    echo "Make sure to set environment variables on your system."
    exit 1
fi

echo "Loading environment variables..."
set -a
. ./.env
set +a

echo "Pulling latest code from Git..."
git fetch origin
git checkout main
git pull origin main

echo "Starting Docker services (docker-compose)..."
docker-compose down --remove-orphans || true
docker-compose up -d

echo "Waiting for PostgreSQL to be ready..."
POSTGRES_READY="false"
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U ${DB_USER} > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        POSTGRES_READY="true"
        break
    fi
    echo "Attempt $i/30: PostgreSQL not ready yet, waiting..."
    sleep 2
done

if [ "$POSTGRES_READY" != "true" ]; then
    echo "ERROR: PostgreSQL did not become ready after 30 attempts. Aborting deployment."
    exit 1
fi

echo "Running database migrations..."
docker-compose exec -T backend alembic upgrade head

echo "Checking backend health..."
BACKEND_HEALTHY="false"
for i in {1..30}; do
    if curl -f http://localhost/api/v1/status/ping > /dev/null 2>&1; then
        echo "Backend is healthy!"
        BACKEND_HEALTHY="true"
        break
    fi
    echo "Attempt $i/30: Backend not ready yet, waiting..."
    sleep 2
done

if [ "$BACKEND_HEALTHY" != "true" ]; then
    echo "ERROR: Backend did not become healthy after 30 attempts. Aborting deployment."
    exit 1
fi
echo ""
echo "Deployment Complete"
echo "Backend is running at http://localhost"
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
