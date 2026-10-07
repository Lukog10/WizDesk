"""Data models and repository for SQLite storage in Wiz."""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from wiz.core.config import config
from wiz.storage.db import Database, get_db
from wiz.utils.sanitizer import sanitize_window_title, is_system_excluded


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
class TagRecord:
    """Represents a user-defined category tag with an icon and accent color."""
    id: Optional[int]
    name: str
    icon: str = "tag"
    color: str = "#3B82F6"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class NoteRecord:
    """Represents a permanent or quick work note."""
    id: Optional[int]
    content: str
    project_tag: Optional[str]
    created_at: datetime
    is_completed: bool = False
    title: str = ""
    updated_at: Optional[datetime] = None
    is_pinned: bool = False
    tags: List[TagRecord] = field(default_factory=list)


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
    status: str = "not_started"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: int = 0
    timer_started_at: Optional[datetime] = None
    logs: List[TaskLogRecord] = field(default_factory=list)


@dataclass
class TaskRecord:
    """Represents a parent task with nested subtasks."""
    id: Optional[int]
    title: str
    project_tag: Optional[str]
    status: str = "not_started"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    scheduled_date: Optional[str] = None
    repeat_mode: str = "none"
    last_completed_date: Optional[str] = None
    duration_seconds: int = 0
    timer_started_at: Optional[datetime] = None
    subtasks: List[SubtaskRecord] = field(default_factory=list)
    task_logs: List[TaskLogRecord] = field(default_factory=list)
    tags: List[TagRecord] = field(default_factory=list)

    @property
    def is_timer_running(self) -> bool:
        """Returns True if the active stopwatch is currently ticking."""
        return self.timer_started_at is not None

    @property
    def total_elapsed_seconds(self) -> int:
        """Calculate total verified work seconds including current running session."""
        if self.timer_started_at:
            delta = int((datetime.now() - self.timer_started_at).total_seconds())
            return self.duration_seconds + max(0, delta)
        return self.duration_seconds

    @property
    def is_recurring(self) -> bool:
        """Returns True if the task has an active recurring schedule."""
        return bool(self.repeat_mode and self.repeat_mode != "none")

    @property
    def effective_date_str(self) -> str:
        """Return scheduled_date if set, else creation date (YYYY-MM-DD)."""
        if self.scheduled_date:
            return self.scheduled_date
        return self.created_at.strftime("%Y-%m-%d")

    @property
    def is_overdue(self) -> bool:
        """Returns True if the task has an effective date earlier than today and is not completed."""
        if self.status in ("done", "completed", "cancelled", "canceled"):
            return False
        today_str = date.today().strftime("%Y-%m-%d")
        return self.effective_date_str < today_str


@dataclass
class ProjectRecord:
    """Represents project keyword matching configuration."""
    id: Optional[int]
    name: str
    keywords: List[str]  # e.g. ["turfline", "booking"]
    color: str = "#FF6B3D"
    description: str = ""


DEFAULT_PROJECT_PALETTE: List[str] = [
    "#FF6B3D",  # Mascot Orange-Red (Brand)
    "#10B981",  # Emerald
    "#3B82F6",  # Electric Blue
    "#8B5CF6",  # Violet
    "#F59E0B",  # Amber Gold
    "#EC4899",  # Hot Pink
    "#06B6D4",  # Cyan
    "#14B8A6",  # Teal
    "#F97316",  # Tangerine
    "#84CC16",  # Lime Green
    "#6366F1",  # Indigo
    "#F43F5E",  # Rose
    "#0EA5E9",  # Sky Blue
    "#D946EF",  # Fuchsia
    "#EAB308",  # Sunburst Yellow
    "#2563EB",  # Cobalt Blue
    "#FF5722",  # Flame Orange
    "#059669",  # Forest Jade
]


