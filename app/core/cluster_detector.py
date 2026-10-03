"""
Cluster Detector using OpenCV.
Used for finding high-intensity areas (heatmaps) or specific color blobs.
"""
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class ClusterDetector:
    def __init__(self):
        pass

    def detect_hotspots(self, image_np, color_range=None, threshold=200, min_area=10):
        """
        Detect loudest/brightest clusters in an image.
        If color_range is specified as (lower_hsv, upper_hsv), matches color blob instead.
        """
        try:
            if color_range:
                # Color based clustering
                lower_bound = np.array(color_range[0])
                upper_bound = np.array(color_range[1])
                hsv = cv2.cvtColor(image_np, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, lower_bound, upper_bound)
            else:
                # Intensity based clustering (grayscale brightness)
                gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
            
            # Clean up mask (remove small noise)
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            hotspots = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area:
                    continue
                    
                # Calculate center of mass for the blob
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # Bounding box
                    x, y, w, h = cv2.boundingRect(cnt)
                    
                    hotspots.append({
                        'center': (cx, cy),
                        'box': (x, y, w, h),
                        'area': area,
                        'intensity': np.mean(mask[y:y+h, x:x+w]) # Average mask intensity
                    })
            
            # Sort by area descending (largest clusters first)
            hotspots.sort(key=lambda item: item['area'], reverse=True)
            return hotspots
            
        except Exception as e:
            logger.error(f"Hotspot detection failed: {e}")
            return []

    def draw_clusters(self, image_np, clusters):
        """Utility function to draw red boxes around clusters for debugging."""
        out = image_np.copy()
        for c in clusters:
            x, y, w, h = c['box']
            cv2.rectangle(out, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.circle(out, c['center'], 4, (0, 255, 0), -1)
        return out
