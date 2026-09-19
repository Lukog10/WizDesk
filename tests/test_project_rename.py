"""Unit tests for project renaming, cascading updates, and color de-duplication."""

from datetime import datetime, timedelta
import pytest

from wiz.storage.db import Database
from wiz.storage.models import StorageRepository


@pytest.fixture
def repo(tmp_path):
    """Provide a fresh SQLite repository backed by a temporary file."""
    db_file = tmp_path / "test_wiz_rename.db"
    db = Database(db_file)
    return StorageRepository(db)


def test_rename_project_cascades_to_sessions_tasks_notes(repo):
    """Verify that renaming a project updates projects, sessions, tasks, and notes."""
    # 1. Setup project
    repo.create_or_update_project("Research", ["zen", "browse"], color="#E11D48", description="Initial")

    # 2. Add historical session, task, and note
    now = datetime(2026, 9, 1, 10, 0, 0)
    repo.log_session("zen.exe", "Research papers", now, now + timedelta(minutes=30), project_tag="Research")
    repo.create_task("Read paper", project_tag="Research")
    repo.create_note("Key findings note", project_tag="Research")

    # 3. Perform rename
    success = repo.rename_project("Research", "Browsing", color="#06B6D4", keywords=["zen", "browse", "web"])
    assert success is True

    # 4. Verify projects table
    all_projs = repo.get_all_projects(force_refresh=True)
    names = [p.name for p in all_projs]
    assert "Browsing" in names
    assert "Research" not in names

    brw_proj = next(p for p in all_projs if p.name == "Browsing")
    assert brw_proj.color == "#06B6D4"
    assert "web" in brw_proj.keywords

    # 5. Verify cascading to sessions, tasks, notes
    with repo.db.cursor() as cur:
        cur.execute("SELECT project_tag FROM sessions")
        sess_tags = [r["project_tag"] for r in cur.fetchall()]
        assert sess_tags == ["Browsing"]

        cur.execute("SELECT project_tag FROM tasks")
        task_tags = [r["project_tag"] for r in cur.fetchall()]
        assert task_tags == ["Browsing"]

        cur.execute("SELECT project_tag FROM notes")
        note_tags = [r["project_tag"] for r in cur.fetchall()]
        assert note_tags == ["Browsing"]


def test_rename_project_merges_duplicate_target(repo):
    """Verify that renaming into an existing project merges sessions/tasks without duplication."""
    # Create both old and new (the duplication scenario reported by the user)
    repo.create_or_update_project("Research", ["zen"], color="#E11D48", description="Old research")
    repo.create_or_update_project("Browsing", ["zen", "web"], color="#FF6B3D", description="")

    now = datetime(2026, 9, 1, 10, 0, 0)
    repo.log_session("zen.exe", "Research work", now, now + timedelta(minutes=15), project_tag="Research")
    repo.log_session("zen.exe", "Browsing news", now + timedelta(minutes=20), now + timedelta(minutes=35), project_tag="Browsing")

    # Rename Research -> Browsing (merge)
    success = repo.rename_project("Research", "Browsing", color="#E11D48")
    assert success is True

    projs = repo.get_all_projects(force_refresh=True)
    assert len(projs) == 1
    assert projs[0].name == "Browsing"
    assert projs[0].color == "#E11D48"

    with repo.db.cursor() as cur:
        cur.execute("SELECT project_tag FROM sessions")
        tags = [r["project_tag"] for r in cur.fetchall()]
        assert all(t == "Browsing" for t in tags)
        assert len(tags) == 2


def test_auto_color_selection_for_new_projects(repo):
    """Verify that multiple projects created without specifying colors receive distinct palette colors."""
    repo.create_or_update_project("Project1", ["kw1"])
    repo.create_or_update_project("Project2", ["kw2"])
    repo.create_or_update_project("Project3", ["kw3"])

    projs = repo.get_all_projects(force_refresh=True)
    colors = [p.color.upper() for p in projs]
    assert len(set(colors)) == 3, f"Expected 3 distinct colors, got: {colors}"
