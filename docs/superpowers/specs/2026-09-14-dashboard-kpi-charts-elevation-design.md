# Projects Dashboard & Chart Elevation Design Specification

## 1. Overview & Goals
Upgrade the dedicated Projects Dashboard in WizDesk to look and feel like a completed, executive-grade product (matching the visual finish and interactive depth of the DealDeck design reference) while remaining within native PyQt6:
- Interactive crosshairs and rich floating tooltip cards on the Project Comparison Chart.
- Visual micro-trend sparklines and contextual progress indicators on the 2x2 KPI cards.
- Bar chart hover glowing highlights and smooth cubic bezier spline node halos.
- Refined responsive breathing room, card elevation, and typography.

## 2. Architecture & Components

### 2.1 Project Comparison Chart Interactive Engine (`ProjectComparisonCanvas`)
- **State & Mouse Tracking**:
  - `setMouseTracking(True)` enabled on `ProjectComparisonCanvas`.
  - Track `hover_bucket_idx: Optional[int]` and `hover_pos: Optional[QPointF]`.
  - Handle `mouseMoveEvent(event)`:
    - Map `x` coordinate to the closest bucket index `0 <= idx < num_buckets`.
    - Repaint only when hover index changes or mouse moves across bucket zones.
  - Handle `leaveEvent(event)`:
    - Clear `hover_bucket_idx = None` and trigger `update()`.
- **Visual Overlay Layers in `paintEvent`**:
  1. Base gridlines, y-axis labels, and series geometries (Bars or Area splines).
  2. Crosshair vertical dashed line (`#52525B` / `#D4D4D8`) at the hovered bucket's x-center.
  3. Hover Highlights:
     - **Bar Mode**: Slightly brighten/glow the hovered bucket's bars while non-hovered bars retain normal opacity.
     - **Area Mode**: Circular halo ring (white/translucent outline) on the hovered point for each project series.
  4. Floating Glassmorphic Tooltip Card:
     - Clamped within canvas boundaries (minimum 10px padding from left/right/top edges).
     - Renders bucket title (e.g., `Tuesday` or `14:00 - 16:00`).
     - Renders row per project: color circle, project name, and exact hours (e.g., `VS Code: 3.25h`).
     - Renders total hours sum for that bucket.

### 2.2 Executive KPI Stat Cards (`KpiHeroCard` & `KpiStatCard`)
- **`KpiHeroCard` (`Total Tracked Time`)**:
  - Deep royal indigo-to-violet linear gradient background (`#4F46E5` to `#3730A3` in dark mode; `#6366F1` to `#4338CA` in light mode).
  - Bold metric display (`18.8h`) with period change pill (`+368.8%`).
  - Integrated **Micro Sparkline Canvas**: Draws an antialiased trend curve across period daily bucket values along the bottom of the card with translucent gradient fill.
  - Contextual subtitle: `vs previous period`.
- **`KpiStatCard` (Standard Cards)**:
  - Active Projects: Count (`3`) with `Active` pill and `All active this week` subtitle.
  - Top Application: App name (`VS Code`) with duration pill (`7.5h`) and percentage share subtitle (`40.0% of total time`).
  - Tasks Completed: Ratio (`2 / 4`) with completion percentage pill (`50%`) and an embedded 4px rounded horizontal progress bar.

### 2.3 Visual Polish & Palette Cohesion
- Harmonized card borders (`#2E2E34` dark / `#E5E0D8` light) with rounded corners (12px radius).
- Eliminates harsh boxy outlines and adds subtle internal padding.
- Clean typography hierarchy using Inter / Segoe UI with integer point sizes for PyQt6 stability.

## 3. Data Flow
1. `StorageRepository.get_dashboard_analytics(timeframe)` continues to provide bucket time-series, KPI totals, and app breakdowns.
2. `ProjectsOverviewPage.refresh()` passes the bucket time-series data to:
   - `KpiHeroCard.set_sparkline_data(bucket_totals)`
   - `ProjectComparisonChartWidget.set_data(series, bucket_labels)`
   - `AppUsageAnalyticsWidget.set_data(apps_data, total_hours)`
3. User interactions (hovering mouse, switching Bar/Area, switching Ring/Bar) occur directly in the UI layer with instant repaints and zero database re-queries.

## 4. Verification Plan
- **Automated Unit Tests**:
  - Update `tests/test_projects_dashboard.py` to assert `KpiHeroCard` sparkline data ingestion and rendering.
  - Test `ProjectComparisonCanvas` hover event handlers and coordinate mapping.
  - Run all tests with `pytest -v`.
- **Visual Screenshot Verification**:
  - Generate screenshots using `scratch/render_projects_preview.py`.
  - Verify interactive hover tooltip rendering, crosshair line, sparkline curve, and KPI progress bar across both dark and light modes.
