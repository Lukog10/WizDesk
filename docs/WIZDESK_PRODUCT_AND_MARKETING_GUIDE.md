# WizDesk Master Product, Architecture & Marketing Enablement Guide
Version: 1.2.0 | Status: Production Release | Author: Wiz Core Team

This document serves as the single source of truth for WizDesk: detailing product identity, technical architecture, feature implementations, security contracts, and complete go-to-market enablement for marketing agencies, content creators, and AI automation platforms.

---

## 1. Executive Summary & Product Identity

### 1.1 What is WizDesk?
WizDesk is an autonomous, local-first desktop companion for Windows 10 and Windows 11 that merges passive window activity tracking, an expressive desktop mascot companion, and a keyboard-centric productivity workspace.

Unlike traditional time trackers that demand manual stopwatch toggles or cloud surveillance apps that harvest sensitive telemetry, WizDesk operates 100% locally on the user machine. It tracks focused activity every 5 seconds, sanitizes private window titles automatically, safeguards databases with authenticated AES-256-GCM encryption, and synchronizes daily work logs directly into the user personal Obsidian Markdown vault.

### 1.2 Core Product Tenets
1. **Autonomous Over Manual**: Users should never have to remember to click "Start" and "Stop" on a timer. The operating system active window state tells the true story of work.
2. **Companion Over Surveillance**: Workplace productivity tools should feel supportive and delightful, not punitive. The expressive desktop mascot ("Wiz") provides friendly feedback, eye tracking, and emotional milestones.
3. **Local-First & Zero-Telemetry**: Privacy is an absolute right. WizDesk contains zero network telemetry SDKs, makes zero outbound API calls, and stores all databases encrypted under the user OS credentials.
4. **Open Knowledge Bridge**: Your data belongs to you. Work logs, session recaps, and notes sync directly into standard Markdown files in your Obsidian vault.

### 1.3 Key Brand Vectors
- **Product Name**: WizDesk
- **Release Version**: v1.2.0 (Standalone Windows x64 Executable)
- **Primary Tagline**: Your Autonomous Desktop Companion & Local-First Work Tracker.
- **Secondary Taglines**:
  - Focus in flow. Wiz remembers the rest.
  - Zero telemetry. Real-time mascot. Obsidian connected.
  - The privacy-first work companion that lives on your desk.

---

## 2. Competitive Positioning & Battlecards

| Feature / Philosophy | WizDesk v1.2.0 | Toggl / Clockify | RescueTime | ActivityWatch |
|---|---|---|---|---|
| **Tracking Method** | Autonomous 5s polling + Live stopwatch | Manual timer start/stop | Passive background service | Passive poller |
| **User Presence** | Expressive eye-tracking mascot | None (web/tray only) | None (tray/background) | None (web UI) |
| **Data Storage** | 100% Local SQLite (Encrypted) | Cloud database | Cloud database | Local database |
| **Privacy / Telemetry** | Zero external network calls | Extensive cloud analytics | Continuous cloud reporting | Local server |
| **Encryption at Rest** | AES-256-GCM + Windows DPAPI | Server-side managed | Server-side managed | Unencrypted local DB |
| **Decryption Auth Gate** | Windows CredUI / Windows Hello | Cloud password / OAuth | Cloud password / SSO | None |
| **Obsidian Vault Sync** | Native Markdown bridge | Unofficial plugins / webhooks | Webhooks / Third-party | Third-party scripts |
| **Licensing & Model** | Free & Open Source (GPL v3) | Subscription SaaS ($9-18/mo) | Subscription SaaS ($12/mo) | Open Source (MPL 2.0) |

### 2.1 Battlecard: Why WizDesk Wins
- **Versus Toggl & Clockify**: Eliminates "timer anxiety" and forgotten timers. You do not lose tracking accuracy just because you forgot to press a button when switching tasks.
- **Versus RescueTime**: Eliminates corporate surveillance fears. RescueTime uploads private browsing URLs and document titles to corporate servers. WizDesk redacts sensitive strings on the machine and never sends a single byte across the network.
- **Versus ActivityWatch**: ActivityWatch runs a local web server and opens a browser tab for dashboards. WizDesk is a native, self-contained desktop application with an interactive companion, integrated keyboard shortcuts, and direct Obsidian vault synchronization.

