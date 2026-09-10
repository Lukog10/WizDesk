# Log Activity Timeline Design Specification

## 1. Overview
The Log Activity Timeline provides a unified, chronological view of auto-tracked application sessions alongside user task and note completions for any selected day. It is built directly into the existing WizDesk companion window, enabling quick navigation between task management and work history without adding desktop clutter.

---

## 2. User Interface and Navigation Architecture

### 2.1 View Switcher in Header
* Location: Embedded in `QuickEntryDialog` (`wiz/ui/popup_dialog.py`), directly below the title bar and date navigation strip.
* Control Type: Segmented button row (`QFrame`) with two selectable tabs:
  * `[ Tasks ]` (Default view: tasks, subtasks, notes)
  * `[ Activity ]` (Timeline view: chronological events and daily metrics)
* Mechanism: Controls a `QStackedWidget` containing:
  * Page 0: Existing task hierarchy and notes layout.
  * Page 1: New `TimelineView` widget (`wiz/ui/timeline_view.py`).
* Date Synchronization: The `< Date >` navigator remains visible across both views. Changing the date reloads the timeline data for that date immediately.

### 2.2 Top Metrics and Filter Bar
Positioned at the top of the `TimelineView`:
* Daily Summary Badges:
  * Total Tracked Time: Formatted as `Xh Ym` calculated by summing duration of all sessions for the day.
  * Tasks Finished: Count of tasks and subtasks marked completed on that date.
* Category Filter Chips:
  * `All` (displays both application activity and task milestones)
  * `Apps` (displays auto-tracked window sessions only)
  * `Tasks & Notes` (displays completed tasks, subtasks, and note entries only)
* Project Dropdown Filter:
  * Dropdown populated dynamically from active projects in the database.
  * Options: `All Projects`, followed by each known project tag, plus `Untagged`.
  * Selecting a project filters both app sessions and tasks having that project tag.

---

## 3. Data Processing and Aggregation Engine

### 3.1 Contiguous Session Merging
The background tracker captures foreground applications every 5 minutes, resulting in multiple small session records for continuous work.
* Algorithm: Runs in linear time $O(N)$ over all sessions for the selected day.
* Condition: Two adjacent sessions are merged if:
  1. `app_name` matches exactly.
  2. `project_tag` matches exactly.
  3. The time difference between the end of session $A$ and the start of session $B$ is 5 minutes or less.
* Output: A merged session object containing start time, end time, total duration in minutes, application name, project tag, and sample window titles.

### 3.2 Timeline Event Unification
Data sources are combined into a single sorted chronological sequence:
1. Merged app sessions: `start_time` used as primary sort key.
2. Completed tasks and subtasks: `completed_at` timestamp used as sort key.
3. Created notes: `created_at` timestamp used as sort key.
4. Ordering: Chronological from earliest to latest in the day.

---

## 4. Visual Components and Theming

### 4.1 Event Cards
1. App Activity Card:
   * Left Column: Time span (`09:00 - 10:15`) and duration (`1h 15m`).
   * Middle Column: Application name in primary bold font, window title snippet in secondary muted text.
   * Right Column: Project tag badge (`[TurfLine]` or `[General]`).
2. Task Milestone Card:
   * Left Column: Timestamp (`10:18`).
   * Indicator: Status badge (`[COMPLETED]`, `[NOTE]`).
   * Middle Column: Task or note title. If subtask, displays parent task name above it (`Parent: Task Title`).
   * Styling: Accent border indicating completion.
3. Empty State:
   * Mascot illustration centered in the view.
   * Text: "No activity recorded for this date."
   * Subtitle: "Active applications and completed tasks will appear here as you work."

### 4.2 Light and Dark Mode Color Palette
* Light Mode:
  * Window Background: `#F7F3EA`
  * Card Background: `#FFFFFF`
  * Card Border: `#E2DDD2`
  * Primary Text: `#111111`
  * Secondary Text: `#666660`
  * Badge Background: `#EBE6DC`
* Dark Mode:
  * Window Background: `#18181B`
  * Card Background: `#242427`
  * Card Border: `#333338`
  * Primary Text: `#F4F4F6`
  * Secondary Text: `#A1A1AA`
  * Badge Background: `#2E2E33`

---

## 5. Storage Layer and Queries

### 5.1 New Methods in `StorageRepository` (`wiz/storage/models.py`)
1. `get_day_sessions(date_str: str) -> List[SessionRecord]`:
   * Retrieves all sessions where `start_time` begins with `date_str` (`YYYY-MM-DD`).
   * Query: `SELECT * FROM sessions WHERE start_time LIKE ? ORDER BY start_time ASC`
2. `get_day_completed_tasks(date_str: str) -> List[Dict[str, Any]]`:
   * Retrieves tasks and subtasks where `completed_at` starts with `date_str`.
3. `get_day_notes(date_str: str) -> List[NoteRecord]`:
   * Retrieves notes where `created_at` starts with `date_str`.

---

## 6. Testing and Verification Plan
1. Unit Tests (`tests/test_timeline.py`):
   * Test contiguous session merging with identical app and project.
   * Test session non-merging when app or project differs.
   * Test chronological event interleaving of sessions, tasks, and notes.
   * Test filtering by category (`All`, `Apps`, `Tasks & Notes`) and project tag.
   * Test total tracked time calculation.
2. UI Tests (`tests/test_dialogs.py`):
   * Test segmented switch switches between Tasks and Timeline views.
   * Test date changes reload timeline contents.
   * Test theme toggle applies light and dark styles to timeline components.
3. Regression Verification:
   * Ensure all 30 existing unit tests continue to pass with zero regressions.
