"""
Main view for managing and launching existing macros.
Shows recent runs and available templates.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QSplitter, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon

from backend.macro.manager import list_macros, load_macro, delete_macro
from backend.macro.live_run_tracker import tracker
from backend.macro.worker import MacroWorker
from app.dialogs.macro_launch_dialog import MacroLaunchDialog
from app.theme import C

class MacroDashboardPage(QWidget):
    # Emitted to tell MainWindow to switch to the Builder tab
    request_builder = pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._build_ui()
        self.refresh_data()
        
        # Auto-refresh history periodically if a macro is running
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh_history)
        self.refresh_timer.start(2000)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.scroll_content = QWidget()
        root = QVBoxLayout(self.scroll_content)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        # ── Header ──────────────────────────────────────────
        header_row = QHBoxLayout()
        left = QVBoxLayout()
        title_row = QHBoxLayout()
        icon = QLabel("⚙")
        icon.setStyleSheet(f"color: {C['purple_l']}; font-size: 24px;")
        
        title = QLabel("Macro Operations")
        title.setStyleSheet(f"color: {C['white']}; font-size: 24px; font-weight: bold;")
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()
        
        subtitle = QLabel("Launch, manage, and monitor your automated macro pipelines.")
        subtitle.setStyleSheet(f"color: {C['text']}; font-size: 13px;")
        
        left.addLayout(title_row)
        left.addWidget(subtitle)
        
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedSize(100, 36)
        self.btn_refresh.setStyleSheet(f"background: {C['bg_sidebar']}; color: {C['white']}; border: 1px solid {C['border']}; border-radius: 4px; font-weight: bold;")
        self.btn_refresh.clicked.connect(self.refresh_data)
        
        self.btn_new = QPushButton("✚ New Macro")
        self.btn_new.setFixedSize(140, 36)
        self.btn_new.setStyleSheet(f"background: {C['purple']}; color: white; border-radius: 4px; font-weight: bold;")
        self.btn_new.clicked.connect(lambda: self.request_builder.emit(""))
        
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_new)
        
        header_row.addLayout(left)
        header_row.addStretch()
        header_row.addLayout(btn_layout)
        
        root.addLayout(header_row)
        root.addSpacing(10)

        # ── Content Splitter ────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {C['border']}; }}")
        
        # LEFT: Library Panel
        lib_widget = QWidget()
        lib_layout = QVBoxLayout(lib_widget)
        lib_layout.setContentsMargins(0, 0, 10, 0)
        lib_layout.setSpacing(12)
        
        lbl_lib = QLabel("MACRO LIBRARY")
        lbl_lib.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        lib_layout.addWidget(lbl_lib)
        
        self.macro_list = QListWidget()
        self.macro_list.setStyleSheet(f"""
            QListWidget {{
                background: {C['bg_sidebar']}44;
                border: 1px solid {C['border']};
                border-radius: 6px;
                color: {C['white']};
                font-size: 14px;
            }}
            QListWidget::item {{
                padding: 16px;
                border-bottom: 1px solid {C['border']};
            }}
            QListWidget::item:selected {{
                background: {C['purple']}44;
                color: {C['white']};
                border-left: 4px solid {C['purple']};
            }}
            QListWidget::item:hover:!selected {{
                background: {C['bg_sidebar']};
            }}
        """)
        self.macro_list.itemSelectionChanged.connect(self.on_macro_selected)
        lib_layout.addWidget(self.macro_list)
        
        # Action Buttons
        act_row = QHBoxLayout()
        self.btn_run = QPushButton("▶ Run")
        self.btn_run.setFixedHeight(40)
        self.btn_run.setStyleSheet(f"background: {C['green']}; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self.on_run_clicked)
        
        self.btn_edit = QPushButton("✎ Edit")
        self.btn_edit.setFixedHeight(40)
        self.btn_edit.setStyleSheet(f"background: {C['bg_sidebar']}; color: white; border: 1px solid {C['border']}; border-radius: 4px;")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self.on_edit_clicked)
        
        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setFixedHeight(40)
        self.btn_delete.setStyleSheet(f"background: transparent; color: {C['status_error']}; border: 1px solid {C['status_error']}; border-radius: 4px;")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        
        act_row.addWidget(self.btn_run, 4)
        act_row.addWidget(self.btn_edit, 3)
        act_row.addWidget(self.btn_delete, 3)
        lib_layout.addLayout(act_row)
        
        # RIGHT: History Panel
        hist_widget = list_wrapper = QFrame()
        hist_widget.setStyleSheet(f"background: {C['bg_sidebar']}22; border: 1px solid {C['border']}; border-radius: 6px;")
        hist_layout = QVBoxLayout(hist_widget)
        hist_layout.setContentsMargins(16, 16, 16, 16)
        hist_layout.setSpacing(12)
        
        lbl_hist = QLabel("RUN HISTORY & EVENTS")
        lbl_hist.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; font-weight: bold; letter-spacing: 1px; border: none; background: transparent;")
        hist_layout.addWidget(lbl_hist)
        
        self.hist_table = QTableWidget(0, 4)
        self.hist_table.setHorizontalHeaderLabels(["Time", "Level", "Node", "Message"])
        self.hist_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.hist_table.verticalHeader().setVisible(False)
        self.hist_table.setShowGrid(False)
        self.hist_table.setAlternatingRowColors(True)
        self.hist_table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent;
                color: {C['text_b']};
                border: none;
                font-size: 12px;
                alternate-background-color: {C['bg_sidebar']}44;
            }}
            QHeaderView::section {{
                background: {C['bg_sidebar']};
                color: {C['text_d']};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {C['border']};
                font-weight: bold;
                text-align: left;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                border-bottom: 1px solid {C['bg_sidebar']};
            }}
        """)
        hist_layout.addWidget(self.hist_table)
        
        splitter.addWidget(lib_widget)
        splitter.addWidget(hist_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        
        root.addWidget(splitter)
        
        # Fit to scroll area
        self.scroll.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll)

    def refresh_data(self):
        self.macro_list.clear()
        macros = list_macros()
        
        if not macros:
            item = QListWidgetItem("No macros found. Create one!")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
            self.macro_list.addItem(item)
        else:
            for m in macros:
                item = QListWidgetItem(f"📄  {m['name']}\n      {m['node_count']} nodes")
                item.setData(Qt.ItemDataRole.UserRole, m['id'])
                self.macro_list.addItem(item)
            
        self._refresh_history()

    def _auto_refresh_history(self):
        if self.worker and self.worker.isRunning():
            self._refresh_history()

    def _refresh_history(self):
        events = tracker.get_recent_events(100)
        self.hist_table.setRowCount(len(events))
        from datetime import datetime
        
        for i, ev in enumerate(reversed(events)):
            ts = datetime.fromtimestamp(ev['timestamp']).strftime("%H:%M:%S")
            lvl = ev['level'].upper()
            
            # Color coding the level
            color = C['text']
            if lvl == "ERROR": color = C['status_error']
            elif lvl == "WARNING": color = C['amber']
            elif lvl in ("SUCCESS", "ACTION"): color = C['green']
            
            itm_ts = QTableWidgetItem(ts)
            itm_ts.setForeground(Qt.GlobalColor.gray)
            
            itm_lvl = QTableWidgetItem(lvl)
            itm_lvl.setStyleSheet(f"color: {color}; font-weight: bold;")
            
            itm_node = QTableWidgetItem(ev['node_id'] or "-")
            itm_node.setForeground(Qt.GlobalColor.gray)
            
            itm_msg = QTableWidgetItem(ev['message'])
            if lvl in ("ERROR", "SUCCESS"):
                itm_msg.setStyleSheet(f"color: {color};")
                
            self.hist_table.setItem(i, 0, itm_ts)
            self.hist_table.setItem(i, 1, itm_lvl)
            self.hist_table.setItem(i, 2, itm_node)
            self.hist_table.setItem(i, 3, itm_msg)

    def on_macro_selected(self):
        sel = self.macro_list.selectedItems()
        has_sel = len(sel) > 0 and sel[0].data(Qt.ItemDataRole.UserRole) is not None
        
        self.btn_run.setEnabled(has_sel)
        self.btn_edit.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)

    def on_delete_clicked(self):
        sel = self.macro_list.selectedItems()
        if not sel: return
        m_id = sel[0].data(Qt.ItemDataRole.UserRole)
        
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Macro")
        dlg.setText("Are you sure you want to permanently delete this macro?")
        dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dlg.setDefaultButton(QMessageBox.StandardButton.No)
        dlg.setStyleSheet(f"background: {C['bg_modal']}; color: {C['text']};")
        
        if dlg.exec() == QMessageBox.StandardButton.Yes:
            delete_macro(m_id)
            self.refresh_data()

    def on_edit_clicked(self):
        sel = self.macro_list.selectedItems()
        if not sel: return
        m_id = sel[0].data(Qt.ItemDataRole.UserRole)
        self.request_builder.emit(m_id)

    def on_run_clicked(self):
        sel = self.macro_list.selectedItems()
        if not sel: return
        m_id = sel[0].data(Qt.ItemDataRole.UserRole)
        
        m_data = load_macro(m_id)
        if not m_data:
            QMessageBox.critical(self, "Error", "Could not load macro data.")
            return
            
        dlg = MacroLaunchDialog(m_data, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            vars = dlg.get_variables()
            self._start_worker(m_data, vars)

    def _start_worker(self, macro_data: dict, init_vars: dict):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "A macro is already running.")
            return

        tracker.start_run(macro_data.get('name', 'Macro'), macro_data.get('id', 'temp'))
        
        self.worker = MacroWorker(
            macro_data=macro_data, 
            init_context=init_vars,
            dry_run=init_vars.get("dry_run", False)
        )
        self.worker.log_msg.connect(tracker.log_event)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()
        
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Running...")
        self.btn_run.setStyleSheet(f"background: {C['amber']}; color: black; font-weight: bold; border-radius: 4px;")

    def _on_worker_finished(self, success: bool, results: dict):
        tracker.stop_run(success, results.get("error", ""))
        self.btn_run.setText("▶ Run")
        self.btn_run.setStyleSheet(f"background: {C['green']}; color: white; font-weight: bold; border-radius: 4px;")
        
        self.on_macro_selected() # re-evaluate enable state
        self._refresh_history()
        
        if not success:
            QMessageBox.critical(self, "Macro Failed", f"Execution failed:\n{results.get('error')}")
