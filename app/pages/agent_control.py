"""
Agent Control page — full model management with 8 tabs.
Matches the original LiquidityAI specification.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QScrollArea, QFrame, QGridLayout, QSizePolicy,
    QCheckBox, QLineEdit, QComboBox, QGroupBox, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from app.theme import C, FONT_UI


class AgentControlPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("Agent Control & Model Management")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        # 8-Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Define Tabs
        self.tabs.addTab(self._create_data_tab(), "Data")
        self.tabs.addTab(self._create_label_tab(), "Label")
        self.tabs.addTab(self._create_actions_tab(), "Actions")
        self.tabs.addTab(self._create_reset_tab(), "Reset")
        self.tabs.addTab(self._create_train_tab(), "Train")
        self.tabs.addTab(self._create_scoring_tab(), "Scoring")
        self.tabs.addTab(self._create_goals_tab(), "Goals")
        self.tabs.addTab(self._create_results_tab(), "Results")

        root.addWidget(self.tabs)

    def _create_data_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 24, 16, 16)
        l.setSpacing(12)
        l.addWidget(QLabel("Region Detection & Data Health"))
        l.addWidget(QCheckBox("Auto-detect chart area"))
        l.addWidget(QCheckBox("Enable data augmentation"))
        l.addLayout(self._path_field("Raw Data Directory", "data/raw"))
        l.addStretch()
        return w

    def _create_label_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 24, 16, 16)
        l.setSpacing(12)
        l.addWidget(QLabel("Labelling & Consistency Check"))
        btn_row = QHBoxLayout()
        btn_row.addWidget(QPushButton("🔍 Auto-detect Labels"))
        btn_row.addWidget(QPushButton("📋 Review Labels"))
        l.addLayout(btn_row)
        l.addStretch()
        return w

    def _create_actions_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 24, 16, 16)
        l.setSpacing(12)
        l.addWidget(QLabel("Desktop Automation Sequences"))
        l.addWidget(QPushButton("⏺ Record New Sequence"))
        l.addStretch()
        return w

    def _create_reset_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 24, 16, 16)
        l.setSpacing(12)
        l.addWidget(QLabel("Reset & Recovery Rules"))
        l.addWidget(QCheckBox("Master Reset (Return to Home)"))
        l.addWidget(QCheckBox("Verify state after reset"))
        l.addStretch()
        return w

    def _create_train_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 24, 16, 16)
        l.setSpacing(14)
        
        # Init Section
        init_box = QGroupBox("MODEL INITIALIZATION")
        init_l = QVBoxLayout(init_box)
        init_l.addWidget(QLabel("Create or load the core vision model for this agent."))
        
        btn_row = QHBoxLayout()
        self.btn_init = QPushButton("🏗  Initialize New Model")
        self.btn_init.setObjectName("btn_primary")
        self.btn_init.setFixedSize(200, 36)
        btn_row.addWidget(self.btn_init)
        
        self.btn_load = QPushButton("📂  Load Weights")
        self.btn_load.setObjectName("btn_secondary")
        self.btn_load.setFixedSize(140, 36)
        btn_row.addWidget(self.btn_load)
        btn_row.addStretch()
        init_l.addLayout(btn_row)
        
        l.addWidget(init_box)
        l.addSpacing(10)

        l.addWidget(QLabel("Training Strategy & Scheduler"))
        modes = QComboBox()
        modes.addItems(["Self-Improving", "Fine-Tuning", "Exploration"])
        l.addWidget(modes)
        l.addStretch()
        return w

    def _create_scoring_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 24, 16, 16)
        l.setSpacing(12)
        l.addWidget(QLabel("Reward & Scoring Logic"))
        l.addWidget(QDoubleSpinBox())
        l.addStretch()
        return w

    def _create_goals_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 24, 16, 16)
        l.setSpacing(12)
        l.addWidget(QLabel("Goal Image & Thresholds"))
        l.addStretch()
        return w

    def _create_results_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 24, 16, 16)
        l.setSpacing(12)
        l.addWidget(QLabel("Performance Comparison & Drift"))
        l.addStretch()
        return w

    def _path_field(self, label, default):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit(default)
        row.addWidget(edit)
        btn = QPushButton("...")
        btn.setFixedWidth(30)
        row.addWidget(btn)
        return row