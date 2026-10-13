# LifeOS — Backend Production Deployment Guide

This guide covers deploying the LifeOS FastAPI backend to cloud platforms including **Railway**, **Render**, and **Docker / VPS**.

---

## 1. Production Architecture Overview

The backend is built as an ASGI application served by `uvicorn`. It requires:
- Python 3.12+
- Persistent storage for SQLite (or managed PostgreSQL)
- Outbound HTTPS access to:
  - Qdrant Cloud (port 6333 or 443)
  - Lyzr Studio API
  - Telegram Bot API (`https://api.telegram.org`)
  - Composio Tool Cloud APIs

---

## 2. Deploying to Railway (Recommended)

Railway offers automatic persistent volume support and container builds using the included `railway.json` and `backend/Dockerfile`.

### Steps:
1. Fork or push your LifeOS repository to GitHub.
2. Log into [Railway.app](https://railway.app) and click **New Project** > **Deploy from GitHub repo**.
3. Select your `lifeos` repository.
4. Set the **Root Directory** or build path:
   - Railway will detect `backend/Dockerfile`.
5. Add a **Persistent Volume** in the service settings:
   - Mount path: `/app/data` (ensures SQLite databases survive redeploys).
   - Alternatively, add a Railway PostgreSQL database and set `DATABASE_URL`.
6. Add the following **Environment Variables**:
   ```ini
   APP_ENV=production
   PORT=8000
   PUBLIC_BASE_URL=https://your-railway-app.up.railway.app
   CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
   JWT_SECRET_KEY=<generate_random_64_hex_string>
   ENCRYPTION_KEY=<generate_fernet_key>
   QDRANT_URL=https://<your-qdrant-cluster>.qdrant.io:6333
   QDRANT_API_KEY=<your_qdrant_api_key>
   QDRANT_COLLECTION_NAME=agentmemory_memories
   LYZR_API_KEY=<your_lyzr_api_key>
   LYZR_MANAGER_AGENT_ID=<your_manager_id>
   LYZR_FACT_FINDER_AGENT_ID=<your_fact_finder_id>
   LYZR_DATA_ANALYST_AGENT_ID=<your_data_analyst_id>
   TELEGRAM_BOT_TOKEN=<your_telegram_bot_token>
   ```
7. Deploy. Verify deployment by visiting `https://your-railway-app.up.railway.app/api/health`.

---

## 3. Deploying to Render

Use the included `render.yaml` blueprint:

1. In Render, select **Blueprints** > **New Blueprint Instance**.
2. Connect your `lifeos` GitHub repository.
3. Render reads `render.yaml` and provisions the `lifeos-backend` web service.
4. Set your private secrets in the Render dashboard.

---

## 4. Deploying with Docker

You can build and run the Docker container anywhere (AWS ECS, Google Cloud Run, DigitalOcean, Hetzner):

```bash
# Build the image from backend context
cd backend
docker build -t lifeos-backend .

# Run container with persistent volume
docker run -d \
  --name lifeos-backend \
  -p 8000:8000 \
  -v lifeos-data:/app/data \
  --env-file .env \
  lifeos-backend
```

---

## 5. PostgreSQL Migration (Optional)

By default, LifeOS uses SQLite in `data/lifeos_saas.db`. For enterprise multi-node deployments:

1. Provision a PostgreSQL instance (Supabase, Neon, AWS RDS, Railway Postgres).
2. Set `DATABASE_URL` in your backend environment:
   ```ini
   DATABASE_URL=postgresql://user:password@hostname:5432/lifeos
   ```
3. SQLAlchemy will automatically create all tables (`users`, `user_integrations`, `workflows`, `actions`) upon first connection.

---

## 6. Health & Status Verification

Once deployed, verify your service:

```bash
curl -X GET https://your-backend-domain.com/api/health
```

Expected JSON response:
```json
{
  "status": "healthy",
  "qdrant": "connected",
  "lyzr": "configured",
  "timestamp": "2026-10-13T12:00:00Z"
}
```
