# Task Stopwatch and Status Synchronization Design Specification

## 1. Overview and Problem Statement

In WizDesk v1.2.0, the task active stopwatch was introduced to track real-time work duration. However, the task status (`not_started`, `in_progress`, `done`, `cancelled`) and the stopwatch state (`timer_started_at`, `duration_seconds`) currently operate in loose coupling:
- Changing a task's status dropdown to **"In Progress"** does not automatically start the stopwatch.
- Re-opening a completed task does not cleanly resume stopwatch time accumulation without manual button toggling.
- If the application is closed or the computer is powered off while a task is in progress, the accrued work time must be paused safely, and upon relaunch, the task must remain in progress with its accumulated time intact, ready to resume without accumulating idle/offline hours.

This specification defines the synchronized state machine between task status and stopwatch tracking, automatic lifecycle persistence, and crash/shutdown protection.

---

## 2. Core Architecture & State Machine

The single source of truth for task status transitions is centralized in `StorageRepository.update_task_status(task_id, new_status, ...)`. Every view (Task list in `popup_dialog.py`, Calendar in `calendar_view.py`, and quick entry bars) routes status updates through this method.

### 2.1 State Transition Matrix

| Action / Trigger | Previous State | Target State | `timer_started_at` Action | `duration_seconds` Action | `completed_at` Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Select "In Progress" / Uncheck to In Progress | `not_started`, `done`, or `cancelled` | `in_progress` | Set to `datetime.now()` (if not already running) | **Preserved intact**; future ticking accumulates on top | Cleared to `NULL` |
| Select "Completed" / Check checkbox | `in_progress` (running) | `done` | Flushed & cleared to `NULL` | `duration_seconds += (now - started_at)` | Set to `datetime.now()` |
| Select "Completed" / Check checkbox | `in_progress` (paused) or `not_started` | `done` | Kept `NULL` | Preserved intact | Set to `datetime.now()` |
| Select "Not Started" | `in_progress` (running) | `not_started` | Flushed & cleared to `NULL` | `duration_seconds += (now - started_at)` | Cleared to `NULL` |
| Select "Cancelled" | `in_progress` (running) | `cancelled` | Flushed & cleared to `NULL` | `duration_seconds += (now - started_at)` | Set to `datetime.now()` |
| Click Stopwatch **Play** | Any (with stopwatch paused) | `in_progress` | Set to `datetime.now()` | Preserved intact | Cleared to `NULL` |
| Click Stopwatch **Pause** | `in_progress` (running) | `in_progress` | Flushed & cleared to `NULL` | `duration_seconds += (now - started_at)` | Kept `NULL` |

### 2.2 Continuity for Re-opened Completed Work
When a user re-opens a completed task (e.g., changes status back to `in_progress` or unchecks the completion box to resume work):
1. `duration_seconds` is **strictly preserved** (never reset to 0).
2. `completed_at` and `last_completed_date` are reset to `NULL`.
3. `timer_started_at` is initialized to `datetime.now()`.
4. The stopwatch live display begins counting upwards immediately from the previously logged total.

---

## 3. Application Lifecycle, Shutdown & Crash Recovery

### 3.1 Graceful Application Shutdown (`__main__.py: quit()`)
When WizDesk is closed cleanly via tray icon or window quit:
1. `StorageRepository.flush_all_running_stopwatches()` executes:
   - Queries all tasks where `timer_started_at IS NOT NULL`.
   - Computes `delta = int((now - started_at).total_seconds())`.
   - Updates `duration_seconds = duration_seconds + max(0, delta)` and `timer_started_at = NULL`.
   - **Crucial**: The task's `status` remains `'in_progress'`.
2. **Next Startup Behavior**:
   - The task loads with `status = 'in_progress'`.
   - It shows its full accumulated duration (e.g. `1h 42m`).
   - The stopwatch is paused (`timer_started_at` is `None`), awaiting the user to resume work by clicking Play.

### 3.2 60-Second Periodic Safety Heartbeat
To protect against sudden power loss, forced reboots, or task termination:
- A lightweight timer (every 60 seconds) in the background checks for any task with `timer_started_at IS NOT NULL`.
- For each running task:
  - Adds the elapsed delta since `timer_started_at` into `duration_seconds`.
  - Resets `timer_started_at = datetime.now()`.
