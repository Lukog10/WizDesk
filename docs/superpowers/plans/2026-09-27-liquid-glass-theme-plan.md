# Implementation Plan: Liquid Glass & Glassmorphism Theme Integration

**Date**: 2026-09-27  
**Design Spec Reference**: [docs/superpowers/specs/2026-09-27-liquid-glass-theme-design.md](file:///h:/Projects/Wiz/docs/superpowers/specs/2026-09-27-liquid-glass-theme-design.md)  
**Status**: Ready for Execution  

---

## 1. Context Lock-in

- **TASK**: Upgrade WizDesk's Dark and Light modes into a luxury Liquid Glass (Glassmorphism) design system with translucent surfaces, specular hairline rim borders, and optional native Windows 11 Acrylic blur, fully architected for Linux cross-platform compatibility.
- **INPUTS**:
  - Design Spec: `docs/superpowers/specs/2026-09-27-liquid-glass-theme-design.md`
- **OUTPUTS**:
  - Standalone cross-platform window blur helper: `wiz/utils/window_blur.py`
  - Liquid Glass styling tokens across `wiz/ui/popup_dialog.py`, `wiz/ui/sidebar_widget.py`, `wiz/ui/settings_dialog.py`, and `wiz/ui/settings_view.py`
  - Unit test suite: `tests/test_window_blur.py`
- **CONSTRAINTS**:
  - Strict preservation of WizDesk brand colors: terracotta and orange (`#BA3F1A`, `#C2410C`, `#FF6B3D`, hover `#9E3414` / `#A3360E`), emerald (`#10B981`), and vivid chart colors.
  - Zero modification to UI component layout, geometry, margins, padding, border radius, or widget hierarchy.
  - Pure PyQt6 cross-platform core: all translucent glass styling runs natively on Linux (X11 / Wayland) without Windows dependencies.
  - Windows Acrylic is strictly an optional progressive enhancement guarded by `if sys.platform == "win32"`.
  - Zero double dashes and zero em-dashes across all code, documentation, and commits.
  - Zero emojis in code and test suites.
  - 100% test pass rate across existing 116 tests plus new tests.

---

## 2. File Impact Analysis

| File | Nature of Change | Target Scope | Verification Method |
| :--- | :--- | :--- | :--- |
| `wiz/utils/window_blur.py` | New module | Implements safe `set_window_acrylic` and `set_window_mica` using standard `ctypes`, guarded by Windows platform check | Pytest (`tests/test_window_blur.py`) |
| `wiz/ui/popup_dialog.py` | Update tokens & blur hook | Apply `WA_TranslucentBackground` on dialog, invoke window blur helper, update `apply_theme` with Dark Liquid Glass and Light Crystal Glass tokens | Visual render test + pytest |
| `wiz/ui/sidebar_widget.py` | Update glass styling | Apply translucent frosted sidebar tokens and specular divider border | Visual render test + pytest |
| `wiz/ui/settings_dialog.py` | Update glass styling | Apply matching glass tokens for outer frame and inner cards | Visual render test + pytest |
| `wiz/ui/settings_view.py` | Update glass styling | Apply matching glass tokens for settings container | Visual render test + pytest |
| `tests/test_window_blur.py` | New test file | Test safe execution on non-Windows platforms, mock Windows DWM calls, and error handling | Pytest |

---

## 3. Incremental Execution Steps

### Phase 1: Window Blur Utility & Tests
- [ ] **Step 1.1**: Create `wiz/utils/window_blur.py`:
  - Check `sys.platform == "win32"`.
  - Define `DWMWA_SYSTEMBACKDROP_TYPE = 38`, `DWMSBT_ACRYLIC = 3`, `DWMSBT_MICA = 2`, `DWMWA_USE_IMMERSIVE_DARK_MODE = 20`.
  - Provide `set_window_backdrop(hwnd, backdrop_type=DWMSBT_ACRYLIC, is_dark=True) -> bool` with graceful error handling.
  - On non-Windows platforms (e.g. Linux), safely return False without attempting any DLL imports.
- [ ] **Step 1.2**: Create `tests/test_window_blur.py`:
  - Test platform detection and mock calls.
  - Verify that invalid window handles or OS exceptions are caught without raising errors.

### Phase 2: Translucent Shell & Color Tokens in QuickEntryDialog
- [ ] **Step 2.1**: Update `QuickEntryDialog.__init__` in `wiz/ui/popup_dialog.py`:
  - Enable `self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)`.
  - Connect theme changes to update the window backdrop mode.
- [ ] **Step 2.2**: Update `QuickEntryDialog.apply_theme`:
  - Dark Liquid Glass:
    - `outer_bg`: `rgba(18, 18, 22, 0.72)` with border `1px solid rgba(255, 255, 255, 0.18)`
    - `inner_bg`: `rgba(24, 24, 29, 0.55)` with border `1px solid rgba(255, 255, 255, 0.12)`
    - `input_bg`: `rgba(255, 255, 255, 0.06)` with border `1px solid rgba(255, 255, 255, 0.15)`
  - Light Crystal Glass:
    - `outer_bg`: `rgba(248, 248, 250, 0.78)` with border `1px solid rgba(255, 255, 255, 0.65)`
    - `inner_bg`: `rgba(238, 238, 242, 0.60)` with border `1px solid rgba(255, 255, 255, 0.50)`
    - `input_bg`: `rgba(255, 255, 255, 0.90)` with border `1px solid #E4E4E7`
  - Brand accents: strictly preserved (`#BA3F1A` / `#C2410C` / `#FF6B3D`).

### Phase 3: SideNavBar & Settings Glass Polish
- [ ] **Step 3.1**: Update `SideNavBar.apply_theme` in `wiz/ui/sidebar_widget.py`:
  - Dark Glass sidebar: `background-color: rgba(14, 14, 18, 0.65); border-right: 1px solid rgba(255, 255, 255, 0.10);`
  - Light Glass sidebar: `background-color: rgba(242, 242, 245, 0.70); border-right: 1px solid rgba(0, 0, 0, 0.08);`
  - Specular button and hover styling: clean translucent states.
- [ ] **Step 3.2**: Update `SettingsDialog.apply_theme` and `SettingsView.apply_theme`:
  - Apply corresponding outer and inner glass tokens.

### Phase 4: Verification, Test Suite & Package Gate
- [ ] **Step 4.1**: Execute automated pytest suite:
  - Run full test suite (`pytest`) verifying all 116 existing tests pass plus new blur tests.
- [ ] **Step 4.2**: Render offscreen verification screenshots:
  - Verify Dark Liquid Glass and Light Crystal Glass render cleanly with high contrast, sharp text, and elegant specular highlights.
- [ ] **Step 4.3**: Rebuild standalone executable (`pyinstaller wizdesk.spec`) to bundle the new utility.
- [ ] **Step 4.4**: Commit working tree with a clean commit message following all constraints.
