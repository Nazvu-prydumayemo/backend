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
export $(cat .env | grep -v '^#' | xargs)

echo "Pulling latest code from Git..."
git fetch origin
git checkout main
git pull origin main

echo "Starting Docker services (docker-compose)..."
docker-compose down --remove-orphans || true
docker-compose up -d

echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U ${DB_USER} > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "Attempt $i/30: PostgreSQL not ready yet, waiting..."
    sleep 2
done

echo "Running database migrations..."
docker-compose exec -T backend alembic upgrade head

echo "Checking backend health..."
for i in {1..30}; do
    if curl -f http://localhost/api/v1/status/ping > /dev/null 2>&1; then
        echo "Backend is healthy!"
        break
    fi
    echo "Attempt $i/30: Backend not ready yet, waiting..."
    sleep 2
done

echo ""
echo "Deployment Complete"
echo "Backend is running at http://localhost"
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
