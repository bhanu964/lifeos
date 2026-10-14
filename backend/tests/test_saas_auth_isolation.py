import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.crypto_service import decrypt_payload
from app.services.user_credentials_service import UserCredentialsService


@pytest.mark.asyncio
async def test_saas_signup_login_and_me():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        # 1. Signup User A
        signup_payload = {
            "email": unique_email,
            "password": "Password123!",
            "full_name": "Alice Operator",
        }
        res = await client.post("/api/auth/signup", json=signup_payload)
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == unique_email
        assert len(data["user"]["omi_webhook_token"]) > 16
        token_a = data["access_token"]

        # 2. Duplicate Signup rejection
        res_dup = await client.post("/api/auth/signup", json=signup_payload)
        assert res_dup.status_code == 400

        # 3. Login User A
        login_payload = {
            "email": unique_email,
            "password": "Password123!",
        }
        res_login = await client.post("/api/auth/login", json=login_payload)
        assert res_login.status_code == 200
        assert "access_token" in res_login.json()

        # 4. Login Invalid Password
        bad_login = {
            "email": unique_email,
            "password": "WrongPassword",
        }
        res_bad = await client.post("/api/auth/login", json=bad_login)
        assert res_bad.status_code == 401

        # 5. Access /api/auth/me with Bearer Token
        headers = {"Authorization": f"Bearer {token_a}"}
        res_me = await client.get("/api/auth/me", headers=headers)
        assert res_me.status_code == 200
        assert res_me.json()["email"] == unique_email

        # 6. Access /api/auth/me without Token -> 401
        res_me_anon = await client.get("/api/auth/me")
        assert res_me_anon.status_code == 401


@pytest.mark.asyncio
async def test_saas_rotate_omi_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"rotator_{uuid.uuid4().hex[:8]}@example.com"
        signup_payload = {
            "email": unique_email,
            "password": "Password123!",
            "full_name": "Token Rotator",
        }
        res = await client.post("/api/auth/signup", json=signup_payload)
        assert res.status_code == 201
        token = res.json()["access_token"]
        old_omi_token = res.json()["user"]["omi_webhook_token"]

        headers = {"Authorization": f"Bearer {token}"}
        res_rot = await client.post("/api/auth/rotate-omi-token", headers=headers)
        assert res_rot.status_code == 200
        new_omi_token = res_rot.json()["omi_webhook_token"]
        assert new_omi_token != old_omi_token


@pytest.mark.asyncio
async def test_saas_credentials_encryption_and_masking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"vault_{uuid.uuid4().hex[:8]}@example.com"
        signup_payload = {
            "email": unique_email,
            "password": "Password123!",
            "full_name": "Vault Tester",
        }
        res = await client.post("/api/auth/signup", json=signup_payload)
        assert res.status_code == 201
        token = res.json()["access_token"]
        user_id = res.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Save Qdrant credentials
        raw_secret_key = "qdrant-secret-test-key-9988776655"
        cred_save = {
            "credentials": {
                "qdrant_url": "https://test-qdrant-cluster.io:6333",
                "qdrant_api_key": raw_secret_key,
                "qdrant_collection_name": "vault_collection",
            }
        }
        res_save = await client.post("/api/integrations/qdrant", json=cred_save, headers=headers)
        assert res_save.status_code == 200
        data = res_save.json()
        assert data["status"] == "connected"
        # Secret MUST BE MASKED and NEVER plaintext
        assert raw_secret_key not in str(data)
        assert "••••••••" in data["masked_fields"]["qdrant_api_key"]

        # Verify underlying storage is encrypted
        decrypted = UserCredentialsService.get_decrypted_credentials(user_id, "qdrant")
        assert decrypted["qdrant_api_key"] == raw_secret_key


@pytest.mark.asyncio
async def test_saas_omi_v2_webhook_tenant_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"omi_{uuid.uuid4().hex[:8]}@example.com"
        signup_payload = {
            "email": unique_email,
            "password": "Password123!",
            "full_name": "Omi Voice Tester",
        }
        res = await client.post("/api/auth/signup", json=signup_payload)
        assert res.status_code == 201
        omi_token = res.json()["user"]["omi_webhook_token"]

        # Call with valid webhook token
        omi_payload = {
            "id": f"conv-test-{uuid.uuid4().hex[:8]}",
            "structured": {
                "title": "Check meetings",
                "overview": "User asked to verify calendar and draft an email.",
                "action_items": [{"description": "Review calendar schedule"}],
                "category": "personal",
            },
            "transcript_segments": [
                {
                    "text": "What meetings do I have tomorrow?",
                    "speaker": "user",
                    "start": 0.0,
                    "end": 2.5,
                }
            ],
        }
        res_omi = await client.post(f"/omi/v2/{omi_token}/conversation", json=omi_payload)
        assert res_omi.status_code == 200
        assert res_omi.json()["status"] in ["success", "completed"]

        # Call with invalid webhook token
        res_bad_token = await client.post("/omi/v2/invalid_fake_token_12345/conversation", json=omi_payload)
        assert res_bad_token.status_code == 404


