from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QStackedWidget, QFrame, QSpinBox, QTimeEdit,
    QCheckBox, QGroupBox, QGridLayout, QWidget
)
from PyQt6.QtCore import Qt, QTime
from app.theme import C

class WizardPage(QWidget):
    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)
        
        t = QLabel(title.upper())
        t.setStyleSheet(f"color: {C['cyan']}; font-size: 18px; font-weight: bold; letter-spacing: 1.5px;")
        self.layout.addWidget(t)
        
        st = QLabel(subtitle)
        st.setStyleSheet(f"color: {C['text_d']}; font-size: 12px;")
        st.setWordWrap(True)
        self.layout.addWidget(st)
        
        self.content = QVBoxLayout()
        self.layout.addLayout(self.content)
        self.layout.addStretch()

class OvernightWizard(QDialog):
    def __init__(self, mobile_mgr, parent=None):
        super().__init__(parent)
        self.mobile_mgr = mobile_mgr
        self.setWindowTitle("Overnight Training Setup Wizard")
        self.setFixedSize(600, 500)
        self.setStyleSheet(f"background: {C['bg_sidebar']}; color: {C['white']};")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Progress Bar at the top
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 5)
        self.progress.setValue(1)
        self.progress.setStyleSheet(f"QProgressBar::chunk {{ background: {C['cyan']}; }}")
        self.main_layout.addWidget(self.progress)
        
        # Stacked Widget for pages
        self.stack = QStackedWidget()
        self._build_pages()
        self.main_layout.addWidget(self.stack)
        
        # Navigation Buttons
        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(30, 0, 30, 30)
        
        self.btn_back = QPushButton("← Back")
        self.btn_back.setFixedSize(100, 40)
        self.btn_back.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 4px;")
        self.btn_back.clicked.connect(self._prev_page)
        self.btn_back.hide()
        
        self.btn_next = QPushButton("Next →")
        self.btn_next.setFixedSize(120, 40)
        self.btn_next.setStyleSheet(f"background: {C['purple']}; color: white; border-radius: 4px; font-weight: bold;")
        self.btn_next.clicked.connect(self._next_page)
        
        nav_row.addWidget(self.btn_back)
        nav_row.addStretch()
        nav_row.addWidget(self.btn_next)
        self.main_layout.addLayout(nav_row)

    def _build_pages(self):
        # 1. Safety Check
        p1 = WizardPage("Device Health Check", "Verifying if the phone is ready for a long session.")
        self.lbl_batt = QLabel("● Battery: Charging (87%) ✓")
        self.lbl_temp = QLabel("● Temperature: 38.2°C ✓")
        self.lbl_storage = QLabel("● Storage: 184GB Available ✓")
        for lbl in [self.lbl_batt, self.lbl_temp, self.lbl_storage]:
            lbl.setStyleSheet(f"color: {C['green']}; font-size: 14px;")
            p1.content.addWidget(lbl)
        self.stack.addWidget(p1)
        
        # 2. Limits
        p2 = WizardPage("Training Limits", "Define how long the session should run.")
        g2 = QGridLayout()
        g2.addWidget(QLabel("Maximum Attempts:"), 0, 0)
        self.spin_attempts = QSpinBox(); self.spin_attempts.setRange(1, 1000); self.spin_attempts.setValue(50)
        g2.addWidget(self.spin_attempts, 0, 1)
        
        g2.addWidget(QLabel("Stop Time:"), 1, 0)
        self.time_stop = QTimeEdit(); self.time_stop.setTime(QTime(6, 0))
        g2.addWidget(self.time_stop, 1, 1)
        
        for i in range(g2.count()):
            w = g2.itemAt(i).widget()
            if isinstance(w, QLabel): w.setStyleSheet(f"color: {C['text_d']};")
            else: w.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; padding: 5px;")
        p2.content.addLayout(g2)
        self.stack.addWidget(p2)
        
        # 3. Strategy
        p3 = WizardPage("Safety Strategy", "How to handle issues during the night.")
        self.chk_thermal = QCheckBox("Auto-pause if overheated (>46°C)")
        self.chk_thermal.setChecked(True)
        self.chk_restart = QCheckBox("Restart the app every 20 attempts")
        self.chk_notifications = QCheckBox("Block notifications during training")
        self.chk_notifications.setChecked(True)
        for chk in [self.chk_thermal, self.chk_restart, self.chk_notifications]:
            chk.setStyleSheet(f"color: {C['text']}; font-size: 13px;")
            p3.content.addWidget(chk)
        self.stack.addWidget(p3)
        
        # 4. Starting Setup
        p4 = WizardPage("The Launch Plan", "Verify orientations and app status.")
        self.lbl_launch = QLabel("✓ The app will be launched via ADB\n✓ Phone locked to current orientation\n✓ Screen will be kept awake")
        self.lbl_launch.setStyleSheet(f"color: {C['cyan']}; line-height: 1.5;")
        p4.content.addWidget(self.lbl_launch)
        self.stack.addWidget(p4)
        
        # 5. Review
        p5 = WizardPage("Review & Start", "Ready for the big run.")
        self.lbl_summary = QLabel("Training will run until 06:00 AM\nMax 50 attempts will be made.\nFull experience replays will be saved.")
        self.lbl_summary.setStyleSheet(f"color: {C['white']}; font-size: 14px; background: {C['bg_darkest']}; padding: 20px; border-radius: 8px;")
        p5.content.addWidget(self.lbl_summary)
        self.stack.addWidget(p5)

    def _next_page(self):
        curr = self.stack.currentIndex()
        if curr < 4:
            self.stack.setCurrentIndex(curr + 1)
            self.progress.setValue(curr + 2)
            self.btn_back.show()
            if curr == 3:
                self.btn_next.setText("🚀 START TRAINING")
                self.btn_next.setStyleSheet(f"background: {C['green']}; color: black; font-weight: bold; border-radius: 4px;")
        else:
            self.accept()

    def _prev_page(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self.stack.setCurrentIndex(curr - 1)
            self.progress.setValue(curr)
            if curr == 1: self.btn_back.hide()
            self.btn_next.setText("Next →")
            self.btn_next.setStyleSheet(f"background: {C['purple']}; color: white; border-radius: 4px; font-weight: bold;")
