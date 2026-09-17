# Dashboard DealDeck Two-Column Layout Design Specification

## 1. Overview and Goals
This specification defines the layout reorganization of the WizDesk Projects Dashboard (`ProjectsOverviewPage`) to match the DealDeck executive dashboard structure:
- **Left Column (~58% width)**:
  - Top: 4 KPI stat cards arranged in a **2 by 2 grid** (`Tracked Time`, `Active Projects`, `Top Application`, `Tasks Completed`).
  - Bottom: **Project Comparison Bar Chart** ("Statistics") positioned directly underneath the 2x2 KPIs, spanning the full width of the left column.
- **Right Column (~42% width)**:
  - Top Card: **Application Usage Distribution Card** ("Distribution") with Donut / Bar toggle, 116x116px Donut canvas, and 2-column app legend.
  - Bottom Card: **Project Tracking Card** ("Project Tracking") featuring an active project counter badge, subtitle, and vertical list of project progress bar tracks matching the reference design.
- **Zero Scrollbars**: Complete elimination of outer vertical scrolling within the 920x680 window geometry.

## 2. Structural Architecture

```
+---------------------------------------------------------------------------------------------------+
| Toolbar: [Today] [This Week] [This Month] [All Time]                           [+ New Project]    |
+-----------------------------------------------------------------+---------------------------------+
| LEFT COLUMN (~58% width, ~390px)                                | RIGHT COLUMN (~42% width, ~280px)|
|                                                                 |                                 |
| [ 2x2 KPI GRID ]                                                | [ CARD 1: APP DISTRIBUTION ]    |
| +-----------------------------+-------------------------------+ | +-----------------------------+ |
| | KPI 1: Tracked Time (Hero)  | KPI 2: Active Projects        | | | Distribution (Donut / Bar)  | |
| | 20.2h  [+2.08%]             | 3  [Active]                   | | |     ( ( 20.2h ) )           | |
| +-----------------------------+-------------------------------+ | | • VS Code 43% • WebStorm 30%| |
| | KPI 3: Top Application      | KPI 4: Tasks Completed        | | +-----------------------------+ |
| | VS Code 8.8h                | 2 / 4  [50%] [====    ]       | |                                 |
| +-----------------------------+-------------------------------+ | [ CARD 2: PROJECT TRACKING ]   |
|                                                                 | +-----------------------------+ |
| [ PROJECT COMPARISON BAR CHART ("Statistics") ]                 | | Project Tracking  [3 Active]| |
| +-------------------------------------------------------------+ | | • Client Portal   7.5h (37%)| |
| | Statistics  20.2h Tracked Hours | 6.2h Peak     [Bar] [Area]| | |   [=============          ] | |
| |                                                             | | | • WizDesk Core   10.2h (51%)| |
| |   ||  ||  ||  ||  ||  ||  ||  (Hover Crosshair & Tooltip)   | | |   [==================     ] | |
| |  Mon Tue Wed Thu Fri Sat Sun                                | | | • Infrastructure 2.5h (12%) | |
| +-------------------------------------------------------------+ | |   [====                   ] | |
|                                                                 | +-----------------------------+ |
+-----------------------------------------------------------------+---------------------------------+
```

## 3. Component Details

### 3.1 Left Column: 2x2 KPI Grid
- Managed via `QGridLayout` with `rowSpacing=6` and `colSpacing=6`:
  - `(0, 0)`: `KpiStatCard` ("Tracked Time", hero styling with royal indigo gradient `#4F46E5` -> `#3730A3` and micro-sparkline).
  - `(0, 1)`: `KpiStatCard` ("Active Projects", count with "Active" pill).
  - `(1, 0)`: `KpiStatCard` ("Top Application", app name and hours with percentage subtitle).
  - `(1, 1)`: `KpiStatCard` ("Tasks Completed", ratio and percentage with inline 4px progress bar).
- Card Height: ~78px each.
- Total Grid Height: ~165px.

### 3.2 Left Column: Project Comparison Bar Chart (`ProjectComparisonChartWidget`)
- Placed directly underneath the 2x2 KPI grid within the left column.
- Features:
  - Header: "Statistics", tracked hours sum, peak period metrics, Bar/Area toggle capsule.
  - Interactive Canvas: Grouped bar columns with background day slots, mouse-tracked vertical dashed crosshair, and floating glassmorphic tooltip card.
  - Footer: Project color legend items with hours.
- Card Height: ~345px.

### 3.3 Right Column: Application Usage Distribution Card (`AppUsageAnalyticsWidget`)
- Standalone top card in the right column.
- Features:
  - Header: "Distribution" title and Donut/Bar toggle capsule.
  - Interactive Donut Canvas: 116x116px antialiased donut with hovered segment spotlighting and center total hours label.
  - Micro Legend: Compact 2-column grid showing top applications with color dots, names, and percentage shares.
- Card Height: ~255px.

### 3.4 Right Column: Project Tracking Card (`ProjectTrackingCard`)
- Standalone bottom card in the right column (split from the old combined widget into a dedicated card matching DealDeck).
- Features:
  - Header: "Project Tracking" title + active project count badge (e.g., "3 Active").
  - Subtitle: "Track time and progress by project".
  - Vertical list of `ProjectTargetRow` widgets:
    - Left: Project color dot + Project name.
    - Right: Tracked hours + percentage share pill.
    - Track: 6px rounded horizontal progress bar filled with project color and subtle background track.
  - Click on row emits `project_selected(str)` for drill-down details.
- Card Height: ~255px.

## 4. Brand Colors and Theming
- Primary Accent: `#6366F1` (Indigo)
- Active States: `#4F46E5`
- Focus / Hover: `#818CF8`
- Live / Success: `#10B981` (Emerald)
- Dark Palette:
  - Card background: `#18181B`
  - Borders: `#27272A`
  - Primary text: `#F4F4F5`, Secondary text: `#A1A1AA`
- Light Palette:
  - Card background: `#FFFFFF`
  - Borders: `#ECECEF`
  - Primary text: `#18181B`, Secondary text: `#71717A`

## 5. Verification Plan
- **Automated Tests**:
  - Verify 2x2 KPI grid instantiation and data population.
  - Verify left column housing KPIs and comparison chart.
  - Verify right column housing separate app donut card and project tracking card.
  - Run all tests in `tests/test_projects_dashboard.py` and full suite with `pytest`.
- **Visual Verification**:
  - Generate screenshots in dark and light modes via `scratch/render_widescreen_preview.py`.
  - Confirm zero scrollbars, proper 2x2 KPI alignment, and balanced right-side cards.
