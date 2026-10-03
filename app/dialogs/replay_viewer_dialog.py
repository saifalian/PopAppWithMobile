import os
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage

from app.theme import C, FONT_UI


class ReplayViewerDialog(QDialog):
    def __init__(self, model_name: str, attempt_number: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Replay Viewer - Attempt #{attempt_number}")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(f"background: {C['bg_card']}; color: {C['white']};")
        
        self.model_name = model_name
        self.attempt_number = attempt_number
        self.frames = []
        self.comp_frames = [] # Frames for comparison pane
        self.total_frames = 0
        self.current_frame = 0
        self.is_dual_mode = False
        self.playing = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._next_frame)
        self.timer.setInterval(100) # 10fps
        
        self._load_data()
        self._build_ui()
        self._show_frame()

    def _load_data(self):
        # Stub data loading for the UI demonstration
        attempt_dir = Path("models") / self.model_name / "attempts" / f"{self.attempt_number:04d}"
        if attempt_dir.exists():
            self.frames = sorted(list(attempt_dir.glob("*.png")))
            self.total_frames = len(self.frames)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # DISPLAY
        self.image_label = QLabel("No Replay Data Found" if not self.frames else "Loading...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']};")
        
        self.image_label_comp = QLabel("Comparison Mode Off")
        self.image_label_comp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label_comp.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']};")
        self.image_label_comp.hide()

        self.img_layout = QHBoxLayout()
        self.img_layout.addWidget(self.image_label)
        self.img_layout.addWidget(self.image_label_comp)
        layout.addLayout(self.img_layout, stretch=1)
        
        # CONTROLS
        controls = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setStyleSheet(f"background: {C['violet']}; color: white; padding: 5px 15px; border-radius: 4px;")
        self.btn_play.clicked.connect(self._toggle_play)
        controls.addWidget(self.btn_play)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(max(0, self.total_frames - 1))
        self.slider.sliderMoved.connect(self._slider_moved)
        controls.addWidget(self.slider)
        
        self.lbl_frame = QLabel("0 / 0")
        controls.addWidget(self.lbl_frame)
        
        self.btn_compare = QPushButton("👯 Add Comparison")
        self.btn_compare.setStyleSheet(f"color: {C['text']}; border: 1px solid {C['border']}; padding: 5px;")
        self.btn_compare.clicked.connect(self._on_add_comparison)
        controls.addWidget(self.btn_compare)
        
        layout.addLayout(controls)

    def _toggle_play(self):
        if not self.frames: return
        self.playing = not self.playing
        if self.playing:
            self.btn_play.setText("⏸ Pause")
            self.timer.start()
        else:
            self.btn_play.setText("▶ Play")
            self.timer.stop()

    def _next_frame(self):
        if self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self.slider.setValue(self.current_frame)
            self._show_frame()
        else:
            self._toggle_play()

    def _slider_moved(self, val):
        self.current_frame = val
        self._show_frame()

    def _show_frame(self):
        self.lbl_frame.setText(f"{self.current_frame + 1} / {max(1, self.total_frames)}")
        if self.frames and self.current_frame < len(self.frames):
            pix = QPixmap(str(self.frames[self.current_frame]))
            w = self.image_label.width()
            h = self.image_label.height()
            self.image_label.setPixmap(pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        if self.is_dual_mode and self.comp_frames:
            idx = min(self.current_frame, len(self.comp_frames) - 1)
            pix = QPixmap(str(self.comp_frames[idx]))
            w = self.image_label_comp.width()
            h = self.image_label_comp.height()
            self.image_label_comp.setPixmap(pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _on_add_comparison(self):
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        path = QFileDialog.getExistingDirectory(self, "Select Attempt Folder for Comparison", str(Path("models") / self.model_name / "attempts"))
        if path:
            self.comp_frames = sorted(list(Path(path).glob("*.png")))
            if self.comp_frames:
                self.is_dual_mode = True
                self.image_label_comp.show()
                self._show_frame()
                self.btn_compare.setText("❌ Remove Comparison")
                self.btn_compare.clicked.disconnect()
                self.btn_compare.clicked.connect(self._remove_comparison)

    def _remove_comparison(self):
        self.is_dual_mode = False
        self.comp_frames = []
        self.image_label_comp.hide()
        self.btn_compare.setText("👯 Add Comparison")
        self.btn_compare.clicked.disconnect()
        self.btn_compare.clicked.connect(self._on_add_comparison)
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._show_frame()
