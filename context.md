# WIZ — Project Context & Living Knowledge Base

> **Single Source of Truth (SSOT)**: This document maintains full context, architectural decisions, data models, UI specifications, and active status for **Wiz**. It must be referenced and updated after every completed task or milestone.

---

## 1. Project Overview

- **Name**: Wiz
- **Description**: A lightweight, minimalist desktop companion/pet for Windows that floats on the screen, passively tracks work/app activity, captures manual notes and multi-step tasks, and syncs structured daily work logs directly into an Obsidian vault.
- **Author**: Gokul R
- **Repository**: [https://github.com/Lukog10/wiz](https://github.com/Lukog10/wiz)
- **Target Platform (MVP)**: Windows 10 / 11
- **Long-term Platform**: Cross-platform (Windows / macOS / Linux)

### 1.1 Core Problems Solved
1. **Time & Work Awareness**: Eliminates the "what did I actually do today?" question when juggling multiple personal, freelance, and learning projects.
2. **Low-Friction Logging**: Combines passive window auto-tracking (every 30 mins) with rapid manual note/task capture via a floating mascot or quick hotkey.
3. **Seamless Obsidian Integration**: Writes structured, clean Markdown daily logs directly into the user's Obsidian vault without manual export or copy-pasting.

---

## 2. Visual Identity & Mascot Specification

### 2.1 Mascot Design
- **Character**: Minimalist ghost mascot with a rounded dome head, straight sides, and a 4-wave dripping bottom edge.
- **Fill**: Ivory (`#F7F3EA`)
- **Stroke**: Solid black (`#111111`), 6px stroke-width, rounded join.
- **Drop Shadow**: Soft semi-transparent ellipse beneath the mascot creating a floating effect.
- **Base Assets Location**: `assets/` (Vector SVGs)

### 2.2 Companion States & Triggers

| State | Asset File | Visual Treatment | Trigger / Purpose |
|---|---|---|---|
| **Idle** | `assets/wiz-idle.svg` | Two solid black dot eyes | Default resting state when inactive or between tracker polls. |
| **Working** | `assets/wiz-working.svg` | Two grey dashed loading-spinner ring eyes (rotated dynamically via Qt transform/timer) | Active during user activity in a tracked app / background poll. |
| **Notify** | `assets/wiz-notify.svg` | One dash eye + one sparkle eye, small burst accents near head | Periodic gentle prompt nudging the user to log progress or notes. |
| **Complete** | `assets/wiz-complete.svg` | Inverted dark body (`#111111`), gradient stroke (`#FF5E7E` → `#FFAE33`), white dot eyes, sparkles | Triggered on note/task completion; celebratory flash. |
| **Sleep** | `assets/wiz-sleep.svg` | Dimmed opacity (55%), closed-dash eyes, "z" marks above head | Triggered after prolonged idle time or outside active hours. |

---

## 3. Technical Architecture & Tech Stack

```
┌────────────────────────────────────────────────────────┐
│                   Wiz Desktop App                      │
│                                                        │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │ Floating Mascot UI   │    │ System Tray & Menu   │  │
│  │ (Frameless PyQt6 SVG)│    │ (Show, Hide, Quit)   │  │
│  └──────────┬───────────┘    └──────────┬───────────┘  │
│             │                           │              │
│  ┌──────────▼───────────────────────────▼───────────┐  │
│  │ Quick-Entry Popup (Notes, Tasks & Subtasks)      │  │
│  └──────────────────────┬───────────────────────────┘  │
│                         │                              │
│  ┌──────────────────────▼───────────────────────────┐  │
│  │ State & Animation Controller                     │  │
│  │ (Idle / Working / Notify / Complete / Sleep)     │  │
│  └──────────────────────┬───────────────────────────┘  │
└─────────────────────────┼──────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                 │
┌────────▼────────────────┐       ┌────────▼────────────────┐
│ Auto-Tracker Service    │       │ Global Hotkey Listener  │
│ (pywin32 / psutil poll) │       │ (pynput)                │
└────────┬────────────────┘       └────────┬────────────────┘
         │                                 │
         └────────────────┬────────────────┘
                          ▼
             ┌─────────────────────────┐
             │ SQLite Database Buffer  │
             │ (wiz.db)                │
             └────────────┬────────────┘
                          │ (batched write)
                          ▼
             ┌─────────────────────────┐
             │ Obsidian Vault Sync     │
             │ /Wiz Logs/YYYY-MM-DD.md │
             └─────────────────────────┘
```

### 3.1 Stack Details
- **Language**: Python 3.14 (`.venv`)
- **GUI & Animations**: PyQt6 (`QtWidgets`, `QtCore`, `QtGui`, `QtSvg`, `QtSvgWidgets`)
  - Frameless, transparent, draggable, always-on-top window.
  - Smooth property animations (`QPropertyAnimation`) for float bobbing and state transitions.
- **Windows System APIs**: `pywin32` (`win32gui`, `win32process`), `psutil` for window handle tracking and executable name resolution.
- **Global Hotkey Capture**: `pynput` for invoking the quick-entry popup from anywhere.
- **Database / Buffer**: SQLite3 (`wiz.db`) for resilient local offline caching.
- **Obsidian Sync**: Direct atomic Markdown file I/O with formatted templates.
- **Testing**: `pytest`

---

## 4. SQLite Database Schema

```sql
-- Tracked active application sessions (every 30m poll or transition)
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name TEXT NOT NULL,
    window_title TEXT,
    project_tag TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL
);

-- Flat quick notes
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    project_tag TEXT,
    created_at DATETIME NOT NULL,
    is_completed BOOLEAN DEFAULT 0
);

-- Structured parent tasks
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    project_tag TEXT,
    status TEXT DEFAULT 'not_started',  -- 'not_started' | 'in_progress' | 'done'
    created_at DATETIME NOT NULL,
    completed_at DATETIME
);

-- Subtasks belonging to a task
CREATE TABLE IF NOT EXISTS subtasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'not_started',  -- 'not_started' | 'in_progress' | 'done'
    created_at DATETIME NOT NULL,
    completed_at DATETIME
);

-- Running timestamped log entries on tasks or subtasks
CREATE TABLE IF NOT EXISTS task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    subtask_id INTEGER REFERENCES subtasks(id) ON DELETE CASCADE,  -- NULL = log on task itself
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL
);

-- Project keyword matching configuration
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    keywords TEXT  -- comma-separated keywords e.g. "TurfLine,turfline,booking"
);

-- General App Settings / Config
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## 5. Obsidian Sync & Daily Log Format

Daily logs are stored inside the configured Obsidian Vault path under the `/Wiz Logs/` folder.
**Filename pattern**: `/Wiz Logs/YYYY-MM-DD.md`

### 5.1 Format Template
```markdown
## YYYY-MM-DD

### Tasks
- [ ] Build TurfLine booking flow
  - [x] Design booking UI
  - [~] Wire up backend API
    - 10:15 — hit CORS issue, debugging
    - 11:40 — fixed, testing now
  - [ ] Write tests

### Auto-tracked
- 09:00–09:30 — VS Code (TurfLine)
- 09:30–10:00 — Chrome (research)

### Notes
- [x] Fixed booking bug in TurfLine ✅ 10:15
- [ ] Draft resume for ML role
```

---

## 6. Implementation Roadmap & Milestones

| Milestone | Feature / Component | Status | Key Deliverables |
|---|---|---|---|
| **M0** | **Environment & Project Setup** | **COMPLETED** | Virtualenv `.venv`, installed PyQt6, pywin32, psutil, pynput, pytest, verified imports, created `requirements.txt` & `context.md`. |
| **M1** | **Floating Mascot Shell & Tray** | **COMPLETED** | Frameless transparent PyQt6 mascot window, draggable, system tray menu (Show/Hide/Settings/Quit), floating bob animation (`wiz/ui/mascot_window.py`, `wiz/ui/mascot_widget.py`, `wiz/ui/tray_icon.py`). |
| **M2** | **SQLite Buffer & Repositories** | **COMPLETED** | `db.py` initialization, schema migrations, CRUD operations for sessions, notes, tasks, subtasks, task_logs, projects (`wiz/storage/db.py`, `wiz/storage/models.py`). |
| **M3** | **Active Window Auto-Tracker** | **COMPLETED** | Background worker thread polling active window/process every 30m, matching project keywords, storing session intervals (`wiz/tracker/window_tracker.py`). |
| **M4** | **Quick-Entry Popup & Task UI** | **COMPLETED** | Hotkey-activated dialog for quick note capture, task/subtask creation, status toggling, and timestamped log trails (`wiz/ui/popup_dialog.py`). |
| **M5** | **State Machine & Face Animations** | **COMPLETED** | Dynamic mascot state switcher (`idle`, `working`, `notify`, `complete`, `sleep`), rotating spinner eye animation for working state (`wiz/core/state_machine.py`, `wiz/ui/mascot_widget.py`). |
| **M6** | **Obsidian Vault Sync Engine** | **COMPLETED** | Markdown generator, atomic batched file writing to `/Wiz Logs/YYYY-MM-DD.md`, vault path selector dialog (`wiz/sync/obsidian.py`). |
| **M7** | **Project Mapping & Settings UI** | **COMPLETED** | Settings window for keyword rules, poll intervals, hotkey configs, and notification cadence (`wiz/ui/settings_dialog.py`, `wiz/utils/hotkey.py`). |

---

## 7. Maintenance & Context Update Rules

1. **Keep Updated**: Every agent modifying or extending the codebase must update this `context.md` file upon task completion.
2. **Schema Integrity**: Any database changes must be reflected in Section 4.
3. **Milestone Tracking**: Progress in Section 6 must be updated from *PENDING* to *IN PROGRESS* to *COMPLETED*.
4. **Zero-Truncation Policy**: All documentation and code must be complete, functional, and free of placeholder stubs.
