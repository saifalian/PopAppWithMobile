"""
Label Tool Dialog.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from app.theme import C
from backend.data.label_manager import LabelManager
from pathlib import Path


class LabelToolDialog(QDialog):
    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self.setWindowTitle("Label Tool")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(f"background: {C['bg_card']}; color: {C['white']};")
        
        self.label_manager = LabelManager(model_name)
        
        extracted_dir = Path("models") / model_name / "extracted"
        self.frames = sorted(list(extracted_dir.glob("*.png")) + list(extracted_dir.glob("*.jpg")))
        self.current_idx = 0
        
        self.class_defs = [
            ("C", "click"),
            ("S", "scroll"),
            ("Z", "zoom"),
            ("N", "no_action"),
            ("P", "popup_detected"),
            ("X", "error_state")
        ]
        
        self._build_ui()
        self._show_frame()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        
        # LEFT: IMAGE
        left = QVBoxLayout()
        self.img_lbl = QLabel("No frames to label")
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']};")
        left.addWidget(self.img_lbl, stretch=1)
        
        self.status = QLabel("0 / 0 | Current Label: None")
        left.addWidget(self.status)
        layout.addLayout(left, stretch=3)
        
        # RIGHT: SIDEBAR
        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Keyboard Shortcuts</b>"))
        
        for key, name in self.class_defs:
            btn = QPushButton(f"[{key}] {name}")
            btn.setStyleSheet(f"background: {C['bg_panel']}; color: white; padding: 10px; border: 1px solid {C['border']}; text-align: left;")
            btn.clicked.connect(lambda _, k=key, n=name: self._apply_label(n))
            right.addWidget(btn)
            
        right.addStretch()
        
        nav = QHBoxLayout()
        btn_prev = QPushButton("◀ Prev")
        btn_prev.clicked.connect(self._prev)
        btn_next = QPushButton("Next ▶")
        btn_next.clicked.connect(self._next)
        nav.addWidget(btn_prev)
        nav.addWidget(btn_next)
        right.addLayout(nav)
        
        btn_save = QPushButton("Save & Exit")
        btn_save.setStyleSheet(f"background: {C['violet']}; color: white; padding: 10px; font-weight: bold;")
        btn_save.clicked.connect(self.accept)
        right.addWidget(btn_save)
        
        layout.addLayout(right, stretch=1)

    def _apply_label(self, label_name: str):
        if not self.frames: return
        frame_name = self.frames[self.current_idx].name
        self.label_manager.add_label(frame_name, label_name, 1.0)
        self._next()

    def _prev(self):
        if self.frames and self.current_idx > 0:
            self.current_idx -= 1
            self._show_frame()

    def _next(self):
        if self.frames and self.current_idx < len(self.frames) - 1:
            self.current_idx += 1
            self._show_frame()
            
    def _show_frame(self):
        if not self.frames: return
        p = self.frames[self.current_idx]
        
        frame_name = p.name
        existing = self.label_manager.labels.get(frame_name, {})
        curr_label = existing.get("label", "None")
        
        self.status.setText(f"{self.current_idx + 1} / {len(self.frames)} | Current Label: {curr_label}")
        
        pix = QPixmap(str(p))
        self.img_lbl.setPixmap(pix.scaled(
            self.img_lbl.width(), self.img_lbl.height(), 
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))

    def keyPressEvent(self, event):
        key_str = event.text().upper()
        for k, name in self.class_defs:
            if key_str == k:
                self._apply_label(name)
                return
        
        if event.key() == Qt.Key.Key_Left:
            self._prev()
        elif event.key() == Qt.Key.Key_Right:
            self._next()
        else:
            super().keyPressEvent(event)
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._show_frame()
