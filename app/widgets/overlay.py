from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar, QListWidget, QGridLayout
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer, pyqtSignal, QRect
import time
from app.theme import C, FONT_UI, FONT_MONO

class SelectionOverlay(QWidget):
    """Semi-transparent rectangular selection box for UI mapping."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._rect = QRect()
        self.hide()

    def set_rect(self, rect):
        self._rect = rect
        self.update()

    def paintEvent(self, event):
        if not self._rect.isNull():
            painter = QPainter(self)
            painter.setPen(QPen(QColor(0, 255, 128), 2))
            painter.setBrush(QColor(0, 255, 128, 40))
            painter.drawRect(self._rect)

class TrainingOverlay(QWidget):
    """Floating draggable training control overlay."""
    def __init__(self, model_name="", handler=None, parent=None):
        super().__init__(None) # Independent window
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(360, 64)
        self._dragging = False
        self._drag_pos = QPoint()
        self.model_name = model_name
        self.handler = handler
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Pill Frame
        self.frame = QFrame()
        self.frame.setFixedHeight(64)
        self.frame.setStyleSheet(f"""
            QFrame {{
                background: #111520;
                border-radius: 32px;
                border: 1px solid #1e2233;
            }}
        """)
        
        fl = QHBoxLayout(self.frame)
        fl.setContentsMargins(0, 0, 16, 0)
        fl.setSpacing(12)
        
        # Left Accent (The curve)
        self.left_accent = QFrame()
        self.left_accent.setFixedSize(24, 64)
        self.left_accent.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border-left: 4px solid {C['amber']};
                border-top-left-radius: 32px;
                border-bottom-left-radius: 32px;
                border-right: none;
                border-top: none;
                border-bottom: none;
            }}
        """)
        fl.addWidget(self.left_accent)
        
        # Line + Dot
        self.line = QFrame()
        self.line.setFixedSize(3, 24)
        self.line.setStyleSheet(f"background: {C['amber']}; border-radius: 1px; border: none;")
        fl.addWidget(self.line)
        
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {C['amber']}; font-size: 10px; background: transparent; border: none;")
        fl.addWidget(self.dot)
        
        # Text
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setMinimumWidth(120)
        self.status_lbl.setStyleSheet(f"color: {C['white']}; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        fl.addWidget(self.status_lbl)
        
        fl.addStretch()
        
        # Buttons
        self.btn_start = QPushButton("▶")
        self.btn_start.setFixedSize(36, 36)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background: #181c2b;
                color: {C['green']};
                border-radius: 18px;
                font-size: 14px;
                border: 1px solid #23283b;
            }}
            QPushButton:hover {{ background: {C['green']}22; border-color: {C['green']}55; }}
        """)
        
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setFixedSize(36, 36)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setStyleSheet(f"""
            QPushButton {{
                background: #181c2b;
                color: {C['amber']};
                border-radius: 18px;
                font-size: 14px;
                border: 1px solid #23283b;
            }}
            QPushButton:hover {{ background: {C['amber']}22; border-color: {C['amber']}55; }}
        """)
        
        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedSize(36, 36)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet(f"""
            QPushButton {{
                background: #181c2b;
                color: {C['red']};
                border-radius: 18px;
                font-size: 12px;
                border: 1px solid #23283b;
            }}
            QPushButton:hover {{ background: {C['red']}22; border-color: {C['red']}55; }}
        """)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: #181c2b;
                color: {C['text_d']};
                border-radius: 18px;
                font-size: 14px;
                border: 1px solid #23283b;
            }}
            QPushButton:hover {{ background: {C['red']}22; color: {C['red']}; border-color: {C['red']}55; }}
        """)
        
        if self.handler:
            self.btn_start.clicked.connect(self._on_start_clicked)
            self.btn_pause.clicked.connect(self._trigger_pause)
            self.btn_stop.clicked.connect(self._trigger_stop)
        
        self.btn_close.clicked.connect(self.hide)
            
        fl.addWidget(self.btn_start)
        fl.addWidget(self.btn_pause)
        fl.addWidget(self.btn_stop)
        fl.addWidget(self.btn_close)
        
        layout.addWidget(self.frame)

    def _on_start_clicked(self):
        # Determine mode from handler if possible, else default to 'gpu' but safe fallback
        mode = "gpu"
        if hasattr(self.handler, "get_device_mode"):
            mode = self.handler.get_device_mode()
        self._trigger_start(mode)

    def _trigger_start(self, mode):
        self._set_state(f"Training ({mode.upper()})", C['green'])
        if self.handler: self.handler._start_training(mode)
        
    def _trigger_pause(self):
        self._set_state("Paused", C['amber'])
        if self.handler: self.handler._pause_training()
        
    def _trigger_stop(self):
        self._set_state("Ready", C['amber'])
        if self.handler: self.handler._stop_training()
        
    def _set_state(self, text, color):
        self.status_lbl.setText(text)
        self.left_accent.setStyleSheet(f"QFrame {{ background: transparent; border-left: 4px solid {color}; border-top-left-radius: 32px; border-bottom-left-radius: 32px; border-right: none; border-top: none; border-bottom: none; }}")
        self.line.setStyleSheet(f"background: {color}; border-radius: 1px; border: none;")
        self.dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent; border: none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False


