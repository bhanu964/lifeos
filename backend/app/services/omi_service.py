from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from app.config import settings
from app.models.memory import MemoryItem
from app.models.omi import (
    ConversationPayload,
    RealtimePayload,
    TranscriptSegment,
)
from app.services.qdrant_service import QdrantService
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)


class OmiService:
    """
    Service responsible for ingesting, parsing, and deduplicating voice transcripts
    received via Omi webhook integrations into Qdrant vector memory, and automatically
    triggering the LifeOS autonomous multi-agent pipeline upon conversation completion.
    """

    def __init__(
        self,
        qdrant_service: Optional[QdrantService] = None,
        workflow_service: Optional[WorkflowService] = None,
    ):
        self.qdrant = qdrant_service or QdrantService()
        self.workflow_service = workflow_service or WorkflowService()

    @staticmethod
    def _generate_segment_id(uid: str, session_or_conv_id: str, text: str, start: Optional[float] = None) -> str:
        """
        Produce a deterministic UUID5 to guarantee idempotency and avoid duplicate
        transcript segments in the vector store.
        """
        normalized_text = " ".join(text.strip().lower().split())
        start_str = f":{start}" if start is not None else ""
        key = f"{uid}:{session_or_conv_id}{start_str}:{normalized_text}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))

    async def process_conversation_webhook(
        self,
        payload: ConversationPayload,
        uid_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes a completed conversation webhook payload from Omi.
        Ingests structured insights and all non-empty transcript segments.
        """
        # Determine effective user ID
        uid = uid_param or payload.uid or settings.lyzr_user_id or "default-user"
        conv_id = payload.id or payload.session_id or str(uuid.uuid4())

        if payload.discarded:
            logger.info("Discarded conversation %s ignored for user %s", conv_id, uid)
            return {
                "status": "ignored",
                "message": "Conversation marked as discarded by Omi",
                "processed_count": 0,
                "memory_id": conv_id,
            }

        memories_to_store: List[MemoryItem] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Ingest Structured Overview if present
        if payload.structured:
            st = payload.structured
            overview_parts = []
            if st.title:
                overview_parts.append(f"Title: {st.title}")
            if st.overview:
                overview_parts.append(f"Summary: {st.overview}")
            if st.action_items:
                act_str = "; ".join([
                    item.get("description", str(item)) if isinstance(item, dict) else item.description
                    for item in st.action_items
                ])
                overview_parts.append(f"Action Items: {act_str}")

            if overview_parts:
                structured_content = "\n".join(overview_parts)
                summary_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{uid}:{conv_id}:summary"))
                memories_to_store.append(
                    MemoryItem(
                        id=summary_id,
                        uid=uid,
                        content=structured_content,
                        metadata={
                            "source": "omi_conversation_summary",
                            "conversation_id": conv_id,
                            "category": st.category,
                            "title": st.title,
                            "started_at": payload.started_at,
                            "finished_at": payload.finished_at,
                        },
                        created_at=payload.created_at or now_iso,
                    )
                )

        # 2. Ingest Transcript Segments
        raw_segments = payload.transcript_segments or payload.segments or []
        seen_keys = set()

        for seg in raw_segments:
            seg_text = seg.text.strip()
            if not seg_text:
                continue

            # In-memory deduplication within the payload
            deterministic_id = self._generate_segment_id(uid, conv_id, seg_text, seg.start)
            if deterministic_id in seen_keys:
                continue
            seen_keys.add(deterministic_id)

            speaker_tag = seg.speaker_name or seg.speaker or ("User" if seg.is_user else "Speaker")
            speaker_prefix = f"{speaker_tag}: {seg_text}"

            memories_to_store.append(
                MemoryItem(
                    id=deterministic_id,
                    uid=uid,
                    content=speaker_prefix,
                    metadata={
                        "source": "omi_conversation_segment",
                        "conversation_id": conv_id,
                        "speaker": speaker_tag,
                        "is_user": bool(seg.is_user),
                        "start": seg.start,
                        "end": seg.end,
                    },
                    created_at=payload.created_at or now_iso,
                )
            )

        user_qdrant = self.qdrant
        try:
            from app.services.user_credentials_service import UserCredentialsService
            user_qdrant = UserCredentialsService.get_qdrant_service_for_user(uid)
        except Exception:
            pass

        if memories_to_store:
            await user_qdrant.store_memories(memories_to_store)

        logger.info(
            "Successfully ingested %d memories from Omi conversation %s for user %s",
            len(memories_to_store),
            conv_id,
            uid,
        )

        # 3. Automatically trigger the LifeOS Multi-Agent Pipeline
        full_transcript = " ".join([seg.text.strip() for seg in raw_segments if seg.text.strip()])
        if not full_transcript and payload.structured:
            full_transcript = payload.structured.overview or payload.structured.title or ""

        workflow = None
        if full_transcript:
            try:
                workflow = await self.workflow_service.create_and_enqueue_workflow(
                    uid=uid,
                    conversation_id=conv_id,
                    transcript=full_transcript,
                )
                logger.info("Enqueued LifeOS workflow %s for conversation %s", workflow.workflow_id, conv_id)
            except Exception as wf_err:
                logger.error("Failed to enqueue workflow for conversation %s: %s", conv_id, wf_err, exc_info=True)

        return {
            "status": "success",
            "message": f"Ingested {len(memories_to_store)} memories and triggered LifeOS operator pipeline.",
            "processed_count": len(memories_to_store),
            "memory_id": conv_id,
            "workflow_id": workflow.workflow_id if workflow else None,
        }

    async def process_realtime_webhook(
        self,
        segments: List[TranscriptSegment],
        uid_param: Optional[str] = None,
        session_id_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes real-time streaming speech chunks from Omi.
        Saves each segment to Qdrant with deterministic deduplication.
        """
        uid = uid_param or settings.lyzr_user_id or "default-user"
        session_id = session_id_param or "live-session"
        now_iso = datetime.now(timezone.utc).isoformat()

        memories_to_store: List[MemoryItem] = []
        seen_keys = set()

        for seg in segments:
            seg_text = seg.text.strip()
            if not seg_text:
                continue

            deterministic_id = self._generate_segment_id(uid, session_id, seg_text, seg.start)
            if deterministic_id in seen_keys:
                continue
            seen_keys.add(deterministic_id)

            speaker_tag = seg.speaker_name or seg.speaker or ("User" if seg.is_user else "Speaker")
            speaker_prefix = f"{speaker_tag}: {seg_text}"

            memories_to_store.append(
                MemoryItem(
                    id=deterministic_id,
                    uid=uid,
                    content=speaker_prefix,
                    metadata={
                        "source": "omi_realtime_segment",
                        "session_id": session_id,
                        "speaker": speaker_tag,
                        "is_user": bool(seg.is_user),
                        "start": seg.start,
                        "end": seg.end,
                    },
                    created_at=now_iso,
                )
            )

        user_qdrant = self.qdrant
        try:
            from app.services.user_credentials_service import UserCredentialsService
            user_qdrant = UserCredentialsService.get_qdrant_service_for_user(uid)
        except Exception:
            pass

        if memories_to_store:
            await user_qdrant.store_memories(memories_to_store)

        logger.info(
            "Ingested %d real-time segments for session %s, user %s",
            len(memories_to_store),
            session_id,
            uid,
        )

        return {
            "status": "success",
            "message": f"Ingested {len(memories_to_store)} real-time segments.",
            "processed_count": len(memories_to_store),
            "session_id": session_id,
        }