---

## 3. Technology Stack & Technical Foundation

WizDesk is engineered as a high-performance Windows desktop application, fully compiled into a standalone Windows PE 64-bit binary requiring no Python installation.

### 3.1 Language & Application Layer
- **Language**: Python 3.14 (bundled via PyInstaller 6.x)
- **GUI Engine**: PyQt6 (Qt 6.7 / 6.8 bindings)
- **Graphics Pipeline**: Native `QPainter` vector rendering, frameless translucent windows (`Qt.WindowType.FramelessWindowHint`, `Qt.WidgetAttribute.WA_TranslucentBackground`), custom pupil vector trigonometry.
- **Inter-Process Communication**: Local Win32 named mutexes scoped with Session and User SID (`Local\WizDesk_SingleInstance_<UserSID>`) with explicit discretionary access control lists (DACLs).

### 3.2 Operating System Integration (Win32 API)
- **Active Window Inspection**: `win32gui.GetForegroundWindow()`, `win32gui.GetWindowText()`, and `win32process.GetWindowThreadProcessId()`.
- **Idle State Detection**: `win32gui.GetLastInputInfo()` polling to automatically detect when the user steps away from the keyboard and pause activity accumulation.
- **Windows Startup**: Native Windows Registry management under `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`, configuring WizDesk in the Windows Task Manager Startup Apps inventory.
- **OS Credential Gate**: Native Windows CredUI (`CredUIPromptForWindowsCredentialsW`) and Win32 `LogonUserW` for hardware and biometric credential challenge verification.

### 3.3 Storage, Cryptography & Backup
- **Database Engine**: Embedded SQLite3 in Write-Ahead Logging (WAL) mode (`PRAGMA journal_mode=WAL`), enforcing foreign keys and sub-millisecond ACID writes.
- **Key Derivation & Protection**: Windows Data Protection API (DPAPI via `win32crypt.CryptProtectData` and `win32crypt.CryptUnprotectData`), tied to the Windows user logon secret.
- **Symmetric Cipher**: AES-256 in Galois/Counter Mode (AES-256-GCM via `cryptography.hazmat.primitives.ciphers.aead.AESGCM`) with 96-bit randomized nonces and 128-bit authentication tags.
- **Database Sanitation**: Secure cryptographic unlinking and zeroization of temporary SQLite WAL (`.db-wal`) and Shared Memory (`.db-shm`) journal buffers upon lock transitions.
- **Automated Backup Engine**: Point-in-time snapshot archiving generating `.wbak` packages with rolling daily retention and automated pruning.

### 3.4 Procedural Audio Synthesis
- **Procedural Synthesizer**: Pure mathematical waveform generator (`wiz/core/sound.py`) producing 44.1 kHz 16-bit PCM stereo audio using sine waveforms, linear decay envelopes, and harmonic chords.
- **Memory Footprint**: Zero external audio audio files or audio assets required; sounds are generated entirely in RAM and dispatched via `PyQt6.QtMultimedia.QAudioSink`.

---

## 4. Comprehensive Feature Deep Dive

### 4.1 The Desktop Mascot Companion ("Wiz")
- **Visual Identity**: A friendly ghost-shaped vector companion rendered at 100x100 to 140x140 screen pixels.
- **Pupil Math & Eye Tracking**: Dual pupils dynamically track the user desktop mouse cursor anywhere across multi-monitor setups. Eye positions are computed using normalized vector clamping around fixed eye sockets:
  - Vector angle calculated: `atan2(cursor_y - eye_y, cursor_x - eye_x)`
  - Radius clamped to socket boundaries: `min(distance * 0.08, max_socket_radius)`
