# Design Specification: Mascot State Machine, Eye-Tracking & Sound Engine

**Date**: 2026-09-24  
**Author**: DeepMind Antigravity / Pair Programming Agent  
**Status**: Approved by User  
**Spec Location**: `docs/superpowers/specs/2026-09-24-mascot-update-design.md`

---

## 1. Overview & Goals

The Wiz desktop companion mascot is an expressive, always-on-top presence designed to give personality to personal task and productivity tracking. This update refines the mascot system across three core dimensions:

1. **Intuitive State Taxonomy**:
   - **Idle / Monitor**: Awake and resting, actively monitoring cursor movement across the desktop.
   - **Working**: Explicitly signals when Wiz logs window tracking activity into the database.
   - **Notify**: Acknowledges task lifecycle actions (add, delete, schedule, move, rename, repeat, subtask add/update).
   - **Complete**: Celebrates task completion.
   - **Sleep**: Naps when the user is inactive past the sleep threshold.
2. **Dynamic Eye-Tracking & Refined Visuals**:
   - In **Idle / Monitor** state, Wiz's dot pupils smoothly track the global mouse cursor with natural socket clamping and linear interpolation (lerp).
   - In **Working** state, the thick spinner eyes are replaced with delicate, thin (1.6px) spinning arcs that also subtly orient toward the cursor.
3. **Procedural Organic Sound Effects Engine**:
   - Synthesizes 16-bit 44.1kHz PCM audio programmatically via Python standard library `wave` and `math` (zero external downloads or missing files).
   - Powered by `PyQt6.QtMultimedia.QSoundEffect` for low-latency, multi-channel, non-blocking playback.
   - Triggers on wake, sleep, task notify, task complete, task cancel, work log, mascot poke (click), and mascot drag.
4. **Settings Parity**:
   - Matches the exact Untitled UI two-column row pattern, color tokens, and font weights used across existing settings tabs.

---

## 2. Mascot State Taxonomy & Transitions

### 2.1 State Definitions

| State Enum | Meaning to User | Trigger Condition | Visual Asset & Animation | Duration & Exit Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `MascotState.IDLE` *(Monitor)* | Awake, observing desktop activity. | User input detected (< sleep threshold), or auto-revert from transient states. | `wiz-idle.svg` base body with dynamic dot pupils tracking `QCursor.pos()`. Gentle vertical bobbing. | Persists until sleep timeout or event trigger. |
| `MascotState.WORKING` *(Work Log)* | Recording window tracking snapshot. | `WindowTracker` completes and commits an activity log interval to SQLite. | Thin 1.6px dashed spinning rings with subtle cursor tracking. | Displays for ~2.5s, then automatically reverts to `IDLE` (Monitor). |
| `MascotState.NOTIFY` *(Action Acknowledged)* | Noticing task management actions. | Emitted on task add, edit, delete, schedule, move, rename, repeat, subtask ops. | `wiz-notify.svg` alert sparkle pose with attention sparkles. | Displays for ~2.0s with audio pop, then reverts to `IDLE`. |
| `MascotState.COMPLETE` *(Celebration)* | Celebrating task completion. | Task marked as completed / done. | `wiz-complete.svg` celebration flash with upward celebratory bounce. | Displays for ~3.5s with celebration chime, then reverts to `IDLE`. |
| `MascotState.SLEEP` *(Resting)* | Inactive away-from-keyboard nap. | System idle time exceeds configured sleep threshold (e.g. 60s). | `wiz-sleep.svg` closed eyes, slow peaceful breathing bob. | Instantly transitions to `IDLE` on keyboard/mouse input, playing wake chime. |

### 2.2 Signal-Driven State Integration

The state machine transitions are driven by `app_signals` rather than polling:
- `app_signals.activity_logged`: Triggers `state_machine.trigger_working(duration_ms=2500)` and plays `work_log` sound.
- `app_signals.task_created`, `app_signals.task_updated`, `app_signals.task_scheduled`, `app_signals.task_deleted`: Triggers `state_machine.trigger_notify(duration_ms=2000)` and plays `task_notify` sound.
- `app_signals.task_completed`: Triggers `state_machine.trigger_complete(duration_ms=3500)` and plays `task_complete` sound.
- `app_signals.task_cancelled`: Plays `task_cancel` sound.
- User inactivity timer checking Windows idle seconds: Triggers `state_machine.trigger_sleep()` when idle >= `sleep_threshold_sec`.

---

## 3. Visuals & Eye-Tracking Architecture (`wiz/ui/mascot_widget.py`)

### 3.1 Pupil Calculation & Gaze Vector

In `MascotWidget.paintEvent`:
1. **Screen Vector**:
   ```python
   cursor_pos = QCursor.pos()
   mascot_center = self.mapToGlobal(self.rect().center())
   dx = cursor_pos.x() - mascot_center.x()
   dy = cursor_pos.y() - mascot_center.y()
   dist = math.hypot(dx, dy)
   ```
2. **Clamped Offset with Non-linear Saccade**:
   - Maximum socket radius: `max_r = 3.5 * scale_x` pixels.
   - Normalized offset vector:
     ```python
     if dist > 0:
         clamped_r = min(max_r, (dist / 300.0) * max_r)
         target_ox = (dx / dist) * clamped_r
         target_oy = (dy / dist) * clamped_r
     else:
         target_ox, target_oy = 0.0, 0.0
     ```
