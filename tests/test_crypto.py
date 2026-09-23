"""Unit tests for WizDesk cryptographic services and key management."""

import pytest
import os
import tempfile
from pathlib import Path
from wiz.core.crypto import (
    CryptoManager,
    WIZ_ENCRYPTION_MAGIC,
    WIZ_BACKUP_MAGIC,
)


def test_generate_key():
    key = CryptoManager.generate_key()
    assert isinstance(key, bytes)
    assert len(key) == 32


def test_format_and_parse_key():
    key = CryptoManager.generate_key()
    formatted = CryptoManager.format_key_for_display(key)
    assert formatted.startswith("WIZK-")
    assert len(formatted.split("-")) == 9  # WIZK + 8 blocks of 8 hex chars

    parsed = CryptoManager.parse_user_key(formatted)
    assert parsed == key


def test_parse_user_key_variants():
    key = CryptoManager.generate_key()
    raw_hex = key.hex()

    # Raw lowercase without prefix
    assert CryptoManager.parse_user_key(raw_hex.lower()) == key
    # With spaces and dashes
    spaced = " ".join([raw_hex[i:i+4] for i in range(0, len(raw_hex), 4)])
    assert CryptoManager.parse_user_key(spaced) == key
    # Mixed case with prefix
    assert CryptoManager.parse_user_key(f"wizk-{raw_hex.lower()}") == key


def test_parse_user_key_invalid():
    with pytest.raises(ValueError, match="Invalid key length"):
        CryptoManager.parse_user_key("WIZK-SHORTKEY")

    with pytest.raises(ValueError, match="Invalid hex"):
        CryptoManager.parse_user_key("Z" * 64)


def test_encrypt_decrypt_payload():
    key = CryptoManager.generate_key()
    original_data = b"WizDesk secret task data: build awesome features."

    encrypted1 = CryptoManager.encrypt_payload(original_data, key)
    encrypted2 = CryptoManager.encrypt_payload(original_data, key)

    assert encrypted1.startswith(WIZ_ENCRYPTION_MAGIC)
    # Nonces should be unique
    assert encrypted1 != encrypted2

    decrypted = CryptoManager.decrypt_payload(encrypted1, key, expected_magic=WIZ_ENCRYPTION_MAGIC)
    assert decrypted == original_data


def test_decrypt_tampered_payload():
    key = CryptoManager.generate_key()
    data = b"Critical database data"
    encrypted = bytearray(CryptoManager.encrypt_payload(data, key))

    # Tamper with one byte in the ciphertext body
    encrypted[-1] ^= 0xFF

    with pytest.raises(ValueError, match="Authentication tag check failed"):
        CryptoManager.decrypt_payload(bytes(encrypted), key)


def test_decrypt_wrong_key():
    key1 = CryptoManager.generate_key()
    key2 = CryptoManager.generate_key()
    data = b"Top secret notes"

    encrypted = CryptoManager.encrypt_payload(data, key1)
    with pytest.raises(ValueError, match="Authentication tag check failed"):
        CryptoManager.decrypt_payload(encrypted, key2)


def test_decrypt_magic_mismatch():
    key = CryptoManager.generate_key()
    data = b"Backup content"
    encrypted = CryptoManager.encrypt_payload(data, key, magic=WIZ_BACKUP_MAGIC)

    with pytest.raises(ValueError, match="Magic header mismatch"):
        CryptoManager.decrypt_payload(encrypted, key, expected_magic=WIZ_ENCRYPTION_MAGIC)


def test_dpapi_store_load_and_delete(tmp_path):
    mgr = CryptoManager(key_dir=tmp_path)
    assert not mgr.has_stored_key()
    assert mgr.load_key_dpapi() is None

    key = CryptoManager.generate_key()
    mgr.store_key_dpapi(key)

    assert mgr.has_stored_key()
    loaded = mgr.load_key_dpapi()
    assert loaded == key

    mgr.delete_key_dpapi()
    assert not mgr.has_stored_key()
    assert mgr.load_key_dpapi() is None


def test_is_encrypted_file(tmp_path):
    mgr = CryptoManager()
    plain_file = tmp_path / "plain.txt"
    plain_file.write_bytes(b"SQLite format 3\x00data...")
    assert not CryptoManager.is_encrypted_file(plain_file)

    enc_file = tmp_path / "enc.db"
    key = CryptoManager.generate_key()
    enc_data = CryptoManager.encrypt_payload(b"hello", key)
    enc_file.write_bytes(enc_data)
    assert CryptoManager.is_encrypted_file(enc_file)
