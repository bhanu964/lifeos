# LifeOS — Local Development & Setup Guide

This guide walks you through setting up and running LifeOS locally for development, testing, and evaluation.

---

## 1. Prerequisites

Ensure you have the following installed on your machine:

- **Python**: `3.12` or later (`python3 --version`)
- **Node.js**: `v18.0.0` or later (`node --version`)
- **npm**: `v9.0.0` or later (`npm --version`)
- **Git**: (`git --version`)

Optional but recommended for voice testing:
- **ngrok** or **localtunnel** (to expose local webhook port to the Omi mobile application)

---

## 2. Clone the Repository

```bash
git clone https://github.com/bhanu964/lifeos.git
cd lifeos
```

---

## 3. Backend Setup

### A. Create and Activate Virtual Environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### B. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### C. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```ini
# Core Configuration
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
PUBLIC_BASE_URL=http://localhost:8000
CORS_ALLOWED_ORIGINS=http://localhost:5173

# Security (Generate random keys)
# python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=your_random_32_byte_jwt_secret
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your_valid_fernet_key_here
DATABASE_URL=sqlite:///data/lifeos_saas.db

# Qdrant Cloud (Required for semantic memory)
QDRANT_URL=https://your-cluster-id.eu-west-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION_NAME=agentmemory_memories

# Lyzr Agent API (Required for Agent Triad)
LYZR_API_KEY=your_lyzr_api_key
LYZR_MANAGER_AGENT_ID=your_manager_agent_id
LYZR_FACT_FINDER_AGENT_ID=your_fact_finder_agent_id
LYZR_DATA_ANALYST_AGENT_ID=your_data_analyst_agent_id
LYZR_USER_ID=your_email@example.com

# Telegram Bot (Required for notifications & approval actions)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_from_botfather
TELEGRAM_BOT_USERNAME=your_bot_username
```

### D. Run the Backend Test Suite

Verify your installation:

```bash
pytest tests/ -v
```
All 74 unit, integration, and security tests should pass.

### E. Start the Backend Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Root / Health**: `http://localhost:8000/api/health`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

---

## 4. Frontend Setup

In a new terminal window:

```bash
cd frontend
npm install
```

### A. Configure Frontend Environment

```bash
cp .env.example .env
```

Ensure `.env` contains:

```ini
VITE_API_BASE_URL=http://localhost:8000
```

### B. Start the Frontend Development Server

```bash
npm run dev
```

Open your browser to: `http://localhost:5173`

---

## 5. Simulating a Spoken Request (No Hardware Required)

You do not need a physical Omi device to test LifeOS:

1. Open `http://localhost:5173` in your browser.
2. Sign up or log into your LifeOS tenant account.
3. In the **Live Pipeline Observability** view, use the **Simulate Spoken Input** terminal at the top right.
4. Enter:
   ```text
   Check my Google calendar for tomorrow. Tell me what meetings I have and how much free time is available.
   ```
5. Click **Trigger Live Pipeline**.
6. Observe all 10 nodes execute in real time via Server-Sent Events (SSE).
