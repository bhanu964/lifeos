import base64
import hashlib
import hmac
import json
import os
import secrets
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Salt length and iterations for PBKDF2
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16

_fernet_instance: Optional[Fernet] = None


def get_fernet() -> Fernet:
    """Provides a singleton Fernet cipher instance."""
    global _fernet_instance
    if _fernet_instance is None:
        key_env = os.getenv("ENCRYPTION_KEY")
        if key_env:
            try:
                _fernet_instance = Fernet(key_env.encode("utf-8"))
                return _fernet_instance
            except Exception:
                pass
        
        # Derive stable 32-byte key from app secret or default seed
        secret_seed = os.getenv("JWT_SECRET_KEY") or os.getenv("LYZR_API_KEY") or "lifeos-master-salt-2026-solo-agents"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"lifeos_saas_static_salt_v1",
            iterations=10_000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(secret_seed.encode("utf-8")))
        _fernet_instance = Fernet(derived_key)
    return _fernet_instance


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with random salt."""
    salt = secrets.token_bytes(SALT_BYTES)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt:key string."""
    try:
        parts = stored_hash.split(":")
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        expected_key = bytes.fromhex(parts[1])
        actual_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return hmac.compare_digest(actual_key, expected_key)
    except Exception:
        return False


def encrypt_payload(data: Dict[str, Any]) -> str:
    """Serialize dictionary and encrypt with Fernet at rest."""
    raw_json = json.dumps(data, sort_keys=True).encode("utf-8")
    cipher = get_fernet()
    encrypted_bytes = cipher.encrypt(raw_json)
    return encrypted_bytes.decode("utf-8")


def decrypt_payload(encrypted_str: str) -> Dict[str, Any]:
    """Decrypt Fernet token and parse JSON payload."""
    if not encrypted_str:
        return {}
    cipher = get_fernet()
    decrypted_bytes = cipher.decrypt(encrypted_str.encode("utf-8"))
    return json.loads(decrypted_bytes.decode("utf-8"))


def mask_secret(value: str) -> str:
    """
    Mask sensitive secrets (API keys, bot tokens, passwords).
    Returns masked representation such as '••••••••4846' or 'sk••••••••1234'.
    Never reveals the secret in plaintext.
    """
    if not value or not isinstance(value, str):
        return ""
    val_clean = value.strip()
    if len(val_clean) <= 6:
        return "••••••••"
    prefix = val_clean[:3] if len(val_clean) > 12 else ""
    suffix = val_clean[-4:]
    return f"{prefix}••••••••{suffix}"
