"""Local secret encryption for sensitive settings (API keys).

Uses OS keyring when available; falls back to a machine-derived AES-256 key
with a per-install random salt (NIST SP 800-132).
"""

from __future__ import annotations

import base64
import hashlib
import os
import platform
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from core.branding import KEYRING_SERVICE

KEY_NAME = "settings_master_key"
_ENCRYPTED_PREFIX = "enc:v1:"
_SALT_BYTES = 16  # NIST SP 800-132 minimum for PBKDF2
_SALT_FILENAME = "kdf_salt.bin"
# Pre-random-salt installs only — never use as the primary salt.
_LEGACY_FIXED_SALT = hashlib.sha256(b"OrcFin-local-fallback").digest()

_uses_system_keyring: bool | None = None
_legacy_key_used: bool = False


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


def _fallback_salt_path() -> Path:
    from core.paths import ensure_app_dirs, get_app_data_dir

    ensure_app_dirs()
    return get_app_data_dir() / "config" / _SALT_FILENAME


def _restrict_file_permissions(path: Path) -> None:
    """Best-effort owner-only access (Unix mode bits; Windows ACL via icacls)."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    if os.name != "nt":
        return
    try:
        import subprocess

        user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        if not user:
            return
        subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"{user}:(R,W)",
            ],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


def _write_salt_file(path: Path, salt: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(salt)
    _restrict_file_permissions(tmp)
    tmp.replace(path)
    _restrict_file_permissions(path)


def _load_or_create_fallback_salt() -> bytes:
    """Per-install random salt, persisted outside the keyring (NIST SP 800-132)."""
    path = _fallback_salt_path()
    if path.is_file():
        try:
            salt = path.read_bytes()
        except OSError:
            salt = b""
        if len(salt) == _SALT_BYTES:
            return salt
    salt = os.urandom(_SALT_BYTES)
    _write_salt_file(path, salt)
    return salt


def uses_system_keyring() -> bool:
    global _uses_system_keyring
    if _uses_system_keyring is None:
        _get_or_create_master_key()
    return bool(_uses_system_keyring)


def consume_legacy_key_migration() -> bool:
    """True once after a decrypt used the pre-random-salt key (caller should re-save)."""
    global _legacy_key_used
    if not _legacy_key_used:
        return False
    _legacy_key_used = False
    return True


def _get_or_create_master_key() -> bytes:
    global _uses_system_keyring
    try:
        import keyring

        stored = keyring.get_password(KEYRING_SERVICE, KEY_NAME)
        if stored:
            _uses_system_keyring = True
            return base64.urlsafe_b64decode(stored.encode("ascii"))
        key = AESGCM.generate_key(bit_length=256)
        keyring.set_password(
            KEYRING_SERVICE,
            KEY_NAME,
            base64.urlsafe_b64encode(key).decode("ascii"),
        )
        _uses_system_keyring = True
        return key
    except Exception:
        _uses_system_keyring = False
        salt = _load_or_create_fallback_salt()
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
    global _legacy_key_used
    if not value:
        return ""
    if not value.startswith(_ENCRYPTED_PREFIX):
        return value
    token = value[len(_ENCRYPTED_PREFIX) :]
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce, ciphertext = raw[:12], raw[12:]
    key = _get_or_create_master_key()
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception:
        if _uses_system_keyring:
            raise
        # Migrate secrets encrypted under the old fixed public salt.
        legacy_key = _derive_key_from_machine(_LEGACY_FIXED_SALT)
        if legacy_key == key:
            raise
        plaintext = AESGCM(legacy_key).decrypt(nonce, ciphertext, None).decode("utf-8")
        _legacy_key_used = True
        return plaintext


def is_encrypted(value: str) -> bool:
    return bool(value) and value.startswith(_ENCRYPTED_PREFIX)
