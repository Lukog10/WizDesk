"""Data models and repository for SQLite storage in Wiz."""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from wiz.storage.db import Database, get_db


@dataclass
class SessionRecord:
    """Represents an auto-tracked application usage session."""
    id: Optional[int]
    app_name: str
    window_title: str
    project_tag: Optional[str]
    start_time: datetime
    end_time: datetime

    @property
    def duration_minutes(self) -> float:
        """Calculate duration in minutes."""
        diff = self.end_time - self.start_time
        return max(0.0, diff.total_seconds() / 60.0)


@dataclass
class NoteRecord:
    """Represents a flat quick note or one-off log."""
    id: Optional[int]
    content: str
    project_tag: Optional[str]
    created_at: datetime
    is_completed: bool = False


@dataclass
class TaskLogRecord:
    """Represents a timestamped log entry on a task or subtask."""
    id: Optional[int]
    task_id: int
    subtask_id: Optional[int]
    content: str
    created_at: datetime


@dataclass
class SubtaskRecord:
    """Represents a subtask under a parent task."""
    id: Optional[int]
    task_id: int
    title: str
    status: str = "not_started"  # 'not_started' | 'in_progress' | 'done'
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    logs: List[TaskLogRecord] = field(default_factory=list)


@dataclass
class TaskRecord:
    """Represents a parent task with subtasks and log trails."""
    id: Optional[int]
    title: str
    project_tag: Optional[str]
    status: str = "not_started"  # 'not_started' | 'in_progress' | 'done'
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    subtasks: List[SubtaskRecord] = field(default_factory=list)
    task_logs: List[TaskLogRecord] = field(default_factory=list)


@dataclass
class ProjectRecord:
    """Represents project keyword matching configuration."""
    id: Optional[int]
    name: str
    keywords: List[str]  # e.g. ["turfline", "booking"]


