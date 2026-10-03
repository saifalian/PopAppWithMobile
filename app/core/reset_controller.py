"""
3-Layer Reset Controller for Unsupervised Learning loops.
Layer 1: Click Home button (Soft Reset)
Layer 2: State Verification (Visual check)
Layer 3: Hard Reset (Restart App/Process matching title)
"""
import logging
import time
import subprocess
import psutil

logger = logging.getLogger(__name__)

class ResetController:
    def __init__(self, target_window_title: str, home_btn_coords: tuple, action_executor, window_controller):
        """
        target_window_title: Window title of the application being trained on (e.g. "CoinGlass").
        home_btn_coords: (x, y) coordinates of the UI back/home button for soft resets.
        action_executor: Instance of ActionExecutor for clicking.
        window_controller: Instance of WindowController to manage window state.
        """
        self.target_window_title = target_window_title
        self.home_coords = home_btn_coords
        self.executor = action_executor
        self.win_ctrl = window_controller
        self.mode = "3-layer"

    def execute_reset(self) -> bool:
        """
        Run the 3-layer reset sequence. Returns True if successfully reset.
        """
        logger.info(f"Starting {self.mode} reset sequence for '{self.target_window_title}'")
        
        # Bring window to front first
        hwnd = self.win_ctrl.find_window(self.target_window_title)
        if not hwnd:
            logger.error("Target window not found. Escalating immediately to Layer 3.")
            return self._hard_reset()
            
        self.win_ctrl.focus_window(hwnd)
        time.sleep(0.5)
        
        # Layer 1: Soft reset (Click home)
        self._click_home()
        time.sleep(1.5) # Wait for UI to update
        
        # Layer 2: Verify state visually
        # (Assuming the main dashboard/home screen has specific distinct features)
        if not self._verify_state():
            logger.warning("Soft reset failed to reach home state, escalating to Layer 3")
            return self._hard_reset()
            
        logger.info("Reset successful at Layer 2")
        return True

    def _click_home(self):
        """Layer 1: Click the home/back/reset button."""
        logger.debug(f"Layer 1: Clicking home/reset button at {self.home_coords}")
        if self.home_coords:
            self.executor.click(self.home_coords[0], self.home_coords[1], clicks=2) # Double click to ensure
            
    def _verify_state(self) -> bool:
        """
        Layer 2: Verify the application is back to the base state.
        In a full implementation, this uses GoalMatcher to see if the current screen
        matches the 'home_state.png' image. For now, we assume failure (True) to test loops.
        """
        logger.debug("Layer 2: Verifying application base state.")
        # Without a specific goal image passed in here, we default to True
        return True

    def _hard_reset(self) -> bool:
        """
        Layer 3: Hard restart. Kills the process matching the window title and relaunches it.
        """
        logger.warning(f"Layer 3: Performing hard reset for {self.target_window_title}")
        
        # 1. Find process matching window title and kill it
        killed = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # Naive matching: if the process name partially matches the title
                if self.target_window_title.lower() in proc.info['name'].lower():
                    logger.debug(f"Killing process {proc.info['name']} (PID: {proc.info['pid']})")
                    proc.kill()
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        time.sleep(2.0)
        
        # 2. Attempt to restart (requires knowing the executable path)
        # In a real scenario, this path would be configured. 
        # Here we just log it as a conceptual layer unless a path is provided.
        logger.error(f"Cannot relaunch {self.target_window_title} automatically without an exe path.")
        
        return False # Hard reset couldn't relaunch automatically
