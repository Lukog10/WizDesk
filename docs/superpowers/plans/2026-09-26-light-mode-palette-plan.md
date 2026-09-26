# Implementation Plan: Crisp Light Mode White Palette (Polymet-Based)

**Date**: 2026-09-26  
**Design Spec Reference**: [docs/superpowers/specs/2026-09-26-light-mode-palette-design.md](file:///h:/Projects/Wiz/docs/superpowers/specs/2026-09-26-light-mode-palette-design.md)  
**Status**: Ready for Execution  

---

## 1. Context Lock-in

- **TASK**: Replace dull, sandy, and yellowish-cream tones in WizDesk's Light Mode with a crisp, pure white and cool neutral grey palette based on the Polymet onboarding reference image.
- **INPUTS**:
  - Design Spec: `docs/superpowers/specs/2026-09-26-light-mode-palette-design.md`
  - Reference Image: `C:\Users\Administrator\.gemini\antigravity-ide\brain\a2c70cca-a4cd-4cea-9a5f-b70cf21f04ec\.user_uploaded\media_1790402033155.png`
- **OUTPUTS**:
  - Surgical color token updates across `wiz/ui/popup_dialog.py`, `wiz/ui/sidebar_widget.py`, `wiz/ui/quick_bar_dialog.py`, `wiz/ui/settings_dialog.py`, `wiz/ui/settings_view.py`, `wiz/ui/timeline_view.py`, `wiz/ui/project_dashboard_view.py`, `wiz/ui/calendar_view.py`, and `wiz/ui/chart_widgets.py`.
  - Verification test script in `scratch/verify_light_palette.py` ensuring pure `#FFFFFF` cards, `#F4F4F6` canvas, and preserved `#BA3F1A` accents.
- **CONSTRAINTS**:
  - Strict preservation of existing brand orange/terracotta accent colors (`#BA3F1A`, `#C2410C`, `#FF6B3D`, hover `#9E3414` / `#A3360E`).
  - Zero modification to UI component layout, geometry, margins, padding, border radius, or structure.
  - Zero modification to Dark Mode colors (`#121214`, `#18181B`, `#27272A`).
  - Zero double dashes and zero em-dashes across all code and documentation.
  - Zero emojis in code or test suites.
  - 100% test suite pass rate (116+ existing unit tests).
- **SUCCESS CRITERIA**:
  - Outer frame background is `#F4F4F6` with `#E4E4E7` border.
  - Main inner workspace cards are pure `#FFFFFF` with `#E5E5EA` border.
  - Input backgrounds are clean `#F4F4F6` with `#E4E4E7` borders.
  - Headings and primary text are deep graphite `#18181B`.
  - Secondary metadata and inactive icons are cool slate `#71717A`.
  - All unit tests pass with zero regressions.

---

## 2. File Impact Analysis

| File | Nature of Change | Target Tokens / Lines | Verification Method |
| :--- | :--- | :--- | :--- |
| `wiz/ui/popup_dialog.py` | Update Light Mode color tokens for dialog frame, inner card, inputs, filter bar, calendar, and task rows | `outer_bg`, `inner_bg`, `input_bg`, `page_title_color`, `SegmentedFilterBar`, `TaskRowWidget` | Pytest + headless render script |
| `wiz/ui/sidebar_widget.py` | Update inactive text/icon colors, hover background, and active pill surface | `text_color`, `icon_color`, `hover_bg`, `normal_fg`, `badge_bg` | Pytest + visual inspect |
| `wiz/ui/quick_bar_dialog.py` | Update card background to pure white, input background to clean neutral grey | `card_bg`, `card_border`, `input_bg`, `input_border`, `dropdown_bg` | Pytest + visual inspect |
| `wiz/ui/settings_dialog.py` | Update settings outer frame, inner card, input fields, neutral buttons, table headers | `outer_bg`, `inner_bg`, `input_bg`, `btn_neutral_bg`, `table_header_bg` | Pytest + visual inspect |
| `wiz/ui/settings_view.py` | Update settings tab background, input backgrounds, neutral buttons, divider lines | `bg`, `text`, `subtext`, `input_bg`, `btn_bg`, `inner_bg` | Pytest + visual inspect |
| `wiz/ui/timeline_view.py` | Update session cards, milestone cards, filter combos to pure white and neutral borders | Card `background-color`, border colors, label text colors | Pytest + visual inspect |
| `wiz/ui/project_dashboard_view.py` | Update project cards, dialogs, directory containers to pure white and neutral borders | Dialog backgrounds, card backgrounds, combo boxes | Pytest + visual inspect |
| `wiz/ui/calendar_view.py` | Update calendar card and combo popups to pure white and neutral borders | `card_bg`, `combo_popup_bg`, border tokens | Pytest + visual inspect |
| `wiz/ui/chart_widgets.py` | Update KPI cards and chart cards in light mode to pure white | `card_bg`, hover backgrounds | Pytest + visual inspect |
| `scratch/verify_light_palette.py` | Automated headless Qt verification script | New verification script | Programmatic pixel & style assertions |

---

## 3. Incremental Execution Steps

### Phase 1: Verification Script Setup
- [ ] **Step 1.1**: Create `scratch/verify_light_palette.py` that instantiates `QuickEntryDialog`, `SideNavBar`, and `SettingsDialog` with `is_dark=False`, captures their stylesheets and computed properties, and asserts the absence of `#E8E4DC`, `#F6F4EE`, and `#EDE9E0`.
  - *Verification*: Script runs and accurately reports current failure on sandy colors.

### Phase 2: Quick Entry Dialog & Sidebar Modernization
- [ ] **Step 2.1**: Update `wiz/ui/popup_dialog.py` main tokens:
  - Replace `outer_bg`: `#E8E4DC` -> `#F4F4F6`
  - Replace `outer_border`: `#D5CEC2` -> `#E4E4E7`
  - Replace `inner_bg`: `#F6F4EE` -> `#FFFFFF`
  - Replace `inner_border`: `#DFD9CE` -> `#E5E5EA`
  - Replace `page_title_color`: `#242220` -> `#18181B`
  - Replace `ctrl_btn_color`: `#57534E` -> `#71717A`
  - Replace `mode_capsule_bg`: `#E6E1D7` -> `#F0F0F2`
  - Replace `day_btn_color`: `#78716C` -> `#71717A`
  - Replace `day_btn_border`: `#D8D1C4` -> `#E4E4E7`
  - Replace `day_btn_hover_bg`: `#EBE6DC` -> `#EAEAEB`
  - Replace `input_bg`: `#EDE9E0` -> `#F4F4F6`
  - Replace `input_border`: `#D6D0C5` -> `#E4E4E7`
  - Replace `input_color`: `#242220` -> `#18181B`
  - Replace `combo_popup_bg`: `#FAF8F5` -> `#FFFFFF`
  - Replace `combo_popup_border`: `#D6D0C5` -> `#E4E4E7`
  - Update `SegmentedFilterBar`: active tab border `#E4E4E7`, container border `#E4E4E7`, inactive text `#71717A`
  - Update `TaskRowWidget`, `SubtaskRowWidget`, `CalendarPopupDialog`, `get_context_menu_style`
  - *Verification*: Run `pytest tests/test_popup_dialog.py` or full test suite.
- [ ] **Step 2.2**: Update `wiz/ui/sidebar_widget.py`:
  - Replace inactive text color: `#57534E` -> `#71717A`
  - Replace inactive icon color: `#78716C` -> `#71717A`
  - Replace hover background: `#DAD5CB` -> `rgba(0, 0, 0, 0.05)`
  - Replace toggle button normal text: `#78716C` -> `#71717A`
  - Replace active item surface: `QColor(0, 0, 0, 10)` -> `QColor("#FFFFFF")`
  - Replace brand text color: `#242220` -> `#18181B`
  - *Verification*: Run `pytest tests/test_sidebar_widget.py`.

### Phase 3: Quick Bar & Settings Modernization
- [ ] **Step 3.1**: Update `wiz/ui/quick_bar_dialog.py`:
  - Replace `card_bg`: `#F6F4EE` -> `#FFFFFF`
  - Replace `card_border`: `#E2DDD3` -> `#E5E5EA`
  - Replace `text_primary`: `#242220` -> `#18181B`
  - Replace `text_secondary`: `#666460` -> `#71717A`
  - Replace `input_bg`: `#EDE9E0` -> `#F4F4F6`
  - Replace `input_border`: `#D6D0C5` -> `#E4E4E7`
  - Replace `dropdown_bg`: `#EDE7DC` -> `#F4F4F6`
  - Replace `dropdown_hover`: `#E2DDD4` -> `#EAEAEB`
  - *Verification*: Run `pytest tests/test_quick_bar.py`.
- [ ] **Step 3.2**: Update `wiz/ui/settings_dialog.py`:
  - Replace `outer_bg`: `#E8E4DC` -> `#F4F4F6`
  - Replace `outer_border`: `#D6D0C5` -> `#E4E4E7`
  - Replace `inner_bg`: `#F6F4EE` -> `#FFFFFF`
  - Replace `inner_border`: `#E2DDD3` -> `#E5E5EA`
  - Replace `text_primary`: `#242220` -> `#18181B`
  - Replace `text_secondary`: `#666460` -> `#71717A`
  - Replace `input_bg`: `#EDE9E0` -> `#F4F4F6`
  - Replace `input_border`: `#D6D0C5` -> `#E4E4E7`
  - Replace `btn_neutral_bg`: `#EDE7DC` -> `#F4F4F6`
  - Replace `btn_neutral_border`: `#D6D0C5` -> `#E4E4E7`
  - Replace `btn_neutral_text`: `#242220` -> `#18181B`
  - Replace `btn_neutral_hover_bg`: `#E2DDD4` -> `#EAEAEB`
  - Replace `div_color`, `table_grid`: `#E2DDD3` -> `#E5E5EA`
  - Replace `table_header_bg`: `#EDE7DC` -> `#F4F4F6`
  - *Verification*: Run `pytest tests/test_settings_dialog.py`.
- [ ] **Step 3.3**: Update `wiz/ui/settings_view.py`:
  - Replace `bg`: `#FAF8F5` -> `#FFFFFF`
  - Replace `text`: `#242220` -> `#18181B`
  - Replace `subtext`: `#78716C` -> `#71717A`
  - Replace `input_bg`: `#EDE9E0` -> `#F4F4F6`
  - Replace `input_border`: `#D6D0C5` -> `#E4E4E7`
  - Replace `btn_bg`: `#EBE6DC` -> `#F4F4F6`
  - Replace `inner_bg`: `#FAF8F5` -> `#FFFFFF`
  - *Verification*: Run `pytest tests/test_settings_view.py`.

### Phase 4: Views & Dashboard Modernization
- [ ] **Step 4.1**: Update `wiz/ui/timeline_view.py`:
  - Replace `#FAF8F5` card backgrounds with `#FFFFFF`
  - Replace `#242220` label colors with `#18181B`
  - Replace `#78716C` subtext with `#71717A`
  - *Verification*: Run `pytest tests/test_timeline_view.py`.
- [ ] **Step 4.2**: Update `wiz/ui/project_dashboard_view.py`, `wiz/ui/calendar_view.py`, and `wiz/ui/chart_widgets.py`:
  - Replace `#FAF8F5` with `#FFFFFF`
  - Replace `#242220` with `#18181B`
  - *Verification*: Run dashboard and calendar tests.

### Phase 5: Verification & Visual Inspection
- [ ] **Step 5.1**: Run `scratch/verify_light_palette.py` to confirm zero remaining sandy tokens and verify pure `#FFFFFF` surfaces.
- [ ] **Step 5.2**: Render offscreen PNG screenshots of `QuickEntryDialog`, `SideNavBar`, and `SettingsDialog` in Light Mode and inspect visually.
- [ ] **Step 5.3**: Run the full test suite (`pytest`) to verify all 116+ unit tests pass.

---

## 4. Verification Protocol

```powershell
# 1. Run headless palette check
.venv/Scripts/python scratch/verify_light_palette.py

# 2. Run full test suite
.venv/Scripts/pytest

# 3. Check git diff for strict color-only modifications
git diff --stat
```
