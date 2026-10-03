"""
Desktop action executor using pyautogui.
Wraps core OS interactions with safety bounds and humanized movement.
"""
import logging
import random
import time
import pyautogui

logger = logging.getLogger(__name__)

# Safety settings
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True

class ActionExecutor:
    def __init__(self, humanize=True):
        self.humanize = humanize
        # Get screen size to clamp coordinates
        self.screen_width, self.screen_height = pyautogui.size()

    def _clamp(self, x, y):
        """Ensure coordinates stay within screen bounds to prevent PyAutoGUI failures."""
        cx = max(0, min(x, self.screen_width - 1))
        cy = max(0, min(y, self.screen_height - 1))
        return cx, cy

    def click(self, x, y, button='left', clicks=1):
        """Move to (x,y) and click."""
        cx, cy = self._clamp(x, y)
        self.move_to(cx, cy)
        
        if self.humanize:
            time.sleep(random.uniform(0.05, 0.15))
            
        logger.debug(f"Clicking at ({cx}, {cy}) with {button}")
        pyautogui.click(x=cx, y=cy, clicks=clicks, button=button)

    def drag(self, start_x, start_y, end_x, end_y, duration=0.5):
        """Click and drag from start to end."""
        self.move_to(start_x, start_y)
        sx, sy = self._clamp(start_x, start_y)
        ex, ey = self._clamp(end_x, end_y)
        
        logger.debug(f"Dragging from ({sx},{sy}) to ({ex},{ey})")
        
        if self.humanize:
            duration += random.uniform(-0.1, 0.2)
            
        pyautogui.moveTo(sx, sy)
        pyautogui.dragTo(ex, ey, duration=max(0.1, duration), button='left')

    def type_text(self, text, interval=0.05):
        """Type out a string of text."""
        logger.debug(f"Typing: {text}")
        
        if self.humanize:
            # Vary typing speed slightly for realism
            for char in text:
                pyautogui.write(char)
                time.sleep(interval + random.uniform(-0.02, 0.05))
        else:
            pyautogui.write(text, interval=interval)

    def press_key(self, key):
        """Press a specific key (e.g. 'enter', 'esc')."""
        logger.debug(f"Pressing: {key}")
        pyautogui.press(key)

    def move_to(self, x, y, duration=0.2):
        """Smoothly move the mouse to a coordinate."""
        cx, cy = self._clamp(x, y)
        
        if self.humanize:
            # Human-like movement duration
            dist = ((pyautogui.position()[0] - cx)**2 + (pyautogui.position()[1] - cy)**2)**0.5
            duration = min(0.8, max(0.1, dist / 2000.0)) + random.uniform(0, 0.1)
            
        pyautogui.moveTo(cx, cy, duration=duration, tween=pyautogui.easeInOutQuad)
