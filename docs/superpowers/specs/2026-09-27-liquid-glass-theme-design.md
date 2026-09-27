# Design Specification: Liquid Glass & Glassmorphism Theme Integration

**Date**: 2026-09-27  
**Author**: DeepMind Antigravity / Pair Programming Agent  
**Status**: Draft - Ready for User Review  
**Spec Location**: `docs/superpowers/specs/2026-09-27-liquid-glass-theme-design.md`

---

## 1. Overview & Goals

WizDesk desktop companion currently features solid-colored surfaces in Dark Mode and Light Mode. The goal of this specification is to elevate both modes into a luxury, state-of-the-art **Liquid Glass** aesthetic inspired by modern macOS and visionOS materials, while strictly preserving WizDesk's established brand identity and layout architecture.

### Core Objectives
1. **True Windows 11 Acrylic & Mica Integration**: Use the Windows Desktop Window Manager (`dwmapi.dll`) API to achieve hardware-accelerated frosted glass blur of the desktop wallpaper and open windows behind WizDesk.
2. **Layered Liquid Glass Styling**: Style outer containers, sidebar, and inner cards with subtle translucent backdrops, specular hairline rim borders, and soft elevation shadows.
3. **Strict Brand Accent Preservation**: Retain all brand colors without alteration:
   - Terracotta and Orange: `#BA3F1A`, `#C2410C`, `#FF6B3D`, hover `#9E3414` / `#A3360E`.
   - Emerald highlights: `#10B981`.
   - Category chart hues: `#6366F1`, `#3B82F6`, `#F59E0B`, etc.
4. **Strict Layout & Component Preservation**: Zero modifications to widget hierarchies, layouts, margins, padding, border radii, or component types. Only styling tokens (rgba/hex stylesheets) and window backdrop flags are updated.
5. **Zero-Regression Automatic Fallback**: If running on Windows 10, Linux, or systems with Windows Transparency Effects disabled, the system automatically falls back to clean opaque styling with zero crashes and zero visual degradation.

---

## 2. Technical Architecture & Windows DWM Integration

### 2.1 Window Blur Engine (`wiz/utils/window_blur.py`)
A lightweight, standalone utility module interfacing with `dwmapi.dll` via Python's standard `ctypes`:

- **API Signature**: `DwmSetWindowAttribute(HWND, DWORD dwAttribute, LPCVOID pvAttribute, DWORD cbAttribute)`
- **Constants**:
  - `DWMWA_SYSTEMBACKDROP_TYPE = 38` (Windows 11 build 22621+)
  - `DWMSBT_AUTO = 0` (Default compositor selection)
  - `DWMSBT_NONE = 1` (Disabled / flat)
  - `DWMSBT_MICA = 2` (Mica subtle wallpaper tint)
  - `DWMSBT_ACRYLIC = 3` (Acrylic rich frosted glass blur)
  - `DWMSBT_MICA_ALT = 4` (Mica Alt high-contrast)
  - `DWMWA_USE_IMMERSIVE_DARK_MODE = 20` (Dark/light titlebar synchronization)
- **Safe Detection**:
  - Check platform is `win32` and Windows release >= 11 (build >= 22000).
  - Wrap all calls in `try / except OSError`.
  - Fall back silently to solid rendering if unsupported or failed.

### 2.2 Top-Level Window Translucency
To allow Windows DWM Acrylic to blend through the window:
- In `QuickEntryDialog.__init__` and `SettingsDialog.__init__`:
  - Set `self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)`.
  - Enable frameless window flag (`Qt.WindowType.FramelessWindowHint`).
  - Pass the window winId (`int(self.winId())`) to `set_window_acrylic(hwnd, is_dark=self.is_dark)`.

---

## 3. Liquid Glass Color Token Specification

### 3.1 Dark Liquid Glass Tokens

