"""
Pc Action Capture Overlay.
A full-screen transparent window that captures exactly one click or swipe and then closes.
"""
import time
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QColor, QPen

class PcActionCaptureOverlay(QWidget):
    # Emits {"type": "click/swipe", "x1", "y1", "x2", "y2", "duration"}
    action_captured = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        # Use window opacity instead of WA_TranslucentBackground for better Windows compatibility
        self.setWindowOpacity(0.01)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        self.start_pos = None
        self.start_time = 0
        self._captured = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.start_time = time.time()
        elif event.button() == Qt.MouseButton.RightButton:
            self.close()

    def mouseReleaseEvent(self, event):
        if self._captured or event.button() != Qt.MouseButton.LeftButton:
            return
            
        if self.start_pos is None: return
        
        end_pos = event.pos()
        duration = time.time() - self.start_time
        
        # Calculate distance to distinguish click vs swipe
        dist = ( (end_pos.x() - self.start_pos.x())**2 + (end_pos.y() - self.start_pos.y())**2 )**0.5
        
        action = {
            "x1": self.start_pos.x(),
            "y1": self.start_pos.y(),
            "x2": end_pos.x(),
            "y2": end_pos.y(),
            "duration": round(duration, 2),
            "type": "swipe" if dist > 20 else "click"
        }
        
        self._captured = True
        self.action_captured.emit(action)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

