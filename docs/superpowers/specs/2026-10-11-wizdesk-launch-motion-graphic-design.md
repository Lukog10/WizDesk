# Design Specification: WizDesk Launch Motion Graphic Video (v1.2.0)
Date: 2026-10-11 | Author: Wiz Core Team | Status: Approved Design

## 1. Executive Summary & Objective

This specification details the end-to-end design, storyboard choreography, typography, audio soundscape, and technical rendering pipeline for the official WizDesk v1.2.0 launch motion graphic video.

The video adapts the fluid character charm and pacing of the reference animation into a high-fidelity 16:9 Landscape (1920x1080) product launch film. It begins with an authentic developer story: coding for 3-4 hours straight and losing track of finished versus unfinished work: before introducing Wiz, demonstrating autonomous passive tracking, unfolding the desktop workspace, highlighting local-first privacy, and concluding with a celebration and call to action.

Crucially, in accordance with user requirements, the video portrays seamless, natural desktop interactions without showing or mentioning keyboard hotkeys.

---

## 2. Technical Parameters & Deliverables

- **Aspect Ratio**: 16:9 Landscape
- **Resolution**: 1920x1080 pixels
- **Target Frame Rate**: 30 fps
- **Total Duration**: 28.5 seconds
- **Format Deliverable**: H.264 MP4 (`brag.mp4`) + Frame 0 Poster Image (`brag.jpg`)
- **Render Engine**: Hyperframes HTML5/CSS3/JavaScript composition rendered via headless Chrome pipeline.
- **Composition Root**: `brag-output/composition/`

---

## 3. Visual System & Typography Design

### 3.1 Color Palette
- **Background**: Deep matte obsidian `#090C10` transitioning subtly into `#0D1117`.
- **Ambient Lighting**: Soft radial glows (`#3B82F6` and `#8B5CF6`) positioned at canvas focal points at 8% to 12% opacity.
- **Card Surfaces**: Frosted dark glassmorphism containers:
  - Background: `rgba(17, 24, 39, 0.85)`
  - Border: `1px solid rgba(255, 255, 255, 0.08)`
  - Box Shadow: `0 20px 40px rgba(0, 0, 0, 0.5)`
  - Backdrop Filter: `blur(16px)`
- **Accent Tokens**:
  - Focus Electric Blue: `#3B82F6`
  - Success Emerald Green: `#10B981`
  - Active Stopwatch Amber: `#F59E0B`
  - Obsidian Purple: `#8B5CF6`

### 3.2 Typography Rules
- **Display Headlines**: Space Grotesk, bold (700 weight), tracking `-0.02em`, crisp white `#FFFFFF`.
- **Subtitles & Descriptions**: Plus Jakarta Sans, medium (500 weight), muted slate `#94A3B8`.
- **Card Labels & Metadata**: Plus Jakarta Sans, semi-bold (600 weight), `#E2E8F0`.

---

## 4. Scene-by-Scene Storyboard Specification

### Scene 1: The Real Developer Story (0.0s - 4.5s)
- **Duration**: 4.5 seconds
- **Visual Action**:
  - Starts on a dark developer workspace. An active code editor and terminal window glow on screen.
  - A subtle focus session badge indicates: `3h 42m continuous flow`.
  - Typing halts. Two clean question cards land in the center with smooth spring animations:
    - **Card 1**: `What did I actually finish?`
    - **Card 2**: `What is still left unfinished?`
  - The screen softens into focus as the question cards settle.
- **On-Screen Typography**:
  - Primary Headline: "You code for 3-4 hours straight."
  - Subtitle: "Where did the hours go? What got finished? What got left behind?"
- **Audio / SFX**:
  - Rapid keyboard typing stops into ambient room tone.
  - Two crisp interface clicks as Card 1 and Card 2 land.
  - Soft musical swell building curiosity.

