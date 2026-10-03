from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QComboBox, QTableWidget, QTableWidgetItem
)
from app.theme import C

class TabResults(QWidget):
    def __init__(self, model_record, parent=None):
        super().__init__(parent)
        self.model_record = model_record
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Exports
        grp_exp = QGroupBox("Export Standalone Agent")
        grp_exp.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        el = QVBoxLayout(grp_exp)
        
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Format:"))
        self.cmb_fmt = QComboBox()
        self.cmb_fmt.addItems(["TensorFlow SavedModel (.tf)", ".keras", "TFLite", "ONNX"])
        h1.addWidget(self.cmb_fmt)
        
        self.btn_exp = QPushButton("Export Now")
        self.btn_exp.setStyleSheet(f"background: {C['violet']}; color: white; padding: 6px 15px; font-weight: bold;")
        h1.addWidget(self.btn_exp)
        h1.addStretch()
        el.addLayout(h1)
        layout.addWidget(grp_exp)

        # Versions
        grp_v = QGroupBox("Model Versions")
        grp_v.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        vl = QVBoxLayout(grp_v)
        
        self.table = QTableWidget(1, 4)
        self.table.setHorizontalHeaderLabels(["Version", "Attempts", "Best Score", "Status"])
        self.table.setItem(0, 0, QTableWidgetItem("v1 (Current)"))
        self.table.setItem(0, 1, QTableWidgetItem("0"))
        self.table.setItem(0, 2, QTableWidgetItem("0.0"))
        self.table.setItem(0, 3, QTableWidgetItem("Untrained"))
        self.table.setStyleSheet(f"background: {C['bg_card']}; color: {C['white']}; border: 1px solid {C['border']};")
        vl.addWidget(self.table)
        layout.addWidget(grp_v)

        # Test Set Evaluation
        grp_eval = QGroupBox("Locked Test Set Analysis")
        grp_eval.setStyleSheet(f"color: {C['white']}; font-weight: bold; border-left: 3px solid {C['purple']};")
        evl = QVBoxLayout(grp_eval)
        evl.addWidget(QLabel("Run an honest performance check against the 5% held-out data (never seen by model)."))
        
        self.btn_eval = QPushButton("🔍 RUN TEST EVALUATION (Locked Set)")
        self.btn_eval.setStyleSheet(f"background: {C['bg_sidebar']}; color: {C['white']}; border: 1px solid {C['purple']}; padding: 8px; font-weight: bold;")
        self.btn_eval.setCursor(Qt.CursorShape.PointingHandCursor)
        evl.addWidget(self.btn_eval)
        
        self.lbl_eval_res = QLabel("Last Test Accuracy: --")
        self.lbl_eval_res.setStyleSheet(f"color: {C['text_d']}; font-style: italic;")
        evl.addWidget(self.lbl_eval_res)
        
        layout.addWidget(grp_eval)
        
        # Drift Monitor
        grp_drift = QGroupBox("Post-Deployment Drift Monitor")
        grp_drift.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        dl = QVBoxLayout(grp_drift)
        self.lbl_drift = QLabel("Baseline Confidence: Not Established\nCurrent Confidence: N/A\nStatus: Healthy")
        dl.addWidget(self.lbl_drift)
        self.btn_res = QPushButton("Reset Baseline")
        self.btn_res.setStyleSheet(f"color: {C['text']}; border: 1px solid {C['border']};")
        dl.addWidget(self.btn_res)
        layout.addWidget(grp_drift)

        layout.addStretch()
