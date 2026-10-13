# LifeOS — Pre-Deployment Comprehensive Codebase Audit
**Project:** LifeOS — Voice-First Personal AI Operator  
**Hackathon:** Stop Prompting, Solo Agents Hackathon 2026 (Track 2)  
**Date:** October 2026  
**Auditor:** LifeOS Automated Agentic Auditor  

---

## Executive Summary

This comprehensive audit inspects every component across the `frontend/`, `backend/`, configuration files, dependencies, database models, and deployment targets to prepare LifeOS for public multi-tenant SaaS deployment on Vercel (Frontend) and Railway/Render (FastAPI Persistent Backend).

---

## 1. Inventory of Localhost URLs

The audit identified the following localhost URLs across the repository:

| File Location | Line / Context | Code Snippet | Issue & Remediation |
| :--- | :--- | :--- | :--- |
| `frontend/src/components/LivePipelineObservabilityView.tsx` | Line 114 | `fetch("http://localhost:8000/omi/conversation?uid=...")` | **CRITICAL BUG**: Bypasses shared API client; fails in production when deployed to Vercel. Must be routed through central `api.simulateVoiceInput()` or `api.getBaseUrl()`. |
| `frontend/src/services/api.ts` | Line 22 | `VITE_API_BASE_URL \|\| 'http://localhost:8000'` | **SILENT FALLBACK**: In a production build, missing `VITE_API_BASE_URL` silently calls localhost instead of rendering an actionable configuration error. |
| `frontend/src/components/IntegrationsSettingsView.tsx` | Line 79 | `const omiUrl = ...` | Uses `api.getBaseUrl()` which inherits the localhost fallback if unconfigured. |

---

## 2. Inventory of Hardcoded ngrok URLs

| File Location | Line / Context | Value | Remediation |
| :--- | :--- | :--- | :--- |
| `backend/app/config.py` | Line 117 | `default="https://unresidential-ultracentrifugally-mao.ngrok-free.dev"` | **LEAK RISK**: Hardcoded temporary development ngrok tunnel as the fallback for `PUBLIC_BASE_URL`. Must default to empty or standard production environment variable check. |
| `frontend/src/components/ConversationActivityView.tsx` | Line 50 | Mention of `"public ngrok webhook tunnel"` in UI copy | Update UI text to reference dynamic public HTTPS webhook tunnel. |

---

## 3. Inventory of Hardcoded Backend URLs

| Location | Hardcoded Value | Scope / Risk | Remediation |
| :--- | :--- | :--- | :--- |
| `backend/app/config.py` | `lyzr_api_url: "https://agent-prod.studio.lyzr.ai/v3/inference/chat/"` | External API endpoint (Lyzr production) | Keep configurable via `LYZR_API_URL` env var. |
| `backend/app/config.py` | `lyzr_tool_execute_url: "https://agent-prod.studio.lyzr.ai/v3/inference/tools/execute"` | External API endpoint (Lyzr tools) | Keep configurable via `LYZR_TOOL_EXECUTE_URL` env var. |
| `backend/app/services/user_credentials_service.py` | `https://api.telegram.org/bot<token>/getMe` | Telegram Bot API verification | Valid external official API endpoint. |

---

## 4. Frontend Requests Bypassing Shared API Client

| Component | Target Route | Issue |
| :--- | :--- | :--- |
| `frontend/src/components/LivePipelineObservabilityView.tsx` | `/omi/conversation` (Line 114) | Uses direct `window.fetch()` with hardcoded `http://localhost:8000`. Does not attach Bearer token or respect `VITE_API_BASE_URL`. |

*All other frontend components correctly route through `frontend/src/services/api.ts`.*

---

## 5. Environment Variables Required for Production

### Frontend (`frontend/.env.production`)
- `VITE_API_BASE_URL`: **REQUIRED**. The public HTTPS URL of the deployed FastAPI backend (e.g., `https://lifeos-api.up.railway.app`).

