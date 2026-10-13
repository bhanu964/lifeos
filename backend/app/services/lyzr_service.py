import ast
import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LyzrAPIError(Exception):
    """Custom exception raised when Lyzr API fails or returns non-200."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class LyzrService:
    """
    Lyzr Agent service for AgentMemory AI.
    Integrates with Lyzr Studio REST API to query deployed research agents.
    Strictly observes security (never logs API keys) and never fabricates responses.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        tool_execute_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        default_user_id: Optional[str] = None,
        timeout: float = 45.0,
    ):
        self.api_key = api_key if api_key is not None else settings.lyzr_api_key
        self.api_url = api_url if api_url is not None else settings.lyzr_api_url
        self.tool_execute_url = tool_execute_url if tool_execute_url is not None else settings.lyzr_tool_execute_url
        self.agent_id = agent_id if agent_id is not None else settings.lyzr_research_agent_id
        self.default_user_id = default_user_id if default_user_id is not None else settings.lyzr_user_id
        self.timeout = timeout

    async def chat(
        self,
        message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends an inference chat request to the Lyzr Agent API.
        
        Args:
            message: Formatted prompt containing user query and relevant memories.
            user_id: Target user ID (defaults to configured LYZR_USER_ID).
            session_id: Session identifier for conversational memory in Lyzr.
            agent_id: Target agent ID (defaults to LYZR_RESEARCH_AGENT_ID).
            
        Returns:
            Dict containing 'response' string and any 'module_outputs'.
            
        Raises:
            LyzrAPIError on missing credentials, network errors, timeouts, or non-200 responses.
        """
        if not self.api_key:
            raise LyzrAPIError(
                "Lyzr API key is missing. Please configure LYZR_API_KEY in the environment.",
                status_code=401,
            )

        active_agent_id = agent_id or self.agent_id
        if not active_agent_id:
            raise LyzrAPIError("Lyzr agent_id is required.", status_code=400)

        active_user_id = user_id or self.default_user_id
        if not active_user_id:
            raise LyzrAPIError("Lyzr user_id is required.", status_code=400)

        # Generate a stable session ID if none provided
        active_session_id = session_id or f"{active_agent_id}-{active_user_id}"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        payload = {
            "user_id": active_user_id,
            "agent_id": active_agent_id,
            "session_id": active_session_id,
            "message": message,
        }

        # Log request metadata without revealing the API key or raw private tokens
        logger.info(
            "Calling Lyzr agent: %s | user: %s | session: %s",
            active_agent_id,
            active_user_id,
            active_session_id,
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                )

            if response.status_code != 200:
                logger.error(
                    "Lyzr API returned HTTP %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                raise LyzrAPIError(
                    f"Lyzr API returned HTTP {response.status_code}: {response.text}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            data = response.json()
            if not isinstance(data, dict):
                raise LyzrAPIError(f"Unexpected Lyzr response structure: {data}")

            response_text = data.get("response", "")
            if not response_text and "message" in data:
                response_text = str(data["message"])

            return {
                "response": response_text,
                "module_outputs": data.get("module_outputs", {}),
                "agent_id": active_agent_id,
                "session_id": active_session_id,
            }

        except httpx.TimeoutException as exc:
            logger.error("Lyzr API request timed out after %s seconds", self.timeout)
            raise LyzrAPIError(
                f"Lyzr API request timed out after {self.timeout} seconds",
                status_code=504,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Lyzr API network communication error: %s", exc)
            raise LyzrAPIError(
                f"Network error communicating with Lyzr API: {exc}",
                status_code=502,
            ) from exc

    def _parse_tool_response(self, result: Any) -> Any:
        """Safely parse tool response data from dictionary or string."""
        if not isinstance(result, dict):
            return result
        raw_resp = result.get("response")
        if isinstance(raw_resp, str):
            try:
                return ast.literal_eval(raw_resp)
            except Exception:
                try:
                    return json.loads(raw_resp)
                except Exception:
                    return raw_resp
        return result

    async def execute_tool(
        self,
        tool_name: str,
        tool_configs: List[Dict[str, Any]],
        arguments: Dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes an authorized tool action via Lyzr tool execution endpoint.
        """
        if not self.api_key:
            raise LyzrAPIError("Lyzr API key missing for tool execution", status_code=401)

        active_agent_id = agent_id or self.agent_id
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }
        payload = {
            "agent_id": active_agent_id,
            "tool_name": tool_name,
            "tool_configs": tool_configs,
            "arguments": arguments,
        }

        logger.info("Executing Lyzr tool '%s' with agent '%s'", tool_name, active_agent_id)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.tool_execute_url,
                    headers=headers,
                    json=payload,
                )

            if response.status_code != 200:
                logger.error("Tool execution failed (HTTP %d): %s", response.status_code, response.text[:200])
                raise LyzrAPIError(
                    f"Tool execution failed (HTTP {response.status_code}): {response.text}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            data = response.json()
            result = data.get("result", {})
            parsed_result = self._parse_tool_response(result)

            return {
                "tool_name": tool_name,
                "trace_id": data.get("trace_id", ""),
                "result": parsed_result,
            }

        except httpx.TimeoutException as exc:
            logger.error("Tool execution timed out after %s seconds", self.timeout)
            raise LyzrAPIError(f"Tool execution timed out after {self.timeout}s", status_code=504) from exc
        except httpx.RequestError as exc:
            logger.error("Tool execution network error: %s", exc)
            raise LyzrAPIError(f"Tool execution network error: {exc}", status_code=502) from exc

    async def list_calendar_events(
        self,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 15,
        calendar_id: str = "primary",
    ) -> List[Dict[str, Any]]:
        """
        Retrieves real calendar events from Google Calendar via Composio.
        """
        tool_config = [
            {
                "tool_name": "googlecalendar",
                "tool_source": "composio",
                "action_names": ["GOOGLECALENDAR_EVENTS_LIST"],
                "provider_uuid": settings.google_calendar_provider_uuid,
                "credential_id": settings.google_calendar_credential_id,
                "persist_auth": True,
            }
        ]
        arguments: Dict[str, Any] = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            arguments["timeMin"] = time_min
        if time_max:
            arguments["timeMax"] = time_max

        res = await self.execute_tool(
            tool_name="GOOGLECALENDAR_EVENTS_LIST",
            tool_configs=tool_config,
            arguments=arguments,
        )
        res_data = res.get("result", {})
        if isinstance(res_data, dict):
            # Might be nested under data -> items or response_data -> items
            data_field = res_data.get("data", {})
            if isinstance(data_field, dict):
                return data_field.get("items", []) or data_field.get("response_data", {}).get("items", [])
        return []

    async def create_calendar_event(
        self,
        summary: str,
        start_datetime: str,
        description: Optional[str] = None,
        timezone: str = "UTC",
        calendar_id: str = "primary",
        event_duration_minutes: int = 60,
    ) -> Dict[str, Any]:
        """
        Creates a real calendar event in Google Calendar via Composio.
        """
        tool_config = [
            {
                "tool_name": "googlecalendar",
                "tool_source": "composio",
                "action_names": ["GOOGLECALENDAR_CREATE_EVENT"],
                "provider_uuid": settings.google_calendar_provider_uuid,
                "credential_id": settings.google_calendar_credential_id,
                "persist_auth": True,
            }
        ]
        arguments: Dict[str, Any] = {
            "summary": summary,
            "start_datetime": start_datetime,
            "timezone": timezone,
            "calendar_id": calendar_id,
            "event_duration_minutes": event_duration_minutes,
        }
        if description:
            arguments["description"] = description

        res = await self.execute_tool(
            tool_name="GOOGLECALENDAR_CREATE_EVENT",
            tool_configs=tool_config,
            arguments=arguments,
        )
        return res.get("result", {})

    async def list_tasks(
        self,
        tasklist_id: str = "@default",
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves real pending tasks from Google Tasks via Composio.
        """
        tool_config = [
            {
                "tool_name": "googletasks",
                "tool_source": "composio",
                "action_names": ["GOOGLETASKS_LIST_TASKS"],
                "provider_uuid": settings.google_tasks_provider_uuid,
                "credential_id": settings.google_tasks_credential_id,
                "persist_auth": True,
            }
        ]
        arguments: Dict[str, Any] = {
            "tasklist_id": tasklist_id,
            "maxResults": max_results,
            "showCompleted": False,
        }
        res = await self.execute_tool(
            tool_name="GOOGLETASKS_LIST_TASKS",
            tool_configs=tool_config,
            arguments=arguments,
        )
        res_data = res.get("result", {})
        if isinstance(res_data, dict):
            data_field = res_data.get("data", {})
            if isinstance(data_field, dict):
                return data_field.get("tasks", []) or data_field.get("items", [])
        return []

    async def create_task(
        self,
        title: str,
        tasklist_id: str = "@default",
        notes: Optional[str] = None,
        due: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a real task in Google Tasks via Composio.
        """
        tool_config = [
            {
                "tool_name": "googletasks",
                "tool_source": "composio",
                "action_names": ["GOOGLETASKS_INSERT_TASK"],
                "provider_uuid": settings.google_tasks_provider_uuid,
                "credential_id": settings.google_tasks_credential_id,
                "persist_auth": True,
            }
        ]
        arguments: Dict[str, Any] = {
            "tasklist_id": tasklist_id,
            "title": title,
            "status": "needsAction",
        }
        if notes:
            arguments["notes"] = notes
        if due:
            arguments["due"] = due

        res = await self.execute_tool(
            tool_name="GOOGLETASKS_INSERT_TASK",
            tool_configs=tool_config,
            arguments=arguments,
        )
        return res.get("result", {})

    async def get_task(
        self,
        task_id: str,
        tasklist_id: str = "@default",
    ) -> Dict[str, Any]:
        """
        Retrieves a task by ID to verify its creation in Google Tasks.
        """
        tool_config = [
            {
                "tool_name": "googletasks",
                "tool_source": "composio",
                "action_names": ["GOOGLETASKS_GET_TASK"],
                "provider_uuid": settings.google_tasks_provider_uuid,
                "credential_id": settings.google_tasks_credential_id,
                "persist_auth": True,
            }
        ]
        arguments = {
            "tasklist_id": tasklist_id,
            "task_id": task_id,
        }
        res = await self.execute_tool(
            tool_name="GOOGLETASKS_GET_TASK",
            tool_configs=tool_config,
            arguments=arguments,
        )
        return res.get("result", {})

    async def create_gmail_draft(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
        user_id: str = "me",
    ) -> Dict[str, Any]:
        """
        Creates a real email draft in Gmail via Composio.
        Strict safety: Only stages/creates drafts, never sends messages.
        """
        tool_config = [
            {
                "tool_name": "gmail",
                "tool_source": "composio",
                "action_names": ["GMAIL_CREATE_EMAIL_DRAFT"],
                "provider_uuid": settings.gmail_provider_uuid,
                "credential_id": settings.gmail_credential_id,
                "persist_auth": True,
            }
        ]
        arguments: Dict[str, Any] = {
            "user_id": user_id,
            "recipient_email": recipient_email,
            "subject": subject,
            "body": body,
            "is_html": is_html,
        }
        res = await self.execute_tool(
            tool_name="GMAIL_CREATE_EMAIL_DRAFT",
            tool_configs=tool_config,
            arguments=arguments,
            agent_id=settings.lyzr_manager_agent_id,
        )
        return res.get("result", {})

    async def list_gmail_drafts(
        self,
        user_id: str = "me",
    ) -> Dict[str, Any]:
        """
        Retrieves real drafts from Gmail to verify draft creation.
        """
        tool_config = [
            {
                "tool_name": "gmail",
                "tool_source": "composio",
                "action_names": ["GMAIL_LIST_DRAFTS"],
                "provider_uuid": settings.gmail_provider_uuid,
                "credential_id": settings.gmail_credential_id,
                "persist_auth": True,
            }
        ]
        res = await self.execute_tool(
            tool_name="GMAIL_LIST_DRAFTS",
            tool_configs=tool_config,
            arguments={"user_id": user_id},
            agent_id=settings.lyzr_manager_agent_id,
        )
        return res.get("result", {})

    async def send_telegram_message(
        self,
        text: str,
        chat_id: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Sends an authorized, concise notification message to Telegram via Composio.
        """
        target_chat_id = chat_id or settings.telegram_chat_id
        if not target_chat_id:
            raise ValueError(
                "Telegram chat_id is missing. Please set TELEGRAM_CHAT_ID or provide a chat_id."
            )

        # Parse numeric chat_id if applicable
        parsed_chat_id: Any = target_chat_id
        if isinstance(target_chat_id, str) and (
            target_chat_id.isdigit() or (target_chat_id.startswith("-") and target_chat_id[1:].isdigit())
        ):
            parsed_chat_id = int(target_chat_id)

        tool_config = [
            {
                "tool_name": "telegram",
                "tool_source": "composio",
                "action_names": ["TELEGRAM_SEND_MESSAGE"],
                "provider_uuid": settings.telegram_provider_uuid,
                "credential_id": settings.telegram_credential_id,
                "persist_auth": True,
            }
        ]
        arguments: Dict[str, Any] = {
            "chat_id": parsed_chat_id,
            "text": text,
        }
        res = await self.execute_tool(
            tool_name="TELEGRAM_SEND_MESSAGE",
            tool_configs=tool_config,
            arguments=arguments,
            agent_id=settings.lyzr_manager_agent_id,
        )
        return res.get("result", {})

    async def get_telegram_bot_info(self) -> Dict[str, Any]:
        """
        Retrieves bot information from Telegram to verify bot connectivity.
        """
        tool_config = [
            {
                "tool_name": "telegram",
                "tool_source": "composio",
                "action_names": ["TELEGRAM_GET_ME"],
                "provider_uuid": settings.telegram_provider_uuid,
                "credential_id": settings.telegram_credential_id,
                "persist_auth": True,
            }
        ]
        res = await self.execute_tool(
            tool_name="TELEGRAM_GET_ME",
            tool_configs=tool_config,
            arguments={},
            agent_id=settings.lyzr_manager_agent_id,
        )
        return res.get("result", {})


