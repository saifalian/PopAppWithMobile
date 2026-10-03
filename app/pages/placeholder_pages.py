from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from app.theme import C

class PlaceholderPage(QWidget):
    """Temporary placeholder for unbuilt pages."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        lbl = QLabel(title)
        lbl.setObjectName("page_title")
        layout.addWidget(lbl)
        sub = QLabel(f"This page is under construction.\nAll functionality for {title} will be built here.")
        sub.setStyleSheet(f"color: {C['text_d']}; font-size: 13px;")
        layout.addWidget(sub)
        layout.addStretch()

def create_agent_control_page():
    return PlaceholderPage("Agent Control")

def create_video_processing_page():
    return PlaceholderPage("Video Processing")

def create_results_page():
    return PlaceholderPage("Results")
