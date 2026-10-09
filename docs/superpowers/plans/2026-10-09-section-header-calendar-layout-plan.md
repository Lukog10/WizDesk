# Implementation Plan: Section Header and Calendar Date Navigator Layout

**Date**: 2026-10-09  
**Design Spec Reference**: [docs/superpowers/specs/2026-10-09-section-header-calendar-layout-design.md](file:///h:/Projects/Wiz/docs/superpowers/specs/2026-10-09-section-header-calendar-layout-design.md)  
**Status**: Ready for Phased Execution  

---

## 1. Context Lock-in

- **GOAL**: Reorganize the workspace section header and calendar date navigator to unify visual hierarchy and maximize content real estate:
  1. Outer top bar: Remove text title from outer bar, slim down top margin to 6px and layout spacing to 4px.
  2. Window controls: Downsize `min_btn` and `close_btn` from 28x28 px to **22x22 px** (11px soft radius) in outer top-right.
  3. Inner card: Expand vertically by ~14px; place `card_header_widget` at index 0 of `inner_layout`.
  4. Header structure inside card:
     - Row 1: Section title (`page_title_lbl`) in 15px bold display typography, left-aligned.
     - Row 2: Date navigator (`date_header_container`) directly below title in left corner, using calendar-styled 28x28 px chevron buttons (`‹` and `›`), date button, and "Today" pill button.
  5. Multi-mode visibility:
     - `tasks`, `notes`, `activity`: Title and date navigator visible.
     - `projects`, `settings`, `help`: Title visible, date navigator hidden.
     - `calendar`: Card header hidden (calendar view has dedicated header).
  6. Status filter capsules (`Task`, `In progress`, `Completed`, `Cancelled`): Preserved completely without modification.
- **FILES IMPACTED**:
  - `wiz/ui/popup_dialog.py`: Widget hierarchy, layout margins, window controls sizing and styling, date navigation chevrons, mode switching logic.
  - `tests/test_section_header_layout.py`: New comprehensive test suite covering hierarchy, sizing, styling, and multi-mode visibility.
- **CONSTRAINTS**:
  - Zero double dashes and zero em-dashes in code, comments, and commit messages.
  - 100% test pass rate across existing test suite (208+ tests passing).

---

## 2. File Impact Analysis

| File | Nature of Change | Target Functionality | Verification |
| :--- | :--- | :--- | :--- |
| `wiz/ui/popup_dialog.py` | UI layout & styling | Reorganize `top_bar`, `card_header_widget`, 22x22 controls, 28x28 chevrons, `_set_view_mode` | Visual render & unit tests |
| `tests/test_section_header_layout.py` | New test suite | Hierarchy assertions, button sizes, chevron labels, visibility matrix across 7 modes | `pytest tests/test_section_header_layout.py` |

---

## 3. Phased Execution Tasks

### Phase 1: UI Hierarchy and Styling in `wiz/ui/popup_dialog.py`
- [ ] In `QuickEntryDialog.__init__`:
  - Set `workspace_layout.setContentsMargins(16, 6, 16, 12)` and `workspace_layout.setSpacing(4)`.
  - Set `top_bar.setContentsMargins(0, 0, 0, 0)` with stretch followed by `controls_layout`.
  - Resize `min_btn` and `close_btn` to `22, 22`.
  - Update `prev_day_btn` and `next_day_btn` text to `‹` and `›`, fixed size `28, 28`.
  - Create `card_header_widget` (QVBoxLayout with margins `0, 0, 0, 4` and spacing `6`).
  - Add `page_title_lbl` to Row 1 of `card_header_widget`.
  - Add left-aligned `date_header_container` with stretch on right to Row 2 of `card_header_widget`.
  - Insert `card_header_widget` at index 0 of `self.inner_layout`.
- [ ] In `QuickEntryDialog.apply_theme`:
  - Update `min_qss` and `close_qss` for 22x22 px size (border radius 11px, font sizes 13px and 11px).
  - Update `day_nav_qss` for 28x28 px chevrons (font size 14px bold, radius 6px).
- [ ] In `QuickEntryDialog._set_view_mode`:
  - Manage visibility of `card_header_widget`, `page_title_lbl`, and `date_header_container`:
    - `tasks`, `notes`, `activity`: `card_header_widget.show()`, `date_header_container.show()`, `page_title_lbl.show()`.
    - `projects`, `settings`, `help`: `card_header_widget.show()`, `date_header_container.hide()`, `page_title_lbl.show()`.
    - `calendar`: `card_header_widget.hide()`.

### Phase 2: Automated Test Suite
- [ ] Create `tests/test_section_header_layout.py`:
  - Test widget parenting (title and date container are inside `inner_card`).
  - Test window controls dimensions (22x22 px).
  - Test day navigation buttons (`‹`, `›` text and 28x28 px).
  - Test visibility states across all 7 modes (`tasks`, `notes`, `activity`, `projects`, `settings`, `help`, `calendar`).

### Phase 3: Verification & Commit
- [ ] Run `pytest tests/test_section_header_layout.py`.
- [ ] Run full pytest suite across repository.
- [ ] Clean git commit before handoff.
