# Code Quality & Maintainability Review: WizDesk

**Reviewer:** Senior Software Engineer  
**Milestone / Objective:** Pre-Release Codebase Cleanup & Red Team Audit Preparation  
**Baseline Test Status:** 234/234 tests passing (`pytest -q` in 70.84s)

---

## Executive Summary

A comprehensive architectural scan and code maintainability review of the WizDesk codebase was conducted across 8 core dimensions. WizDesk is a desktop companion and work tracking application built with PyQt6, SQLite (with optional AES-256-GCM authenticated encryption and Windows DPAPI), psutil, and win32gui. The baseline test suite currently passes with 100% success across all 234 automated tests, confirming solid functional stability.

However, the audit revealed several notable areas of technical debt, dead weight, and optimization opportunities. These include:
1. **Dead imports and unreferenced stubs**: Over 30 dead imports and multiple disconnected slot stubs left behind from previous UI refactorings.
2. **Duplicate asset files and orphaned icons**: Duplicate SVGs located in both `assets/` root and `assets/icons/`, plus orphaned icons (including typo-named `subttasks.svg`).
3. **Severe UI monolithic files**: `wiz/ui/popup_dialog.py` has grown into a 7,042-line monolith housing 28 distinct UI classes, mixing task items, notes, tag dialogs, calendar widgets, and the workspace shell.
4. **N+1 query pattern in project analytics**: `get_projects_overview_metrics` iterates through projects and runs 2 individual SQLite queries per project, generating 2*N queries rather than 2 batched set queries.
5. **Abandoned development files**: 342 scratch files and multiple temporary test SQLite databases (`test_debug.db`, `test_debug2.db`, and `scratch/*.db`) adding unnecessary clutter.

Executing the phased cleanup outlined below will eliminate dead code, reduce distribution package size, optimize database throughput, and establish clear architectural boundaries prior to the red team security audit.

---

## 1. Dead Code

### Issue 1.1: Dead Imports Across 12 Modules
* **Location:** Multiple files:
  - `wiz/ui/calendar_view.py:29-63` (`datetime`, `QPoint`, `QRect`, `QDate`, `QIcon`, `QComboBox`, `TaskRecord`, `FONT_MONO`)
  - `wiz/ui/settings_view.py:9-44` (`Any`, `List`, `QSize`, `QColor`, `QSpinBox`, `QTableWidget`, `QTableWidgetItem`, `QHeaderView`, `QInputDialog`, `FONT_DISPLAY`, `RoundedCheckbox`, `get_status_icon`)
  - `wiz/ui/help_faq_view.py:8-23` (`Tuple`, `QButtonGroup`, `FONT_MONO`)
  - `wiz/ui/settings_dialog.py:6,28` (`QSpinBox`, `FONT_MONO`)
  - `wiz/ui/sidebar_widget.py:29` (`FONT_DISPLAY`)
  - `wiz/ui/pill_number_picker.py:8,9` (`QTimer`, `QColor`)
  - `wiz/ui/popup_dialog.py:54` (`ProjectRecord`)
  - `wiz/ui/mascot_window.py:10` (`MascotState`)
  - `wiz/ui/icons.py:4` (`Path`)
  - `wiz/core/autostart.py:9` (`Optional`)
  - `wiz/core/state_machine.py:7` (`config`)
  - `wiz/sync/obsidian.py:8` (`NoteRecord`)
  - `wiz/utils/sanitizer.py:3` (`os`)
* **Why Unnecessary:** These symbols were imported during earlier iterations but are no longer referenced in their respective modules. They pollute the namespace and marginally increase module import overhead.
* **Estimated Impact:** Eliminates 34 unused imports, cleans linter warnings, reduces memory overhead.
* **Pre-Deletion Risks:** Zero risk. Verified that none are referenced dynamically or exported via `__all__`.
* **Recommended Cleanup Plan:** Remove unused import statements cleanly from the identified files.

