from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

class PcRegionVisualizer(QWidget):
    """
    A non-interactive, always-on-top overlay that highlights a PC screen region.
    It is transparent to mouse clicks (pass-through).
    """
    def __init__(self):
        super().__init__()
        # Frameless, Always on Top, Tool window (no taskbar icon), Click-through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        # Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.region_rect = QRect()
        self.region_name = ""
        self.color = QColor(0, 255, 255, 200) # Cyan by default

    def set_region(self, x1, y1, x2, y2, name=""):
        """Sets the screen geometry and label for this visualizer."""
        self.region_rect = QRect(QPoint(x1, y1), QPoint(x2, y2)).normalized()
        self.region_name = name
        
        # Set full-screen geometry but only draw in the specific area
        # Actually, it's more efficient to just set geometry to the rect
        # and draw a border around our own edges.
        self.setGeometry(self.region_rect.adjusted(-2, -2, 2, 2)) # Padding for border
        self.update()
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a bright border
        pen = QPen(self.color, 3)
        painter.setPen(pen)
        
        # Draw the rect (relative to our widget's geometry)
        draw_rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawRect(draw_rect)
        
        # Draw label at the top-left
        if self.region_name:
            painter.setBrush(self.color)
            label_rect = QRect(draw_rect.topLeft(), QPoint(draw_rect.left() + 100, draw_rect.top() + 18))
            painter.drawRect(label_rect)
            
            painter.setPen(QColor(0, 0, 0))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(label_rect.adjusted(5, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, self.region_name)
