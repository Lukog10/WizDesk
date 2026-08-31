# Product Requirements Document: Wiz

**Desktop Companion for Work Tracking & Project Logging**

| | |
|---|---|
| **Author** | Gokul R |
| **Status** | Draft — MVP Definition |
| **Platform (MVP)** | Windows |
| **Platform (Long-term)** | Cross-platform (Windows / macOS / Linux) |
| **Last Updated** | August 2026 |

---

## 1. Overview

**Wiz** is a desktop companion — a small animated mascot that lives on the user's screen — designed to help individuals track their work, log project activity, and stay aware of how their time is spent across tasks and projects. Wiz combines passive activity tracking with manual note-taking, surfaces that information through a friendly on-screen presence, and stores logs directly into the user's Obsidian vault for long-term reference.

### 1.1 Problem Statement

People juggling multiple projects (freelance work, personal projects, job applications, learning) often lose track of:
- What they actually worked on during a given day/week
- How much time was spent per project or app
- What tasks were completed vs. left open

Existing time trackers are either too heavyweight (enterprise tools), too passive (silent background loggers with no presence or engagement), or disconnected from the user's existing knowledge base (not integrated with note-taking tools like Obsidian).

### 1.2 Solution

Wiz sits on the desktop as a lightweight, expressive companion that:
- Passively tracks active application/window usage on a fixed interval
- Lets the user log manual notes on demand (task completed, blocker, idea)
- Reflects its current "state" (idle, working, notifying, celebrating, asleep) through mascot animation
- Writes structured logs directly into the user's Obsidian vault as daily notes

---

## 2. Goals & Non-Goals

### 2.1 Goals (MVP)
- Provide a persistent, non-intrusive on-screen presence (the Wiz mascot)
- Auto-track active window/application usage every 30 minutes
- Allow manual note logging via a quick-entry popup
- Animate the mascot to reflect current state (idle / working / notify / complete / sleep)
- Store all logs as Markdown directly into an Obsidian vault
- Run reliably on Windows as a lightweight background app

### 2.2 Non-Goals (MVP)
- Cross-platform support (macOS/Linux) — planned for a later phase
- Full desktop file/folder management features
- Cloud sync or multi-device support
- Team/multi-user collaboration features
- Deep project-management features (Gantt charts, kanban boards, etc.)

---

## 3. Target User

- Primary user: the developer/creator themself — someone managing multiple concurrent projects (e.g. personal ML projects, job applications, freelance work) who wants a lightweight, always-present way to know "what did I actually do today/this week."
- Secondary (future): other users who want a similarly lightweight, mascot-driven work tracker.

---

## 4. Core Features

### 4.1 Desktop Companion (Mascot UI)
- A small, floating, always-on-top window rendering the Wiz ghost mascot
- Draggable/repositionable on screen
- System tray icon for quick access (show/hide, quit, settings)
- Reflects current state via swappable mascot artwork (see Section 6: Design)

### 4.2 Activity Auto-Tracking
- Background thread polls the active window/application
- **Polling interval: every 30 minutes** (fixed for MVP; not real-time/continuous tracking)
- Each poll records: active app name, window title, timestamp
- Sessions are later mapped to a project via keyword/app-matching rules

### 4.3 Manual Note Logging
- Hybrid logging model: auto-tracking + manual notes together give the full picture
- Triggered via tray icon click or hotkey
- Quick-entry popup for logging what was just completed, a blocker, or a general note
- Notes can be tagged to a project and marked complete/incomplete

### 4.4 Task & Subtask Management
Manual entries aren't limited to flat notes — a single task can be broken down and tracked over time:
- Create a task (e.g. "Build TurfLine booking flow")
- Split it into subtasks at any point — up front or as work progresses
- Each task/subtask has a status: **not started / in progress / done**
- Append timestamped **log entries** to a task or a specific subtask — a running trail of updates ("hit CORS issue, debugging" → "fixed, testing now"), independent of marking something complete
- Task status can be inferred automatically once all subtasks are done, or set manually

