"""
Common helper widgets: specialized buttons, labels, and panels.
"""
from PyQt6.QtWidgets import QPushButton, QLabel, QFrame, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from app.theme import C, FONT_UI


class PrimaryButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("btn_primary")


class SecondaryButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("btn_secondary")


class DangerButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("btn_danger")


class SectionLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("label_section")


class ValueLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("label_value")


class MutedLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("label_muted")


class Panel(QFrame):
    """A styled container panel."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            background-color: {C['bg_panel']};
            border: 1px solid {C['border']};
            border-radius: 8px;
        """)
        self.layout = QVBoxLayout(self)

class SectionHeader(QLabel):
    """A consistent header for sidebar sections."""
    def __init__(self, text, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(f"color: {C['text_d']}; font-size: 10px; font-weight: bold; letter-spacing: 1.2px; margin-top: 10px; margin-bottom: 5px; border: none; background: transparent;")