- **Guarantee**: If a sudden crash occurs, at most 60 seconds of uncommitted work time can ever be lost.

### 3.3 Startup Recovery Sweep (Anti-Sleep/Anti-Crash Drift)
During application startup in `StorageRepository.__init__`:
- The repository checks if any tasks in SQLite have a dangling `timer_started_at IS NOT NULL` (which only happens if the process was terminated without a clean shutdown).
- It retrieves the `end_time` of the most recent tracked window session from the `sessions` table (representing the moment user activity on the PC actually ended before crash or power cut).
- If the difference between `now` and `timer_started_at` exceeds normal limits (e.g. overnight sleep or days of shutdown):
  - The delta is capped to `max(0, (last_session_time - timer_started_at))`.
  - That legitimate delta is added to `duration_seconds`.
  - `timer_started_at` is set to `NULL`.
- Status remains `in_progress`. This guarantees users will never see false 24+ hour time accumulations due to machine sleep.

---

## 4. UI Components & Synchronization

### 4.1 Task Row Component (`TaskRowWidget` in `wiz/ui/popup_dialog.py`)
- **Status Dropdown Change (`_on_status_combo_changed`)**:
  - Automatically triggers `repo.update_task_status(self.task_id, new_status)`.
  - Calls `self.stopwatch_btn.refresh()` to update the button's internal state.
  - If status is `in_progress`: starts the live 1-second ticker, flips icon to Pause, and displays the ticking timer label.
  - If status is `done`, `not_started`, or `cancelled`: stops the ticker and reflects the final duration.
- **Checkbox Toggle (`_on_checkbox_toggled`)**:
  - Checking the box sets status to `done`, stops the stopwatch, and records completed duration.
  - Unchecking the box sets status to `in_progress` (if previously completed), resuming the stopwatch.
- **Stopwatch Button Click (`TaskStopwatchButton._toggle_stopwatch`)**:
  - Clicking Play starts the stopwatch and automatically updates the status dropdown to "In Progress".
  - Clicking Pause commits elapsed seconds and keeps the status dropdown on "In Progress".

### 4.2 Cross-View Event Broadcasting
- All status and stopwatch toggles emit `app_signals.task_updated.emit(task_id)` and `status_toggled.emit(task_id, status)`.
- Calendar agenda rows, task lists, and overview cards re-read the updated status and duration without requiring full view re-instantiation.

---

## 5. Verification & Testing Plan

### 5.1 Automated Unit Tests (`tests/test_stopwatch_sync.py`)
1. **Status to `in_progress` Starts Timer**:
   - Create task with status `not_started`.
   - Update status to `in_progress`.
   - Assert `task.status == 'in_progress'` and `task.timer_started_at is not None`.
2. **Status to `done` Commits Duration & Stops Timer**:
   - Start stopwatch on task, simulate 5 seconds elapsed.
   - Update status to `done`.
   - Assert `task.status == 'done'`, `task.timer_started_at is None`, and `task.duration_seconds >= 5`.
3. **Re-opening Completed Task Preserves Duration**:
   - Given a completed task with `duration_seconds = 300` (5 minutes).
   - Change status to `in_progress`.
   - Assert `task.duration_seconds == 300`, `task.completed_at is None`, and `task.timer_started_at is not None`.
4. **Status to `not_started` Stops Timer & Saves Delta**:
   - Given a running task with 10 seconds elapsed.
   - Change status to `not_started`.
   - Assert `task.timer_started_at is None` and `task.duration_seconds >= 10`.
5. **Clean Shutdown Persistence (`flush_all_running_stopwatches`)**:
   - Start stopwatch on two tasks.
   - Run `flush_all_running_stopwatches()`.
   - Assert both tasks retain `status == 'in_progress'`, `timer_started_at is None`, and durations increased by elapsed delta.
6. **Crash Recovery Sweep**:
   - Insert a task with `timer_started_at` set to 1 hour ago.
   - Run startup recovery with a known last session timestamp.
   - Verify duration is capped legitimately and `timer_started_at` cleared to `None`.