class StorageRepository:
    """High-level repository for database CRUD operations."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()
        self._projects_cache: Optional[List[ProjectRecord]] = None
        self.heal_duplicate_projects()

    def close(self) -> None:
        """Close underlying database connection and release resources."""
        if self.db is not None:
            self.db.close()

    def heal_duplicate_projects(self) -> None:
        """Self-healing migration: resolve known duplicate projects and duplicate colors."""
        try:
            with self.db.cursor() as cur:
                # 1. Merge duplicate Research -> Browsing if both exist
                cur.execute("SELECT id FROM projects WHERE name = 'Research'")
                has_res = cur.fetchone()
                cur.execute("SELECT id FROM projects WHERE name = 'Browsing'")
                has_brw = cur.fetchone()
                if has_res and has_brw:
                    self.rename_project("Research", "Browsing")

                # 2. De-duplicate project colors in DB if any collide
                cur.execute("SELECT id, name, color FROM projects ORDER BY id ASC")
                rows = cur.fetchall()
                used_colors: set[str] = set()
                palette_idx = 0
                for r in rows:
                    col = (r["color"] or "").strip().upper()
                    if not col or col in used_colors:
                        while palette_idx < len(DEFAULT_PROJECT_PALETTE) and DEFAULT_PROJECT_PALETTE[palette_idx].upper() in used_colors:
                            palette_idx += 1
                        new_col = DEFAULT_PROJECT_PALETTE[palette_idx] if palette_idx < len(DEFAULT_PROJECT_PALETTE) else DEFAULT_PROJECT_PALETTE[len(used_colors) % len(DEFAULT_PROJECT_PALETTE)]
                        cur.execute("UPDATE projects SET color = ? WHERE id = ?", (new_col, r["id"]))
                        used_colors.add(new_col.upper())
                    else:
                        used_colors.add(col)
            self._projects_cache = None
        except Exception:
            pass

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
        if is_system_excluded(app_name, window_title):
            return 0

        if config.get("sanitize_tracked_titles", True):
            clean_title = sanitize_window_title(window_title, app_name)
        else:
            clean_title = window_title

        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (app_name, window_title, project_tag, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    app_name,
                    clean_title,
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

    # Tag Operations

    def create_tag(self, name: str, icon: str = "tag", color: str = "#3B82F6") -> TagRecord:
        """Create a user-defined category tag."""
        clean_name = name.strip()
        clean_icon = icon.strip().lower() or "tag"
        clean_color = color.strip() or "#3B82F6"
        now = datetime.now()
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tags (name, icon, color, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (clean_name, clean_icon, clean_color, now.isoformat()),
            )
            tag_id = cur.lastrowid or 0
            return TagRecord(
                id=tag_id,
                name=clean_name,
                icon=clean_icon,
                color=clean_color,
                created_at=now,
            )

    def get_all_tags(self) -> List[TagRecord]:
        """Fetch all user tags ordered alphabetically."""
        with self.db.cursor() as cur:
            cur.execute("SELECT id, name, icon, color, created_at FROM tags ORDER BY name ASC")
            rows = cur.fetchall()
            return [
                TagRecord(
                    id=r["id"],
                    name=r["name"],
                    icon=r["icon"] or "tag",
                    color=r["color"] or "#3B82F6",
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]

    def get_tag_by_id(self, tag_id: int) -> Optional[TagRecord]:
        """Fetch a tag by primary ID."""
        with self.db.cursor() as cur:
            cur.execute("SELECT id, name, icon, color, created_at FROM tags WHERE id = ?", (tag_id,))
            r = cur.fetchone()
            if not r:
                return None
            return TagRecord(
                id=r["id"],
                name=r["name"],
                icon=r["icon"] or "tag",
                color=r["color"] or "#3B82F6",
                created_at=datetime.fromisoformat(r["created_at"]),
            )

    def get_tag_by_name(self, name: str) -> Optional[TagRecord]:
        """Fetch a tag by exact name (case-insensitive)."""
        with self.db.cursor() as cur:
            cur.execute("SELECT id, name, icon, color, created_at FROM tags WHERE LOWER(name) = LOWER(?)", (name.strip(),))
            r = cur.fetchone()
            if not r:
                return None
            return TagRecord(
                id=r["id"],
                name=r["name"],
                icon=r["icon"] or "tag",
                color=r["color"] or "#3B82F6",
                created_at=datetime.fromisoformat(r["created_at"]),
            )

    def update_tag(self, tag_id: int, name: str, icon: str, color: str) -> bool:
        """Update a tag's name, icon, and accent color."""
        clean_name = name.strip()
        clean_icon = icon.strip().lower() or "tag"
        clean_color = color.strip() or "#3B82F6"
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE tags SET name = ?, icon = ?, color = ? WHERE id = ?",
                (clean_name, clean_icon, clean_color, tag_id),
            )
            return cur.rowcount > 0

    def delete_tag(self, tag_id: int) -> bool:
        """Delete a tag and cascade remove its associations from tasks and notes."""
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            return cur.rowcount > 0

    def get_tags_for_task(self, task_id: int) -> List[TagRecord]:
        """Fetch all tags linked to a task."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, t.name, t.icon, t.color, t.created_at
                FROM task_tags tt
                JOIN tags t ON tt.tag_id = t.id
                WHERE tt.task_id = ?
                ORDER BY t.name ASC
                """,
                (task_id,),
            )
            rows = cur.fetchall()
            return [
                TagRecord(
                    id=r["id"],
                    name=r["name"],
                    icon=r["icon"] or "tag",
                    color=r["color"] or "#3B82F6",
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]

    def set_task_tags(self, task_id: int, tag_ids: List[int]) -> bool:
        """Replace all tags assigned to a task."""
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM task_tags WHERE task_id = ?", (task_id,))
            for tid in tag_ids:
                cur.execute(
                    "INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)",
                    (task_id, tid),
                )
            return True

    def add_task_tag(self, task_id: int, tag_id: int) -> bool:
        """Add a single tag to a task if not already present."""
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)",
                (task_id, tag_id),
            )
            return cur.rowcount > 0

    def remove_task_tag(self, task_id: int, tag_id: int) -> bool:
        """Remove a tag from a task."""
        with self.db.cursor() as cur:
            cur.execute(
                "DELETE FROM task_tags WHERE task_id = ? AND tag_id = ?",
                (task_id, tag_id),
            )
            return cur.rowcount > 0

    def get_tags_for_note(self, note_id: int) -> List[TagRecord]:
        """Fetch all tags linked to a note."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, t.name, t.icon, t.color, t.created_at
                FROM note_tags nt
                JOIN tags t ON nt.tag_id = t.id
                WHERE nt.note_id = ?
                ORDER BY t.name ASC
                """,
                (note_id,),
            )
            rows = cur.fetchall()
            return [
                TagRecord(
                    id=r["id"],
                    name=r["name"],
                    icon=r["icon"] or "tag",
                    color=r["color"] or "#3B82F6",
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]

    def set_note_tags(self, note_id: int, tag_ids: List[int]) -> bool:
        """Replace all tags assigned to a note."""
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
            for tid in tag_ids:
                cur.execute(
                    "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                    (note_id, tid),
                )
            return True

    # Note Operations

    def create_note(
        self,
        content: str,
        project_tag: Optional[str] = None,
        created_at: Optional[datetime] = None,
        title: str = "",
        tag_ids: Optional[List[int]] = None,
        is_pinned: bool = False,
    ) -> int:
        """Create a permanent or quick work note."""
        now = created_at or datetime.now()
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notes (title, content, project_tag, created_at, updated_at, is_completed, is_pinned)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (title.strip(), content.strip(), project_tag, now.isoformat(), now.isoformat(), 1 if is_pinned else 0),
            )
            note_id = cur.lastrowid or 0
            if tag_ids:
                for tid in tag_ids:
                    cur.execute(
                        "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                        (note_id, tid),
                    )
            return note_id

    def update_note(
        self,
        note_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        project_tag: Optional[str] = None,
        is_pinned: Optional[bool] = None,
        tag_ids: Optional[List[int]] = None,
    ) -> bool:
        """Update an existing note's fields and tags."""
        now_str = datetime.now().isoformat()
        updates = ["updated_at = ?"]
        params: list = [now_str]

        if title is not None:
            updates.append("title = ?")
            params.append(title.strip())
        if content is not None:
            updates.append("content = ?")
            params.append(content.strip())
        if project_tag is not None:
            updates.append("project_tag = ?")
            clean_proj = project_tag.strip() if project_tag and project_tag != "None" else None
            params.append(clean_proj)
        if is_pinned is not None:
            updates.append("is_pinned = ?")
            params.append(1 if is_pinned else 0)

        params.append(note_id)
        with self.db.cursor() as cur:
            cur.execute(f"UPDATE notes SET {', '.join(updates)} WHERE id = ?", params)
            if tag_ids is not None:
                cur.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
                for tid in tag_ids:
                    cur.execute(
                        "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                        (note_id, tid),
                    )
            return cur.rowcount > 0

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

    def update_note_project(self, note_id: int, project_tag: Optional[str]) -> bool:
        """Update the project/section tag of a quick note."""
        clean_proj = project_tag.strip() if project_tag and project_tag != "None" else None
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE notes SET project_tag = ? WHERE id = ?",
                (clean_proj, note_id),
            )
            return cur.rowcount > 0

    def get_notes_for_date(self, target_date: date) -> List[NoteRecord]:
        """Fetch all notes created on the specified date."""
        day_str = target_date.strftime("%Y-%m-%d")
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, content, project_tag, created_at, updated_at, is_completed, is_pinned
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
                    title=row["title"] if "title" in row.keys() and row["title"] else "",
                    updated_at=datetime.fromisoformat(row["updated_at"]) if ("updated_at" in row.keys() and row["updated_at"]) else datetime.fromisoformat(row["created_at"]),
                    is_pinned=bool(row["is_pinned"]) if "is_pinned" in row.keys() else False,
                )
                for row in rows
            ]

    def get_all_open_notes(self) -> List[NoteRecord]:
        """Fetch all incomplete notes regardless of creation date."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, content, project_tag, created_at, updated_at, is_completed, is_pinned
                FROM notes
                WHERE is_completed = 0
                ORDER BY is_pinned DESC, updated_at DESC, created_at DESC
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
                    title=row["title"] if "title" in row.keys() and row["title"] else "",
                    updated_at=datetime.fromisoformat(row["updated_at"]) if ("updated_at" in row.keys() and row["updated_at"]) else datetime.fromisoformat(row["created_at"]),
                    is_pinned=bool(row["is_pinned"]) if "is_pinned" in row.keys() else False,
                )
                for row in rows
            ]

    def get_notes(
        self,
        project_tag: Optional[str] = None,
        tag_id: Optional[int] = None,
        include_completed: bool = True,
    ) -> List[NoteRecord]:
        """Fetch notes with optional project and tag filtering."""
        with self.db.cursor() as cur:
            query = "SELECT * FROM notes WHERE 1=1 "
            params: list = []
            if project_tag:
                query += "AND project_tag = ? "
                params.append(project_tag)
            if tag_id is not None:
                query += "AND id IN (SELECT note_id FROM note_tags WHERE tag_id = ?) "
                params.append(tag_id)
            if not include_completed:
                query += "AND is_completed = 0 "
            query += "ORDER BY is_pinned DESC, updated_at DESC, created_at DESC"
            cur.execute(query, params)
            rows = cur.fetchall()

            notes: List[NoteRecord] = []
            if not rows:
                return notes

            note_ids = [r["id"] for r in rows]
            placeholders = ",".join("?" for _ in note_ids)
            cur.execute(
                f"""
                SELECT nt.note_id, t.id, t.name, t.icon, t.color, t.created_at
                FROM note_tags nt
                JOIN tags t ON nt.tag_id = t.id
                WHERE nt.note_id IN ({placeholders})
                ORDER BY t.name ASC
                """,
                note_ids,
            )
            tag_rows = cur.fetchall()
            note_tags_map: Dict[int, List[TagRecord]] = {}
            for tr in tag_rows:
                note_tags_map.setdefault(tr["note_id"], []).append(
                    TagRecord(
                        id=tr["id"],
                        name=tr["name"],
                        icon=tr["icon"] or "tag",
                        color=tr["color"] or "#3B82F6",
                        created_at=datetime.fromisoformat(tr["created_at"]),
                    )
                )

            for r in rows:
                notes.append(
                    NoteRecord(
                        id=r["id"],
                        content=r["content"],
                        project_tag=r["project_tag"],
                        created_at=datetime.fromisoformat(r["created_at"]),
                        is_completed=bool(r["is_completed"]),
                        title=r["title"] if "title" in r.keys() and r["title"] else "",
                        updated_at=datetime.fromisoformat(r["updated_at"]) if ("updated_at" in r.keys() and r["updated_at"]) else datetime.fromisoformat(r["created_at"]),
                        is_pinned=bool(r["is_pinned"]) if "is_pinned" in r.keys() else False,
                        tags=note_tags_map.get(r["id"], []),
                    )
                )
            return notes

    def create_permanent_note(
        self,
        title: str,
        content: str = "",
        project_tag: Optional[str] = None,
        tag_ids: Optional[List[int]] = None,
        is_pinned: bool = False,
    ) -> int:
        """Create a permanent titled note with optional content, project tag, and tags."""
        return self.create_note(
            content=content,
            project_tag=project_tag,
            title=title,
            tag_ids=tag_ids,
            is_pinned=is_pinned,
        )

    def get_permanent_notes(
        self,
        project_tag: Optional[str] = None,
        tag_id: Optional[int] = None,
    ) -> List[NoteRecord]:
        """Fetch all permanent notes ordered by pinned state, updated date, and creation date."""
        return self.get_notes(project_tag=project_tag, tag_id=tag_id, include_completed=True)

    def update_permanent_note(
        self,
        note_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        project_tag: Optional[str] = None,
        tag_ids: Optional[List[int]] = None,
        is_pinned: Optional[bool] = None,
    ) -> bool:
        """Update title, content, project tag, tags, or pinned status of a permanent note."""
        return self.update_note(
            note_id=note_id,
            title=title,
            content=content,
            project_tag=project_tag,
            is_pinned=is_pinned,
            tag_ids=tag_ids,
        )

    def delete_permanent_note(self, note_id: int) -> bool:
        """Delete a permanent note by ID."""
        return self.delete_note(note_id)

    # Task & Subtask Operations

    def create_task(
        self,
        title: str,
        project_tag: Optional[str] = None,
        scheduled_date: Optional[str] = None,
        repeat_mode: str = "none",
        tag_ids: Optional[List[int]] = None,
    ) -> int:
        """Create a new parent task with optional scheduled date, repeat mode, and tags."""
        now = datetime.now()
        mode = repeat_mode.strip().lower() if repeat_mode else "none"
        if mode not in ("none", "daily", "weekdays", "weekends"):
            mode = "none"
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tasks (title, project_tag, status, created_at, scheduled_date, repeat_mode, duration_seconds, timer_started_at)
                VALUES (?, ?, 'not_started', ?, ?, ?, 0, NULL)
                """,
                (title.strip(), project_tag, now.isoformat(), scheduled_date or None, mode),
            )
            task_id = cur.lastrowid or 0
            if tag_ids:
                for tid in tag_ids:
                    cur.execute(
                        "INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)",
                        (task_id, tid),
                    )
            return task_id

    def update_task_status(self, task_id: int, status: str, completed_at: Optional[datetime] = None) -> bool:
        """Update status of a task ('not_started', 'in_progress', 'done', 'cancelled')."""
        is_done = status in ("done", "completed", "cancelled", "canceled")
        if completed_at is not None:
            comp_str = completed_at.isoformat()
        else:
            comp_str = datetime.now().isoformat() if is_done else None
        today_str = date.today().strftime("%Y-%m-%d") if is_done else None
        with self.db.cursor() as cur:
            cur.execute("SELECT duration_seconds, timer_started_at FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            dur = row["duration_seconds"] if row and "duration_seconds" in row.keys() else 0
            started = row["timer_started_at"] if row and "timer_started_at" in row.keys() else None

            new_dur = dur
            new_started = started
            if is_done and started:
                delta = int((datetime.now() - datetime.fromisoformat(started)).total_seconds())
                new_dur = dur + max(0, delta)
                new_started = None

            if is_done:
                cur.execute(
                    """
                    UPDATE tasks
                    SET status = ?, completed_at = ?, last_completed_date = ?, duration_seconds = ?, timer_started_at = ?
                    WHERE id = ?
                    """,
                    (status, comp_str, today_str, new_dur, new_started, task_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE tasks
                    SET status = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (status, comp_str, task_id),
                )
            return cur.rowcount > 0

    def start_task_stopwatch(self, task_id: int) -> bool:
        """Start the live stopwatch for a task, setting status to in_progress."""
        now_iso = datetime.now().isoformat()
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET status = 'in_progress', timer_started_at = ?
                WHERE id = ?
                """,
                (now_iso, task_id),
            )
            return cur.rowcount > 0

    def pause_task_stopwatch(self, task_id: int) -> bool:
        """Pause running stopwatch and commit elapsed seconds to cumulative duration."""
        with self.db.cursor() as cur:
            cur.execute("SELECT duration_seconds, timer_started_at FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            if not row or not row["timer_started_at"]:
                return False
            dur = row["duration_seconds"] or 0
            started = datetime.fromisoformat(row["timer_started_at"])
            delta = int((datetime.now() - started).total_seconds())
            new_dur = dur + max(0, delta)
            cur.execute(
                "UPDATE tasks SET duration_seconds = ?, timer_started_at = NULL WHERE id = ?",
                (new_dur, task_id),
            )
            return cur.rowcount > 0

    def complete_task_stopwatch(self, task_id: int) -> bool:
        """Flush running session into duration_seconds, clear timer_started_at, and mark task done."""
        return self.update_task_status(task_id, "done")

    def update_task_duration(
        self,
        task_id: int,
        duration_seconds: int,
        timer_started_at: Optional[datetime] = None,
    ) -> bool:
        """Manually update duration_seconds and optional timer_started_at for a task."""
        started_str = timer_started_at.isoformat() if timer_started_at else None
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET duration_seconds = ?, timer_started_at = ? WHERE id = ?",
                (duration_seconds, started_str, task_id),
            )
            return cur.rowcount > 0

    def flush_all_running_stopwatches(self) -> int:
        """Commit all currently ticking tasks to database duration_seconds and set timer_started_at to NULL."""
        with self.db.cursor() as cur:
            cur.execute("SELECT id, duration_seconds, timer_started_at FROM tasks WHERE timer_started_at IS NOT NULL")
            rows = cur.fetchall()
            now = datetime.now()
            count = 0
            for r in rows:
                tid = r["id"]
                dur = r["duration_seconds"] or 0
                started = datetime.fromisoformat(r["timer_started_at"])
                delta = int((now - started).total_seconds())
                new_dur = dur + max(0, delta)
                cur.execute(
                    "UPDATE tasks SET duration_seconds = ?, timer_started_at = NULL WHERE id = ?",
                    (new_dur, tid),
                )
                count += 1
            return count

    def update_task_schedule(
        self,
        task_id: int,
        scheduled_date: Optional[str] = None,
        repeat_mode: Optional[str] = None,
    ) -> bool:
        """Update scheduled_date and/or repeat_mode for an existing task."""
        if scheduled_date is None and repeat_mode is None:
            return False

        val = None
        if scheduled_date is not None:
            val = None if (scheduled_date == "" or scheduled_date.strip().lower() == "clear") else scheduled_date.strip()

        mode = None
        if repeat_mode is not None:
            mode = repeat_mode.strip().lower()
            if mode not in ("none", "daily", "weekdays", "weekends"):
                mode = "none"

        with self.db.cursor() as cur:
            if scheduled_date is not None and repeat_mode is not None:
                cur.execute(
                    "UPDATE tasks SET scheduled_date = ?, repeat_mode = ? WHERE id = ?",
                    (val, mode, task_id),
                )
            elif scheduled_date is not None:
                cur.execute(
                    "UPDATE tasks SET scheduled_date = ? WHERE id = ?",
                    (val, task_id),
                )
            elif repeat_mode is not None:
                cur.execute(
                    "UPDATE tasks SET repeat_mode = ? WHERE id = ?",
                    (mode, task_id),
                )
            return cur.rowcount > 0

    def roll_recurring_tasks(self, today: Optional[date] = None) -> int:
        """
        Advance recurring tasks to today if a new day has arrived.
        - If completed before today, resets status to 'not_started' and resets subtasks.
        - If scheduled_date is in the past, advances scheduled_date to today (or next matching day).
        """
        current_day = today or date.today()
        today_str = current_day.strftime("%Y-%m-%d")
        updated_count = 0

        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, repeat_mode, scheduled_date, status, last_completed_date
                FROM tasks
                WHERE repeat_mode IS NOT NULL AND repeat_mode != 'none'
                """
            )
            recurring_tasks = cur.fetchall()

            for row in recurring_tasks:
                task_id = row["id"]
                repeat_mode = row["repeat_mode"]
                last_comp = row["last_completed_date"]
                sched = row["scheduled_date"]
                status = row["status"]

                needs_status_reset = False
                needs_sched_advance = False

                if status in ("done", "completed") and last_comp and last_comp < today_str:
                    needs_status_reset = True

                if sched and sched < today_str:
                    needs_sched_advance = True

                if needs_status_reset or needs_sched_advance:
                    new_status = "not_started" if needs_status_reset else status
                    new_sched = sched
                    if needs_sched_advance or (sched and needs_status_reset):
                        check_day = current_day
                        for _ in range(7):
                            wd = check_day.weekday()  # 0=Mon, 6=Sun
                            if repeat_mode == "daily":
                                break
                            elif repeat_mode == "weekdays" and wd < 5:
                                break
                            elif repeat_mode == "weekends" and wd >= 5:
                                break
                            check_day += timedelta(days=1)
                        new_sched = check_day.strftime("%Y-%m-%d")

                    cur.execute(
                        """
                        UPDATE tasks
                        SET status = ?,
                            completed_at = CASE WHEN ? = 'not_started' THEN NULL ELSE completed_at END,
                            scheduled_date = ?
                        WHERE id = ?
                        """,
                        (new_status, new_status, new_sched, task_id),
                    )

                    if needs_status_reset:
                        cur.execute(
                            """
                            UPDATE subtasks
                            SET status = 'not_started', completed_at = NULL
                            WHERE task_id = ?
                            """,
                            (task_id,),
                        )
                    updated_count += 1

        return updated_count

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

    def update_task_project(self, task_id: int, project_tag: Optional[str]) -> bool:
        """Update the project/section tag of a task."""
        clean_proj = project_tag.strip() if project_tag and project_tag != "None" else None
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET project_tag = ? WHERE id = ?",
                (clean_proj, task_id),
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
        project_tag: Optional[str] = None,
        tag_id: Optional[int] = None,
    ) -> List[TaskRecord]:
        """Fetch all tasks with their nested subtasks and log entries, with optional status, schedule, project, and tag filtering."""
        with self.db.cursor() as cur:
            query = "SELECT * FROM tasks WHERE 1=1 "
            params: list = []
            today_str = date.today().strftime("%Y-%m-%d")

            if project_tag is not None:
                query += "AND project_tag = ? "
                params.append(project_tag)

            if tag_id is not None:
                query += "AND id IN (SELECT task_id FROM task_tags WHERE tag_id = ?) "
                params.append(tag_id)

            filter_key = status_filter.strip().lower() if status_filter else None

            # Special views: upcoming and unfinished
            if filter_key == "upcoming":
                # Tasks scheduled for future dates that are not finished
                query += "AND scheduled_date IS NOT NULL AND scheduled_date > ? "
                params.append(today_str)
                query += "AND status NOT IN ('done', 'completed', 'cancelled', 'canceled') "
                query += "ORDER BY scheduled_date ASC, created_at ASC"
            elif filter_key == "unfinished":
                # Overdue tasks (scheduled or created before today) that are not finished
                query += "AND COALESCE(scheduled_date, substr(created_at, 1, 10)) < ? "
                params.append(today_str)
                query += "AND status NOT IN ('done', 'completed', 'cancelled', 'canceled') "
                query += "ORDER BY COALESCE(scheduled_date, substr(created_at, 1, 10)) ASC, created_at ASC"
            else:
                # Normal target date and status filtering
                if target_date is not None:
                    day_str = target_date.strftime("%Y-%m-%d")
                    wd = target_date.weekday()
                    if wd < 5:
                        valid_repeat = "('daily', 'weekdays')"
                    else:
                        valid_repeat = "('daily', 'weekends')"

                    query += f"""AND (
                        ( (repeat_mode IS NULL OR repeat_mode = 'none') AND COALESCE(scheduled_date, substr(created_at, 1, 10)) = ? )
                        OR
                        ( repeat_mode IN {valid_repeat} AND COALESCE(scheduled_date, substr(created_at, 1, 10)) <= ? )
                    ) """
                    params.extend([day_str, day_str])

                if filter_key:
                    if filter_key in ("task", "all"):
                        pass
                    else:
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

            # Batch fetch all tags for matching tasks
            cur.execute(
                f"""
                SELECT tt.task_id, t.id, t.name, t.icon, t.color, t.created_at
                FROM task_tags tt
                JOIN tags t ON tt.tag_id = t.id
                WHERE tt.task_id IN ({placeholders})
                ORDER BY t.name ASC
                """,
                task_ids,
            )
            tag_rows = cur.fetchall()
            task_tags_map: Dict[int, List[TagRecord]] = {}
            for tr in tag_rows:
                task_tags_map.setdefault(tr["task_id"], []).append(
                    TagRecord(
                        id=tr["id"],
                        name=tr["name"],
                        icon=tr["icon"] or "tag",
                        color=tr["color"] or "#3B82F6",
                        created_at=datetime.fromisoformat(tr["created_at"]),
                    )
                )

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
                st_dur = st_row["duration_seconds"] if ("duration_seconds" in st_row.keys() and st_row["duration_seconds"]) else 0
                st_start = datetime.fromisoformat(st_row["timer_started_at"]) if ("timer_started_at" in st_row.keys() and st_row["timer_started_at"]) else None
                task_subtasks_map.setdefault(t_id, []).append(
                    SubtaskRecord(
                        id=st_id,
                        task_id=t_id,
                        title=st_row["title"],
                        status=st_row["status"],
                        created_at=datetime.fromisoformat(st_row["created_at"]),
                        completed_at=datetime.fromisoformat(st_row["completed_at"]) if st_row["completed_at"] else None,
                        duration_seconds=st_dur,
                        timer_started_at=st_start,
                        logs=subtask_logs_map.get(st_id, []),
                    )
                )

            # Assemble TaskRecord list
            for t_row in task_rows:
                t_id = t_row["id"]
                sched = t_row["scheduled_date"] if "scheduled_date" in t_row.keys() else None
                rep = t_row["repeat_mode"] if "repeat_mode" in t_row.keys() and t_row["repeat_mode"] else "none"
                last_c = t_row["last_completed_date"] if "last_completed_date" in t_row.keys() else None
                dur_sec = t_row["duration_seconds"] if ("duration_seconds" in t_row.keys() and t_row["duration_seconds"]) else 0
                tim_start = datetime.fromisoformat(t_row["timer_started_at"]) if ("timer_started_at" in t_row.keys() and t_row["timer_started_at"]) else None
                tasks.append(
                    TaskRecord(
                        id=t_id,
                        title=t_row["title"],
                        project_tag=t_row["project_tag"],
                        status=t_row["status"],
                        created_at=datetime.fromisoformat(t_row["created_at"]),
                        completed_at=datetime.fromisoformat(t_row["completed_at"]) if t_row["completed_at"] else None,
                        scheduled_date=sched,
                        repeat_mode=rep,
                        last_completed_date=last_c,
                        duration_seconds=dur_sec,
                        timer_started_at=tim_start,
                        subtasks=task_subtasks_map.get(t_id, []),
                        task_logs=parent_logs_map.get(t_id, []),
                        tags=task_tags_map.get(t_id, []),
                    )
                )

            return tasks

    def get_scheduled_summary_for_month(self, year: int, month: int) -> Dict[str, str]:
        """Return a mapping of 'YYYY-MM-DD' -> 'active' | 'completed' for dates in the month.
        
        If a day has at least one active (not done/completed/cancelled) task, it is marked 'active'.
        If all tasks for that day are completed, it is marked 'completed'.
        """
        month_prefix = f"{year:04d}-{month:02d}%"
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT scheduled_date, status
                FROM tasks
                WHERE scheduled_date LIKE ?
                ORDER BY scheduled_date ASC
                """,
                (month_prefix,),
            )
            rows = cur.fetchall()
            date_status: Dict[str, str] = {}
            for r in rows:
                dt = r["scheduled_date"]
                if not dt:
                    continue
                st = (r["status"] or "not_started").lower()
                if dt not in date_status:
                    date_status[dt] = "completed" if st in ("done", "completed") else "active"
                else:
                    if st not in ("done", "completed", "cancelled", "canceled"):
                        date_status[dt] = "active"
            return date_status

    # --- Project Keyword Mapping Operations ---

    def create_or_update_project(
        self,
        name: str,
        keywords: List[str],
        color: Optional[str] = None,
        description: str = "",
    ) -> int:
        """Create or update a project and its comma-separated keywords, color, and description."""
        self._projects_cache = None  # Invalidate in-memory cache
        name_clean = name.strip()
        kw_str = ",".join([k.strip().lower() for k in keywords if k.strip()])
        with self.db.cursor() as cur:
            cur.execute("SELECT color FROM projects WHERE name = ?", (name_clean,))
            existing = cur.fetchone()

            final_color = color.strip() if (color and color.strip()) else None
            if not final_color:
                if existing and existing["color"]:
                    final_color = existing["color"]
                else:
                    cur.execute("SELECT color FROM projects")
                    used = {r["color"].upper() for r in cur.fetchall() if r["color"]}
                    for c in DEFAULT_PROJECT_PALETTE:
                        if c.upper() not in used:
                            final_color = c
                            break
                    if not final_color:
                        final_color = DEFAULT_PROJECT_PALETTE[0]

            cur.execute(
                """
                INSERT INTO projects (name, keywords, color, description)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    keywords = excluded.keywords,
                    color = excluded.color,
                    description = excluded.description
                """,
                (name_clean, kw_str, final_color, description.strip()),
            )
            return cur.lastrowid or 0

    def rename_project(
        self,
        old_name: str,
        new_name: str,
        color: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> bool:
        """
        Safely rename a project and cascade changes to sessions, tasks, and notes.
        If new_name already exists, merge the old project records into new_name and delete the old project.
        """
        self._projects_cache = None
        old_clean = old_name.strip()
        new_clean = new_name.strip()
        if not old_clean or not new_clean:
            return False

        with self.db.cursor() as cur:
            if old_clean.lower() == new_clean.lower():
                # Case change or in-place attribute update
                cur.execute("SELECT id, keywords, color, description FROM projects WHERE name = ?", (old_clean,))
                current = cur.fetchone()
                if not current:
                    return False

                kw_str = ",".join([k.strip().lower() for k in keywords if k.strip()]) if keywords is not None else current["keywords"]
                c_val = color.strip() if (color and color.strip()) else current["color"]
                d_val = description.strip() if description is not None else current["description"]

                cur.execute(
                    "UPDATE projects SET name = ?, keywords = ?, color = ?, description = ? WHERE id = ?",
                    (new_clean, kw_str, c_val, d_val, current["id"]),
                )
                cur.execute("UPDATE sessions SET project_tag = ? WHERE project_tag = ?", (new_clean, old_clean))
                cur.execute("UPDATE tasks SET project_tag = ? WHERE project_tag = ?", (new_clean, old_clean))
                cur.execute("UPDATE notes SET project_tag = ? WHERE project_tag = ?", (new_clean, old_clean))
                return True

            # Check if target new_name already exists in projects table
            cur.execute("SELECT id, keywords, color, description FROM projects WHERE name = ?", (new_clean,))
            target_existing = cur.fetchone()

            cur.execute("SELECT id, keywords, color, description FROM projects WHERE name = ?", (old_clean,))
            source_existing = cur.fetchone()

            if target_existing:
                # Merge duplicate: update target with source's info or overrides, delete source
                kw_str = ",".join([k.strip().lower() for k in keywords if k.strip()]) if keywords is not None else (
                    target_existing["keywords"] or (source_existing["keywords"] if source_existing else "")
                )
                c_val = color.strip() if (color and color.strip()) else (
                    target_existing["color"] if target_existing["color"] and target_existing["color"] != "#FF6B3D"
                    else (source_existing["color"] if source_existing else "#FF6B3D")
                )
                d_val = description.strip() if description is not None else (
                    target_existing["description"] or (source_existing["description"] if source_existing else "")
                )

                cur.execute(
                    "UPDATE projects SET keywords = ?, color = ?, description = ? WHERE id = ?",
                    (kw_str, c_val, d_val, target_existing["id"]),
                )
                if source_existing:
                    cur.execute("DELETE FROM projects WHERE id = ?", (source_existing["id"],))
            else:
                # Direct rename
                if source_existing:
                    kw_str = ",".join([k.strip().lower() for k in keywords if k.strip()]) if keywords is not None else source_existing["keywords"]
                    c_val = color.strip() if (color and color.strip()) else source_existing["color"]
                    d_val = description.strip() if description is not None else source_existing["description"]
                    cur.execute(
                        "UPDATE projects SET name = ?, keywords = ?, color = ?, description = ? WHERE id = ?",
                        (new_clean, kw_str, c_val, d_val, source_existing["id"]),
                    )
                else:
                    kw_str = ",".join([k.strip().lower() for k in keywords if k.strip()]) if keywords is not None else ""
                    c_val = color.strip() if (color and color.strip()) else DEFAULT_PROJECT_PALETTE[0]
                    d_val = description.strip() if description is not None else ""
                    cur.execute(
                        "INSERT INTO projects (name, keywords, color, description) VALUES (?, ?, ?, ?)",
                        (new_clean, kw_str, c_val, d_val),
                    )

            # Cascade update all historical records
            cur.execute("UPDATE sessions SET project_tag = ? WHERE project_tag = ?", (new_clean, old_clean))
            cur.execute("UPDATE tasks SET project_tag = ? WHERE project_tag = ?", (new_clean, old_clean))
            cur.execute("UPDATE notes SET project_tag = ? WHERE project_tag = ?", (new_clean, old_clean))
            return True

    def delete_project(self, project_id: int) -> bool:
        """Delete a project by its database ID."""
        self._projects_cache = None
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cur.rowcount > 0

    def delete_project_by_name(self, name: str) -> bool:
        """Delete a project by its unique name."""
        self._projects_cache = None
        with self.db.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE name = ?", (name.strip(),))
            return cur.rowcount > 0

    def get_all_projects(self, force_refresh: bool = False) -> List[ProjectRecord]:
        """Fetch all configured projects with in-memory caching."""
        if self._projects_cache is not None and not force_refresh:
            return self._projects_cache

        with self.db.cursor() as cur:
            cur.execute("SELECT id, name, keywords, color, description FROM projects ORDER BY name ASC")
            rows = cur.fetchall()
            self._projects_cache = [
                ProjectRecord(
                    id=row["id"],
                    name=row["name"],
                    keywords=[k.strip() for k in (row["keywords"] or "").split(",") if k.strip()],
                    color=row["color"] or "#FF6B3D",
                    description=row["description"] or "",
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

    def _get_timeframe_bounds(self, timeframe: str) -> Optional[datetime]:
        """Return start datetime for the given timeframe (or None for all_time)."""
        now = datetime.now()
        tf = timeframe.lower().replace(" ", "_")
        if tf == "today":
            return datetime(now.year, now.month, now.day, 0, 0, 0)
        elif tf in ("this_week", "week"):
            start_of_week = now - timedelta(days=now.weekday())
            return datetime(start_of_week.year, start_of_week.month, start_of_week.day, 0, 0, 0)
        elif tf in ("this_month", "month"):
            return datetime(now.year, now.month, 1, 0, 0, 0)
        return None

    def get_projects_overview_metrics(self, timeframe: str = "all_time") -> List[Dict[str, Any]]:
        """
        Aggregate project metrics (tracked minutes, task counts, completion rate, top apps)
        for all configured projects within the specified timeframe.
        """
        projects = self.get_all_projects(force_refresh=True)
        start_bound = self._get_timeframe_bounds(timeframe)
        start_iso = start_bound.isoformat() if start_bound else None

        results = []
        with self.db.cursor() as cur:
            for proj in projects:
                # 1. Sessions & Top Apps
                if start_iso:
                    cur.execute(
                        """
                        SELECT app_name, start_time, end_time
                        FROM sessions
                        WHERE project_tag = ? AND start_time >= ?
                        """,
                        (proj.name, start_iso),
                    )
                else:
                    cur.execute(
                        """
                        SELECT app_name, start_time, end_time
                        FROM sessions
                        WHERE project_tag = ?
                        """,
                        (proj.name,),
                    )
                sess_rows = cur.fetchall()

                total_minutes = 0.0
                app_durations: Dict[str, float] = {}
                for r in sess_rows:
                    try:
                        st = datetime.fromisoformat(r["start_time"])
                        et = datetime.fromisoformat(r["end_time"])
                        dur = max(0.0, (et - st).total_seconds() / 60.0)
                    except Exception:
                        dur = 0.0
                    total_minutes += dur
                    app_name = r["app_name"] or "Unknown"
                    app_durations[app_name] = app_durations.get(app_name, 0.0) + dur

                sorted_apps = sorted(app_durations.items(), key=lambda x: x[1], reverse=True)
                top_apps = [(app, round(mins, 1)) for app, mins in sorted_apps[:3]]

                # 2. Tasks & Completion
                if start_iso:
                    cur.execute(
                        """
                        SELECT id, status
                        FROM tasks
                        WHERE project_tag = ? AND (created_at >= ? OR (completed_at IS NOT NULL AND completed_at >= ?))
                        """,
                        (proj.name, start_iso, start_iso),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, status
                        FROM tasks
                        WHERE project_tag = ?
                        """,
                        (proj.name,),
                    )
                task_rows = cur.fetchall()
                total_tasks = len(task_rows)
                completed_tasks = sum(1 for t in task_rows if t["status"] in ("done", "completed"))
                completion_rate = (completed_tasks / total_tasks) if total_tasks > 0 else 0.0

                results.append({
                    "id": proj.id,
                    "name": proj.name,
                    "color": proj.color,
                    "description": proj.description,
                    "keywords": proj.keywords,
                    "tracked_minutes": round(total_minutes, 1),
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "completion_rate": round(completion_rate, 2),
                    "top_apps": top_apps,
                })

        # Ensure all project cards and tracking tracks display distinct colors
        used_overview_colors: set[str] = set()
        pal_idx = 0
        for item in results:
            col = (item.get("color") or "").strip().upper()
            if not col or col in used_overview_colors:
                while pal_idx < len(DEFAULT_PROJECT_PALETTE) and DEFAULT_PROJECT_PALETTE[pal_idx].upper() in used_overview_colors:
                    pal_idx += 1
                assigned = DEFAULT_PROJECT_PALETTE[pal_idx] if pal_idx < len(DEFAULT_PROJECT_PALETTE) else DEFAULT_PROJECT_PALETTE[len(used_overview_colors) % len(DEFAULT_PROJECT_PALETTE)]
                item["color"] = assigned
                used_overview_colors.add(assigned.upper())
            else:
                used_overview_colors.add(col)

        return results

    def get_project_detail(self, project_name: str, timeframe: str = "all_time") -> Dict[str, Any]:
        """Fetch full metrics, tasks, and application breakdown for a specific project."""
        projects = self.get_all_projects(force_refresh=True)
        target_proj = next((p for p in projects if p.name.lower() == project_name.lower()), None)
        if target_proj is None:
            target_proj = ProjectRecord(id=None, name=project_name, keywords=[], color="#FF6B3D", description="")

        start_bound = self._get_timeframe_bounds(timeframe)
        start_iso = start_bound.isoformat() if start_bound else None

        with self.db.cursor() as cur:
            # 1. Sessions & App breakdown
            if start_iso:
                cur.execute(
                    """
                    SELECT app_name, window_title, start_time, end_time
                    FROM sessions
                    WHERE project_tag = ? AND start_time >= ?
                    ORDER BY start_time DESC
                    """,
                    (target_proj.name, start_iso),
                )
            else:
                cur.execute(
                    """
                    SELECT app_name, window_title, start_time, end_time
                    FROM sessions
                    WHERE project_tag = ?
                    ORDER BY start_time DESC
                    """,
                    (target_proj.name,),
                )
            sess_rows = cur.fetchall()

            total_minutes = 0.0
            app_durations: Dict[str, float] = {}
            for r in sess_rows:
                try:
                    st = datetime.fromisoformat(r["start_time"])
                    et = datetime.fromisoformat(r["end_time"])
                    dur = max(0.0, (et - st).total_seconds() / 60.0)
                except Exception:
                    dur = 0.0
                total_minutes += dur
                app_name = r["app_name"] or "Unknown"
                app_durations[app_name] = app_durations.get(app_name, 0.0) + dur

            apps_breakdown = []
            for app_name, mins in sorted(app_durations.items(), key=lambda x: x[1], reverse=True):
                pct = round((mins / total_minutes * 100), 1) if total_minutes > 0 else 0.0
                apps_breakdown.append({
                    "app_name": app_name,
                    "minutes": round(mins, 1),
                    "percentage": pct,
                })

            # 2. Tasks with subtasks
            tasks = self.get_task_hierarchy(project_tag=target_proj.name)
            if start_iso:
                # Filter tasks created or completed in timeframe
                tasks = [
                    t for t in tasks
                    if t.created_at >= start_bound or (t.completed_at and t.completed_at >= start_bound)
                ]

            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.status in ("done", "completed"))
            in_progress_tasks = sum(1 for t in tasks if t.status in ("in_progress", "pending", "ongoing"))
            open_tasks = total_tasks - completed_tasks

            return {
                "project": target_proj,
                "tracked_minutes": round(total_minutes, 1),
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "open_tasks": open_tasks,
                "completion_rate": round((completed_tasks / total_tasks), 2) if total_tasks > 0 else 0.0,
                "apps_breakdown": apps_breakdown,
                "tasks": tasks,
                "total_sessions": len(sess_rows),
            }

    def get_dashboard_analytics(self, timeframe: str = "this_week") -> Dict[str, Any]:
        """
        Aggregate high-level analytics for visual dashboard:
        - KPI summary metrics (total hours, change %, active projects, tasks completed, top app)
        - Time-series buckets for project comparison (Bar / Area charts)
        - Application usage ranking with durations and percentages (Ring / Bar charts)
        """
        now = datetime.now()
        tf = timeframe.lower().replace(" ", "_")

        # 1. Determine date boundaries for current and previous periods
        if tf == "today":
            start_curr = datetime(now.year, now.month, now.day, 0, 0, 0)
            end_curr = now
            start_prev = start_curr - timedelta(days=1)
            end_prev = start_curr
            bucket_labels = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00+"]
        elif tf in ("this_week", "week"):
            start_curr = datetime(now.year, now.month, now.day, 0, 0, 0) - timedelta(days=now.weekday())
            end_curr = start_curr + timedelta(days=7)
            start_prev = start_curr - timedelta(days=7)
            end_prev = start_curr
            bucket_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        elif tf in ("this_month", "month"):
            start_curr = datetime(now.year, now.month, 1, 0, 0, 0)
            if now.month == 12:
                end_curr = datetime(now.year + 1, 1, 1, 0, 0, 0)
            else:
                end_curr = datetime(now.year, now.month + 1, 1, 0, 0, 0)
            first_day_prev = (start_curr - timedelta(days=1)).replace(day=1)
            start_prev = first_day_prev
            end_prev = start_curr
            bucket_labels = ["Week 1", "Week 2", "Week 3", "Week 4"]
        else:
            start_curr = None
            end_curr = None
            start_prev = None
            end_prev = None
            bucket_labels = []

        all_projects = self.get_all_projects(force_refresh=True)
        proj_colors: Dict[str, str] = {p.name: (p.color or "#FF6B3D") for p in all_projects}

        with self.db.cursor() as cur:
            # 2. Fetch current period sessions
            if start_curr:
                cur.execute(
                    """
                    SELECT app_name, project_tag, start_time, end_time
                    FROM sessions
                    WHERE start_time >= ? AND start_time <= ?
                    ORDER BY start_time ASC
                    """,
                    (start_curr.isoformat(), end_curr.isoformat()),
                )
            else:
                cur.execute(
                    """
                    SELECT app_name, project_tag, start_time, end_time
                    FROM sessions
                    ORDER BY start_time ASC
                    """
                )
            curr_rows = cur.fetchall()

            # 3. Fetch previous period sessions for change % calculation
            prev_minutes = 0.0
            if start_prev and end_prev:
                cur.execute(
                    """
                    SELECT start_time, end_time
                    FROM sessions
                    WHERE start_time >= ? AND start_time < ?
                    """,
                    (start_prev.isoformat(), end_prev.isoformat()),
                )
                prev_rows = cur.fetchall()
                for r in prev_rows:
                    try:
                        st = datetime.fromisoformat(r["start_time"])
                        et = datetime.fromisoformat(r["end_time"])
                        prev_minutes += max(0.0, (et - st).total_seconds() / 60.0)
                    except Exception:
                        pass

            # 4. Fetch tasks in current period
            if start_curr:
                cur.execute(
                    """
                    SELECT id, status, project_tag
                    FROM tasks
                    WHERE created_at >= ? OR (completed_at IS NOT NULL AND completed_at >= ?)
                    """,
                    (start_curr.isoformat(), start_curr.isoformat()),
                )
            else:
                cur.execute("SELECT id, status, project_tag FROM tasks")
            task_rows = cur.fetchall()
            completed_tasks = sum(1 for t in task_rows if t["status"] in ("done", "completed"))
            open_tasks = len(task_rows) - completed_tasks

            # 5. Process current sessions
            total_minutes = 0.0
            app_durations: Dict[str, float] = {}
            project_durations: Dict[str, float] = {}
            app_proj_minutes: Dict[str, Dict[str, float]] = {}

            if tf == "all_time":
                if all_projects:
                    bucket_labels = [p.name for p in all_projects]
                else:
                    bucket_labels = ["General"]

            num_buckets = len(bucket_labels) if bucket_labels else 1
            project_bucket_mins: Dict[str, List[float]] = {}

            for r in curr_rows:
                try:
                    st = datetime.fromisoformat(r["start_time"])
                    et = datetime.fromisoformat(r["end_time"])
                    dur = max(0.0, (et - st).total_seconds() / 60.0)
                except Exception:
                    dur = 0.0

                total_minutes += dur
                app_name = r["app_name"] or "Unknown"
                app_durations[app_name] = app_durations.get(app_name, 0.0) + dur

                proj_name = r["project_tag"] or "Untagged"
                project_durations[proj_name] = project_durations.get(proj_name, 0.0) + dur

                if app_name not in app_proj_minutes:
                    app_proj_minutes[app_name] = {}
                app_proj_minutes[app_name][proj_name] = app_proj_minutes[app_name].get(proj_name, 0.0) + dur

                if proj_name not in project_bucket_mins:
                    project_bucket_mins[proj_name] = [0.0] * num_buckets

                if tf == "today":
                    h = st.hour
                    if h < 10:
                        b_idx = 0
                    elif h < 12:
                        b_idx = 1
                    elif h < 14:
                        b_idx = 2
                    elif h < 16:
                        b_idx = 3
                    elif h < 18:
                        b_idx = 4
                    else:
                        b_idx = 5
                elif tf in ("this_week", "week") and start_curr:
                    diff_days = (st.date() - start_curr.date()).days
                    b_idx = max(0, min(6, diff_days))
                elif tf in ("this_month", "month"):
                    day = st.day
                    if day <= 7:
                        b_idx = 0
                    elif day <= 14:
                        b_idx = 1
                    elif day <= 21:
                        b_idx = 2
                    else:
                        b_idx = 3
                elif tf == "all_time":
                    if proj_name in bucket_labels:
                        b_idx = bucket_labels.index(proj_name)
                    else:
                        b_idx = 0
                else:
                    b_idx = 0

                if 0 <= b_idx < num_buckets:
                    project_bucket_mins[proj_name][b_idx] += dur

            # Build app breakdown list using bar chart color style & project alignment
            APP_PALETTE = [
                "#FF6B3D",  # Mascot Orange-Red (Brand - Coding)
                "#10B981",  # Emerald (Gaming)
                "#6366F1",  # Indigo (WizDesk)
                "#64748B",  # Slate (Untagged)
                "#38BDF8",  # Sky Blue
                "#F97316",  # Tangerine
                "#14B8A6",  # Teal
                "#A855F7",  # Soft Purple
                "#E11D48",  # Rose (Browsing)
                "#84CC16",  # Lime
                "#475569",  # Steel
                "#EC4899",  # Pink
                "#0EA5E9",  # Ocean Blue
                "#059669",  # Forest Jade
                "#D97706",  # Bronze Ochre
                "#52525B",  # Zinc Gray
            ]

            app_dominant_proj = {
                an: max(pm.items(), key=lambda x: x[1])[0]
                for an, pm in app_proj_minutes.items()
            }

            used_app_colors: set[str] = set()
            palette_app_idx = 0
            apps_list = []
            for idx, (app_name, mins) in enumerate(sorted(app_durations.items(), key=lambda x: x[1], reverse=True)):
                pct = round((mins / total_minutes * 100), 1) if total_minutes > 0 else 0.0
                dom_proj = app_dominant_proj.get(app_name)
                assigned_c = None
                if dom_proj:
                    if dom_proj == "Untagged":
                        cand_c = "#64748B"
                    else:
                        cand_c = proj_colors.get(dom_proj)
                    if cand_c and cand_c.upper() not in used_app_colors:
                        assigned_c = cand_c

                if not assigned_c:
                    while palette_app_idx < len(APP_PALETTE) and APP_PALETTE[palette_app_idx].upper() in used_app_colors:
                        palette_app_idx += 1
                    if palette_app_idx < len(APP_PALETTE):
                        assigned_c = APP_PALETTE[palette_app_idx]
                        palette_app_idx += 1
                    else:
                        assigned_c = APP_PALETTE[idx % len(APP_PALETTE)]

                used_app_colors.add(assigned_c.upper())
                apps_list.append({
                    "app_name": app_name,
                    "minutes": round(mins, 1),
                    "hours": round(mins / 60.0, 1),
                    "percentage": pct,
                    "color": assigned_c,
                })

            top_app = apps_list[0] if apps_list else None

            if prev_minutes > 0:
                change_pct = round(((total_minutes - prev_minutes) / prev_minutes) * 100, 1)
            else:
                change_pct = 0.0

            # Ensure distinct colors across all compared project series (24 colors)
            PROJECT_COMPARISON_PALETTE = [
                "#FF6B3D",  # Mascot Orange-Red (Brand)
                "#10B981",  # Emerald
                "#3B82F6",  # Electric Blue
                "#F59E0B",  # Amber Gold
                "#8B5CF6",  # Violet
                "#EC4899",  # Hot Pink
                "#06B6D4",  # Cyan
                "#F43F5E",  # Rose
                "#84CC16",  # Lime Green
                "#14B8A6",  # Teal
                "#F97316",  # Tangerine
                "#A855F7",  # Purple
                "#0EA5E9",  # Sky Blue
                "#E11D48",  # Crimson
                "#059669",  # Forest Jade
                "#6366F1",  # Indigo
                "#EAB308",  # Sunburst Yellow
                "#D946EF",  # Fuchsia
                "#2563EB",  # Cobalt Blue
                "#FF5722",  # Flame Orange
                "#0284C7",  # Cerulean
                "#D97706",  # Bronze Ochre
                "#64748B",  # Slate
                "#475569",  # Steel
            ]

            sorted_proj_buckets = sorted(
                project_bucket_mins.items(),
                key=lambda item: sum(item[1]),
                reverse=True,
            )

            UNTAGGED_COLOR = "#64748B"  # Dedicated neutral slate gray for untagged activity
            used_colors: set[str] = set()
            palette_idx = 0
            series_pre = []

            # First pass: assign explicit unique colors for named projects and dedicated neutral for Untagged
            for proj_name, bucket_vals in sorted_proj_buckets:
                hours_vals = [round(m / 60.0, 2) for m in bucket_vals]
                tot_h = round(sum(hours_vals), 2)
                if proj_name == "Untagged":
                    used_colors.add(UNTAGGED_COLOR.upper())
                    series_pre.append((proj_name, hours_vals, tot_h, UNTAGGED_COLOR))
                else:
                    raw_color = proj_colors.get(proj_name)
                    if raw_color and raw_color.upper() not in used_colors and raw_color.upper() != UNTAGGED_COLOR.upper():
                        used_colors.add(raw_color.upper())
                        series_pre.append((proj_name, hours_vals, tot_h, raw_color))
                    else:
                        series_pre.append((proj_name, hours_vals, tot_h, None))

            # Second pass: assign distinct palette colors to unregistered or colliding projects
            project_series = []
            for proj_name, hours_vals, tot_h, assigned_color in series_pre:
                if not assigned_color:
                    while palette_idx < len(PROJECT_COMPARISON_PALETTE) and (
                        PROJECT_COMPARISON_PALETTE[palette_idx].upper() in used_colors
                        or PROJECT_COMPARISON_PALETTE[palette_idx].upper() == UNTAGGED_COLOR.upper()
                    ):
                        palette_idx += 1
                    if palette_idx < len(PROJECT_COMPARISON_PALETTE):
                        assigned_color = PROJECT_COMPARISON_PALETTE[palette_idx]
                        palette_idx += 1
                    else:
                        assigned_color = PROJECT_COMPARISON_PALETTE[len(used_colors) % len(PROJECT_COMPARISON_PALETTE)]
                    used_colors.add(assigned_color.upper())

                project_series.append({
                    "name": proj_name,
                    "color": assigned_color,
                    "hours": hours_vals,
                    "total_hours": tot_h,
                })

            project_series.sort(key=lambda s: s["total_hours"], reverse=True)

            active_projects = set(project_durations.keys()) | {t["project_tag"] for t in task_rows if t["project_tag"]}
            active_projects.discard(None)

            return {
                "timeframe": tf,
                "total_tracked_minutes": round(total_minutes, 1),
                "total_tracked_hours": round(total_minutes / 60.0, 1),
                "previous_period_minutes": round(prev_minutes, 1),
                "change_percentage": change_pct,
                "active_projects_count": max(len(active_projects), len(all_projects)),
                "completed_tasks_count": completed_tasks,
                "open_tasks_count": open_tasks,
                "top_app": top_app,
                "apps_breakdown": apps_list,
                "chart_bucket_labels": bucket_labels,
                "chart_project_series": project_series,
            }


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

