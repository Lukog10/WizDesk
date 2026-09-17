# Widescreen Shell and Sidebar Navigation Design Specification

## 1. Overview and Goals
This specification details the structural transformation of the WizDesk main workspace (`QuickEntryDialog`) from a narrow vertical pop-up (640x800) to a modern, widescreen executive desktop application shell (920x680) featuring an integrated Left Side Navigation Bar.

Key objectives:
- Provide a persistent, ergonomic Left Side Navigation Bar (~190px width) housing branding, navigation items with dynamic status badges, settings, and theme toggle.
- Provide a spacious Right Main Workspace (~710px width) housing a unified top header (dynamic page title, contextual controls, frameless window controls) and a 5-view stacked workspace.
- Embed Settings directly into the central view stack as a 5th view, eliminating disjointed modal dialogs.
- Adhere strictly to WizDesk brand colors: Indigo `#6366F1`, active `#4F46E5`, glow `#818CF8`, success emerald `#10B981`, and tailored dark/light surface tokens.
- Maintain zero scrolling on the Projects Dashboard at 920x680 resolution while preserving smooth internal scrolling for long lists in Tasks and Notes.

## 2. Brand Color Palette and Tokens

### 2.1 Accent and State Colors
- Primary Brand Accent: `#6366F1` (Indigo 500)
- Active / Pressed Accent: `#4F46E5` (Indigo 600)
- Hover / Focus Glow: `#818CF8` (Indigo 400)
- Success / Live Tracking Dot: `#10B981` (Emerald 500)
- Badge Background (Dark): `rgba(99, 102, 241, 0.20)` with text `#A5B4FC`
- Badge Background (Light): `#EEF2FF` with text `#4F46E5`

### 2.2 Dark Theme Palette
- Outer Frame / Shell Background: `#121214`
- Outer Frame Border: `#27272A`
- Left Sidebar Background: `#16161A`
- Sidebar Border Separator: `#232328`
- Right Workspace Inner Card Background: `#18181B`
- Card and Panel Border: `#27272A`
- Primary Typography: `#F4F4F5`
- Secondary / Muted Typography: `#A1A1AA`
- Tertiary / Caption Typography: `#71717A`
- Nav Pill Hover Background: `rgba(255, 255, 255, 0.05)`
- Nav Pill Active Background: `rgba(99, 102, 241, 0.14)`
- Nav Pill Active Border: `3px solid #6366F1` (left edge)

### 2.3 Light Theme Palette
- Outer Frame / Shell Background: `#F0EFEB`
- Outer Frame Border: `#D8D8DE`
- Left Sidebar Background: `#F8F7F4`
- Sidebar Border Separator: `#E5E0D8`
- Right Workspace Inner Card Background: `#FFFFFF`
- Card and Panel Border: `#ECECEF`
- Primary Typography: `#18181B`
- Secondary / Muted Typography: `#71717A`
- Tertiary / Caption Typography: `#A1A1AA`
- Nav Pill Hover Background: `rgba(0, 0, 0, 0.04)`
- Nav Pill Active Background: `#EEF2FF`
- Nav Pill Active Border: `3px solid #6366F1` (left edge)

## 3. Architecture and Component Hierarchy

### 3.1 Window Geometry
- Default Dimensions: 920px width x 680px height.
- Minimum Dimensions: 780px width x 560px height.
- Screen Adaptation: On smaller displays (height < 740px), the initial height is clamped to `min(680, max(560, screen_height - 60))`.

### 3.2 Layout Structure (`QuickEntryDialog`)
```
+------------------------------------------------------------------------------------------------+
| Outer Frame (Frameless, Rounded 20px, Subtle Drop Shadow)                                       |
| +-------------------------+------------------------------------------------------------------+ |
| | Left Sidebar (~190px)   | Right Main Workspace (~710px)                                    | |
| |                         |                                                                  | |
| | [Logo] WizDesk  (dot)   | [Dynamic Title]        [Contextual Controls]      [-  □  x]      | |
| |                         | ---------------------------------------------------------------- | |
| | -- Navigation --        |                                                                  | |
| | [ ] Tasks          (3)  |  Stacked Widget (5 Pages):                                       | |
| | [ ] Quick Notes         |  - Page 0: Tasks View                                            | |
| | [ ] Activity            |  - Page 1: Quick Notes View                                      | |
| | [ ] Projects            |  - Page 2: Activity Timeline View                                | |
| |                         |  - Page 3: Projects Dashboard View                               | |
| |                         |  - Page 4: Embedded Settings View                                | |
| | (stretch)               |                                                                  | |
| |                         |                                                                  | |
| | ----------------------- |                                                                  | |
| | [ ] Settings            |                                                                  | |
| | [ Theme Toggle ☀/☾ ]    |                                                                  | |
| +-------------------------+------------------------------------------------------------------+ |
+------------------------------------------------------------------------------------------------+
```

