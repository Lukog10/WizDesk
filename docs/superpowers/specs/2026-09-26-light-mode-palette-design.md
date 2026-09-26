# Design Specification: Crisp Light Mode White Palette (Polymet-Based)

**Date**: 2026-09-26  
**Author**: DeepMind Antigravity / Pair Programming Agent  
**Status**: Draft - Pending User Final Review  
**Spec Location**: `docs/superpowers/specs/2026-09-26-light-mode-palette-design.md`

---

## 1. Overview & Goals

The Light Mode theme in WizDesk currently relies on warm, yellowish-cream and sandy beige tones (`#E8E4DC`, `#F6F4EE`, `#EDE9E0`, `#D5CEC2`, `#DFD9CE`). In practice, these warm parchment tones appear dull, muddy, and visually heavy compared to modern, crisp desktop applications.

The goal of this specification is to modernize WizDesk's Light Mode into a clean, tech-forward, high-contrast white aesthetic inspired by the Polymet design system reference:

1. **Pure Crisp White Surfaces**: Elevated workspace containers, main cards, and dialog bodies use `#FFFFFF` for maximum clarity and freshness.
2. **Clean Neutral Grey Frame**: Outer canvases and parent container frames use a cool, neutral light grey (`#F4F4F6`), completely free of any yellow, sand, or beige undertones.
3. **High-Contrast Typography**: Headings and titles use deep graphite `#18181B`, while secondary metadata uses cool slate `#71717A`.
4. **Hairline Subtle Borders**: Delimiting lines use neutral `#E4E4E7` and `#E5E5EA` to provide crisp structural separation without heavy visual borders.
5. **Strict Accent Preservation**: All existing brand orange, rust, and terracotta accent colors (`#BA3F1A`, `#C2410C`, `#FF6B3D`, and their active/hover shades) remain 100% unchanged.
6. **Strict Layout Preservation**: Zero changes to component layouts, padding, margins, border radii, or widget hierarchies. Only color tokens (hex/rgba) are modified.

---

## 2. Token Specification & Color Mapping

### 2.1 Surface & Container Tokens

| Token Role | Old Value (Dull / Sandy) | New Value (Crisp White / Cool Grey) | Purpose & Usage |
| :--- | :--- | :--- | :--- |
| `outer_bg` | `#E8E4DC` (sand) | `#F4F4F6` | Outer dialog canvas frame |
| `outer_border` | `#D5CEC2` / `#D6D0C5` | `#E4E4E7` | Perimeter border of outer frame |
| `inner_bg` | `#F6F4EE` (cream parchment) | `#FFFFFF` | Main elevated inner card surface |
| `inner_border` | `#DFD9CE` / `#E2DDD3` | `#E5E5EA` | Boundary border of inner card |
| `input_bg` | `#EDE9E0` (clay sand) | `#F4F4F6` | Text fields, combo boxes, spin boxes |
| `input_border` | `#D6D0C5` | `#E4E4E7` | Border around input fields |
| `mode_capsule_bg` | `#E6E1D7` | `#F0F0F2` | Segmented filter bar and pill backgrounds |
| `btn_neutral_bg` | `#EDE7DC` / `#EBE6DC` | `#F4F4F6` | Secondary button backgrounds ("Browse", "Cancel") |
| `btn_neutral_border`| `#D6D0C5` | `#E4E4E7` | Secondary button borders |
| `hover_bg` | `#EBE6DC` / `#DAD5CB` | `rgba(0, 0, 0, 0.05)` | Hover state for day buttons, list rows, nav pills |

### 2.2 Typography & Icon Tokens

| Token Role | Old Value (Warm / Stone) | New Value (Cool / Neutral) | Purpose & Usage |
| :--- | :--- | :--- | :--- |
| `text_primary` | `#242220` (warm brown-black) | `#18181B` | Page titles, primary task labels, headings |
| `text_secondary` | `#57534E` / `#78716C` (stone) | `#71717A` | Subtitles, date buttons, inactive icons, hints |
| `icon_inactive` | `#78716C` / `#9CA3AF` | `#71717A` | Inactive navigation and toolbar icons |
| `icon_hover` | `#18181B` | `#18181B` | Hovered navigation icons |

### 2.3 Brand & Accent Tokens (Strictly Preserved)

The following tokens represent WizDesk's established brand identity and are retained without any modification:

| Token Role | Value (Light Mode) | Value (Dark Mode) | Status |
| :--- | :--- | :--- | :--- |
| `today_pill_bg` | `#BA3F1A` | `#C2410C` | Preserved |
| `btn_action_bg` | `#BA3F1A` | `#C2410C` | Preserved |
| `btn_action_hover` | `#9E3414` | `#A3360E` | Preserved |
| `input_focus_border` | `#BA3F1A` | `#C2410C` | Preserved |
| `sidebar_active_accent` | `#BA3F1A` / `#FF6B3D` | `#C2410C` / `#FF6B3D` | Preserved |
| `combo_popup_sel_bg` | `#FEECE5` | `rgba(194, 65, 12, 0.22)` | Preserved |
| `combo_popup_sel_text` | `#BA3F1A` | `#FFAB91` | Preserved |