@pytest.mark.asyncio
async def test_saas_custom_credentials_service_resolution():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"custom_creds_{uuid.uuid4().hex[:8]}@example.com"
        signup_payload = {
            "email": unique_email,
            "password": "Password123!",
            "full_name": "Custom Credentials Tester",
        }
        res = await client.post("/api/auth/signup", json=signup_payload)
        assert res.status_code == 201
        token = res.json()["access_token"]
        user_id = res.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Before custom credentials, resolves defaults
        default_qdrant = UserCredentialsService.get_qdrant_service_for_user(user_id)
        assert default_qdrant.collection_name == "agentmemory_memories"

        default_lyzr = UserCredentialsService.get_lyzr_service_for_user(user_id)
        assert default_lyzr.default_user_id == user_id

        # 2. Save custom Qdrant credentials
        await client.post(
            "/api/integrations/qdrant",
            json={
                "credentials": {
                    "qdrant_url": "https://custom-cluster.qdrant.tech:6333",
                    "qdrant_api_key": "custom-qdrant-key-12345",
                    "qdrant_collection_name": "custom_personal_memories",
                }
            },
            headers=headers,
        )

        custom_qdrant = UserCredentialsService.get_qdrant_service_for_user(user_id)
        assert custom_qdrant.collection_name == "custom_personal_memories"
        assert custom_qdrant.url == "https://custom-cluster.qdrant.tech:6333"

        # 3. Save custom Lyzr credentials with custom manager agent ID
        custom_agent_id = "agent-custom-998877"
        await client.post(
            "/api/integrations/lyzr",
            json={
                "credentials": {
                    "lyzr_api_key": "custom-lyzr-sk-9988",
                    "lyzr_manager_agent_id": custom_agent_id,
                }
            },
            headers=headers,
        )

        custom_lyzr = UserCredentialsService.get_lyzr_service_for_user(user_id)
        assert custom_lyzr.agent_id == custom_agent_id
        assert custom_lyzr.api_key == "custom-lyzr-sk-9988"

        # 4. Save custom Telegram bot credentials with custom chat ID
        custom_chat = "998877665"
        await client.post(
            "/api/integrations/telegram",
            json={
                "credentials": {
                    "telegram_bot_token": "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_custom",
                    "telegram_bot_username": "CustomUserBot",
                    "telegram_chat_id": custom_chat,
                }
            },
            headers=headers,
        )

        custom_tg = UserCredentialsService.get_telegram_service_for_user(user_id)
        assert custom_tg.bot_token == "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_custom"
        assert custom_tg.get_effective_chat_id(user_id) == custom_chat


