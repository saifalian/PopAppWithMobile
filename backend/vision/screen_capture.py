import logging
import numpy as np
import mss

logger = logging.getLogger(__name__)


def capture_region(region: dict) -> np.ndarray | None:
    if not region:
        return capture_full()
    try:
        with mss.mss() as sct:
            monitor = {
                "left":   region["x1"],
                "top":    region["y1"],
                "width":  region["x2"] - region["x1"],
                "height": region["y2"] - region["y1"],
            }
            shot = sct.grab(monitor)
            img  = np.array(shot)
            return img[:, :, :3]  # drop alpha, return BGR
    except Exception as e:
        logger.error(f"Region capture error: {e}")
        return None


def capture_full() -> np.ndarray | None:
    try:
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[1])
            img  = np.array(shot)
            return img[:, :, :3]
    except Exception as e:
        logger.error(f"Full capture error: {e}")
        return None
