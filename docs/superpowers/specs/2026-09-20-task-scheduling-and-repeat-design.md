# Task Scheduling, Deadlines, and Repeat Modes Design Specification

## 1. Overview and Goals
This specification defines the architecture, data models, business rules, and UI controls for adding **Task Scheduling**, **Deadlines (by date)**, and **Repeat Modes** to WizDesk, without introducing modal window clutter or disrupting the frictionless default task creation workflow.

### Key Objectives
- **Frictionless Defaults**: Typing a task and pressing Enter creates a standard task assigned to Today with no repeat rule. No extra manual clicks required.
- **Date-Only Scheduling & Deadlines**: Focus strictly on calendar dates (`YYYY-MM-DD`) without time-of-day complexity.
- **Repeat Modes**: Support `None`, `Daily`, `Weekdays` (Mon–Fri), and `Weekends` (Sat–Sun).
- **Rolling In-Place Reset (Vacation / Skip Resilient)**:
  - Completing a repeating task marks it as Done for today.
  - At midnight or upon next app launch, if `last_completed_date < today`, the task automatically resets to `not_started`.
  - If a user misses days or takes a vacation, the recurring task rolls forward to Today as `not_started` instead of creating redundant past clones.
- **Two Dedicated Filter Views**:
  - **`Upcoming`**: Lists all future scheduled tasks across coming dates.
  - **`Unfinished`**: Lists past incomplete tasks whose scheduled date has passed (overdue work).
- **In-Workspace UI Controls (No Popups)**:
  - Bottom Add Bar incorporates compact Schedule (`schedule.svg`) and Repeat (`repeat.svg`) icon buttons with upward dropdown selection boxes.
  - Existing task rows incorporate matching Schedule and Repeat action buttons next to the subtask icon for instant one-click updating.
- **Strict Zero-Emoji Policy**: Pure SVG vector icons, crisp typography, and subtle badge tokens.

---

## 2. Database Schema and Storage Layer

### 2.1 SQLite Schema Extensions
The `tasks` table is extended with three new columns:

```sql
ALTER TABLE tasks ADD COLUMN scheduled_date TEXT DEFAULT NULL;       -- ISO-8601 Date string: YYYY-MM-DD
ALTER TABLE tasks ADD COLUMN repeat_mode TEXT DEFAULT 'none';        -- 'none' | 'daily' | 'weekdays' | 'weekends'
ALTER TABLE tasks ADD COLUMN last_completed_date TEXT DEFAULT NULL;  -- ISO-8601 Date string: YYYY-MM-DD
```

Indexes are created for rapid query execution and filtering:
```sql
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_tasks_repeat_mode ON tasks(repeat_mode);
```

### 2.2 Dataclass Updates (`wiz/storage/models.py`)
`TaskRecord` is updated to include:
```python
@dataclass
class TaskRecord:
    id: Optional[int]
    title: str
    project_tag: Optional[str]
    status: str = "not_started"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    scheduled_date: Optional[date] = None
    repeat_mode: str = "none"  # 'none' | 'daily' | 'weekdays' | 'weekends'
    last_completed_date: Optional[date] = None
    subtasks: List[SubtaskRecord] = field(default_factory=list)
    task_logs: List[TaskLogRecord] = field(default_factory=list)

    @property
    def is_recurring(self) -> bool:
        return self.repeat_mode in ("daily", "weekdays", "weekends")

    def is_overdue(self, current_date: Optional[date] = None) -> bool:
        ref_date = current_date or date.today()
        task_date = self.scheduled_date or self.created_at.date()
        return (
            self.status not in ("done", "completed", "cancelled", "canceled")
            and task_date < ref_date
        )
```

---

## 3. Business Logic and Auto-Roll Engine

### 3.1 Date Matching in Daily View
When viewing a specific `target_date` (via the date navigator `< Date >`):
1. **Non-Recurring Tasks (`repeat_mode == 'none'`)**:
   - Displayed if `COALESCE(scheduled_date, created_at.date()) == target_date`.
2. **Recurring Tasks (`repeat_mode != 'none'`)**:
   - `daily`: Displayed on every date.
   - `weekdays`: Displayed if `target_date.weekday() < 5` (Monday through Friday).
   - `weekends`: Displayed if `target_date.weekday() >= 5` (Saturday and Sunday).

### 3.2 Vacation & Overnight Auto-Roll Logic (`StorageRepository.roll_recurring_tasks`)
A repository method runs at application startup and whenever the date advances:
- Iterates over all active tasks where `repeat_mode != 'none'`:
  - If `last_completed_date` is not `None` and `last_completed_date < today`:
    - Resets `status = 'not_started'`, `completed_at = NULL`.
  - If `scheduled_date` is in the past:
    - Automatically advances `scheduled_date = today` (or the next upcoming active weekday/weekend).
  - This ensures returning from a 2-week vacation presents a fresh "Today" list rather than 14 backlogged overdue copies.

### 3.3 Status Transitions on Checkbox Click
- **Completing a Recurring Task**:
  - Setting status to `'done'` records `completed_at = datetime.now()` and `last_completed_date = date.today()`.
  - The task remains checked off for the remainder of today.
- **Unchecking a Completed Task**:
  - Setting status back to `'not_started'` clears `completed_at` and `last_completed_date`.

---

## 4. Query Logic and New Filter Modes

