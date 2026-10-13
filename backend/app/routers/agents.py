from datetime import datetime, timezone
import logging
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.models.agent import AskRequest, AskResponse, ExecutionEvent
from app.models.memory import MemoryItem
from app.services.lyzr_service import LyzrService, LyzrAPIError
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Agents"])


def get_memory_service() -> MemoryService:
    return MemoryService()


def get_lyzr_service() -> LyzrService:
    return LyzrService()


@router.post("/ask", response_model=AskResponse, summary="Query Lyzr agent with retrieved user memories")
async def ask_agent(
    request: AskRequest,
    memory_service: MemoryService = Depends(get_memory_service),
    lyzr_service: LyzrService = Depends(get_lyzr_service),
):
    """
    Collaborative Agent Reasoning Workflow:
    1. Validates the incoming query and user identity.
    2. Semantically retrieves user-scoped memories from Qdrant.
    3. Clearly distinguishes between present context and absence of memories.
    4. Submits question and contextual memories to the Lyzr Research Agent.
    5. Returns synthesized answer, citations of supporting memories, and full execution event trace.
    """
    events: List[ExecutionEvent] = []
    start_time = datetime.now(timezone.utc).isoformat()

    # Step 1: Validation
    clean_uid = request.uid.strip()
    clean_question = request.question.strip()
    if not clean_uid:
        raise HTTPException(status_code=400, detail="User ID ('uid') is required.")
    if not clean_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    events.append(
        ExecutionEvent(
            step="request_validation",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="completed",
            details={"uid": clean_uid, "question_length": len(clean_question)},
        )
    )

    # Step 2: Memory Retrieval from Qdrant
    retrieval_start = datetime.now(timezone.utc).isoformat()
    events.append(
        ExecutionEvent(
            step="memory_retrieval",
            timestamp=retrieval_start,
            status="started",
            details={"query": clean_question, "uid": clean_uid},
        )
    )

    retrieved_memories: List[MemoryItem] = []
    try:
        retrieved_memories = await memory_service.search_memories(
            uid=clean_uid,
            query=clean_question,
            limit=5,
            score_threshold=0.20,
        )
        events.append(
            ExecutionEvent(
                step="memory_retrieval",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="completed",
                details={
                    "count": len(retrieved_memories),
                    "memory_ids": [m.id for m in retrieved_memories],
                    "scores": [m.score for m in retrieved_memories if m.score is not None],
                },
            )
        )
    except Exception as exc:
        logger.error("Failed to retrieve memories from Qdrant: %s", exc)
        events.append(
            ExecutionEvent(
                step="memory_retrieval",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="failed",
                details={"error": str(exc)},
            )
        )
        # Continue reasoning even if vector search encounters an issue, but note absence
        retrieved_memories = []

    # Step 3: Format Context & Prompt Assembly
    if retrieved_memories:
        context_block = memory_service.format_memories_for_prompt(retrieved_memories)
        memory_indicator = f"RETRIEVED {len(retrieved_memories)} RELEVANT MEMORIES"
    else:
        context_block = "NO RELEVANT MEMORIES FOUND IN VECTOR STORE."
        memory_indicator = "NO_RELEVANT_MEMORIES"

    events.append(
        ExecutionEvent(
            step="prompt_synthesis",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="completed",
            details={"status": memory_indicator, "context_bytes": len(context_block)},
        )
    )

    # Construct strict anti-hallucination prompt for Lyzr agent
    prompt = f"""You are the AgentMemory AI reasoning assistant.
Answer the user's question accurately using ONLY the retrieved memories below if relevant.

--- RETRIEVED MEMORIES ---
{context_block}
--- END RETRIEVED MEMORIES ---

USER QUESTION:
{clean_question}

INSTRUCTIONS:
1. If relevant memories are provided above, synthesize a direct, clear answer citing the context.
2. If NO relevant memories are provided or the retrieved memories do not address the question, clearly state: "I could not find any relevant memories in your stored conversation history regarding this topic."
3. Never invent or hallucinate facts, memories, or actions.
4. If an action or plan was discussed, distinguish clearly between what was planned versus what was confirmed completed.
"""

    # Step 4: Collaborative Multi-Agent Orchestration
    session_id = request.session_id or f"session-{clean_uid}-{uuid.uuid4().hex[:8]}"
    specialist_outputs: Dict[str, str] = {}

    is_multi_agent = bool(settings.lyzr_manager_agent_id and settings.lyzr_data_analyst_agent_id)

    try:
        if is_multi_agent:
            # -------------------------------------------------------------
            # Stage 4a: Specialist 1 - Fact Finder Agent (6acd9f07cb0aafc9293bd126)
            # -------------------------------------------------------------
            ff_agent_id = settings.lyzr_fact_finder_agent_id or settings.lyzr_research_agent_id
            events.append(
                ExecutionEvent(
                    step="fact_finder_agent",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="started",
                    details={
                        "agent_id": ff_agent_id,
                        "agent_name": "Fact Finder Agent",
                        "role": "Verified fact and evidence extraction from voice memories",
                        "session_id": f"{session_id}-ff",
                    },
                )
            )

            ff_prompt = f"""You are the Fact Finder Agent in AgentMemory AI.
Identify and extract all verified factual statements from the retrieved memories regarding the user question.

IMPORTANT INSTRUCTIONS:
1. Distinguish between original spoken evidence (e.g. phonetically transcribed 'Quadrant' or 'Lyzer') and recognized normalized terminology ('Qdrant', 'Lyzr'). Note both what was verbally spoken and the normalized canonical name where context is clear.
2. Clearly separate explicit facts from absent or unmentioned information.
3. Never infer technical details that the speaker did not mention.

--- RETRIEVED MEMORIES ---
{context_block}
--- END RETRIEVED MEMORIES ---

USER QUESTION:
{clean_question}
"""
            ff_result = await lyzr_service.chat(
                message=ff_prompt,
                user_id=clean_uid,
                session_id=f"{session_id}-ff",
                agent_id=ff_agent_id,
            )
            fact_output = ff_result.get("response", "").strip()
            specialist_outputs["fact_finder"] = fact_output

            events.append(
                ExecutionEvent(
                    step="fact_finder_agent",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="completed",
                    details={
                        "agent_id": ff_agent_id,
                        "agent_name": "Fact Finder Agent",
                        "facts_length": len(fact_output),
                        "snippet": fact_output[:140] if fact_output else "",
                    },
                )
            )

            # -------------------------------------------------------------
            # Stage 4b: Specialist 2 - Verifiable Data Analyst (6acd1ec70b4f09cf4da21e21)
            # -------------------------------------------------------------
            da_agent_id = settings.lyzr_data_analyst_agent_id
            events.append(
                ExecutionEvent(
                    step="data_analyst_agent",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="started",
                    details={
                        "agent_id": da_agent_id,
                        "agent_name": "Verifiable Data Analyst",
                        "role": "Action item structuring, plan vs completion classification",
                        "session_id": f"{session_id}-da",
                    },
                )
            )

            da_prompt = f"""You are the Verifiable Data Analyst in AgentMemory AI.
Analyze the user question and the verified factual findings from the Fact Finder Agent.

IMPORTANT INSTRUCTIONS:
1. Distinguish original spoken evidence from normalized terminology (Qdrant, Lyzr).
2. Structure action items, and clearly differentiate between planned goals versus confirmed completions.
3. Do not infer technical details that the speaker did not mention.

VERIFIED FACTS FROM FACT FINDER:
{fact_output}

USER QUESTION:
{clean_question}
"""
            da_result = await lyzr_service.chat(
                message=da_prompt,
                user_id=clean_uid,
                session_id=f"{session_id}-da",
                agent_id=da_agent_id,
            )
            analyst_output = da_result.get("response", "").strip()
            specialist_outputs["data_analyst"] = analyst_output

            events.append(
                ExecutionEvent(
                    step="data_analyst_agent",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="completed",
                    details={
                        "agent_id": da_agent_id,
                        "agent_name": "Verifiable Data Analyst",
                        "analysis_length": len(analyst_output),
                        "snippet": analyst_output[:140] if analyst_output else "",
                    },
                )
            )

            # -------------------------------------------------------------
            # Stage 4c: AgentMemory Manager Agent (6acdcd0f8a6a8741bd6df3df)
            # -------------------------------------------------------------
            mgr_agent_id = settings.lyzr_manager_agent_id
            events.append(
                ExecutionEvent(
                    step="agent_reasoning",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="started",
                    details={
                        "agent_id": mgr_agent_id,
                        "agent_name": "AgentMemory Manager Agent",
                        "role": "Multi-agent coordination and final synthesis",
                        "managed_specialists": ["Fact Finder Agent", "Verifiable Data Analyst"],
                        "session_id": session_id,
                    },
                )
            )

            mgr_prompt = f"""You are the AgentMemory Manager Agent coordinating our collaborative multi-agent system.
Synthesize the verified evidence from Fact Finder Agent and the structured analysis from Verifiable Data Analyst into a clear, cohesive final response to the user.

IMPORTANT INSTRUCTIONS:
1. Answer the user's question directly based strictly on the verified findings.
2. Distinguish original spoken evidence from normalized terminology (e.g. spoken 'Quadrant' -> recognized 'Qdrant', spoken 'Lyzer' -> recognized 'Lyzr').
3. Do not infer or invent technical details that the speaker did not mention.

FACT FINDER FINDINGS:
{fact_output}

DATA ANALYST FINDINGS:
{analyst_output}

USER QUESTION:
{clean_question}
"""
            mgr_result = await lyzr_service.chat(
                message=mgr_prompt,
                user_id=clean_uid,
                session_id=session_id,
                agent_id=mgr_agent_id,
            )
            answer = mgr_result.get("response", "").strip()
            active_agent_id = mgr_result.get("agent_id", mgr_agent_id)
            active_session_id = mgr_result.get("session_id", session_id)

            events.append(
                ExecutionEvent(
                    step="agent_reasoning",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="completed",
                    details={
                        "agent_id": active_agent_id,
                        "agent_name": "AgentMemory Manager Agent",
                        "session_id": active_session_id,
                        "answer_length": len(answer),
                    },
                )
            )

        else:
            # Fallback to single agent if multi-agent is not configured
            single_agent_id = settings.lyzr_research_agent_id
            events.append(
                ExecutionEvent(
                    step="agent_reasoning",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="started",
                    details={"agent_id": single_agent_id, "session_id": session_id},
                )
            )

            lyzr_result = await lyzr_service.chat(
                message=prompt,
                user_id=clean_uid,
                session_id=session_id,
                agent_id=single_agent_id,
            )
            answer = lyzr_result.get("response", "").strip()
            active_agent_id = lyzr_result.get("agent_id", single_agent_id)
            active_session_id = lyzr_result.get("session_id", session_id)

            events.append(
                ExecutionEvent(
                    step="agent_reasoning",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status="completed",
                    details={
                        "agent_id": active_agent_id,
                        "session_id": active_session_id,
                        "answer_length": len(answer),
                    },
                )
            )

        # Stage 5: Final Response Delivery
        events.append(
            ExecutionEvent(
                step="final_response",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="completed",
                details={
                    "total_events": len(events) + 1,
                    "supporting_memories_count": len(retrieved_memories),
                    "is_multi_agent": is_multi_agent,
                },
            )
        )

        return AskResponse(
            answer=answer,
            supporting_memories=retrieved_memories,
            execution_events=events,
            agent_id=active_agent_id,
            session_id=active_session_id,
            specialist_outputs=specialist_outputs,
        )

    except LyzrAPIError as api_err:
        logger.error("Lyzr API error during reasoning: %s", api_err)
        events.append(
            ExecutionEvent(
                step="agent_reasoning",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="failed",
                details={"error": str(api_err), "status_code": api_err.status_code},
            )
        )
        raise HTTPException(
            status_code=api_err.status_code or 502,
            detail=f"Lyzr Agent Error: {str(api_err)}",
        )
    except Exception as exc:
        logger.error("Unexpected error invoking Lyzr: %s", exc)
        events.append(
            ExecutionEvent(
                step="agent_reasoning",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="failed",
                details={"error": str(exc)},
            )
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal reasoning error: {str(exc)}",
        )