This gives Wiz two complementary logging layers: the lightweight one-off **note** (Section 4.3) for quick capture, and the structured **task → subtask → log** hierarchy for anything that needs to be tracked over multiple sessions.

**Example flow:**
1. User creates a task: *"Frontend work"*
2. Adds subtasks as the work becomes clear: *"Build navbar"*, *"Style login page"*, *"Fix responsive layout"*
3. Starts working on *"Build navbar"* — status moves to **in progress**
4. Finishes it — manually marks that subtask **done**
5. Moves to the next subtask (*"Style login page"*) and repeats
6. Once all subtasks are done, the parent task *"Frontend work"* is marked **done** (auto-inferred or manual)

Each step above is a manual update from the user — Wiz doesn't guess subtask completion, it just makes logging each step fast (a couple of taps/clicks) and keeps the full history so the user can later see exactly what was done and when.

### 4.5 Project Tagging
- Simple keyword-based mapping (e.g. app/window title containing "TurfLine" → tagged to TurfLine project)
- Enables per-project time and task summaries later

### 4.6 Obsidian Sync (Log Storage)
- All logs (auto-tracked sessions + manual notes) are written directly into the user's **Obsidian vault**
- Format: one Markdown daily note per day (e.g. `/Wiz Logs/2026-08-21.md`), with auto-tracked sessions and notes appended under clear headings
- A local SQLite database acts as a working buffer/cache before batched writes to the vault — this avoids file-lock conflicts if Obsidian has the vault open, and speeds up internal queries for reporting

**Example log format:**
```markdown
## 2026-08-21

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

### 4.7 Companion States & Behavior
The mascot changes appearance to reflect what's happening:

| State | Trigger | Purpose |
|---|---|---|
| **Idle** | No active tracked window / between polls | Default resting state |
| **Working** | User active in a tracked app | Shows Wiz is "paying attention" (loading-style animated eyes) |
| **Notify** | Periodic check-in prompt | Gently prompts the user to log a note |
| **Complete** | A note/task marked done | Brief celebratory animation |
| **Sleep/Away** | Long idle period or after hours | Dimmed, low-attention state |

---

## 5. Technical Architecture

### 5.1 Stack (MVP — Windows)

| Layer | Technology |
|---|---|
| UI / floating companion window | PyQt6 / PySide6 (transparent, frameless, always-on-top) |
| Window/app activity tracking | `pywin32` (`win32gui`, `win32process`) + `psutil` |
| Local data buffer | SQLite (`sqlite3` / SQLAlchemy) |
| Vault sync | Direct Markdown file writes into Obsidian vault (via Obsidian CLI tooling or raw file I/O) |
| Companion animation | Static SVG/PNG state swaps + `QPropertyAnimation` for transitions (fade/bob/pulse) |
| Packaging | PyInstaller → single `.exe` |

### 5.2 System Flow

```
┌────────────────────────┐
│  Wiz Companion (UI)     │  ← floating mascot, tray icon
└───────────┬─────────────┘
            │
   ┌────────┴─────────┐
   │                   │
┌──▼───────┐    ┌──────▼──────┐
│ Auto-     │    │ Manual Note  │
│ Tracker   │    │ Input (popup)│
│ (30-min   │    │              │
│  interval)│    │              │
└──┬────────┘    └──────┬───────┘
   │                    │
   └─────────┬──────────┘
             │
    ┌────────▼─────────┐
    │ Local SQLite       │  ← working buffer (fast queries,
    │ (working buffer)   │     avoids vault file-lock conflicts)
    └────────┬───────────┘
             │ (batched write)
    ┌────────▼─────────┐
    │ Obsidian Vault      │
    │ /Wiz Logs/YYYY-MM-DD.md │
    └──────────────────────┘
