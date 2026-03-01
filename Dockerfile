# ===========================================================================
# Multi-stage Dockerfile for the Statik-Tool (Durchlaufträger web app)
#
# Stage 1 – Build the React SPA with Vite
# Stage 2 – Python runtime serving FastAPI + built frontend
# ===========================================================================

# ---- Stage 1: Frontend build ----
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY web/frontend/package*.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend + serve built frontend ----
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy backend (existing calculation engine – UNTOUCHED)
COPY backend/ ./backend/

# Copy web API layer
COPY web/__init__.py ./web/
COPY web/api/ ./web/api/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./web/frontend/dist

EXPOSE 8000

CMD ["uvicorn", "web.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
