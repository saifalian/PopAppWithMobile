"""
Model Drift & Performance Decay Detector.
Tracks performance degradation over rolling windows.
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)

class DriftDetector:
    def __init__(self, history_size=100, baseline_size=20, threshold=0.15):
        """
        history_size: Total rolling window.
        baseline_size: How many of the initial runs formulate the "healthy" baseline.
        threshold: 15% drop from baseline triggers drift.
        """
        self.history_size = history_size
        self.baseline_size = baseline_size
        self.threshold = threshold
        self.history = []

    def add_score(self, score: float):
        """Record a training/inference outcome score (0.0 to 100.0)."""
        self.history.append(score)
        if len(self.history) > self.history_size:
            self.history.pop(0)

    def check_drift(self) -> dict:
        """
        Determine if the model's recent performance is trending downwards.
        Returns a dict with drift metrics.
        """
        if len(self.history) < self.baseline_size * 2:
            return {"drift_detected": False, "severity": 0.0, "reason": "Insufficient data"}
            
        baseline = np.mean(self.history[:self.baseline_size])
        
        # Check the most recent cluster of actions
        recent_window = max(5, self.baseline_size // 2)
        current = np.mean(self.history[-recent_window:])
        
        drift_ratio = 0.0
        if baseline > 1.0: # avoid division by near-zero
            drift_ratio = (baseline - current) / baseline
            
        is_drifting = drift_ratio > self.threshold
        
        return {
            "drift_detected": bool(is_drifting),
            "severity": float(drift_ratio),
            "baseline": float(baseline),
            "current": float(current)
        }
        
    def reset(self):
        """Clear history."""
        self.history.clear()
