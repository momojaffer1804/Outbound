# Multi-stage Dockerfile for Outbound (Unified Fullstack Production Deployment)

# Stage 1: Build React 19 Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend & Static Asset Serving
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Pre-cache SentenceTransformer and CrossEncoder models to prevent startup lag
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
               SentenceTransformer('all-MiniLM-L6-v2'); \
               CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

COPY backend/ /app/backend/
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

RUN mkdir -p /app/backend/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "uvicorn api.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8000}"]
