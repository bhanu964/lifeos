# LifeOS — Vercel Frontend Deployment Guide

This guide describes how to deploy the LifeOS React + Vite dashboard to **Vercel** with dynamic backend connectivity and zero hardcoded URLs.

---

## 1. Overview

The LifeOS frontend is a single-page application (SPA) built with React 18, Vite, TypeScript, and Tailwind CSS. It communicates with the FastAPI backend via:
- REST API calls (`/api/...`)
- Real-time Server-Sent Events (`/api/lifeos/events?token=<jwt>`)

The frontend dynamically resolves all endpoints from the `VITE_API_BASE_URL` environment variable at runtime.

---

## 2. Option A: Monorepo Root Deployment (Recommended)

When importing the repository directly into Vercel from the root:

1. **Import Repository**: Connect your GitHub repository (`lifeos`) in the [Vercel Dashboard](https://vercel.com/new).
2. **Framework Preset**: Select `Vite` (or `Other`).
3. **Root Directory**: Leave as `./` (Root).
4. **Build & Output Settings**:
   - The included root `vercel.json` automatically handles the build:
     ```json
     {
       "buildCommand": "cd frontend && npm install && npm run build",
       "outputDirectory": "frontend/dist",
       "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
     }
     ```
5. **Environment Variables**:
   Add the following environment variable:
   | Key | Value | Notes |
   | :--- | :--- | :--- |
   | `VITE_API_BASE_URL` | `https://your-backend.railway.app` | URL of your deployed FastAPI backend (no trailing slash) |
6. **Deploy**: Click **Deploy**.

---

## 3. Option B: Frontend Subdirectory Deployment

If you prefer configuring Vercel specifically for the `frontend/` directory:

1. In the Vercel project configuration, set **Root Directory** to `frontend`.
2. Vercel will automatically detect `frontend/package.json` and use:
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add `VITE_API_BASE_URL` in **Environment Variables**.
4. Deploy.

---

## 4. Backend CORS Configuration

The LifeOS backend dynamically allows Vercel preview and production deployments. In `backend/app/main.py`:

```python
# Allowed Origins: Configured explicitly via CORS_ALLOWED_ORIGINS
# Allowed Origin Regex: Automatically matches all Vercel domains:
CORSMiddleware(
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Ensure your backend has your production domain in `CORS_ALLOWED_ORIGINS`:
```ini
CORS_ALLOWED_ORIGINS=https://lifeos.yourdomain.com,https://your-project.vercel.app
```

---

## 5. Post-Deployment Verification Checklist

1. **Health Check**: Open your Vercel URL. If `VITE_API_BASE_URL` is missing or misconfigured, LifeOS displays a prominent configuration banner explaining what is missing.
2. **Authentication Flow**: Click **Sign In / Create Account** to register a tenant account.
3. **SSE Connection**: Verify that the top status bar displays `SSE Live Stream Active`.
4. **Inspect Console**: Ensure there are no mixed-content errors or blocked cross-origin requests.
