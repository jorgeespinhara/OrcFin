"""Local secret encryption for sensitive settings (API keys).

Uses OS keyring when available; falls back to a machine-derived AES-256 key.
"""

from __future__ import annotations

import base64
import hashlib
import os
import platform
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from core.branding import KEYRING_SERVICE, LEGACY_KEYRING_SERVICE

KEY_NAME = "settings_master_key"
_ENCRYPTED_PREFIX = "enc:v1:"


def _machine_fingerprint() -> bytes:
    parts = [
        platform.node(),
        platform.system(),
        platform.machine(),
        str(uuid.getnode()),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).digest()


def _derive_key_from_machine(salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    return kdf.derive(_machine_fingerprint())


def _get_or_create_master_key() -> bytes:
    try:
        import keyring

        for service in (KEYRING_SERVICE, LEGACY_KEYRING_SERVICE):
            stored = keyring.get_password(service, KEY_NAME)
            if stored:
                return base64.urlsafe_b64decode(stored.encode("ascii"))
        key = AESGCM.generate_key(bit_length=256)
        keyring.set_password(
            KEYRING_SERVICE,
            KEY_NAME,
            base64.urlsafe_b64encode(key).decode("ascii"),
        )
        return key
    except Exception:
        salt = hashlib.sha256(b"OrcFin-local-fallback").digest()
        return _derive_key_from_machine(salt)


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    key = _get_or_create_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    token = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{_ENCRYPTED_PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(_ENCRYPTED_PREFIX):
        return value
    token = value[len(_ENCRYPTED_PREFIX) :]
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce, ciphertext = raw[:12], raw[12:]
    key = _get_or_create_master_key()
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def is_encrypted(value: str) -> bool:
    return bool(value) and value.startswith(_ENCRYPTED_PREFIX)