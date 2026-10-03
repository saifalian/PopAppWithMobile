"""
Persistent settings manager.
Saves to settings.json in app directory.
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
SETTINGS_FILE = Path(__file__).parent.parent.parent / "settings.json"


DEFAULTS = {
    # Compute
    "compute_device_id":   "cpu",
    "compute_device_name": "CPU",
    "compute_device_type": "cpu",
    "batch_size":          32,
    "mixed_precision":     True,

    # App paths
    "coinglass_path":      r"C:\Program Files\Coinglass\Coinglass.exe",
    "tesseract_path":      r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    "video_recordings_dir": "",

    # Training
    "auto_save_every":     10,
    "max_attempts":        200,
    "default_confidence":  0.65,
    "attempt_timeout":     60,
    "popup_wait":          0.7,

    # Backup
    "backup_enabled":     True,
    "backup_path":        r"D:\Backups\ModelFactory",
    "backup_keep_days":   7,

    # Scheduler
    "scheduler_enabled":  False,
    "scheduler_start":    "02:00",
    "scheduler_stop":     "06:00",
    "scheduler_attempts": 50,

    # Drift
    "drift_detection":    True,
    "drift_threshold":    0.15,
    "drift_check_every":  20,

    # Ollama
    "ollama_enabled":     False,
    "ollama_model":       "qwen3.5:0.8b",
}


class SettingsManager:
    def __init__(self):
        self._data = DEFAULTS.copy()
        self.load()

    def load(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE) as f:
                    saved = json.load(f)
                self._data.update(saved)
            except Exception as e:
                logger.error(f"Settings load error: {e}")

    def save(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.error(f"Settings save error: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def set_device(self, device):
        """Save selected compute device."""
        self._data["compute_device_id"]   = device.id
        self._data["compute_device_name"] = device.name
        self._data["compute_device_type"] = device.device_type
        self.save()

    def get_all(self) -> dict:
        return self._data.copy()


# Global singleton
settings = SettingsManager()
