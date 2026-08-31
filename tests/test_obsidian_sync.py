"""Unit tests for Wiz Obsidian Sync Engine and Markdown formatting."""

from datetime import datetime, date, timedelta
from pathlib import Path
import pytest

from wiz.core.config import Config
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository
from wiz.sync.obsidian import ObsidianSync


@pytest.fixture
def repo_with_data(tmp_path):
    """Provide a repository populated with sample daily data."""
    db_file = tmp_path / "test_sync.db"
    db = Database(db_file)
    repo = StorageRepository(db)

    # 1. Add Task with subtasks and logs
    task_id = repo.create_task("Build TurfLine booking flow", project_tag="TurfLine")
    st1 = repo.create_subtask(task_id, "Design booking UI")
    st2 = repo.create_subtask(task_id, "Wire up backend API")
    repo.update_subtask_status(st1, "done")
    repo.update_subtask_status(st2, "in_progress")

    repo.add_task_log(task_id, "hit CORS issue, debugging", subtask_id=st2)
    repo.add_task_log(task_id, "fixed, testing now", subtask_id=st2)

    # 2. Add Auto-tracked sessions
    t1 = datetime(2026, 8, 31, 9, 0, 0)
    t2 = datetime(2026, 8, 31, 9, 30, 0)
    t3 = datetime(2026, 8, 31, 10, 0, 0)
    repo.log_session("Code.exe", "TurfLine - VS Code", t1, t2, project_tag="TurfLine")
    repo.log_session("chrome.exe", "Research - Google Chrome", t2, t3, project_tag="research")

    # 3. Add Notes
    n1 = repo.create_note("Fixed booking bug in TurfLine", project_tag="TurfLine")
    repo.toggle_note_completed(n1, True)
    repo.create_note("Draft resume for ML role")

    return repo


def test_obsidian_markdown_generation(repo_with_data):
    """Test generating structured Markdown daily note matching the PRD format."""
    sync_engine = ObsidianSync(repo_with_data)
    md = sync_engine.generate_markdown(date(2026, 8, 31))

    # Verify sections
    assert "## 2026-08-31" in md
    assert "### Tasks" in md
    assert "Build TurfLine booking flow" in md
    assert "- [x] Design booking UI" in md
    assert "- [~] Wire up backend API" in md
    assert "hit CORS issue, debugging" in md
    assert "fixed, testing now" in md

    assert "### Auto-tracked" in md
    assert "09:00–09:30 — Code (TurfLine)" in md
    assert "09:30–10:00 — chrome (research)" in md

    assert "### Notes" in md
    assert "[x] [TurfLine] Fixed booking bug in TurfLine ✅" in md
    assert "[ ] Draft resume for ML role" in md


def test_obsidian_vault_file_sync(repo_with_data, tmp_path, monkeypatch):
    """Test sync_date writing the daily note into the vault directory."""
    vault_dir = tmp_path / "MyObsidianVault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    test_cfg = Config(config_file=tmp_path / "test_cfg.json")
    test_cfg.set("obsidian_vault_path", str(vault_dir))

    monkeypatch.setattr("wiz.sync.obsidian.config", test_cfg)

    sync_engine = ObsidianSync(repo_with_data)
    success, msg = sync_engine.sync_date(date(2026, 8, 31))

    assert success is True
    expected_file = vault_dir / "Wiz Logs" / "2026-08-31.md"
    assert expected_file.exists()

    content = expected_file.read_text(encoding="utf-8")
    assert "## 2026-08-31" in content
    assert "Build TurfLine booking flow" in content