### Issue 1.2: Disconnected Slot Stubs in CalendarView
* **Location:** `wiz/ui/calendar_view.py:1305-1309`
* **Why Unnecessary:** `_on_tag_filter_combo_changed(self, idx)` and `_on_detail_tag_filter_combo_changed(self, idx)` are empty `pass` methods with zero references and zero signal connections.
* **Estimated Impact:** Eliminates 6 lines of dead boilerplate.
* **Pre-Deletion Risks:** None. No signals connect to these methods.
* **Recommended Cleanup Plan:** Safely delete the two unreferenced stubs.

### Issue 1.3: Obsolete Unconnected ComboBox Handler Methods in QuickEntryDialog
* **Location:** `wiz/ui/popup_dialog.py:6298-6330`
* **Why Unnecessary:** `_on_project_combo_changed` and `_on_note_project_combo_changed` were written for `QComboBox` dropdowns that offered a `+ Create Section...` item. The UI has since transitioned to `ProjectIconButton` with a dedicated popup menu. These methods are never connected to any signals.
* **Estimated Impact:** Removes 33 lines of dead logic.
* **Pre-Deletion Risks:** None. Verified zero signal connections across the repository.
* **Recommended Cleanup Plan:** Remove the two orphaned methods from `QuickEntryDialog`.

### Issue 1.4: Obsolete Helper Methods on CreateSectionDialog
* **Location:** `wiz/ui/popup_dialog.py:858-868`
* **Why Unnecessary:** `get_section_name` and `get_section_data` are classmethods that wrap `get_section_details`, but neither is ever invoked anywhere in the codebase.
* **Estimated Impact:** Removes 11 lines of dead wrapper code.
* **Pre-Deletion Risks:** Low. Verify callers use `get_section_details`.
* **Recommended Cleanup Plan:** Remove the two obsolete classmethods.

### Issue 1.5: Unused Container Factory Method in SettingsView
* **Location:** `wiz/ui/settings_view.py:384-389`
* **Why Unnecessary:** `_create_card_container` creates an elevated `QFrame` with objectName `"SettingsCard"`, but is never invoked. Setting sections are built directly in `_create_setting_row`.
* **Estimated Impact:** Removes 6 lines of dead code.
* **Pre-Deletion Risks:** None.
* **Recommended Cleanup Plan:** Remove `_create_card_container`.

---

## 2. Duplicate Logic that Should Be Consolidated

### Issue 2.1: Duplicate Icon Assets in Root Assets Directory
* **Location:** Root `assets/` directory vs `assets/icons/`
  - `assets/activity-04.svg` duplicates `assets/icons/activity-04.svg`
  - `assets/cancelled.svg` duplicates `assets/icons/cancelled.svg`
  - `assets/dashboard-2-outline.svg` duplicates `assets/icons/dashboard-2-outline.svg`
  - `assets/in-progress.svg` duplicates `assets/icons/in-progress.svg`
  - `assets/media-media-complete.svg` duplicates `assets/icons/media-media-complete.svg`
  - `assets/notes-bold.svg` duplicates `assets/icons/notes-bold.svg`
  - `assets/status-circle-ring.svg` duplicates `assets/icons/status-circle-ring.svg`
  - `assets/tasklist-24.svg` duplicates `assets/icons/tasklist-24.svg`
* **Why Unnecessary:** When icons were organized into the `assets/icons/` directory, the duplicate files in the `assets/` root were left behind. Both paths exist on disk, creating file confusion and doubling asset payload size.
* **Estimated Impact:** Eliminates 8 redundant SVG files (~4.5 KB) and prevents confusion during asset resolution.
* **Pre-Deletion Risks:** Very low. `config.get_asset_path` automatically falls back to searching `icons/` if the root asset directory does not have the file, and code explicitly requests `"icons/<name>.svg"`.
* **Recommended Cleanup Plan:** Delete the 8 duplicate SVG files from the root `assets/` directory.

