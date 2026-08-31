# 👻 Wiz

> **A minimalist desktop companion for work tracking, project logging, and Obsidian sync.**

![Wiz Preview](assets/wiz-final-preview.png)

Wiz is a lightweight Windows desktop companion that lives on your screen. It passively tracks your active windows/applications every 30 minutes, lets you quickly capture notes and hierarchical tasks/subtasks, reacts expressively through mascot animations, and writes structured Markdown work logs directly into your **Obsidian vault**.

---

## ✨ Key Features

- 🛸 **Floating Mascot UI**: Frameless, transparent, draggable, always-on-top companion widget built with PyQt6.
- ⏱️ **Passive Activity Tracking**: Periodically polls active application & window titles every 30 minutes and associates them with project tags.
- 📝 **Quick-Entry Manual Notes & Tasks**: Rapidly log notes, blockers, or structured tasks with subtasks and timestamped progress logs.
- 🎭 **Expressive Mascot States**: Swappable SVG faces for 5 distinct states (`idle`, `working` with rotating spinner eyes, `notify`, `complete` celebration, and `sleep`).
- 📓 **Direct Obsidian Sync**: Automatically formats and writes daily work logs to `/Wiz Logs/YYYY-MM-DD.md` in your Obsidian vault.
- 🗄️ **Local SQLite Buffer**: Fast local storage for offline reliability and smooth performance.

---

## 🛠️ Tech Stack

- **GUI & Animations**: Python 3.14 + [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- **Window & Process Tracking**: `pywin32` + `psutil`
- **Global Hotkeys**: `pynput`
- **Database**: SQLite3 (`wiz.db`)
- **Testing**: `pytest`

---

## 🚀 Getting Started

### Prerequisites
- Windows 10 or 11
- Python 3.10+ (Recommended: Python 3.14)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Lukog10/wiz.git
   cd wiz
   ```

2. **Set up virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 📖 Documentation
- [Product Requirements Document (PRD)](Wiz-PRD.md)
- [Living Project Context & Knowledge Base](context.md)

---

## 📄 License
MIT License. Created by Gokul R.