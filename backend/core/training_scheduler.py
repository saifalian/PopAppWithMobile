"""
Automatic training scheduler.
Triggers training sessions at configured times.
Runs as a background daemon thread.
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TrainingScheduler:
    """
    Monitors the clock and triggers training at scheduled times.
    Uses a background thread — does not block the UI.

    Usage:
        scheduler = TrainingScheduler(settings_manager)
        scheduler.set_trigger_callback(start_training_fn)
        scheduler.start()
        # ... later ...
        scheduler.stop()
    """

    def __init__(self, settings_manager):
        self._settings   = settings_manager
        self._trigger_cb: Optional[Callable] = None
        self._thread:     Optional[threading.Thread] = None
        self._running     = False
        self._last_run:   Optional[datetime] = None

    def set_trigger_callback(self, callback: Callable):
        """
        callback(model_names: list, max_attempts: int)
        Called when a scheduled run should start.
        """
        self._trigger_cb = callback

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop,
            daemon=True,
            name="TrainingScheduler"
        )
        self._thread.start()
        logger.info("Training scheduler started")

    def stop(self):
        self._running = False
        logger.info("Training scheduler stopped")

    def get_next_run_time(self) -> Optional[datetime]:
        """Return next scheduled run datetime or None if disabled."""
        s = self._settings
        if not s.get("scheduler_enabled"):
            return None

        start_str = s.get("scheduler_start", "02:00")
        now       = datetime.now()

        try:
            h, m = _parse_time(start_str)
        except ValueError:
            return None

        next_run = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

        # Check day filter
        days = s.get("scheduler_days",
                     ["Mon","Tue","Wed","Thu","Fri"])
        day_map = {
            "Mon": 0, "Tue": 1, "Wed": 2,
            "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6
        }
        allowed = {day_map[d] for d in days if d in day_map}

        attempts = 0
        while next_run.weekday() not in allowed and attempts < 7:
            next_run += timedelta(days=1)
            attempts += 1

        return next_run

    def get_status(self) -> dict:
        next_run  = self.get_next_run_time()
        s         = self._settings
        return {
            "enabled":   s.get("scheduler_enabled", False),
            "next_run":  next_run.isoformat() if next_run else None,
            "last_run":  self._last_run.isoformat() if self._last_run else None,
            "running":   self._running,
        }

    def _loop(self):
        """Background thread — checks every 30 seconds."""
        while self._running:
            try:
                self._check_and_trigger()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            time.sleep(30)

    def _check_and_trigger(self):
        s = self._settings
        if not s.get("scheduler_enabled"):
            return

        now       = datetime.now()
        start_str = s.get("scheduler_start", "02:00")
        stop_str  = s.get("scheduler_stop",  "06:00")

        try:
            s_h, s_m = _parse_time(start_str)
            e_h, e_m = _parse_time(stop_str)
        except ValueError:
            return

        start_time = now.replace(
            hour=s_h, minute=s_m, second=0, microsecond=0
        )
        stop_time  = now.replace(
            hour=e_h, minute=e_m, second=0, microsecond=0
        )

        # Check if we are in the training window
        in_window = start_time <= now <= stop_time
        if not in_window:
            return

        # Check day filter
        days    = s.get("scheduler_days", ["Mon","Tue","Wed","Thu","Fri"])
        day_map = {"Mon":0,"Tue":1,"Wed":2,"Thu":3,"Fri":4,"Sat":5,"Sun":6}
        allowed = {day_map[d] for d in days if d in day_map}
        if now.weekday() not in allowed:
            return

        # Prevent running twice on same day
        if self._last_run and self._last_run.date() == now.date():
            return

        # Trigger training
        if self._trigger_cb:
            max_attempts = s.get("scheduler_attempts", 50)
            model_names  = s.get("scheduler_models", [])
            logger.info(
                f"Scheduled training triggered at {now.strftime('%H:%M')}"
            )
            self._last_run = now
            try:
                self._trigger_cb(model_names, max_attempts)
            except Exception as e:
                logger.error(f"Scheduler trigger error: {e}")


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse "02:00" or "02:00 AM" into (hour, minute)."""
    time_str = time_str.strip().upper().replace("AM", "").replace("PM", "").strip()
    parts    = time_str.split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