class ProcessOverlay(QWidget):
    # Emit progress 0.0-1.0
    progress_changed = pyqtSignal(float)
    cancelled = pyqtSignal()
    """Semi-transparent overlay for long-running processes (Extraction, Labeling)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setMouseTracking(True)
        self.hide()
        
        # Style
        self.setStyleSheet(f"background-color: rgba(11, 14, 26, 220); color: {C['white']};")
        
        self.start_time = 0
        self.last_update = 0
        
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Center container
        self.container = QFrame()
        self.container.setFixedWidth(400)
        self.container.setStyleSheet("background: transparent; border: none;")
        c_layout = QVBoxLayout(self.container)
        c_layout.setSpacing(20)
        
        # Title
        self.title_lbl = QLabel("PROCESS IN PROGRESS")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {C['purple_l']}; letter-spacing: 2px;")
        c_layout.addWidget(self.title_lbl)
        
        # Percent
        self.percent_lbl = QLabel("0%")
        self.percent_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.percent_lbl.setStyleSheet(f"font-size: 48px; font-weight: 800; font-family: '{FONT_UI}';")
        c_layout.addWidget(self.percent_lbl)
        
        # Progress Bar
        self.bar = QProgressBar()
        self.bar.setFixedHeight(8)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet(f"""
            QProgressBar {{ background: {C['bg_input']}; border-radius: 4px; border: none; }}
            QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {C['purple']}, stop:1 {C['violet']}); border-radius: 4px; }}
        """)
        c_layout.addWidget(self.bar)
        
        # Status / Details
        self.status_lbl = QLabel("Initializing...")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet(f"color: {C['text_b']}; font-size: 13px;")
        c_layout.addWidget(self.status_lbl)
        
        # ETA
        self.eta_lbl = QLabel("Calculating time remaining...")
        self.eta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eta_lbl.setStyleSheet(f"color: {C['text_d']}; font-family: '{FONT_MONO}'; font-size: 11px;")
        c_layout.addWidget(self.eta_lbl)
        
        # Log Console
        self.log_widget = QListWidget()
        self.log_widget.setFixedHeight(120)
        self.log_widget.setWordWrap(True)
        self.log_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.log_widget.setStyleSheet(f"""
            QListWidget {{
                background: {C['bg_darkest']}88;
                border: 1px solid {C['border']};
                border-radius: 4px;
                color: {C['text_d']};
                font-family: '{FONT_MONO}';
                font-size: 11px;
                padding: 5px;
            }}
            QListWidget::item {{ margin-bottom: 2px; }}
        """)
        c_layout.addWidget(self.log_widget)
        
        # Cancel Button
        self.cancel_btn = QPushButton("Cancel Operation")
        self.cancel_btn.setFixedSize(140, 32)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_darkest']}88;
                color: {C['red']};
                border: 1px solid {C['red']}44;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
                margin-top: 10px;
            }}
            QPushButton:hover {{
                border-color: {C['red']};
                background: {C['red']}22;
            }}
        """)
        self.cancel_btn.clicked.connect(self.cancelled.emit)
        c_layout.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.container)

    def show_process(self, title):
        self.title_lbl.setText(title.upper())
        self.bar.setValue(0)
        self.percent_lbl.setText("0%")
        self.status_lbl.setText("Initializing...")
        self.eta_lbl.setText("Calculating time remaining...")
        self.log_widget.clear()
        self.add_log(f"Started: {title}")
        
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("Cancel Operation")
        
        self.start_time = time.time()
        self.last_update = self.start_time
        
        # Resize to parent
        if self.parentWidget():
            self.setGeometry(0, 0, self.parentWidget().width(), self.parentWidget().height())
        
        self.show()
        self.raise_()

    def add_log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_widget.addItem(f"[{timestamp}] {msg}")
        self.log_widget.scrollToBottom()

    def update_progress(self, value, status=None):
        """value is 0.0 to 1.0"""
        pct = int(value * 100)
        self.bar.setValue(pct)
        self.percent_lbl.setText(f"{pct}%")
        
        if status:
            self.status_lbl.setText(status)
            
        # Calculate ETA
        elapsed = time.time() - self.start_time
        if value > 0.05 and elapsed > 2: # Wait for some data to stabilize
            total_est = elapsed / value
            remaining = total_est - elapsed
            
            if remaining > 60:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                self.eta_lbl.setText(f"~{mins}m {secs}s remaining")
            else:
                self.eta_lbl.setText(f"~{int(remaining)}s remaining")
        
        # Ensure we cover the parent correctly if it resized
        if self.parentWidget():
            self.setGeometry(0, 0, self.parentWidget().width(), self.parentWidget().height())

    def resizeEvent(self, event):
        if self.parentWidget():
            self.setGeometry(0, 0, self.parentWidget().width(), self.parentWidget().height())
        super().resizeEvent(event)

