"""Data models and repository for SQLite storage in Wiz."""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
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
        self._projects_cache: Optional[List[ProjectRecord]] = None

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

    def create_note(
        self,
        content: str,
        project_tag: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> int:
        """Create a manual quick note."""
        now = created_at or datetime.now()
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

    def update_note_project(self, note_id: int, project_tag: str) -> bool:
        """Update the project/section tag of a quick note."""
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE notes SET project_tag = ? WHERE id = ?",
                (project_tag.strip(), note_id),
            )
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

    def update_task_status(self, task_id: int, status: str, completed_at: Optional[datetime] = None) -> bool:
        """Update status of a task ('not_started', 'in_progress', 'done', 'cancelled')."""
        if completed_at is not None:
            comp_str = completed_at.isoformat()
        else:
            comp_str = datetime.now().isoformat() if status in ("done", "completed", "cancelled", "canceled") else None
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, comp_str, task_id),
            )
            return cur.rowcount > 0

    def update_task_title(self, task_id: int, new_title: str) -> bool:
        """Update the title of a task."""
        title = new_title.strip()
        if not title:
            return False
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET title = ? WHERE id = ?",
                (title, task_id),
            )
            return cur.rowcount > 0

    def update_subtask_title(self, subtask_id: int, new_title: str) -> bool:
        """Update the title of a subtask."""
        title = new_title.strip()
        if not title:
            return False
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE subtasks SET title = ? WHERE id = ?",
                (title, subtask_id),
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
            return subtask_id

    add_subtask = create_subtask

    def update_subtask_status(self, subtask_id: int, status: str, completed_at: Optional[datetime] = None) -> bool:
        """Update status of a subtask without modifying parent task status."""
        if completed_at is not None:
            comp_str = completed_at.isoformat()
        else:
            comp_str = datetime.now().isoformat() if status in ("done", "completed", "cancelled", "canceled") else None
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE subtasks
                SET status = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, comp_str, subtask_id),
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
                filter_key = status_filter.strip().lower()
                if filter_key in ("task", "all"):
                    # Shows all tasks regardless of status
                    pass
                else:
                    # Map friendly UI filter names to database status values
                    status_map = {
                        "in progress": ["in_progress", "pending", "ongoing"],
                        "in_progress": ["in_progress", "pending", "ongoing"],
                        "ongoing": ["in_progress", "pending", "ongoing"],
                        "pending": ["in_progress", "pending", "ongoing"],
                        "completed": ["done", "completed"],
                        "done": ["done", "completed"],
                        "on hold": ["on_hold"],
                        "on_hold": ["on_hold"],
                        "cancelled": ["cancelled", "canceled"],
                        "canceled": ["cancelled", "canceled"],
                    }
                    valid_statuses = status_map.get(filter_key, [filter_key])
                    placeholders = ",".join("?" for _ in valid_statuses)
                    query += f"AND status IN ({placeholders}) "
                    params.extend(valid_statuses)
            elif not include_completed:
                query += "AND status NOT IN ('done', 'completed', 'cancelled', 'canceled') "

            query += "ORDER BY created_at DESC"
            cur.execute(query, params)
            task_rows = cur.fetchall()

            tasks = []
            if not task_rows:
                return tasks

            task_ids = [t_row["id"] for t_row in task_rows]
            placeholders = ",".join("?" for _ in task_ids)

            # Batch fetch all subtasks for matching tasks
            cur.execute(
                f"SELECT * FROM subtasks WHERE task_id IN ({placeholders}) ORDER BY created_at ASC",
                task_ids,
            )
            subtask_rows = cur.fetchall()

            # Batch fetch all logs for matching tasks
            cur.execute(
                f"SELECT * FROM task_logs WHERE task_id IN ({placeholders}) ORDER BY created_at ASC",
                task_ids,
            )
            log_rows = cur.fetchall()

            # Group logs by task_id and subtask_id
            parent_logs_map: Dict[int, List[TaskLogRecord]] = {}
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
                    parent_logs_map.setdefault(l_row["task_id"], []).append(log_obj)
                else:
                    subtask_logs_map.setdefault(l_row["subtask_id"], []).append(log_obj)

            # Group subtasks by task_id
            task_subtasks_map: Dict[int, List[SubtaskRecord]] = {}
            for st_row in subtask_rows:
                st_id = st_row["id"]
                t_id = st_row["task_id"]
                task_subtasks_map.setdefault(t_id, []).append(
                    SubtaskRecord(
                        id=st_id,
                        task_id=t_id,
                        title=st_row["title"],
                        status=st_row["status"],
                        created_at=datetime.fromisoformat(st_row["created_at"]),
                        completed_at=datetime.fromisoformat(st_row["completed_at"]) if st_row["completed_at"] else None,
                        logs=subtask_logs_map.get(st_id, []),
                    )
                )

            # Assemble TaskRecord list
            for t_row in task_rows:
                t_id = t_row["id"]
                tasks.append(
                    TaskRecord(
                        id=t_id,
                        title=t_row["title"],
                        project_tag=t_row["project_tag"],
                        status=t_row["status"],
                        created_at=datetime.fromisoformat(t_row["created_at"]),
                        completed_at=datetime.fromisoformat(t_row["completed_at"]) if t_row["completed_at"] else None,
                        subtasks=task_subtasks_map.get(t_id, []),
                        task_logs=parent_logs_map.get(t_id, []),
                    )
                )

            return tasks

    # --- Project Keyword Mapping Operations ---

    def create_or_update_project(self, name: str, keywords: List[str]) -> int:
        """Create or update a project and its comma-separated keywords."""
        self._projects_cache = None  # Invalidate in-memory cache
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

    def get_all_projects(self, force_refresh: bool = False) -> List[ProjectRecord]:
        """Fetch all configured projects with in-memory caching."""
        if self._projects_cache is not None and not force_refresh:
            return self._projects_cache

        with self.db.cursor() as cur:
            cur.execute("SELECT id, name, keywords FROM projects ORDER BY name ASC")
            rows = cur.fetchall()
            self._projects_cache = [
                ProjectRecord(
                    id=row["id"],
                    name=row["name"],
                    keywords=[k.strip() for k in row["keywords"].split(",") if k.strip()],
                )
                for row in rows
            ]
            return self._projects_cache

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

    # --- Timeline & Day Activity Operations ---

    def get_day_sessions(self, date_str: str) -> List[SessionRecord]:
        """Retrieve all tracked sessions starting on a given date (YYYY-MM-DD)."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, app_name, window_title, project_tag, start_time, end_time
                FROM sessions
                WHERE start_time LIKE ?
                ORDER BY start_time ASC
                """,
                (f"{date_str}%",),
            )
            rows = cur.fetchall()
            return [
                SessionRecord(
                    id=r["id"],
                    app_name=r["app_name"],
                    window_title=r["window_title"] or "",
                    project_tag=r["project_tag"],
                    start_time=datetime.fromisoformat(r["start_time"]),
                    end_time=datetime.fromisoformat(r["end_time"]),
                )
                for r in rows
            ]

    def get_day_completed_tasks(self, date_str: str) -> List[Dict[str, Any]]:
        """Retrieve all tasks and subtasks marked complete on a given date."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, project_tag, 'task' as item_type, NULL as parent_title, completed_at
                FROM tasks
                WHERE completed_at LIKE ?
                UNION ALL
                SELECT s.id, s.title, t.project_tag, 'subtask' as item_type, t.title as parent_title, s.completed_at
                FROM subtasks s
                JOIN tasks t ON s.task_id = t.id
                WHERE s.completed_at LIKE ?
                ORDER BY completed_at ASC
                """,
                (f"{date_str}%", f"{date_str}%"),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "project_tag": r["project_tag"],
                    "item_type": r["item_type"],
                    "parent_title": r["parent_title"],
                    "completed_at": datetime.fromisoformat(r["completed_at"]),
                }
                for r in rows
            ]

    def get_day_notes(self, date_str: str) -> List[NoteRecord]:
        """Retrieve all notes recorded on a given date."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, project_tag, created_at, is_completed
                FROM notes
                WHERE created_at LIKE ?
                ORDER BY created_at ASC
                """,
                (f"{date_str}%",),
            )
            rows = cur.fetchall()
            return [
                NoteRecord(
                    id=r["id"],
                    content=r["content"],
                    project_tag=r["project_tag"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    is_completed=bool(r["is_completed"]),
                )
                for r in rows
            ]

    def get_aggregated_day_sessions(self, date_str: str, max_gap_minutes: int = 5) -> List[Dict[str, Any]]:
        """Fetch and aggregate day sessions into contiguous blocks."""
        sessions = self.get_day_sessions(date_str)
        return aggregate_sessions(sessions, max_gap_minutes=max_gap_minutes)

    def get_day_timeline_events(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Produce a unified chronological list of activity events for a date.
        Combines aggregated app sessions, completed tasks, and notes.
        """
        raw_sessions = self.get_day_sessions(date_str)
        aggregated = aggregate_sessions(raw_sessions)
        completed_tasks = self.get_day_completed_tasks(date_str)
        day_notes = self.get_day_notes(date_str)

        events: List[Dict[str, Any]] = []

        for sess in aggregated:
            events.append({
                "event_type": "session",
                "timestamp": sess["start_time"],
                "end_timestamp": sess["end_time"],
                "duration_minutes": sess["duration_minutes"],
                "title": sess["app_name"],
                "subtitle": sess.get("window_title") or "",
                "project_tag": sess.get("project_tag"),
                "raw": sess,
            })

        for task in completed_tasks:
            parent_info = f"Parent: {task['parent_title']}" if task["parent_title"] else ""
            events.append({
                "event_type": "task",
                "timestamp": task["completed_at"],
                "end_timestamp": None,
                "duration_minutes": 0.0,
                "title": task["title"],
                "subtitle": parent_info,
                "project_tag": task["project_tag"],
                "item_type": task["item_type"],
                "raw": task,
            })

        for note in day_notes:
            events.append({
                "event_type": "note",
                "timestamp": note.created_at,
                "end_timestamp": None,
                "duration_minutes": 0.0,
                "title": note.content,
                "subtitle": "Quick Note",
                "project_tag": note.project_tag,
                "raw": note,
            })

        events.sort(key=lambda x: x["timestamp"])
        return events

    def get_day_metrics(self, date_str: str) -> Dict[str, Any]:
        """Calculate total tracked time and counts for the day."""
        raw_sessions = self.get_day_sessions(date_str)
        total_minutes = sum(s.duration_minutes for s in raw_sessions)
        completed_tasks = self.get_day_completed_tasks(date_str)
        day_notes = self.get_day_notes(date_str)
        unique_apps = len(set(s.app_name for s in raw_sessions))

        return {
            "total_tracked_minutes": round(total_minutes, 1),
            "completed_tasks_count": len(completed_tasks),
            "notes_count": len(day_notes),
            "unique_apps_count": unique_apps,
        }


def aggregate_sessions(sessions: List[SessionRecord], max_gap_minutes: int = 5) -> List[Dict[str, Any]]:
    """
    Merge adjacent sessions sharing the same app_name and project_tag in linear O(N) time.
    Sessions must be sorted by start_time.
    """
    if not sessions:
        return []

    merged: List[Dict[str, Any]] = []
    current_block: Optional[Dict[str, Any]] = None

    for session in sessions:
        if current_block is None:
            current_block = {
                "app_name": session.app_name,
                "project_tag": session.project_tag,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "window_title": session.window_title,
                "session_count": 1,
            }
            continue

        same_app = (session.app_name.lower() == current_block["app_name"].lower())
        same_proj = (session.project_tag == current_block["project_tag"])
        gap_minutes = (session.start_time - current_block["end_time"]).total_seconds() / 60.0

        if same_app and same_proj and gap_minutes <= max_gap_minutes:
            current_block["end_time"] = max(current_block["end_time"], session.end_time)
            current_block["session_count"] += 1
            if session.window_title and session.window_title != current_block["window_title"]:
                current_block["window_title"] = session.window_title
        else:
            diff_secs = (current_block["end_time"] - current_block["start_time"]).total_seconds()
            current_block["duration_minutes"] = max(1.0, round(diff_secs / 60.0, 1))
            merged.append(current_block)
            current_block = {
                "app_name": session.app_name,
                "project_tag": session.project_tag,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "window_title": session.window_title,
                "session_count": 1,
            }

    if current_block is not None:
        diff_secs = (current_block["end_time"] - current_block["start_time"]).total_seconds()
        current_block["duration_minutes"] = max(1.0, round(diff_secs / 60.0, 1))
        merged.append(current_block)

    return merged

