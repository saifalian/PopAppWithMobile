from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QScrollArea,
    QListView, QListWidget, QListWidgetItem, QDialog, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from app.theme import C, FONT_MONO
from pathlib import Path
import json

class SectionHeader(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; font-weight: bold; letter-spacing: 1.5px; margin-top: 20px; margin-bottom: 10px;")

class ReplayDialog(QDialog):
    """A dialog to play back a captured experience replay."""
    def __init__(self, replay_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mobile Experience Replay Viewer")
        self.resize(1000, 700)
        self.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['white']};")
        
        self.path = Path(replay_path)
        self.steps = sorted([d for d in self.path.iterdir() if d.is_dir() and d.name.startswith("step_")])
        self.current_step = 0
        
        layout = QVBoxLayout(self)
        
        # Header
        hl = QHBoxLayout()
        self.lbl_title = QLabel(f"Replay: {self.path.name}")
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        hl.addWidget(self.lbl_title)
        hl.addStretch()
        layout.addLayout(hl)
        
        # Splitter for steps list and image view
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Step List
        self.list_steps = QListWidget()
        self.list_steps.setFixedWidth(200)
        self.list_steps.setStyleSheet(f"background: {C['bg_sidebar']}; border: 1px solid {C['border']};")
        for s in self.steps:
            item = QListWidgetItem(s.name.replace("_", " ").capitalize())
            self.list_steps.addItem(item)
        self.list_steps.currentRowChanged.connect(self._show_step)
        splitter.addWidget(self.list_steps)
        
        # Preview Area
        preview_container = QWidget()
        pv = QVBoxLayout(preview_container)
        
        img_row = QHBoxLayout()
        self.lbl_before = QLabel("BEFORE")
        self.lbl_after = QLabel("AFTER")
        for lbl in [self.lbl_before, self.lbl_after]:
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"background: #000; border: 1px solid {C['border']};")
            img_row.addWidget(lbl)
        
        pv.addLayout(img_row)
        
        self.lbl_meta = QLabel("Action: None | Confidence: 0%")
        self.lbl_meta.setStyleSheet(f"color: {C['cyan']}; font-family: '{FONT_MONO}'; font-size: 14px; padding: 10px;")
        pv.addWidget(self.lbl_meta)
        
        splitter.addWidget(preview_container)
        layout.addWidget(splitter)
        
        # Controls
        ctrl = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Previous")
        self.btn_next = QPushButton("Next ▶")
        for b in [self.btn_prev, self.btn_next]: 
            b.setFixedSize(120, 40)
            b.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 4px;")
        
        self.btn_prev.clicked.connect(lambda: self.list_steps.setCurrentRow(max(0, self.list_steps.currentRow()-1)))
        self.btn_next.clicked.connect(lambda: self.list_steps.setCurrentRow(min(len(self.steps)-1, self.list_steps.currentRow()+1)))
        
        ctrl.addStretch()
        ctrl.addWidget(self.btn_prev)
        ctrl.addWidget(self.btn_next)
        ctrl.addStretch()
        layout.addLayout(ctrl)
        
        if self.steps:
            self.list_steps.setCurrentRow(0)

    def _show_step(self, index):
        if index < 0 or index >= len(self.steps): return
        step_dir = self.steps[index]
        
        # Load images
        self.lbl_before.setPixmap(QPixmap(str(step_dir / "before.png")).scaled(400, 500, Qt.AspectRatioMode.KeepAspectRatio))
        self.lbl_after.setPixmap(QPixmap(str(step_dir / "after.png")).scaled(400, 500, Qt.AspectRatioMode.KeepAspectRatio))
        
        # Load meta
        try:
            with open(step_dir / "meta.json") as f:
                m = json.load(f)
                self.lbl_meta.setText(f"Action: {m['action']} | Confidence: {m.get('confidence', 1.0)*100:.1f}%")
        except: pass

class ResultsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_name = ""
        self._build_ui()

    def set_model(self, model_name):
        self.model_name = model_name
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)
        root.setSpacing(10)
        
        # Scroll Area for the whole page
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. CORE STATS TABLE
        self.content_layout.addWidget(SectionHeader("General Training History"))
        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["Model", "Latest Accuracy", "Last Update", "Drift Status"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; gridline-color: {C['border']}; selection-background-color: {C['purple']}33;")
        self.results_table.setFixedHeight(150)
        self.content_layout.addWidget(self.results_table)
        
        # 2. MOBILE EXPERIENCE REPLAYS (P10)
        self.content_layout.addWidget(SectionHeader("Mobile Experience Replays (Snapshots)"))
        self.replay_list = QListWidget()
        self.replay_list.setFixedHeight(300)
        self.replay_list.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; color: {C['text']}; padding: 10px;")
        self.replay_list.itemDoubleClicked.connect(self._on_replay_double_click)
        self.content_layout.addWidget(self.replay_list)
        
        self.btn_refresh = QPushButton("🔄 Refresh Replays")
        self.btn_refresh.setFixedWidth(150)
        self.btn_refresh.setStyleSheet(f"background: {C['bg_sidebar']}; color: {C['cyan']}; border: 1px solid {C['cyan']}; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_refresh.clicked.connect(self.refresh)
        self.content_layout.addWidget(self.btn_refresh)
        
        self.content_layout.addStretch()
        
        scroll.setWidget(content)
        root.addWidget(scroll)

    def refresh(self):
        if not self.model_name: return
        
        # Refresh Replays
        self.replay_list.clear()
        from backend.core.replay_manager import ReplayManager
        rm = ReplayManager(self.model_name)
        replays = rm.list_replays()
        
        if not replays:
            self.replay_list.addItem("No replays found for this model yet.")
        
        for r in replays:
            status = "✅ SUCCESS" if r.get("success") else "❌ FAILED"
            score = f"Score: {r.get('total_score', 0):.1f}"
            date = f"[{time.ctime(r.get('end_time', 0))}]"
            item = QListWidgetItem(f"{status} | {score} | {date}")
            item.setData(Qt.ItemDataRole.UserRole, r.get("path"))
            self.replay_list.addItem(item)

    def _on_replay_double_click(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            dialog = ReplayDialog(path, self)
            dialog.exec()

import time
