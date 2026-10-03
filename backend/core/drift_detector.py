from collections import deque
import logging

logger = logging.getLogger(__name__)


class DriftDetector:
    def __init__(self, window: int = 20, threshold_drop: float = 0.15):
        self.window          = window
        self.threshold_drop  = threshold_drop
        self.history         = deque(maxlen=200)
        self.baseline        = None

    def record(self, confidence: float):
        self.history.append(confidence)
        if self.baseline is None and len(self.history) >= self.window:
            self.baseline = (
                sum(list(self.history)[:self.window]) / self.window
            )
            logger.info(f"Drift baseline set: {self.baseline:.3f}")

    def check(self) -> dict:
        if len(self.history) < self.window:
            return {"alert": False, "status": "insufficient_data"}
        if self.baseline is None:
            return {"alert": False, "status": "no_baseline"}

        recent = list(self.history)[-self.window:]
        avg    = sum(recent) / len(recent)
        drop   = (self.baseline - avg) / (self.baseline + 1e-9)
        alert  = drop > self.threshold_drop

        return {
            "alert":          alert,
            "status":         "alert" if alert else "healthy",
            "current_avg":    round(avg,            3),
            "baseline":       round(self.baseline,  3),
            "drop_pct":       round(drop * 100,     1),
            "recommendation": "Record new videos and retrain" if alert else None,
        }

    def reset_baseline(self):
        if self.history:
            recent = list(self.history)[-self.window:]
            self.baseline = sum(recent) / len(recent)
            logger.info(f"Drift baseline reset: {self.baseline:.3f}")
