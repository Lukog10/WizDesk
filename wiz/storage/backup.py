"""Automated and on-demand database backup management for WizDesk."""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from wiz.core.config import config
from wiz.core.crypto import (
    CryptoManager,
    WIZ_BACKUP_MAGIC,
    WIZ_ENCRYPTION_MAGIC,
    crypto_manager,
)


class BackupManager:
    """Handles snapshot backups, automated rolling retention, and database restoration."""

    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or (config.user_data_dir / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        db: Any,
        tag: str = "manual",
        encrypt: Optional[bool] = None,
        dest_path: Optional[Path] = None,
    ) -> Path:
        """Create a full snapshot backup of the current database state.

        Args:
            db: Database instance to snapshot.
            tag: Identifier tag ('manual', 'auto', 'pre-migrate', etc.).
            encrypt: Whether to encrypt the backup with AES-256-GCM.
                     If None, defaults to current config encryption setting.
            dest_path: Optional explicit target path; otherwise saved in self.backup_dir.

        Returns:
            Path to the written backup file.
        """
        if encrypt is None:
            encrypt = bool(config.get("encryption_enabled", False))

        # Retrieve plain SQLite bytes from active database instance
        raw_sqlite_bytes = db.get_raw_sqlite_bytes()
        if not raw_sqlite_bytes or not raw_sqlite_bytes.startswith(b"SQLite format 3\x00"):
            raise ValueError("Failed to obtain valid SQLite snapshot data from database.")

        # Determine target file path
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = ".wbak" if encrypt else ".bak"

        if dest_path:
            out_path = Path(dest_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            filename = f"wizdesk_backup_{now_str}_{tag}{extension}"
            out_path = self.backup_dir / filename
            counter = 1
            while out_path.exists():
                out_path = self.backup_dir / f"wizdesk_backup_{now_str}_{tag}_{counter}{extension}"
                counter += 1

        # Prepare payload
        if encrypt:
            key = crypto_manager.load_key_dpapi()
            if not key:
                raise ValueError("Cannot encrypt backup: no master encryption key available.")
            payload = CryptoManager.encrypt_payload(raw_sqlite_bytes, key, magic=WIZ_BACKUP_MAGIC)
        else:
            payload = raw_sqlite_bytes

        # Write atomically via temp file
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
        try:
            with open(tmp_path, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, out_path)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

        # Rolling retention cleanup for automatic backups
        if tag == "auto":
            keep_count = int(config.get("max_backups_retained", 5))
            self.clean_old_backups(keep_count=keep_count)

        return out_path

    def restore_backup(
        self,
        backup_path: Path,
        db: Any,
        custom_key: Optional[bytes] = None,
    ) -> bool:
        """Validate and restore a backup file into the active database instance.

        Args:
            backup_path: Path to the backup file to restore.
            db: Target Database instance.
            custom_key: Optional decryption key (if encrypted and not using local DPAPI).

        Returns:
            True on successful restore.

        Raises:
            ValueError: If the file is corrupt, invalid, or decryption fails.
        """
        if not backup_path.is_file():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        raw_data = backup_path.read_bytes()
        if len(raw_data) < 16:
            raise ValueError("File is too small to be a valid backup.")

        # Check if file is encrypted
        if raw_data.startswith(WIZ_BACKUP_MAGIC) or raw_data.startswith(WIZ_ENCRYPTION_MAGIC):
            key = custom_key or crypto_manager.load_key_dpapi()
            if not key:
                raise ValueError("Backup is encrypted but no decryption key was provided or found in DPAPI.")
            expected_magic = raw_data[:8]
            sqlite_bytes = CryptoManager.decrypt_payload(raw_data, key, expected_magic=expected_magic)
        else:
            sqlite_bytes = raw_data

        # Verify SQLite format and structure integrity
        if not sqlite_bytes.startswith(b"SQLite format 3\x00"):
            raise ValueError("Restored data is not a valid SQLite database header.")

        verify_tmp = self.backup_dir / f".verify_{os.getpid()}_{datetime.now().strftime('%f')}.db"
        try:
            verify_tmp.write_bytes(sqlite_bytes)
            test_conn = sqlite3.connect(str(verify_tmp))
            test_cur = test_conn.cursor()
            test_cur.execute("PRAGMA integrity_check;")
            res = test_cur.fetchone()
            if not res or res[0] != "ok":
                raise ValueError(f"SQLite integrity check failed on backup: {res}")
            test_cur.execute("SELECT count(*) FROM tasks;")
            test_cur.fetchone()
            test_conn.close()
        except Exception as e:
            raise ValueError(f"Backup verification failed: {e}") from e
        finally:
            if verify_tmp.exists():
                try:
                    verify_tmp.unlink()
                except OSError:
                    pass

        # Apply restored bytes to active database
        db.restore_from_raw_bytes(sqlite_bytes)
        return True

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backup snapshots in descending chronological order."""
        if not self.backup_dir.exists():
            return []

        results: List[Dict[str, Any]] = []
        for file in self.backup_dir.iterdir():
            if not file.is_file():
                continue
            ext = file.suffix.lower()
            if ext not in (".bak", ".wbak"):
                continue

            stat = file.stat()
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)

            is_enc = ext == ".wbak"
            tag = "manual"
            if "_auto." in file.name or "_auto_" in file.name:
                tag = "auto"
            elif "_pre-migrate." in file.name:
                tag = "pre-migrate"

            # Human-readable size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.2f} MB"

            results.append({
                "filename": file.name,
                "path": file,
                "size_bytes": size,
                "size_str": size_str,
                "created_at": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": stat.st_mtime,
                "is_encrypted": is_enc,
                "tag": tag,
            })

        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results

    def clean_old_backups(self, keep_count: int = 5) -> int:
        """Prune older automated backups to enforce retention limits.

        Preserves all manual and pre-migration backups regardless of keep_count.
        """
        backups = self.list_backups()
        auto_backups = [b for b in backups if b["tag"] == "auto"]

        deleted = 0
        if len(auto_backups) > keep_count:
            to_remove = auto_backups[keep_count:]
            for item in to_remove:
                try:
                    item["path"].unlink()
                    deleted += 1
                except OSError as e:
                    print(f"[BackupManager] Failed to prune backup {item['path']}: {e}")

        return deleted


# Global default instance
backup_manager = BackupManager()
