# Hyperframes Composition Brief: WizDesk

## Objective
Create a short, polished launch motion graphic video for WizDesk v1.2.0 adapting the visual charm of the reference companion animation into a 16:9 Landscape product film.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape (16:9) — 1920x1080
- Duration: 28.5 seconds (855 frames at 30 fps)

## Source Material
- Project root: `H:/Projects/Wiz`
- Primary files read: `README.md`, `wiz/ui/mascot_widget.py`, `wiz/ui/popup_dialog.py`, `wiz/storage/models.py`, `docs/WIZDESK_PRODUCT_AND_MARKETING_GUIDE.md`
- Product name: WizDesk
- Tagline: "Focus in flow. Wiz remembers the rest."
- Key UI and visual moments to recreate:
  - Developer flow state with 2 question cards: "What did I actually finish?", "What is still left unfinished?"
  - Vector mascot Wiz with pupil eye-tracking physics and gentle boop reaction
  - Minimalist floating Quick Bar Island docked at screen top
  - Full 920x680 QuickEntry workspace unfolding with live stopwatch timers, tag badges, and SVG Donut chart
  - Local AES-256 encryption card and Obsidian Markdown note card
  - Task completion celebration with confetti particles and official logo
- Verbatim copy:
  - "You code for 3-4 hours straight."
  - "Where did the hours go? What got finished? What got left behind?"
  - "Meet Wiz. Your autonomous desktop companion."
  - "Quietly tracking your active windows."
  - "No start/stop timers. Zero manual logging."
  - "Instant access to your full workspace."
  - "Tasks, live stopwatch timers, and project analytics."
  - "100% Local-First & Zero Telemetry."
  - "AES-256 protected. Auto-synced to your Obsidian vault."
  - "WizDesk. Focus in flow. Wiz remembers the rest."
  - `github.com/Lukog10/WizDesk`

## Creative Direction
- Tone preset: polished
- Creative direction: clean companion-led tech launch with authentic developer story
- Interpretation: Smooth pacing, high typographic elegance, responsive mascot animations, and zero hotkey references.
- Angle: Developer codes for hours in deep flow, loses track of what finished vs what is left open. Wiz sits on the desk to quietly remember everything, manage live stopwatches, and sync to Obsidian with local-first privacy.
- Hook: Scene 1 developer flow state and the two question cards.
- Outro: Task completed, confetti celebration, WizDesk logo and GitHub call to action.
- Avoid:
  - Generic SaaS buzzwords
  - Abstract filler graphics
  - Any mention or display of keyboard hotkeys (access is shown via direct desktop presence and clicks)

## Visual Identity
- Background: `#090C10`
- Surface: `rgba(17, 24, 39, 0.85)`
- Border: `rgba(255, 255, 255, 0.08)`
- Accent Blue: `#3B82F6`
- Accent Green: `#10B981`
- Accent Amber: `#F59E0B`
- Accent Purple: `#8B5CF6`
- Display Font: Space Grotesk
- Body Font: Plus Jakarta Sans
- Visual references: `assets/wiz-idle.svg`, `assets/wiz-complete.svg`, `assets/WizDesk Logo v1.jpeg`

## Storyboard
Contract defined in `brag-output/brag-plan.md`:
1. Scene 1 — The Real Developer Story — 4.5s (0.0s - 4.5s)
2. Scene 2 — Meet Wiz — 4.5s (4.5s - 9.0s)
3. Scene 3 — Autonomous Tracking & Floating Island — 5.5s (9.0s - 14.5s)
4. Scene 4 — Full Workspace Expansion — 5.5s (14.5s - 20.0s)
5. Scene 5 — Local-First Privacy & Obsidian Sync — 4.5s (20.0s - 24.5s)
6. Scene 6 — Celebration & Outro — 4.0s (24.5s - 28.5s)

## Audio
- Audio role: warm electronic bed with tactile UI accents
- Music: `happy-beats-business-moves-vol-10-by-ende-dot-app.mp3`
- Music treatment: volume 0.70, starts at 0.0s, gentle fade-out under final logo from 27.0s to 28.5s.
- SFX files:
  - Keyboard typing: `assets/sfx/keyboard/`
  - Tactile UI clicks: `assets/sfx/ui/`
  - Boop & chirp: `assets/sfx/interface/`
  - Glass slide whoosh: `assets/sfx/interface/`
  - Celebration fanfare / chime: `assets/sfx/casino/`

## Hyperframes Instructions
- Composition must use deterministic frame stepping via CSS animations and JavaScript timelines (`data-start`, `data-duration`).
- Pass WCAG AA contrast rules (minimum 4.5:1 ratio for text).
- Run `npx hyperframes check` to ensure zero errors before rendering.
- Render to `brag-output/brag.mp4`.
- Extract frame 0 poster to `brag-output/brag.jpg`.
