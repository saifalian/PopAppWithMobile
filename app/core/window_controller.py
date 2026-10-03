"""
Window Controller using win32gui.
Finds, focuses, and gets the bounds of application windows.
"""
import logging
import ctypes
import time

logger = logging.getLogger(__name__)

class WindowController:
    def __init__(self):
        self._win32gui = None
        self._win32con = None
        self._is_windows = False
        
        try:
            import win32gui
            import win32con
            self._win32gui = win32gui
            self._win32con = win32con
            self._is_windows = True
        except ImportError:
            logger.warning("win32gui not installed or not on Windows. Window control disabled.")

    def find_window(self, title_part: str):
        """Find the first window containing title_part."""
        if not self._is_windows:
            return None

        hwnd_list = []
        def callback(hwnd, extra):
            if self._win32gui.IsWindowVisible(hwnd):
                title = self._win32gui.GetWindowText(hwnd)
                if title_part.lower() in title.lower():
                    hwnd_list.append((hwnd, title))
                    
        self._win32gui.EnumWindows(callback, None)
        
        if hwnd_list:
            logger.debug(f"Found window: {hwnd_list[0][1]}")
            return hwnd_list[0][0]
        return None

    def focus_window(self, hwnd) -> bool:
        """Restore and bring the window to the foreground."""
        if not self._is_windows or not hwnd:
            return False
            
        try:
            # If minimized, restore it
            placement = self._win32gui.GetWindowPlacement(hwnd)
            if placement[1] == self._win32con.SW_SHOWMINIMIZED:
                self._win32gui.ShowWindow(hwnd, self._win32con.SW_RESTORE)
            else:
                self._win32gui.ShowWindow(hwnd, self._win32con.SW_SHOW)
                
            # Allow process to take focus
            self._win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.2) # Give OS time to bring to front
            return True
        except Exception as e:
            logger.error(f"Error focusing window {hwnd}: {e}")
            return False

    def get_window_rect(self, hwnd) -> tuple:
        """Get the (left, top, width, height) of a window."""
        if not self._is_windows or not hwnd:
            return None
            
        try:
            rect = self._win32gui.GetWindowRect(hwnd)
            # rect is (left, top, right, bottom)
            x, y, right, bottom = rect
            w = right - x
            h = bottom - y
            return (x, y, w, h)
        except Exception as e:
            logger.error(f"Error getting rect for window {hwnd}: {e}")
            return None
