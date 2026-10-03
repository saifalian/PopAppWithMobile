from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QDoubleSpinBox
)
from app.theme import C

class TabActions(QWidget):
    def __init__(self, model_record, parent=None):
        super().__init__(parent)
        self.model_record = model_record
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Sequence Recorder
        grp_rec = QGroupBox("Live Action Recorder")
        grp_rec.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        rl = QVBoxLayout(grp_rec)
        self.btn_rec = QPushButton("Start Recording (F9 to Stop)")
        self.btn_rec.setStyleSheet(f"background: {C['red']}; color: white; padding: 10px; font-weight: bold;")
        rl.addWidget(self.btn_rec)
        layout.addWidget(grp_rec)

        # Humanization
        grp_hum = QGroupBox("Humanization Variance")
        grp_hum.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        hl = QVBoxLayout(grp_hum)
        
        v1 = QHBoxLayout()
        v1.addWidget(QLabel("Mouse Speed Variance:"))
        sp1 = QDoubleSpinBox(); sp1.setRange(0.0, 1.0); sp1.setSingleStep(0.1); sp1.setValue(0.2)
        v1.addWidget(sp1); v1.addStretch()
        hl.addLayout(v1)

        v2 = QHBoxLayout()
        v2.addWidget(QLabel("Landing Offset (px):"))
        sp2 = QDoubleSpinBox(); sp2.setRange(0.0, 50.0); sp2.setValue(3.0)
        v2.addWidget(sp2); v2.addStretch()
        hl.addLayout(v2)
        
        layout.addWidget(grp_hum)

        # Static Actions
        grp_stat = QGroupBox("Static Cleanup Actions")
        grp_stat.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        sl = QVBoxLayout(grp_stat)
        self.btn_stat = QPushButton("Add Always-Run Action")
        self.btn_stat.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; padding: 8px;")
        sl.addWidget(self.btn_stat)
        
        layout.addWidget(grp_stat)
        layout.addStretch()
