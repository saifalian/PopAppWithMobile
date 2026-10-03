import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def compute_similarity(
    img1: np.ndarray,
    img2: np.ndarray
) -> float:
    """
    Normalized cross-correlation similarity.
    Robust to brightness differences.
    Returns 0.0 to 1.0.
    """
    try:
        size = (224, 224)
        a    = cv2.resize(img1, size)
        b    = cv2.resize(img2, size)
        ag   = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float32)
        bg   = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float32)
        an   = (ag - ag.mean()) / (ag.std() + 1e-8)
        bn   = (bg - bg.mean()) / (bg.std() + 1e-8)
        corr = float(np.mean(an * bn))
        return float(np.clip((corr + 1) / 2, 0.0, 1.0))
    except Exception as e:
        logger.error(f"Similarity error: {e}")
        return 0.0
