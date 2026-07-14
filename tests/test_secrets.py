"""Secrets: keyring fallback uses per-install random salt (not a fixed public constant)."""

from __future__ import annotations

import base64
import hashlib
import sys
import types
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.secrets import (
    _ENCRYPTED_PREFIX,
    _LEGACY_FIXED_SALT,
    _SALT_BYTES,
    _SALT_FILENAME,
    _derive_key_from_machine,
    consume_legacy_key_migration,
    decrypt_secret,
    encrypt_secret,
    is_encrypted,
)


@pytest.fixture
def fallback_only(monkeypatch, project_tmp_path):
    """Force machine-derived key path (no OS keyring) under an isolated data dir."""
    import core.secrets as secrets

    monkeypatch.setenv("ORCFIN_DATA_DIR", str(project_tmp_path))
    monkeypatch.setattr(secrets, "_uses_system_keyring", None)
    monkeypatch.setattr(secrets, "_legacy_key_used", False)

    broken = types.ModuleType("keyring")

    def _fail(*_args, **_kwargs):
        raise RuntimeError("keyring unavailable for test")

    broken.get_password = _fail  # type: ignore[attr-defined]
    broken.set_password = _fail  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "keyring", broken)

    yield project_tmp_path
    secrets._uses_system_keyring = None
    secrets._legacy_key_used = False


def test_encrypt_decrypt_roundtrip(fallback_only):
    token = encrypt_secret("sk-test-secret")
    assert is_encrypted(token)
    assert token.startswith(_ENCRYPTED_PREFIX)
    assert decrypt_secret(token) == "sk-test-secret"


def test_fallback_creates_random_salt_file(fallback_only: Path):
    encrypt_secret("one")
    salt_path = fallback_only / "config" / _SALT_FILENAME
    assert salt_path.is_file()
    salt = salt_path.read_bytes()
    assert len(salt) == _SALT_BYTES
    assert salt != _LEGACY_FIXED_SALT
    assert salt != hashlib.sha256(b"OrcFin-local-fallback").digest()


def test_salt_reused_across_calls(fallback_only: Path):
    encrypt_secret("a")
    salt_path = fallback_only / "config" / _SALT_FILENAME
    first = salt_path.read_bytes()
    encrypt_secret("b")
    assert salt_path.read_bytes() == first


def test_different_salts_yield_different_keys(fallback_only: Path):
    salt_a = b"\x01" * _SALT_BYTES
    salt_b = b"\x02" * _SALT_BYTES
    assert _derive_key_from_machine(salt_a) != _derive_key_from_machine(salt_b)


def test_legacy_fixed_salt_ciphertext_still_decrypts(fallback_only: Path):
    """Secrets encrypted before per-install salt remain readable and mark migration."""
    import core.secrets as secrets

    legacy_key = _derive_key_from_machine(_LEGACY_FIXED_SALT)
    nonce = b"\x00" * 12
    ciphertext = AESGCM(legacy_key).encrypt(nonce, b"legacy-api-key", None)
    token = _ENCRYPTED_PREFIX + base64.urlsafe_b64encode(nonce + ciphertext).decode(
        "ascii"
    )

    # Ensure current master key uses a random salt (not the legacy constant).
    encrypt_secret("seed-salt-file")
    secrets._legacy_key_used = False

    assert decrypt_secret(token) == "legacy-api-key"
    assert consume_legacy_key_migration() is True
    assert consume_legacy_key_migration() is False


def test_empty_secret(fallback_only):
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""
