"""
Unsupervised Learning Dashboard page.
Main page showing model cards, training controls, and live terminal.
Matches the screenshot exactly.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QMessageBox, QStackedWidget,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from app.theme import C, FONT_UI
from app.widgets.model_card import ModelCard
from app.widgets.terminal import TerminalWidget
from app.widgets.gpu_bar import GpuBar
from app.dialogs.create_model_dialog import CreateModelDialog
from backend.core.settings_manager import settings
from backend.core.training_worker import TrainingWorker
from backend.core.gpu_manager import get_live_gpu_stats, ComputeDevice
from app.core.gpu_manager import TFDeviceSetup
from app.widgets.overlay import TrainingOverlay


DEMO_MODELS = [
    {"name": "click_clusters",  "status": "trained",   "score": 84, "attempts": 142},
    {"name": "read_popup",      "status": "trained",   "score": 91, "attempts": 89},
    {"name": "assess_chart",    "status": "training",  "score": 61, "attempts": 12},
    {"name": "open_the_app",    "status": "untrained", "score": 0,  "attempts": 0},
]


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: dict[str, TrainingWorker] = {}
        self._cards:   dict[str, ModelCard]      = {}
        self._build_ui()
        # _load_models is now called at the end of _build_ui

    def _build_ui(self):
        # The entire page is now scrollable as one piece
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.scroll_content = QWidget()
        root = QVBoxLayout(self.scroll_content)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # ── Page header ──────────────────────────────────────────
        header_row = QHBoxLayout()
        left = QVBoxLayout()
        title_row = QHBoxLayout()
        icon = QLabel("📊")
        icon.setStyleSheet("font-size: 22px;")
        title = QLabel("Unsupervised Learning Dashboard")
        title.setStyleSheet(f"color: {C['white']}; font-size: 22px; font-weight: bold;")
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()
        
        subtitle = QLabel(
            "Monitor and manage your autonomous, unsupervised model training loops.\n"
            "This view provides a high-level overview of active models and their performance."
        )
        subtitle.setStyleSheet(f"color: {C['text']}; font-size: 12px; line-height: 1.6;")
        subtitle.setWordWrap(True)
        left.addLayout(title_row)
        left.addSpacing(6)
        left.addWidget(subtitle)
        header_row.addLayout(left)
        header_row.addStretch()

        # Buttons on right
        root.addLayout(header_row)

        # Spacing
        root.addSpacing(10)

        # ── GPU bar ──────────────────────────────────────────────
        root.addSpacing(4)
        self.gpu_bar = GpuBar()
        root.addWidget(self.gpu_bar)
        root.addSpacing(6)

        # ── Summary Stat Cards ──────────────────────────────────
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(16)
        
        def stat_card(value, label, color):
            card = QFrame()
            card.setFixedHeight(84)
            card.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {C['bg_sidebar']}, stop:1 #1e1e2e);
                    border: 1px solid {C['border']};
                    border-left: 4px solid {color};
                    border-radius: 8px;
                }}
            """)
            l = QVBoxLayout(card)
            l.setContentsMargins(18, 14, 18, 14)
            l.setSpacing(2)
            
            v = QLabel(str(value))
            v.setStyleSheet(f"color: {C['white']}; font-size: 32px; font-weight: 800; border: none; background: transparent;")
            
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px; border: none; background: transparent;")
            
            l.addWidget(v)
            l.addWidget(lbl)
            return card, v

        self.stat_items = []
        for i, (val, lbl, clr) in enumerate([
            (0, "TOTAL MODELS", C['amber']),
            (0, "TRAINED", C['green']),
            (0, "IN TRAINING", C['amber']),
            (0, "DRIFT ALERTS", C['status_error']),
        ]):
            card, v_lbl = stat_card(val, lbl, clr)
            self.stat_items.append({"frame": card, "val_lbl": v_lbl})
            self.stats_grid.addWidget(card, 0, i)
            
        root.addLayout(self.stats_grid)

        # ── View Toggle ──────────────────────────────────────────
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(10, 10, 10, 0)
        toggle_row.setSpacing(20)
        
        self.btn_training_view = QPushButton("TRAINING VIEW")
        self.btn_training_view.setCheckable(True)
        self.btn_training_view.setChecked(True)
        self.btn_training_view.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                color: {C['text']}; 
                border: none; 
                font-weight: bold; 
                padding: 12px 20px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: {C['bg_panel']}; color: {C['white']}; }}
            QPushButton:checked {{ 
                background: {C['bg_panel']};
                color: {C['white']}; 
                border-bottom: 3px solid {C['purple']}; 
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
        """)
        
        self.btn_ops_view = QPushButton("DAILY OPERATIONS")
        self.btn_ops_view.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ops_view.setCheckable(True)
        self.btn_ops_view.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                color: {C['text']}; 
                border: none; 
                font-weight: bold; 
                padding: 12px 20px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: {C['bg_panel']}; color: {C['white']}; }}
            QPushButton:checked {{ 
                background: {C['bg_panel']};
                color: {C['white']}; 
                border-bottom: 3px solid {C['purple']}; 
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
        """)
        
        toggle_row.addWidget(self.btn_training_view)
        toggle_row.addWidget(self.btn_ops_view)
        toggle_row.addStretch()
        root.addLayout(toggle_row)

        # ── Main Stacked Content ─────────────────────────────────
        self.main_stack = QStackedWidget()
        
        # 1. Training View
        training_widget = QWidget()
        training_layout = QVBoxLayout(training_widget)
        training_layout.setContentsMargins(0, 10, 0, 0)
        training_layout.setSpacing(24) # More breathing room
        
        # Model cards grid (no internal scroll)
        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(20)
        training_layout.addLayout(self.cards_grid)
        
        # Controls
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_cpu = QPushButton("🧠  Train (CPU)")
        self.btn_cpu.setFixedSize(160, 46)
        self.btn_cpu.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 {C['purple']}); 
                color: white; 
                border-radius: 6px; 
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #5a54e8;
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5a54e8, stop:1 #b043e6); }}
            QPushButton:disabled {{ background: {C['bg_input']}; color: {C['text_d']}; border: none; }}
        """)
        self.btn_cpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cpu.clicked.connect(lambda: self._start_training("cpu"))
        
        self.btn_gpu = QPushButton("🚀  Train (GPU)")
        self.btn_gpu.setFixedSize(160, 46)
        self.btn_gpu.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {C['purple']}, stop:1 #ec4899); 
                color: white; 
                border-radius: 6px; 
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #b043e6;
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b043e6, stop:1 #f45b9b); }}
            QPushButton:disabled {{ background: {C['bg_input']}; color: {C['text_d']}; border: none; }}
        """)
        self.btn_gpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gpu.clicked.connect(lambda: self._start_training("gpu"))
        
        self.btn_stop = QPushButton("⏹  Stop All")
        self.btn_stop.setFixedSize(130, 46)
        self.btn_stop.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_sidebar']}; 
                color: {C['text']}; 
                border: 1px solid {C['border']}; 
                border-radius: 6px; 
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {C['red']}22; color: {C['red']}; border: 1px solid {C['red']}; }}
            QPushButton:disabled {{ opacity: 0.5; }}
        """)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self._stop_all)
        
        btn_row.addWidget(self.btn_cpu)
        btn_row.addWidget(self.btn_gpu)
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch()
        training_layout.addLayout(btn_row)
        
        # Terminal
        # Terminal (fixed minimum height but part of long scroll)
        self.terminal = TerminalWidget()
        self.terminal.setMinimumHeight(350) 
        training_layout.addWidget(self.terminal)
        
        self.main_stack.addWidget(training_widget)
        
        # 2. Daily Operations View
        ops_widget = QWidget()
        ops_layout = QHBoxLayout(ops_widget)
        ops_layout.setContentsMargins(0, 10, 0, 0)
        ops_layout.setSpacing(20)
        
        # Left Column: Today's Runs
        left_col = QVBoxLayout()
        left_col.addWidget(self._section_header("TRAINED MODELS"))
        
        self.runs_frame = QFrame()
        self.runs_frame.setStyleSheet(f"background: {C['bg_sidebar']}; border: 1px solid {C['border']}; border-radius: 4px;")
        self.runs_layout = QVBoxLayout(self.runs_frame)
        left_col.addWidget(self.runs_frame)
        
        left_col.addSpacing(20)
        left_col.addWidget(self._section_header("QUICK DEPLOY (STANDALONE)"))
        
        self.deploy_card = QFrame()
        self.deploy_card.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 4px;")
        self.deploy_layout = QVBoxLayout(self.deploy_card)
        left_col.addWidget(self.deploy_card)
        left_col.addStretch()
        
        # Right Column: Agent Health
        right_col = QVBoxLayout()
        right_col.addWidget(self._section_header("AGENT HEALTH"))
        
        self.health_widget = QWidget()
        self.health_layout = QVBoxLayout(self.health_widget)
        self.health_layout.setContentsMargins(0, 0, 0, 0)
        right_col.addWidget(self.health_widget)
            
        right_col.addSpacing(20)
        right_col.addWidget(self._section_header("RECENT OUTPUTS"))
        
        out_card = QFrame()
        out_card.setStyleSheet(f"background: {C['bg_sidebar']}44; border: 1px solid {C['border']}; border-radius: 4px;")
        ol = QVBoxLayout(out_card)
        ol.addWidget(QLabel("No recent standalone outputs detected."))
        right_col.addWidget(out_card)
        right_col.addStretch()

        ops_layout.addLayout(left_col, 55)
        ops_layout.addLayout(right_col, 45)
        
        self.main_stack.addWidget(ops_widget)
        
        # View Toggle Connections
        self.btn_training_view.clicked.connect(lambda: (self.main_stack.setCurrentIndex(0), self.btn_ops_view.setChecked(False), self.btn_training_view.setChecked(True)))
        self.btn_ops_view.clicked.connect(lambda: (self.main_stack.setCurrentIndex(1), self.btn_training_view.setChecked(False), self.btn_ops_view.setChecked(True)))

        self.overlay = None
        
        # Main Stack - let it fit its children naturally
        root.addWidget(self.main_stack)
        
        self.scroll.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll)

        # Alert area - fixed height container to prevent layout shifting
        self.alert_container = QWidget()
        self.alert_container.setMaximumHeight(120) # Max 2-3 alerts
        self.alert_area = QVBoxLayout(self.alert_container)
        self.alert_area.setContentsMargins(0,0,0,0)
        self.alert_area.setSpacing(4)
        root.insertWidget(1, self.alert_container) # Directly below header
        
        # Load models once
        self._load_models()

    def _section_header(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text_d']}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        return l

    def show_alert(self, title, msg, type="warning"):
        alert = QFrame()
        alert.setFixedHeight(54)
        bg = C['amber'] if type == "warning" else C['status_error']
        alert.setStyleSheet(f"""
            QFrame {{
                background: {bg}33;
                border: 1px solid {bg}66;
                border-left: 5px solid {bg};
                border-radius: 6px;
            }}
            QLabel {{ color: {C['white']}; background: transparent; border: none; }}
        """)
        
        al = QHBoxLayout(alert)
        al.setContentsMargins(20, 0, 20, 0)
        al.setSpacing(12)
        
        icon = QLabel("⚠️" if type == "warning" else "🚫")
        icon.setStyleSheet("font-size: 16px;")
        al.addWidget(icon)
        
        msg_lbl = QLabel(f"<b>{title}</b> <span style='color:{C['text_d']};'>—</span> {msg}")
        msg_lbl.setStyleSheet("font-size: 13px;")
        al.addWidget(msg_lbl)
        
        al.addStretch()
        
        close = QPushButton("✕")
        close.setFixedSize(24, 24)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet(f"""
            QPushButton {{ 
                color: {C['text_d']}; 
                border: none; 
                background: transparent; 
                font-size: 14px; 
                font-weight: bold;
                border-radius: 12px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.1); color: white; }}
        """)
        close.clicked.connect(lambda: alert.deleteLater())
        al.addWidget(close)
        
        self.alert_area.addWidget(alert)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = self.width()
        
        # 1. Responsive Stats (1 row vs 2x2)
        stat_cols = 4 if width > 900 else 2
        if not hasattr(self, '_current_stat_cols') or self._current_stat_cols != stat_cols:
            self._current_stat_cols = stat_cols
            # Clear grid (don't delete widgets!)
            for i in reversed(range(self.stats_grid.count())):
                self.stats_grid.itemAt(i).widget().setParent(None)
                
            for i, item in enumerate(self.stat_items):
                row, col = i // stat_cols, i % stat_cols
                self.stats_grid.addWidget(item["frame"], row, col)

        # 2. Responsive Model Cards (3, 2, or 1 col)
        new_cols = 3
        if width < 750: new_cols = 1
        elif width < 1100: new_cols = 2
        
        if hasattr(self, '_current_cols') and self._current_cols == new_cols:
            return
            
        self._current_cols = new_cols
        self._realign_model_cards(new_cols)

    def _realign_model_cards(self, cols):
        """Rearrange existing model cards into new grid columns."""
        if not self._cards: return
        
        # Clear grid (don't delete widgets!)
        for i in reversed(range(self.cards_grid.count())):
            self.cards_grid.itemAt(i).widget().setParent(None)
            
        for i, card in enumerate(self._cards.values()):
            row, col = i // cols, i % cols
            self.cards_grid.addWidget(card, row, col)

    def _load_models(self):
        """Populate model cards once."""
        if self._cards: return # Don't re-load if already populated
        self.refresh_models()

    def refresh_models(self):
        """Reload models from disk and update cards."""
        
        from backend.core.model_manager import list_models
        from backend.data.label_manager import LabelManager
        models = list_models()
        self.btn_cpu.setEnabled(len(models) > 0)
        self.btn_gpu.setEnabled(len(models) > 0)

        # Calculate live stats
        trained_count = 0
        for m in models:
            lm = LabelManager(m['name'])
            if lm.is_compiled() or m.get("status") == "trained":
                trained_count += 1

        # Build dynamic Top Stats bar
        if hasattr(self, "stat_items") and len(self.stat_items) >= 2:
            self.stat_items[0]["val_lbl"].setText(str(len(models)))     # TOTAL MODELS
            self.stat_items[1]["val_lbl"].setText(str(trained_count))   # TRAINED Models
        
        # Clear existing cards from grid but keep references if they still exist
        for i in reversed(range(self.cards_grid.count())):
            self.cards_grid.itemAt(i).widget().setParent(None)
        
        new_cards = {}
        for m in models:
            name = m['name']
            if name in self._cards:
                new_cards[name] = self._cards[name]
            else:
                card = ModelCard(name)
                card.action_clicked.connect(self._on_model_action)
                
                lm = LabelManager(name)
                stats = lm.get_stats()
                if lm.is_compiled():
                    card.update_status("trained", stats.get("pct_complete", 0), 0)
                elif stats.get("labeled", 0) > 0:
                    card.update_status("training", stats.get("pct_complete", 0), 0)
                else:
                    card.update_status("untrained", 0, 0)
                    
                new_cards[name] = card
        
        self._cards = new_cards
        
        # Initial alignment based on window width
        cols = 3
        width = self.width()
        if width < 750: cols = 1
        elif width < 1100: cols = 2
        self._current_cols = cols
        self._realign_model_cards(cols)
        
        self._refresh_daily_ops(models)

    def _refresh_daily_ops(self, models):
        # Clear existing
        for layout in [self.runs_layout, self.deploy_layout, self.health_layout]:
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item.widget():
                    item.widget().setParent(None)

        trained_models = [m for m in models if m["status"] == "trained" or m["score"] > 0]
        
        # 1. Trained Models (Runs)
        if not trained_models:
            self.runs_layout.addWidget(QLabel("No trained models yet."))
        else:
            for m in trained_models:
                row = QHBoxLayout()
                score = m["score"]
                icon = QLabel("✓" if score > 50 else "⚠️")
                icon.setStyleSheet(f"color: {C['green'] if score > 50 else C['amber']}; font-weight: bold;")
                row.addWidget(icon)
                row.addWidget(QLabel(m["name"]), 1)
                row.addWidget(QLabel(f"{score:.1f}pts"))
                btn = QPushButton("Open Config")
                btn.setFixedSize(90, 26)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {C['purple_l']}; 
                        font-size: 11px; 
                        font-weight: bold;
                        border: 1px solid {C['purple_l']}44;
                        border-radius: 4px;
                        background: transparent;
                    }}
                    QPushButton:hover {{ background: {C['purple_l']}22; border: 1px solid {C['purple_l']}; }}
                """)
                from backend.core.model_manager import load_model_config
                btn.clicked.connect(lambda checked, n=m["name"]: import_and_open_json(n))
                row.addWidget(btn)
                self.runs_layout.addLayout(row)

        def import_and_open_json(name):
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            from pathlib import Path
            path = Path("models") / name / "config.json"
            if path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
                
        # 2. Quick Deploy (Standalone)
        if not trained_models:
            self.deploy_layout.addWidget(QLabel("Train a model first to unlock Standalone Agent extraction."))
        else:
            from PyQt6.QtWidgets import QComboBox
            self.deploy_combo = QComboBox()
            for m in trained_models:
                self.deploy_combo.addItem(f"{m['name']} ({m['score']:.1f} pts)", m["name"])
            
            self.deploy_layout.addWidget(QLabel("Select Model to Export:"))
            self.deploy_layout.addWidget(self.deploy_combo)
            
            run_btn = QPushButton("📦 Export Agent Bundle")
            run_btn.setFixedHeight(46)
            run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            run_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C['purple']}; 
                    color: white; 
                    border-radius: 6px; 
                    font-weight: bold;
                    font-size: 13px;
                }}
                QPushButton:hover {{ background: {C['purple_l']}; }}
            """)
            run_btn.clicked.connect(self._on_quick_deploy)
            self.deploy_layout.addWidget(run_btn)

        # 3. Agent Health (Progress bars)
        if not models:
            self.health_layout.addWidget(QLabel("No models found."))
        else:
            for m in models:
                h_row = QVBoxLayout()
                h_row.addWidget(QLabel(f"{m['name']}  ·  {m['score']:.1f}%"))
                pb = QProgressBar()
                pb.setFixedHeight(4)
                pb.setRange(0, 100)
                pb.setValue(int(m["score"]))
                pb.setTextVisible(False)
                pb.setStyleSheet(f"QProgressBar::chunk {{ background: {C['green'] if m['score'] > 70 else C['amber']}; }}")
                h_row.addWidget(pb)
                self.health_layout.addLayout(h_row)
                self.health_layout.addSpacing(10)

        # 4. Dynamic Alerts
        # Clear existing alerts first
        for i in reversed(range(self.alert_area.count())):
            item = self.alert_area.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
                
        for m in models:
            if 0 < m['score'] < 50:
                self.show_alert("Low Confidence", f"Model '{m['name']}' is struggling to learn (Best Score: {m['score']:.1f}%). Adjust curriculum layers.", "warning")

    def _on_quick_deploy(self):
        if not hasattr(self, "deploy_combo"): return
        
        model_name = self.deploy_combo.currentData()
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from backend.core.standalone_exporter import StandaloneExporter
        
        out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if out_dir:
            self.terminal.append(f"📦 Packaging {model_name}...", "warning")
            success = StandaloneExporter(model_name, None).export(out_dir)
            if success:
                self.terminal.append(f"✓ Extracted correctly to {out_dir}", "success")
                QMessageBox.information(self, "Exported", f"Successfully packaged {model_name} to:\n{out_dir}")
            else:
                self.terminal.append(f"❌ Failed to extract {model_name}.", "error")

    def _on_new_model(self):
        """Show the modal creation dialog and call backend."""
        from backend.core.model_manager import create_model
        dlg = CreateModelDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            if data["name"]:
                success = create_model(
                    model_name=data["name"],
                    description=data["description"],
                    tasks=data["tasks"],
                    outputs=data["outputs"]
                )
                if success:
                    self.terminal.append(f"✨  Created new model: <b>{data['name']}</b>", "success")
                    self.terminal.append(f"📁  Initialized folder structure and config.json in models/{data['name']}/", "info")
                    # Refresh BOTH dashboard and sidebar
                    self.refresh_models()
                    # Also notify parent/main_window if it needs to refresh sidebar
                    if self.window() and hasattr(self.window(), "refresh_sidebar"):
                        self.window().refresh_sidebar()
                else:
                    self.terminal.append(f"❌  Failed to create model: {data['name']}", "error")
            else:
                self.terminal.append("⚠️  Model creation cancelled (no name provided).", "warning")

    def _start_training(self, mode: str):
        """Start training on selected models only."""
        selected_cards = [c for c in self._cards.values() if c.is_selected()]
        
        if not selected_cards:
            QMessageBox.warning(self, "No Selection", "Please select at least one model to train.")
            return

        # Get device from settings
        device_id   = settings.get("compute_device_id", "cpu")
        device_name = settings.get("compute_device_name", "CPU")
        device_type = settings.get("compute_device_type", "cpu")
        
        if mode == "cpu":
            # Force CPU regardless of settings
            device = ComputeDevice(
                id="cpu",
                name="CPU",
                device_type="cpu",
                memory_mb=0,
                available=True,
                description="CPU training",
                tf_device_string="/CPU:0"
            )
            self.terminal.append("Starting selective training on CPU...")
        else:
            if device_type == "cpu":
                self.terminal.append(
                    "⚠ No GPU selected in Settings. Configure a GPU first.", "warning"
                )
                return
            device = ComputeDevice(
                id=device_id,
                name=device_name,
                device_type=device_type,
                memory_mb=0,
                available=True,
                description=f"{device_type.upper()} training",
                tf_device_string="/GPU:0"
            )
            self.terminal.append(f"Starting selective training on GPU ({device_name})...")

        for card in selected_cards:
            name = card.model_name
            self.terminal.append(f"▶ Initializing training for: {name}", "best")
            card.update_status("training", card._score, card._attempts)
            
            if name not in self._workers:
                from backend.core.model_manager import load_model_config
                actual_cfg = load_model_config(name)
                
                worker = TrainingWorker(
                    model_config=actual_cfg,
                    training_config=actual_cfg.get("train_config", {"mode": "self_improving"}),
                    scoring_config=actual_cfg.get("scoring_config", {"mode": "auto"}),
                    device_string=device.tf_device_string if device else "/CPU:0"
                )
                worker.log_line.connect(self._on_log)
                worker.status_update.connect(self._on_status)
                worker.attempt_done.connect(self._on_attempt)
                worker.training_finished.connect(self._on_finished)
                self._workers[name] = worker
                worker.start()
        
        # Show overlay
        if not self.overlay:
            self.overlay = TrainingOverlay()
            self.overlay.show()
            self.overlay.move(self.window().x() + self.window().width() - 220, self.window().y() + 60)

        # Update button states
        self.btn_cpu.setEnabled(False)
        self.btn_gpu.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def _stop_all(self):
        for worker in self._workers.values():
            worker.stop()
        self._workers.clear()
        self.btn_cpu.setEnabled(True)
        self.btn_gpu.setEnabled(True)
        self.terminal.append("All training stopped.", "warning")
        if self.overlay:
            self.overlay.hide()
            self.overlay = None

    def _on_model_action(self, name: str, action: str):
        """Handle individual model action buttons."""
        if action == "stop":
            if name in self._workers:
                self._workers[name].stop()
                del self._workers[name]
                self.terminal.append(f"⏹  Training stopped for model: {name}", "warning")
            if name in self._cards:
                c = self._cards[name]
                c.update_status("untrained", c._score, c._attempts)
                c.set_selected(False)
        elif action == "pause":
            self.terminal.append(f"⏯  Pause/Resume for '{name}' requested (Control Logic WIP)", "info")

    def _on_log(self, model_name: str, line: str):
        self.terminal.append(line)

    def _on_status(self, status: dict):
        name = status.get("model_name", "")
        if name in self._cards:
            score    = status.get("best_score", 0)
            attempts = status.get("iteration", 0)
            self._cards[name].update_status("training", score, attempts)

    def _on_attempt(self, name: str, score: float, attempt: int):
        if name in self._cards:
            self._cards[name].update_status("training", score, attempt)

    def _on_finished(self, name: str, reason: str = "manual"):
        if name in self._workers:
            del self._workers[name]
        if name in self._cards:
            self._cards[name].update_status("trained", self._cards[name]._score, self._cards[name]._attempts)
        self.terminal.append(f"✓ Training finished for '{name}': {reason}", "success")
        if not self._workers:
            self.btn_cpu.setEnabled(True)
            self.btn_gpu.setEnabled(True)
            if self.overlay:
                self.overlay.hide()
                self.overlay = None