### Issue 2.2: Dual Settings Interfaces (SettingsDialog vs SettingsView)
* **Location:** `wiz/ui/settings_dialog.py` (678 lines) vs `wiz/ui/settings_view.py` (1,495 lines)
* **Why Unnecessary:** `SettingsDialog` was the original standalone modal dialog for configuring preferences. It was subsequently replaced by `SettingsView`, which embeds directly inside the widescreen workspace sidebar. However, `SettingsDialog` remains in the codebase and is tested in `tests/test_dialogs.py`.
* **Estimated Impact:** Identifies 678 lines of legacy code for planned deprecation.
* **Pre-Deletion Risks:** High if deleted immediately, as `tests/test_dialogs.py` imports and tests it.
* **Recommended Cleanup Plan:** Document `SettingsDialog` as deprecated. If desired, migrate existing test coverage to `SettingsView` before removing `settings_dialog.py`.

---

## 3. Unused UI Components & Assets

### Issue 3.1: Orphaned and Typo-Named Icons in `assets/icons/`
* **Location:** `assets/icons/`
  - `assets/icons/subttasks.svg` (524 bytes, typo filename with double 't'; actual code uses `assets/icons/subtask.svg`)
  - `assets/icons/stopwatch-icon.svg` (1,239 bytes; actual code uses `assets/icons/stopwatch.svg`)
  - `assets/icons/folder-svgrepo-com.svg` (716 bytes; actual code uses `assets/icons/folder.svg`)
  - `assets/icons/tag-horizontal-svgrepo-com.svg` (2,436 bytes) & `tag-right-svgrepo-com.svg` (679 bytes; actual code uses `assets/icons/tag.svg`)
  - `assets/icons/time-limit-icon.svg` (666 bytes; unreferenced)
* **Why Unnecessary:** These are leftover third-party icon variations downloaded during prototyping and never hooked up to application widgets.
* **Estimated Impact:** Removes ~6.2 KB of orphaned binary asset payload.
* **Pre-Deletion Risks:** None. Verified zero string occurrences in codebase and tests.
* **Recommended Cleanup Plan:** Safely delete the orphaned icon files.

### Issue 3.2: Duplicate Logos in Assets Root
* **Location:** `assets/WizDesk Logo v1.jpeg` (37 KB) and `assets/wizdesk_logo_perfect.png` (155 KB)
* **Why Unnecessary:** WizDesk uses vectorized SVG assets (`wizdesk-logo.svg`, `wiz-idle.svg`) and `wizdesk.ico` for runtime rendering and window icons. The JPEG and large uncompressed PNG are leftover design exports not loaded by application code.
* **Estimated Impact:** Saves ~192 KB of asset space in compiled installer packages.
* **Pre-Deletion Risks:** None for application runtime.
* **Recommended Cleanup Plan:** Move or remove unused promotional rasters from runtime `assets/` directory.

---

## 4. Overly Complex Implementations that Can Be Simplified

### Issue 4.1: Monolithic `popup_dialog.py` File (7,042 Lines, 28 Classes)
* **Location:** `wiz/ui/popup_dialog.py`
* **Why Unnecessary:** `popup_dialog.py` contains 28 distinct UI widget classes spanning:
  1. Date & Calendar utilities (`MonthOnlyCalendarWidget`, `CalendarPopupDialog`)
  2. Section management (`CreateSectionDialog`)
  3. Filter bars (`SegmentedFilterBar`, `TagFilterBar`)
  4. Task controls (`TaskRowWidget`, `SubtaskRowWidget`, `TaskStopwatchWidget`, `SubtaskAddButton`, etc.)
  5. Tag controls (`TagBadgeWidget`, `TagIconChoiceButton`, `TagCreateDialog`, etc.)
  6. Notes system (`NoteRowWidget`, `NoteCardWidget`, `NoteEditorWidget`, `PermanentNotesWorkspaceWidget`)
  7. Main Shell (`QuickEntryDialog`)
  Maintaining 7,042 lines in a single Python file causes editor latency, complicates code reviews, increases merge collision risk, and obscures class dependencies.
