"""
Score Calculator with Layered Rewards.
Generates scalar rewards for unsupervised models.
"""
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class ScoreCalculator:
    def __init__(self, config=None):
        self.config = config or {}
        
        # Weighting for the different score layers
        self.w_visual = float(self.config.get("weight_visual", 0.4))
        self.w_goal = float(self.config.get("weight_goal", 0.6))
        
        # Track penalties
        self.penalize_stagnation = bool(self.config.get("penalize_stagnation", True))

    def calculate_score(self, state_img, action, next_state_img, goal_img=None) -> float:
        """
        Calculate a multi-layered score for an action based on before/after states.
        state_img: Screen before action.
        next_state_img: Screen after action.
        goal_img: Absolute goal state if available.
        """
        if state_img is None or next_state_img is None:
            return -1.0 # Invalid inputs

        # Layer 1: Visual Delta (Reward doing SOMETHING rather than nothing)
        # If the screen drastically changes, the action was likely valid/impactful.
        l1_score = self._visual_delta_reward(state_img, next_state_img)
        
        # Layer 2: Goal reach
        l2_score = 0.0
        if goal_img is not None:
            l2_score = self._goal_reward(next_state_img, goal_img)
            
        # Optional: Penalize if screen did not change at all
        if self.penalize_stagnation and l1_score < 1.0:
            return -5.0 # Penalty for stagnation

        # Combine
        if goal_img is not None:
            final_score = (l1_score * self.w_visual) + (l2_score * self.w_goal)
        else:
            final_score = l1_score
            
        logger.debug(f"Calculated Score: {final_score:.2f} (Delta: {l1_score:.2f}, Goal: {l2_score:.2f})")
        return float(np.clip(final_score, -100.0, 100.0))

    def _visual_delta_reward(self, s, ns) -> float:
        """Measure how much the screen changed. High diff = high reward."""
        try:
            s_gray = cv2.cvtColor(s, cv2.COLOR_BGR2GRAY)
            ns_gray = cv2.cvtColor(ns, cv2.COLOR_BGR2GRAY)
            
            diff = cv2.absdiff(s_gray, ns_gray)
            mse = np.mean(diff)
            
            # Normalize to 0-100. Cap max meaningful change at MSE=50.
            score = min(100.0, (mse / 50.0) * 100.0)
            return score
        except Exception:
            return 0.0

    def _goal_reward(self, ns, goal) -> float:
        """Measure how similar the new state is to the final goal state."""
        from .goal_matcher import GoalMatcher
        matcher = GoalMatcher()
        
        # Check if the goal image appears completely inside the current screen
        # Or if the the whole screen matches the goal
        res1 = matcher.compare(ns, goal, method='mse')
        
        # Template match if goal is smaller
        res2 = 0.0
        if goal.shape[0] < ns.shape[0] and goal.shape[1] < ns.shape[1]:
            res2 = matcher.compare(ns, goal, method='template')
            
        return max(res1, res2)
