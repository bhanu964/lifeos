# AgentMemory AI - API Specification

Base URL: `http://localhost:8000`

---

## 1. System Health

### `GET /health`
Returns service status and configuration flags.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "app_name": "AgentMemory AI",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-10-13T10:00:00.000000+00:00",
  "integrations": {
    "lyzr_configured": true,
    "qdrant_configured": true,
    "omi_configured": true
  }
}
```

---

## 2. Omi Webhook Integration

### `POST /omi/conversation`
Captures completed listening sessions from Omi.

**Query Parameters:**
- `uid` *(optional)*: User ID.

**Request Body:**
```json
{
  "id": "conv-9921",
  "created_at": "2026-10-13T09:30:00Z",
  "transcript_segments": [
    {
      "text": "Let's make sure the Qdrant connector uses 384 dimensional embeddings.",
      "speaker": "SPEAKER_00",
      "speaker_name": "Bhanu",
      "is_user": true,
      "start": 1.2,
      "end": 5.4
    }
  ],
  "structured": {
    "title": "Vector DB Configuration",
    "overview": "Team aligned on FastEmbed model specs.",
    "category": "engineering",
    "action_items": [
      { "description": "Configure FastEmbed BAAI/bge-small-en-v1.5", "completed": true }
    ]
  },
  "discarded": false
}
```

**Response `200 OK`**:
```json
{
  "status": "success",
  "message": "Ingested 2 memory items from conversation.",
  "processed_count": 2,
  "memory_id": "conv-9921"
}
```

---

### `POST /omi/realtime`
Ingests incremental real-time transcript streaming.

**Query Parameters:**
- `uid` *(optional)*: User ID.
- `session_id` *(optional)*: Live listening session ID.

**Request Body (Object Format):**
```json
{
  "session_id": "live-session-12",
  "segments": [
    {
      "text": "Remember to submit before the hackathon cutoff.",
      "speaker": "SPEAKER_00",
      "is_user": true,
      "start": 12.0,
      "end": 15.0
    }
  ]
}
```

*(Note: Raw array payloads `[ { "text": "..." } ]` are also natively supported).*

**Response `200 OK`**:
```json
{
  "status": "success",
  "message": "Ingested 1 real-time segments.",
  "processed_count": 1,
  "session_id": "live-session-12"
}
```

---

## 3. Collaborative Agent Workflow

### `POST /api/ask`
Queries the Lyzr Research Agent with user-scoped vector memories retrieved from Qdrant Cloud.

**Request Body:**
```json
{
  "uid": "demo-user",
  "question": "What did I discuss earlier regarding vector dimensions?"
}
```

**Response `200 OK`**:
```json
{
  "answer": "Earlier you discussed ensuring that the Qdrant connector uses 384-dimensional embeddings generated with FastEmbed BAAI/bge-small-en-v1.5.",
  "supporting_memories": [
    {
      "id": "312cfa23-...",
      "uid": "demo-user",
      "content": "Bhanu: Let's make sure the Qdrant connector uses 384 dimensional embeddings.",
      "metadata": {
        "speaker": "Bhanu",
        "source": "omi_conversation_segment"
      },
      "score": 0.884,
      "created_at": "2026-10-13T09:30:00Z"
    }
  ],
  "execution_events": [
    {
      "step": "request_validation",
      "timestamp": "2026-10-13T10:01:00.100Z",
      "status": "completed",
      "details": { "uid": "demo-user", "question_length": 51 }
    },
    {
      "step": "memory_retrieval",
      "timestamp": "2026-10-13T10:01:00.120Z",
      "status": "completed",
      "details": { "count": 1, "scores": [0.884] }
    },
    {
      "step": "prompt_synthesis",
      "timestamp": "2026-10-13T10:01:00.150Z",
      "status": "completed",
      "details": { "status": "RETRIEVED 1 RELEVANT MEMORIES" }
    },
    {
      "step": "agent_reasoning",
      "timestamp": "2026-10-13T10:01:01.400Z",
      "status": "completed",
      "details": { "agent_id": "6acd9f07cb0aafc9293bd126", "answer_length": 142 }
    }
  ],
  "agent_id": "6acd9f07cb0aafc9293bd126",
  "session_id": "session-demo-user-1a2b3c4d"
}
```

---

## 4. Vector Memory Management

### `GET /api/memories`
List memories for a specific user.
- Query: `uid=demo-user&limit=20`

### `POST /api/memories`
Store a custom memory into Qdrant.
```json
{
  "uid": "demo-user",
  "content": "Research meeting with Dr. Smith regarding protein folding models.",
  "metadata": { "tag": "science" }
}
```

### `POST /api/memories/search`
Perform direct semantic vector search.
```json
{
  "uid": "demo-user",
  "query": "protein models",
  "limit": 5,
  "score_threshold": 0.25
}
```

### `DELETE /api/memories/{memory_id}`
Delete a memory point by ID safely scoped to `uid`.
- Query: `uid=demo-user`