### Scene 2: Meet Wiz (4.5s - 9.0s)
- **Duration**: 4.5 seconds
- **Visual Action**:
  - Question cards dissolve smoothly.
  - A gentle radial spotlight illuminates the center of the frame.
  - Wiz the mascot ([assets/wiz-idle.svg](file:///H:/Projects/Wiz/assets/wiz-idle.svg)) pops into view with a playful elastic bounce.
  - An animated white mouse cursor glides into view. Wiz's pupils smoothly track the cursor across the screen.
  - The cursor gently boops Wiz. Wiz tilts slightly, blinks, and smiles.
- **On-Screen Typography**:
  - Primary Headline: "Meet Wiz."
  - Subtitle: "Your autonomous desktop companion."
- **Audio / SFX**:
  - Playful entrance pop, smooth harmonic chord, friendly procedural chirp sound on boop.

### Scene 3: Autonomous Tracking & The Floating Island (9.0s - 14.5s)
- **Duration**: 5.5 seconds
- **Visual Action**:
  - Wiz floats smoothly toward the top-right corner, resting as an always-on-top companion.
  - Coding, browser, and terminal windows switch in the background.
  - Wiz quietly pulses every 5 seconds, logging focused activity automatically.
  - A minimal floating Quick Bar Island docks smoothly at the top edge of the desktop, showing: `WizDesk • Active: VS Code (2h 15m)`.
  - A brief indicator confirms: `Sensitive titles auto-sanitized`.
  - Crucially: No hotkeys are displayed or mentioned; the island is part of the natural desktop environment.
- **On-Screen Typography**:
  - Primary Headline: "Quietly tracking your active windows."
  - Subtitle: "No start/stop timers. Zero manual logging."
- **Audio / SFX**:
  - Subtle window slide whoosh, soft keyboard sound, gentle 5-second pulse blip.

### Scene 4: Full Workspace Expansion (14.5s - 20.0s)
- **Duration**: 5.5 seconds
- **Visual Action**:
  - The cursor clicks on the floating island.
  - The island smoothly unfolds and morphs into the full 920x680 QuickEntry workspace:
    - **Tasks Panel**: A task row with subtasks expands. The play button is clicked, starting a live stopwatch timer (`00:42:15` ticking smoothly). Custom tags (`Work`, `Release`) light up in color.
    - **Projects Analytics**: An interactive SVG Donut Chart animates into place, showcasing project time breakdown.
- **On-Screen Typography**:
  - Primary Headline: "Instant access to your full workspace."
  - Subtitle: "Tasks, live stopwatch timers, and project analytics."
- **Audio / SFX**:
  - Smooth glass card expansion whoosh, clean button click, soft stopwatch tick.

### Scene 5: Local-First Privacy & Obsidian Vault Sync (20.0s - 24.5s)
- **Duration**: 4.5 seconds
- **Visual Action**:
  - The workspace glides left into a balanced split-view:
    - **Left Card**: A dark cryptographic shield: `AES-256-GCM Encrypted at Rest • Protected by Windows Hello`.
    - **Right Card**: A clean Markdown document with the purple Obsidian icon: `2026-10-11.md`, populated with daily work logs, completed tasks, and structured checkboxes.
- **On-Screen Typography**:
  - Primary Headline: "100% Local-First & Zero Telemetry."
  - Subtitle: "AES-256 protected. Auto-synced to your Obsidian vault."
- **Audio / SFX**:
  - Solid lock click sound, paper slide whoosh.

### Scene 6: Celebration & Outro (24.5s - 28.5s)
- **Duration**: 4.0 seconds
- **Visual Action**:
  - A task checkbox gets ticked with a vibrant green checkmark.
  - Wiz transforms into his celebration pose ([assets/wiz-complete.svg](file:///H:/Projects/Wiz/assets/wiz-complete.svg)), bursting colorful confetti particles.
  - The official WizDesk logo ([assets/WizDesk Logo v1.jpeg](file:///H:/Projects/Wiz/assets/WizDesk%20Logo%20v1.jpeg)) and tagline settle in the center.
  - Badges settle below: `Standalone Windows x64 • Free & Open Source on GitHub`.
- **On-Screen Typography**:
  - Primary Headline: "WizDesk"
  - Subtitle: "Focus in flow. Wiz remembers the rest."
  - Call to Action: `github.com/Lukog10/WizDesk`
- **Audio / SFX**:
  - Satisfying task check sound, celebratory chime, confetti pop, warm resolving synth bed.

---

## 5. Composition Architecture & Technical Requirements

1. **Self-Contained Web Stack**: The composition will be authored using HTML5 semantic containers, Vanilla CSS3 animations, and deterministic requestAnimationFrame/timeline playback.
2. **Deterministic Frame Stepping**: All animations use absolute timestamps (`data-start` and `data-duration` attributes) so that headless Chrome renders every frame identically regardless of CPU speed.
3. **No External Network Dependencies**: All font files, SVG icons, and audio assets are referenced locally from `brag-output/composition/assets/`.
4. **Contrast & Accessibility Validation**: All foreground text elements must pass WCAG AA contrast thresholds (minimum 4.5:1 ratio against card backgrounds).
5. **Frame 0 Poster Extraction**: Upon rendering the MP4, the settled final logo frame will be captured to `brag.jpg` and baked into frame 0 of `brag.mp4`.

---

## 6. Verification Plan & Exit Criteria

- [x] Spec approved by user.
- [x] HTML/CSS composition authored in `brag-output/composition/`.
- [x] `npx hyperframes check` passes with 0 errors and 0 contrast warnings.
- [x] Video rendered cleanly to `brag-output/brag.mp4` at 1920x1080 30fps.
- [x] Video verified visually across all 6 scenes.
- [x] Share copy saved to `brag-output/share-copy.txt`.