class RunOverlay(QWidget):
    """Floating draggable overlay for controlling Agent Inference."""
    def __init__(self, model_name="Agent", parent=None):
        super().__init__(None) # Independent window
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(360, 64)
        self._dragging = False
        self._drag_pos = QPoint()
        self.model_name = model_name
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Pill Frame
        self.frame = QFrame()
        self.frame.setFixedHeight(64)
        self.frame.setStyleSheet(f"""
            QFrame {{
                background: #111520;
                border-radius: 32px;
                border: 1px solid #1e2233;
            }}
        """)
        
        fl = QHBoxLayout(self.frame)
        fl.setContentsMargins(0, 0, 16, 0)
        fl.setSpacing(12)
        
        # Left Accent (The curve)
        self.left_accent = QFrame()
        self.left_accent.setFixedSize(24, 64)
        self.left_accent.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border-left: 4px solid {C['amber']};
                border-top-left-radius: 32px;
                border-bottom-left-radius: 32px;
                border-right: none;
                border-top: none;
                border-bottom: none;
            }}
        """)
        fl.addWidget(self.left_accent)
        
        # Line + Dot
        self.line = QFrame()
        self.line.setFixedSize(3, 24)
        self.line.setStyleSheet(f"background: {C['amber']}; border-radius: 1px; border: none;")
        fl.addWidget(self.line)
        
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {C['amber']}; font-size: 10px; background: transparent; border: none;")
        fl.addWidget(self.dot)
        
        # Text
        self.status_lbl = QLabel(f"{self.model_name}")
        self.status_lbl.setMinimumWidth(180)
        self.status_lbl.setStyleSheet(f"color: {C['white']}; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        fl.addWidget(self.status_lbl)
        
        fl.addStretch()
        
        # Buttons
        self.btn_start = QPushButton("▶")
        self.btn_start.setToolTip("Start Inference")
        self.btn_start.setFixedSize(36, 36)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background: #181c2b;
                color: {C['green']};
                border-radius: 18px;
                font-size: 14px;
                border: 1px solid #23283b;
            }}
            QPushButton:hover {{ background: {C['green']}22; border-color: {C['green']}55; }}
        """)
        
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setToolTip("Pause Inference")
        self.btn_pause.setFixedSize(36, 36)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setStyleSheet(f"""
            QPushButton {{
                background: #181c2b;
                color: {C['amber']};
                border-radius: 18px;
                font-size: 14px;
                border: 1px solid #23283b;
            }}
            QPushButton:hover {{ background: {C['amber']}22; border-color: {C['amber']}55; }}
        """)
        
        self.btn_stop = QPushButton("■")
        self.btn_stop.setToolTip("Stop Inference")
        self.btn_stop.setFixedSize(36, 36)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet(f"""
            QPushButton {{
                background: #181c2b;
                color: {C['red']};
                border-radius: 18px;
                font-size: 12px;
                border: 1px solid #23283b;
            }}
            QPushButton:hover {{ background: {C['red']}22; border-color: {C['red']}55; }}
        """)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: #181c2b;
                color: {C['text_d']};
                border-radius: 18px;
                font-size: 14px;
                border: 1px solid #23283b;
            }}
            QPushButton:hover {{ background: {C['red']}22; color: {C['red']}; border-color: {C['red']}55; }}
        """)
        
        self.btn_start.clicked.connect(self._on_start)
        self.btn_pause.clicked.connect(self._on_pause)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_close.clicked.connect(self.hide)
        
        fl.addWidget(self.btn_start)
        fl.addWidget(self.btn_pause)
        fl.addWidget(self.btn_stop)
        fl.addWidget(self.btn_close)
        
        layout.addWidget(self.frame)

    def _on_start(self):
        self._set_state("Running", C['green'])

    def _on_pause(self):
        self._set_state("Paused", C['amber'])

    def _on_stop(self):
        self._set_state("Stopped", C['red'])
        
    def _set_state(self, text, color):
        self.status_lbl.setText(text)
        self.left_accent.setStyleSheet(f"QFrame {{ background: transparent; border-left: 4px solid {color}; border-top-left-radius: 32px; border-bottom-left-radius: 32px; border-right: none; border-top: none; border-bottom: none; }}")
        self.line.setStyleSheet(f"background: {color}; border-radius: 1px; border: none;")
        self.dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent; border: none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False
