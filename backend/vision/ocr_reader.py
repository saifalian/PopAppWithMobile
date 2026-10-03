import logging
import re
import cv2
import numpy as np
import pytesseract

logger = logging.getLogger(__name__)
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def read_popup(image: np.ndarray) -> dict:
    if image is None:
        return {
            "success": False, "price": None,
            "value_str": None, "usd": None
        }

    # Scale up 3× for better OCR accuracy
    scale = 3
    h, w  = image.shape[:2]
    large = cv2.resize(
        image, (w * scale, h * scale),
        interpolation=cv2.INTER_CUBIC
    )
    gray  = cv2.cvtColor(large, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    config = "--psm 6 -c tessedit_char_whitelist=0123456789.,MKBmkb$%"
    try:
        text = pytesseract.image_to_string(th, config=config)
        return _parse(text)
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return {
            "success": False, "price": None,
            "value_str": None, "usd": None
        }


def _parse(text: str) -> dict:
    text = text.strip().upper()

    # Parse dollar value: 2.3M, 450K, 1.2B
    vm = re.search(r'(\d+\.?\d*)\s*([MKB])', text)
    usd = value_str = None
    if vm:
        num = float(vm.group(1))
        m   = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[vm.group(2)]
        usd       = num * m
        value_str = f"{num}{vm.group(2)}"

    # Parse price: 1.3777
    pm = re.findall(r'(\d+\.\d{2,6})', text)
    price = float(max(pm, key=len)) if pm else None

    return {
        "success":   price is not None or usd is not None,
        "price":     price,
        "value_str": value_str,
        "usd":       usd,
        "raw_text":  text,
    }
