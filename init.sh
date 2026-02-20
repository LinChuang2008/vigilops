#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=== VigilOps Init ==="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ docker not found"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "❌ docker compose not found"; exit 1; }

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📋 Created .env from .env.example — please review settings"
fi

# Start services
echo "🚀 Starting services..."
docker compose up -d --build

# Wait for health
echo "⏳ Waiting for services..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U vigilops >/dev/null 2>&1; then
        echo "✅ PostgreSQL ready"
        break
    fi
    sleep 1
done

for i in $(seq 1 30); do
    if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        echo "✅ Redis ready"
        break
    fi
    sleep 1
done

# Health check backend
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ Backend ready"
        break
    fi
    sleep 2
done

echo ""
echo "🎉 VigilOps is running!"
echo "   Frontend: http://localhost:3001"
echo "   Backend:  http://localhost:8001"
echo "   API Docs: http://localhost:8001/docs"
