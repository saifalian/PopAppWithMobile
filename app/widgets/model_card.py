"""
Model status card widget matching the screenshot.
Shows: colored dot, model name, status, performance bar, attempt count.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame, QCheckBox, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from app.theme import C, FONT_MONO, FONT_UI


class StatusDot(QWidget):
    """Colored animated status dot."""
    def __init__(self, color=C["status_idle"], animate=False, parent=None):
        super().__init__(parent)
        self._color = color
        self._alpha = 255
        self._fade_dir = -1
        self.setFixedSize(10, 10)

        if animate:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._pulse)
            self._timer.start(50)

    def set_color(self, color, animate=False):
        self._color = color
        self.update()

    def _pulse(self):
        self._alpha += self._fade_dir * 8
        if self._alpha <= 80:
            self._fade_dir = 1
        elif self._alpha >= 255:
            self._fade_dir = -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._color)
        color.setAlpha(self._alpha)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 8, 8)


class ModelCard(QWidget):
    """
    Model status card matching the screenshot style.
    Dark card with dot + name, status line, performance bar, attempt count.
    """

    STATUS_COLORS = {
        "trained":   C["status_confident"],
        "confident": C["status_confident"],
        "training":  C["status_training"],
        "untrained": C["status_idle"],
        "error":     C["status_error"],
    }
    STATUS_LABELS = {
        "trained":   "Confident",
        "confident": "Confident",
        "training":  "Training",
        "untrained": "No Data",
        "error":     "Error",
    }
    
    selected_changed = pyqtSignal(bool)
    action_clicked   = pyqtSignal(str, str) # (model_name, action)

    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self._score     = 0.0
        self._attempts  = 0
        self._status    = "untrained"
        self.setObjectName("model_card")
        self.setMinimumWidth(300)
        self.setMinimumHeight(220)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(4)

        # ── Header row ───────────────────────────────────────────
        header = QHBoxLayout()
        
        # Checkbox for selection
        self.check = QCheckBox()
        self.check.setFixedSize(20, 20)
        self.check.stateChanged.connect(lambda state: self.selected_changed.emit(state == 2))
        header.addWidget(self.check)
        header.addSpacing(4)

        self.dot = StatusDot(C["status_idle"])
        header.addWidget(self.dot)
        header.addSpacing(6)
        
        self.name_label = QLabel(self.model_name)
        self.name_label.setFont(QFont(FONT_MONO, 12, QFont.Weight.Bold))
        self.name_label.setStyleSheet(f"color: {C['white']};")
        header.addWidget(self.name_label)
        header.addStretch()

        # Action buttons (Pause, Stop)
        self.btn_pause = QPushButton("⏯")
        self.btn_pause.setFixedSize(32, 32)
        self.btn_pause.setToolTip("Pause/Resume")
        self.btn_pause.setObjectName("model_action_btn")
        self.btn_pause.clicked.connect(lambda: self.action_clicked.emit(self.model_name, "pause"))
        header.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setFixedSize(32, 32)
        self.btn_stop.setToolTip("Stop")
        self.btn_stop.setObjectName("model_action_btn_danger")
        self.btn_stop.clicked.connect(lambda: self.action_clicked.emit(self.model_name, "stop"))
        header.addWidget(self.btn_stop)

        layout.addLayout(header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C['border']};")
        layout.addWidget(sep)

        # ── Status ───────────────────────────────────────────────
        status_row = QHBoxLayout()
        self.status_key = QLabel("Status:")
        self.status_key.setStyleSheet(f"color: {C['text_d']}; font-size: 12px;")
        self.status_val = QLabel("No Data")
        self.status_val.setStyleSheet(f"color: {C['status_idle']}; font-size: 12px; font-weight: 600;")
        status_row.addWidget(self.status_key)
        status_row.addSpacing(4)
        status_row.addWidget(self.status_val)
        status_row.addStretch()
        layout.addLayout(status_row)

        # ── Performance ──────────────────────────────────────────
        perf_row = QHBoxLayout()
        self.perf_label = QLabel("Performance: —")
        self.perf_label.setStyleSheet(f"color: {C['text_b']}; font-size: 13px; font-weight: 700;")
        perf_row.addWidget(self.perf_label)
        perf_row.addStretch()
        layout.addLayout(perf_row)

        # Progress bar
        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setValue(0)
        self.prog.setFixedHeight(4)
        self.prog.setTextVisible(False)
        layout.addWidget(self.prog)

        # ── Sparkline Placeholder ───────────────────────────
        self.sparkline = QFrame()
        self.sparkline.setFixedHeight(60)
        self.sparkline.setStyleSheet(f"background: {C['bg_darkest']}; border-radius: 4px; border: 1px solid {C['border']}44;")
        sl_layout = QVBoxLayout(self.sparkline)
        sl_lbl = QLabel("Performance History")
        sl_lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 10px;")
        sl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl_layout.addWidget(sl_lbl)
        layout.addWidget(self.sparkline)

        # ── Last run row ─────────────────────────────────────────
        self.last_run_lbl = QLabel("No past runs recorded")
        self.last_run_lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 11px;")
        layout.addWidget(self.last_run_lbl)

        # ── Drift row ────────────────────────────────────────────
        self.drift_row = QHBoxLayout()
        self.drift_dot = QLabel("●")
        self.drift_dot.setStyleSheet(f"color: {C['text_d']}; font-size: 12px;") # Gray dot initially
        self.drift_lbl = QLabel("Health Status: Unknown")
        self.drift_lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 11px;")
        self.drift_row.addWidget(self.drift_dot)
        self.drift_row.addWidget(self.drift_lbl)
        self.drift_row.addStretch()
        layout.addLayout(self.drift_row)

        # ── Attempt count ────────────────────────────────────────
        self.attempt_label = QLabel("Attempt: 0 / ∞")
        self.attempt_label.setStyleSheet(f"color: {C['text_d']}; font-size: 11px;")
        layout.addWidget(self.attempt_label)

    def update_status(self, status: str, score: float, attempts: int):
        """Update all displayed values."""
        self._status   = status
        self._score    = score
        self._attempts = attempts

        color = self.STATUS_COLORS.get(status, C["status_idle"])
        label = self.STATUS_LABELS.get(status, status.title())

        self.dot.set_color(color, animate=(status == "training"))
        self.status_val.setText(label)
        self.status_val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        self.perf_label.setText(f"Performance: {score:.0f}%" if score > 0 else "Performance: —")
        self.prog.setValue(int(score))
        self.prog.setStyleSheet(f"""
            QProgressBar {{ background: {C['border']}; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}
        """)
        self.attempt_label.setText(f"Attempt: {attempts:,} / ∞")

    def is_selected(self) -> bool:
        return self.check.isChecked()

    def set_selected(self, selected: bool):
        self.check.setChecked(selected)
