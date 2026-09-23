# Calendar Section and Task Filter Streamline Design Specification

## 1. Overview and Problem Statement

### 1.1 Problem
In the WizDesk workspace, the **Tasks** filter bar currently contains 6 pills: `Task`, `In progress`, `Upcoming`, `Unfinished`, `Completed`, and `Cancelled`. On standard window widths (especially when the sidebar is expanded), having 6 capsule buttons in a single horizontal bar feels cramped and visually congested. Furthermore, *Upcoming* (future scheduled tasks) and *Unfinished* (overdue scheduled tasks) represent temporal calendar queries rather than status filters, diluting the focus of the daily task view.

### 1.2 Solution
1. **Streamline the Tasks Filter Bar**: Reduce the filter options to **4 core status pills**:
   - `Task` (All active tasks for the day)
   - `In progress`
   - `Completed`
   - `Cancelled`
2. **Dedicated Calendar Section**: Create a standalone **Calendar** view accessible from the primary sidebar navigation (`SideNavBar`):
   - Uses the existing `assets/icons/schedule.svg` vector icon.
   - Employs a clean two-pane master-detail layout tailored for WizDesk's ~710px–840px content width.
   - **Left Pane (~240px)**: Compact month calendar grid with visual status dots (Orange for active, Emerald for completed) plus quick-jump filters (`Today`, `Upcoming (7 Days)`, `Overdue`).
   - **Right Pane (~470px–580px)**: Spacious agenda list showing scheduled tasks for the active date/filter, with inline task creation (`+ Add task for this day...`), inline status updates, section assignments, and reschedule actions.

---

## 2. Navigation & Shell Integration

### 2.1 Sidebar Navigation (`wiz/ui/sidebar_widget.py`)
- Add `"calendar"` to the sidebar pill definitions in `SideNavBar`:
  - **Pill Order**:
    1. `tasks` (Tasks)
    2. `calendar` (Calendar)
    3. `notes` (Quick Notes)
    4. `activity` (Activity)
    5. `projects` (Projects)
    6. *Lower section*: `settings` (Settings), `help` (Help & FAQ)
  - **Vector Icon**: Map `"calendar"` in `_SVG_ICON_MAP` to `"icons/schedule.svg"`.
  - **Badge Support**: Optionally show a count badge of today's scheduled tasks or overdue tasks.
  - **Collapsed State**: Collapses down to 44x40px icon pill with tooltip `"Calendar"`.

### 2.2 Shell Integration (`wiz/ui/popup_dialog.py`)
- Add `CalendarView` to the `QStackedWidget` in `QuickEntryDialog`.
- Register the view mode transition in `_set_view_mode(mode: str)`:
  - If `mode == "calendar"`, switch the stack index to the `CalendarView` instance and refresh its date data.

---

## 3. Tasks Filter Bar Streamline

### 3.1 Updated Capsule Filter (`wiz/ui/popup_dialog.py` -> `SegmentedFilterBar`)
- Replace the options list:
  ```python
  self.options = ["Task", "In progress", "Completed", "Cancelled"]
  ```
- Remove legacy filter branches for `"Upcoming"` and `"Unfinished"` in the task list query logic of `popup_dialog.py`.
- Resulting pill capsule bar has ample breathing room, larger click targets, and a cleaner visual hierarchy.

---

## 4. Calendar Section Architecture (`wiz/ui/calendar_view.py`)

### 4.1 Layout Overview
The `CalendarView` widget is divided horizontally into two panes using a `QHBoxLayout` with zero outer margins and a subtle vertical divider:

```
+-----------------------------------------------------------------------------------------------+
| CALENDAR VIEW                                                                                 |
+------------------------------------+----------------------------------------------------------+
| LEFT PANE: DATE NAVIGATOR (~240px) | RIGHT PANE: SCHEDULED AGENDA (~500px+)                   |
|                                    |                                                          |
| [ < ]  September 2026  [ > ]       | September 23, Wednesday • 3 tasks scheduled              |
|                                    |                                                          |
| Mo  Tu  We  Th  Fr  Sa  Su         | + Add task for this day... (Press Enter)     [Work v] [+]|
| 01  02  03  04  05  06  07         |                                                          |
| 08  09  10  11  12  13  14         | [ ] Finalize Q3 Report               [Open v] (10:00 AM) |
| 15  16  17  18  19  20  21         |     Schedule: Today • Work • [Repeat: None]              |
| 22  23  24  25  26  27  28         |                                                          |
|     *   *                          | [x] Team Standup Meeting        [Completed v] (09:00 AM) |
| 29  30                             |     Schedule: Today • Internal                           |
|                                    |                                                          |
| Quick Filters:                     | [ ] Database Schema Migration    [In progress v]         |
| [ Today ]                          |     Schedule: Today • Engineering                        |
| [ Upcoming (7 Days) ]              |                                                          |
| [ Overdue (2) ]                    |                                                          |
+------------------------------------+----------------------------------------------------------+
```