```

### 5.3 Data Model (Starter Schema)

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    app_name TEXT,
    window_title TEXT,
    project_tag TEXT,
    start_time DATETIME,
    end_time DATETIME
);

CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    content TEXT,
    project_tag TEXT,
    created_at DATETIME,
    is_completed BOOLEAN DEFAULT 0
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT,
    project_tag TEXT,
    status TEXT DEFAULT 'not_started',  -- not_started | in_progress | done
    created_at DATETIME,
    completed_at DATETIME
);

CREATE TABLE subtasks (
    id INTEGER PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id),
    title TEXT,
    status TEXT DEFAULT 'not_started',
    created_at DATETIME,
    completed_at DATETIME
);

CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id),
    subtask_id INTEGER REFERENCES subtasks(id) NULL,  -- NULL = log on the task itself
    content TEXT,
    created_at DATETIME
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    keywords TEXT  -- comma-separated app/window match hints
);
```

---

## 6. Design

### 6.1 Mascot Concept
Wiz is represented as a minimalist ghost character — a flat-vector, rounded blob body with a wavy/dripping bottom edge. The design is intentionally simple: monochrome outline style, expressive purely through eye/face changes rather than complex animation, so it stays legible even at small (tray-icon) sizes.

### 6.2 Finalized Visual Style (v1, locked)
- **Body:** rounded dome top, straight sides, 4-wave dripping bottom edge
- **Fill:** ivory (#F7F3EA)
- **Outline:** solid black, bold stroke
- **Drop shadow:** soft ellipse beneath the mascot for a "floating" effect

### 6.3 State-Based Face Variants

| State | Visual Treatment |
|---|---|
| **Idle** | Two simple black dot eyes |
| **Working** | Two grey loading-spinner ring eyes (dashed circles, rotate via animation in-app) — signals active tracking |
| **Notify** | One dash + one sparkle eye, small attention-burst accents near the head |
| **Complete** | Inverted color scheme (dark body, gradient pink→orange outline), white dot eyes, sparkle accents — celebratory flash |
| **Sleep/Away** | Dimmed opacity (55%), closed-dash eyes, small "z" marks above the head |

### 6.4 Asset Format
- Delivered as SVG (vector, scales cleanly from tray-icon size up to full companion widget size)
- 5 state files: `wiz-idle.svg`, `wiz-working.svg`, `wiz-notify.svg`, `wiz-complete.svg`, `wiz-sleep.svg`
- Shared body path across all states — only eyes/accents/fill differ, keeping the character visually consistent
- In-app, the working state's spinner eyes should be given a subtle rotation animation (CSS/Qt transform) rather than shipped as a static image, to reinforce the "loading/tracking" feel

---

## 7. MVP Build Order

1. **Tray + always-on-top window shell** — static mascot image floating on screen, draggable, right-click tray menu (Show/Hide/Quit)
2. **SQLite schema + auto-tracker thread** — poll active window every 30 minutes, log session start/end
3. **Manual note popup** — hotkey/tray-triggered quick-entry dialog, saves to `notes` table
4. **Task & subtask management** — create tasks, break into subtasks, append running log entries per task/subtask, track status
5. **Animation states** — swap mascot art based on current state; add spinner rotation for "working"
6. **Obsidian sync module** — batched writer that appends buffered sessions/tasks/notes into the daily vault note
7. **Project tagging** — keyword-match config mapping apps/window titles to project names

---

## 8. Open Questions

- **Log format granularity:** one Markdown file per day (all projects mixed) vs. one note per project (each project accumulates its own log file)?
- **Notify cadence:** should the "log a note" nudge fire every auto-track cycle (30 min), or on a separate, less frequent schedule?
- **Hotkey scheme:** what global hotkey should open the manual note popup?
- **Vault path configuration:** how does the user point Wiz at their Obsidian vault on first run (manual path entry vs. auto-detect)?

---

## 9. Future Considerations (Post-MVP)

- Cross-platform support (macOS, Linux)
- Weekly/monthly summary reports (time per project, tasks completed) rendered as a dashboard
- Desktop management features (quick folder/repo launch, clutter cleanup)
- Deeper project auto-detection (beyond simple keyword matching)
- Optional cloud sync for multi-device use
