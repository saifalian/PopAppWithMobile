"""
Model Screen.
Top-level view for a specific model.
Contains a QTabWidget for Data, Label, Actions, Reset, Train, Scoring, Goals, Results.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt

from app.theme import C
from backend.database.models import ModelRecord
from backend.database.db import SessionLocal

from app.model_tabs.tab_data import TabData
from app.model_tabs.tab_label import TabLabel
from app.model_tabs.tab_actions import TabActions
from app.model_tabs.tab_reset import TabReset
from app.model_tabs.tab_train import TabTrain
from app.model_tabs.tab_scoring import TabScoring
from app.model_tabs.tab_goals import TabGoals
from app.model_tabs.tab_results import TabResults

class ModelScreen(QWidget):
    def __init__(self, model_id: str = None, parent=None):
        super().__init__(parent)
        self.model_id = model_id
        
        if model_id:
            db = SessionLocal()
            self.model_record = db.query(ModelRecord).filter_by(id=model_id).first()
            db.close()
        else:
            self.model_record = None
            
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if not self.model_record:
            layout.addWidget(QLabel("Model not found."))
            return
            
        # Header
        header = QHBoxLayout()
        header.setContentsMargins(20, 20, 20, 10)
        title = QLabel(f"⚙ Model Configuration: {self.model_record.name}")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {C['white']};")
        header.addWidget(title)
        
        btn_save = QPushButton("Save Settings")
        btn_save.setStyleSheet(f"background: {C['violet']}; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        header.addStretch()
        header.addWidget(btn_save)
        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"QTabWidget::pane {{ border: 1px solid {C['border']}; }} QTabBar::tab {{ background: {C['bg_panel']}; color: {C['text']}; padding: 10px 20px; }} QTabBar::tab:selected {{ background: {C['bg_card']}; color: {C['purple']}; font-weight: bold; border-bottom: 2px solid {C['purple']}; }}")
        
        self.tabs.addTab(TabData(self.model_record, self), "Data")
        self.tabs.addTab(TabLabel(self.model_record, self), "Label")
        self.tabs.addTab(TabActions(self.model_record, self), "Actions")
        self.tabs.addTab(TabReset(self.model_record, self), "Reset")
        self.tabs.addTab(TabTrain(self.model_record, self), "Train")
        self.tabs.addTab(TabScoring(self.model_record, self), "Scoring")
        self.tabs.addTab(TabGoals(self.model_record, self), "Goals")
        self.tabs.addTab(TabResults(self.model_record, self), "Results")
        
        layout.addWidget(self.tabs)
