# Design Specification: Startup Splash Screen & Workspace Loading Transition

**Date**: 2026-09-25  
**Author**: DeepMind Antigravity / Pair Programming Agent  
**Status**: Approved by User  
**Spec Location**: `docs/superpowers/specs/2026-09-25-splash-screen-design.md`

---

## 1. Overview & Goals

WizDesk is a minimalist, local-first productivity companion. As the application initializes on startup, it performs several asynchronous steps including connecting to SQLite, verifying/decrypting the database, starting the background window tracker, loading the tray icon, and spawning the desktop companion.

To provide a refined open-source desktop experience, this update introduces:
1. **Startup Splash Screen (`SplashScreen`)**: A standalone, frameless, centered card displayed on application launch. It presents real-time initialization progress, holds for a minimum duration to eliminate jarring visual flicker, and fades out cleanly into the active desktop companion.
2. **Workspace Loading Transition (`WorkspaceSplashOverlay`)**: An integrated loading overlay within the 920x680 workspace window (`QuickEntryDialog`). When summoned for the first time, it provides a smooth, cross-fading loading card while tasks, calendar, notes, and project views populate.

---

## 2. Startup Splash Screen Component (`wiz/ui/splash_screen.py`)

### 2.1 Window Configuration & Geometry
- **Class**: `SplashScreen(QWidget)`
- **Window Flags**: `Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen`
- **Widget Attributes**: `Qt.WidgetAttribute.WA_TranslucentBackground`, `Qt.WidgetAttribute.WA_DeleteOnClose`
- **Fixed Dimensions**: 460px width by 280px height.
- **Centering**: Dynamically positioned at the center of the primary screen via `QScreen.availableGeometry()`.

### 2.2 Visual Hierarchy & Styling
- **Background & Border**:
  - Dark Theme: `#16161A` background, `1px solid #27272A` border, 20px rounded corners, ambient drop shadow.
  - Light Theme: `#FFFFFF` background, `1px solid #D8D8DE` border, 20px rounded corners, soft shadow.
- **Header**:
  - Centered Wiz mascot or logo icon (64x64px).
  - App Title: "WizDesk" (18pt bold font, `#F4F4F5` in dark, `#18181B` in light). No subtitle.
- **Progress Section**:
  - Dynamic status label: Single-line status readout (9pt medium, `#A1A1AA` in dark, `#71717A` in light).
  - Progress bar: 4px height, 2px radius, track `#27272A`, progress bar accent `#FF6B3D` (terracotta brand accent).
- **Footer**:
  - Subtle version indicator: "v1.0.0" (8pt muted text).

### 2.3 Status Milestones
During startup in `wiz/__main__.py`, `SplashScreen.set_progress(value: int, text: str)` updates the UI:
- `0%`: "Starting WizDesk..."
- `25%`: "Loading local database..."
- `55%`: "Starting background tracker..."
- `80%`: "Preparing desktop companion..."
- `100%`: "Ready"

### 2.4 Hold & Fade-Out Lifecyle
- **Minimum Display Time**: A hold timer enforces a minimum display of 1.2 seconds, preventing rapid flicker on high-performance machines.
- **Fade Animation**: `QPropertyAnimation` animates `windowOpacity` from 1.0 to 0.0 over 300ms.
- **Close & Cleanup**: Upon animation completion, `SplashScreen.close()` is invoked, handing off smoothly to `MascotWindow` and `TrayIcon`.

---

## 3. Workspace Loading Transition (`wiz/ui/popup_dialog.py`)

### 3.1 Component Structure
Inside `QuickEntryDialog`, a dedicated `WorkspaceSplashOverlay(QWidget)` is placed over the central canvas:
- **Geometry**: Aligned to match the central view container or fill the workspace dialog area.
- **Visuals**: Frameless card with mascot icon (40x40px), "Loading workspace..." label (10pt medium), and animated terracotta progress indicator.
- **Lifecycle**:
  - Shows when the workspace is opened for the first time.
  - Holds briefly (~350ms to 400ms) while tasks, subtasks, notes, and calendar items load.
  - Fades out via `QGraphicsOpacityEffect` and `QPropertyAnimation` over 200ms, cleanly revealing the populated workspace.

---

## 4. Application Startup Integration (`wiz/__main__.py`)

The startup sequence in `WizApplication`:
1. Instantiates `SplashScreen` and calls `splash.show()`.
2. Emits progress at `0%` ("Starting WizDesk...").
3. Connects to SQLite repository and runs integrity checks (`25%`, "Loading local database...").
4. Spawns `WindowTracker` (`55%`, "Starting background tracker...").
5. Prepares `MascotWindow` and `TrayIcon` (`80%`, "Preparing desktop companion...").
6. Emits `100%` ("Ready").
7. Triggers `splash.finish()` which honors the minimum hold time, fades out, and reveals the mascot.

---

## 5. Automated Verification & Test Strategy

### 5.1 New Tests (`tests/test_splash_screen.py`)
1. **Instantiation**: Validates frameless flags, dimensions (460x280), translucency attribute, and child widgets (logo, title, progress bar, status label).
2. **Progress Stepping**: Validates `set_progress(50, "Loading local database...")` updates progress bar value to 50 and label text accurately.
3. **Fade-Out Animation**: Tests that `finish()` initializes `QPropertyAnimation` and closes the widget upon completion.
4. **Theme Support**: Verifies dark and light theme styles apply correctly.

### 5.2 Regression Verification
- All 116 existing tests across tasks, calendar, timeline, crypto, backups, and shell views must pass with 0 regressions.
