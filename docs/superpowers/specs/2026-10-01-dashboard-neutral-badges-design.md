# Workspace Dashboard Neutralization and Project Badges Specification

- **Date**: 2026-10-01
- **Status**: Approved
- **Author**: Antigravity & User

---

## 1. Problem Statement & Objectives

### Problem
The workspace dashboard previously relied on saturated multi-color palettes to distinguish projects, resulting in visual clutter, cognitive fatigue, and high contrast distractions across charts, progress bars, and KPI cards.

### Objectives
1. Replace rainbow color coding with crisp vector Badges and symbols to represent projects.
2. Provide an interactive Badge Selector in both Create and Edit Project dialogs.
3. Apply a graded neutral shading scheme (light grey to dark slate/charcoal) ordered from high to low usage in Project Comparison, App Distribution, and Project Tracking.
4. Provide interactive hover highlighting using the minimal brand accent (`#FF7A45`) on charts and list items.
5. Maintain 100% backward compatibility with existing SQLite databases and project records.

---

## 2. Architecture & Data Model

### Database Migration ([wiz/storage/db.py](file:///h:/Projects/Wiz/wiz/storage/db.py))
- Table `projects` schema update:
  - Add column: `badge TEXT DEFAULT ''`
  - Safe migration inside `_run_schema_and_migrations`:
    ```python
    try:
        conn.execute("ALTER TABLE projects ADD COLUMN badge TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    ```
- Table creation script `SCHEMA_SQL` update:
  - Add `badge TEXT DEFAULT ''` to `CREATE TABLE IF NOT EXISTS projects`.

### Model Layer ([wiz/storage/models.py](file:///h:/Projects/Wiz/wiz/storage/models.py))
- Update `ProjectRecord` dataclass:
  ```python
  @dataclass
  class ProjectRecord:
      id: Optional[int]
      name: str
      keywords: List[str]
      color: str = "#FF6B3D"
      description: str = ""
      badge: str = ""
  ```
- Update queries:
  - `get_all_projects`: fetch `badge` column and construct `ProjectRecord` with `badge=row["badge"] if "badge" in row.keys() else ""`.
  - `create_project`: insert `(name, keywords, color, description, badge)`.
  - `update_project`: update `badge = ?` along with name, keywords, color, and description.

---

## 3. Vector Badge System ([assets/icons/badges/](file:///h:/Projects/Wiz/assets/icons/badges/))

### Library
48 clean 24x24 Lucide vector SVGs downloaded and verified across categories:
- **Internet / Web**: `globe`, `compass`, `wifi`, `link`
- **Tech / Dev**: `code`, `terminal`, `cpu`, `database`, `server`, `laptop`, `smartphone`, `monitor`, `git-branch`, `layers`
- **Office / Work**: `briefcase`, `folder`, `file-text`, `square-check`, `calendar`, `mail`, `message-square`
- **Creative / Design**: `palette`, `pen-tool`, `image`, `video`, `music`, `headphones`
- **Learning / Knowledge**: `book-open`, `graduation-cap`, `search`, `lightbulb`, `sparkles`
- **Metrics / Finance**: `chart-column`, `trending-up`, `dollar-sign`, `credit-card`
- **Lifestyle / Goals**: `gamepad-2`, `coffee`, `zap`, `rocket`, `target`, `flag`, `shield`, `award`, `star`, `heart`, `clock`, `activity`

### Rendering Pipeline ([wiz/ui/icons.py](file:///h:/Projects/Wiz/wiz/ui/icons.py) & [wiz/ui/chart_widgets.py](file:///h:/Projects/Wiz/wiz/ui/chart_widgets.py))
- `render_tinted_svg(painter, f"badges/{badge}.svg", color_hex, x, y, size)`:
  - Renders the vector badge scaled and anti-aliased at any resolution.
  - Automatically tints stroke and fill with the requested neutral or minimal accent color.
- Fallback:
  - When `badge` is empty or the file is missing, the system falls back to a clean typographic monogram capsule (first letter of project name).

---

## 4. UI Components

### 4.1 Project Dialog Badge Picker ([wiz/ui/project_dashboard_view.py](file:///h:/Projects/Wiz/wiz/ui/project_dashboard_view.py))
- Inside `ProjectDialog`:
  - Add a "Project Badge" section above or below the accent color section.
  - Grid of badge buttons with clean hover and selected states:
    - Selected state: 2px solid `#FF7A45` accent outline with `#2A2A2E` background capsule.
    - Default state: subtle outline (`#3F3F46`).
  - First tile: "Auto Monogram" option (badge `""`), followed by all 48 badge options.
  - Returns `badge` string in `get_data()`.

### 4.2 Project Comparison Canvas ([wiz/ui/chart_widgets.py](file:///h:/Projects/Wiz/wiz/ui/chart_widgets.py))
- Sort projects by tracked duration descending.
- Assign graded neutral tints:
  - Dark mode: rank 0 gets `#E4E4E7`, rank 1 gets `#A1A1AA`, rank 2 gets `#71717A`, rank 3 gets `#52525B`, rank 4 gets `#3F3F46`, rank 5+ gets `#27272A`.
  - Light mode: rank 0 gets `#27272A`, rank 1 gets `#3F3F46`, rank 2 gets `#52525B`, rank 3 gets `#71717A`, rank 4 gets `#A1A1AA`, rank 5+ gets `#D4D4D8`.
- Hover state:
  - Hovering over a project bar or stacked slice changes the fill color to `#FF7A45`.
  - Tooltip shows project badge, project name, and duration.

### 4.3 App Usage Donut Canvas ([wiz/ui/chart_widgets.py](file:///h:/Projects/Wiz/wiz/ui/chart_widgets.py))
- Sort app categories/names by duration descending.
- Assign graded neutral tints to donut segments matching the high-to-low scale.
- Hover state:
  - Hovered donut segment illuminates with `#FF7A45`.
  - Center donut hole KPI updates to show hovered app name, duration, and percentage.

### 4.4 Project Tracking Rows ([wiz/ui/chart_widgets.py](file:///h:/Projects/Wiz/wiz/ui/chart_widgets.py))
- Display the project badge icon in the leading capsule of each row.
- Progress bars rendered with neutral fill tints according to target completion / volume.
- Hovering over the row applies a `#FF7A45` border accent and progress glow.

---

## 5. Verification & Testing
1. Unit tests for database migrations: `ALTER TABLE projects ADD COLUMN badge` works without losing existing rows.
2. CRUD tests for project records with badges: creating, updating, and querying projects with badge identifiers.
3. Canvas rendering tests: verify `render_tinted_svg` and painter logic without crashes or memory leaks across themes.
4. Run full pytest suite across all tests (148+ tests).