- **Expressive Companion States**:
  - `IDLE` (`wiz-idle.svg`): Neutral state, pupil tracking, occasional resting blinks.
  - `WORKING` (`wiz-working.svg`): Focus state triggered during continuous window activity.
  - `NOTIFY` (`wiz-notify.svg`): Alert state triggered when attention is requested or milestone reached.
  - `COMPLETE` (`wiz-complete.svg`): Celebration state triggered when tasks are checked off, bursting colorful confetti particles.
  - `SLEEP` (`wiz-sleep.svg`): Inactive state triggered when system idle exceeds configured thresholds.
- **Interactive Gestures**: Drag to move anywhere on screen; click to summon quick menu; double-click to open workspace.

### 4.2 Autonomous Window & Activity Tracker
- **Polling Loop**: Background thread interrogates the foreground window every 5 seconds without UI stutter.
- **Sanitization & Privacy Engine**:
  - Automatically strips binary extensions (e.g., `code.exe` becomes `code`).
  - Redacts browser URLs and sensitive strings matching password managers, banking domains, and private authentication flows.
  - Normalizes common productivity applications (VS Code, Cursor, Chrome, Obsidian, Figma, Windows Terminal).
- **Project Mapping**: Assigns time logs to designated projects based on user-defined keyword matching rules.

### 4.3 The Integrated Workspace Shell (QuickEntry Dialog)
Summoned instantly via global hotkey (`Ctrl+Shift+Space`) or mascot double-click. A custom 920x680 dark glassmorphic canvas featuring:

1. **Tasks & Subtasks Hub**:
   - Hierarchical task tree with collapsible subtasks.
   - **Live Stopwatch Timers**: Real-time timer toggle per task with persistent elapsed seconds tracking across app restarts.
   - **Custom Tags System**: Multi-tag assignment with custom color badges and tag-based filtering.
   - Time tracking labels formatting start and completion timestamps across single-day and multi-day rescheduled tasks.
2. **Projects Analytics Dashboard**:
   - Interactive SVG-driven Donut Charts showing application distribution.
   - Project Comparison bar graphs illustrating time allocation across projects.
   - Stat cards highlighting total focus time, active tasks, and streak counts.
3. **Calendar & Schedule Agenda**:
   - Current-month focus grid eliminating off-month visual clutter.
   - Integrated agenda panel displaying tasks scheduled for the selected day.
   - One-click scheduling and date adjustments.
4. **Activity Timeline**:
   - Granular chronological log of tracked window sessions.
   - Session duration breakdown by application and matched project.
5. **Notes & Pinned Scratchpad**:
   - Fast plain-text scratchpad for in-flight thoughts and blockers.
   - Pinned notes support for persistent references and key task reminders.

### 4.4 Floating Quick Note Island (`Ctrl+Shift+N`)
A minimal, floating pill bar designed for rapid capture without breaking focus.
- Global summon via hotkey.
- Single-line note or task capture with immediate project tag selection.
- Smoothly docks into the screen perimeter.

### 4.5 Obsidian Vault Synchronization
- Bidirectional integration with local Obsidian knowledge bases.
- Writes structured daily work notes into the vault under `YYYY-MM-DD.md`.
- Formats sessions, completed tasks, and notes with standard YAML frontmatter and Markdown checkboxes.
- **Unblocked Plaintext Bridge**: Permanent notes and daily logs sync cleanly as open Markdown even when local database encryption is locked, ensuring the user knowledge base remains always accessible.

---

## 5. Security & Privacy Blueprint

WizDesk underwent a comprehensive red-team security audit and code hardening phase in v1.2.0.

### 5.1 Zero-Telemetry Guarantee
- WizDesk has no network socket listeners and opens no outbound HTTP/HTTPS connections during operation.
- No third-party crash analytics SDKs (no Sentry, Google Analytics, Segment, or PostHog).
- All data remains on the physical storage of the host operating system.

### 5.2 Encryption at Rest
- Local database file `wizdesk.db` can be encrypted using AES-256-GCM.
- Encryption keys are derived via PBKDF2/HMAC-SHA256 and protected via Windows DPAPI, binding encryption keys to the user Windows user profile.

