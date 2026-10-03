from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox
)
from app.theme import C

class TabTrain(QWidget):
    def __init__(self, model_record, parent=None):
        super().__init__(parent)
        self.model_record = model_record
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Training Mode
        grp_mode = QGroupBox("Training Mode & Architecture")
        grp_mode.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        ml = QVBoxLayout(grp_mode)
        
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Mode:"))
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["Self-Improving Loop", "Single Pass (Supervised)", "Fine-tune Existing"])
        h1.addWidget(self.cmb_mode)
        
        h1.addWidget(QLabel("Base Model:"))
        self.cmb_base = QComboBox()
        self.cmb_base.addItems(["MobileNetV2", "EfficientNetB0", "ResNet50"])
        h1.addWidget(self.cmb_base)
        h1.addStretch()
        ml.addLayout(h1)
        layout.addWidget(grp_mode)

        # Stop Conditions
        grp_stop = QGroupBox("Stop Conditions")
        grp_stop.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        sl = QVBoxLayout(grp_stop)
        
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Stop when: "))
        self.cmb_stop = QComboBox()
        self.cmb_stop.addItems(["Manual stop by user", "Target score reached", "Attempt count reached"])
        h2.addWidget(self.cmb_stop)
        
        self.sp_score = QDoubleSpinBox()
        self.sp_score.setRange(0, 100)
        self.sp_score.setValue(95.0)
        self.sp_score.setSuffix("% Score")
        h2.addWidget(self.sp_score)
        
        self.sp_att = QSpinBox()
        self.sp_att.setRange(1, 10000)
        self.sp_att.setValue(200)
        self.sp_att.setSuffix(" Attempts")
        h2.addWidget(self.sp_att)
        h2.addStretch()
        sl.addLayout(h2)
        layout.addWidget(grp_stop)
        
        # Production Promotion
        self.btn_satisfied = QPushButton("✅ I AM SATISFIED - SAVE AND STOP")
        self.btn_satisfied.setFixedSize(300, 45)
        self.btn_satisfied.setStyleSheet(f"""
            QPushButton {{
                background: {C['green']};
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                margin-top: 10px;
            }}
            QPushButton:hover {{ background: #059669; }}
            QPushButton:disabled {{ background: {C['bg_darkest']}; color: {C['text_d']}; }}
        """)
        self.btn_satisfied.setEnabled(True) 
        layout.addWidget(self.btn_satisfied, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Hyperparameters
        grp_hyp = QGroupBox("Hyperparameters")
        grp_hyp.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        hl = QHBoxLayout(grp_hyp)
        
        hl.addWidget(QLabel("Learning Rate:"))
        self.sp_lr = QDoubleSpinBox()
        self.sp_lr.setDecimals(4)
        self.sp_lr.setSingleStep(0.0001)
        self.sp_lr.setValue(0.001)
        hl.addWidget(self.sp_lr)
        
        hl.addWidget(QLabel("Batch Size:"))
        self.cmb_batch = QComboBox()
        self.cmb_batch.addItems(["8", "16", "32", "64", "128"])
        self.cmb_batch.setCurrentText("32")
        hl.addWidget(self.cmb_batch)
        
        hl.addWidget(QLabel("Dropout:"))
        self.sp_drop = QDoubleSpinBox()
        self.sp_drop.setRange(0.0, 0.9)
        self.sp_drop.setSingleStep(0.1)
        self.sp_drop.setValue(0.3)
        hl.addWidget(self.sp_drop)
        hl.addStretch()
        layout.addWidget(grp_hyp)

        # Scheduler
        grp_sched = QGroupBox("Training Scheduler (Overnight Ops)")
        grp_sched.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        scl = QVBoxLayout(grp_sched)
        self.chk_sched = QCheckBox("Enable Scheduler")
        scl.addWidget(self.chk_sched)
        
        sh = QHBoxLayout()
        sh.addWidget(QLabel("From: 02:00  To: 06:00  Days: Mon-Fri"))
        sh.addStretch()
        scl.addLayout(sh)
        layout.addWidget(grp_sched)

        layout.addStretch()
