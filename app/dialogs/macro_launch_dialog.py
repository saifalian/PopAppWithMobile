"""
Pre-flight dialog shown before launching a macro.
Allows the user to override global pipeline variables (like Pair and Timeframe).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFormLayout, QCheckBox,
    QMessageBox
)
from PyQt6.QtCore import Qt

class MacroLaunchDialog(QDialog):
    def __init__(self, macro_data: dict, parent=None):
        super().__init__(parent)
        self.macro_data = macro_data
        self.launch_vars = {}
        
        self.setWindowTitle("Launch Macro")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background: var(--bg-base);
                color: var(--text-primary);
            }
            QLabel { color: var(--text-primary); }
            QLineEdit, QCheckBox { 
                background: var(--bg-surface); 
                color: var(--text-primary);
                border: 1px solid var(--border);
                padding: 4px;
                border-radius: 4px;
            }
            QPushButton {
                background: var(--bg-surface-elevated);
                color: var(--text-primary);
                border: 1px solid var(--border);
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: var(--primary);
                color: white;
            }
        """)
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        lbl_title = QLabel(f"Configure Launch: {self.macro_data.get('name', 'Macro')}")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(lbl_title)
        
        desc = self.macro_data.get('description', '')
        if desc:
            lbl_desc = QLabel(desc)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("color: var(--text-secondary); margin-bottom: 10px;")
            layout.addWidget(lbl_desc)

        # Variables Form
        self.form_layout = QFormLayout()
        
        self.input_pair = QLineEdit("BTCUSDT")
        self.input_tf = QLineEdit("15m")
        self.chk_humanize = QCheckBox("Humanize Mouse Movements")
        self.chk_humanize.setChecked(True)
        self.chk_dry_run = QCheckBox("Dry Run (Simulate only)")
        
        self.form_layout.addRow("Trading Pair:", self.input_pair)
        self.form_layout.addRow("Timeframe:", self.input_tf)
        self.form_layout.addRow("", self.chk_humanize)
        self.form_layout.addRow("", self.chk_dry_run)
        
        layout.addLayout(self.form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_launch = QPushButton("Launch Pipeline")
        btn_launch.setStyleSheet("""
            QPushButton {
                background: var(--primary);
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: var(--primary-hover);
            }
        """)
        btn_launch.clicked.connect(self.accept_launch)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_launch)
        
        layout.addLayout(btn_layout)

    def accept_launch(self):
        # Validate logic (could check models here)
        pair = self.input_pair.text().strip()
        tf = self.input_tf.text().strip()
        
        if not pair:
            QMessageBox.warning(self, "Validation", "Trading Pair is required.")
            return
            
        self.launch_vars = {
            "pipeline.pair": pair,
            "pipeline.timeframe": tf,
            "pipeline.humanize": self.chk_humanize.isChecked(),
            "dry_run": self.chk_dry_run.isChecked() # passed to worker
        }
        self.accept()

    def get_variables(self) -> dict:
        return self.launch_vars
