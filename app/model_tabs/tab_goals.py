from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QComboBox, QDoubleSpinBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from app.theme import C

class TabGoals(QWidget):
    def __init__(self, model_record, parent=None):
        super().__init__(parent)
        self.model_record = model_record
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        h1 = QHBoxLayout()
        self.btn_add = QPushButton("+ Add Goal Image")
        self.btn_add.setStyleSheet(f"background: {C['violet']}; color: white; padding: 10px; font-weight: bold;")
        h1.addWidget(self.btn_add)
        
        self.btn_test = QPushButton("Test Current Screen")
        self.btn_test.setStyleSheet(f"background: {C['bg_card']}; color: {C['purple']}; border: 1px solid {C['purple']}; padding: 10px;")
        h1.addWidget(self.btn_test)
        h1.addStretch()
        layout.addLayout(h1)
        
        grp_metric = QGroupBox("Goal Evaluation Metric")
        grp_metric.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        ml = QHBoxLayout(grp_metric)
        ml.addWidget(QLabel("Algorithm:"))
        self.cmb_alg = QComboBox()
        self.cmb_alg.addItems(["SSIM (Structural Similarity)", "Normalized Cross-Correlation", "MSE"])
        ml.addWidget(self.cmb_alg)
        ml.addStretch()
        layout.addWidget(grp_metric)
        
        # Grid of current goals
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']};")
        
        content = QWidget()
        cl = QVBoxLayout(content)
        lbl_empty = QLabel("No Goal Images Registered.")
        lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_empty.setStyleSheet(f"color: {C['text']}; padding: 30px;")
        cl.addWidget(lbl_empty)
        cl.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)