### 3.3 Component Breakdown

#### 3.3.1 `SideNavBar` (`wiz/ui/sidebar_widget.py`)
- Inherits from `QWidget` with a fixed width of 190px.
- Sections:
  1. Brand Header:
     - App icon or mascot avatar (24x24px).
     - "WizDesk" typography in semi-bold 13pt.
     - Live status pulse indicator (green dot `#10B981`).
  2. Navigation Items:
     - `nav_changed = pyqtSignal(str)` emitted with mode identifier (`tasks`, `notes`, `activity`, `projects`, `settings`).
     - Items implemented as custom pill buttons (`NavPillButton`) with left icon, label text, and optional counter badge.
     - `Tasks` pill displays an active task badge count (updated whenever tasks are loaded or changed).
  3. Bottom Utilities:
     - `Settings` pill button.
     - Mode/Theme toggle button (`☀` / `☾`) with smooth tooltip and hover styling.
- Signals:
  - `mode_selected(str)`: Emits target mode name.
  - `theme_toggle_requested()`: Emits request to switch light/dark theme.

#### 3.3.2 Unified Top Header (`QuickEntryDialog`)
- Sits above the central stacked widget on the right side.
- Left: Dynamic page title (`Tasks & To-Dos`, `Quick Notes`, `Activity Timeline`, `Projects Dashboard`, `Settings & Preferences`).
- Center / Right: Contextual controls:
  - For `Tasks`: Date navigator (`<`, `Today`, `>`) and Calendar picker button.
  - For `Activity`: Date navigator (`<`, `Today`, `>`) and Calendar picker button.
  - For `Projects`: Timeframe switcher capsule (`Today`, `Week`, `Month`) and `+ New Project` button.
  - For `Notes`: Search/filter input or clear notes action.
  - For `Settings`: Status label (`All settings saved`).
- Far Right: Frameless window controls (`-` minimize, `□` maximize/restore, `x` close).

#### 3.3.3 Embedded Settings View (`wiz/ui/settings_view.py`)
- Replaces the separate modal popup dialog with an in-window view.
- Contains:
  1. Obsidian Vault Integration: Vault path text input with Browse button.
  2. Tracking Preferences: Floating bob animation toggle, dark mode toggle, auto-tracking interval spinbox (1 to 120 minutes).
  3. Project Auto-Tagging Keywords: Editable table with Project Name and Keywords, plus Add Project and Remove Selected buttons.
  4. Save Action Button: Clean action button with feedback badge.
- `SettingsDialog` in `wiz/ui/settings_dialog.py` is maintained for backwards compatibility.

#### 3.3.4 Projects Dashboard Integration
- Inside the 710px wide right workspace:
  - Top: 4 KPI cards in a 4-column row (spacious ~165px per card).
  - Main Body: 2-column layout:
    - Left Column (~420px): Project Comparison Chart Canvas (generous landscape aspect ratio for 7-day columns, hover crosshairs, rich tooltips).
    - Right Column (~275px): App Usage Donut Canvas (116x116px) and Project Target progress bars.
  - Fits comfortably within 680px total dialog height with zero scrolling.

## 4. Verification and Testing Plan

### 4.1 Automated Tests
- Test sidebar widget instantiation, item selection, and signal emissions (`tests/test_sidebar_and_shell.py`).
- Test `QuickEntryDialog` 920x680 dimensions, view mode transitions across all 5 pages, and badge updates.
- Test `SettingsView` loading, editing, and saving without modal dialogs.
- Run full existing test suite (`pytest -v`) to ensure no regressions across dashboard, timeline, or storage.

### 4.2 Visual and Interactive Verification
- Render screenshots for all 5 views in both Dark Mode and Light Mode.
- Verify zero scrollbar presence on the Projects Dashboard.
- Verify active pill accent styling with `#6366F1` 3px left border and theme consistency.
