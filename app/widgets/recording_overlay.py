from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from app.theme import C

class RecordingOverlay(QWidget):
    """
    A persistent, always-on-top overlay for controlling the macro recorder.
    Emits signals for pause, resume, and stop.
    """
    stop_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 80)
        
        self.is_paused = False
        self._blink = False
        self.seconds_elapsed = 0
        
        self._setup_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.card = QFrame()
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {C['bg_darkest']};
                border: 1px solid {C['border']};
                border-radius: 40px;
                border-left: 4px solid {C['red']};
            }}
        """)
        
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(20, 10, 20, 10)
        card_layout.setSpacing(15)
        
        # Recording indicator
        self.indicator = QLabel("●")
        self.indicator.setStyleSheet(f"color: {C['red']}; font-size: 20px;")
        card_layout.addWidget(self.indicator)
        
        # Timer / Status Text
        self.status_lbl = QLabel("00:00")
        self.status_lbl.setStyleSheet(f"color: {C['white']}; font-size: 16px; font-weight: bold; border: none;")
        card_layout.addWidget(self.status_lbl)
        
        card_layout.addStretch()
        
        # Pause/Resume Button
        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setFixedSize(40, 40)
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.setStyleSheet(self._btn_style(C['amber']))
        self.pause_btn.clicked.connect(self._toggle_pause)
        card_layout.addWidget(self.pause_btn)
        
        # Stop Button
        self.stop_btn = QPushButton("■")
        self.stop_btn.setFixedSize(40, 40)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet(self._btn_style(C['red']))
        self.stop_btn.clicked.connect(self._on_stop)
        card_layout.addWidget(self.stop_btn)
        
        layout.addWidget(self.card)

    def _btn_style(self, color):
        return f"""
            QPushButton {{
                background-color: {C['bg_sidebar']};
                color: {color};
                border: 1px solid {color}44;
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}22;
                border: 1px solid {color};
            }}
        """

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText("▶")
            self.pause_btn.setStyleSheet(self._btn_style(C['green']))
            self.indicator.setStyleSheet(f"color: {C['amber']}; font-size: 20px;")
            self.card.setStyleSheet(f"""
                QFrame {{
                    background-color: {C['bg_darkest']};
                    border: 1px solid {C['border']};
                    border-radius: 40px;
                    border-left: 4px solid {C['amber']};
                }}
            """)
            self.pause_requested.emit()
        else:
            self.pause_btn.setText("⏸")
            self.pause_btn.setStyleSheet(self._btn_style(C['amber']))
            self.indicator.setStyleSheet(f"color: {C['red']}; font-size: 20px;")
            self.card.setStyleSheet(f"""
                QFrame {{
                    background-color: {C['bg_darkest']};
                    border: 1px solid {C['border']};
                    border-radius: 40px;
                    border-left: 4px solid {C['red']};
                }}
            """)
            self.resume_requested.emit()

    def _on_stop(self):
        self.stop_requested.emit()

    def _on_tick(self):
        if not self.is_paused:
            self.seconds_elapsed += 1
            mins = self.seconds_elapsed // 60
            secs = self.seconds_elapsed % 60
            self.status_lbl.setText(f"{mins:02d}:{secs:02d}")
            
            self._blink = not self._blink
            color = C['red'] if self._blink else f"{C['red']}44"
            self.indicator.setStyleSheet(f"color: {color}; font-size: 20px; border: none;")

    def start_recording(self):
        self.is_paused = True
        self.seconds_elapsed = 0
        self.status_lbl.setText("Ready")
        self.pause_btn.setText("▶")
        self.pause_btn.setStyleSheet(self._btn_style(C['green']))
        self.indicator.setStyleSheet(f"color: {C['amber']}; font-size: 20px;")
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {C['bg_darkest']};
                border: 1px solid {C['border']};
                border-radius: 40px;
                border-left: 4px solid {C['amber']};
            }}
        """)
        
        # Position near top center of primary screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = 50
        self.move(x, y)
        
        self.show()
        self.raise_()
        self.timer.start(1000)

    def stop_recording(self):
        self.timer.stop()
        self.hide()