* **Estimated Impact:** Splitting `popup_dialog.py` into focused submodules (`wiz/ui/tasks/`, `wiz/ui/notes/`, `wiz/ui/tags/`, `wiz/ui/calendar_popup.py`) will dramatically improve maintainability and testability without changing runtime behavior.
* **Pre-Deletion Risks:** Medium. Requires careful import re-exports in `wiz/ui/popup_dialog.py` so existing tests and consumers continue importing without breakage.
* **Recommended Cleanup Plan:** 
  1. Extract `CalendarPopupDialog` and `MonthOnlyCalendarWidget` to `wiz/ui/calendar_popup.py`.
  2. Extract `CreateSectionDialog` to `wiz/ui/section_dialog.py`.
  3. Extract `TagCreateDialog` and tag badge widgets to `wiz/ui/tag_widgets.py`.
  4. Keep backward-compatibility re-exports in `popup_dialog.py`.

---

## 5. Legacy Code No Longer Needed

### Issue 5.1: Temporary Test Databases in Workspace Root
* **Location:** `test_debug.db` (77 KB) and `test_debug2.db` (77 KB) in project root
* **Why Unnecessary:** These are test SQLite database artifacts left behind during earlier manual debugging runs. Automated tests run against isolated `tmp_path` fixtures and do not touch these files.
* **Estimated Impact:** Cleans 154 KB of leftover binary clutter from the repository root.
* **Pre-Deletion Risks:** Zero risk.
* **Recommended Cleanup Plan:** Delete `test_debug.db` and `test_debug2.db`.

### Issue 5.2: Note on Light Mode Preservation
* **Location:** Across UI stylesheets and theme logic
* **Status:** **PRESERVED INTENTIONALLY per user directive.**
* **Context:** The user instructed: *"the light mode is not optimized and its not good so remove it from use but not fully remove the code, we can optimize the light mode and add in future release"*. All light mode palettes, styles, and rendering methods are retained intact for future optimization.

---

## 6. Redundant Database Queries or I/O Calls

### Issue 6.1: N+1 Query Loop in `get_projects_overview_metrics`
* **Location:** `wiz/storage/models.py:1685-1746`
* **Why Unnecessary:** When loading the Projects dashboard overview, `get_projects_overview_metrics` retrieves all projects, and then inside a `for proj in projects:` loop, executes:
  1. `SELECT app_name, start_time, end_time FROM sessions WHERE project_tag = ? ...`
  2. `SELECT id, status FROM tasks WHERE project_tag = ? ...`
  For $N$ projects, this executes $2N$ sequential SQLite queries. When database encryption (AES-256-GCM) is enabled, each query cycle incurs synchronization overhead.
* **Estimated Impact:** Replaces $2N$ queries with exactly 2 batched queries (`SELECT ... FROM sessions WHERE project_tag IN (...)` and `SELECT ... FROM tasks WHERE project_tag IN (...)`), reducing database round-trips by up to 90% on multi-project environments.
* **Pre-Deletion Risks:** Low. Requires aggregating results in Python dictionaries grouped by `project_tag`.
* **Recommended Cleanup Plan:** Refactor `get_projects_overview_metrics` to batch fetch all matching session rows and task rows, group by `project_tag` in-memory, and compute metrics per project.

---

## 7. Abandoned or Disconnected Files

### Issue 7.1: Accumulation of Scratch Scripts and Render Artifacts
* **Location:** `scratch/` directory (342 files, ~20+ MB)
* **Why Unnecessary:** `scratch/` contains dozens of one-off image crop prototypes, test renders, font verification scripts, and 7 abandoned test databases (`preview_calendar.db`, `preview_help.db`, `preview_nav.db`, `test.db`, `test_db.sqlite`, `test_spacing.db`, `readme_demo.db`).
* **Estimated Impact:** Huge reduction in git repository size and workspace file count.
* **Pre-Deletion Risks:** Low for runtime (none of `wiz/` imports from `scratch/`).
* **Recommended Cleanup Plan:** Archive or clean obsolete test databases and temporary crop images. Ensure `.gitignore` ignores `scratch/*.db` and `scratch/*.png`.

---

## 8. Technical Debt & Release / Packaging Readiness

