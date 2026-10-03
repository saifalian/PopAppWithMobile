"""
High-speed screen capture using mss.
Handles multiple monitors and DPI scaling.
"""
import logging
import cv2
import mss
import numpy as np
import ctypes

logger = logging.getLogger(__name__)

class ScreenCapture:
    def __init__(self, monitor_index=1):
        """
        Initialize the screen capture.
        monitor_index: 0 for all monitors, 1 for primary, 2 for secondary, etc.
        """
        try:
            # Tell Windows backend that we are DPI aware so screenshots aren't rescaled
            ctypes.windll.user32.SetProcessDPIAware()
        except AttributeError:
            pass  # Not on Windows
            
        self.sct = mss.mss()
        self.monitor_index = monitor_index
        
        # Verify monitor index exists, fallback to primary if not
        if self.monitor_index >= len(self.sct.monitors):
            logger.warning(f"Monitor {monitor_index} not found. Defaulting to primary (1).")
            self.monitor_index = 1

    def capture(self, region=None) -> np.ndarray:
        """
        Capture screen region and return as BGR numpy array.
        region format: (left, top, width, height)
        """
        try:
            if region:
                monitor = {
                    "top": int(region[1]),
                    "left": int(region[0]),
                    "width": int(region[2]),
                    "height": int(region[3])
                }
            else:
                monitor = self.sct.monitors[self.monitor_index]

            sct_img = self.sct.grab(monitor)
            img_np = np.array(sct_img)
            
            # Convert BGRA to BGR to save memory and match OpenCV standard
            if img_np.shape[2] == 4:
                return cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
            return img_np
            
        except Exception as e:
            logger.error(f"Failed to capture screen: {str(e)}")
            # Return a blank image in case of failure to prevent crashes downstream
            if region:
                return np.zeros((int(region[3]), int(region[2]), 3), dtype=np.uint8)
            else:
                m = self.sct.monitors[self.monitor_index]
                return np.zeros((m['height'], m['width'], 3), dtype=np.uint8)

    def get_monitor_info(self) -> dict:
        """Return information about the currently selected monitor."""
        return self.sct.monitors[self.monitor_index]

    def save_screenshot(self, path, region=None):
        """Helper to quickly save a screenshot to disk."""
        img = self.capture(region)
        cv2.imwrite(path, img)
        logger.debug(f"Screenshot saved to {path}")
