# Implementation Plan: Task Stopwatch & Status Synchronization

**Date**: 2026-10-09  
**Design Spec Reference**: [docs/superpowers/specs/2026-10-09-task-stopwatch-status-sync-design.md](file:///h:/Projects/Wiz/docs/superpowers/specs/2026-10-09-task-stopwatch-status-sync-design.md)  
**Status**: Ready for Phased Execution  

---

## 1. Context Lock-in

- **GOAL**: Synchronize task status and the active stopwatch so that:
  1. Setting status to `in_progress` starts the stopwatch, preserving any existing accumulated duration.
  2. Setting status to `done` stops the stopwatch and logs elapsed seconds into `duration_seconds`.
  3. Setting status to `not_started` or `cancelled` pauses the stopwatch and saves accumulated seconds.
  4. Re-opening a completed task to `in_progress` resumes stopwatch accumulation directly from previous work time.
  5. Closing the app or PC while in progress commits elapsed time; on next launch, the task remains `in_progress` with accumulated time preserved and paused until manually resumed.
  6. A 60-second periodic heartbeat and startup recovery sweep prevent false sleep/shutdown time drift.
- **FILES IMPACTED**:
  - `wiz/storage/models.py`: Centralized status transition state machine, periodic heartbeat flush, startup recovery sweep.
  - `wiz/__main__.py`: Startup crash recovery invocation, periodic 60s safety heartbeat timer, graceful quit flush.
  - `wiz/ui/popup_dialog.py`: UI synchronization between status dropdown, checkbox, and `TaskStopwatchButton`.
  - `wiz/ui/calendar_view.py`: Status update synchronization in calendar agenda rows.
  - `tests/test_stopwatch_sync.py`: New unit test suite verifying all state transitions, persistence, and recovery.
- **CONSTRAINTS**:
  - Zero double dashes and zero em-dashes in code and commits.
  - 100% test pass rate with zero regressions across entire test suite.

---

## 2. File Impact Analysis

| File | Nature of Change | Target Functionality | Verification |
| :--- | :--- | :--- | :--- |
| `wiz/storage/models.py` | Core state machine | `update_task_status`, `periodic_stopwatch_heartbeat`, `recover_dangling_stopwatches` | Pytest |
| `wiz/__main__.py` | App lifecycle integration | Startup recovery call, 60s safety heartbeat timer | Integration check |
| `wiz/ui/popup_dialog.py` | UI synchronization | `TaskRowWidget._on_status_combo_changed`, `_on_checkbox_toggled`, `TaskStopwatchButton` sync | UI & unit tests |
| `wiz/ui/calendar_view.py` | UI synchronization | Calendar agenda row status change synchronization | Unit tests |
| `tests/test_stopwatch_sync.py` | New test suite | Complete state machine, persistence, and recovery test suite | `pytest tests/test_stopwatch_sync.py` |

---

## 3. Phased Execution Tasks

### Phase 1: Storage State Machine & Lifecycle Persistence
- [ ] In `wiz/storage/models.py`, update `StorageRepository.update_task_status`:
  - When `new_status == 'in_progress'`:
    - If `timer_started_at` is None, set `timer_started_at = datetime.now().isoformat()`.
    - Preserve existing `duration_seconds`.
    - Clear `completed_at = NULL` and `last_completed_date = NULL`.
  - When `new_status in ('done', 'completed')`:
    - If `timer_started_at` is set, compute delta, add to `duration_seconds`, clear `timer_started_at = NULL`.
    - Stamp `completed_at` and `last_completed_date`.
  - When `new_status in ('not_started', 'cancelled')`:
    - If `timer_started_at` is set, compute delta, add to `duration_seconds`, clear `timer_started_at = NULL`.
    - Clear `completed_at = NULL`.
- [ ] In `wiz/storage/models.py`, add `periodic_stopwatch_heartbeat()`:
  - Commit running delta into `duration_seconds` for all active tasks and reset `timer_started_at = datetime.now()`.
- [ ] In `wiz/storage/models.py`, add `recover_dangling_stopwatches()`:
  - For tasks with dangling `timer_started_at` on startup, query the latest session `end_time` from `sessions`.
  - Cap delta to `(latest_session_end - timer_started_at)`, flush into `duration_seconds`, clear `timer_started_at = NULL`.
- [ ] In `wiz/__main__.py`:
  - Call `StorageRepository().recover_dangling_stopwatches()` during app startup.
  - Set up a 60-second `QTimer` invoking `StorageRepository().periodic_stopwatch_heartbeat()`.

### Phase 2: UI Row & Dropdown Synchronization
- [ ] In `wiz/ui/popup_dialog.py` (`TaskRowWidget`):
  - In `_on_status_combo_changed`:
    - Call `repo.update_task_status(self.task_id, new_status)`.
    - Synchronize `self.stopwatch_btn`: if `in_progress`, ensure ticking timer is active; if `done` or `not_started`, stop ticker and display formatted total.
  - In `_on_checkbox_toggled`:
    - If checking (done): update status to `done`, stop stopwatch.
    - If unchecking: update status to `in_progress` (if previously done) or `not_started`, syncing stopwatch.
  - In `TaskStopwatchButton._toggle_stopwatch`:
    - On Play: start stopwatch and update parent `TaskRowWidget.status_combo` to "In Progress".
    - On Pause: pause stopwatch and keep `status_combo` on "In Progress".
- [ ] In `wiz/ui/calendar_view.py`:
  - Ensure status toggle reflects into `repo.update_task_status` and refreshes task stopwatch state.

### Phase 3: Comprehensive Automated Tests
- [ ] Create `tests/test_stopwatch_sync.py`:
  - Test 1: Setting status to `in_progress` starts stopwatch and preserves past duration.
  - Test 2: Setting status to `done` stops stopwatch and flushes running delta into `duration_seconds`.
  - Test 3: Re-opening completed task to `in_progress` resumes stopwatch on top of existing duration.
  - Test 4: Setting status to `not_started` pauses stopwatch and preserves elapsed delta.
  - Test 5: Manual Play updates status to `in_progress`; Manual Pause preserves `in_progress` while committing delta.
  - Test 6: `flush_all_running_stopwatches()` leaves tasks `in_progress` and clears `timer_started_at`.
  - Test 7: `recover_dangling_stopwatches()` caps drift using last recorded session timestamp.
  - Test 8: `periodic_stopwatch_heartbeat()` commits delta without changing `timer_started_at` status.

### Phase 4: Full Test Suite & Verification
- [ ] Run full test suite: `pytest`
- [ ] Verify zero regressions across all existing tests.

### Phase 5: Git Commit & Handoff
- [ ] Commit working tree before handing off to user.
