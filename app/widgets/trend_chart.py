import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QLinearGradient
from PyQt6.QtCore import Qt, QRectF

from app.theme import C

class TrendChart(QWidget):
    """
    A custom, lightweight line chart widget for displaying performance history.
    Uses QPainter for smooth antialiased lines and gradients matching the premium aesthetic.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self._data = []
        self._max_value = 100.0
        self._min_value = 0.0

    def set_data(self, data):
        """Update the chart with a list of float values."""
        self._data = data
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        width = rect.width()
        height = rect.height()
        
        # Margins inside the widget
        margin_x = 10
        margin_y = 10
        chart_w = width - 2 * margin_x
        chart_h = height - 2 * margin_y
        
        # Calculate scales
        n_points = len(self._data)
        if n_points < 2:
            return # Need at least 2 points to draw a meaningful line
            
        x_step = chart_w / (n_points - 1)
        value_range = max(1.0, self._max_value - self._min_value) # Avoid division by zero
        
        # Build the path
        path = QPainterPath()
        
        for i, val in enumerate(self._data):
            # Clamp value
            val = max(self._min_value, min(self._max_value, val))
            
            x = margin_x + i * x_step
            # Y goes from top to bottom, so we invert
            y = margin_y + chart_h - ((val - self._min_value) / value_range) * chart_h
            
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
                
        # Draw the line with a gradient using the theme's cyan color
        pen = QPen(QColor(C['cyan']))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        painter.drawPath(path)
        
        # Optional: draw subtle gradient fill underneath the line
        fill_path = QPainterPath(path)
        fill_path.lineTo(margin_x + chart_w, rect.bottom())
        fill_path.lineTo(margin_x, rect.bottom())
        fill_path.closeSubpath()
        
        gradient = QLinearGradient(0, margin_y, 0, rect.bottom())
        # Cyan with some opacity at the top fading to transparent at the bottom
        gradient.setColorAt(0.0, QColor(C['cyan'] + "44")) # ~25% alpha
        gradient.setColorAt(1.0, QColor(C['bg_darkest'] + "00"))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(fill_path)
