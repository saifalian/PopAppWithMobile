from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QComboBox, QSpinBox
)
from app.theme import C
from app.dialogs.label_tool_dialog import LabelToolDialog

class TabLabel(QWidget):
    def __init__(self, model_record, parent=None):
        super().__init__(parent)
        self.model_record = model_record
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Manual Label Tool
        grp_tool = QGroupBox("Manual Labeling")
        grp_tool.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        tl = QVBoxLayout(grp_tool)
        self.open_btn = QPushButton("🚀 Open 10/10 Smart Label Tool")
        self.open_btn.setStyleSheet(f"background: {C['violet']}; color: white; padding: 12px; font-weight: bold; border-radius: 6px;")
        tl.addWidget(self.open_btn)
        layout.addWidget(grp_tool)

        # Auto Labeling
        grp_auto = QGroupBox("Auto-Labeling Rules")
        grp_auto.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        al = QVBoxLayout(grp_auto)
        
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Detection Method:"))
        self.cmb_method = QComboBox()
        self.cmb_method.addItems(["Pixel Delta (Visual changes)", "Click Sound (Audio cues)"])
        h1.addWidget(self.cmb_method)
        h1.addStretch()
        al.addLayout(h1)
        
        self.run_auto_btn = QPushButton("Run Auto-Labeler")
        self.run_auto_btn.setStyleSheet(f"background: {C['bg_darkest']}; padding: 8px; border: 1px solid {C['border']};")
        al.addWidget(self.run_auto_btn)
        layout.addWidget(grp_auto)

        # Split Config
        grp_split = QGroupBox("Dataset Split (Lock 5% for testing)")
        grp_split.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        sl = QHBoxLayout(grp_split)
        
        for k, v in [("Train", 80), ("Val", 15), ("Test", 5)]:
            sl.addWidget(QLabel(k))
            sp = QSpinBox()
            sp.setRange(0, 100)
            sp.setValue(v)
            sl.addWidget(sp)
            sl.addSpacing(20)
            
        sl.addStretch()
        layout.addWidget(grp_split)

        layout.addStretch()

    def _open_tool(self):
        # This will now be handled by ModelScreen
        pass
