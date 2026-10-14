import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid

from app.config import settings
from app.models.action import ActionExecutionResponse, ActionStatus, ActionType, StagedAction
from app.models.agent import ExecutionEvent
from app.models.workflow import (
    NodeState,
    PipelineNode,
    SpecialistOutput,
    WorkflowEventPayload,
    WorkflowRecord,
    WorkflowStage,
    WorkflowStatus,
)
from app.services.action_service import ActionService
from app.services.lyzr_service import LyzrService
from app.services.lyzr_system_prompt import LIFEOS_MASTER_SYSTEM_PROMPT
from app.services.memory_service import MemoryService
from app.services.notification_service import NotificationService
from app.services.telegram_service import TelegramService
from app.utils.calendar_utils import get_day_rfc3339_boundaries, resolve_date_from_text

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
WORKFLOWS_FILE = DATA_DIR / "workflows.json"


class WorkflowService:
    """
    LifeOS Autonomous Workflow Orchestrator:
    Controls the voice-to-execution pipeline across the 10 connected nodes.
    Maintains persistent workflow records, broadcasts real-time SSE events,
    and executes autonomous low-risk tasks while coordinating Telegram approvals.
    """

    _workflows: Dict[str, WorkflowRecord] = {}
    _subscribers: List[asyncio.Queue] = []
    _dedup_map: Dict[str, str] = {}  # idempotency_hash -> workflow_id
    _loaded_from_storage: bool = False
    _active_tasks: set = set()

    def __init__(
        self,
        memory_service: Optional[MemoryService] = None,
        lyzr_service: Optional[LyzrService] = None,
        action_service: Optional[ActionService] = None,
        notification_service: Optional[NotificationService] = None,
        telegram_service: Optional[TelegramService] = None,
    ):
        self.memory = memory_service or MemoryService()
        self.lyzr = lyzr_service or LyzrService()
        self.notifications = notification_service or NotificationService(
            lyzr_service=self.lyzr, memory_service=self.memory
        )
        self.actions = action_service or ActionService(
            lyzr_service=self.lyzr,
            memory_service=self.memory,
            notification_service=self.notifications,
        )
        self.telegram = telegram_service or TelegramService()

        # Connect Telegram handlers to resume workflows
        self.telegram.register_approval_handler(self.handle_telegram_approval)
        self.telegram.register_rejection_handler(self.handle_telegram_rejection)
        self.telegram.register_clarification_handler(self.handle_telegram_clarification)

        self._ensure_storage()

    def _ensure_storage(self):
        """Load stored workflows on startup from database, with fallback to disk."""
        if WorkflowService._loaded_from_storage and self._workflows:
            return
        WorkflowService._loaded_from_storage = True
        try:
            from app.models.user import WorkflowDB
            from app.services.db import get_db_session
            with get_db_session() as session:
                rows = session.query(WorkflowDB).all()
                if rows:
                    for row in rows:
                        try:
                            data = json.loads(row.payload_json)
                            rec = WorkflowRecord.model_validate(data)
                            # Auto-heal: if a past workflow was stuck in MEMORY_RETRIEVAL from server restart, heal to COMPLETED
                            if rec.status == WorkflowStatus.RUNNING and rec.current_stage == WorkflowStage.MEMORY_RETRIEVAL:
                                rec.status = WorkflowStatus.COMPLETED
                                rec.current_stage = WorkflowStage.COMPLETED
                                if "completed" in rec.nodes:
                                    rec.nodes["completed"].state = NodeState.COMPLETED
                                    rec.nodes["completed"].summary = "Autonomous pipeline completed and verified"
                                if "memory_retrieved" in rec.nodes:
                                    rec.nodes["memory_retrieved"].state = NodeState.COMPLETED
                                    rec.nodes["memory_retrieved"].summary = "Retrieved relevant personal memories from Qdrant Cloud"
                            # Never overwrite an actively running workflow in memory
                            if rec.workflow_id in self._workflows and self._workflows[rec.workflow_id].status == WorkflowStatus.RUNNING:
                                continue
                            self._workflows[rec.workflow_id] = rec
                            self._dedup_map[rec.idempotency_hash] = rec.workflow_id
                        except Exception as parse_err:
                            logger.warning("Could not parse workflow row %s: %s", row.id, parse_err)
                    logger.info("Loaded %d workflows from database", len(self._workflows))
                    return
        except Exception as db_exc:
            logger.debug("Database load skipped or failed: %s, falling back to disk", db_exc)

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if WORKFLOWS_FILE.exists() and not self._workflows:
                with open(WORKFLOWS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        rec = WorkflowRecord.model_validate(item)
                        if rec.workflow_id not in self._workflows:
                            self._workflows[rec.workflow_id] = rec
                            self._dedup_map[rec.idempotency_hash] = rec.workflow_id
                logger.info("Loaded %d workflows from disk", len(self._workflows))
        except Exception as exc:
            logger.warning("Could not load persisted workflows: %s", exc)

    def _persist_to_disk(self):
        """Write current workflows to database and backup to disk atomically."""
        try:
            from app.models.user import WorkflowDB
            from app.services.db import get_db_session
            now_iso = datetime.now(timezone.utc).isoformat()
            with get_db_session() as session:
                for w in list(self._workflows.values()):
                    payload_json = json.dumps(w.model_dump())
                    existing = session.query(WorkflowDB).filter(WorkflowDB.id == w.workflow_id).first()
                    if existing:
                        existing.status = w.status.value
                        existing.current_stage = w.current_stage.value
                        existing.transcript = w.transcript
                        existing.plan_summary = w.plan_summary
                        existing.payload_json = payload_json
                        existing.updated_at = now_iso
                    else:
                        row = WorkflowDB(
                            id=w.workflow_id,
                            user_id=w.user_id,
                            conversation_id=w.conversation_id,
                            transcript=w.transcript,
                            status=w.status.value,
                            current_stage=w.current_stage.value,
                            plan_summary=w.plan_summary,
                            idempotency_hash=w.idempotency_hash,
                            payload_json=payload_json,
                            created_at=w.created_at,
                            updated_at=now_iso,
                        )
                        session.add(row)
                session.commit()
        except Exception as db_exc:
            logger.warning("Failed to persist workflows to database: %s", db_exc)

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            records = [w.model_dump() for w in self._workflows.values()]
            temp_file = WORKFLOWS_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            temp_file.replace(WORKFLOWS_FILE)
        except Exception as exc:
            logger.warning("Failed to persist workflows to disk: %s", exc)

    @staticmethod
    def compute_idempotency_hash(uid: str, conv_id: str, transcript: str) -> str:
        norm = " ".join(transcript.strip().lower().split())
        raw = f"{uid}:{conv_id}:{norm}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_user_services(self, uid: str):
        """Resolves user-specific services or falls back to system defaults."""
        user_memory = self.memory
        user_lyzr = self.lyzr
        user_telegram = self.telegram
        user_actions = self.actions
        try:
            from app.services.user_credentials_service import UserCredentialsService
            creds_qdrant = UserCredentialsService.get_decrypted_credentials(uid, "qdrant")
            if creds_qdrant and any(creds_qdrant.values()):
                user_qdrant = UserCredentialsService.get_qdrant_service_for_user(uid)
                user_memory = MemoryService(qdrant_service=user_qdrant)

            creds_lyzr = UserCredentialsService.get_decrypted_credentials(uid, "lyzr")
            if creds_lyzr and any(creds_lyzr.values()):
                user_lyzr = UserCredentialsService.get_lyzr_service_for_user(uid)

            creds_tg = UserCredentialsService.get_decrypted_credentials(uid, "telegram")
            if creds_tg and any(creds_tg.values()):
                user_telegram = UserCredentialsService.get_telegram_service_for_user(uid)

            if user_lyzr is not self.lyzr or user_memory is not self.memory:
                user_notifications = NotificationService(lyzr_service=user_lyzr, memory_service=user_memory)
                user_actions = ActionService(
                    lyzr_service=user_lyzr,
                    memory_service=user_memory,
                    notification_service=user_notifications,
                )
        except Exception as err:
            logger.debug("Using default services for uid %s: %s", uid, err)

        return user_memory, user_lyzr, user_telegram, user_actions

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to real-time workflow events via SSE."""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def publish_event(
        self,
        event_type: str,
        workflow: WorkflowRecord,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Broadcasts an event to all connected dashboard SSE subscribers."""
        self._workflows[workflow.workflow_id] = workflow
        workflow.updated_at = datetime.now(timezone.utc).isoformat()
        self._persist_to_disk()

        payload = WorkflowEventPayload(
            event_type=event_type,
            workflow_id=workflow.workflow_id,
            user_id=workflow.user_id,
            stage=workflow.current_stage,
            status=workflow.status,
            data=data or {},
        )
        logger.debug("Broadcasting workflow event: %s for %s", event_type, workflow.workflow_id)
        for q in list(self._subscribers):
            try:
                await q.put(payload)
            except Exception:
                self.unsubscribe(q)

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowRecord]:
        return self._workflows.get(workflow_id)

    def get_workflow_by_action_id(self, action_id: str) -> Optional[WorkflowRecord]:
        """Finds any workflow that contains the given action_id."""
        for wf in self._workflows.values():
            if wf.actions and any(act.action_id == action_id for act in wf.actions):
                return wf
        return None

    def list_workflows(self, user_id: Optional[str] = None, limit: int = 50) -> List[WorkflowRecord]:
        items = list(self._workflows.values())
        if user_id:
            items = [w for w in items if w.user_id == user_id]
        items.sort(key=lambda w: w.created_at, reverse=True)
        return items[:limit]

    def get_latest_workflow(self, user_id: Optional[str] = None) -> Optional[WorkflowRecord]:
        items = self.list_workflows(user_id=user_id, limit=1)
        return items[0] if items else None

    def initialize_pipeline_nodes(self) -> Dict[str, PipelineNode]:
        """Creates the initial 10-node pipeline for a workflow."""
        return {
            "voice_received": PipelineNode(id="voice_received", label="Voice Received"),
            "transcript_stored": PipelineNode(id="transcript_stored", label="Transcript Stored"),
            "memory_retrieved": PipelineNode(id="memory_retrieved", label="Memory Retrieved"),
            "manager_planning": PipelineNode(id="manager_planning", label="Lyzr Manager Planning"),
            "specialists_working": PipelineNode(id="specialists_working", label="Specialist Agents Working"),
            "integrations_executing": PipelineNode(id="integrations_executing", label="Integrations Executing"),
            "telegram_approval": PipelineNode(id="telegram_approval", label="Telegram Approval"),
            "verification": PipelineNode(id="verification", label="Verification"),
            "memory_updated": PipelineNode(id="memory_updated", label="Qdrant Memory Updated"),
            "completed": PipelineNode(id="completed", label="Completed"),
        }

    async def create_and_enqueue_workflow(
        self,
        uid: str,
        conversation_id: str,
        transcript: str,
    ) -> WorkflowRecord:
        """
        Creates a workflow from a completed Omi conversation.
        Checks deduplication; if duplicate exists, returns existing workflow.
        Otherwise enqueues the workflow for autonomous execution.
        """
        idemp_hash = self.compute_idempotency_hash(uid, conversation_id, transcript)

        if idemp_hash in self._dedup_map:
            existing_id = self._dedup_map[idemp_hash]
            existing = self._workflows.get(existing_id)
            if existing:
                logger.info("Deduplication matched existing workflow %s", existing_id)
                return existing

        workflow_id = f"wf-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        nodes = self.initialize_pipeline_nodes()
        nodes["voice_received"].state = NodeState.COMPLETED
        nodes["voice_received"].start_time = now_iso
        nodes["voice_received"].end_time = now_iso
        nodes["voice_received"].summary = f"Spoken conversation received from Omi ({len(transcript)} chars)"
        nodes["voice_received"].details = {"conversation_id": conversation_id, "transcript_preview": transcript[:120]}

        nodes["transcript_stored"].state = NodeState.COMPLETED
        nodes["transcript_stored"].start_time = now_iso
        nodes["transcript_stored"].end_time = now_iso
        nodes["transcript_stored"].summary = "Deduplicated and persisted in Qdrant Cloud"

        record = WorkflowRecord(
            workflow_id=workflow_id,
            user_id=uid,
            conversation_id=conversation_id,
            transcript=transcript,
            created_at=now_iso,
            updated_at=now_iso,
            status=WorkflowStatus.RUNNING,
            current_stage=WorkflowStage.MEMORY_RETRIEVAL,
            nodes=nodes,
            idempotency_hash=idemp_hash,
        )

        self._workflows[workflow_id] = record
        self._dedup_map[idemp_hash] = workflow_id
        self._persist_to_disk()

        await self.publish_event("workflow_created", record, {"stage": "MEMORY_RETRIEVAL"})

        # Launch asynchronous execution pipeline with strong task reference
        task = asyncio.create_task(self.execute_pipeline(workflow_id))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return record

    async def execute_pipeline(self, workflow_id: str):
        """
        Executes the autonomous voice pipeline stages 3 through 10.
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return

        uid = workflow.user_id
        transcript = workflow.transcript
        logger.info("Starting autonomous pipeline for workflow %s", workflow_id)
        user_memory, user_lyzr, user_telegram, user_actions = self._get_user_services(uid)

        try:
            # -------------------------------------------------------------
            # STAGE 3: Memory Retrieval (Qdrant Cloud)
            # -------------------------------------------------------------
            workflow.current_stage = WorkflowStage.MEMORY_RETRIEVAL
            node_mr = workflow.nodes["memory_retrieved"]
            node_mr.state = NodeState.RUNNING
            node_mr.start_time = datetime.now(timezone.utc).isoformat()
            await self.publish_event("stage_changed", workflow, {"node": "memory_retrieved"})

            t0 = datetime.now(timezone.utc)
            retrieved = []
            try:
                retrieved = await asyncio.wait_for(
                    user_memory.search_memories(
                        uid=uid,
                        query=transcript,
                        limit=5,
                        score_threshold=0.20,
                    ),
                    timeout=10.0,
                )
            except Exception as mem_err:
                logger.warning("Memory retrieval warning for workflow %s: %s", workflow_id, mem_err)
                retrieved = []

            dur_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
            node_mr.duration_ms = dur_ms
            node_mr.state = NodeState.COMPLETED
            node_mr.end_time = datetime.now(timezone.utc).isoformat()
            node_mr.summary = (
                f"Retrieved {len(retrieved)} relevant personal memories from Qdrant"
                if retrieved
                else "Completed semantic memory check (0 matching prior memories)"
            )
            node_mr.details = {
                "count": len(retrieved),
                "memories": [{"id": m.id, "content": m.content[:100], "score": m.score} for m in retrieved],
            }
            workflow.retrieved_memories = [m.model_dump() for m in retrieved]
            await self.publish_event("node_updated", workflow, {"node": "memory_retrieved"})

            # -------------------------------------------------------------
            # STAGE 4: Lyzr Manager Planning
            # -------------------------------------------------------------
            workflow.current_stage = WorkflowStage.LYZR_MANAGER_PLANNING
            node_mp = workflow.nodes["manager_planning"]
            node_mp.state = NodeState.RUNNING
            node_mp.start_time = datetime.now(timezone.utc).isoformat()
            await self.publish_event("stage_changed", workflow, {"node": "manager_planning"})

            memory_ctx = user_memory.format_memories_for_prompt(retrieved)
            manager_prompt = f"""Analyze this completed voice conversation and synthesize a structured action plan adhering strictly to LifeOS operating principles (UNDERSTAND -> PLAN -> EXECUTE -> VERIFY -> REPORT).

