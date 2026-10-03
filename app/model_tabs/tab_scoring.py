from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QComboBox, QCheckBox, 
    QDoubleSpinBox, QSlider, QFrame, QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt
from app.theme import C
from app.widgets.rule_builder import RuleItemRow, AddRuleDialog

class TabScoring(QWidget):
    def __init__(self, model_record, parent=None):
        super().__init__(parent)
        self.model_record = model_record
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Mode
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Scoring Architect: "))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["auto", "manual", "goal_only"])
        self.mode_combo.setStyleSheet(f"background: {C['bg_dark']}; color: {C['white']}; border: 1px solid {C['border']};")
        h1.addWidget(self.mode_combo)
        
        # Reward Timing
        h1.addWidget(QLabel("Reward Timing:"))
        self.timing_combo = QComboBox()
        self.timing_combo.addItems(["sparse", "dense", "mixed"])
        self.timing_combo.setToolTip("Dense: Reward every step. Sparse: Reward at end only. Mixed: Key actions.")
        self.timing_combo.setStyleSheet(f"background: {C['bg_dark']}; color: {C['white']}; border: 1px solid {C['border']};")
        h1.addWidget(self.timing_combo)
        
        h1.addStretch()
        layout.addLayout(h1)
        
        self.layers_widget = QFrame()
        hl = QHBoxLayout(self.layers_widget)
        
        # Layer 1
        l1 = QGroupBox("Layer 1: Goal Match")
        l1.setStyleSheet(f"border-top: 3px solid {C['purple']};")
        vl1 = QVBoxLayout(l1)
        self.chk_l1 = QCheckBox("Enable Layer 1")
        self.chk_l1.setChecked(True)
        vl1.addWidget(self.chk_l1)
        vl1.addWidget(QLabel("Weight: 30%"))
        vl1.addStretch()
        hl.addWidget(l1)
        
        # Layer 2: Penalty and Reward Rules
        l2 = QGroupBox("Layer 2: Penalty and Reward Rules")
        l2.setStyleSheet(f"border-top: 3px solid #3b82f6;")
        vl2 = QVBoxLayout(l2)
        self.chk_l2 = QCheckBox("Enable Layer 2")
        self.chk_l2.setChecked(True)
        vl2.addWidget(self.chk_l2)
        
        # Rule List
        self.rule_scroll = QScrollArea()
        self.rule_scroll.setWidgetResizable(True)
        self.rule_scroll.setFixedHeight(120)
        self.rule_scroll.setStyleSheet(f"background: {C['bg_dark']}; border: 1px solid {C['border']};")
        self.rule_list_widget = QWidget()
        self.rule_list_layout = QVBoxLayout(self.rule_list_widget)
        self.rule_list_layout.setContentsMargins(2,2,2,2)
        self.rule_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.rule_scroll.setWidget(self.rule_list_widget)
        vl2.addWidget(self.rule_scroll)
        
        btn_add = QPushButton("+ Add Sentence Rule")
        btn_add.setStyleSheet(f"color: {C['cyan']}; background: transparent; text-align: left; padding: 4px; border: none; font-size: 11px;")
        btn_add.clicked.connect(self._on_add_rule)
        vl2.addWidget(btn_add)
        
        vl2.addStretch()
        hl.addWidget(l2)
        
        # Layer 3
        l3 = QGroupBox("Layer 3: Behavior Analysis")
        l3.setStyleSheet(f"border-top: 3px solid #10b981;")
        vl3 = QVBoxLayout(l3)
        self.chk_l3 = QCheckBox("Enable Layer 3")
        self.chk_l3.setChecked(True)
        vl3.addWidget(self.chk_l3)
        vl3.addWidget(QCheckBox("Click Spread Pen.", checked=True))
        vl3.addWidget(QCheckBox("Sequence Quality", checked=True))
        vl3.addWidget(QCheckBox("Retry Det.", checked=True))
        vl3.addWidget(QCheckBox("Time Dist.", checked=True))
        vl3.addStretch()
        hl.addWidget(l3)
        
        layout.addWidget(self.layers_widget)
        
        # Advanced
        self.adv_widget = QGroupBox("Advanced Constraints")
        self.adv_widget.setStyleSheet(f"color: {C['white']}; font-weight: bold;")
        al = QVBoxLayout(self.adv_widget)
        self.chk_dim = QCheckBox("Diminishing Returns (Penalty for repeating clicks)")
        self.chk_dim.setChecked(True)
        al.addWidget(self.chk_dim)
        
        ha = QHBoxLayout()
        ha.addWidget(QLabel("Confidence Threshold:"))
        self.slider_conf = QSlider(Qt.Orientation.Horizontal)
        self.slider_conf.setRange(0, 100)
        self.slider_conf.setValue(65)
        ha.addWidget(self.slider_conf)
        self.lbl_conf = QLabel("65%")
        self.slider_conf.valueChanged.connect(lambda v: self.lbl_conf.setText(f"{v}%"))
        ha.addWidget(self.lbl_conf)
        ha.addStretch()
        al.addLayout(ha)
        
        # Global Safety Guards (10/10 Feature)
        al.addWidget(QLabel("GLOBAL SAFETY GUARDS:"))
        hp1 = QHBoxLayout()
        hp1.addWidget(QLabel("Step Penalty (Forces Speed):"))
        self.spin_step = QDoubleSpinBox()
        self.spin_step.setRange(0, 10)
        self.spin_step.setSingleStep(0.1)
        self.spin_step.setValue(0.1)
        hp1.addWidget(self.spin_step)
        hp1.addStretch()
        al.addLayout(hp1)
        
        self.chk_loop = QCheckBox("Auto Loop Detection (Penalize spamming)")
        self.chk_loop.setChecked(True)
        al.addWidget(self.chk_loop)
        
        layout.addWidget(self.adv_widget)

        layout.addStretch()

        # Connections
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        
        # Load Existing
        self._load_config()
        self._on_mode_changed(self.mode_combo.currentText())

    def _on_add_rule(self):
        # Gather names for dropdowns
        goals = []
        if self.model_record and self.model_record.scoring_config:
             # Assume goals are listed or we can infer them from config
             pass
        
        # Mocking list for now if record is not loaded yet
        goals = ["App_Home", "Login_Screen", "Success_Popup"]
        actions = ["Wait", "Click_Icon", "Swipe_Up", "Submit"]
        
        dlg = AddRuleDialog(goals, actions, self)
        if dlg.exec():
            data = dlg.get_data()
            self._add_rule_item(data)

    def _add_rule_item(self, data):
        row = RuleItemRow(data)
        row.removed.connect(self._remove_rule)
        self.rule_list_layout.addWidget(row)

    def _remove_rule(self, row):
        row.setParent(None)
        row.deleteLater()

    def _on_mode_changed(self, text):
        visible = (text == "manual")
        self.layers_widget.setVisible(visible)
        self.adv_widget.setVisible(visible)

    def _load_config(self):
        if not self.model_record or not self.model_record.scoring_config:
            return
        sc = self.model_record.scoring_config
        l2 = sc.get("layer2", {})
        
        self.mode_combo.setCurrentText(sc.get("mode", "auto"))
        self.timing_combo.setCurrentText(sc.get("reward_timing", "sparse"))
        self.slider_conf.setValue(int(sc.get("confidence_threshold", 0.65) * 100))
        
        self.chk_l2.setChecked(l2.get("enabled", True))
        for r in l2.get("rules", []):
            self._add_rule_item(r)
            
        guards = sc.get("global_constraints", {})
        self.spin_step.setValue(guards.get("step_penalty", 0.1))
        self.chk_loop.setChecked(guards.get("loop_detection", True))

    def get_scoring_config(self) -> dict:
        rules = []
        for i in range(self.rule_list_layout.count()):
            row = self.rule_list_layout.itemAt(i).widget()
            if isinstance(row, RuleItemRow):
                rules.append(row.rule_data)
                
        return {
            "mode": self.mode_combo.currentText(),
            "reward_timing": self.timing_combo.currentText(),
            "confidence_threshold": self.slider_conf.value() / 100.0,
            "layer1": {"enabled": self.chk_l1.isChecked()},
            "layer2": {
                "enabled": self.chk_l2.isChecked(),
                "rules": rules
            },
            "layer3": {"enabled": self.chk_l3.isChecked()},
            "global_constraints": {
                "step_penalty": self.spin_step.value(),
                "loop_detection": self.chk_loop.isChecked()
            }
        }