class StorageRepository:
    """High-level repository for database CRUD operations."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    # --- Session Operations ---

    def log_session(
        self,
        app_name: str,
        window_title: str,
        start_time: datetime,
        end_time: datetime,
        project_tag: Optional[str] = None,
    ) -> int:
        """Insert a tracked application session."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (app_name, window_title, project_tag, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    app_name,
                    window_title,
                    project_tag,
                    start_time.isoformat(),
                    end_time.isoformat(),
                ),
            )
            return cur.lastrowid or 0

    def get_sessions_for_date(self, target_date: date) -> List[SessionRecord]:
        """Fetch all tracked sessions that occurred on the specified date."""
        day_str = target_date.strftime("%Y-%m-%d")
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, app_name, window_title, project_tag, start_time, end_time
                FROM sessions
                WHERE substr(start_time, 1, 10) = ?
                ORDER BY start_time ASC
                """,
                (day_str,),
            )
            rows = cur.fetchall()
            return [
                SessionRecord(
                    id=row["id"],
                    app_name=row["app_name"],
                    window_title=row["window_title"] or "",
                    project_tag=row["project_tag"],
                    start_time=datetime.fromisoformat(row["start_time"]),
                    end_time=datetime.fromisoformat(row["end_time"]),
                )
                for row in rows
            ]

    # --- Note Operations ---

    def create_note(self, content: str, project_tag: Optional[str] = None) -> int:
        """Create a manual quick note."""
        now = datetime.now()
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notes (content, project_tag, created_at, is_completed)
                VALUES (?, ?, ?, 0)
                """,
                (content.strip(), project_tag, now.isoformat()),
            )
            return cur.lastrowid or 0

    def toggle_note_completed(self, note_id: int, is_completed: bool) -> bool:
        """Toggle the completion state of a note."""
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE notes SET is_completed = ? WHERE id = ?",
                (1 if is_completed else 0, note_id),
            )
            return cur.rowcount > 0

    def delete_note(self, note_id: int) -> bool:
        """Delete a note by ID."""
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return cur.rowcount > 0

    def get_notes_for_date(self, target_date: date) -> List[NoteRecord]:
        """Fetch all notes created on the specified date."""
        day_str = target_date.strftime("%Y-%m-%d")
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, project_tag, created_at, is_completed
                FROM notes
                WHERE substr(created_at, 1, 10) = ?
                ORDER BY created_at ASC
                """,
                (day_str,),
            )
            rows = cur.fetchall()
            return [
                NoteRecord(
                    id=row["id"],
                    content=row["content"],
                    project_tag=row["project_tag"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    is_completed=bool(row["is_completed"]),
                )
                for row in rows
            ]

    def get_all_open_notes(self) -> List[NoteRecord]:
        """Fetch all incomplete notes regardless of creation date."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, project_tag, created_at, is_completed
                FROM notes
                WHERE is_completed = 0
                ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()
            return [
                NoteRecord(
                    id=row["id"],
                    content=row["content"],
                    project_tag=row["project_tag"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    is_completed=False,
                )
                for row in rows
            ]

    # --- Task & Subtask Operations ---

    def create_task(self, title: str, project_tag: Optional[str] = None) -> int:
        """Create a new parent task."""
        now = datetime.now()
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tasks (title, project_tag, status, created_at)
                VALUES (?, ?, 'not_started', ?)
                """,
                (title.strip(), project_tag, now.isoformat()),
            )
            return cur.lastrowid or 0

    def update_task_status(self, task_id: int, status: str) -> bool:
        """Update status of a task ('not_started', 'in_progress', 'done')."""
        completed_at = datetime.now().isoformat() if status == "done" else None
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, completed_at, task_id),
            )
            return cur.rowcount > 0

    def update_task_project(self, task_id: int, project_tag: str) -> bool:
        """Update the project/section tag of a task."""
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET project_tag = ? WHERE id = ?",
                (project_tag.strip(), task_id),
            )
            return cur.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        """Delete a task and cascade its subtasks and logs."""
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cur.rowcount > 0

    def delete_subtask(self, subtask_id: int) -> bool:
        """Delete a subtask by ID."""
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
            return cur.rowcount > 0

    def create_subtask(self, task_id: int, title: str) -> int:
        """Create a subtask under a parent task."""
        now = datetime.now()
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO subtasks (task_id, title, status, created_at)
                VALUES (?, ?, 'not_started', ?)
                """,
                (task_id, title.strip(), now.isoformat()),
            )
            subtask_id = cur.lastrowid or 0

            # If task was not_started, optionally set to in_progress or leave as is
            return subtask_id

    def update_subtask_status(self, subtask_id: int, status: str) -> bool:
        """Update status of a subtask without modifying parent task status."""
        completed_at = datetime.now().isoformat() if status == "done" else None
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE subtasks
                SET status = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, completed_at, subtask_id),
            )
            return True

    def add_task_log(self, task_id: int, content: str, subtask_id: Optional[int] = None) -> int:
        """Add a timestamped running update/log entry to a task or subtask."""
        now = datetime.now()
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO task_logs (task_id, subtask_id, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, subtask_id, content.strip(), now.isoformat()),
            )
            return cur.lastrowid or 0

    def get_task_hierarchy(
        self,
        target_date: Optional[date] = None,
        status_filter: Optional[str] = None,
        include_completed: bool = True,
    ) -> List[TaskRecord]:
        """Fetch all tasks with their nested subtasks and log entries, with optional status filtering."""
        with self.db.cursor() as cur:
            query = "SELECT * FROM tasks WHERE 1=1 "
            params: list = []

            if target_date is not None:
                day_str = target_date.strftime("%Y-%m-%d")
                query += "AND substr(created_at, 1, 10) = ? "
                params.append(day_str)

            if status_filter:
                # Map friendly UI filter names to database status values
                status_map = {
                    "task": ["not_started", "to_do", "todo", "task"],
                    "to-do": ["not_started", "to_do", "todo", "task"],
                    "in progress": ["not_started", "to_do", "todo", "task", "in_progress", "pending"],
                    "in_progress": ["not_started", "to_do", "todo", "task", "in_progress", "pending"],
                    "pending": ["not_started", "to_do", "todo", "task", "in_progress", "pending"],
                    "completed": ["done", "completed"],
                    "done": ["done", "completed"],
                    "on hold": ["on_hold"],
                    "cancelled": ["cancelled", "canceled"],
                }
                valid_statuses = status_map.get(status_filter.lower(), [status_filter.lower()])
                placeholders = ",".join("?" for _ in valid_statuses)
                query += f"AND status IN ({placeholders}) "
                params.extend(valid_statuses)
            elif not include_completed:
                query += "AND status NOT IN ('done', 'completed', 'cancelled', 'canceled') "

            query += "ORDER BY created_at DESC"
            cur.execute(query, params)
            task_rows = cur.fetchall()

            tasks = []
            for t_row in task_rows:
                task_id = t_row["id"]

                # Fetch subtasks
                cur.execute(
                    "SELECT * FROM subtasks WHERE task_id = ? ORDER BY created_at ASC",
                    (task_id,),
                )
                subtask_rows = cur.fetchall()

                # Fetch task logs
                cur.execute(
                    "SELECT * FROM task_logs WHERE task_id = ? ORDER BY created_at ASC",
                    (task_id,),
                )
                log_rows = cur.fetchall()

                # Group logs by subtask_id
                parent_logs: List[TaskLogRecord] = []
                subtask_logs_map: Dict[int, List[TaskLogRecord]] = {}

                for l_row in log_rows:
                    log_obj = TaskLogRecord(
                        id=l_row["id"],
                        task_id=l_row["task_id"],
                        subtask_id=l_row["subtask_id"],
                        content=l_row["content"],
                        created_at=datetime.fromisoformat(l_row["created_at"]),
                    )
                    if l_row["subtask_id"] is None:
                        parent_logs.append(log_obj)
                    else:
                        subtask_logs_map.setdefault(l_row["subtask_id"], []).append(log_obj)

                subtasks: List[SubtaskRecord] = []
                for st_row in subtask_rows:
                    st_id = st_row["id"]
                    subtasks.append(
                        SubtaskRecord(
                            id=st_id,
                            task_id=task_id,
                            title=st_row["title"],
                            status=st_row["status"],
                            created_at=datetime.fromisoformat(st_row["created_at"]),
                            completed_at=datetime.fromisoformat(st_row["completed_at"]) if st_row["completed_at"] else None,
                            logs=subtask_logs_map.get(st_id, []),
                        )
                    )

                tasks.append(
                    TaskRecord(
                        id=task_id,
                        title=t_row["title"],
                        project_tag=t_row["project_tag"],
                        status=t_row["status"],
                        created_at=datetime.fromisoformat(t_row["created_at"]),
                        completed_at=datetime.fromisoformat(t_row["completed_at"]) if t_row["completed_at"] else None,
                        subtasks=subtasks,
                        task_logs=parent_logs,
                    )
                )

            return tasks

    # --- Project Keyword Mapping Operations ---

    def create_or_update_project(self, name: str, keywords: List[str]) -> int:
        """Create or update a project and its comma-separated keywords."""
        kw_str = ",".join([k.strip().lower() for k in keywords if k.strip()])
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO projects (name, keywords)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET keywords = excluded.keywords
                """,
                (name.strip(), kw_str),
            )
            return cur.lastrowid or 0

    def get_all_projects(self) -> List[ProjectRecord]:
        """Fetch all configured projects."""
        with self.db.cursor() as cur:
            cur.execute("SELECT id, name, keywords FROM projects ORDER BY name ASC")
            rows = cur.fetchall()
            return [
                ProjectRecord(
                    id=row["id"],
                    name=row["name"],
                    keywords=[k.strip() for k in row["keywords"].split(",") if k.strip()],
                )
                for row in rows
            ]

    def match_project_tag(self, text_to_match: str) -> Optional[str]:
        """Match window title or app name against project keywords."""
        if not text_to_match:
            return None
        text_lower = text_to_match.lower()
        projects = self.get_all_projects()
        for proj in projects:
            for kw in proj.keywords:
                if kw in text_lower:
                    return proj.name
        return None