### 5.3 Credential Authentication Gate (CredUI)
- Decrypting the database requires validating the active Windows user credentials.
- Invokes native Windows CredUI (`CredUIPromptForWindowsCredentialsW`) supporting Windows Hello (PIN, facial recognition, fingerprint) and Windows domain passwords.
- Verifies identity via Win32 `LogonUserW` without storing user passwords in plaintext memory.

### 5.4 Multi-User Isolation & Anti-Hijacking
- Prevents cross-user local privilege escalation on shared Windows machines.
- IPC named mutexes are prefixed with the active Windows user Security Identifier (SID): `Local\WizDesk_SingleInstance_<UserSID>`.
- Configured with restricted Discretionary Access Control Lists (DACLs) and Medium Mandatory Integrity Labels, blocking lower-integrity processes from sending rogue messages.

---

## 6. Target Audience, Personas & ICP

### 6.1 Ideal Customer Profile (ICP)
- **Primary ICP**: Independent Software Engineers, Indie Hackers, Freelance Developers, Technical Writers, and PKM (Personal Knowledge Management) enthusiasts using Windows 10/11.
- **Hardware/OS Profile**: Developers running Windows workstations who value desktop customization, dark themes, and local control.

### 6.2 Key User Personas
1. **The Flow-State Developer (Alex, 29)**
   - *Pain Point*: Jumps between VS Code, terminal, and browser for 8 hours, then has no idea what was accomplished or how long a bug fix took.
   - *Why WizDesk Wins*: Passive tracking records every window change; live stopwatch timers clock specific tasks; Wiz gives friendly visual feedback.
2. **The Obsidian Power User (Elena, 34)**
   - *Pain Point*: Wants daily work logs inside their Obsidian second brain, but hates manually copy-pasting times and session recaps.
   - *Why WizDesk Wins*: Native Markdown vault sync outputs clean daily notes with tags, frontmatter, and checkboxes automatically.
3. **The Privacy-Conscious Freelancer (Marcus, 41)**
   - *Pain Point*: Refuses to install cloud time trackers that record keystrokes or upload sensitive client code titles to unknown SaaS servers.
   - *Why WizDesk Wins*: 100% local-first, zero telemetry, AES-256-GCM database encryption, and OS credential verification.

---

## 7. Brand Voice, Copywriting & Messaging Framework

### 7.1 Tone of Voice
- **Tone Profile**: Intelligent, technically precise, respectful of user focus, lightly playful through the companion mascot.
- **Persona**: An attentive, loyal desk companion. Wiz is sharp and quiet, not noisy or distracting.

### 7.2 Terminology Guide
- **Use These Terms**: Autonomous Tracking, Desktop Companion, Local-First, Zero-Telemetry, AES-256 Encrypted, Obsidian Vault Sync, Live Stopwatch, Focused Work.
- **Do NOT Use These Terms**: Surveillance, Employee Monitoring, Boss Mode, Webhook, Cloud Sync, Artificial Intelligence Agent (Wiz is an interactive companion, not a generative chatbot).

### 7.3 Headline Formulae
- *The Problem Hook*: "Where did your last 6 hours of coding actually go?"
- *The Solution Hook*: "Stop setting manual timers. Let your desk companion track your flow."
- *The Privacy Hook*: "Time tracking without the cloud surveillance."
- *The Companion Hook*: "Meet Wiz: the desk companion that watches your windows, not your personal life."

---

## 8. Brand Assets & Marketing Production References

External marketing agencies, motion designers, and creative AI workflows can draw from the following verified project assets and references:

