# LifeOS — Qdrant Cloud Vector Memory Setup

LifeOS utilizes **Qdrant Cloud** as its distributed, high-performance semantic memory store. This document explains how Qdrant is configured, how vector embeddings are generated, and how multi-tenant isolation is enforced.

---

## 1. Qdrant Cloud Provisioning

1. Sign up for a free or production cluster at [cloud.qdrant.io](https://cloud.qdrant.io).
2. Create a new cluster (default AWS or GCP region).
3. Copy your **Cluster URL** (e.g. `https://xxx-yyy.eu-west-1-0.aws.cloud.qdrant.io:6333`).
4. Generate an **API Key** with read/write permissions.
5. Set these in your `.env`:
   ```ini
   QDRANT_URL=https://your-cluster-id.eu-west-1-0.aws.cloud.qdrant.io:6333
   QDRANT_API_KEY=your_qdrant_api_key_here
   QDRANT_COLLECTION_NAME=agentmemory_memories
   ```

---

## 2. FastEmbed Embedding Architecture

LifeOS generates dense semantic vectors locally on the backend using **FastEmbed**:

- **Model**: `BAAI/bge-small-en-v1.5`
- **Vector Dimensions**: `384`
- **Distance Metric**: `Cosine`
- **Performance**: Embeddings are computed in sub-5ms on CPU and executed asynchronously via `asyncio.to_thread` to prevent blocking the FastAPI event loop.

---

## 3. Auto-Collection Provisioning

Upon backend initialization, `MemoryService._ensure_collection()` checks if the collection exists. If not, it creates it automatically:

```python
client.create_collection(
    collection_name="agentmemory_memories",
    vectors_config=models.VectorParams(
        size=384,
        distance=models.Distance.COSINE,
    )
)
```

---

## 4. Multi-Tenant Payload Isolation

To guarantee privacy, every vector point stored in Qdrant contains payload metadata with the user's `uid`:

```json
{
  "id": "e4b2a8d1-...",
  "vector": [0.024, -0.012, ...],
  "payload": {
    "uid": "usr_9f8e2a1b",
    "content": "LifeOS Verified Google Calendar Inspection: Date 2026-10-14...",
    "source": "lifeos_action_execution",
    "timestamp": "2026-10-13T16:50:00Z"
  }
}
```

### Mandatory Query Filtering:
Every similarity search strictly filters by `uid`:
```python
query_filter = models.Filter(
    must=[
        models.FieldCondition(
            key="uid",
            match=models.MatchValue(value=uid)
        )
    ]
)
```
No user can ever query or retrieve vector points belonging to another tenant.

---

## 5. Memory Retrieval Threshold & Anti-Hallucination Guardrail

During workflow Stage 3 (`memory_retrieved`):
- If the cosine similarity score of top points is below `0.40`, LifeOS explicitly injects:
  ```text
  NO_RELEVANT_MEMORIES_AVAILABLE
  ```
- This prevents the Lyzr agent from hallucinating false context from unrelated prior conversations.