3. **Smooth Damping (Lerp)**:
   - To avoid harsh snapping, current offsets interpolate toward target offsets:
     `self._eye_ox += (target_ox - self._eye_ox) * 0.25`
     `self._eye_oy += (target_oy - self._eye_oy) * 0.25`
4. **Drawing Pupils**:
   - In `IDLE` (Monitor) mode, draw clean circular pupils (`#242220`) of radius `5.5 * scale_x` at `(eye_center_x + self._eye_ox, eye_center_y + self._eye_oy)`.
   - Small glint highlight (`#FFFFFF`) of radius `1.5 * scale_x` drawn at top-left of each pupil for lively character depth.

### 3.2 Refined Working State Spinner

- Eye stroke width: `max(1.5, 3.2 * scale_x)` (reduced by 50% from prior 5.0px).
- Spinner radius: `6.5 * scale_x`.
- Color: `#BA3F1A` brand terracotta accent in light mode / `#FF6B3D` in dark mode.
- Pen: `Qt.PenStyle.CustomDashLine` with thin arc proportions `[4.0, 2.5]`.
- Subtle cursor orientation: Spinner rotation center shifts by up to `1.5 * scale_x` pixels toward the cursor.

---

## 4. Procedural Sound Effects Engine (`wiz/core/sound.py`)

### 4.1 Audio Synthesis (Standard Library)

A dedicated helper `WavSynthesizer` generates clean WAV files programmatically on first boot:
- **Sample Rate**: 44,100 Hz, 16-bit Mono PCM.
- **Waveform Synthesis**: Pure sine and soft harmonic tones with exponential attack and release envelopes to eliminate any clicking or popping artifacts.

### 4.2 Sound Table

| Sound Name | Musical Notes / Frequencies | Wave Characteristics | Associated Event |
| :--- | :--- | :--- | :--- |
| `wake_up` | C5 (523Hz) → G5 (784Hz) | Warm rising bell chime (180ms) | User returns from sleep/inactivity |
| `sleep` | G4 (392Hz) → E4 (330Hz) → C4 (261Hz) | Gentle descending lullaby sigh (450ms) | Mascot enters sleep state |
| `task_complete` | C5 → E5 → G5 → C6 (1046Hz) | Bright 4-tone celebration arpeggio (600ms) | Task marked completed |
| `task_notify` | F5 (698Hz) → A5 (880Hz) | Crisp marimba bubble ping (120ms) | Task added, scheduled, moved, or edited |
| `task_cancel` | E4 (330Hz) → C4 (261Hz) | Soft mellow low tone (200ms) | Task cancelled / discarded |
| `work_log` | C6 click (1046Hz, 35ms) | Subtle mechanical focus click | WindowTracker logs activity |
| `mascot_poke` | A5 (880Hz, 80ms) | Cute, pillowy pop squeak | Left-click on mascot |
| `mascot_drag` | G5 whoosh & C5 drop | Flutter lift and soft landing tap | Drag start and drop |

### 4.3 Playback Management

- Singleton `sound_manager` using `QSoundEffect` pools for instant trigger.
- Respects `config.sound_effects_enabled` (boolean) and `config.sound_volume` (0.0 to 1.0).

---

## 5. UI & Settings Integration (`wiz/ui/settings_view.py`)

In the **General** settings tab, add a dedicated **Mascot & Sound** section following the exact Untitled UI two-column row design pattern:

1. **Row: Mascot Sound Effects**
   - Left: Label `Mascot Sound Effects`, Subtitle `Play subtle chimes on state changes, task actions, and interactions`.
   - Right: `SettingsCheckbox` toggle (`size=18`).
2. **Row: Sound Volume**
   - Left: Label `Sound Volume`, Subtitle `Master volume for companion alerts and interaction sounds`.
   - Right: Compact `QSlider` (Qt horizontal) with percentage label (`65%`). Styled with brand terracotta `#BA3F1A` groove and handle.
3. **Row: Sleep Timeout**
   - Left: Label `Sleep Inactivity Timeout`, Subtitle `Duration of keyboard and mouse inactivity before Wiz sleeps`.
   - Right: `QSpinBox` (30s to 600s, suffix ` sec`).

All inputs match existing `neutral_btn_qss`, `input_qss`, and `apply_theme` rules, with zero emojis and clean typography (`get_font`).

---

## 6. Verification & Test Plan

1. **Unit Tests**:
   - `test_state_machine.py`: Verify transition between `IDLE` (Monitor), `WORKING` (on log), `NOTIFY` (on task changes), `COMPLETE` (on complete), and `SLEEP` (on timeout).
   - `test_sound_engine.py`: Test WAV synthesis, volume clamping, and mute behavior.
2. **UI & Regression Tests**:
   - Offscreen PyQt test verifying `MascotWidget` renders all states without exceptions.
   - Verify Settings tab loads, updates volume/sound configs, and persists to database.
   - Run complete suite (`pytest`) to maintain 100% test passing status.
