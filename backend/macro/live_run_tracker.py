"""
Tracks the live execution state of the current pipeline,
saving events to DB or memory for the Dashboard to display.
Allows pausing and resuming pipelines.
"""
import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, List
import time

logger = logging.getLogger(__name__)

class LiveRunTracker:
    def __init__(self, history_file: str = "data/macro_history.json"):
        self.current_run_id = None
        self.events: List[Dict[str, Any]] = []
        self.is_paused = False
        self.start_time = None
        self.history_file = Path(history_file)
        self._load_history()

    def _load_history(self):
        """Load past history from disk to display in dashboard."""
        if not self.history_file.exists():
            return
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self.events = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load macro history: {e}")
            self.events = []

    def _save_history(self):
        """Persist history to disk."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            # Keep only the last 500 events to prevent massive file growth
            if len(self.events) > 500:
                self.events = self.events[-500:]
                
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save macro history: {e}")

    def start_run(self, macro_name: str, run_id: str):
        self.current_run_id = run_id
        self.is_paused = False
        self.start_time = time.time()
        self.log_event("action", f"▶ Started macro run: {macro_name}")

    def log_event(self, level: str, message: str, node_id: str = None):
        event = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "node_id": node_id
        }
        self.events.append(event)
        self._save_history() # Save on every event so progressive runs are tracked
        
        if level == "error":
            logger.error(f"[LiveRun] {message}")
        elif level == "warning":
            logger.warning(f"[LiveRun] {message}")
        else:
            logger.info(f"[LiveRun] {message}")

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        return self.events[-limit:]

    def pause(self):
        self.is_paused = True
        self.log_event("warning", "Run paused by user.")

    def resume(self):
        self.is_paused = False
        self.log_event("info", "Run resumed by user.")

    def stop_run(self, success: bool, reason: str = ""):
        duration = time.time() - (self.start_time or time.time())
        status = "Success" if success else "Failed"
        msg = f"⏹ Run {status} after {duration:.1f}s. {reason}"
        self.log_event("success" if success else "error", msg)
        self.current_run_id = None

# Global singleton
tracker = LiveRunTracker()
