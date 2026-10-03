from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QCheckBox, QComboBox, QDoubleSpinBox, QFrame
)
from app.theme import C

class TabReset(QWidget):
    def __init__(self, model_record, parent=None):
        super().__init__(parent)
        self.model_record = model_record
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        desc = QLabel("3-Layer Recovery System. Runs before every training attempt.")
        desc.setStyleSheet(f"color: {C['text']}; font-style: italic;")
        layout.addWidget(desc)
        
        # Layer 1
        grp_l1 = QGroupBox("Layer 1: Master Reset (Recorded Sequence)")
        grp_l1.setStyleSheet(f"color: {C['white']}; font-weight: bold; border-left: 3px solid {C['purple']};")
        l1 = QVBoxLayout(grp_l1)
        self.cmb_seq = QComboBox()
        self.cmb_seq.addItems(["(No sequence selected)", "Macro: Clear Charts and Refresh", "Macro: Go to Homepage"])
        l1.addWidget(self.cmb_seq)
        layout.addWidget(grp_l1)

        # Layer 2
        grp_l2 = QGroupBox("Layer 2: Verify (OpenCV Checks)")
        grp_l2.setStyleSheet(f"color: {C['white']}; font-weight: bold; border-left: 3px solid #3b82f6;")
        l2 = QVBoxLayout(grp_l2)
        self.chk_popup = QCheckBox("No popup visible")
        self.chk_heat = QCheckBox("Heatmap data present")
        self.chk_zoom = QCheckBox("Not over-zoomed")
        self.chk_win = QCheckBox("Window focused")
        
        for c in [self.chk_popup, self.chk_heat, self.chk_zoom, self.chk_win]:
            c.setChecked(True)
            l2.addWidget(c)
            
        layout.addWidget(grp_l2)

        # Layer 3
        grp_l3 = QGroupBox("Layer 3: Confirm (Goal Matching)")
        grp_l3.setStyleSheet(f"color: {C['white']}; font-weight: bold; border-left: 3px solid #10b981;")
        l3 = QVBoxLayout(grp_l3)
        
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Screenshot Similarity Threshold:"))
        self.sp_sim = QDoubleSpinBox()
        self.sp_sim.setRange(0.0, 1.0)
        self.sp_sim.setSingleStep(0.05)
        self.sp_sim.setValue(0.75)
        h1.addWidget(self.sp_sim)
        h1.addStretch()
        l3.addLayout(h1)
        
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("On Fail Behavior:"))
        self.cmb_fail = QComboBox()
        self.cmb_fail.addItems(["Retry 3x then Skip", "Skip Immediately", "Pause Training"])
        h2.addWidget(self.cmb_fail)
        h2.addStretch()
        l3.addLayout(h2)
        
        layout.addWidget(grp_l3)

        layout.addStretch()
