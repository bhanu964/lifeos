import asyncio
import logging
from typing import Any, Dict, List, Optional
import uuid

from qdrant_client import AsyncQdrantClient, models
from fastembed import TextEmbedding

from app.config import settings
from app.models.memory import MemoryItem

logger = logging.getLogger(__name__)


class QdrantService:
    """
    Qdrant Cloud vector database service for AgentMemory AI.
    Handles connection verification, collection lifecycle, FastEmbed embedding generation,
    memory storage, semantic search, user-scoped retrieval, and deletion.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_model: Optional[TextEmbedding] = None,
    ):
        self.url = url if url is not None else settings.qdrant_url
        self.api_key = api_key if api_key is not None else settings.qdrant_api_key
        self.collection_name = collection_name if collection_name is not None else settings.qdrant_collection_name
        self.embedding_model_name = settings.embedding_model_name
        self.embedding_dim = settings.embedding_dim

        self._client: Optional[AsyncQdrantClient] = None
        self._embedding_model = embedding_model

    @property
    def client(self) -> AsyncQdrantClient:
        """Lazily initialize the AsyncQdrantClient."""
        if self._client is None:
            if not self.url:
                raise ValueError("QDRANT_URL is not configured.")
            self._client = AsyncQdrantClient(
                url=self.url,
                api_key=self.api_key or None,
                timeout=30.0,
            )
        return self._client

    @property
    def embedding_model(self) -> TextEmbedding:
        """Lazily initialize the FastEmbed TextEmbedding model."""
        if self._embedding_model is None:
            logger.info("Initializing FastEmbed model: %s", self.embedding_model_name)
            self._embedding_model = TextEmbedding(model_name=self.embedding_model_name)
        return self._embedding_model

    async def verify_connection(self) -> bool:
        """Verify network and authentication connectivity to Qdrant Cloud."""
        try:
            await self.client.get_collections()
            return True
        except Exception as e:
            logger.error("Qdrant connection verification failed: %s", e)
            return False

    async def init_collection(self) -> bool:
        """
        Verify if the 384-dim cosine collection exists, creating it if needed.
        Also configures payload index on 'uid' for high-performance tenant isolation.
        """
        try:
            collections_res = await self.client.get_collections()
            existing_names = {c.name for c in collections_res.collections}

            if self.collection_name not in existing_names:
                logger.info(
                    "Creating Qdrant collection '%s' with %d-dim cosine distance",
                    self.collection_name,
                    self.embedding_dim,
                )
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.embedding_dim,
                        distance=models.Distance.COSINE,
                    ),
                )

                # Create payload index for user isolation
                try:
                    await self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="uid",
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
                except Exception as idx_err:
                    logger.warning("Could not create payload index on 'uid': %s", idx_err)

            return True
        except Exception as e:
            logger.error("Failed to initialize Qdrant collection '%s': %s", self.collection_name, e)
            raise

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a 384-dimensional dense vector using FastEmbed offloaded to threadpool."""
        if not text or not text.strip():
            return [0.0] * self.embedding_dim

        def _embed():
            generator = self.embedding_model.embed([text])
            return list(next(generator))

        vector = await asyncio.to_thread(_embed)
        return [float(x) for x in vector]

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings for multiple texts."""
        if not texts:
            return []

        def _batch_embed():
            return [list(vec) for vec in self.embedding_model.embed(texts)]

        vectors = await asyncio.to_thread(_batch_embed)
        return [[float(x) for x in vec] for vec in vectors]

    async def store_memory(self, memory: MemoryItem) -> str:
        """Store a single memory in Qdrant with user scoping."""
        vector = await self.generate_embedding(memory.content)
        point_id = memory.id

        # Validate that point_id is a valid UUID or generate deterministic UUID
        try:
            uuid.UUID(str(point_id))
        except ValueError:
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{memory.uid}:{point_id}"))

        payload = {
            "id": memory.id,
            "uid": memory.uid,
            "content": memory.content,
            "metadata": memory.metadata,
            "created_at": memory.created_at,
        }

        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        return memory.id

    async def store_memories(self, memories: List[MemoryItem]) -> List[str]:
        """Store a batch of memories in Qdrant efficiently."""
        if not memories:
            return []

        texts = [m.content for m in memories]
        vectors = await self.generate_embeddings(texts)

        points = []
        stored_ids = []
        for memory, vector in zip(memories, vectors):
            point_id = memory.id
            try:
                uuid.UUID(str(point_id))
            except ValueError:
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{memory.uid}:{point_id}"))

            payload = {
                "id": memory.id,
                "uid": memory.uid,
                "content": memory.content,
                "metadata": memory.metadata,
                "created_at": memory.created_at,
            }
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )
            stored_ids.append(memory.id)

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        return stored_ids

    async def search_memories(
        self,
        uid: str,
        query: str,
        limit: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[MemoryItem]:
        """
        Perform user-scoped semantic search over stored memories.
        Strictly filters on the provided uid.
        """
        if not query or not query.strip():
            return []

        query_vector = await self.generate_embedding(query)

        user_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="uid",
                    match=models.MatchValue(value=uid),
                )
            ]
        )

        try:
            # First try standard search method
            search_results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=user_filter,
                limit=limit,
                score_threshold=score_threshold,
            )
        except Exception:
            # Fallback for newer query_points interface
            query_res = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=user_filter,
                limit=limit,
                score_threshold=score_threshold,
            )
            search_results = query_res.points

        memories = []
        for pt in search_results:
            payload = pt.payload or {}
            memories.append(
                MemoryItem(
                    id=str(payload.get("id", pt.id)),
                    uid=payload.get("uid", uid),
                    content=payload.get("content", ""),
                    metadata=payload.get("metadata", {}),
                    score=float(pt.score) if pt.score is not None else None,
                    created_at=payload.get("created_at", ""),
                )
            )
        return memories

    async def delete_memory(self, memory_id: str, uid: str) -> bool:
        """
        Delete a memory by ID while strictly enforcing user ownership.
        """
        # Resolve the point ID stored in Qdrant
        try:
            uuid.UUID(str(memory_id))
            point_id = memory_id
        except ValueError:
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{uid}:{memory_id}"))

        # Delete strictly matching both the point ID and the user ID
        id_selector = models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.HasIdCondition(has_id=[point_id]),
                    models.FieldCondition(
                        key="uid",
                        match=models.MatchValue(value=uid),
                    ),
                ]
            )
        )
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=id_selector,
        )

        return True

    async def list_memories(self, uid: str, limit: int = 50) -> List[MemoryItem]:
        """List memories for a specific user."""
        user_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="uid",
                    match=models.MatchValue(value=uid),
                )
            ]
        )

        scroll_res, _ = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=user_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        memories = []
        for pt in scroll_res:
            payload = pt.payload or {}
            memories.append(
                MemoryItem(
                    id=str(payload.get("id", pt.id)),
                    uid=payload.get("uid", uid),
                    content=payload.get("content", ""),
                    metadata=payload.get("metadata", {}),
                    created_at=payload.get("created_at", ""),
                )
            )
        return memories

    async def close(self):
        """Cleanly close underlying Qdrant client."""
        if self._client is not None:
            await self._client.close()
            self._client = None
