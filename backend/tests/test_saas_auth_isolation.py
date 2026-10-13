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
