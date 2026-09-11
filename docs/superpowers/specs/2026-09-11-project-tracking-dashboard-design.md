# Dedicated Project Tracking Dashboard: Technical Specification

## Overview

The Dedicated Project Tracking Dashboard introduces a centralized project performance hub into WizDesk. It aggregates auto-tracked application sessions, task completion progress, and keyword auto-tagging rules per project. 

The dashboard lives as a 4th mode inside the main WizDesk window header capsule (`[ Tasks ]` | `[ Quick Notes ]` | `[ Activity ]` | `[ Projects ]`), and employs an in-page drilldown architecture (Approach A: Overview Cards feed -> Detailed Project Hub) to keep navigation compact, fluid, and frameless without opening disruptive external windows.

---

## 1. User Interface Architecture

### 1.1 Header Mode Switcher Extension
In `QuickEntryDialog` (`wiz/ui/popup_dialog.py`):
- Extend the mode capsule layout from 3 buttons to 4 buttons:
  - `Tasks`: Daily tasks and subtasks list.
  - `Quick Notes`: Daily scratchpad notes.
  - `Activity`: Daily chronological session timeline.
  - `Projects`: Dedicated Project Tracking Dashboard.
- Button styling, active pill states, and keyboard/mouse accessibility remain identical to existing modes.
- Hosted on the primary `QStackedWidget` (`self.stack`) as index 3 (`self.project_dashboard_view`).

### 1.2 In-Page Drilldown Sub-Pages
`ProjectDashboardView` (`wiz/ui/project_dashboard_view.py`) manages a child `QStackedWidget` (`self.view_stack`):

#### Page 0: Projects Overview
1. **Toolbar Header**:
   - Section Title: "Projects".
   - `+ New Project` button: triggers an in-place modal or card form to create a project with a custom color and keyword list.
   - Timeframe filter chips: `[ Today ]` `[ This Week ]` `[ This Month ]` `[ All Time ]` with single-selection toggle behavior.
2. **Global Metrics Strip**:
   - Individual badges: `Active Projects: N`, `Total Tracked: Xh Ym`, `Tasks Completed: X / Y (Z%)`.
3. **Scrollable Project Cards List**:
   - Rendered inside a frameless `QScrollArea` (`ScrollBarAlwaysOff`).
   - Each project is presented as a `ProjectSummaryCard(QFrame)`:
     - Left: Project color dot/accent and project title.
     - Center: Formatted tracked time badge for the active timeframe.
     - Progress Bar: Custom compact progress bar displaying completed / total tasks with percentage text.
     - Right: Application tags chip list showing the top 2-3 applications used for this project.
     - Hover feedback: Subtle background tint change; click transitions to the Project Detail Page.
   - If no projects are found, renders an `EmptyStateCard` prompting the user to create their first project.

#### Page 1: Project Detail Hub
1. **Navigation Header**:
   - `< All Projects` back button: returns to the Overview Page with state preserved.
   - Project color pill indicator and project title.
   - Action controls: `Edit Project` (name, color, keywords) and `Delete Project` (with confirmation).
2. **Timeframe Selector**:
   - Synchronized `[ Today ]` `[ This Week ]` `[ This Month ]` `[ All Time ]` filter chips.
3. **Summary Badges**:
   - `Tracked Time: Xh Ym`, `Tasks: X completed (Y open)`, `Top App: AppName (Z%)`.
4. **Detail Sections**:
   - **Tasks Section**: List of all tasks tagged to this project, with status pills (`Task`, `In progress`, `Completed`, `Cancelled`) and completion toggles.
   - **App Breakdown Section**: Visual breakdown of active applications used under this project (name, duration, percentage).
   - **Keyword Auto-Tagging Rules**: Editable list of window title keywords assigned to this project.

---

## 2. Data Layer Extensions (`wiz/storage/models.py`)

Extend `StorageRepository` with dedicated aggregation queries:

### 2.1 `get_projects_overview_metrics(timeframe: str) -> List[Dict[str, Any]]`
- **Timeframe bounds**:
  - `today`: start of current day to end of day.
  - `this_week`: Monday 00:00 of current week to now.
  - `this_month`: 1st day of current month to now.
  - `all_time`: unbound (all historical sessions and tasks).
- **Returned Dictionary per Project**:
  - `project_id`: int
  - `project_name`: str
  - `color`: str (hex code)
  - `description`: str
  - `tracked_minutes`: float
  - `total_tasks`: int
  - `completed_tasks`: int
  - `completion_rate`: float (0.0 to 1.0)
  - `top_apps`: List[Tuple[str, float]] (app name and minutes)

### 2.2 `get_project_detail(project_name: str, timeframe: str) -> Dict[str, Any]`
- Returns comprehensive metrics for the selected project:
  - Time tracking breakdown by app.
  - Associated tasks and subtasks.
  - Associated keyword matching rules from `project_keywords`.

### 2.3 `create_project_with_keywords(name: str, color: str, description: str, keywords: List[str]) -> int`
- Transactionally inserts the project into `projects` table and inserts rows into `project_keywords` table.
- Invalidates the project cache in `StorageRepository`.

---

## 3. Theming & Design Consistency

- **Dark Mode**:
  - Main background: `#18181B`.
  - Card background: `#242427`.
  - Card border: `#3F3F46`.
  - Text: Primary `#F4F4F6`, Secondary `#A1A1AA`.
  - Progress bar track: `#3F3F46`, fill: `#F4F4F6` or project accent color.
- **Light Mode**:
  - Main background: `#F7F5F0`.
  - Card background: `#FFFFFF`.
  - Card border: `#DCD6CA`.
  - Text: Primary `#111111`, Secondary `#666660`.
  - Progress bar track: `#EBE6DC`, fill: `#111111` or project accent color.
- **Micro-Interactions**:
  - Standard Windows cursor (`ArrowCursor`) across all surfaces.
  - `PointingHandCursor` strictly on clickable buttons and project cards.
  - Instant zero-flicker view swapping via `QStackedWidget`.

---

## 4. Verification Plan

### 4.1 Automated Tests (`tests/test_projects_dashboard.py`)
- Test storage queries for `today`, `this_week`, `this_month`, and `all_time`.
- Test project metric calculations (tracked minutes, task completion rates, top apps).
- Test UI view mode switching to `Projects` in `QuickEntryDialog`.
- Test overview card generation and empty state handling.
- Test drilldown navigation: selecting a card opens detail, back button returns to overview.
- Test in-place project creation and keyword rule editing.
- Test light and dark theme styling changes.

### 4.2 Manual / Visual Verification
- Verify that 4 header mode pills fit cleanly without truncation or overflow at default 640px window width.
- Verify progress bars render crisply with proper colors in both Light and Dark themes.
- Confirm mouse cursor remains standard Windows arrow cursor throughout.
