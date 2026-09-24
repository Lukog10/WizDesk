# Implementation Plan: Mascot State Machine, Eye-Tracking & Sound Engine

**Date**: 2026-09-24  
**Design Spec Reference**: [docs/superpowers/specs/2026-09-24-mascot-update-design.md](file:///h:/Projects/Wiz/docs/superpowers/specs/2026-09-24-mascot-update-design.md)  
**Status**: Ready for Execution  

---

## 1. Context Lock-in

- **TASK**: Update Wiz desktop mascot with custom state transitions (Monitor, Working, Notify, Complete, Sleep), cursor-tracking dot eyes in Monitor state, thin spinner eyes in Working state, a procedural organic sound effects engine, and integrated settings matching existing Untitled UI styling.
- **INPUTS**:
  - `QCursor.pos()` global mouse coordinates.
  - `WindowTracker` activity log commitments.
  - Task lifecycle events via `app_signals` (`task_created`, `task_updated`, `task_completed`, `task_deleted`, `task_cancelled`).
  - System idle detection via `get_system_idle_seconds()`.
  - User configuration in `config` and `settings_view.py`.
- **OUTPUTS**:
  - Real-time eye-tracking animation in `MascotWidget`.
  - Responsive state machine transitions in `StateMachine`.
  - Low-latency procedural sound playback via `wiz/core/sound.py`.
  - General Settings UI rows for sound effects toggle, volume slider, and sleep timeout.
- **CONSTRAINTS**:
  - Strict zero-emoji compliance across all UI text, settings rows, and labels.
  - Settings UI components must strictly match existing Untitled UI styling, dimensions, font weights, and color tokens.
  - Zero external sound asset dependencies: all 16-bit PCM WAV chimes synthesized programmatically via Python standard library `wave` and `math`.
  - All existing test suite tests (113 passed) must continue to pass with 0 regressions.
- **SUCCESS CRITERIA**:
  - Eyes smoothly follow mouse cursor across screen in `IDLE` (Monitor) state.
  - `WORKING` state displays thin, refined spinning eyes during window activity logging.
  - Sound effects trigger appropriately on wake, sleep, notify, complete, cancel, work log, and mascot poke/drag.
  - Sound toggle, volume slider, and sleep spinbox persist in settings and update live.
  - 100% of test suite passes.

---

## 2. File Impact Analysis

| File | Purpose of Change | Verification Method |
| :--- | :--- | :--- |
| `wiz/core/sound.py` *(New)* | Procedural WAV synthesis and `SoundManager` singleton using `QSoundEffect`. | `tests/test_sound.py` |
| `wiz/core/config.py` | Add config properties for sound toggle, volume, and sleep inactivity timeout. | Unit test / verify config load |
| `wiz/core/signals.py` | Extend `app_signals` with `activity_logged`, `task_deleted`, `task_cancelled`. | Pytest / signal emission check |
| `wiz/core/state_machine.py` | Update state transitions, connect to `app_signals`, trigger sounds on transitions. | `tests/test_mascot_core.py` |
| `wiz/ui/mascot_widget.py` | Add cursor gaze calculation, smooth lerp damping, and thin spinning eyes. | Offscreen PyQt paint test |
| `wiz/ui/mascot_window.py` | Connect click/drag gestures to poke/drag sound effects. | Interactive / gesture test |
| `wiz/tracker/window_tracker.py` | Emit `app_signals.activity_logged` when committing interval to storage. | Unit test tracker signal |
| `wiz/ui/settings_view.py` | Add Mascot & Sound rows in General settings matching Untitled UI design. | Offscreen settings load & theme test |
| `tests/test_sound.py` *(New)* | Verify WAV generation, sound playback calls, mute toggle, and volume scaling. | `pytest tests/test_sound.py` |

---

## 3. Incremental Execution Steps

### Phase 1: Core Sound Engine & Configuration
- [ ] **Step 1.1**: Update `wiz/core/config.py` to add `sound_effects_enabled`, `sound_volume`, and `sleep_inactivity_sec` properties with defaults.
  - *Verification*: Import config and check default values.
- [ ] **Step 1.2**: Create `wiz/core/sound.py` with `WavSynthesizer` and `SoundManager` (using `QSoundEffect` and standard library `wave`/`math`).
  - *Verification*: Run standalone script generating WAVs and asserting file headers and non-empty byte streams.
- [ ] **Step 1.3**: Create `tests/test_sound.py` testing sound synthesis, mute state, and volume bounds.
  - *Verification*: Run `pytest tests/test_sound.py`.

### Phase 2: Signal Bus & State Machine Transition Logic
- [ ] **Step 2.1**: Update `wiz/core/signals.py` to add `activity_logged`, `task_deleted`, `task_cancelled`.
  - *Verification*: Ensure signals instantiate and connect cleanly.
- [ ] **Step 2.2**: Update `wiz/tracker/window_tracker.py` to emit `activity_logged` upon committing a tracking window.
  - *Verification*: Test window tracker logs emit signal.
- [ ] **Step 2.3**: Refactor `wiz/core/state_machine.py`:
  - Wire signals from `app_signals` to state triggers.
  - Add wake/sleep sound triggers on sleep transition and wake input.
  - Connect task events to `NOTIFY` and `COMPLETE`.
  - Update `_check_idle_state` to respect configurable sleep timeout.
  - *Verification*: Run `pytest tests/test_mascot_core.py`.

### Phase 3: Visuals & Eye-Tracking Animation in MascotWidget
- [ ] **Step 3.1**: Implement cursor tracking in `MascotWidget.paintEvent` for `MascotState.IDLE`:
  - Calculate `(dx, dy)` from mascot center to `QCursor.pos()`.
  - Clamp to max socket radius (`3.5 * scale_x`).
  - Apply linear interpolation (lerp factor `0.25`) for smooth eye glide.
  - Draw pupils with cute white glints at offset coordinates.
- [ ] **Step 3.2**: Refine `_render_working_state`:
  - Reduce spinner stroke to `max(1.5, 3.2 * scale_x)`.
  - Use brand terracotta accent (`#BA3F1A` light / `#FF6B3D` dark).
  - Slightly offset spinner center toward cursor direction.
- [ ] **Step 3.3**: Connect mascot clicks and drag events in `MascotWindow` to `sound_manager.play_mascot_poke()` and drag sounds.
  - *Verification*: Offscreen test asserting widget paint without errors across all states.

### Phase 4: Settings View Integration (General Tab)
- [ ] **Step 4.1**: In `wiz/ui/settings_view.py`:
  - Add "Mascot Sound Effects" toggle (`SettingsCheckbox`).
  - Add "Sound Volume" slider (`QSlider` + percentage text).
  - Add "Sleep Inactivity Timeout" spinbox (`QSpinBox`).
  - Style with `neutral_btn_qss`, `input_qss`, brand terracotta `#BA3F1A` slider accent, and zero emojis.
- [ ] **Step 4.2**: Bind settings load and save to `config`.
  - *Verification*: Instantiate `SettingsView`, switch to General tab, verify values and theme application.

### Phase 5: Verification & Self-Review
- [ ] **Step 5.1**: Run complete test suite `pytest`.
- [ ] **Step 5.2**: Perform visual inspection and offscreen rendering verification.
- [ ] **Step 5.3**: Commit working tree following `AGENTS.md` commit routine.
