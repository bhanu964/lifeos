# Changelog

All notable changes to the **LifeOS** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-13

### Added
- **Multi-Tenant SaaS Foundation**: Complete tenant isolation, user signup/login with JWT HS256 auth, and encrypted credential management (`UserDB`, `UserIntegrationDB`).
- **Fernet AES-128 Credential Encryption**: User tokens and integration secrets are securely encrypted at rest.
- **Dynamic API Base URL**: Replaced all hardcoded localhost/ngrok endpoints in the React/Vite frontend with centralized `apiConfig.ts` driven by `VITE_API_BASE_URL`.
- **Durable State Persistence**: Database-backed `WorkflowDB` and `ActionDB` models with SQLite / PostgreSQL support to survive server restarts.
- **Lyzr Multi-Agent Triad**: Collaborative architecture incorporating Lyzr Manager (orchestrator), Lyzr Fact Finder (context specialist), and Lyzr Data Analyst (temporal & schedule specialist).
- **Qdrant Semantic Memory Loop**: Dual-stage FastEmbed vectorization (`BAAI/bge-small-en-v1.5`, 384 dimensions) with payload-level tenant isolation.
- **Omi Webhook Ingestion**: Dual deduplication engine utilizing UUID5 namespace hashing and SHA-256 workflow idempotency keys.
- **Telegram Human-in-the-Loop Gateway**: Mobile approval buttons for high-risk actions and push updates for autonomous completions.
- **Production Deployment Configuration**:
  - `backend/Dockerfile` for containerization.
  - `railway.json` and `render.yaml` for one-click backend deployment.
  - `vercel.json` (root and frontend) for edge SPA hosting.
- **Documentation Suite**: Complete operational and architecture guides in `docs/` (`architecture.md`, `SETUP.md`, `VERCEL_DEPLOYMENT.md`, `BACKEND_DEPLOYMENT.md`, `OMI_SETUP.md`, `TELEGRAM_SETUP.md`, `QDRANT_SETUP.md`, `LYZR_SETUP.md`, `SECURITY.md`).

### Fixed
- Calendar inspection autonomous execution loop: low-risk operations now execute automatically without waiting for frontend dashboard clicks.
- CORS policy hardened to reject arbitrary origins while allowing explicit configured domains and `*.vercel.app` preview deployments.
- Missing production configuration banner in frontend to guide operators when `VITE_API_BASE_URL` is omitted.
