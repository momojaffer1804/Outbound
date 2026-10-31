#!/usr/bin/env bash
set -e

echo "========================================================"
echo "       Outbound - Production Deployment Script"
echo "========================================================"

if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo "[INFO] Docker daemon is running. Deploying via Docker Compose..."
    docker compose up --build -d
    echo ""
    echo "========================================================"
    echo "[SUCCESS] Outbound deployed successfully via Docker!"
    echo " - Frontend: http://localhost:3000"
    echo " - Backend API: http://localhost:8000"
    echo " - API Docs: http://localhost:8000/docs"
    echo "========================================================"
    exit 0
fi

echo "[INFO] Docker daemon not active. Starting local production server..."
cd frontend
npm run build
cd ..

export PYTHONPATH=backend
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
