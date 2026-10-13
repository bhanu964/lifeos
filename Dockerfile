# Stage 1: Build Frontend SPA
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build

# Stage 2: Production Python Backend + Embedded Frontend
FROM python:3.12-slim
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install system dependencies (build tools, libffi, openssl for cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies from backend/requirements.txt
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source code and data
COPY backend/app/ ./app/
COPY backend/data/ ./data/

# Copy built frontend SPA assets from Stage 1 into /app/static
COPY --from=frontend-builder /app/dist /app/static

# Create persistent storage directory
RUN mkdir -p /app/data

# Expose standard port
EXPOSE 8000

# Run FastAPI with uvicorn using shell form to support dynamic $PORT from PaaS (Railway / Render / Fly)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
