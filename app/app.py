"""
QApplication setup and lifecycle management.
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication, QPushButton, QCheckBox, QRadioButton, QComboBox, QSlider
from PyQt6.QtCore import Qt, QObject, QEvent
from app.main_window import MainWindow
from app.theme import QSS

class GlobalCursorFilter(QObject):
    """Event filter to apply pointing hand cursor to all buttons/interactive widgets."""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            if isinstance(obj, (QPushButton, QCheckBox, QRadioButton, QComboBox, QSlider)):
                obj.setCursor(Qt.CursorShape.PointingHandCursor)
        return super().eventFilter(obj, event)

def create_app():
    app = QApplication(sys.argv)
    app.setApplicationName("ModelFactory")
    app.setApplicationVersion("1.0.0")
    
    # 10/10 NUCLEAR FIX: Global font enforcement & Hinting lockdown
    from PyQt6.QtGui import QFont, QFontDatabase
    
    global_font = QFont("Segoe UI", 9)
    global_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(global_font)
    
    # 🎯 Surgical Override: Stop fallbacks for system bold dialogs (pointsize 11/16px)
    bold_font = QFont("Segoe UI", 11, QFont.Weight.Bold)
    bold_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    
    app.setStyleSheet(QSS + f"""
        * {{ font-family: "Segoe UI"; }}
        QDialog, QMessageBox, QInputDialog {{ font-family: "Segoe UI"; font-size: 13px; }}
        QLabel {{ font-family: "Segoe UI"; }}
    """)
    
    # Global cursor filter
    app._cursor_filter = GlobalCursorFilter()
    app.installEventFilter(app._cursor_filter)
    
    return app
