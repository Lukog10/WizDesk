"""Application configuration and persistent settings manager for WizDesk."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Manages application paths, persistent settings, and configuration defaults."""

    def __init__(self, config_file: Optional[Path] = None):
        # Base paths
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.assets_dir = self.root_dir / "assets"
        
        # User app data directory for persistent settings & storage
        appdata = os.environ.get("APPDATA")
        if appdata:
            self.user_data_dir = Path(appdata) / "WizDesk"
        else:
            self.user_data_dir = Path.home() / ".wizdesk"
            
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = config_file or (self.user_data_dir / "config.json")
        self.db_path = self.user_data_dir / "wizdesk.db"

        # Default settings dictionary
        self._defaults: Dict[str, Any] = {
            "window_width": 140,
            "window_height": 168,
            "window_x": None,
            "window_y": None,
            "always_on_top": True,
            "enable_floating_animation": True,
            "tracking_interval_seconds": 1800,  # 30 minutes
            "obsidian_vault_path": "",
            "obsidian_logs_folder": "WizDesk Logs",
            "global_hotkey": "<ctrl>+<shift>+w",
            "auto_start_on_login": False,
            "sound_effects": False,
        }

        self._data: Dict[str, Any] = self._defaults.copy()
        self.load()

    def get_asset_path(self, asset_name: str) -> Path:
        """Resolve the path to an asset file in the assets directory."""
        path = self.assets_dir / asset_name
        if not path.exists():
            # Fallback check relative to cwd
            fallback = Path.cwd() / "assets" / asset_name
            if fallback.exists():
                return fallback
        return path

    def load(self) -> None:
        """Load configuration from persistent JSON file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._data.update(loaded)
            except Exception as e:
                print(f"[Config] Warning: Failed to load config from {self.config_file}: {e}")

    def save(self) -> None:
        """Persist current configuration to JSON file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"[Config] Error: Failed to save config to {self.config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value."""
        return self._data.get(key, self._defaults.get(key, default))

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Set a configuration value and optionally persist."""
        self._data[key] = value
        if auto_save:
            self.save()

    @property
    def window_size(self) -> tuple[int, int]:
        """Return the (width, height) for the companion mascot window."""
        return (int(self.get("window_width", 140)), int(self.get("window_height", 168)))

    @property
    def window_position(self) -> Optional[tuple[int, int]]:
        """Return the saved (x, y) coordinates if available."""
        x = self.get("window_x")
        y = self.get("window_y")
        if x is not None and y is not None:
            return (int(x), int(y))
        return None

    def save_window_position(self, x: int, y: int) -> None:
        """Save the mascot window screen position."""
        self._data["window_x"] = int(x)
        self._data["window_y"] = int(y)
        self.save()

    @property
    def obsidian_vault_path(self) -> Optional[Path]:
        """Return Path to Obsidian vault if configured."""
        val = self.get("obsidian_vault_path", "").strip()
        return Path(val) if val else None


# Global singleton instance
config = Config()