### Issue 8.1: Package Size Optimization in PyInstaller Build Spec
* **Location:** `wizdesk.spec:11-15`
* **Why Unnecessary / Deficit:** `wizdesk.spec` bundles `('assets', 'assets')` wholesale. Because root `assets/` contains redundant SVG copies of icons and large unused JPEG/PNG promotional images, these are bundled into the final `.exe` distribution directory.
* **Estimated Impact:** Reduces compiled distribution package size and eliminates duplicate asset files in the packaged bundle.
* **Pre-Deletion Risks:** None. Asset resolution via `config.get_asset_path` is already frozen-executable aware.
* **Recommended Cleanup Plan:** Clean up the duplicate and unused assets prior to building the distribution executable.

### Issue 8.2: Separation of Dev/Test Tooling in Dependency Manifest
* **Location:** `requirements.txt:12-14`
* **Why Unnecessary:** `requirements.txt` currently mixes runtime dependencies (`PyQt6`, `psutil`, `cryptography`) with developer and build tools (`pytest`, `pyinstaller`).
* **Estimated Impact:** Clear separation allows production environments to install only runtime dependencies.
* **Pre-Deletion Risks:** None.
* **Recommended Cleanup Plan:** Separate into `requirements.txt` (runtime) and `requirements-dev.txt` (dev/build/test).

---

## Summary of Cleanup Leverage

| Area | Issues Identified | Estimated Code/Asset Reduction | Performance / Reliability Gain |
|---|---|---|---|
| **Dead Code** | 5 issues (imports, stubs, obsolete handlers) | ~84 LOC deleted | Cleaner namespaces, faster imports, zero lint warnings |
| **Duplicate Logic** | 2 issues (root SVGs, dual dialogs) | ~8 redundant files | Prevents asset divergence, clear source of truth |
| **Unused UI / Assets** | 2 issues (orphaned icons, raster logos) | ~200 KB asset reduction | Cleaner asset tree, smaller distribution bundle |
| **Complexity & Monoliths** | 1 issue (`popup_dialog.py` 7K LOC) | Architecture refactoring | Better modularity, easier maintenance and testing |
| **Legacy Code** | 2 issues (root `.db` files, deprecated dialog) | 154 KB disk cleanup | Clean workspace, zero orphaned test databases |
| **Database & I/O** | 1 issue (N+1 query in project metrics) | $2N \to 2$ queries | Up to 90% reduction in query round-trips for projects |
| **Abandoned Files** | 1 issue (`scratch/` databases & debris) | ~20 MB cleanup | Drastically cleaner repository footprint |
| **Technical Debt & Packaging**| 2 issues (spec bundling, dev requirements) | Packaging optimization | Leaner distribution `.exe`, clear dependency contracts |

---

## Phased Action Plan

### Tier 1: Safe Surgical Cleanups (Zero Risk)
1. Delete temporary SQLite databases in root: `test_debug.db` and `test_debug2.db`.
2. Remove 34 unused imports across the 12 identified `.py` files.
3. Remove dead slot stubs:
   - `_on_tag_filter_combo_changed` and `_on_detail_tag_filter_combo_changed` in `wiz/ui/calendar_view.py`.
   - `_on_project_combo_changed` and `_on_note_project_combo_changed` in `wiz/ui/popup_dialog.py`.
   - `get_section_name` and `get_section_data` in `wiz/ui/popup_dialog.py`.
   - `_create_card_container` in `wiz/ui/settings_view.py`.
4. Delete duplicate root SVGs in `assets/` and orphaned icons in `assets/icons/`.

### Tier 2: Database I/O Optimization (Batching N+1 Queries)
1. Refactor `StorageRepository.get_projects_overview_metrics()` to execute 2 batched queries instead of $2N$ queries.
2. Verify all project dashboard tests pass without regression.

### Tier 3: Packaging & Dependency Optimization
1. Separate `requirements.txt` (runtime) and `requirements-dev.txt` (testing & packaging).
2. Clean `scratch/*.db` leftover databases.

### Tier 4: Verification Gate
1. Execute full test suite (`pytest -q`).
2. Verify 100% of tests (234+ tests) continue to pass.
3. Verify application launches cleanly with `.venv\Scripts\python -m wiz`.
