"""
Goal Image Matcher using OpenCV Template Matching and structural similarity.
"""
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class GoalMatcher:
    def __init__(self):
        pass

    def compare(self, current_img, goal_img, method='mse') -> float:
        """
        Compare current image to goal image.
        Returns absolute similarity score 0.0 to 100.0.
        Method can be 'mse' (Mean Squared Error) or 'template' (Template Matching).
        """
        try:
            if current_img is None or goal_img is None:
                return 0.0
                
            c_gray = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
            g_gray = cv2.cvtColor(goal_img, cv2.COLOR_BGR2GRAY)
            
            if method == 'mse':
                # MSE is very fast, good for checking if the entire screen looks exactly like goal
                if c_gray.shape != g_gray.shape:
                    g_gray = cv2.resize(g_gray, (c_gray.shape[1], c_gray.shape[0]))
                    
                diff = cv2.absdiff(c_gray, g_gray)
                mse = np.mean(diff)
                
                # Normalize MSE to 0-100 score where 0 MSE = 100 Score
                # Max diff for a pixel is 255. 
                score = max(0.0, 100.0 - (mse / 255.0 * 100.0))
                return score
                
            elif method == 'template':
                # Template matching checks if the goal image EXISTS SOMEWHERE in the current image
                if g_gray.shape[0] > c_gray.shape[0] or g_gray.shape[1] > c_gray.shape[1]:
                    logger.warning("Goal image is larger than current image, template match impossible.")
                    return 0.0
                    
                res = cv2.matchTemplate(c_gray, g_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                # TM_CCOEFF_NORMED returns -1.0 to 1.0. We want 0-100
                score = max(0.0, max_val * 100.0)
                return score
            else:
                logger.error(f"Unknown compare method: {method}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Goal Matching Error: {e}")
            return 0.0

    def find_sub_image(self, main_image, sub_image, threshold=0.8):
        """
        Find coordinates of a sub-image inside a main image if it exists.
        Returns top-left coordinate (x,y) or None.
        """
        try:
            m_gray = cv2.cvtColor(main_image, cv2.COLOR_BGR2GRAY)
            s_gray = cv2.cvtColor(sub_image, cv2.COLOR_BGR2GRAY)
            
            res = cv2.matchTemplate(m_gray, s_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            if max_val >= threshold:
                return max_loc # (x, y)
            return None
        except Exception as e:
            logger.error(f"Sub-image find error: {e}")
            return None
