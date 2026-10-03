"""
Region Picker Dialog.
A full-screen transparent overlay to click-and-drag a region for the model vision.
"""
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

class RegionPickerDialog(QWidget):
    region_selected = pyqtSignal(dict) # Emits {"x1", "y1", "x2", "y2"}

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Capture screen for background
        screen = QApplication.primaryScreen()
        if screen:
            self.background_pixmap = screen.grabWindow(0)
        else:
            self.background_pixmap = None

        self.start_pos = None
        self.current_pos = None
        self.selection_rect = QRect()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = self.start_pos
            self.selection_rect = QRect()
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.close()

    def mouseMoveEvent(self, event):
        if self.start_pos is not None:
            self.current_pos = event.pos()
            self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.start_pos is not None:
            x1 = self.selection_rect.left()
            y1 = self.selection_rect.top()
            x2 = self.selection_rect.right()
            y2 = self.selection_rect.bottom()
            
            # Require minimum size
            if (x2 - x1) > 10 and (y2 - y1) > 10:
                self.region_selected.emit({
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2
                })
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw the screenshot background
        if self.background_pixmap:
            painter.drawPixmap(self.rect(), self.background_pixmap)
            
        # Semi-transparent dark overlay (vignette effect)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))

        if not self.selection_rect.isNull():
            # Border
            pen = QPen(QColor(0, 255, 128), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)
            
            # Highlight selected area (clearer)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.selection_rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Inner border for contrast
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
            painter.drawRect(self.selection_rect.adjusted(1, 1, -1, -1))
