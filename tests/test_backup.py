"""Unit tests for WizDesk database snapshot backups, rolling retention, and restoration."""

import pytest
from pathlib import Path

from wiz.core.crypto import CryptoManager, crypto_manager
from wiz.storage.backup import BackupManager
from wiz.storage.db import Database
from wiz.storage.models import StorageRepository


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_wiz.db"
    db = Database(db_file)
    repo = StorageRepository(db)
    # Populate test data
    repo.create_task("Test Task A", "proj1")
    repo.create_task("Test Task B", "proj2")
    repo.create_note("Quick test note", "proj1")
    return db, repo


def test_create_and_list_plaintext_backup(tmp_path, test_db):
    db, repo = test_db
    backup_dir = tmp_path / "backups"
    bm = BackupManager(backup_dir=backup_dir)

    bak_path = bm.create_backup(db, tag="manual", encrypt=False)
    assert bak_path.is_file()
    assert bak_path.suffix == ".bak"

    backups = bm.list_backups()
    assert len(backups) == 1
    assert backups[0]["filename"] == bak_path.name
    assert not backups[0]["is_encrypted"]
    assert backups[0]["tag"] == "manual"


def test_create_and_restore_encrypted_backup(tmp_path, test_db):
    db, repo = test_db
    # Ensure master key is available
    key = CryptoManager.generate_key()
    crypto_manager.store_key_dpapi(key)

    backup_dir = tmp_path / "backups"
    bm = BackupManager(backup_dir=backup_dir)

    wbak_path = bm.create_backup(db, tag="manual", encrypt=True)
    assert wbak_path.is_file()
    assert wbak_path.suffix == ".wbak"

    backups = bm.list_backups()
    assert len(backups) == 1
    assert backups[0]["is_encrypted"]

    # Delete all tasks in the current database
    tasks = repo.get_task_hierarchy()
    assert len(tasks) == 2
    for t in tasks:
        repo.delete_task(t.id)
    assert len(repo.get_task_hierarchy()) == 0

    # Restore from encrypted backup
    success = bm.restore_backup(wbak_path, db)
    assert success is True

    restored_tasks = repo.get_task_hierarchy()
    assert len(restored_tasks) == 2
    titles = {t.title for t in restored_tasks}
    assert titles == {"Test Task A", "Test Task B"}


def test_restore_corrupted_backup(tmp_path, test_db):
    db, repo = test_db
    corrupt_file = tmp_path / "corrupt.bak"
    corrupt_file.write_bytes(b"corrupt junk data that is not sqlite")

    bm = BackupManager(backup_dir=tmp_path / "backups")
    with pytest.raises(ValueError, match="not a valid SQLite database"):
        bm.restore_backup(corrupt_file, db)


def test_restore_missing_file(tmp_path, test_db):
    db, _ = test_db
    bm = BackupManager(backup_dir=tmp_path / "backups")
    with pytest.raises(FileNotFoundError):
        bm.restore_backup(tmp_path / "nonexistent.bak", db)


def test_auto_backup_rolling_retention(tmp_path, test_db):
    db, _ = test_db
    backup_dir = tmp_path / "backups"
    bm = BackupManager(backup_dir=backup_dir)

    # Create 3 manual backups
    bm.create_backup(db, tag="manual", encrypt=False)
    bm.create_backup(db, tag="manual", encrypt=False)
    bm.create_backup(db, tag="manual", encrypt=False)

    # Create 7 auto backups with artificial files
    for i in range(7):
        # We manually write dummy auto backup files with valid header
        f = backup_dir / f"wizdesk_backup_20260901_00000{i}_auto.bak"
        f.write_bytes(db.get_raw_sqlite_bytes())

    all_backups = bm.list_backups()
    assert len(all_backups) == 10

    # Clean keeping only 3 auto backups
    deleted = bm.clean_old_backups(keep_count=3)
    assert deleted == 4

    remaining = bm.list_backups()
    auto_remaining = [b for b in remaining if b["tag"] == "auto"]
    manual_remaining = [b for b in remaining if b["tag"] == "manual"]
    assert len(auto_remaining) == 3
    assert len(manual_remaining) == 3
