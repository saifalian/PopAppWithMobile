"""
Mini performance sparkline widget.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QPath
from PyQt6.QtCore import Qt
from app.theme import C

class MiniChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []
        self.setMinimumHeight(30)
        self.setMinimumWidth(100)

    def set_data(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        if len(self.points) < 2:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor(C["purple_l"]), 2)
        painter.setPen(pen)
        
        w, h = self.width(), self.height()
        max_p = max(self.points) if self.points else 1
        min_p = min(self.points) if self.points else 0
        range_p = max(1, max_p - min_p)
        
        path = QPath()
        for i, p in enumerate(self.points):
            x = (i / (len(self.points) - 1)) * w
            y = h - ((p - min_p) / range_p) * h
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        
        painter.drawPath(path)
