"""
Converts attempt result into a 0-100 score.
Three modes: auto, manual, goal_only.
Full curriculum support and behavior analysis.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScoreCalculator:
    def __init__(self, config: dict):
        self.config = config
        self.mode   = config.get("mode", "auto")
        self.timing_mode = config.get("reward_timing", "sparse") # dense, sparse, mixed
        self.conf_threshold = config.get("confidence_threshold", 0.65)
        self.action_history = []  # Last 10 actions for loop detection

    def calculate(self, result: dict, attempt_n: int = 1) -> float:
        if not result:
            return 0.0

        # Record action in history
        action = result.get("action_name") or result.get("action", "unknown")
        self.action_history.append(action)
        if len(self.action_history) > 10:
            self.action_history.pop(0)

        # Determine which layers are active (curriculum)
        active_layers = self._active_layers(attempt_n)

        if self.mode == "auto":
            return self._auto_score(result)
        elif self.mode == "manual":
            return self._manual_score(result, active_layers)
        elif self.mode == "goal_only":
            return self._goal_score(result)
        return self._auto_score(result)

    def should_score_now(self, step_type: str, is_end: bool) -> bool:
        if self.timing_mode == "dense":
            return True
        if self.timing_mode == "sparse":
            return is_end
        if self.timing_mode == "mixed":
            return is_end or step_type in ("click", "success")
        return is_end

    # ── AUTO SCORE ───────────────────────────────────────────────

    def _auto_score(self, result: dict) -> float:
        score = 0.0
        if result.get("success"):               score += 40.0
        if result.get("output") is not None:    score += 30.0
        if result.get("duration", 999) < 60:    score += 20.0
        conf = result.get("confirm_score", 0)
        if conf > 0.5:                           score += conf * 10.0
        return float(min(100.0, max(0.0, score)))

    # ── MANUAL SCORE (10/10 ENGINE) ───────────────────────────────

    def _manual_score(self, result: dict, active_layers: list) -> float:
        score = 0.0
        cfg   = self.config

        # 1. Layer 1: Goal image match (The "Main Objective")
        if 1 in active_layers and cfg.get("layer1", {}).get("enabled", True):
            weight    = cfg["layer1"].get("weight", 0.30)
            goal_sim  = result.get("confirm_score", 0)
            score    += goal_sim * 100 * weight

        # 2. Layer 2: Penalty and Reward Rules (Sentence Builder)
        if 2 in active_layers and cfg.get("layer2", {}).get("enabled", True):
            # Evaluate each rule from the new builder
            for rule in cfg["layer2"].get("rules", []):
                if self._eval_rule(rule, result):
                    # Multiplier based on priority (1x, 2x, 5x)
                    priority = rule.get("priority", "MEDIUM")
                    mult = {"LOW": 1, "MEDIUM": 2, "HIGH": 5}.get(priority, 2)
                    
                    points = float(rule.get("points", 0))
                    if rule.get("type") == "penalty":
                        score -= points * mult
                    else:
                        score += points * mult

        # 3. Layer 3: Behavior Analysis (Automatic)
        if 3 in active_layers and cfg.get("layer3", {}).get("enabled", True):
            weight = cfg["layer3"].get("weight", 0.20)
            score += self._behavior_score(result, cfg["layer3"]) * weight

        # 4. Global Safety Guards (The "Discipline")
        guards = cfg.get("global_constraints", {})
        
        # Step Penalty: forces the AI to be fast
        step_pen = guards.get("step_penalty", 0.1)
        score -= step_pen

        # Loop Detection: penalize repeated actions
        if guards.get("loop_detection", True):
            if len(self.action_history) >= 3:
                last_3 = self.action_history[-3:]
                if all(a == last_3[0] for a in last_3):
                    score -= 5.0 # Automatic loop penalty

        # Legacy Compatibility / State Rewards
        score += self._state_score(result, cfg.get("state_rewards", {}))

        return float(min(100.0, max(0.0, score)))

    def _eval_rule(self, rule: dict, result: dict) -> bool:
        """Evaluates a multi-condition sentence rule."""
        # 1. Check State (Goal Image)
        if_state = rule.get("if_state")
        if if_state:
            # Check if this specific goal image was matched
            # (Requires vision result to pass best matches)
            matched_goals = result.get("matched_goals", [])
            if if_state not in matched_goals:
                # Also fallback to full screen goal match if it's the only one
                if result.get("confirm_score", 0) < 0.75:
                    return False

        # 2. Check Action
        if_action = rule.get("if_action")
        if if_action:
            action = result.get("action_name") or result.get("action", "")
            if action != if_action:
                return False

        return True

    # ── GOAL ONLY ────────────────────────────────────────────────

    def _goal_score(self, result: dict) -> float:
        return float(
            min(100.0, result.get("confirm_score", 0) * 100)
        )

    # ── BEHAVIOR ANALYSIS ────────────────────────────────────────

    def _behavior_score(self, result: dict, cfg: dict) -> float:
        score = 0.0
        if cfg.get("click_spread") and result.get("click_spread", 0) > 0.5:
            score += 15.0
        if cfg.get("sequence_quality") and result.get("good_ordering"):
            score += 20.0
        if cfg.get("retry_detection") and not result.get("retried"):
            score += 10.0
        if cfg.get("time_distribution"):
            dur = result.get("duration", 999)
            if dur < 30:
                score += 15.0
            elif dur < 60:
                score += 8.0
        return min(60.0, score)

    # ── STATE REWARDS ───────────────────────────────────────────

    def _state_score(self, result: dict, sr: dict) -> float:
        if not sr: return 0.0
        s = 0.0
        if result.get("master_reset_ok") and result.get("verify_ok"):
            s += sr.get("ready_bonus", 0.0)
        et = result.get("error_type")
        if et:
            if et in ("reset_error", "app_error"):
                s += sr.get("fatal_penalty", 0.0)
            elif et in ("vision_error", "click_error", "ocr_error"):
                s += sr.get("error_penalty", 0.0)
        if result.get("is_discovery") or result.get("new_state_found"):
            s += sr.get("discovery_bonus", 0.0)
        return float(s)

    # ── CURRICULUM ───────────────────────────────────────────────

    def _active_layers(self, attempt_n: int) -> list:
        curriculum = self.config.get("curriculum", {})
        if not curriculum.get("enabled", True):
            return [1, 2, 3]
        for phase in curriculum.get("phases", []):
            f = phase.get("from_attempt", 1)
            t = phase.get("to_attempt", 9999)
            if f <= attempt_n <= t:
                return phase.get("active_layers", [1, 2, 3])
        return [1, 2, 3]
