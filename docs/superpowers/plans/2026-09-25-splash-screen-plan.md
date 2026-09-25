# Implementation Plan: Startup Splash Screen & Workspace Loading Transition

**Date**: 2026-09-25  
**Design Spec Reference**: [docs/superpowers/specs/2026-09-25-splash-screen-design.md](file:///h:/Projects/Wiz/docs/superpowers/specs/2026-09-25-splash-screen-design.md)  
**Status**: Ready for Execution  

---

## 1. Context Lock-in

- **TASK**: Implement a modern minimalist startup splash screen (`SplashScreen`) and an integrated workspace loading transition overlay (`WorkspaceSplashOverlay`) for WizDesk.
- **INPUTS**:
  - Application startup in `wiz/__main__.py`.
  - Database, tracker, and companion initialization steps.
  - Workspace summon (`Ctrl+Shift+W` or mascot double-click) in `QuickEntryDialog`.
  - Vector mascot asset `assets/wiz-idle.svg` and brand terracotta accent `#FF6B3D`.
- **OUTPUTS**:
  - New module `wiz/ui/splash_screen.py` containing `SplashScreen`.
  - New overlay class `WorkspaceSplashOverlay` in `wiz/ui/popup_dialog.py`.
  - Startup coordination in `wiz/__main__.py` with progress milestones and minimum 1.2s hold.
  - Comprehensive automated tests in `tests/test_splash_screen.py`.
- **CONSTRAINTS**:
  - Strict zero-emoji compliance across all UI text and labels.
  - Zero double dashes or em-dashes across all files.
  - No subtitle under the app title in the header section.
  - Do not use "Registering hotkeys..." status message.
  - 100% of existing tests (116 passing) must continue to pass with zero regressions.
- **SUCCESS CRITERIA**:
  - `SplashScreen` displays centered (460x280px) on app startup with mascot icon, "WizDesk" title, terracotta progress bar, and dynamic status messages.
  - Minimum 1.2-second display time avoids rapid flickering.
  - Smooth 300ms fade-out animation cleanly transitions to the desktop companion.
  - `WorkspaceSplashOverlay` displays on initial workspace summon and fades out smoothly after views load.
  - Full test suite passes without errors.

---

## 2. File Impact Analysis

| File | Purpose of Change | Verification Method |
| :--- | :--- | :--- |
| `wiz/ui/splash_screen.py` *(New)* | Frameless, centered startup splash card with progress bar, dynamic status text, and opacity animation. | `tests/test_splash_screen.py` |
| `wiz/ui/popup_dialog.py` | Add `WorkspaceSplashOverlay` component and show on initial workspace launch. | `pytest tests/test_dialogs.py` |
| `wiz/__main__.py` | Instantiate splash screen on launch, update progress milestones during initialization, call `finish()`. | Startup test / `python -m wiz` |
| `tests/test_splash_screen.py` *(New)* | Unit tests for splash screen geometry, progress milestones, fade-out animation, and workspace overlay. | `pytest tests/test_splash_screen.py` |

---

## 3. Incremental Execution Steps

### Phase 1: Create `SplashScreen` Component (`wiz/ui/splash_screen.py`)
- [ ] **Step 1.1**: Create `wiz/ui/splash_screen.py` defining `SplashScreen(QWidget)`:
  - Frameless, stays on top, splash screen flags, translucent background.
  - 460x280px fixed geometry, centered on current screen.
  - Dark/light styling: `#16161A` / `#FFFFFF` background, 20px radius, 1px border.
  - Mascot logo (64x64px), "WizDesk" title (18pt bold font sans, no subtitle).
  - Terracotta progress bar (4px height, `#FF6B3D` accent) and dynamic status label (9pt medium).
  - Version footer: "v1.0.0".
  - `set_progress(value: int, text: str)` method.
  - `finish()` method with minimum 1.2s hold timer and 300ms `QPropertyAnimation` on `windowOpacity`.
- [ ] **Step 1.2**: Write initial unit tests in `tests/test_splash_screen.py` verifying geometry, child widgets, progress updates, and theme styling.
  - *Verification*: `pytest tests/test_splash_screen.py`.

### Phase 2: Create Workspace Loading Overlay (`wiz/ui/popup_dialog.py`)
- [ ] **Step 2.1**: Define `WorkspaceSplashOverlay(QFrame)` inside `wiz/ui/popup_dialog.py`:
  - Centered card with mascot icon (40x40px), "Loading workspace..." label, and slim progress bar.
  - Smooth fade-out using `QGraphicsOpacityEffect` and `QPropertyAnimation` over 200ms.
- [ ] **Step 2.2**: Integrate `WorkspaceSplashOverlay` into `QuickEntryDialog`:
  - Show on initial opening, load tasks and calendar views, then fade out overlay.
  - Ensure overlay only shows once on initial launch so subsequent openings are instantaneous.
- [ ] **Step 2.3**: Verify existing dialog tests in `tests/test_dialogs.py` pass without regressions.
  - *Verification*: `pytest tests/test_dialogs.py`.

### Phase 3: Wire Startup Lifecycle in `wiz/__main__.py`
- [ ] **Step 3.1**: Update `WizApplication.__init__()` and `start()`:
  - Instantiate and show `SplashScreen` before initializing repository and companion.
  - Step through progress milestones:
    - 0%: "Starting WizDesk..."
    - 25%: "Loading local database..."
    - 55%: "Starting background tracker..."
    - 80%: "Preparing desktop companion..."
    - 100%: "Ready"
  - Call `splash.finish()` to initiate smooth fade-out into active mascot and tray icon.
- [ ] **Step 3.2**: Add test coverage for startup splash progress flow in `tests/test_splash_screen.py`.
  - *Verification*: `pytest tests/test_splash_screen.py`.

### Phase 4: Full Test Suite Verification & Commit
- [ ] **Step 4.1**: Run complete test suite (`pytest`) to ensure all 116 existing tests plus new splash screen tests pass.
- [ ] **Step 4.2**: Verify zero double dashes and zero em-dashes across all modified files.
- [ ] **Step 4.3**: Commit working tree following `AGENTS.md` commit routine.
