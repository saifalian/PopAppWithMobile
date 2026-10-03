import logging
import time
import random

logger = logging.getLogger(__name__)

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE    = 0.05
    HAS_PYAUTOGUI = True
except ImportError as e:
    logger.warning(f"Could not import pyautogui: {e}")
    HAS_PYAUTOGUI = False


def execute_action(action: dict, humanize: dict = None, condition_evaluator=None) -> bool:
    """
    Executes a specific action.
    Now supports conditional logic:
    {
       "type": "condition",
       "check": "no_popup",
       "then": [...],
       "else": [...]
    }
    """
    atype = action.get("type", "wait").lower()

    if atype == "condition":
        return _handle_condition(action, humanize, condition_evaluator)

    # Standard actions...
    
    if not HAS_PYAUTOGUI:
        logger.error(f"Cannot execute {atype}: pyautogui not available")
        return False

    try:
        if atype in ("click", "double_click", "right_click"):
            x, y = _humanize_coords(
                action["x"], action["y"], humanize
            )
            if atype == "click":
                pyautogui.click(x=x, y=y)
            elif atype == "double_click":
                pyautogui.doubleClick(x=x, y=y)
            elif atype == "right_click":
                pyautogui.rightClick(x=x, y=y)

        elif atype == "drag":
            dur = action.get("duration", 0.3)
            if humanize:
                dur *= (1 + random.uniform(
                    -humanize.get("speed_variance", 0),
                     humanize.get("speed_variance", 0)
                ))
            pyautogui.moveTo(action["x1"], action["y1"])
            pyautogui.dragTo(action["x2"], action["y2"], duration=dur)

        elif atype == "scroll":
            x = action.get("x")
            y = action.get("y")
            if x and y:
                pyautogui.moveTo(x, y)
            pyautogui.scroll(int(action.get("amount", -3)))

        elif atype == "key":
            key = action.get("key", "")
            if "+" in key:
                pyautogui.hotkey(*[k.strip() for k in key.split("+")])
            else:
                pyautogui.press(key)

        elif atype == "wait":
            secs = float(action.get("seconds", 0.5))
            if humanize:
                lo, hi = humanize.get("random_wait_between_steps", [0, 0])
                secs  += random.uniform(lo, hi)
            time.sleep(secs)

        elif atype == "type":
            interval = 0.05
            if humanize:
                interval += random.uniform(0, 0.05)
            pyautogui.typewrite(
                str(action.get("text", "")),
                interval=interval
            )

        elif atype == "move":
            pyautogui.moveTo(action["x"], action["y"])

        else:
            logger.warning(f"Unknown action type: {atype}")
            return False

        return True

    except Exception as e:
        logger.error(f"Action error ({atype}): {e}")
        return False


def _handle_condition(action, humanize, evaluator):
    if not evaluator:
        logger.warning("Condition action encountered but no evaluator provided.")
        return True # Skip by default if no evaluator
    
    check_name = action.get("check")
    passed = False
    
    # Try calling the check on the evaluator
    if hasattr(evaluator, check_name):
        res = getattr(evaluator, check_name)()
        if isinstance(res, tuple):
            passed = res[0]
        else:
            passed = bool(res)
    else:
        logger.warning(f"Evaluator does not have check: {check_name}")
        
    branch = action.get("then" if passed else "else", [])
    for step in branch:
        execute_action(step, humanize, evaluator)
        
    return True


def _humanize_coords(
    x: int, y: int, humanize: dict = None
) -> tuple[int, int]:
    if not humanize:
        return x, y
    offset = humanize.get("offset_px", 0)
    if offset > 0:
        x += random.randint(-offset, offset)
        y += random.randint(-offset, offset)
    return x, y


def execute_sequence(steps: list, humanize: dict = None) -> bool:
    for step in steps:
        execute_action(step, humanize)
    return True