---

## 3. UI Component Scope & Implementation Targets

### 3.1 QuickEntryDialog (`wiz/ui/popup_dialog.py`)
- **`outer_frame`**: Updates to `background-color: #F4F4F6; border: 1px solid #E4E4E7;`.
- **`inner_card`**: Updates to `background-color: #FFFFFF; border: 1px solid #E5E5EA;`.
- **Title & Controls**: `page_title_color = #18181B`, `ctrl_btn_color = #71717A`, `ctrl_btn_hover_bg = rgba(0, 0, 0, 0.05)`.
- **Date Selector**: `mode_capsule_bg = #F0F0F2`, `day_btn_color = #71717A`, `day_btn_border = #E4E4E7`, `day_btn_hover_bg = #EAEAEB`. "Today" pill remains `#BA3F1A`.
- **Task Inputs**: `input_bg = #F4F4F6`, `input_border = #E4E4E7`, `input_color = #18181B`. Focus border remains `#BA3F1A`.
- **Action Button ("Add")**: Background remains `#BA3F1A`, hover remains `#9E3414`.
- **Segmented Filter Bar**: Capsule container background `rgba(0, 0, 0, 0.04)` or `#F0F0F2`, border `#E4E4E7`. Active tab background `#FFFFFF`, text `#18181B`, border `#E4E4E7`. Inactive tab text `#71717A`.
- **Task Rows (`TaskRowWidget`)**: Clean `#FFFFFF` canvas, `rgba(0, 0, 0, 0.03)` row hover background, subtle `#E4E4E7` divider lines.

### 3.2 SideNavBar (`wiz/ui/sidebar_widget.py`)
- **Background**: Seamlessly aligns with `#F4F4F6`.
- **Inactive Nav Items**: Text and icons set to `#71717A`.
- **Hover Nav Items**: Translucent `rgba(0, 0, 0, 0.05)` pill with `#18181B` text.
- **Active Nav Item**: Elevated `#FFFFFF` pill with preserved `#BA3F1A` / `#FF6B3D` accent bar and dot.
- **Toggle Button & Badges**: Clean neutral `rgba(0, 0, 0, 0.06)` pills, `hover_bg = #EAEAEB`, normal foreground `#71717A`.

### 3.3 SettingsDialog & SettingsView (`wiz/ui/settings_dialog.py`, `wiz/ui/settings_view.py`)
- **Window & Container**: `outer_bg = #F4F4F6`, `outer_border = #E4E4E7`, `inner_bg = #FFFFFF`, `inner_border = #E5E5EA`.
- **Inputs & Combos**: `input_bg = #F4F4F6`, `input_border = #E4E4E7`, `text = #18181B`, `subtext = #71717A`. Focus border remains `#BA3F1A`.
- **Secondary Buttons**: `btn_neutral_bg = #F4F4F6`, `btn_neutral_border = #E4E4E7`, `btn_neutral_hover_bg = #EAEAEB`.

### 3.4 QuickBarDialog (`wiz/ui/quick_bar_dialog.py`)
- **Card Surface**: `card_bg = #FFFFFF`, border `#E5E5EA`.
- **Input Background**: `#F4F4F6` with `#E4E4E7` border.

### 3.5 Timeline & Dashboard Views (`wiz/ui/timeline_view.py`, `wiz/ui/projects_dashboard_view.py`)
- **Cards**: Background `#FFFFFF`, border `#E5E5EA`.
- **Labels & Metas**: Primary `#18181B`, secondary `#71717A`.

---

## 4. Verification & Testing Strategy

### 4.1 Automated Test Suite
- Run `pytest` to execute all 116 existing unit tests.
- Verify that theme toggling (`set_theme(False)` and `set_theme(True)`) works seamlessly without runtime styling errors or attribute crashes.

### 4.2 Visual Verification Script
- Execute a headless Qt script (`scratch/verify_light_palette.py`) that instantiates `QuickEntryDialog`, `SideNavBar`, and `SettingsDialog` in Light Mode (`is_dark=False`).
- Capture screenshots and programmatically inspect pixel values to ensure:
  - No `#E8E4DC` (sand) remains on `outerFrame`.
  - No `#F6F4EE` (cream) remains on `innerCard`.
  - Inner card background evaluates to pure `#FFFFFF`.
  - Action button and active indicators remain `#BA3F1A` / `#FF6B3D`.

---

## 5. Non-Goals & Invariants

- **No Layout Alterations**: Zero changes to sizes, heights, paddings, margins, or flex alignments.
- **No Dark Mode Changes**: Dark mode tokens (`#121214`, `#18181B`, `#27272A`, `#F4F4F5`) remain untouched.
- **No Icon Replacement**: Existing SVG icons and icon rendering logic remain intact.
- **No Accent Alteration**: All orange, terracotta, and rust accent colors are preserved.
