"""Cryptographic services and key management for WizDesk data security at rest.

Provides AES-256-GCM authenticated database encryption and Windows DPAPI
(Data Protection API) hardware/user-credential backed key storage.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from wiz.core.config import config

# 8-byte file magic signatures
WIZ_ENCRYPTION_MAGIC = b"WIZENC01"
WIZ_BACKUP_MAGIC = b"WIZBAK01"

# Windows DPAPI import with safe non-Windows fallback
try:
    import win32crypt
    HAS_DPAPI = True
except ImportError:
    HAS_DPAPI = False


class CryptoManager:
    """Manages AES-256-GCM symmetric encryption and DPAPI-protected key persistence."""

    def __init__(self, key_dir: Optional[Path] = None):
        self.key_dir = key_dir or config.user_data_dir
        self.dpapi_file = self.key_dir / ".wizkey.dpapi"
        self.fallback_file = self.key_dir / ".wizkey.bin"

    @staticmethod
    def generate_key() -> bytes:
        """Generate a cryptographically secure 256-bit (32-byte) AES key."""
        return AESGCM.generate_key(bit_length=256)

    @staticmethod
    def format_key_for_display(key: bytes) -> str:
        """Format 32-byte key into human-readable dash-separated blocks:
        WIZK-XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX
        """
        hex_str = key.hex().upper()
        # 64 hex chars split into 8 blocks of 8 chars
        chunks = [hex_str[i:i + 8] for i in range(0, 64, 8)]
        return f"WIZK-{'-'.join(chunks)}"

    @staticmethod
    def parse_user_key(key_str: str) -> bytes:
        """Parse, validate, and return the 32-byte key from user input string.

        Accepts:
        - 'WIZK-A1B2C3D4-...'
        - Raw 64-character hex strings
        - Case-insensitive, ignores spaces and dashes
        """
        cleaned = key_str.strip().upper()
        if cleaned.startswith("WIZK-"):
            cleaned = cleaned[5:]
        cleaned = cleaned.replace("-", "").replace(" ", "").strip()

        if len(cleaned) != 64:
            raise ValueError(f"Invalid key length: expected 64 hex characters (32 bytes), got {len(cleaned)}")

        try:
            raw_key = bytes.fromhex(cleaned)
        except ValueError as e:
            raise ValueError(f"Invalid hex character in key string: {e}") from e

        if len(raw_key) != 32:
            raise ValueError(f"Invalid key byte size: expected 32 bytes, got {len(raw_key)}")

        return raw_key

    def store_key_dpapi(self, key: bytes, description: str = "WizDesk Master Encryption Key") -> None:
        """Securely store the master key using Windows DPAPI.

        DPAPI binds the key to the current Windows user login and machine credentials.
        On non-Windows systems, falls back to a restricted local file.
        """
        if len(key) != 32:
            raise ValueError("Key must be precisely 32 bytes (256 bits).")

        self.key_dir.mkdir(parents=True, exist_ok=True)

        if HAS_DPAPI and sys.platform == "win32":
            # CryptProtectData(DataIn, Description, OptionalEntropy, Reserved, PromptStruct, Flags)
            protected_blob = win32crypt.CryptProtectData(key, description, None, None, None, 0)
            self.dpapi_file.write_bytes(protected_blob)
            if self.fallback_file.exists():
                try:
                    self.fallback_file.unlink()
                except OSError:
                    pass
        else:
            # Fallback for Linux / macOS environments
            self.fallback_file.write_bytes(key)
            try:
                os.chmod(self.fallback_file, 0o600)
            except OSError:
                pass

    def load_key_dpapi(self) -> Optional[bytes]:
        """Load and decrypt the master key using DPAPI or local fallback."""
        if HAS_DPAPI and sys.platform == "win32" and self.dpapi_file.exists():
            try:
                blob = self.dpapi_file.read_bytes()
                # Returns (description, decrypted_data)
                _, key = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
                if len(key) == 32:
                    return key
            except Exception as e:
                print(f"[CryptoManager] Failed to unprotect key with DPAPI: {e}")

        if self.fallback_file.exists():
            try:
                key = self.fallback_file.read_bytes()
                if len(key) == 32:
                    return key
            except Exception as e:
                print(f"[CryptoManager] Failed to read fallback key: {e}")

        return None

    def delete_key_dpapi(self) -> None:
        """Remove DPAPI and fallback key files from disk."""
        for path in (self.dpapi_file, self.fallback_file):
            if path.exists():
                try:
                    path.unlink()
                except OSError as e:
                    print(f"[CryptoManager] Warning: Failed to delete key file {path}: {e}")

    def has_stored_key(self) -> bool:
        """Check if a stored master key is available on the machine."""
        return self.dpapi_file.exists() or self.fallback_file.exists()

    @staticmethod
    def encrypt_payload(data: bytes, key: bytes, magic: bytes = WIZ_ENCRYPTION_MAGIC) -> bytes:
        """Encrypt arbitrary bytes using AES-256-GCM.

        Format:
        [8-byte MAGIC] + [12-byte NONCE] + [CIPHERTEXT with 16-byte AUTH TAG]
        """
        if len(key) != 32:
            raise ValueError("AES-256 key must be 32 bytes.")

        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # Recommended 96-bit standard nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return magic + nonce + ciphertext

    @staticmethod
    def decrypt_payload(payload: bytes, key: bytes, expected_magic: Optional[bytes] = None) -> bytes:
        """Decrypt AES-256-GCM ciphertext payload and verify authentication tag.

        Format expected:
        [8-byte MAGIC] + [12-byte NONCE] + [CIPHERTEXT with 16-byte AUTH TAG]
        """
        if len(key) != 32:
            raise ValueError("AES-256 key must be 32 bytes.")

        if len(payload) < 8 + 12 + 16:
            raise ValueError("Payload too short to be a valid encrypted WizDesk archive.")

        magic = payload[:8]
        if expected_magic is not None and magic != expected_magic:
            raise ValueError(f"Magic header mismatch: expected {expected_magic!r}, got {magic!r}")

        nonce = payload[8:20]
        ciphertext = payload[20:]

        aesgcm = AESGCM(key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext
        except InvalidTag as e:
            raise ValueError("Authentication tag check failed: incorrect key or corrupted data.") from e

    @staticmethod
    def is_encrypted_file(file_path: Path) -> bool:
        """Check whether the given file has a WizDesk encrypted magic header."""
        if not file_path.is_file():
            return False
        try:
            with open(file_path, "rb") as f:
                header = f.read(8)
                return header in (WIZ_ENCRYPTION_MAGIC, WIZ_BACKUP_MAGIC)
        except OSError:
            return False


# Global default instance
crypto_manager = CryptoManager()
