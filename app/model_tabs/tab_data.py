from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QSpinBox, QDoubleSpinBox, QCheckBox
)
from app.theme import C

class TabData(QWidget):
    def __init__(self, model_record, parent=None):
        super().__init__(parent)
        self.model_record = model_record
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Screen Region
        grp_region = QGroupBox("Screen Region to Capture")
        grp_region.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        rl = QVBoxLayout(grp_region)
        self.btn_picker = QPushButton("Launch Region Picker Overlay")
        self.btn_picker.setStyleSheet(f"background: {C['bg_card']}; color: {C['purple']}; padding: 8px; border: 1px solid {C['purple']};")
        rl.addWidget(self.btn_picker)
        self.lbl_region = QLabel("Current Region: (None)")
        rl.addWidget(self.lbl_region)
        layout.addWidget(grp_region)
        
        # Extraction Logic
        grp_ext = QGroupBox("Extraction Logic")
        grp_ext.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        el = QVBoxLayout(grp_ext)
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Extract 1 frame every"))
        self.sp_extract = QSpinBox()
        self.sp_extract.setRange(1, 100)
        self.sp_extract.setValue(5)
        hbox.addWidget(self.sp_extract)
        hbox.addWidget(QLabel("frames"))
        hbox.addStretch()
        el.addLayout(hbox)
        layout.addWidget(grp_ext)

        # Augmentation
        grp_aug = QGroupBox("Training Augmentation")
        grp_aug.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        al = QVBoxLayout(grp_aug)
        self.chk_brightness = QCheckBox("Random Brightness")
        self.chk_color = QCheckBox("Color Jitter")
        self.chk_zoom = QCheckBox("Random Zoom")
        self.chk_flip = QCheckBox("Horizontal Flip")
        
        self.chk_brightness.setChecked(True)
        self.chk_color.setChecked(True)
        self.chk_zoom.setChecked(True)
        self.chk_flip.setChecked(True)
        
        al.addWidget(self.chk_brightness)
        al.addWidget(self.chk_color)
        al.addWidget(self.chk_zoom)
        al.addWidget(self.chk_flip)
        layout.addWidget(grp_aug)

        layout.addStretch()
