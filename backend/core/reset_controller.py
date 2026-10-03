"""
3-Layer Reset System.
Layer 1: Master Reset  — run recorded action sequence
Layer 2: Verify        — OpenCV pixel-level checks
Layer 3: Confirm       — screenshot similarity vs goal image
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from backend.desktop.action_executor import execute_action
from backend.vision.screen_capture import capture_full, capture_region
from backend.vision.goal_matcher import compute_similarity

logger = logging.getLogger(__name__)


class ResetController:
    def __init__(self, model_name: str, model_config: dict):
        self.model_name  = model_name
        self.model_dir   = Path("models") / model_name
        self.config      = model_config
        self.reset_config = model_config.get("reset_config", {})
        self._load_assets()

    def _load_assets(self):
        # Load reset sequence steps
        seq_id = self.reset_config.get("master_reset_sequence_id")
        self.reset_steps = []
        if not self.model_dir.exists():
            self.model_dir.mkdir(parents=True, exist_ok=True)
            
        if seq_id:
            seq_file = self.model_dir / "reset_sequence.json"
            if seq_file.exists():
                with open(seq_file) as f:
                    self.reset_steps = json.load(f)

        # Load goal images for Confirm layer
        goals_dir  = self.model_dir / "goals"
        self.goals = []
        if goals_dir.exists():
            for p in sorted(goals_dir.glob("*.png")):
                img = cv2.imread(str(p))
                if img is not None:
                    self.goals.append(img)

        self.confirm_threshold = self.reset_config.get(
            "confirm_threshold", 0.75
        )
        self.on_fail = self.reset_config.get("on_fail", "Retry Reset")
        self.max_retries = self.reset_config.get("max_retries", 3)
        self.safety_timeout = self.reset_config.get(
            "safety_timeout_seconds", 30
        )

    # ── LAYER 1: MASTER RESET ────────────────────────────────────

    def execute_master_reset(self) -> bool:
        if not self.reset_steps:
            logger.warning(
                f"{self.model_name}: No reset sequence defined — skipping"
            )
            return True
        try:
            for step in self.reset_steps:
                execute_action(step)
            time.sleep(1.5)
            return True
        except Exception as e:
            logger.error(f"Master reset error: {e}")
            return False

    # ── LAYER 2: VERIFY ──────────────────────────────────────────

    def verify(self) -> tuple[bool, str]:
        """
        Pixel-level checks via OpenCV.
        Returns (passed: bool, detail_string: str)
        """
        screenshot = capture_full()
        if screenshot is None:
            return False, "screen_capture_failed"

        checks  = self.reset_config.get("verify_checks", {})
        failed  = []
        region  = self._get_active_region()

        # Check 1: No popup visible
        if checks.get("no_popup", True):
            if self._popup_visible(screenshot):
                failed.append("popup_detected")

        # Check 2: Heatmap data present
        if checks.get("heatmap_present", True) and region:
            chart = screenshot[
                region['y1']:region['y2'],
                region['x1']:region['x2']
            ]
            if not self._heatmap_present(chart):
                failed.append("no_heatmap")

        # Check 3: Not over-zoomed
        if checks.get("not_overzoomed", True) and region:
            chart = screenshot[
                region['y1']:region['y2'],
                region['x1']:region['x2']
            ]
            if self._over_zoomed(chart):
                failed.append("over_zoomed")

        # Check 4: Window focused
        if checks.get("window_focused", True):
            if not self._window_focused():
                failed.append("window_not_focused")

        # Custom checks
        for custom in self.reset_config.get("verify_custom_checks", []):
            if not self._run_custom_check(custom, screenshot):
                failed.append(f"custom:{custom.get('name','unknown')}")

        ok = len(failed) == 0
        return ok, ", ".join(failed) if failed else "ok"

    def _get_active_region(self) -> Optional[dict]:
        """Gets the primary region from focus_config or legacy screen_region."""
        fcfg = self.config.get("focus_config", {})
        if fcfg.get("mode") == "whole_screen":
            return None
            
        regions = fcfg.get("regions", [])
        if regions:
            return regions[0]
            
        return self.config.get("screen_region")

    def _popup_visible(self, screenshot: np.ndarray) -> bool:
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
        white_pct = np.sum(thresh > 0) / thresh.size
        return white_pct > 0.08

    def _heatmap_present(self, chart: np.ndarray) -> bool:
        if chart.size == 0:
            return False
        hsv   = cv2.cvtColor(chart, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(
            hsv, np.array([0, 100, 100]), np.array([10, 255, 255])
        )
        mask2 = cv2.inRange(
            hsv, np.array([160, 100, 100]), np.array([180, 255, 255])
        )
        red_pct = (np.sum(mask1) + np.sum(mask2)) / (chart.size / 3)
        return red_pct >= 0.02

    def _over_zoomed(self, chart: np.ndarray) -> bool:
        if chart.size == 0:
            return False
        hsv   = cv2.cvtColor(chart, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(
            hsv, np.array([0, 100, 100]), np.array([10, 255, 255])
        )
        mask2 = cv2.inRange(
            hsv, np.array([160, 100, 100]), np.array([180, 255, 255])
        )
        red_pct = (np.sum(mask1) + np.sum(mask2)) / (chart.size / 3)
        return red_pct > 0.60

    def _window_focused(self) -> bool:
        try:
            import win32gui
            hwnd  = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd).lower()
            return "coinglass" in title
        except Exception:
            return True  # non-fatal if win32gui unavailable

    def _run_custom_check(
        self, check_config: dict, screenshot: np.ndarray
    ) -> bool:
        check_type = check_config.get("type", "pixel_color")
        if check_type == "pixel_color":
            x = check_config.get("x", 0)
            y = check_config.get("y", 0)
            expected_bgr = check_config.get("expected_bgr", [0, 0, 0])
            tolerance    = check_config.get("tolerance", 20)
            try:
                actual = screenshot[y, x].tolist()
                return all(
                    abs(a - e) <= tolerance
                    for a, e in zip(actual, expected_bgr)
                )
            except Exception:
                return True
        return True

    # ── AUTO RECOVERY ────────────────────────────────────────────

    def auto_recover(self):
        logger.info("Auto-recovery: pressing Escape and scrolling out")
        for step in [
            {"type": "key",    "key": "Escape"},
            {"type": "key",    "key": "Escape"},
            {"type": "scroll", "amount": -10},
            {"type": "wait",   "seconds": 1.0},
        ]:
            execute_action(step)

    # ── LAYER 3: CONFIRM ─────────────────────────────────────────

    def confirm(self) -> tuple[float, bool]:
        """
        Screenshot similarity check vs goal images.
        Returns (best_similarity: float, passed: bool)
        """
        if not self.reset_config.get("enable_visual_confirmation", True):
            return 1.0, True
            
        if not self.goals:
            return 1.0, True  # no goal images — always pass

        screenshot = capture_full()
        if screenshot is None:
            return 0.0, False

        best = 0.0
        for goal_img in self.goals:
            sim  = compute_similarity(screenshot, goal_img)
            best = max(best, sim)

        passed = best >= self.confirm_threshold
        return best, passed
