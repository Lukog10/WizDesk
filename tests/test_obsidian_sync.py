"""Unit tests for WizDesk Obsidian Sync Engine and Markdown formatting."""

from datetime import datetime, date
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
    n2 = repo.create_note("Draft resume for ML role")

    # Ensure records match the test target date 2026-08-31
    with db.cursor() as cur:
        cur.execute("UPDATE tasks SET created_at = '2026-08-31T09:00:00'")
        cur.execute("UPDATE subtasks SET created_at = '2026-08-31T09:00:00'")
        cur.execute("UPDATE task_logs SET created_at = '2026-08-31T09:15:00'")
        cur.execute("UPDATE notes SET created_at = '2026-08-31T10:15:00'")

    return repo


def test_obsidian_markdown_generation(repo_with_data):
    """Test generating structured Markdown daily note matching the PRD format without emojis."""
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
    assert "09:00-09:30 - Code (TurfLine)" in md
    assert "09:30-10:00 - chrome (research)" in md

    assert "### Notes" in md
    assert "[x] [TurfLine] Fixed booking bug in TurfLine (10:15)" in md or "[x] [TurfLine] Fixed booking bug in TurfLine" in md
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
    expected_file = vault_dir / "WizDesk Logs" / "2026-08-31.md"
    assert expected_file.exists()

    content = expected_file.read_text(encoding="utf-8")
    assert "## 2026-08-31" in content
    assert "Build TurfLine booking flow" in content


def test_obsidian_sync_blocked_when_encryption_enabled(repo_with_data, tmp_path, monkeypatch):
    """Test that sync_date blocks plaintext file creation when DB encryption is active without opt-in."""
    vault_dir = tmp_path / "VaultSecure"
    vault_dir.mkdir(parents=True, exist_ok=True)

    test_cfg = Config(config_file=tmp_path / "test_cfg_sec.json")
    test_cfg.set("obsidian_vault_path", str(vault_dir))
    test_cfg.set("encryption_enabled", True)
    test_cfg.set("allow_plaintext_obsidian_sync", False)

    monkeypatch.setattr("wiz.sync.obsidian.config", test_cfg)

    sync_engine = ObsidianSync(repo_with_data)
    success, msg = sync_engine.sync_date(date(2026, 8, 31))

    assert success is False
    assert "Database encryption is active" in msg
    # Verify no file written
    assert not (vault_dir / "WizDesk Logs" / "2026-08-31.md").exists()


def test_obsidian_sync_allowed_when_encryption_enabled_with_opt_in(repo_with_data, tmp_path, monkeypatch):
    """Test that sync_date proceeds when DB encryption is active and user explicitly opts in."""
    vault_dir = tmp_path / "VaultOptIn"
    vault_dir.mkdir(parents=True, exist_ok=True)

    test_cfg = Config(config_file=tmp_path / "test_cfg_opt.json")
    test_cfg.set("obsidian_vault_path", str(vault_dir))
    test_cfg.set("encryption_enabled", True)
    test_cfg.set("allow_plaintext_obsidian_sync", True)

    monkeypatch.setattr("wiz.sync.obsidian.config", test_cfg)

    sync_engine = ObsidianSync(repo_with_data)
    success, msg = sync_engine.sync_date(date(2026, 8, 31))

    assert success is True
    assert (vault_dir / "WizDesk Logs" / "2026-08-31.md").exists()


def test_obsidian_sync_path_traversal_sanitized(repo_with_data, tmp_path, monkeypatch):
    """Test that malicious path traversal in logs folder name is clamped to vault directory."""
    vault_dir = tmp_path / "VaultTraversal"
    vault_dir.mkdir(parents=True, exist_ok=True)

    test_cfg = Config(config_file=tmp_path / "test_cfg_trav.json")
    test_cfg.set("obsidian_vault_path", str(vault_dir))
    test_cfg.set("obsidian_logs_folder", "../../escaped_dir")

    monkeypatch.setattr("wiz.sync.obsidian.config", test_cfg)

    sync_engine = ObsidianSync(repo_with_data)
    success, msg = sync_engine.sync_date(date(2026, 8, 31))

    assert success is True
    # Confirm it was clamped to safe default folder inside vault
    assert (vault_dir / "WizDesk Logs" / "2026-08-31.md").exists()
    assert not (tmp_path / "escaped_dir").exists()


def test_obsidian_sync_note_blocked_when_encryption_enabled(repo_with_data, tmp_path, monkeypatch):
    """Test that sync_note blocks plaintext note file creation when DB encryption is active without opt-in."""
    vault_dir = tmp_path / "VaultNoteSecure"
    vault_dir.mkdir(parents=True, exist_ok=True)

    test_cfg = Config(config_file=tmp_path / "test_cfg_note_sec.json")
    test_cfg.set("obsidian_vault_path", str(vault_dir))
    test_cfg.set("encryption_enabled", True)
    test_cfg.set("allow_plaintext_obsidian_sync", False)

    monkeypatch.setattr("wiz.sync.obsidian.config", test_cfg)

    notes = repo_with_data.get_notes_for_date(date(2026, 8, 31))
    assert len(notes) > 0
    note = notes[0]

    sync_engine = ObsidianSync(repo_with_data)
    success, msg = sync_engine.sync_note(note)

    assert success is False
    assert "Database encryption is active" in msg
    assert not (vault_dir / "WizNotes").exists()


def test_obsidian_sync_note_allowed_with_opt_in(repo_with_data, tmp_path, monkeypatch):
    """Test that sync_note proceeds when DB encryption is active and user explicitly opts in."""
    vault_dir = tmp_path / "VaultNoteOptIn"
    vault_dir.mkdir(parents=True, exist_ok=True)

    test_cfg = Config(config_file=tmp_path / "test_cfg_note_opt.json")
    test_cfg.set("obsidian_vault_path", str(vault_dir))
    test_cfg.set("encryption_enabled", True)
    test_cfg.set("allow_plaintext_obsidian_sync", True)

    monkeypatch.setattr("wiz.sync.obsidian.config", test_cfg)

    notes = repo_with_data.get_notes_for_date(date(2026, 8, 31))
    assert len(notes) > 0
    note = notes[0]

    sync_engine = ObsidianSync(repo_with_data)
    success, msg = sync_engine.sync_note(note)

    assert success is True
    assert (vault_dir / "WizNotes").exists()