### 4.1 Filter Bar Tabs (`TaskFilterBar`)
The filter bar is updated to include six status filters:
1. `Task` (All tasks for selected date)
2. `In Progress`
3. `Upcoming` *(New)*
4. `Unfinished` *(New)*
5. `Completed`
6. `Cancelled`

### 4.2 Query Behavior
- **`Upcoming` Filter Selected**:
  - Queries all incomplete tasks (`status NOT IN ('done', 'completed', 'cancelled')`) where:
    `scheduled_date > date.today()` OR `repeat_mode != 'none'`
  - Ordered chronologically by `scheduled_date ASC`.
  - In this mode, the date header container displays `"Upcoming Scheduled Tasks"` with an option to jump back to Today.
- **`Unfinished` Filter Selected**:
  - Queries all incomplete tasks whose scheduled date or creation date is before today:
    `COALESCE(scheduled_date, substr(created_at, 1, 10)) < today AND status NOT IN ('done', 'completed', 'cancelled')`
  - Ordered by date `ASC` (oldest overdue first) so overdue debt can be caught up or rescheduled.
  - In this mode, the date header displays `"Unfinished Tasks (Overdue)"`.

---

## 5. UI Architecture and Vector Controls

### 5.1 Bottom Add Task Bar Layout
The bottom input bar in `QuickEntryDialog` (`wiz/ui/popup_dialog.py`) is reorganized:

```
+---------------------------------------------------------------------------------------------------------+
| [ + Add task... (Press Enter) ] [ Project v ] [ 📅 Schedule ] [ 🔁 Repeat ] [ Add ]                     |
+---------------------------------------------------------------------------------------------------------+
```

- **Width Adjustments**:
  - `add_input`: `stretch=3` (responsive text entry).
  - `project_combo`: `stretch=1` (compact section choice).
  - `schedule_btn`: Fixed size `30x30px`, housing `assets/icons/schedule.svg`.
  - `repeat_btn`: Fixed size `30x30px`, housing `assets/icons/repeat.svg`.
  - `add_task_btn`: Compact action button `padding: 8px 16px`.

### 5.2 Dropdown Interactions (Upward-Opening, No Popups)
- **Schedule Button**:
  - Opens a styled `QMenu` directly above the button:
    - `Today` *(Default)*
    - `Tomorrow`
    - `Next Weekday`
    - `Pick Date...` *(Triggers a lightweight date selector dialog)*
    - `Clear Schedule`
  - **Active State**: When a future date is selected, the button turns brand orange (`#FF6B3D`) with a tooltip showing the scheduled date.
- **Repeat Button**:
  - Opens a styled `QMenu` directly above the button:
    - `None (One-time)` *(Default)*
    - `Daily (Every day)`
    - `Weekdays (Mon–Fri)`
    - `Weekends (Sat–Sun)`
  - **Active State**: When active, the button turns brand orange with a tooltip showing the repeat rule.
- **On Submit**:
  - The task is persisted with the selected `scheduled_date` and `repeat_mode`.
  - The bottom selectors immediately reset to `Today` and `None` for the next entry.

### 5.3 Task Card Rows
On each task item row, in addition to the existing subtask icon button on the right edge:
1. **Schedule Button / Badge (`schedule.svg`)**:
   - If scheduled for a future date, displays a subtle date pill (e.g. `Sep 25`).
   - If overdue (`is_overdue == True`), displays with warning amber/red badge styling (e.g. `Overdue · Sep 18`).
   - Clicking opens the schedule dropdown to reschedule or clear the date.
2. **Repeat Button / Badge (`repeat.svg`)**:
   - If recurring, displays the repeat icon with text label (e.g. `Daily` or `Weekdays`).
   - Clicking opens the repeat dropdown to change or clear the recurrence.
3. **Subtask Button (`subtask.svg` / `subttasks.svg`)**:
   - Preserves existing subtask drawer toggling.

---

## 6. Zero-Emoji Compliance
- Strictly enforces zero-emoji guidelines across all tooltips, labels, and badges:
  - Uses `assets/icons/schedule.svg` for scheduling.
  - Uses `assets/icons/repeat.svg` for recurring tasks.
  - Uses `assets/icons/subtask.svg` for subtasks.
  - Uses clean text badges (e.g. `[Daily]`, `[Weekdays]`, `[Overdue · Sep 18]`).

---

## 7. Verification and Testing Plan

### 7.1 Automated Unit Tests
1. **Schema & Models Test (`tests/test_storage.py`)**:
   - Verify `scheduled_date`, `repeat_mode`, `last_completed_date` persistence and retrieval.
   - Verify `is_recurring` and `is_overdue` helper properties.
2. **Auto-Roll & Vacation Test**:
   - Verify that completed recurring tasks reset to `not_started` on the next day.
   - Verify that multi-day gap (vacation) rolls forward cleanly to today.
3. **Filter Query Tests**:
   - Verify `Upcoming` filter returns future tasks and recurring tasks.
   - Verify `Unfinished` filter returns incomplete past-deadline tasks.
4. **UI Lifecycle Tests (`tests/test_sidebar_and_shell.py` & `tests/test_dialogs.py`)**:
   - Verify Schedule and Repeat dropdown menu actions.
   - Verify task card action button triggers and badge rendering.

### 7.2 Manual & Visual Verification
- Verify dark and light theme appearance of new bottom bar icons and task row badges using screenshot captures.
- Verify that keyboard-only flow (`Type task -> Press Enter`) still functions instantly for today's normal tasks.
