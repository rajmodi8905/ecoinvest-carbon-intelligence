#!/bin/bash

set -e

if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo "🚀 Starting Carbon Intelligence Platform..."
echo ""
echo "📦 Building and starting the Docker stack..."
$COMPOSE_CMD up -d --build

echo ""
echo "⏳ Waiting for services to become available..."
sleep 20

echo ""
echo "🔍 Checking backend health..."
if curl -fsS http://localhost:5001/health >/dev/null; then
    echo "✅ Backend API is ready at http://localhost:5001"
else
    echo "⚠️ Backend is still starting. Check docker logs if it does not come up."
fi

echo ""
echo "🔍 Checking frontend health..."
if curl -fsS http://localhost:5173 >/dev/null; then
    echo "✅ Frontend is ready at http://localhost:5173"
else
    echo "⚠️ Frontend is still starting. Check docker logs if it does not come up."
fi

echo ""
echo "📝 View logs: $COMPOSE_CMD logs -f"
echo "🛑 Stop all: $COMPOSE_CMD down"
echo ""
echo "✨ Setup complete!"
