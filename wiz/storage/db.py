"""SQLite database connection and schema management for Wiz."""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from wiz.core.config import config


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

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
    completed_at TEXT
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
    keywords TEXT NOT NULL  -- Comma-separated match hints
);

-- Indices for rapid daily reporting and sync queries
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_subtasks_task_id ON subtasks(task_id);
CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_logs(task_id);
"""


class Database:
    """Manages SQLite database connections and transactions."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with row factory and foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def cursor(self):
        """Context manager providing an auto-committing database cursor."""
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

    def init_db(self) -> None:
        """Initialize database tables and schema indices."""
        conn = self.get_connection()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()


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
