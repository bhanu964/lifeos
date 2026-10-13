import pytest
import httpx
from unittest.mock import AsyncMock, patch
from app.services.lyzr_service import LyzrService, LyzrAPIError


@pytest.mark.asyncio
async def test_lyzr_missing_api_key_raises():
    service = LyzrService(api_key="", agent_id="agent-123", default_user_id="user-123")
    with pytest.raises(LyzrAPIError) as exc_info:
        await service.chat(message="Hello")
    assert "Lyzr API key is missing" in str(exc_info.value)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_lyzr_success_call():
    service = LyzrService(
        api_key="test-key-123",
        agent_id="test-agent",
        default_user_id="test-user",
    )

    mock_response = httpx.Response(
        status_code=200,
        json={"response": "The answer is 42", "module_outputs": {}},
        request=httpx.Request("POST", "http://test"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await service.chat(
            message="What is the answer?",
            user_id="test-user",
            session_id="session-xyz",
        )

        assert res["response"] == "The answer is 42"
        assert res["agent_id"] == "test-agent"
        assert res["session_id"] == "session-xyz"

        # Verify headers and payload
        mock_post.assert_awaited_once()
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["x-api-key"] == "test-key-123"
        json_body = mock_post.call_args.kwargs["json"]
        assert json_body["user_id"] == "test-user"
        assert json_body["agent_id"] == "test-agent"
        assert json_body["session_id"] == "session-xyz"
        assert json_body["message"] == "What is the answer?"


@pytest.mark.asyncio
async def test_lyzr_timeout_handling():
    service = LyzrService(api_key="test-key", timeout=1.0)

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timed out")):
        with pytest.raises(LyzrAPIError) as exc_info:
            await service.chat(message="Will timeout")

        assert exc_info.value.status_code == 504
        assert "timed out" in str(exc_info.value)
        # Ensure API key is NOT leaked in the error message
        assert "test-key" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_lyzr_http_error_response():
    service = LyzrService(api_key="test-key")

    mock_response = httpx.Response(
        status_code=403,
        text='{"detail": "Forbidden"}',
        request=httpx.Request("POST", "http://test"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(LyzrAPIError) as exc_info:
            await service.chat(message="Query")

        assert exc_info.value.status_code == 403
        assert "403" in str(exc_info.value)
        # Ensure API key is NOT leaked in the error message
        assert "test-key" not in str(exc_info.value)
