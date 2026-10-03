import time
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QColor, QPen

class PcRegionSelectionOverlay(QWidget):
    """A full-screen transparent window for selecting a rectangular PC screen region."""
    region_selected = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        # Simple opacity - this worked before and is reliable
        self.setWindowOpacity(0.3)
        self.setStyleSheet("background-color: black;")
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        self.start_pos = None
        self.current_pos = None
        self._is_drawing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self._is_drawing = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.close()

    def mouseMoveEvent(self, event):
        if self._is_drawing:
            self.current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_drawing:
            end_pos = event.pos()
            rect = QRect(self.start_pos, end_pos).normalized()
            
            if rect.width() > 5 and rect.height() > 5:
                region = {
                    "x1": rect.left(),
                    "y1": rect.top(),
                    "x2": rect.right(),
                    "y2": rect.bottom(),
                    "source": "pc"
                }
                self.region_selected.emit(region)
            
            self._is_drawing = False
            self.close()

    def paintEvent(self, event):
        if self._is_drawing and self.start_pos and self.current_pos:
            painter = QPainter(self)
            rect = QRect(self.start_pos, self.current_pos).normalized()
            
            # Simple border
            painter.setPen(QPen(QColor(0, 255, 128), 2))
            painter.setBrush(QColor(0, 255, 128, 40))
            painter.drawRect(rect)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