### Backend (`backend/.env` / Container Host)
- `APP_ENV`: `production`
- `PORT`: `8000` (or injected by Railway/Render)
- `PUBLIC_BASE_URL`: **REQUIRED**. The public HTTPS URL of the backend (used for generating Omi webhook endpoints and Telegram webhooks).
- `JWT_SECRET_KEY`: **REQUIRED**. High-entropy 32+ character secret for signing user session JWTs.
- `ENCRYPTION_KEY`: **REQUIRED**. 32-byte urlsafe-base64 Fernet key for encrypting user credentials at rest.
- `DATABASE_URL`: **REQUIRED FOR PERSISTENCE**. PostgreSQL connection string (`postgresql://...`) or persistent volume SQLite (`sqlite:////app/data/lifeos_saas.db`).
- `CORS_ALLOWED_ORIGINS`: **REQUIRED**. Comma-separated list of allowed frontend origins (e.g. `https://lifeos.vercel.app,https://lifeos-preview.vercel.app`).
- `QDRANT_URL`: Managed cluster endpoint.
- `QDRANT_API_KEY`: Managed cluster API key.
- `QDRANT_COLLECTION_NAME`: Default `agentmemory_memories`.
- `LYZR_API_KEY`: Studio API key.
- `LYZR_MANAGER_AGENT_ID`: Default `6acdcd0f8a6a8741bd6df3df`.
- `LYZR_FACT_FINDER_AGENT_ID`: Default `6acd9f07cb0aafc9293bd126`.
- `LYZR_DATA_ANALYST_AGENT_ID`: Default `6acd1ec70b4f09cf4da21e21`.
- `TELEGRAM_BOT_TOKEN`: BotFather token for `@Ididhswkje_bot`.
- `TELEGRAM_BOT_USERNAME`: `Ididhswkje_bot`.
- `GOOGLE_CALENDAR_CREDENTIAL_ID`: Composio OAuth credential.
- `GOOGLE_TASKS_CREDENTIAL_ID`: Composio OAuth credential.
- `GMAIL_CREDENTIAL_ID`: Composio OAuth credential.

---

## 6. Endpoints Requiring Public HTTPS Backend

1. **Omi Conversation Webhook**: `POST /omi/v2/{webhook_token}/conversation`  
   The Omi iOS/Android mobile apps require a publicly accessible HTTPS endpoint to deliver transcripts when the user stops speaking.
2. **Omi Realtime Webhook**: `POST /omi/v2/{webhook_token}/realtime`  
   Real-time streaming transcript chunks.
3. **Telegram Bot Webhook**: `POST /api/telegram/webhook`  
   Telegram Bot API requires a verified HTTPS webhook to deliver interactive callback button taps (`[Approve]`, `[Reject]`) and `/start` commands.
4. **Server-Sent Events (SSE)**: `GET /api/lifeos/events`  
   Cross-origin browser SSE connection from Vercel frontend to backend.

---

## 7. Dependencies on Local Files & Process-Local State

| State Artifact | Current Implementation | Failure Mode on Restart | Remediation |
| :--- | :--- | :--- | :--- |
| `WorkflowRecord` items | `_workflows` dict + `data/workflows.json` | Local JSON erased on container redeploy | Back with `WorkflowDB` table in SQLAlchemy (`DATABASE_URL`). |
| `StagedAction` items | `_actions` in-memory dict in `ActionService` | All pending approvals lost on container restart | Back with `ActionDB` table in SQLAlchemy (`DATABASE_URL`). |
| Telegram state | `data/telegram_state.json` | Chat ID mappings lost on redeploy | Store in `UserDB.telegram_chat_id`. |
| SSE Subscribers | `_subscribers: List[asyncio.Queue]` | Valid per-process subscription | Safe for single-worker persistent containers. |

---

## 8. Secrets and Credentials Audit

1. **Committed Defaults in `config.py`**:
   - `TELEGRAM_BOT_TOKEN`: Had fallback value `8364330229:AAEnA_...` in code. Must be removed from default and strictly loaded from environment.
   - `PUBLIC_BASE_URL`: Had fallback to a personal ngrok URL.
2. **Git Tracking**:
   - `.env` is properly excluded in `.gitignore`.
   - `QdrantAPIKEY*` is excluded in `.gitignore`.
   - SQLite files `*.db`, `*.sqlite` are excluded in `.gitignore`.

---

## 9. Issues Preventing Deployment & Action Plan

| Issue | Impact | Action Required |
| :--- | :--- | :--- |
| Wildcard CORS `allow_origins=["*"]` with credentials | Browsers reject authenticated cross-origin requests from Vercel | Implement explicit origin validation matching Vercel domains. |
| Incomplete `backend/requirements.txt` | Railway/Render fails to build because `sqlalchemy`, `cryptography`, `pyjwt` are missing | Regenerate `requirements.txt` with all pinned dependencies. |
| Missing `Dockerfile` in `backend/` | Container hosts cannot containerize Python 3.12 app | Create optimized multi-stage `Dockerfile`. |
| Vercel root ambiguity | Monorepo without root `package.json` | Document Vercel project root as `frontend/` and configure rewrites. |
| Missing Production DB models for workflows & actions | Restart wipes workflow progress | Create `WorkflowDB` and `ActionDB` models in SQLAlchemy. |
