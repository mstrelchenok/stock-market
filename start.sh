#!/usr/bin/env bash
# start.sh — run backend + frontend locally WITHOUT Docker
# Usage: ./start.sh [PORT]
# Default port: 8000

set -e

PORT="${1:-8000}"

echo "==> Installing Python dependencies..."
pip install -r backend/requirements.txt --break-system-packages -q 2>/dev/null || pip install -r backend/requirements.txt -q

echo "==> Starting backend on port $PORT..."
(cd backend && python3 main.py "$PORT") &
BACKEND_PID=$!

echo "==> Installing frontend dependencies..."
(cd frontend && npm install --silent)

echo "==> Starting frontend (React dev server)..."
(cd frontend && REACT_APP_API_URL="http://localhost:$PORT" npm start) &
FRONTEND_PID=$!

echo ""
echo "✅ Backend  → http://localhost:$PORT"
echo "✅ Frontend → http://localhost:3000"
echo "✅ API docs → http://localhost:$PORT/docs"
echo ""
echo "Press Ctrl+C to stop everything."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait