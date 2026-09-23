"""SQLite database connection, encryption lifecycle, and schema management for WizDesk."""

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple

from wiz.core.config import config
from wiz.core.crypto import (
    CryptoManager,
    WIZ_ENCRYPTION_MAGIC,
    crypto_manager,
)


SCHEMA_SQL = """
-- Auto-tracked application sessions
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name TEXT NOT NULL,
    window_title TEXT,
    project_tag TEXT,
    start_time TEXT NOT NULL,  -- ISO-8601 string
    end_time TEXT NOT NULL
);

-- Flat quick notes
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    project_tag TEXT,
    created_at TEXT NOT NULL,
    is_completed INTEGER DEFAULT 0  -- 0 = open, 1 = completed
);

-- Structured parent tasks
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    project_tag TEXT,
    status TEXT DEFAULT 'not_started',  -- 'not_started' | 'in_progress' | 'done'
    created_at TEXT NOT NULL,
    completed_at TEXT,
    scheduled_date TEXT DEFAULT NULL,       -- ISO-8601 Date: YYYY-MM-DD
    repeat_mode TEXT DEFAULT 'none',        -- 'none' | 'daily' | 'weekdays' | 'weekends'
    last_completed_date TEXT DEFAULT NULL   -- ISO-8601 Date: YYYY-MM-DD
);

-- Subtasks belonging to a task
CREATE TABLE IF NOT EXISTS subtasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'not_started',  -- 'not_started' | 'in_progress' | 'done'
    created_at TEXT NOT NULL,
    completed_at TEXT
);

-- Running timestamped log entries on tasks or subtasks
CREATE TABLE IF NOT EXISTS task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    subtask_id INTEGER REFERENCES subtasks(id) ON DELETE CASCADE,  -- NULL = log on parent task
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Project keyword matching configuration
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    keywords TEXT NOT NULL,  -- Comma-separated match hints
    color TEXT DEFAULT '#FF6B3D',
    description TEXT DEFAULT ''
);

-- Indices for rapid daily reporting, project filtering, and sync queries
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_sessions_project_tag ON sessions(project_tag);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_notes_project_tag ON notes(project_tag);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_project_tag ON tasks(project_tag);
CREATE INDEX IF NOT EXISTS idx_subtasks_task_id ON subtasks(task_id);
CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_logs(task_id);
"""


class Database:
    """Manages SQLite database connections, AES-256-GCM encryption lifecycle, and transactions."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db_path
        self.is_memory_db = str(self.db_path) == ":memory:"

        if not self.is_memory_db:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.enc_path = self.db_path.with_name(self.db_path.name + ".enc")
        else:
            self.enc_path = Path(":memory:.enc")

        self._lock = threading.RLock()
        self._mem_conn: Optional[sqlite3.Connection] = None
        self._is_encrypted = False

        self._init_database_state()

    @property
    def is_encrypted(self) -> bool:
        """Check whether the active database is running in encrypted mode."""
        return self._is_encrypted

    def _init_database_state(self) -> None:
        """Initialize connection, detect encryption state, and execute schema migrations."""
        with self._lock:
            enc_file_exists = not self.is_memory_db and self.enc_path.is_file()
            is_default_db = not self.is_memory_db and self.db_path == config.db_path
            config_enc_enabled = is_default_db and bool(config.get("encryption_enabled", False))

            if enc_file_exists or config_enc_enabled:
                self._init_encrypted_mode()
            else:
                self._init_standard_mode()

    def _init_encrypted_mode(self) -> None:
        """Initialize an in-memory SQLite database loaded from AES-256-GCM encrypted disk file."""
        key = crypto_manager.load_key_dpapi()
        if not key:
            key = CryptoManager.generate_key()
            crypto_manager.store_key_dpapi(key)

        self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._mem_conn.row_factory = sqlite3.Row
        self._mem_conn.execute("PRAGMA foreign_keys = ON;")
        self._mem_conn.execute("PRAGMA journal_mode = MEMORY;")
        self._is_encrypted = True

        if not self.is_memory_db and self.enc_path.is_file():
            try:
                encrypted_blob = self.enc_path.read_bytes()
                plain_bytes = CryptoManager.decrypt_payload(
                    encrypted_blob, key, expected_magic=WIZ_ENCRYPTION_MAGIC
                )
                self._mem_conn.deserialize(plain_bytes)
                self._run_schema_and_migrations(self._mem_conn)
            except Exception as e:
                print(f"[Database] Error decrypting database: {e}. Reinitializing schema.")
                self._run_schema_and_migrations(self._mem_conn)
                self._flush_to_disk(key=key)
        elif not self.is_memory_db and self.db_path.is_file():
            # Migrate existing plaintext database to encrypted memory format
            try:
                src_conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                src_conn.execute("PRAGMA journal_mode = DELETE;")
                src_conn.backup(self._mem_conn)
                src_conn.close()
                self._run_schema_and_migrations(self._mem_conn)
            except Exception as e:
                print(f"[Database] Error migrating plaintext db: {e}")
                self._run_schema_and_migrations(self._mem_conn)

            self._flush_to_disk(key=key)
            try:
                self.db_path.unlink()
            except OSError:
                pass
        else:
            self._run_schema_and_migrations(self._mem_conn)
            if not self.is_memory_db:
                self._flush_to_disk(key=key)

        if not self.is_memory_db and self.db_path == config.db_path:
            config.set("encryption_enabled", True)

    def _init_standard_mode(self) -> None:
        """Initialize standard plaintext file-based or memory SQLite database."""
        self._is_encrypted = False
        conn = self.get_connection()
        try:
            self._run_schema_and_migrations(conn)
        finally:
            conn.close()

    def _run_schema_and_migrations(self, conn: sqlite3.Connection) -> None:
        """Execute core schema definitions and table column migrations."""
        conn.execute("PRAGMA foreign_keys = ON;")
        if not self._is_encrypted and not self.is_memory_db:
            try:
                conn.execute("PRAGMA journal_mode = WAL;")
            except sqlite3.OperationalError:
                pass
        else:
            try:
                conn.execute("PRAGMA journal_mode = MEMORY;")
            except sqlite3.OperationalError:
                pass

        conn.executescript(SCHEMA_SQL)

        # Safe migrations for projects table extensions
        try:
            conn.execute("ALTER TABLE projects ADD COLUMN color TEXT DEFAULT '#FF6B3D'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE projects ADD COLUMN description TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        # Safe migrations for tasks table scheduling and repeat extensions
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN scheduled_date TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN repeat_mode TEXT DEFAULT 'none'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN last_completed_date TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date)")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_repeat_mode ON tasks(repeat_mode)")
        except sqlite3.OperationalError:
            pass
        conn.commit()

    def _flush_to_disk(self, key: Optional[bytes] = None) -> None:
        """Serialize in-memory SQLite database, encrypt with AES-256-GCM, and save to disk atomically."""
        if self.is_memory_db or not self._is_encrypted or self._mem_conn is None:
            return

        if key is None:
            key = crypto_manager.load_key_dpapi()
            if not key:
                print("[Database] Warning: Cannot flush encrypted DB without master key.")
                return

        raw_bytes = self._mem_conn.serialize()
        encrypted_payload = CryptoManager.encrypt_payload(
            raw_bytes, key, magic=WIZ_ENCRYPTION_MAGIC
        )

        tmp_path = self.enc_path.with_suffix(self.enc_path.suffix + ".tmp")
        try:
            with open(tmp_path, "wb") as f:
                f.write(encrypted_payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.enc_path)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def get_connection(self) -> sqlite3.Connection:
        """Create or return an SQLite connection with row factory and foreign keys enabled."""
        if self._is_encrypted and self._mem_conn is not None:
            return self._mem_conn

        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def cursor(self):
        """Context manager providing a thread-safe, auto-committing database cursor."""
        with self._lock:
            if self._is_encrypted and self._mem_conn is not None:
                cur = self._mem_conn.cursor()
                try:
                    yield cur
                    self._mem_conn.commit()
                    self._flush_to_disk()
                except Exception:
                    self._mem_conn.rollback()
                    raise
                finally:
                    cur.close()
            else:
                conn = self.get_connection()
                try:
                    cur = conn.cursor()
                    yield cur
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()

    def get_raw_sqlite_bytes(self) -> bytes:
        """Retrieve unencrypted SQLite binary database snapshot for backup or export."""
        with self._lock:
            if self._is_encrypted and self._mem_conn is not None:
                return self._mem_conn.serialize()
            elif not self.is_memory_db and self.db_path.is_file():
                src_conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                temp_mem = sqlite3.connect(":memory:")
                try:
                    src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    src_conn.backup(temp_mem)
                    return temp_mem.serialize()
                finally:
                    src_conn.close()
                    temp_mem.close()
            else:
                conn = self.get_connection()
                temp_mem = sqlite3.connect(":memory:")
                try:
                    conn.backup(temp_mem)
                    return temp_mem.serialize()
                finally:
                    conn.close()
                    temp_mem.close()

    def restore_from_raw_bytes(self, raw_bytes: bytes) -> None:
        """Restore database state from plain SQLite binary data."""
        with self._lock:
            if self._is_encrypted and self._mem_conn is not None:
                self._mem_conn.deserialize(raw_bytes)
                self._run_schema_and_migrations(self._mem_conn)
                self._flush_to_disk()
            else:
                if not self.is_memory_db:
                    wal_file = self.db_path.with_name(self.db_path.name + "-wal")
                    shm_file = self.db_path.with_name(self.db_path.name + "-shm")
                    for f in (wal_file, shm_file):
                        if f.exists():
                            try:
                                f.unlink()
                            except OSError:
                                pass
                    tmp_file = self.db_path.with_suffix(".tmp")
                    with open(tmp_file, "wb") as f:
                        f.write(raw_bytes)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp_file, self.db_path)
                    conn = self.get_connection()
                    try:
                        self._run_schema_and_migrations(conn)
                    finally:
                        conn.close()

    def enable_encryption(self) -> Tuple[bool, str]:
        """Convert the current database to AES-256-GCM encrypted mode at rest.

        Returns:
            Tuple of (success: bool, user_formatted_key: str)
        """
        with self._lock:
            if self._is_encrypted:
                key = crypto_manager.load_key_dpapi()
                formatted = CryptoManager.format_key_for_display(key) if key else ""
                return True, formatted

            # 1. Generate and store master key in DPAPI
            key = CryptoManager.generate_key()
            crypto_manager.store_key_dpapi(key)

            # 2. Setup in-memory connection
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
            self._mem_conn.execute("PRAGMA foreign_keys = ON;")
            self._mem_conn.execute("PRAGMA journal_mode = MEMORY;")

            # 3. Migrate data from disk into memory
            if not self.is_memory_db and self.db_path.is_file():
                src_conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                src_conn.execute("PRAGMA journal_mode = DELETE;")
                src_conn.backup(self._mem_conn)
                src_conn.close()
                try:
                    self.db_path.unlink()
                except OSError:
                    pass

            self._run_schema_and_migrations(self._mem_conn)

            # 4. Save encrypted file to disk
            self._is_encrypted = True
            if not self.is_memory_db:
                self._flush_to_disk(key=key)

            # 5. Update config
            if not self.is_memory_db and self.db_path == config.db_path:
                config.set("encryption_enabled", True)
            formatted_key = CryptoManager.format_key_for_display(key)
            return True, formatted_key

    def disable_encryption(self) -> Tuple[bool, str]:
        """Decrypt database and revert to standard plaintext SQLite file on disk."""
        with self._lock:
            if not self._is_encrypted or self._mem_conn is None:
                return True, "Encryption already disabled."

            # 1. Write memory DB to plaintext database file on disk using backup API
            if not self.is_memory_db:
                disk_conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                self._mem_conn.backup(disk_conn)
                disk_conn.execute("PRAGMA journal_mode = WAL;")
                disk_conn.close()

            # 2. Delete encrypted database and DPAPI key
            if not self.is_memory_db and self.enc_path.is_file():
                try:
                    self.enc_path.unlink()
                except OSError as e:
                    print(f"[Database] Warning: Failed to remove encrypted file: {e}")

            crypto_manager.delete_key_dpapi()

            # 3. Clean up in-memory connection
            try:
                self._mem_conn.close()
            except Exception:
                pass
            self._mem_conn = None
            self._is_encrypted = False

            # 4. Update config
            if not self.is_memory_db and self.db_path == config.db_path:
                config.set("encryption_enabled", False)
            return True, "Database successfully decrypted to standard plaintext."


# Global singleton instance
_default_db: Optional[Database] = None


def get_db(db_path: Optional[Path] = None) -> Database:
    """Retrieve or initialize the global database instance."""
    global _default_db
    if db_path is not None:
        return Database(db_path)
    if _default_db is None:
        _default_db = Database()
    return _default_db