@pytest.mark.asyncio
async def test_strict_user_credentials_and_zero_fallback():
    """
    Acceptance Criteria Matrix:
    1. Mode 1 (PRECONFIGURED LYZR):
       - Google Calendar & Google Tasks are active via preconfigured Lyzr.
       - Gmail is completely disabled and inaccessible (status unconfigured/policy inaccessible).
       - Testing Gmail fails with 400 Bad Request.
       - Action execution for Gmail draft raises ValueError in Preconfigured Lyzr mode.
    2. Mode 2 (USER'S OWN LYZR CREDENTIALS):
       - User provides own Lyzr credentials.
       - Google Calendar, Tasks, and Gmail are all enabled via user's Lyzr account.
       - Testing Gmail succeeds.
    3. Reversion:
       - Deleting custom Lyzr credentials safely restores Preconfigured Lyzr mode.
    4. Telegram chat resolution strictly yields None for unlinked users (no developer chat_id leak).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a brand new tenant user
        unique_email = f"isolated_user_{uuid.uuid4().hex[:8]}@example.com"
        signup_res = await client.post(
            "/api/auth/signup",
            json={"email": unique_email, "password": "SecurePassword123!", "full_name": "Isolated Tenant"},
        )
        assert signup_res.status_code == 201
        token = signup_res.json()["access_token"]
        uid = signup_res.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Check all integration statuses in PRECONFIGURED LYZR mode (Default)
        res_list = await client.get("/api/integrations", headers=headers)
        assert res_list.status_code == 200
        integrations = res_list.json()["integrations"]

        assert integrations["google_calendar"]["status"] == "connected"
        assert integrations["google_calendar"]["masked_fields"].get("mode") == "preconfigured_lyzr"
        assert integrations["google_tasks"]["status"] == "connected"
        assert integrations["google_tasks"]["masked_fields"].get("mode") == "preconfigured_lyzr"
        assert integrations["gmail"]["status"] == "unconfigured"
        assert integrations["gmail"]["masked_fields"].get("mode") == "preconfigured_lyzr"
        assert integrations["telegram"]["status"] == "unconfigured"
        assert integrations["qdrant"]["status"] == "unconfigured"
        assert integrations["lyzr"]["status"] == "connected"
        assert integrations["lyzr"]["masked_fields"].get("mode") == "preconfigured_lyzr"

        # 3. Check Telegram chat ID resolution for new user: must strictly be None
        from app.services.telegram_service import TelegramService
        tg_svc = TelegramService()
        assert tg_svc.get_effective_chat_id(uid) is None

        # 4. Mode 1 tests: Calendar and Tasks test endpoints succeed via Preconfigured Lyzr
        test_cal = await client.post("/api/integrations/google_calendar/test", headers=headers)
        assert test_cal.status_code == 200
        assert test_cal.json()["success"] is True

        test_tasks = await client.post("/api/integrations/google_tasks/test", headers=headers)
        assert test_tasks.status_code == 200
        assert test_tasks.json()["success"] is True

        # Mode 1 test: Gmail test MUST fail cleanly (disabled in Preconfigured mode)
        test_gmail = await client.post("/api/integrations/gmail/test", headers=headers)
        assert test_gmail.status_code == 400
        assert "disabled in preconfigured lyzr mode" in test_gmail.json()["detail"].lower()

        # 5. User provides OWN Lyzr credentials -> switches to Mode 2 (USER'S OWN LYZR CREDENTIALS)
        save_lyzr_res = await client.post(
            "/api/integrations/lyzr",
            json={"credentials": {"lyzr_api_key": "lyzr-sk-user-custom-secret-key-12345"}},
            headers=headers,
        )
        assert save_lyzr_res.status_code == 200

        # Verify Mode 2 statuses
        res_list_mode2 = await client.get("/api/integrations", headers=headers)
        assert res_list_mode2.status_code == 200
        integrations_m2 = res_list_mode2.json()["integrations"]

        assert integrations_m2["lyzr"]["masked_fields"].get("mode") == "user_own_lyzr"
        assert integrations_m2["google_calendar"]["masked_fields"].get("mode") == "user_own_lyzr"
        assert integrations_m2["google_tasks"]["masked_fields"].get("mode") == "user_own_lyzr"
        assert integrations_m2["gmail"]["status"] == "connected"
        assert integrations_m2["gmail"]["masked_fields"].get("mode") == "user_own_lyzr"

        # In Mode 2, testing Gmail succeeds via user's own Lyzr account
        test_gmail_m2 = await client.post("/api/integrations/gmail/test", headers=headers)
        assert test_gmail_m2.status_code == 200
        assert test_gmail_m2.json()["success"] is True

        # 6. Revert back to Preconfigured Lyzr
        del_lyzr_res = await client.delete("/api/integrations/lyzr", headers=headers)
        assert del_lyzr_res.status_code == 200

        # Verify reverted status
        res_list_reverted = await client.get("/api/integrations", headers=headers)
        integrations_rev = res_list_reverted.json()["integrations"]
        assert integrations_rev["gmail"]["status"] == "unconfigured"
        assert integrations_rev["gmail"]["masked_fields"].get("mode") == "preconfigured_lyzr"

        # 7. Verify ActionService strictly rejects Gmail draft execution in Preconfigured Lyzr mode
        from app.services.action_service import ActionService
        from app.models.action import ActionType
        action_svc = ActionService()
        staged_draft = await action_svc.stage_action(
            uid=uid,
            action_type=ActionType.CREATE_GMAIL_DRAFT,
            title="Draft to test@example.com",
            description="Testing email draft staging",
            parameters={"recipient_email": "test@example.com", "subject": "Subject", "body": "Body"},
        )
        with pytest.raises(ValueError, match="Gmail is completely disabled in Preconfigured Lyzr mode"):
            await action_svc.confirm_and_execute(staged_draft.action_id, uid)