| Component / Layer | Token Name | Glass Value | Border Highlight | Visual Effect |
| :--- | :--- | :--- | :--- | :--- |
| Outer Frame | `outer_bg` | `rgba(18, 18, 22, 0.72)` | `1px solid rgba(255, 255, 255, 0.18)` | Deep obsidian frosted glass with perimeter specular rim |
| Side Navigation Bar | `sidebar_bg` | `rgba(14, 14, 18, 0.65)` | `1px solid rgba(255, 255, 255, 0.10)` | Translucent navigational panel |
| Inner Canvas Card | `inner_bg` | `rgba(24, 24, 29, 0.55)` | `1px solid rgba(255, 255, 255, 0.12)` | Recessed secondary frosted glass surface |
| Content Cards | `card_bg` | `rgba(32, 32, 38, 0.68)` | `1px solid rgba(255, 255, 255, 0.15)` | Elevated floating cards for KPIs, charts, and agendas |
| Input Fields | `input_bg` | `rgba(255, 255, 255, 0.06)`| `1px solid rgba(255, 255, 255, 0.15)` | Frosted glass text inputs and dropdowns |
| Active Navigation Pill| `active_pill_bg` | `rgba(186, 63, 26, 0.88)` | `1px solid rgba(255, 107, 61, 0.40)` | Luminous brand terracotta glow |
| Primary Text | `text_primary` | `#FFFFFF` | N/A | Crisp, high-contrast typography |
| Secondary Text | `text_secondary`| `rgba(255, 255, 255, 0.65)`| N/A | Subdued metadata and hints |

### 3.2 Light Crystal Glass Tokens

| Component / Layer | Token Name | Glass Value | Border Highlight | Visual Effect |
| :--- | :--- | :--- | :--- | :--- |
| Outer Frame | `outer_bg` | `rgba(248, 248, 250, 0.78)` | `1px solid rgba(255, 255, 255, 0.65)` | Frosted crystal window with radiant edge |
| Side Navigation Bar | `sidebar_bg` | `rgba(242, 242, 245, 0.70)` | `1px solid rgba(0, 0, 0, 0.08)` | Clean frosted navigation panel |
| Inner Canvas Card | `inner_bg` | `rgba(238, 238, 242, 0.60)` | `1px solid rgba(255, 255, 255, 0.50)` | Soft translucent canvas backdrop |
| Content Cards | `card_bg` | `rgba(255, 255, 255, 0.85)` | `1px solid rgba(255, 255, 255, 0.95)` | Pure elevated white frosted glass cards |
| Input Fields | `input_bg` | `rgba(255, 255, 255, 0.90)` | `1px solid #E4E4E7` | Crisp readable inputs |
| Active Navigation Pill| `active_pill_bg` | `rgba(186, 63, 26, 0.92)` | `none` | Clean solid brand terracotta pill |
| Primary Text | `text_primary` | `#18181B` | N/A | Crisp graphite typography |
| Secondary Text | `text_secondary`| `#71717A` | N/A | Cool neutral metadata |

---

## 4. Brand Preservation & Legibility Guarantees

1. **Brand Identity**:
   - Primary action buttons ("Add", "Schedule", "Save") retain `#BA3F1A` / `#C2410C` with `#9E3414` / `#A3360E` hover states.
   - Donut charts, progress meters, and session bars use 100% opaque, vivid palette colors so graphs pop through the translucent surfaces.
   - The official mascot mark ([assets/wizdesk-logo.svg](file:///h:/Projects/Wiz/assets/wizdesk-logo.svg)) maintains its high-contrast white dome and crisp `#18181B` outline.
2. **Text Legibility**:
   - No blur filters are ever applied over text, icons, or task content.
   - Background opacities (0.55 to 0.88) ensure that background desktop wallpaper patterns never interfere with reading tasks, notes, or metrics.

---

## 5. Scope of Implementation Files

- **`wiz/utils/window_blur.py`**: New helper implementing safe DWM backdrop calls (`set_window_acrylic`, `set_window_mica`).
- **`wiz/ui/popup_dialog.py`**:
  - Integrate window blur helper on `QuickEntryDialog`.
  - Update `apply_theme` with Dark Liquid Glass and Light Crystal Glass token sets.
- **`wiz/ui/sidebar_widget.py`**:
  - Update `apply_theme` with translucent sidebar background and specular divider styling.
- **`wiz/ui/settings_dialog.py` & `wiz/ui/settings_view.py`**:
  - Update `apply_theme` to match the liquid glass tokens.
- **`tests/test_window_blur.py`**:
  - Unit tests verifying fallback behavior, platform detection, and mock DWM calls.

---

## 6. Verification & Exit Criteria

1. **Automated Test Suite**: 100% of existing tests (116/116) pass without regressions.
2. **New Tests**: `test_window_blur.py` verifies Windows 11 API invocation and safe fallback on non-Windows/unsupported environments.
3. **Visual Validation**: Offscreen rendered screenshots verify that Dark Liquid Glass and Light Crystal Glass render cleanly with high contrast, sharp text, and elegant specular highlights.
4. **Clean Commit Routine**: Git working tree committed before handoff with zero double dashes and zero em-dashes.
