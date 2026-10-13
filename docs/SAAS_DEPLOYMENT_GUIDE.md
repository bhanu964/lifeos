# LifeOS — Multi-User SaaS Platform Deployment Guide
**Hackathon:** Stop Prompting, Solo Agents Hackathon 2026  
**Track:** Track 2 — Collaborative Multi-Agent Workflows  
**Project:** LifeOS — Voice-Triggered Autonomous Personal AI Operator  

---

## 1. Architecture & Multi-Tenant Design

LifeOS is an autonomous, voice-triggered personal AI operator platform. Every user receives a completely isolated personal workspace:
- **Tenant Isolation**: Spoken transcripts, FastEmbed vectors, and memories in Qdrant Cloud are filtered strictly by `uid = user_id`.
- **Dedicated Omi Webhooks**: Each user gets a unique, revocable webhook URL (`/omi/v2/{webhook_token}/conversation`) that routes voice transcripts directly to their account.
- **Interactive Telegram Approvals**: Each user pairs their Telegram account via `/start pair_<token>` to receive interactive `[Approve]` and `[Reject]` buttons for high-risk actions.
- **Encrypted Credential Storage**: All external API keys and tokens are encrypted at rest with Fernet (AES-128-CBC with SHA256 HMAC) and masked in all UI responses (`sk_••••••••1234`).
- **Real-Time Observability**: Live Server-Sent Events (SSE) push updates across the 10 connected nodes of the multi-agent pipeline.

---

## 2. Deploying the Frontend to Vercel

The frontend is built with **React, Vite, TypeScript, and Tailwind CSS**, featuring an atmospheric flowing Aurora background.

### Option A: Deploy via Vercel Web Dashboard (Recommended)
1. Push your repository to GitHub.
2. Go to [vercel.com](https://vercel.com) and click **"Add New Project"**.
3. Import your repository.
4. Set the **Root Directory** to `frontend` (or leave as root if using the root `vercel.json`).
5. Configure the Environment Variables:
   - `VITE_API_BASE_URL`: The public HTTPS URL of your deployed backend (e.g. `https://your-backend.up.railway.app` or ngrok URL).
6. Click **Deploy**. Vercel will build and deploy the SPA within ~45 seconds.

### Option B: Deploy via Vercel CLI
```bash
cd frontend
npx vercel
# Follow prompt: set project name, keep build command 'npm run build', output 'dist'
# Set environment variable:
npx vercel env add VITE_API_BASE_URL
# Deploy to production:
npx vercel --prod
```

`frontend/vercel.json` ensures all client-side routes rewrite seamlessly to `/index.html`:
```json
{
  "version": 2,
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

---

## 3. Deploying the Backend

The backend is built with **FastAPI**, **SQLAlchemy**, and **Python 3.12**.

### Option A: Railway (One-Click)
1. Go to [railway.app](https://railway.app) and create a **New Project**.
2. Select **Deploy from GitHub repo**.
3. Set the **Root Directory** to `/backend`.
4. Add the following Environment Variables in Railway:
   ```env
   APP_ENV=production
   PORT=8000
   PUBLIC_BASE_URL=https://${{RAILWAY_PUBLIC_DOMAIN}}
   JWT_SECRET_KEY=generate_a_random_32_char_hex_secret
   ENCRYPTION_KEY=generate_a_fernet_key_or_leave_empty_for_auto_derive
   DATABASE_URL=sqlite:///data/lifeos_saas.db
   
   # Shared Provider Credentials (or users can provide their own in the wizard):
   QDRANT_URL=https://your-cluster.qdrant.tech:6333
   QDRANT_API_KEY=your_qdrant_api_key
   QDRANT_COLLECTION_NAME=agentmemory_memories
   
   LYZR_API_KEY=your_lyzr_api_key
   LYZR_MANAGER_AGENT_ID=6acdcd0f8a6a8741bd6df3df
   LYZR_FACT_FINDER_AGENT_ID=6acd9f07cb0aafc9293bd126
   LYZR_DATA_ANALYST_AGENT_ID=6acd1ec70b4f09cf4da21e21
   
   TELEGRAM_BOT_TOKEN=8364330229:AAEnA_DKko8OzntedDX3OK8MWHH2BpuVbgU
   TELEGRAM_BOT_USERNAME=Ididhswkje_bot
   ```
5. Set the Start Command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### Option B: Render or Fly.io
1. Create a Web Service pointing to the repository.
2. Build command:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Start command:
   ```bash
   cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

---

## 4. Setting Up New Users (Tenant Walkthrough)

1. **Sign Up**:
   Navigate to your Vercel URL and click **Get Started Free**. Enter an email and password, or click **⚡ Quick-fill demo account**.
2. **Setup Wizard**:
   The 5-step guided wizard walks you through:
   - **Step 1:** Verifying Qdrant Cloud semantic memory.
   - **Step 2:** Verifying the Lyzr Multi-Agent triad.
   - **Step 3:** Linking your Telegram bot via `@Ididhswkje_bot` with one-tap `/start pair_<code}>`.
   - **Step 4:** Copying your unique Omi Webhook URL (`https://.../omi/v2/<token>/conversation`).
   - **Step 5:** Verifying Google Calendar, Tasks, and Gmail integrations.
3. **Voice Interaction**:
   Speak into your Omi wearable device. Once the session finishes, Omi sends the conversation to your webhook URL. LifeOS autonomously indexes your memories, coordinates the Lyzr Triad, executes low-risk actions, and sends Telegram approvals for review.
