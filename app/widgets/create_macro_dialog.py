from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, 
                             QFrame, QWidget, QScrollArea)
from PyQt6.QtCore import Qt
from app.theme import C

class CreateMacroDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(600, 500)
        self._setup_ui()

    def _setup_ui(self):
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("main_frame")
        self.main_frame.setStyleSheet(f"""
            #main_frame {{
                background-color: {C['bg_sidebar']};
                border: 1px solid {C['border_b']};
                border-radius: 12px;
            }}
        """)
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.main_frame)
        
        layout = QVBoxLayout(self.main_frame)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Header
        header = QHBoxLayout()
        title = QLabel("CREATE NEW MACRO")
        title.setStyleSheet(f"color: {C['white']}; font-size: 16px; font-weight: 800; letter-spacing: 1px;")
        header.addWidget(title)
        header.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"color: {C['text_d']}; border: none; background: transparent; font-size: 20px;")
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Inputs
        layout.addWidget(self._create_label("MACRO NAME"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. coinglass_auto_scan")
        self.name_input.setMinimumHeight(45)
        self.name_input.setStyleSheet(self._input_style())
        layout.addWidget(self.name_input)

        layout.addWidget(self._create_label("DESCRIPTION"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("What does this macro automate?")
        self.desc_input.setMaximumHeight(100)
        self.desc_input.setStyleSheet(self._input_style())
        layout.addWidget(self.desc_input)

        layout.addStretch()

        # Action Buttons
        actions = QHBoxLayout()
        actions.addStretch()
        
        cancel = QPushButton("Cancel")
        cancel.setFixedSize(100, 36)
        cancel.setStyleSheet(f"color: {C['text']}; border: none; background: transparent; font-weight: 600;")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        
        create = QPushButton("Create Macro")
        create.setFixedSize(150, 36)
        create.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['purple']};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {C['purple_l']}; }}
        """)
        create.clicked.connect(self.accept)
        actions.addWidget(create)
        layout.addLayout(actions)

    def _create_label(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        return l

    def _input_style(self):
        return f"background-color: {C['bg_darkest']}; color: {C['white']}; border: 1px solid {C['border']}; border-radius: 6px; padding: 12px; font-size: 14px;"

    def get_data(self):
        return {
            "name": self.name_input.text(),
            "description": self.desc_input.toPlainText()
        }
