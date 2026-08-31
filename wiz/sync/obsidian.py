"""Obsidian vault synchronization and structured Markdown daily log generation."""

from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

from wiz.core.config import config
from wiz.core.signals import app_signals
from wiz.storage.models import StorageRepository, TaskRecord, NoteRecord, SessionRecord


class ObsidianSync:
    """
    Serializes buffered SQLite data (sessions, tasks, notes) into structured
    Markdown daily notes and writes them into the user's Obsidian vault.
    """

    def __init__(self, repository: Optional[StorageRepository] = None):
        self.repo = repository or StorageRepository()

    def generate_markdown(self, target_date: date) -> str:
        """Generate the complete Markdown content for the given date."""
        day_str = target_date.strftime("%Y-%m-%d")

        sessions = self.repo.get_sessions_for_date(target_date)
        tasks = self.repo.get_task_hierarchy(target_date=target_date)
        notes = self.repo.get_notes_for_date(target_date)

        lines = [f"## {day_str}", ""]

        # 1. Tasks Section
        lines.append("### Tasks")
        if tasks:
            for task in tasks:
                status_char = "x" if task.status == "done" else ("~" if task.status == "in_progress" else " ")
                tag_str = f" ({task.project_tag})" if task.project_tag else ""
                lines.append(f"- [{status_char}] {task.title}{tag_str}")

                # Subtasks
                for subtask in task.subtasks:
                    st_char = "x" if subtask.status == "done" else ("~" if subtask.status == "in_progress" else " ")
                    lines.append(f"  - [{st_char}] {subtask.title}")
                    # Subtask logs
                    for log in subtask.logs:
                        time_str = log.created_at.strftime("%H:%M")
                        lines.append(f"    - {time_str} — {log.content}")

                # Parent task logs
                for log in task.task_logs:
                    time_str = log.created_at.strftime("%H:%M")
                    lines.append(f"  - {time_str} — {log.content}")
        else:
            lines.append("_No tasks recorded for today._")

        lines.append("")

        # 2. Auto-tracked Section
        lines.append("### Auto-tracked")
        if sessions:
            for s in sessions:
                start_str = s.start_time.strftime("%H:%M")
                end_str = s.end_time.strftime("%H:%M")
                app_clean = s.app_name.removesuffix(".exe")
                desc = s.project_tag or s.window_title or "general"
                lines.append(f"- {start_str}–{end_str} — {app_clean} ({desc})")
        else:
            lines.append("_No activity tracked._")

        lines.append("")

        # 3. Notes Section
        lines.append("### Notes")
        if notes:
            for note in notes:
                check_char = "x" if note.is_completed else " "
                time_str = note.created_at.strftime("%H:%M")
                tag_str = f"[{note.project_tag}] " if note.project_tag else ""
                check_emoji = " ✅" if note.is_completed else ""
                lines.append(f"- [{check_char}] {tag_str}{note.content}{check_emoji} {time_str}")
        else:
            lines.append("_No notes logged._")

        lines.append("")
        return "\n".join(lines)

    def sync_date(self, target_date: date) -> Tuple[bool, str]:
        """
        Write or overwrite the daily Markdown note in the Obsidian Vault.
        
        Returns:
            (success: bool, message: str)
        """
        vault_path = config.obsidian_vault_path
        if not vault_path or not vault_path.exists():
            msg = "Obsidian vault path not configured or directory does not exist."
            app_signals.sync_finished.emit(False, msg)
            return False, msg

        logs_folder_name = config.get("obsidian_logs_folder", "Wiz Logs")
        dest_dir = vault_path / logs_folder_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{target_date.strftime('%Y-%m-%d')}.md"
        dest_file = dest_dir / filename

        try:
            content = self.generate_markdown(target_date)

            # Atomic write via temporary file
            temp_file = dest_file.with_suffix(".tmp")
            temp_file.write_text(content, encoding="utf-8")
            temp_file.replace(dest_file)

            msg = f"Successfully synced daily logs to {dest_file.name}"
            app_signals.sync_finished.emit(True, msg)
            return True, msg
        except Exception as e:
            msg = f"Error writing to Obsidian vault: {e}"
            app_signals.sync_finished.emit(False, msg)
            return False, msg


def sync_today_logs() -> Tuple[bool, str]:
    """Helper to sync today's logs directly."""
    sync_engine = ObsidianSync()
    return sync_engine.sync_date(date.today())
