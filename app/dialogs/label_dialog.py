"""
Label Dialog.
A professional tool to review extracted frames and assign labels manually.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QProgressBar, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QKeyEvent
import cv2
import numpy as np
from pathlib import Path

from app.theme import C, FONT_UI, FONT_MONO

class LabelDialog(QDialog):
    labels_updated = pyqtSignal()

    def __init__(self, model_name, label_manager, parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self.lm = label_manager
        self.frames = self.lm.get_all_frame_names()
        self.current_idx = 0
        self._loading_frame_flag = False
        
        self.setWindowTitle(f"Label Tool - {model_name}")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(f"background-color: {C['bg_darkest']}; color: {C['text_b']};")
        
        self._init_ui()
        if not self.frames:
            QMessageBox.warning(self, "No Data", f"No extracted frames found for '{model_name}'. Please run 'Extract All Frames' first.")
            # We don't close here, we'll show empty state, and user can escape
            self._load_frame()
        else:
            self._load_frame()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ── HEADER ───────────────────────────────────────────────
        header = QHBoxLayout()
        self.title_lbl = QLabel("Manual Review")
        self.title_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {C['white']};")
        header.addWidget(self.title_lbl)
        header.addStretch()
        self.progress_lbl = QLabel("0 / 0")
        self.progress_lbl.setStyleSheet(f"color: {C['text_d']}; font-family: '{FONT_MONO}';")
        header.addWidget(self.progress_lbl)
        main_layout.addLayout(header)

        # ── VIEWPORT ─────────────────────────────────────────────
        self.view_frame = QFrame()
        self.view_frame.setStyleSheet(f"background: {C['bg_input']}; border: 1px solid {C['border']}; border-radius: 8px;")
        view_layout = QVBoxLayout(self.view_frame)
        self.img_lbl = QLabel("Loading frame...")
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_layout.addWidget(self.img_lbl)
        main_layout.addWidget(self.view_frame, stretch=1)

        # ── INFO BAR ─────────────────────────────────────────────
        info_bar = QHBoxLayout()
        self.fname_lbl = QLabel("frame_0000.png")
        self.fname_lbl.setStyleSheet(f"color: {C['cyan']}; font-family: '{FONT_MONO}'; font-weight: bold;")
        info_bar.addWidget(self.fname_lbl)
        
        info_bar.addSpacing(20)
        self.status_lbl = QLabel("Status: Unlabeled")
        self.status_lbl.setStyleSheet(f"color: {C['text_d']};")
        info_bar.addWidget(self.status_lbl)
        
        info_bar.addStretch()
        main_layout.addLayout(info_bar)

        # ── CONTROLS ─────────────────────────────────────────────
        ctrl_layout = QHBoxLayout()
        
        # Navigation
        prev_btn = QPushButton("← Previous")
        prev_btn.setFixedSize(120, 40)
        prev_btn.clicked.connect(self._prev_frame)
        ctrl_layout.addWidget(prev_btn)
        
        # Label Buttons
        self.btn_click = QPushButton("[1] Click")
        self.btn_click.setFixedSize(140, 40)
        self.btn_click.setStyleSheet(f"background: {C['purple']}; color: white; font-weight: bold;")
        self.btn_click.clicked.connect(lambda: self._set_label("click"))
        ctrl_layout.addWidget(self.btn_click)
        
        self.btn_no_action = QPushButton("[2] No Action")
        self.btn_no_action.setFixedSize(140, 40)
        self.btn_no_action.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border_b']};")
        self.btn_no_action.clicked.connect(lambda: self._set_label("no_action"))
        ctrl_layout.addWidget(self.btn_no_action)
        
        self.btn_delete = QPushButton("[Del] Clear")
        self.btn_delete.setFixedSize(100, 40)
        self.btn_delete.setStyleSheet(f"color: {C['red']}; border: 1px solid {C['red']}44;")
        self.btn_delete.clicked.connect(self._clear_label)
        ctrl_layout.addWidget(self.btn_delete)
        
        next_btn = QPushButton("Next →")
        next_btn.setFixedSize(120, 40)
        next_btn.clicked.connect(self._next_frame)
        ctrl_layout.addWidget(next_btn)
        
        main_layout.addLayout(ctrl_layout)

        # ── KEYBOARD HINT ────────────────────────────────────────
        hint = QLabel("Use [1], [2], [Space/Right], [Left], or [Delete] keys")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color: {C['text_d']}; font-size: 11px;")
        main_layout.addWidget(hint)

    def _load_frame(self):
        if self._loading_frame_flag:
            return
        self._loading_frame_flag = True

        try:
            if not self.frames or self.current_idx >= len(self.frames):
                self.img_lbl.setText("No frames found in extracted/ directory.")
                self.fname_lbl.setText("—")
                self.status_lbl.setText("Status: N/A")
                return

            fname = self.frames[self.current_idx]
            self.fname_lbl.setText(fname)
            self.progress_lbl.setText(f"{self.current_idx + 1} / {len(self.frames)}")

            # Load image
            img_np = self.lm.get_frame_image(fname)
            if img_np is not None:
                # Convert BGR to RGB
                img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
                h, w, c = img_rgb.shape
                
                # Create a local copy of data to ensure it stays alive for QImage
                # Though QPixmap.fromImage(qimg.copy()) should already handle this.
                bytes_per_line = c * w
                qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                
                # We copy the QImage to a separate object before converting to Pixmap
                # to be extremely safe about the underlying buffer.
                pixmap = QPixmap.fromImage(qimg.copy())
                
                if not pixmap.isNull():
                    # Scale to viewport while keeping aspect ratio
                    scaled = pixmap.scaled(
                        self.img_lbl.size(), 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.img_lbl.setPixmap(scaled)
                else:
                    self.img_lbl.setText(f"Error: Pixmap is null for {fname}")
            else:
                self.img_lbl.setText(f"Error: Could not load {fname}")
            
            # Load label status
            label_entry = self.lm.get_label(fname)
            if label_entry:
                lbl = label_entry.get("label", "unknown")
                conf = label_entry.get("confidence", 1.0)
                src = label_entry.get("source", "manual")
                self.status_lbl.setText(f"Status: <font color='{C['white']}'>{lbl.upper()}</font> ({src}, {conf:.1%})")
            else:
                self.status_lbl.setText("Status: <font color='#ef4444'>Unlabeled</font>")
        except Exception as e:
            self.img_lbl.setText(f"Load Error: {str(e)}")
            print(f"DEBUG: Frame load error: {e}")
        finally:
            self._loading_frame_flag = False

    def _next_frame(self):
        if self.current_idx < len(self.frames) - 1:
            self.current_idx += 1
            self._load_frame()

    def _prev_frame(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._load_frame()

    def _set_label(self, label):
        if not self.frames: return
        fname = self.frames[self.current_idx]
        self.lm.set_label(fname, label, source="manual")
        self.lm.save()
        self.labels_updated.emit()
        self._next_frame()

    def _clear_label(self):
        if not self.frames: return
        fname = self.frames[self.current_idx]
        self.lm.delete_label(fname)
        self.lm.save()
        self.labels_updated.emit()
        self._load_frame()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_1:
            self._set_label("click")
        elif event.key() == Qt.Key.Key_2:
            self._set_label("no_action")
        elif event.key() == Qt.Key.Key_Right or event.key() == Qt.Key.Key_Space:
            self._next_frame()
        elif event.key() == Qt.Key.Key_Left:
            self._prev_frame()
        elif event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self._clear_label()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._load_frame()
