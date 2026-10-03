from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QComboBox, QCheckBox, 
    QDoubleSpinBox, QSlider, QFrame, QPushButton, QDialog, QLineEdit, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.theme import C

class RuleItemRow(QFrame):
    removed = pyqtSignal(object)

    def __init__(self, rule_data: dict, parent=None):
        super().__init__(parent)
        self.rule_data = rule_data
        self.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; border-radius: 4px; margin: 1px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Build Sentence
        state = rule_data.get("if_state", "Any State")
        action = rule_data.get("if_action", "Any Action")
        rtype = rule_data.get("type", "reward").upper()
        pts = rule_data.get("points", 0)
        prio = rule_data.get("priority", "MEDIUM")
        
        sentence = f"IF <b>{state}</b> + <b>{action}</b> THEN <span style='color:{C['green'] if rtype=='REWARD' else C['red']}'>{rtype} {pts} pts</span> <small>({prio})</small>"
        
        lbl = QLabel(sentence)
        lbl.setStyleSheet(f"color: {C['text']}; font-size: 11px;")
        layout.addWidget(lbl)
        layout.addStretch()
        
        btn_del = QPushButton("×")
        btn_del.setFixedSize(20, 20)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(f"color: {C['text_d']}; background: transparent; border: none; font-size: 16px; font-weight: bold;")
        btn_del.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(btn_del)

class AddRuleDialog(QDialog):
    def __init__(self, goal_names, action_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Build Reward Rule")
        self.setFixedWidth(450)
        self.setStyleSheet(f"background: {C['bg_panel']}; color: {C['white']};")
        layout = QVBoxLayout(self)
        
        # State
        layout.addWidget(QLabel("IF State looks like:"))
        self.combo_state = QComboBox()
        self.combo_state.addItems(["[ Any State ]"] + goal_names)
        layout.addWidget(self.combo_state)
        
        # Action
        layout.addWidget(QLabel("AND Action is:"))
        self.combo_action = QComboBox()
        self.combo_action.addItems(["[ Any Action ]"] + action_names)
        layout.addWidget(self.combo_action)
        
        # Result
        h2 = QHBoxLayout()
        v2_1 = QVBoxLayout()
        v2_1.addWidget(QLabel("THEN:"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Reward (+)", "Penalty (-)"])
        v2_1.addWidget(self.combo_type)
        h2.addLayout(v2_1)
        
        v2_2 = QVBoxLayout()
        v2_2.addWidget(QLabel("Points:"))
        self.spin_pts = QDoubleSpinBox()
        self.spin_pts.setRange(0, 1000)
        self.spin_pts.setValue(10.0)
        v2_2.addWidget(self.spin_pts)
        h2.addLayout(v2_2)
        layout.addLayout(h2)
        
        # Priority
        layout.addWidget(QLabel("Priority (Weight):"))
        self.combo_prio = QComboBox()
        self.combo_prio.addItems(["LOW", "MEDIUM", "HIGH"])
        self.combo_prio.setCurrentText("MEDIUM")
        layout.addWidget(self.combo_prio)
        
        btns = QHBoxLayout()
        btn_ok = QPushButton("Add to Checklist")
        btn_ok.setStyleSheet(f"background: {C['purple']}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_ok.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(btn_ok)
        layout.addLayout(btns)

    def get_data(self):
        return {
            "if_state": None if self.combo_state.currentIndex() == 0 else self.combo_state.currentText(),
            "if_action": None if self.combo_action.currentIndex() == 0 else self.combo_action.currentText(),
            "type": "reward" if self.combo_type.currentIndex() == 0 else "penalty",
            "points": self.spin_pts.value(),
            "priority": self.combo_prio.currentText()
        }
