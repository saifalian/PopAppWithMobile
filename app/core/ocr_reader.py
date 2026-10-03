"""
OCR Reader using pytesseract.
Extracts text and finds coordinates of specific phrases on screen.
"""
import logging
import pytesseract
import cv2
import PIL.Image
import re

logger = logging.getLogger(__name__)

class OCRReader:
    def __init__(self, tesseract_path=None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
    def _preprocess(self, image_np):
        """Preprocess image for better OCR results."""
        # Convert to grayscale
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        
        # Scaling up helps Tesseract read small UI fonts
        scaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        
        # Thresholding
        _, thresh = cv2.threshold(scaled, 150, 255, cv2.THRESH_TRUNC)
        return thresh

    def read_text(self, image_np, config="--psm 11") -> str:
        """
        Extract text from a numpy image array.
        Uses PSM 11 (Sparse text. Find as much text as possible) by default for UIs.
        """
        try:
            processed = self._preprocess(image_np)
            
            # Tesseract expects PIL
            pil_img = PIL.Image.fromarray(processed)
            text = pytesseract.image_to_string(pil_img, config=config)
            
            # Clean up excessive newlines/whitespace
            cleaned = re.sub(r'\n+', '\n', text.strip())
            return cleaned
        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract not found. Please install it or set the correct path.")
            return ""
        except Exception as e:
            logger.error(f"OCR Error: {e}")
            return ""

    def find_text_coordinates(self, image_np, search_text, exact_match=False):
        """
        Find center coordinates of a specific piece of text.
        Returns multiple locations if found multiple times.
        """
        try:
            processed = self._preprocess(image_np)
            data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
            
            results = []
            search_lower = search_text.lower()
            
            for i, text in enumerate(data['text']):
                txt_lower = text.lower().strip()
                if not txt_lower:
                    continue
                    
                match = (txt_lower == search_lower) if exact_match else (search_lower in txt_lower)
                
                if match:
                    # Account for the 2x scaling done in preprocessing
                    x = (data['left'][i] + data['width'][i] // 2) // 2
                    y = (data['top'][i] + data['height'][i] // 2) // 2
                    conf = int(data['conf'][i])
                    
                    if conf > 30: # Filter out absolute garbage
                        results.append({'x': x, 'y': y, 'confidence': conf, 'text': text})
                        
            return sorted(results, key=lambda r: r['confidence'], reverse=True)
            
        except Exception as e:
            logger.error(f"Text locate error: {e}")
            return []
