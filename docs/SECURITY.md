# LifeOS — Security Architecture & Threat Model

LifeOS is designed with defense-in-depth principles to safeguard personal user data, voice transcripts, and external service credentials.

---

## 1. Security Tenets

1. **Zero Client Secrets**: The frontend client never receives or stores raw external API keys (`LYZR_API_KEY`, `QDRANT_API_KEY`, `TELEGRAM_BOT_TOKEN`, Google OAuth secrets). All integrations are managed server-side.
2. **Strict Multi-Tenant Isolation**: No tenant can view, query, or execute operations against another user's workflows, memories, or integrations.
3. **Encryption at Rest**: User-specific credentials and tokens are encrypted before being written to disk or database.
4. **Human-in-the-Loop Safeguards**: Destructive or outbound actions (email drafting, calendar modification, task creation) require explicit authorization.

---

## 2. Authentication & Session Management

- **Protocol**: JWT (JSON Web Tokens) signed with HMAC-SHA256 (`HS256`).
- **Token Expiry**: 72 hours by default.
- **Header**: Standard HTTP `Authorization: Bearer <token>`.
- **Password Hashing**: PBKDF2-HMAC-SHA256 with 100,000 iterations and a 16-byte cryptographically secure random salt (`crypto_service.py`).
- **Tenant Extraction**: The `get_current_user` FastAPI dependency extracts and validates the token subject (`sub`), verifying the user exists before granting request execution.

---

## 3. Cryptographic Storage of Credentials

User integrations (Google Calendar, Tasks, Gmail, Telegram) are persisted in the `user_integrations` table:

```python
encrypted_payload = Fernet(ENCRYPTION_KEY).encrypt(json.dumps(credentials).encode())
```

- **Algorithm**: Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256 authentication).
- **Key Generation**: A 32-byte URL-safe base64-encoded key configured via the `ENCRYPTION_KEY` environment variable.
- **Masking**: When returning integration status to the frontend, credential values are masked (e.g. `••••••••9cb4`).

---

## 4. Omi Webhook Ingestion Security

Voice input endpoints (`/omi/conversation`, `/omi/realtime`) use token-based authorization:

- Each user is assigned a cryptographically random webhook token (`omi_webhook_token`) during signup.
- Requests without a valid matching `?token=<omi_webhook_token>` are immediately rejected with `401 Unauthorized`.
- Deduplication keys prevent replay attacks.

---

## 5. Network Security & CORS

- **CORS Policy**: Configured explicitly using `CORS_ALLOWED_ORIGINS`.
- **Preview Domains**: Vercel preview deployments are permitted using a secure regex (`r"^https://.*\.vercel\.app$"`), while rejecting arbitrary origins.
- **Server-Sent Events (SSE)**: The real-time stream endpoint `/api/lifeos/events?token=<jwt>` requires a valid JWT query parameter and filters events server-side by `user_id`.

---

## 6. Threat Modeling & Mitigation Matrix

| Threat Vector | Mitigation Strategy |
| :--- | :--- |
| **Cross-Tenant Vector Bleed** | Qdrant searches enforce mandatory payload filter: `uid == current_user_id`. |
| **Credential Exfiltration from DB** | Credentials encrypted with AES-128 Fernet key held in server environment. |
| **Webhook Replay Attack** | SHA-256 idempotency hash deduplicates transcripts; duplicate calls return cached status. |
| **Accidental Email Transmission** | Gmail integration creates **Drafts only**; no automated email dispatch. |
| **Brute Force Login** | PBKDF2 computation delay (100k rounds) rate limits offline hash cracking. |
