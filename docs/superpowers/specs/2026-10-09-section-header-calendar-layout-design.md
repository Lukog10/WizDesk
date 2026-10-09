# Section Header and Calendar Date Navigator Layout Design Specification

## 1. Overview and Problem Statement

In WizDesk, the main workspace layout previously suffered from fragmented visual hierarchy in the Tasks, Notes, and Activity views:
1. **Disconnected Section Title**: The dynamic page title (`Tasks & To-Dos`, `Quick Notes`, `Activity Timeline`) was placed in the outer window bar (`top_bar`) outside the main content card (`inner_card`), making it appear detached from the content it labels.
2. **Floating Centered Date Navigator**: Inside `inner_card`, the date navigation controls (`< October 09, Friday >`) were centered horizontally, floating with dead space on both sides instead of anchoring the content like the Calendar section.
3. **Chunky Outer Window Chrome**: The outer window controls (`−`, `✕`) were 28x28 px with a 12px top margin and 8px spacing, consuming ~38px of vertical height that could otherwise be used for active tasks, notes, and activity logs.

This specification unifies the header hierarchy:
- Section titles move inside the content card at the top-left in bold display typography.
- The date navigator moves directly below the section title into the left corner, adopting Calendar-view chevron buttons (`‹` and `›`).
- The outer window chrome is slimmed into an unobtrusive ~24px drag bar with compact 22x22 px window controls.
- The inner card expands vertically, regaining ~14px of usable workspace.
- The status filter capsules (`Task`, `In progress`, `Completed`, `Cancelled`) remain untouched.

---

## 2. Layout Architecture and Hierarchy

### 2.1 Workspace Container (Outer Layer)

The outer container `self.workspace_layout` (in `QuickEntryDialog`) is streamlined:
- **Margins**: Reduced from `(16, 12, 16, 14)` to `(16, 6, 16, 12)`.
- **Spacing**: Reduced from `8px` to `4px`.
- **Top Bar (`top_bar`)**:
  - `page_title_lbl` is removed from `top_bar` and reparented inside the inner card.
  - `top_bar` contains `top_bar.addStretch()` followed by `controls_layout` containing `min_btn` and `close_btn`.
  - Window dragging (`_is_in_draggable_area`) continues to function across the entire top bar area.
- **Window Controls (`min_btn`, `close_btn`)**:
  - Button fixed size: **22x22 px** (down from 28x28 px).
  - Border radius: **11px** (circular / soft pill).
  - Minimize symbol `−`: font-size **13px bold**.
  - Close symbol `✕`: font-size **11px bold**.
  - Hover background: subtle rgba overlay matching current styling.

### 2.2 Inner Content Card (`inner_card`)

The inner card layout `self.inner_layout` holds the content stack and the new unified card header:
- **Margins**: `(14, 10, 14, 10)`.
- **Card Header Container (`card_header_widget`)**:
  - Inserted at index 0 of `self.inner_layout`.
  - Layout: `QVBoxLayout` with `(0, 0, 0, 4)` margins and `6px` spacing.
  - **Row 1 - Section Title**:
    - `page_title_lbl`: Left-aligned QLabel with `get_font(15, QFont.Weight.Bold, display=True)`.
    - Text automatically updates per mode (`Tasks & To-Dos`, `Quick Notes`, `Activity Timeline`, etc.).
  - **Row 2 - Date Navigator (`date_header_container`)**:
    - Left-aligned `QHBoxLayout` with `8px` spacing.
    - `prev_day_btn`: Fixed size 28x28 px, text updated to `‹` (matching Calendar view), font size 14px bold, radius 6px.
    - `date_btn`: Formatted date text (e.g. `October 09, Friday`), font size 13px semi-bold, left-padded.
    - `next_day_btn`: Fixed size 28x28 px, text updated to `›`, font size 14px bold, radius 6px.
    - `today_pill_btn`: Height 24px, text `Today`, font size 11px bold, radius 6px (visible when viewing past/future dates).
    - `addStretch()` at the right edge so the navigator sits snug in the left corner.
  - **Row 3 / Below Header**:
    - In Tasks View: `SegmentedFilterBar` (`filter_bar`) sits directly below the header, completely untouched.
    - In Notes View: Notes sub-stack / list sits directly below.
    - In Activity View: Timeline widget sits directly below.

---

## 3. View Mode Visibility Matrix

| Mode | `page_title_lbl` | `date_header_container` | Header Container Visible? | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Tasks** (`tasks`) | Visible ("Tasks & To-Dos") | Visible | Yes | Standard 2-row card header + filter pills |
| **Notes** (`notes`) | Visible ("Quick Notes") | Visible | Yes | Standard 2-row card header |
| **Activity** (`activity`) | Visible ("Activity Timeline") | Visible | Yes | Standard 2-row card header |
| **Calendar** (`calendar`) | Hidden (or custom) | Hidden | Hidden | Calendar has dedicated full-month header |
| **Projects** (`projects`) | Visible ("Projects Dashboard") | Hidden | Yes (Title only) | Single title row inside card |
| **Settings** (`settings`) | Visible ("Settings & Preferences") | Hidden | Yes (Title only) | Single title row inside card |
| **Help** (`help`) | Visible ("Help & Documentation") | Hidden | Yes (Title only) | Single title row inside card |

---

## 4. Theme & Styling Specification (QSS)

### 4.1 Window Controls (22x22 px)
```css
QPushButton#minBtn {
    background-color: transparent;
    color: var(--ctrl-btn-color);
    border: none;
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: bold;
    border-radius: 11px;
}
QPushButton#minBtn:hover {
    background-color: var(--ctrl-btn-hover-bg);
    color: var(--ctrl-btn-hover-color);
}
QPushButton#closeBtn {
    background-color: transparent;
    color: var(--ctrl-btn-color);
    border: none;
    font-family: var(--font-sans);
    font-size: 11px;
    font-weight: bold;
    border-radius: 11px;
}
QPushButton#closeBtn:hover {
    background-color: rgba(239, 68, 68, 0.20);
    color: #EF4444;
}
```

### 4.2 Date Navigation Chevron Buttons (28x28 px)
```css
QPushButton {
    background: transparent;
    color: var(--day-btn-color);
    border: 1px solid var(--day-btn-border);
    border-radius: 6px;
    font-family: var(--font-sans);
    font-size: 14px;
    font-weight: bold;
}
QPushButton:hover {
    color: var(--day-btn-hover-color);
    background-color: var(--day-btn-hover-bg);
    border-color: var(--input-focus-border);
}
```

---

## 5. Verification & Testing Plan

1. **Automated Unit Tests**:
   - `test_section_header_layout_hierarchy`: Verifies `page_title_lbl` and `date_header_container` reside inside `inner_card`.
   - `test_window_controls_dimensions`: Verifies `min_btn` and `close_btn` have fixed size `(22, 22)`.
   - `test_header_visibility_per_mode`: Verifies mode switches toggle `date_header_container` visibility appropriately (`tasks`, `notes`, `activity` visible; `projects`, `calendar`, `settings`, `help` hidden).
   - `test_date_navigation_chevrons`: Verifies `prev_day_btn` and `next_day_btn` use `‹` and `›` characters and 28x28 fixed size.
2. **Visual & Regression Verification**:
   - Verify all 208+ repo tests pass without failures.
   - Verify smooth theme switching between Dark and Light palettes.
   - Verify window drag-to-move remains fully responsive.
