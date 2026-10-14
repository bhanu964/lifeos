import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.services.lyzr_service import LyzrService
from app.services.lyzr_system_prompt import (
    LIFEOS_MASTER_SYSTEM_PROMPT,
    LIFEOS_MANAGER_ROLE,
    LIFEOS_MANAGER_GOAL,
    get_master_system_prompt,
)


def test_master_system_prompt_structure():
    """Verify that the LifeOS Master System Prompt contains all 15 required sections and operating principles."""
    prompt = get_master_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 2000

    # Verify identity & core operating principle
    assert "You are LifeOS, the primary intelligence agent" in prompt
    assert "UNDERSTAND → PLAN → EXECUTE → VERIFY → REPORT" in prompt

    # Verify all 15 sections are present
    expected_sections = [
        "1. UNDERSTAND THE USER'S INTENTION",
        "2. THINK BEFORE ACTING",
        "3. COORDINATE SPECIALIST AGENTS",
        "4. USE TOOLS CORRECTLY",
        "5. EMAIL INTELLIGENCE",
        "6. TELEGRAM RESPONSES",
        "7. QDRANT AND PERSISTENT MEMORY",
        "8. GOOGLE TASKS AND CALENDAR",
        "9. MEMORY-AWARE EMAIL AND TASK WORKFLOWS",
        "10. APPROVAL AND PERMISSION CONTROL",
        "11. FAILURE HANDLING",
        "12. VERIFICATION AND STATUS REPORTING",
        "13. NATURAL COMMUNICATION STYLE",
        "14. STANDARD RESPONSE FORMAT",
        "15. FINAL OPERATING RULE",
    ]
    for section in expected_sections:
        assert section in prompt, f"Missing section: {section}"

    # Verify role & goal constants
    assert "LifeOS Master Intelligence Operator" in LIFEOS_MANAGER_ROLE
    assert "UNDERSTAND -> PLAN -> EXECUTE -> VERIFY -> REPORT" in LIFEOS_MANAGER_GOAL


@pytest.mark.asyncio
async def test_lyzr_manager_agent_automatically_receives_master_prompt():
    """Verify that calling chat() with the Manager Agent ID automatically populates instructions in the API payload."""
    service = LyzrService(
        api_key="test-key-lyzr",
        agent_id=settings.lyzr_manager_agent_id,
        default_user_id="test-user@lifeos.ai",
    )

    mock_response = httpx.Response(
        status_code=200,
        json={"response": "Plan created according to LifeOS Master Prompt.", "module_outputs": {}},
        request=httpx.Request("POST", "https://test.api"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await service.chat(
            message="Check my emails and summarize tasks",
            agent_id=settings.lyzr_manager_agent_id,
        )

        assert res["response"] == "Plan created according to LifeOS Master Prompt."
        mock_post.assert_awaited_once()

        payload = mock_post.call_args.kwargs["json"]
        # Verify instructions, role, and goal are in payload
        assert "instructions" in payload
        assert payload["instructions"] == LIFEOS_MASTER_SYSTEM_PROMPT
        assert payload["role"] == LIFEOS_MANAGER_ROLE
        assert payload["goal"] == LIFEOS_MANAGER_GOAL
        # Verify user message remains clean and separate from instructions
        assert payload["message"] == "Check my emails and summarize tasks"


@pytest.mark.asyncio
async def test_lyzr_custom_instructions_override():
    """Verify that caller-supplied instructions override the default Master System Prompt."""
    service = LyzrService(
        api_key="test-key-lyzr",
        agent_id=settings.lyzr_manager_agent_id,
        default_user_id="test-user@lifeos.ai",
    )

    mock_response = httpx.Response(
        status_code=200,
        json={"response": "Custom instruction output.", "module_outputs": {}},
        request=httpx.Request("POST", "https://test.api"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        custom_prompt = "Custom emergency override instructions."
        await service.chat(
            message="Test message",
            agent_id=settings.lyzr_manager_agent_id,
            instructions=custom_prompt,
        )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["instructions"] == custom_prompt


@pytest.mark.asyncio
async def test_non_manager_agent_does_not_inject_manager_prompt():
    """Verify that non-manager agents (like Fact Finder or general agents) do not have Manager instructions injected."""
    service = LyzrService(
        api_key="test-key-lyzr",
        agent_id="some-other-agent-id",
        default_user_id="test-user@lifeos.ai",
    )

    mock_response = httpx.Response(
        status_code=200,
        json={"response": "Non-manager output.", "module_outputs": {}},
        request=httpx.Request("POST", "https://test.api"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        await service.chat(
            message="Investigate facts",
            agent_id="some-other-agent-id",
        )

        payload = mock_post.call_args.kwargs["json"]
        assert "instructions" not in payload
        assert "role" not in payload
        assert "goal" not in payload
        assert payload["message"] == "Investigate facts"


@pytest.mark.asyncio
async def test_sync_manager_agent_in_studio_success():
    """Verify that sync_manager_agent_in_studio performs GET then PUT with AgentConfig."""
    service = LyzrService(api_key="test-key-lyzr")

    agent_config_mock = {
        "name": "AgentMemory Manager Agent",
        "description": "Old description",
        "provider_id": "openai",
        "model": "gpt-5.4-mini",
        "top_p": 1.0,
        "temperature": 0.7,
        "managed_agents": [],
    }

    mock_get = httpx.Response(
        status_code=200,
        json=agent_config_mock,
        request=httpx.Request("GET", "https://test.api"),
    )
    mock_put = httpx.Response(
        status_code=200,
        json={"message": "Agent updated successfully"},
        request=httpx.Request("PUT", "https://test.api"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as m_get, \
         patch("httpx.AsyncClient.put", new_callable=AsyncMock) as m_put:
        m_get.return_value = mock_get
        m_put.return_value = mock_put

        res = await service.sync_manager_agent_in_studio()
        assert res["ok"] is True
        assert m_get.await_count == 1
        assert m_put.await_count == 1

        put_payload = m_put.call_args.kwargs["json"]
        assert put_payload["agent_role"] == LIFEOS_MANAGER_ROLE
        assert put_payload["agent_goal"] == LIFEOS_MANAGER_GOAL
        assert put_payload["agent_instructions"] == LIFEOS_MASTER_SYSTEM_PROMPT