### 8.1 Visual & Character Assets
- **Vector Mascot Artwork**:
  - Idle Companion: [assets/wiz-idle.svg](file:///H:/Projects/Wiz/assets/wiz-idle.svg)
  - Working State: [assets/wiz-working.svg](file:///H:/Projects/Wiz/assets/wiz-working.svg)
  - Notification State: [assets/wiz-notify.svg](file:///H:/Projects/Wiz/assets/wiz-notify.svg)
  - Task Completion Celebration: [assets/wiz-complete.svg](file:///H:/Projects/Wiz/assets/wiz-complete.svg)
  - Sleep State: [assets/wiz-sleep.svg](file:///H:/Projects/Wiz/assets/wiz-sleep.svg)
- **Logos & App Icons**:
  - Official Brand Logo: [assets/WizDesk Logo v1.jpeg](file:///H:/Projects/Wiz/assets/WizDesk%20Logo%20v1.jpeg)
  - Windows Executable Icon: [assets/wizdesk.ico](file:///H:/Projects/Wiz/assets/wizdesk.ico)
  - UI Icons Library: [assets/icons/](file:///H:/Projects/Wiz/assets/icons/)
- **Bundled Typography**:
  - Display Font: Space Grotesk (`assets/fonts/SpaceGrotesk-*.ttf`)
  - Body & UI Font: Plus Jakarta Sans (`assets/fonts/PlusJakartaSans-*.ttf`)

### 8.2 Interactive Demonstrations & Media References
- **Interactive System Architecture Map**: [docs/wizdesk-interactive-map.html](file:///H:/Projects/Wiz/docs/wizdesk-interactive-map.html)
- **High-Resolution Architecture Screenshot**: [assets/screenshots/archify-system-design.png](file:///H:/Projects/Wiz/assets/screenshots/archify-system-design.png)
- **Interactive Web Banner**: [docs/wizdesk-banner.html](file:///H:/Projects/Wiz/docs/wizdesk-banner.html)
- **Motion Graphic Pacing Reference**: [scratch/instagram_1791512982158720p.mp4](file:///H:/Projects/Wiz/scratch/instagram_1791512982158720p.mp4) (Vertical companion animation reference illustrating character eye tracking, floating island docks, and session replay transitions)

### 8.3 Core Value Pillars for Campaign Messaging
When structuring copy across channels (Product Hunt, Twitter/X, LinkedIn, Reddit, or technical blogs), campaigns should anchor to these six verified pillars:
1. **Zero Manual Timers**: Passive 5-second active window polling eliminates forgotten timers and tracking anxiety.
2. **Expressive Companion**: A desk mascot with real-time pupil tracking that reacts to user focus, celebration, and idle states.
3. **Live Stopwatches & Tags**: Granular task management with live timers, subtask hierarchies, and custom color tags.
4. **Local-First Zero Telemetry**: 100% offline, zero external API calls, zero analytics SDKs.
5. **Hardware-Backed Encryption**: AES-256-GCM encrypted SQLite storage protected by Windows DPAPI and Windows CredUI / Windows Hello.
6. **Native Obsidian Sync**: Direct unblocked Markdown synchronization into personal Obsidian vaults with frontmatter and checkboxes.

---

## 9. Repository & Documentation Cross-References

- System Architecture Specification: [docs/CODEBASE_ARCHITECTURE.md](file:///H:/Projects/Wiz/docs/CODEBASE_ARCHITECTURE.md)
- Interactive Archify System Map: [docs/wizdesk-interactive-map.html](file:///H:/Projects/Wiz/docs/wizdesk-interactive-map.html)
- Product Requirements Document: [Wiz-PRD.md](file:///H:/Projects/Wiz/Wiz-PRD.md)
- Security & Vulnerability Policy: [SECURITY.md](file:///H:/Projects/Wiz/SECURITY.md)
- Main Documentation & Badges: [README.md](file:///H:/Projects/Wiz/README.md)
- Core Mascot Engine: [wiz/ui/mascot_widget.py](file:///H:/Projects/Wiz/wiz/ui/mascot_widget.py)
- Storage & Data Models: [wiz/storage/models.py](file:///H:/Projects/Wiz/wiz/storage/models.py)
- Obsidian Sync Engine: [wiz/sync/obsidian.py](file:///H:/Projects/Wiz/wiz/sync/obsidian.py)
- Standalone Executable Spec: [wizdesk.spec](file:///H:/Projects/Wiz/wizdesk.spec)