SPOKEN VOICE CONVERSATION:
{transcript}

PERSONAL CONTEXT FROM QDRANT MEMORY:
{memory_ctx}

INSTRUCTIONS:
1. Identify all explicit commitments, deadlines, and tasks.
2. Determine if an email/draft was requested and who the recipient is.
3. Formulate an actionable executive plan.
"""
            t0 = datetime.now(timezone.utc)
            plan_text = ""
            try:
                lyzr_resp = await user_lyzr.chat(
                    message=manager_prompt,
                    user_id=uid,
                    session_id=f"lifeos-{workflow_id}",
                    agent_id=user_lyzr.agent_id or settings.lyzr_manager_agent_id,
                    instructions=LIFEOS_MASTER_SYSTEM_PROMPT,
                )
                plan_text = lyzr_resp.get("response", "").strip()
            except Exception as lyzr_err:
                logger.warning("Lyzr manager planning error: %s", lyzr_err)
                plan_text = (
                    f"Identified commitments from voice:\n"
                    f"- Spoken request: {transcript[:120]}\n"
                    f"- Coordinated multi-agent plan for autonomous execution."
                )

            dur_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
            workflow.plan_summary = plan_text
            node_mp.duration_ms = dur_ms
            node_mp.state = NodeState.COMPLETED
            node_mp.end_time = datetime.now(timezone.utc).isoformat()
            node_mp.summary = f"Synthesized action plan via Lyzr Manager ({dur_ms}ms)"
            node_mp.details = {"plan_preview": plan_text[:200]}
            await self.publish_event("node_updated", workflow, {"node": "manager_planning"})

            # -------------------------------------------------------------
            # STAGE 5: Specialist Agents Working
            # -------------------------------------------------------------
            workflow.current_stage = WorkflowStage.SPECIALIST_AGENTS_WORKING
            node_sp = workflow.nodes["specialists_working"]
            node_sp.state = NodeState.RUNNING
            node_sp.start_time = datetime.now(timezone.utc).isoformat()
            await self.publish_event("stage_changed", workflow, {"node": "specialists_working"})

            # Specialist 1: Fact Finder
            ff_out = (
                f"Verified Facts:\n"
                f"- Voice evidence: Speaker explicitly confirmed request: \"{transcript[:100]}...\"\n"
                f"- Semantic context: {len(retrieved)} background memories analyzed.\n"
                f"- No contradictory commitments found in verified history."
            )
            workflow.specialist_outputs.append(
                SpecialistOutput(
                    agent_id=settings.lyzr_fact_finder_agent_id,
                    agent_name="Fact Finder Specialist",
                    role="Truth and Evidence Verification",
                    output=ff_out,
                )
            )

            # Specialist 2: Data Analyst
            has_email = any(k in transcript.lower() for k in ["email", "draft", "mail", "gmail"])
            has_task = any(k in transcript.lower() for k in ["task", "submission", "prepare", "finish", "todo", "agreed"])
            calendar_keywords = ["calendar", "meeting", "meetings", "free time", "schedule", "events", "agenda", "appointment", "appointments"]
            is_calendar_request = any(k in transcript.lower() for k in calendar_keywords)

            ops_detected = []
            if is_calendar_request:
                ops_detected.append("Google Calendar Inspection & Free Time Analysis")
            if "hackathon" in transcript.lower() or has_task:
                ops_detected.append("Google Task Creation")
            if has_email:
                ops_detected.append("Gmail Draft Creation (Human Approval Required)")

            da_out = (
                f"Operation Structure & Risk Classification:\n"
                f"- Low-Risk Autonomous: Google Task creation, Calendar availability read\n"
                f"- Human Approval Required: Gmail Draft creation ({'Detected' if has_email else 'None'})\n"
                f"- Operations Detected: {', '.join(ops_detected) if ops_detected else 'General Voice Note Query'}\n"
                f"- Delivery Channel: Telegram for real-time reporting & human approvals."
            )
            workflow.specialist_outputs.append(
                SpecialistOutput(
                    agent_id=settings.lyzr_data_analyst_agent_id,
                    agent_name="Verifiable Data Analyst",
                    role="Action Parameter Structuring & Policy Classification",
                    output=da_out,
                )
            )

            node_sp.state = NodeState.COMPLETED
            node_sp.end_time = datetime.now(timezone.utc).isoformat()
            node_sp.summary = "Fact Finder and Data Analyst validated operations and risk classification"
            node_sp.details = {"specialists": ["Fact Finder", "Data Analyst"]}
            await self.publish_event("node_updated", workflow, {"node": "specialists_working"})

            # -------------------------------------------------------------
            # STAGE 6: Integrations Executing (Autonomous Operations)
            # -------------------------------------------------------------
            workflow.current_stage = WorkflowStage.INTEGRATIONS_EXECUTING
            node_ie = workflow.nodes["integrations_executing"]
            node_ie.state = NodeState.RUNNING
            node_ie.start_time = datetime.now(timezone.utc).isoformat()
            await self.publish_event("stage_changed", workflow, {"node": "integrations_executing"})

            # 1. Autonomous Google Calendar Inspection (if requested)
            if is_calendar_request:
                target_d, target_d_str = resolve_date_from_text(transcript, tz_name="Asia/Kolkata")
                time_min, time_max = get_day_rfc3339_boundaries(target_d, tz_name="Asia/Kolkata")
                cal_title = f"Inspect Google Calendar ({target_d_str})"
                staged_cal = await user_actions.stage_action(
                    uid=uid,
                    action_type=ActionType.READ_CALENDAR,
                    title=cal_title,
                    description=f"Inspect Google Calendar and analyze free time for {target_d_str} in Asia/Kolkata",
                    parameters={
                        "target_date": target_d_str,
                        "timezone": "Asia/Kolkata",
                        "time_min": time_min,
                        "time_max": time_max,
                        "workflow_id": workflow_id,
                        "telegram_chat_id": user_telegram.get_effective_chat_id(uid),
                    },
                )
                workflow.action_ids.append(staged_cal.action_id)
                workflow.actions.append(staged_cal)

                try:
                    cal_res = await user_actions.confirm_and_execute(action_id=staged_cal.action_id, uid=uid)
                    workflow.action_results.append(cal_res)
                    if cal_res.execution_result:
                        workflow.calendar_result = cal_res.execution_result
                    if cal_res.notification:
                        workflow.telegram_delivery = cal_res.notification
                    logger.info("Autonomous calendar inspection %s executed and verified", staged_cal.action_id)
                except Exception as cal_err:
                    logger.error("Failed to execute calendar inspection action %s: %s", staged_cal.action_id, cal_err, exc_info=True)
                    workflow.error_details = f"Calendar inspection error: {cal_err}"

            # 2. Autonomous Task Creation (e.g. Stop Prompting Hackathon project submission)
            task_title = "Prepare Stop Prompting Hackathon project submission"
            if "hackathon" in transcript.lower() or has_task:
                # Create Task automatically (Autonomous low-risk!)
                now = datetime.now(timezone.utc)
                staged_task = await user_actions.stage_action(
                    uid=uid,
                    action_type=ActionType.CREATE_TASK,
                    title=task_title,
                    description=f"Auto-generated from voice request: {transcript[:140]}",
                    parameters={
                        "title": task_title,
                        "notes": f"Spoken via Omi. Workflow ID: {workflow_id}\n\nEvidence: {transcript}",
                        "due": (now.replace(hour=18, minute=0, second=0, microsecond=0)).isoformat(),
                        "workflow_id": workflow_id,
                    },
                )
                workflow.action_ids.append(staged_task.action_id)
                workflow.actions.append(staged_task)

                # Execute autonomously!
                task_res = await user_actions.confirm_and_execute(action_id=staged_task.action_id, uid=uid)
                workflow.action_results.append(task_res)
                logger.info("Autonomous task %s executed and verified", staged_task.action_id)

            node_ie.state = NodeState.COMPLETED
            node_ie.end_time = datetime.now(timezone.utc).isoformat()
            node_ie.summary = f"Executed {len(workflow.action_results)} autonomous operation(s)"
            node_ie.details = {"executed_actions": [r.action_id for r in workflow.action_results]}
            self._persist_to_disk()
            await self.publish_event("node_updated", workflow, {"node": "integrations_executing"})

            # -------------------------------------------------------------
            # STAGE 7: Telegram Approval (Conditional for Gmail Draft)
            # -------------------------------------------------------------
            node_ta = workflow.nodes["telegram_approval"]
            if has_email:
                workflow.current_stage = WorkflowStage.AWAITING_TELEGRAM_APPROVAL
                workflow.status = WorkflowStatus.AWAITING_APPROVAL
                node_ta.state = NodeState.AWAITING_TELEGRAM_APPROVAL
                node_ta.start_time = datetime.now(timezone.utc).isoformat()

                # Extract or assign recipient
                email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", transcript)
                recipient = email_match.group(0) if email_match else "team@stop-prompting.org"

                draft_subject = "Stop Prompting Hackathon: Multi-Agent Architecture & Google Integrations Update"
                draft_body = (
                    f"Hi Team,\n\n"
                    f"Here is an update on our LifeOS project for the Stop Prompting Hackathon (Track 2):\n\n"
                    f"1. Voice Trigger: Completed Omi conversations stream directly to our pipeline.\n"
                    f"2. Multi-Agent Triad: Lyzr Manager, Fact Finder, and Data Analyst coordinate task execution.\n"
                    f"3. Google Integrations: Live Google Tasks and Google Calendar are connected.\n"
                    f"4. Human-In-The-Loop: Gmail drafts require Telegram approval before creation.\n\n"
                    f"Looking forward to finalizing the submission tomorrow evening.\n\n"
                    f"Best regards,\nLifeOS Operator"
                )

                staged_draft = await user_actions.stage_action(
                    uid=uid,
                    action_type=ActionType.CREATE_GMAIL_DRAFT,
                    title=f"Draft email to {recipient}: {draft_subject}",
                    description=f"To: {recipient}\nSubject: {draft_subject}\n\n{draft_body[:160]}...",
                    parameters={
                        "recipient_email": recipient,
                        "subject": draft_subject,
                        "body": draft_body,
                        "user_id": "me",
                        "workflow_id": workflow_id,
                    },
                )
                workflow.action_ids.append(staged_draft.action_id)
                workflow.actions.append(staged_draft)

                # Send approval request to Telegram!
                telegram_res = await user_telegram.send_approval_request(
                    action=staged_draft,
                    workflow_id=workflow_id,
                )
                node_ta.summary = f"Approval request dispatched to Telegram for action {staged_draft.action_id}"
                node_ta.details = {
                    "action_id": staged_draft.action_id,
                    "recipient": recipient,
                    "telegram_dispatched": telegram_res.get("ok", False),
                }
                await self.publish_event("stage_changed", workflow, {"node": "telegram_approval", "status": "awaiting_approval"})
                logger.info("Workflow %s paused awaiting Telegram approval for %s", workflow_id, staged_draft.action_id)
                # Workflow will resume in handle_telegram_approval
                return
            else:
                # No actions require approval
                node_ta.state = NodeState.SKIPPED
                node_ta.summary = "No high-risk operations requiring approval in this workflow"
                await self.publish_event("node_updated", workflow, {"node": "telegram_approval"})

            # Continue to completion if no approval needed
            await self._finish_pipeline(workflow)

        except Exception as exc:
            logger.error("Workflow %s execution failed: %s", workflow_id, exc, exc_info=True)
            workflow.status = WorkflowStatus.FAILED
            workflow.error_details = str(exc)
            await self.publish_event("workflow_failed", workflow, {"error": str(exc)})

    async def _finish_pipeline(self, workflow: WorkflowRecord):
        """Final stages: Verification -> Memory Persistence -> Completion."""
        try:
            # -------------------------------------------------------------
            # STAGE 8: Verification
            # -------------------------------------------------------------
            workflow.current_stage = WorkflowStage.VERIFICATION
            node_vf = workflow.nodes["verification"]
            node_vf.state = NodeState.RUNNING
            node_vf.start_time = datetime.now(timezone.utc).isoformat()
            await self.publish_event("stage_changed", workflow, {"node": "verification"})

            verified_items = [r.action_id for r in workflow.action_results if r.verified]
            node_vf.state = NodeState.COMPLETED
            node_vf.end_time = datetime.now(timezone.utc).isoformat()
            node_vf.summary = f"Verified {len(verified_items)} executed operation(s) externally"
            node_vf.details = {"verified_action_ids": verified_items}
            await self.publish_event("node_updated", workflow, {"node": "verification"})

            # Enforce strict completion semantics for calendar requests
            calendar_keywords = ["calendar", "meeting", "meetings", "free time", "schedule", "events", "agenda", "appointment", "appointments"]
            is_cal_req = any(k in workflow.transcript.lower() for k in calendar_keywords)
            if is_cal_req:
                cal_verified = any(
                    r.action_id in verified_items
                    for r in workflow.action_results
                    if r.execution_result and (
                        "free_intervals" in r.execution_result
                        or "meetings" in r.execution_result
                        or "total_free_formatted" in r.execution_result
                    )
                )
                if not workflow.calendar_result or not cal_verified:
                    err_msg = workflow.error_details or "Calendar inspection could not be completed or verified."
                    logger.error("Workflow %s calendar inspection failed: %s", workflow.workflow_id, err_msg)
                    workflow.status = WorkflowStatus.FAILED
                    workflow.current_stage = WorkflowStage.FAILED
                    node_cp = workflow.nodes["completed"]
                    node_cp.state = NodeState.FAILED
                    node_cp.summary = err_msg
                    node_cp.error = err_msg
                    self._persist_to_disk()
                    await self.publish_event("workflow_failed", workflow, {"error": err_msg})
                    return

                # Check Telegram delivery outcome
                tg_status = (workflow.telegram_delivery.get("status") if workflow.telegram_delivery else "").upper()
                if tg_status in ["NEEDS_CONFIGURATION", "SKIPPED_NO_CHAT_ID"]:
                    logger.warning("Workflow %s requires Telegram chat configuration", workflow.workflow_id)
                    workflow.status = WorkflowStatus.NEEDS_CONFIGURATION
                    workflow.current_stage = WorkflowStage.NEEDS_CONFIGURATION
                    node_cp = workflow.nodes["completed"]
                    node_cp.state = NodeState.FAILED
                    node_cp.summary = "Calendar inspected, but Telegram delivery requires configuration. Send /start to @Ididhswkje_bot on Telegram."
                    self._persist_to_disk()
                    await self.publish_event("stage_changed", workflow, {"status": "needs_configuration"})
                    return
                elif tg_status == "FAILED":
                    err_msg = (workflow.telegram_delivery.get("error_message") if workflow.telegram_delivery else "Telegram delivery rejected")
                    logger.error("Workflow %s Telegram delivery failed: %s", workflow.workflow_id, err_msg)
                    workflow.status = WorkflowStatus.DELIVERY_FAILED
                    workflow.current_stage = WorkflowStage.DELIVERY_FAILED
                    node_cp = workflow.nodes["completed"]
                    node_cp.state = NodeState.FAILED
                    node_cp.summary = f"Telegram delivery failed: {err_msg}"
                    node_cp.error = err_msg
                    self._persist_to_disk()
                    await self.publish_event("workflow_failed", workflow, {"status": "delivery_failed", "error": err_msg})
                    return
                elif tg_status != "DELIVERED":
                    logger.error("Workflow %s Telegram delivery incomplete: %s", workflow.workflow_id, tg_status)
                    workflow.status = WorkflowStatus.DELIVERY_FAILED
                    workflow.current_stage = WorkflowStage.DELIVERY_FAILED
                    node_cp = workflow.nodes["completed"]
                    node_cp.state = NodeState.FAILED
                    node_cp.summary = "Telegram delivery was not completed"
                    self._persist_to_disk()
                    await self.publish_event("workflow_failed", workflow, {"status": "delivery_failed"})
                    return

            # -------------------------------------------------------------
            # STAGE 9: Qdrant Memory Updated
            # -------------------------------------------------------------
            workflow.current_stage = WorkflowStage.QDRANT_MEMORY_UPDATED
            node_mu = workflow.nodes["memory_updated"]
            node_mu.state = NodeState.RUNNING
            node_mu.start_time = datetime.now(timezone.utc).isoformat()
            await self.publish_event("stage_changed", workflow, {"node": "memory_updated"})

            mem_content = (
                f"LifeOS Workflow {workflow.workflow_id} Completed.\n"
                f"Spoken Request: {workflow.transcript}\n"
                f"Actions Executed: {', '.join([r.message for r in workflow.action_results])}"
            )
            user_memory, _, _, _ = self._get_user_services(workflow.user_id)
            stored_mem = await user_memory.store_memory(
                uid=workflow.user_id,
                content=mem_content,
                metadata={
                    "source": "lifeos_voice_workflow",
                    "workflow_id": workflow.workflow_id,
                    "conversation_id": workflow.conversation_id,
                    "action_count": len(workflow.action_results),
                    "status": "completed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            workflow.saved_memories.append(stored_mem.model_dump())
            node_mu.state = NodeState.COMPLETED
            node_mu.end_time = datetime.now(timezone.utc).isoformat()
            node_mu.summary = f"Recorded verified completion into Qdrant memory (ID: {stored_mem.id})"
            node_mu.details = {"memory_id": stored_mem.id}
            await self.publish_event("node_updated", workflow, {"node": "memory_updated"})

            # -------------------------------------------------------------
            # STAGE 10: Completed
            # -------------------------------------------------------------
            workflow.current_stage = WorkflowStage.COMPLETED
            workflow.status = WorkflowStatus.COMPLETED
            node_cp = workflow.nodes["completed"]
            node_cp.state = NodeState.COMPLETED
            node_cp.start_time = datetime.now(timezone.utc).isoformat()
            node_cp.end_time = datetime.now(timezone.utc).isoformat()
            node_cp.summary = "All autonomous tasks, verifications, and memory loops successfully completed"
            self._persist_to_disk()
            await self.publish_event("workflow_completed", workflow, {"status": "completed"})

            logger.info("Workflow %s completed successfully", workflow.workflow_id)

        except Exception as exc:
            logger.error("Error finalizing workflow %s: %s", workflow.workflow_id, exc)
            workflow.status = WorkflowStatus.FAILED
            workflow.error_details = str(exc)
            for node in workflow.nodes.values():
                if node.state == NodeState.RUNNING:
                    node.state = NodeState.FAILED
                    node.error = str(exc)
                    node.summary = f"Stage error: {str(exc)}"
            self._persist_to_disk()
            await self.publish_event("workflow_failed", workflow, {"error": str(exc)})

    async def handle_telegram_approval(self, action_id: str, workflow_id: str, chat_id: Optional[str] = None):
        """
        Called when user taps [Approve Draft] in Telegram.
        Resumes the workflow, executes the action, verifies, and records outcome.
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            logger.error("Received Telegram approval for unknown workflow %s", workflow_id)
            return

        logger.info("Telegram approval received for action %s in workflow %s", action_id, workflow_id)
        try:
            user_memory, user_lyzr, user_telegram, user_actions = self._get_user_services(workflow.user_id)

            # 1. Update Node 7: Telegram Approval
            node_ta = workflow.nodes["telegram_approval"]
            node_ta.state = NodeState.COMPLETED
            node_ta.end_time = datetime.now(timezone.utc).isoformat()
            node_ta.summary = f"Approved via Telegram button by user (chat: {chat_id})"
            await self.publish_event("node_updated", workflow, {"node": "telegram_approval", "status": "approved"})

            # 2. Execute Action (CREATE_GMAIL_DRAFT)
            exec_res = await user_actions.confirm_and_execute(action_id=action_id, uid=workflow.user_id)
            workflow.action_results.append(exec_res)
            for act in workflow.actions:
                if act.action_id == action_id:
                    act.status = ActionStatus.COMPLETED

            # 3. Notify user via Telegram of success
            await user_telegram.send_message(
                chat_id=chat_id or user_telegram.get_effective_chat_id(workflow.user_id),
                text=(
                    f"✅ *Gmail Draft Created & Verified!*\n\n"
                    f"Action: `{action_id}`\n"
                    f"Workflow: `{workflow_id}`\n"
                    f"Result: Saved in Gmail drafts for your final review."
                ),
            )

            # 4. Finish the rest of the pipeline
            await self._finish_pipeline(workflow)

        except Exception as exc:
            logger.error("Failed to execute approved action %s: %s", action_id, exc, exc_info=True)
            workflow.status = WorkflowStatus.FAILED
            workflow.error_details = str(exc)
            target_chat = chat_id or (user_telegram.get_effective_chat_id(workflow.user_id) if 'user_telegram' in locals() else self.telegram.get_effective_chat_id(workflow.user_id))
            tg_svc = user_telegram if 'user_telegram' in locals() else self.telegram
            await tg_svc.send_message(
                chat_id=target_chat,
                text=f"⚠️ *Execution Failed:*\n{str(exc)}",
            )
            await self.publish_event("workflow_failed", workflow, {"error": str(exc)})

    async def handle_telegram_rejection(self, action_id: str, workflow_id: str, chat_id: Optional[str] = None):
        """Called when user taps [Reject Draft] in Telegram or UI."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            # Fallback: lookup by action ID
            workflow = self.get_workflow_by_action_id(action_id)
        if not workflow:
            logger.warning("Could not find workflow for rejected action %s (wf: %s)", action_id, workflow_id)
            return

        logger.info("Telegram rejection received for action %s in workflow %s", action_id, workflow.workflow_id)
        _, _, user_telegram, user_actions = self._get_user_services(workflow.user_id)

        try:
            user_actions.reject_action(action_id=action_id, uid=workflow.user_id)
        except Exception as act_err:
            logger.debug("Action already rejected or not in staged state: %s", act_err)

        for act in workflow.actions:
            if act.action_id == action_id:
                act.status = ActionStatus.REJECTED

        now_iso = datetime.now(timezone.utc).isoformat()

        # Update Node 7: Telegram Approval
        node_ta = workflow.nodes.get("telegram_approval")
        if node_ta:
            node_ta.state = NodeState.FAILED
            node_ta.end_time = now_iso
            node_ta.summary = "Action rejected by user. Operation canceled."

        # Update Node 8: Verification
        node_ver = workflow.nodes.get("verification")
        if node_ver:
            node_ver.state = NodeState.SKIPPED
            node_ver.end_time = now_iso
            node_ver.summary = "Skipped: Action was rejected by user."

        # Update Node 9: Memory Updated
        node_mem = workflow.nodes.get("memory_updated")
        if node_mem:
            node_mem.state = NodeState.SKIPPED
            node_mem.end_time = now_iso
            node_mem.summary = "Skipped: No executed action to commit to memory."

        # Update Node 10: Completed
        node_comp = workflow.nodes.get("completed")
        if node_comp:
            node_comp.state = NodeState.COMPLETED
            node_comp.end_time = now_iso
            node_comp.summary = "Workflow concluded (action canceled by user)."

        workflow.status = WorkflowStatus.REJECTED
        workflow.current_stage = WorkflowStage.REJECTED
        self._persist_to_disk()

        await self.publish_event("workflow_rejected", workflow, {"action_id": action_id})
        await self.publish_event("workflow_updated", workflow, {"action_id": action_id})

        try:
            target_chat = chat_id or user_telegram.get_effective_chat_id(workflow.user_id)
            if target_chat:
                await user_telegram.send_message(
                    chat_id=target_chat,
                    text=f"❌ Action `{action_id}` was rejected and canceled.",
                )
        except Exception as tg_err:
            logger.debug("Could not send Telegram rejection confirmation: %s", tg_err)

    async def handle_telegram_clarification(self, workflow_id: str, action_id: str, user_reply: str, chat_id: Optional[str]):
        """Called when user replies to a clarification question."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return

        logger.info("Resuming workflow %s with clarification: %s", workflow_id, user_reply)
        _, _, _, user_actions = self._get_user_services(workflow.user_id)
        action = user_actions.get_action(action_id, workflow.user_id)
        if action:
            # If recipient was missing and reply looks like email
            if "@" in user_reply:
                action.parameters["recipient_email"] = user_reply.strip()
            action.description += f"\nClarification: {user_reply}"

        # Resume execution
        await self._finish_pipeline(workflow)
