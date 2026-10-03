import logging
import subprocess

logger = logging.getLogger(__name__)

try:
    import win32gui
    import win32con
    WIN32 = True
except ImportError:
    WIN32 = False
    logger.warning("pywin32 not available")


def find_window(title_contains: str) -> int | None:
    if not WIN32:
        return None
    found = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if title_contains.lower() in win32gui.GetWindowText(hwnd).lower():
                found.append(hwnd)
    win32gui.EnumWindows(cb, None)
    return found[0] if found else None


def bring_to_front(hwnd: int) -> bool:
    if not WIN32 or not hwnd:
        return False
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        logger.error(f"bring_to_front: {e}")
        return False


def focus_coinglass() -> bool:
    hwnd = find_window("Coinglass")
    if hwnd:
        return bring_to_front(hwnd)
    return False


def is_running(title: str) -> bool:
    return find_window(title) is not None


def launch(exe_path: str) -> bool:
    try:
        subprocess.Popen(exe_path)
        return True
    except Exception as e:
        logger.error(f"Launch error: {e}")
        return False