### 4.2 Left Pane Components
1. **Month Navigation Bar**:
   - `QPushButton` prev month (`<`) and next month (`>`).
   - `QLabel` displaying formatted month and year (e.g., `September 2026`).
2. **Interactive Month Grid (`MonthCalendarGridWidget`)**:
   - 7 weekday column headers (`Mo`, `Tu`, `We`, `Th`, `Fr`, `Sa`, `Su`).
   - Day cells with day number (`1`..`31`).
   - **Task Status Indicators**:
     - Below each day number, a small 4px accent dot:
       - **Orange (`#FF6B3D`)**: Day contains active or in-progress tasks.
       - **Emerald (`#10B981`)**: All tasks scheduled for that day are marked completed.
   - **Selection Highlight**: Selected day is surrounded by an accent pill or soft background highlight.
   - **Today Highlight**: Current date displays a subtle ring or bold accent number.
3. **Quick Shortcut Presets**:
   - Styled pill buttons under the calendar:
     - `Today`: Immediately selects today's date on the grid and displays today's agenda.
     - `Upcoming (7 Days)`: Switches right pane to a 7-day chronological agenda view.
     - `Overdue`: Switches right pane to all incomplete tasks with `scheduled_date < today`.

### 4.3 Right Pane Components
1. **Agenda Header**:
   - Formatted full date label (e.g. `September 23, Wednesday`).
   - Summary badge with scheduled task count.
2. **Inline Fast Task Creation**:
   - Input line: `+ Add task for this day... (Press Enter)`.
   - Section selector dropdown (`Work`, `Personal`, etc.).
   - On pressing Enter: Task is created immediately with `scheduled_date` set to the currently active calendar date.
3. **Task List Display**:
   - Uses the existing robust `TaskRowWidget` components.
   - Supports:
     - Checkbox toggle.
     - Status dropdown (`Open`, `In progress`, `Completed`, `Cancelled`).
     - Subtasks expansion and inline toggle.
     - Section tag change.
     - Reschedule button (opens calendar picker or sets new date).
4. **Empty State Display**:
   - Displayed when no tasks match the selected date or preset.
   - Styled cleanly with typography and zero emojis:
     - Heading: *"No Tasks Scheduled"*
     - Subtext: *"Click the input above to schedule a task for this date."*

---

## 5. Storage and Data Access

The `CalendarView` interacts with `StorageRepository` using existing and optimized queries:
1. **`get_tasks_by_scheduled_date(date: date) -> List[TaskRecord]`**: Fetches tasks scheduled for the active date.
2. **`get_scheduled_dates_in_month(year: int, month: int) -> Dict[str, str]`**: Returns a mapping of `{ "YYYY-MM-DD": "active" | "completed" }` to populate the calendar day dots efficiently in a single query.
3. **`get_upcoming_tasks(limit_days: int = 7) -> List[TaskRecord]`**: Fetches tasks scheduled within the next 7 days.
4. **`get_overdue_tasks() -> List[TaskRecord]`**: Fetches tasks where `scheduled_date < today` and `status != 'completed'` and `status != 'cancelled'`.

---

## 6. Visual Design & Theme Integration

- **Strict Zero-Emoji Policy**: Pure SVG vector icons (`assets/icons/schedule.svg`, `repeat.svg`, etc.) and typography.
- **Dark Theme Tokens**:
  - Background: `#18181B` / `#0F0F12`
  - Border / Divider: `#27272A`
  - Accent Highlight: `#FF6B3D`
  - Text Primary: `#FAFAFA`
  - Text Secondary: `#A1A1AA`
- **Light Theme Tokens**:
  - Background: `#FFFFFF` / `#F4F0E8`
  - Border / Divider: `#E4E4E7`
  - Accent Highlight: `#FF6B3D`
  - Text Primary: `#18181B`
  - Text Secondary: `#71717A`

---

## 7. Verification and Testing Plan

### 7.1 Automated Tests
- **`tests/test_calendar_view.py`**:
  - Test `CalendarView` initialization and dark/light mode toggle.
  - Test month navigation (`prev_month`, `next_month`).
  - Test date selection updates the agenda task query.
  - Test quick presets (`Today`, `Upcoming`, `Overdue`).
  - Test creating a task directly from the Calendar inline input assigns the active date.
- **`tests/test_sidebar_and_shell.py`**:
  - Test that `"calendar"` is present in `SideNavBar` pills.
  - Test clicking the `"calendar"` pill triggers the view switch signal.
  - Test that `SegmentedFilterBar` has exactly 4 options: `["Task", "In progress", "Completed", "Cancelled"]`.

### 7.2 Manual Verification
- Launch WizDesk via `.venv/scripts/python -m wiz`.
- Open Workspace Dialog.
- Verify the Tasks filter bar now has 4 clean pills.
- Click the new **Calendar** pill in the sidebar.
- Navigate months, pick dates, schedule tasks, and test the Upcoming and Overdue quick presets.
