import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def detect_clusters(
    image: np.ndarray,
    min_area: int = 200
) -> list:
    """
    Detect red/purple liquidity clusters in Coinglass heatmap.
    Returns sorted list by area (largest first = highest value wall).
    """
    if image is None or image.size == 0:
        return []

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Red (wraps around hue 0/180)
    m1 = cv2.inRange(hsv, np.array([0,  80, 80]),
                          np.array([10, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([160, 80, 80]),
                          np.array([180, 255, 255]))
    red = cv2.bitwise_or(m1, m2)

    # Purple
    purple = cv2.inRange(hsv, np.array([130, 50, 50]),
                               np.array([160, 255, 255]))

    mask = cv2.bitwise_or(red, purple)

    # Morphological cleanup — close gaps, remove noise
    kernel = np.ones((5, 5), np.uint8)
    mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    clusters = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        cx, cy     = x + w // 2, y + h // 2
        color = (
            "purple"
            if np.mean(purple[y:y+h, x:x+w]) > np.mean(red[y:y+h, x:x+w])
            else "red"
        )
        clusters.append({
            "x": int(x), "y": int(y),
            "w": int(w), "h": int(h),
            "cx": int(cx), "cy": int(cy),
            "area": int(area),
            "color": color,
        })

    clusters.sort(key=lambda c: c["area"], reverse=True)
    return clusters
