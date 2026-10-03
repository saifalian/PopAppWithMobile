from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QGroupBox, QFrame, QScrollArea, QSplitter,
    QComboBox, QCheckBox, QListWidget, QInputDialog, QMessageBox,
    QGridLayout, QSizePolicy, QListWidgetItem, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRect, QSize
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont

from app.theme import C
from app.core.device_monitor import DeviceMonitorWorker
from app.widgets.common import SectionHeader
from app.widgets.overlay import SelectionOverlay

class ClickOnlyComboBox(QComboBox):
    """QComboBox that ignores mouse wheel events to prevent accidental changes."""
    def wheelEvent(self, event):
        event.ignore()

class CalibrationActionItem(QFrame):
    """A single item in the PC calibration action list."""
    rename_requested = pyqtSignal(str)
    delete_requested = pyqtSignal()
    move_up_requested = pyqtSignal()
    move_down_requested = pyqtSignal()
    delay_changed = pyqtSignal(int)  # delay in ms

    DEFAULT_DELAY_MS = 1000

    def __init__(self, index, action_data):
        super().__init__()
        self.setFixedHeight(34)
        self.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 4px;")
        self._delay_ms = action_data.get("delay", self.DEFAULT_DELAY_MS)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(4)

        # 1. Index / Number
        idx_lbl = QLabel(str(index))
        idx_lbl.setFixedWidth(18)
        idx_lbl.setStyleSheet(f"color: {C['purple_l']}; font-weight: bold; font-size: 11px;")
        layout.addWidget(idx_lbl)

        # 2. Name
        self.name_lbl = QLabel(action_data.get("name", f"Action {index}"))
        self.name_lbl.setStyleSheet("font-size: 11px; color: white;")
        layout.addWidget(self.name_lbl, 1)

        # 3. Delay button  ⏱ 1.0s
        self.delay_btn = QPushButton(self._fmt_delay(self._delay_ms))
        self.delay_btn.setFixedSize(48, 20)
        self.delay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delay_btn.setToolTip("Click to set delay after this action (ms)")
        self.delay_btn.setStyleSheet(
            f"background: {C['bg_darkest']}; color: {C['amber']}; "
            f"border: 1px solid {C['amber']}44; border-radius: 3px; font-size: 9px; font-weight: bold;"
        )
        self.delay_btn.clicked.connect(self._on_set_delay)
        layout.addWidget(self.delay_btn)

        # 4. Action buttons (Rename, Delete, Reorder)
        def btn(txt, color, slot):
            b = QPushButton(txt)
            b.setFixedSize(20, 20)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"background: transparent; color: {color}; border: none; font-size: 11px;")
            b.clicked.connect(slot)
            return b

        layout.addWidget(btn("✏️", C['text_d'], self._on_rename))
        layout.addWidget(btn("🗑️", C['red'], self.delete_requested.emit))

        self.up_btn = btn("🔼", C['text_d'], self.move_up_requested.emit)
        self.down_btn = btn("🔽", C['text_d'], self.move_down_requested.emit)
        layout.addWidget(self.up_btn)
        layout.addWidget(self.down_btn)

    @staticmethod
    def _fmt_delay(ms: int) -> str:
        return f"⏱ {ms / 1000:.1f}s"

    def _on_set_delay(self):
        from PyQt6.QtWidgets import QInputDialog
        val, ok = QInputDialog.getInt(
            self, "Set Delay",
            "Delay after this action (milliseconds):\n(Default: 1000 ms = 1 second)",
            value=self._delay_ms, min=0, max=30000, step=100
        )
        if ok:
            self._delay_ms = val
            self.delay_btn.setText(self._fmt_delay(val))
            self.delay_changed.emit(val)

    def _on_rename(self):
        new_name, ok = QInputDialog.getText(self, "Rename Action", "New name for this step:", text=self.name_lbl.text())
        if ok and new_name:
            self.rename_requested.emit(new_name)


class RegionActionItem(QFrame):
    """A single item in the Focus Areas list."""
    rename_requested = pyqtSignal(str)
    delete_requested = pyqtSignal()
    visibility_toggled = pyqtSignal(bool)

    def __init__(self, index, region_data):
        super().__init__()
        self.setFixedHeight(34)
        self.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 4px;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(4)

        # 1. Visibility (Eye)
        self.visible = region_data.get("visible", True)
        self.eye_btn = QPushButton("👁️" if self.visible else "🙈")
        self.eye_btn.setFixedSize(24, 24)
        self.eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eye_btn.setStyleSheet("background: transparent; border: none; font-size: 14px;")
        self.eye_btn.clicked.connect(self._on_toggle_visibility)
        layout.addWidget(self.eye_btn)

        # 2. Name
        self.name_lbl = QLabel(region_data.get("name", f"Region {index}"))
        self.name_lbl.setStyleSheet("font-size: 11px; color: white;")
        layout.addWidget(self.name_lbl, 1)

        # 3. Action buttons
        def btn(txt, color, slot):
            b = QPushButton(txt)
            b.setFixedSize(20, 20)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"background: transparent; color: {color}; border: none; font-size: 11px;")
            b.clicked.connect(slot)
            return b

        layout.addWidget(btn("✏️", C['text_d'], self._on_rename))
        layout.addWidget(btn("🗑️", C['red'], self.delete_requested.emit))

    def _on_rename(self):
        new_name, ok = QInputDialog.getText(self, "Rename Region", "New name for this area:", text=self.name_lbl.text())
        if ok and new_name:
            self.name_lbl.setText(new_name)
            self.rename_requested.emit(new_name)

    def _on_toggle_visibility(self):
        self.visible = not self.visible
        self.eye_btn.setText("👁️" if self.visible else "○")
        self.visibility_toggled.emit(self.visible)

class DeviceTab(QWidget):
    config_changed = pyqtSignal(dict)
    calibrate_requested = pyqtSignal()
    action_rename_requested = pyqtSignal(int, str)
    action_delete_requested = pyqtSignal(int)
    action_move_requested = pyqtSignal(int, int)   # (index, direction)
    action_delay_changed = pyqtSignal(int, int)    # (index, delay_ms)
    takeover_requested = pyqtSignal()
    mirror_pause_requested = pyqtSignal()
    mirror_resume_requested = pyqtSignal()
    clicked_pos = pyqtSignal(int, int)             # USER manually clicked preview (Triggers ADB)
    show_ripple_pos = pyqtSignal(int, int)         # INTERNAL request to show visual dot (No ADB)
    focus_config_changed = pyqtSignal(dict)
    define_pc_region_requested = pyqtSignal()
    test_calibration_requested = pyqtSignal()
    fullscreen_requested = pyqtSignal(bool)
    captured_native_pos = pyqtSignal(int, int) # x, y on the phone's resolution
    
    def __init__(self, mobile_mgr, parent=None):
        super().__init__(parent)
        self.mobile_mgr = mobile_mgr
        self.model_name = ""
        self._is_selecting = False
        self._start_pos = None
        self._current_rect = QRect()
        self._regions = [] # List of dicts {"x1", "y1", "x2", "y2"}
        
        # Performance Cache
        self._cached_screen_pw = 1920
        self._cached_screen_ph = 1080
        self._cached_mobile_mw = 1080
        self._cached_mobile_mh = 1920
        self._update_resolution_cache()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(10)
        
        # --- TOP: CONNECTION STATUS CARD (P1) ---
        self.status_card = QFrame()
        self.status_card.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 8px;")
        self.status_card.setFixedHeight(90)
        sl = QHBoxLayout(self.status_card)
        sl.setContentsMargins(20, 10, 20, 10)
        
        # Info Column
        info_vbox = QVBoxLayout()
        self.lbl_model = QLabel("No Device Connected")
        self.lbl_model.setStyleSheet(f"color: {C['white']}; font-size: 16px; font-weight: bold; border: none;")
        self.lbl_serial = QLabel("Waiting for ADB link...")
        self.lbl_serial.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; border: none;")
        info_vbox.addWidget(self.lbl_model)
        info_vbox.addWidget(self.lbl_serial)
        sl.addLayout(info_vbox)
        
        sl.addStretch()
        
        # Stats Grid
        stats_grid = QGridLayout()
        stats_grid.setSpacing(15)
        
        self.stat_battery = self._create_mini_stat("BATTERY", "0%", C['green'])
        self.stat_temp = self._create_mini_stat("TEMP", "N/C", C['amber'])
        self.stat_ping = self._create_mini_stat("PING", "N/A", C['cyan'])
        self.stat_storage = self._create_mini_stat("STORAGE", "N/A", C['text_d'])
        
        stats_grid.layout().addWidget(self.stat_battery, 0, 0)
        stats_grid.layout().addWidget(self.stat_temp, 0, 1)
        stats_grid.layout().addWidget(self.stat_ping, 1, 0)
        stats_grid.layout().addWidget(self.stat_storage, 1, 1)
        sl.addLayout(stats_grid)
        
        # Action Column
        act_vbox = QVBoxLayout()
        self.btn_link = QPushButton("🚀 LINK MOBILE")
        self.btn_link.setFixedHeight(30)
        self.btn_link.setStyleSheet(f"background: {C['bg_sidebar']}; color: {C['cyan']}; border: 1px solid {C['cyan']}; border-radius: 4px; font-weight: bold; font-size: 10px; padding: 0 10px;")
        self.btn_link.clicked.connect(self._on_link_clicked)
        
        self.btn_release = QPushButton("🛑 RELEASE")
        self.btn_release.setFixedHeight(25)
        self.btn_release.setStyleSheet(f"background: {C['red']}11; color: {C['red']}; border: 1px solid {C['red']}; border-radius: 4px; font-size: 9px;")
        self.btn_release.clicked.connect(self._on_release_clicked)
        
        act_vbox.addWidget(self.btn_link)
        act_vbox.addWidget(self.btn_release)
        sl.addLayout(act_vbox)
        
        main_layout.addWidget(self.status_card)
        
        self.monitor_worker = None
        
        # --- MIDDLE: PREVIEW & PERF MONITOR (P5) ---
        self.mid_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.mid_splitter.setHandleWidth(1)
        
        # Left: Preview Area
        preview_container = QWidget()
        pv = QVBoxLayout(preview_container)
        pv.setContentsMargins(0, 0, 0, 0)
        
        self.ctrl_bar = QWidget()
        ctrl_layout = QHBoxLayout(self.ctrl_bar)
        ctrl_layout.setContentsMargins(10, 5, 10, 5)
        ctrl_layout.setSpacing(10)
        
        self.combo_res = QComboBox()
        self.combo_res.addItems(["Native", "1080p", "720p", "480p (Turbo)"])
        self.combo_res.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px; font-size: 10px;")
        
        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["60 FPS", "30 FPS", "15 FPS"])
        self.combo_fps.setCurrentIndex(1)
        self.combo_fps.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px; font-size: 10px;")
        
        ctrl_layout.addWidget(SectionHeader("VIEWPORT:"), 0)
        ctrl_layout.addWidget(self.combo_res)
        ctrl_layout.addWidget(self.combo_fps)
        ctrl_layout.addStretch()
        
        self.btn_shot = QPushButton("📸 Shot")
        self.btn_shot.setFixedSize(60, 22)
        self.btn_shot.setStyleSheet(f"background: {C['bg_panel']}; color: {C['white']}; border: 1px solid {C['border']}; border-radius: 3px; font-size: 10px;")
        ctrl_layout.addWidget(self.btn_shot)
        
        pv.addWidget(self.ctrl_bar)
        self.pv_layout = pv # Save ref
        
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet(f"background: #000; border: 1px solid {C['border']}; border-radius: 4px;")
        self.p_layout = QVBoxLayout(self.preview_frame); self.p_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_lbl = QLabel("Initializing stream...")
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setStyleSheet("color: #333; font-style: italic;")
        self.preview_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored) # Prevents pixmap from expanding layout
        self.p_layout.addWidget(self.preview_lbl)
        pv.addWidget(self.preview_frame, 1) # ADDED STRETCH FACTOR (1)
        
        # --- FULLSCREEN OVERLAY BUTTONS (Bottom-Right) ---
        self.btn_enter_fs = QPushButton("⛶ FULL", self.preview_frame)
        self.btn_enter_fs.setFixedSize(65, 26)
        self.btn_enter_fs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_enter_fs.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_darkest']}cc; 
                color: {C['cyan']}; 
                border: 1px solid {C['cyan']}44; 
                border-top-left-radius: 6px;
                font-weight: bold; 
                font-size: 9px;
            }}
            QPushButton:hover {{ background: {C['bg_sidebar']}; border-color: {C['cyan']}; }}
        """)
        self.btn_enter_fs.clicked.connect(lambda: self.fullscreen_requested.emit(True))
        
        self.btn_exit_fs = QPushButton("✖ EXIT", self.preview_frame)
        self.btn_exit_fs.setFixedSize(65, 26)
        self.btn_exit_fs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit_fs.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_darkest']}cc; 
                color: {C['red']}; 
                border: 1px solid {C['red']}44; 
                border-top-left-radius: 6px;
                font-weight: bold; 
                font-size: 9px;
            }}
            QPushButton:hover {{ background: {C['bg_sidebar']}; border-color: {C['red']}; }}
        """)
        self.btn_exit_fs.clicked.connect(lambda: self.fullscreen_requested.emit(False))
        self.btn_exit_fs.hide()
        
        # --- PREVIEW SELECTION OVERLAY (For Mobile Drawing) ---
        self.selection_overlay = SelectionOverlay(self.preview_frame)
        self.selection_overlay.hide()
        
        self.mid_splitter.addWidget(preview_container)
        
        # Right: Performance sidebar (P5)
        self.perf_panel = QFrame()
        self.perf_panel.setFixedWidth(200)
        self.perf_panel.setStyleSheet(f"background: {C['bg_sidebar']}; border-left: 1px solid {C['border']};")
        pl = QVBoxLayout(self.perf_panel)
        
        pl.addWidget(SectionHeader("Vision Focus"))
        pl.addWidget(QLabel("Source Device:"))
        self.combo_source = ClickOnlyComboBox()
        self.combo_source.addItems(["PC Screen", "Mobile Device"])
        self.combo_source.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['text']}; border: 1px solid {C['border']};")
        self.combo_source.currentIndexChanged.connect(self._on_source_index_changed)
        pl.addWidget(self.combo_source)

        pl.addWidget(SectionHeader("Performance Monitor"))
        self.cpu_bar = self._create_perf_bar("CPU Utilization", C['cyan'])
        self.ram_bar = self._create_perf_bar("RAM (Available)", C['purple_l'])
        pl.addWidget(self.cpu_bar)
        pl.addWidget(self.ram_bar)
        
        # --- CLICK FEEDBACK DOT ---
        self.click_dot = QFrame(self.preview_frame)
        self.click_dot.setFixedSize(20, 20)
        self.click_dot.setStyleSheet(f"background: {C['cyan']}; border: 2px solid white; border-radius: 10px;")
        self.click_dot.hide()
        self.click_dot_timer = QTimer(self)
        self.click_dot_timer.setSingleShot(True)
        self.click_dot_timer.timeout.connect(self.click_dot.hide)
        
        # Connect both signals to show the visual dot on the PC preview
        self.clicked_pos.connect(self._show_click_dot)
        self.show_ripple_pos.connect(self._show_click_dot)
        
        # --- PREVIEW OVERLAY FOR DRAWING ---
        
        pl.addWidget(SectionHeader("App Context"))
        self.lbl_app = QLabel("Foreground: None")
        self.lbl_app.setWordWrap(True)
        self.lbl_app.setStyleSheet(f"color: {C['text']}; font-size: 11px; padding: 5px; background: {C['bg_darkest']}; border-radius: 4px;")
        pl.addWidget(self.lbl_app)
        
        pl.addWidget(SectionHeader("Setup Actions"))
        self.btn_calibrate = QPushButton("📐 CALIBRATION")
        self.btn_calibrate.setFixedHeight(34)
        self.btn_calibrate.setStyleSheet(f"background: transparent; color: {C['purple_l']}; border: 1px solid {C['purple_d']}; border-radius: 4px; font-weight: bold; font-size: 10px;")
        self.btn_calibrate.clicked.connect(self.calibrate_requested.emit)
        pl.addWidget(self.btn_calibrate)
        
        # --- PC CALIBRATION ACTIONS LIST ---
        self.pc_actions_group = QWidget()
        pal = QVBoxLayout(self.pc_actions_group)
        pal.setContentsMargins(0, 5, 0, 0)
        pal.setSpacing(5)
        pal.addWidget(SectionHeader("Calibration Actions (PC)"))
        self.pc_actions_list = QWidget()
        self.pc_actions_layout = QVBoxLayout(self.pc_actions_list)
        self.pc_actions_layout.setContentsMargins(0,0,0,0)
        self.pc_actions_layout.setSpacing(4)
        self.pc_actions_scroll = QScrollArea()
        self.pc_actions_scroll.setWidgetResizable(True)
        self.pc_actions_scroll.setFixedHeight(150)
        self.pc_actions_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.pc_actions_scroll.setWidget(self.pc_actions_list)
        pal.addWidget(self.pc_actions_scroll)
        pl.addWidget(self.pc_actions_group)
        self.pc_actions_group.setVisible(False)
        
        # --- PHONE CALIBRATION MARKERS LIST ---
        self.phone_actions_group = QWidget()
        phl = QVBoxLayout(self.phone_actions_group)
        phl.setContentsMargins(0, 5, 0, 0)
        phl.setSpacing(5)
        phl.addWidget(SectionHeader("UI Markers (Phone)"))
        self.phone_actions_list = QWidget()
        self.phone_actions_layout = QVBoxLayout(self.phone_actions_list)
        self.phone_actions_layout.setContentsMargins(0,0,0,0)
        self.phone_actions_layout.setSpacing(4)
        self.phone_actions_scroll = QScrollArea()
        self.phone_actions_scroll.setWidgetResizable(True)
        self.phone_actions_scroll.setFixedHeight(150)
        self.phone_actions_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.phone_actions_scroll.setWidget(self.phone_actions_list)
        phl.addWidget(self.phone_actions_scroll)
        pl.addWidget(self.phone_actions_group)
        self.phone_actions_group.setVisible(False)

        # --- TEST CALIBRATION BUTTON (Right under actions) ---
        self.btn_test = QPushButton("▶️  TEST CALIBRATION")
        self.btn_test.setFixedHeight(38)
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.setStyleSheet(f"""
            QPushButton {{
                background: {C['green']}22;
                color: {C['green']};
                border: 1px solid {C['green']}55;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                margin-top: 5px;
                margin-bottom: 10px;
            }}
            QPushButton:hover {{
                background: {C['green']}33;
                border: 1px solid {C['green']};
            }}
        """)
        self.btn_test.clicked.connect(self.test_calibration_requested.emit)
        self.btn_test.setVisible(False) 
        pl.addWidget(self.btn_test)
        
        # --- VISION FOCUS AREAS ---
        pl.addWidget(SectionHeader("Focus Areas"))
        self.chk_whole_screen = QCheckBox("Look at Whole Screen")
        self.chk_whole_screen.setChecked(True)
        self.chk_whole_screen.setStyleSheet(f"color: {C['white']}; font-weight: bold; margin-top: 5px;")
        self.chk_whole_screen.toggled.connect(self._on_focus_mode_toggled)
        pl.addWidget(self.chk_whole_screen)
        
        self.focus_ctrl_widget = QWidget()
        fcl = QVBoxLayout(self.focus_ctrl_widget)
        fcl.setContentsMargins(0, 0, 0, 0)
        
        fcl.addWidget(QLabel("Defined Regions:"))
        self.region_list = QListWidget()
        self.region_list.setFixedHeight(80)
        self.region_list.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['cyan']}; border: 1px solid {C['border']}; font-size: 10px;")
        fcl.addWidget(self.region_list)
        
        self.region_list.currentRowChanged.connect(self._on_region_selection_changed)
        fcl.addWidget(self.region_list)
        
        rl_btns = QHBoxLayout()
        self.btn_define = QPushButton("🎯 Add Area")
        self.btn_define.setFixedHeight(28)
        self.btn_define.setStyleSheet(f"background: {C['purple']}; color: white; border-radius: 4px; font-weight: bold; border: none;")
        self.btn_define.clicked.connect(self._on_define_clicked)
        rl_btns.addWidget(self.btn_define)
        fcl.addLayout(rl_btns)
        
        pl.addWidget(self.chk_whole_screen)
        pl.addWidget(self.focus_ctrl_widget)
        
        self._on_focus_mode_toggled(True) # Sync initial state
        
        pl.addStretch()
        self.mid_splitter.addWidget(self.perf_panel)
        main_layout.addWidget(self.mid_splitter)
        
        # Update Timer should only trigger UI refreshes, not blocking ADB calls
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._refresh_stats)
        self.stats_timer.start(2000)
        
    def _on_source_index_changed(self, index):
        source = "pc" if index == 0 else "phone"
        self.set_active_source(source)
        self.config_changed.emit({"source": source})
        
        # Refresh the Focus Areas list to show ONLY regions for this source
        self._refresh_region_list()

    def update_pc_actions(self, actions: list):
        """Re-populate the PC actions list in the UI safely."""
        while self.pc_actions_layout.count():
            item = self.pc_actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, act in enumerate(actions):
            item = CalibrationActionItem(i + 1, act)
            item.delete_requested.connect(lambda idx=i: self.action_delete_requested.emit(idx))
            item.rename_requested.connect(lambda name, idx=i: self.action_rename_requested.emit(idx, name))
            item.move_up_requested.connect(lambda idx=i: self.action_move_requested.emit(idx, -1))
            item.move_down_requested.connect(lambda idx=i: self.action_move_requested.emit(idx, 1))
            item.delay_changed.connect(lambda ms, idx=i: self.action_delay_changed.emit(idx, ms))
            self.pc_actions_layout.addWidget(item)

        self.pc_actions_layout.addStretch()
        self._update_test_visibility(len(actions) > 0)

    def update_phone_actions(self, markers: list):
        """Re-populate the Phone markers list in the UI safely."""
        while self.phone_actions_layout.count():
            item = self.phone_actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, pt in enumerate(markers):
            item = CalibrationActionItem(i + 1, pt)
            item.delete_requested.connect(lambda idx=i: self.action_delete_requested.emit(idx))
            item.rename_requested.connect(lambda name, idx=i: self.action_rename_requested.emit(idx, name))
            item.delay_changed.connect(lambda ms, idx=i: self.action_delay_changed.emit(idx, ms))
            self.phone_actions_layout.addWidget(item)

        self.phone_actions_layout.addStretch()
        self._update_test_visibility(len(markers) > 0)

    def _update_test_visibility(self, current_list_has_items=False):
        """Force check visibility based on both lists."""
        p_count = self.pc_actions_layout.count() - 1 # items + stretch
        m_count = self.phone_actions_layout.count() - 1 
        
        # If the update just happened, we trust the incoming signal more than the layout count
        has_any = (p_count > 0 or m_count > 0 or current_list_has_items)
        self.btn_test.setVisible(has_any)

    def set_active_source(self, source: str):
        """Toggle visibility of calibration lists based on source."""
        is_pc = source.lower() == "pc"
        self.pc_actions_group.setVisible(is_pc)
        self.phone_actions_group.setVisible(not is_pc)
        
        # Also sync dropdown if needed
        self.combo_source.blockSignals(True)
        self.combo_source.setCurrentIndex(0 if is_pc else 1)
        self.combo_source.blockSignals(False)
        
    def _on_focus_mode_toggled(self, checked):
        self.focus_ctrl_widget.setEnabled(not checked)
        self._emit_config()

    def _on_define_clicked(self):
        """Activates mouse selection for MOBILE regions on the preview label."""
        if self.combo_source.currentIndex() == 0:
            # PC Source -> Signal to parent to launch the full-screen dialog
            self.define_pc_region_requested.emit()
            return

        # Mobile Source -> Internal overlay on preview label
        self._is_selecting = not self._is_selecting
        if self._is_selecting:
            self.btn_define.setText("❌ Cancel")
            self.btn_define.setStyleSheet(f"background: {C['red']}; color: white; border-radius: 4px; font-weight: bold; border: none;")
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.selection_overlay.show()
        else:
            self.btn_define.setText("🎯 Add Area")
            self.btn_define.setStyleSheet(f"background: {C['purple']}; color: white; border-radius: 4px; font-weight: bold; border: none;")
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.selection_overlay.hide()
            self._start_pos = None
            self._current_rect = QRect()

    def _emit_config(self):
        config = {
            "mode": "whole_screen" if self.chk_whole_screen.isChecked() else "regions",
            "device_type": "pc" if self.combo_source.currentText() == "PC Screen" else "mobile",
            "regions": self._regions
        }
        self.focus_config_changed.emit(config)

    def add_region(self, region):
        """Called externally or internally to add a new region."""
        # Assign source based on current dropdown selection
        region["source"] = "pc" if self.combo_source.currentIndex() == 0 else "mobile"
        region.setdefault("visible", True)
        
        self._regions.append(region)
        self._refresh_region_list() # Re-populate list to respect filters
        self._emit_config()

    def _add_region_item(self, index, region_data):
        item = QListWidgetItem(self.region_list)
        item.setSizeHint(QSize(0, 34))
        widget = RegionActionItem(index, region_data)
        
        widget.rename_requested.connect(lambda name, idx=index-1: self._on_region_rename(idx, name))
        widget.delete_requested.connect(lambda idx=index-1: self._on_region_delete(idx))
        widget.visibility_toggled.connect(lambda vis, idx=index-1: self._on_region_visibility_toggle(idx, vis))
        
        self.region_list.addItem(item)
        self.region_list.setItemWidget(item, widget)

    def _on_region_rename(self, idx, name):
        if idx < len(self._regions):
            self._regions[idx]["name"] = name
            self._emit_config()

    def _on_region_visibility_toggle(self, idx, visible):
        if idx < len(self._regions):
            self._regions[idx]["visible"] = visible
            self._emit_config()
            # Trigger immediate redraw of the current frame with new visibility
            self.update_preview()

    def _on_region_delete(self, idx):
        if 0 <= idx < len(self._regions):
            self._regions.pop(idx)
            self._refresh_region_list()
            self._emit_config()

    def _refresh_region_list(self):
        self.region_list.clear()
        
        # Determine current source for filtering
        active_source = "pc" if self.combo_source.currentIndex() == 0 else "mobile"
        
        for i, r in enumerate(self._regions):
            # Only show regions that match our currently active SOURCE
            if r.get("source", "mobile") == active_source:
                # Pass the ACTUAL index i+1 for the UI, 
                # signal handlers use idx=index-1 which points back to i perfectly.
                self._add_region_item(i + 1, r)
        
        # Immediate visualization update
        self.update_preview()

    def get_focus_config(self):
        return {
            "mode": "whole_screen" if self.chk_whole_screen.isChecked() else "regions",
            "device_type": "pc" if self.combo_source.currentIndex() == 0 else "phone",
            "regions": self._regions
        }

    def _on_region_selection_changed(self, row):
        self.update_preview()

    def _create_mini_stat(self, label, value, color):
        w = QWidget()
        l = QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(1)
        lbl = QLabel(label.upper())
        lbl.setObjectName("lbl_static") # Name it
        lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 8px; font-weight: bold; border: none; letter-spacing: 0.5px;")
        
        val = QLabel(value)
        val.setObjectName("lbl_value") # Name it
        val.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 800; border: none;")
        
        l.addWidget(lbl)
        l.addWidget(val)
        return w

    def _create_perf_bar(self, title, color):
        w = QWidget()
        l = QVBoxLayout(w); l.setContentsMargins(0,10,0,0); l.setSpacing(4)
        t = QLabel(title); t.setStyleSheet(f"color: {C['text_d']}; font-size: 10px;")
        bar_bg = QFrame()
        bar_bg.setFixedHeight(6)
        bar_bg.setFixedWidth(180) # Fixed width for reliable math
        bar_bg.setStyleSheet(f"background: {C['bg_darkest']}; border-radius: 3px;")
        bar_fill = QFrame(bar_bg)
        bar_fill.setFixedHeight(6)
        bar_fill.setFixedWidth(0)
        bar_fill.setStyleSheet(f"background: {color}; border-radius: 3px;")
        l.addWidget(t); l.addWidget(bar_bg)
        w.title_lbl = t
        w.fill = bar_fill
        return w

    def set_model(self, name, config):
        self.model_name = name
        fcfg = config.get("focus_config", {})
        self.chk_whole_screen.setChecked(fcfg.get("mode", "whole_screen") == "whole_screen")
        self.combo_source.setCurrentText("PC Screen" if fcfg.get("device_type", "pc") == "pc" else "Mobile Device")
        
        self._regions = fcfg.get("regions", [])
        self._refresh_region_list()
            
        self._on_focus_mode_toggled(self.chk_whole_screen.isChecked())
        self._start_monitor(config.get("target_serial") or self.mobile_mgr.connected_device_ip)
        self._refresh_stats()

    def _start_monitor(self, serial):
        if self.monitor_worker and self.monitor_worker.isRunning():
            if self.monitor_worker.serial == serial: return
            self.monitor_worker.stop()
        
        if not serial: return
        self.monitor_worker = DeviceMonitorWorker(self.mobile_mgr, serial)
        self.monitor_worker.info_received.connect(self._on_info_received)
        self.monitor_worker.start()

    def _on_info_received(self, info):
        # Update Mini Stats UI using the background data
        if not info.get("partial"):
            # Full update
            self.lbl_model.setText(info.get("model", "Android Device"))
            self.stat_battery.findChild(QLabel, "lbl_value").setText(f"{info.get('battery')}%")
            self.stat_temp.findChild(QLabel, "lbl_value").setText(info.get('temp'))
            self.stat_ping.findChild(QLabel, "lbl_value").setText(info.get('ping'))
            self.stat_storage.findChild(QLabel, "lbl_value").setText(info.get('storage'))
        else:
            # Partial update (likely just app + battery/temp if using dynamic)
            if "battery" in info:
                self.stat_battery.findChild(QLabel, "lbl_value").setText(f"{info.get('battery')}%")
            if "temp" in info:
                self.stat_temp.findChild(QLabel, "lbl_value").setText(info.get('temp'))
            if "ping" in info:
                self.stat_ping.findChild(QLabel, "lbl_value").setText(info.get('ping'))
            if "storage" in info:
                self.stat_storage.findChild(QLabel, "lbl_value").setText(info.get('storage'))
        
        # CPU / RAM stats (every 30s)
        if "cpu" in info:
            cpu_val = info["cpu"]
            self.cpu_bar.fill.setFixedWidth(int(cpu_val * 180 / 100))
            self.cpu_bar.title_lbl.setText(f"CPU Utilization ({cpu_val}%)")
            
        if "ram_percent" in info:
            ram_p = info["ram_percent"]
            self.ram_bar.fill.setFixedWidth(int(ram_p * 180 / 100))
            self.ram_bar.title_lbl.setText(f"RAM ({info['ram_used']:.1f}G / {info['ram_total']:.1f}G)")
            
        self.lbl_app.setText(f"Foreground: {info.get('app')}")

    def update_connection_status(self, connected, ip="", battery="0"):
        if not connected and not self.mobile_mgr.is_connected:
            self.lbl_model.setText("No Device Connected")
            self.lbl_serial.setText("Waiting for ADB link...")
            self.btn_link.hide()
            self.btn_release.hide()
            self.preview_lbl.setText("Plug in device or use Wireless Connect")
            return

        serial = ip or self.mobile_mgr.connected_device_ip
        if not serial: return

        # Only start monitor if not running for this serial
        if not self.monitor_worker or not self.monitor_worker.isRunning():
            self._start_monitor(serial)
        
        self._update_resolution_cache()
        self.lbl_serial.setText(f"{serial} • {self.mobile_mgr.connection_type}")
        
        # Ownership & Session Logic Refactored
        lock_owner = self.mobile_mgr.is_device_locked(serial, self.model_name)
        owner_is_me = (self.mobile_mgr.device_owners.get(serial) == self.model_name)
        
        # Get mirror worker status from parent if possible, but let's assume we maintain a state
        # Better yet, let's check a central registry or signal
        # For now, we'll use a hack to check MirrorWorker 'paused' flag via ModelScreen if needed
        # Or just use the button text as state.
        
        if lock_owner:
            self.btn_link.setText(f"LOCKED BY {lock_owner.upper()}")
            self.btn_link.setEnabled(True) # Enabled so we can show error popup
            self.btn_link.setStyleSheet(f"background: #111; color: {C['red']}; border: 1px solid {C['red']};")
            self.btn_release.hide()
        elif owner_is_me:
            # We own it. Check if active or paused.
            # In update_preview, if we are receiving frames, we are active.
            # But we need a persistent state.
            self.btn_release.show()
            # If the current button text is LINK/ACQUIRE and we just transitioned, we need to know
            # Let's use the button's own text to track state OR extra property
            current_state = self.btn_link.text()
            if "DISCONNECT" in current_state:
                pass # Stay in DISCONNECT
            elif "ACQUIRE" in current_state:
                pass # Stay in ACQUIRE
            else:
                # First time linking or resumed from another tab
                # Default to DISCONNECT (active) when linked
                self.btn_link.setText("⚡ DISCONNECT")
                self.btn_link.setStyleSheet(f"background: {C['green']}33; color: {C['green']}; border: 1px solid {C['green']};")
        else:
            self.btn_link.setText("🚀 LINK MOBILE")
            self.btn_link.setEnabled(True)
            self.btn_link.setStyleSheet(f"background: {C['bg_sidebar']}; color: {C['cyan']}; border: 1px solid {C['cyan']};")
            self.btn_release.hide()

        self.btn_link.show()

    def _refresh_stats(self):
        if self.mobile_mgr.is_connected:
            self.update_connection_status(True)

    def _on_link_clicked(self):
        txt = self.btn_link.text()
        serial = self.mobile_mgr.connected_device_ip
        if not serial: return

        if "LOCKED" in txt:
            owner = self.mobile_mgr.device_owners.get(serial)
            QMessageBox.critical(self, "Device Locked", f"Error: Model '{owner}' has access right now. You must release it from that model first.")
            return

        if "LINK" in txt:
            # Attempt to LINK
            self.takeover_requested.emit()
            # update_connection_status will handle button text change if link succeeded
        elif "DISCONNECT" in txt:
            # Mirror is active, PAUSE it
            self.mirror_pause_requested.emit()
            self.btn_link.setText("🔄 ACQUIRE")
            self.btn_link.setStyleSheet(f"background: {C['purple_d']}33; color: {C['purple_l']}; border: 1px solid {C['purple_l']};")
            self.preview_lbl.setText("MIRRORING PAUSED")
            # Show the session-locked-style overlay on preview
            self.update_preview_status("PAUSED")
        elif "ACQUIRE" in txt:
            # Mirror is paused, RESUME it
            self.mirror_resume_requested.emit()
            self.btn_link.setText("⚡ DISCONNECT")
            self.btn_link.setStyleSheet(f"background: {C['green']}33; color: {C['green']}; border: 1px solid {C['green']};")
            self.preview_lbl.setText("Resuming mirroring...")
            self.update_preview_status("ACTIVE")

    def update_preview_status(self, status: str):
        # We can draw or set text on the label
        if status == "LOCKED":
            self.preview_lbl.setPixmap(QPixmap()) # Clear stale frame
            self.preview_lbl.setText(f"DEVICE LOCKED BY ANOTHER MODEL\n(NO ACCESS)")
            self.preview_lbl.setStyleSheet("color: #FF5555; background: #110000; font-weight: bold; border: 2px solid red;")
        elif status == "PAUSED":
            # Don't clear, just overlay
            self.preview_lbl.setStyleSheet("color: white; background: rgba(0,0,0,150); font-weight: bold;")
        elif status == "ACTIVE":
            self.preview_lbl.setStyleSheet("color: #333; background: black;")

    def _on_release_clicked(self):
        if "DISCONNECT" in self.btn_link.text():
             reply = QMessageBox.question(self, "Active Session", 
                                "Warning: Mirroring is still active. Are you sure you want to release the device?\n\It is smoother to Disconnect first.",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
             if reply == QMessageBox.StandardButton.No:
                 return

        serial = self.mobile_mgr.connected_device_ip
        self.mobile_mgr.release_device(serial)
        self.btn_link.setText("🚀 LINK MOBILE")
        self.update_connection_status(False)
        self.update_preview_status("LOCKED") # Reset UI

    def set_fullscreen_ui(self, enabled: bool):
        """Toggle button visibility locally based on FS state."""
        self.btn_enter_fs.setVisible(not enabled)
        self.btn_exit_fs.setVisible(enabled)
        
        # Hide top status card and viewport controls
        if hasattr(self, 'status_card'):
            self.status_card.setVisible(not enabled)
        if hasattr(self, 'ctrl_bar'):
            self.ctrl_bar.setVisible(not enabled)
            
        # Reposition buttons immediately
        self.btn_enter_fs.raise_()
        self.btn_exit_fs.raise_()
        
        # Remove layout spacing/margins in FS for edge-to-edge
        if hasattr(self, 'pv_layout'):
            self.pv_layout.setContentsMargins(0, 0, 0, 0 if enabled else 10)
            self.pv_layout.setSpacing(0 if enabled else 5)

    def update_preview(self, qimg: QImage = None):
        """Redraws the preview frame and adds regional focus overlays."""
        # 1. Base Image Prep
        if qimg is not None and not qimg.isNull():
            self.last_qimg = qimg # Cache the fresh mirror frame
            
        # Determine Canvas Dimensions
        frame_w = self.preview_frame.width()
        frame_h = self.preview_frame.height()
        if frame_w < 10: frame_w = 400
        if frame_h < 10: frame_h = 600

        # Create the Base Pixmap
        if hasattr(self, 'last_qimg') and not self.last_qimg.isNull():
            # Use the last known mirror frame
            # USing FastTransformation for mirroring to ELIMINATE LAG (Very important for 60fps)
            pix = QPixmap.fromImage(self.last_qimg).scaled(
                frame_w, frame_h, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.FastTransformation # Faster than SmoothTransformation
            )
        else:
            # Mirror not running? Use a dark placeholder so regions are STILL visible
            pix = QPixmap(frame_w, frame_h)
            pix.fill(QColor(20, 20, 30))
            
        # 2. Draw Regions (If Focus Mode is active)
        if not self.chk_whole_screen.isChecked() and self._regions:
            painter = QPainter(pix)
            selected_idx = self.region_list.currentRow()
            
            # Use Cached Resolutions (Optimized for 60FPS)
            mw, mh = self._cached_mobile_mw, self._cached_mobile_mh
            pw, ph = self._cached_screen_pw, self._cached_screen_ph
            
            # Determine logic source based on what the user is currently looking at
            active_src = "pc" if self.combo_source.currentIndex() == 0 else "mobile"
            
            for i, r in enumerate(self._regions):
                # Visibility check: always show selected, hide others if eye is off
                if not r.get("visible", True) and i != selected_idx:
                    continue
                
                # Native dimensions for THIS specific region's source
                # (We show all regions if toggled on, but scale them based on their home source)
                is_pc = (r.get("source") == "pc")
                if is_pc:
                    continue # USer only wants to see PC regions on the ACTUAL screen, not in the preview label
                    
                nw = pw if is_pc else mw
                nh = ph if is_pc else mh
                
                # Native -> Pixmap scaling
                sw = pix.width() / nw
                sh = pix.height() / nh
                
                # Calculate Rect
                rx = int(r["x1"] * sw)
                ry = int(r["y1"] * sh)
                rw = int((r["x2"] - r["x1"]) * sw)
                rh = int((r["y2"] - r["y1"]) * sh)
                rect = QRect(rx, ry, rw, rh).normalized()
                
                # Stylize
                is_sel = (i == selected_idx)
                color = QColor(0, 255, 255) if is_sel else QColor(160, 100, 255)
                pen = QPen(color, 2 if is_sel else 1)
                if not is_sel: pen.setStyle(Qt.PenStyle.DashLine)
                
                painter.setPen(pen)
                painter.drawRect(rect)
                
                # Name Label
                painter.setPen(color)
                painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
                painter.drawText(rect.topLeft() + QPoint(5, 12), r.get("name", f"R{i+1}"))
            
            painter.end()

        # Update the UI
        self.preview_lbl.setPixmap(pix)
        self.preview_lbl.setText("")
        
    def resizeEvent(self, event):
        """Ensure buttons stay at the bottom-right when the widget is resized."""
        super().resizeEvent(event)
        fw = self.preview_frame.width()
        fh = self.preview_frame.height()
        # Position enter-fullscreen button
        self.btn_enter_fs.move(fw - self.btn_enter_fs.width() - 5, 
                               fh - self.btn_enter_fs.height() - 5)
        # Position exit-fullscreen button
        self.btn_exit_fs.move(fw - self.btn_exit_fs.width() - 5, 
                               fh - self.btn_exit_fs.height() - 5)

    def _update_resolution_cache(self):
        """Updates internal cache for PC and Mobile resolutions (avoiding repeated expensive system calls)."""
        try:
            # PC Screen Cache
            screen = QApplication.primaryScreen()
            if screen:
                sz = screen.size()
                self._cached_screen_pw, self._cached_screen_ph = sz.width(), sz.height()
            
            # Mobile Device Cache
            if self.mobile_mgr.connected_device_ip:
                res_str = self.mobile_mgr.get_device_info(self.mobile_mgr.connected_device_ip).get("resolution", "1080x1920")
                m_res = res_str.split("x")
                self._cached_mobile_mw = int(m_res[0])
                self._cached_mobile_mh = int(m_res[1])
        except Exception as e:
            pass # Use defaults if something fails

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if not self.preview_frame.geometry().contains(pos):
            super().mousePressEvent(event)
            return

        # Calculate relative position within the frame
        rel_pos = self.preview_frame.mapFrom(self, pos)

        if self._is_selecting:
            if event.button() == Qt.MouseButton.LeftButton:
                self._start_pos = rel_pos
                self._current_rect = QRect(rel_pos, rel_pos)
                self.selection_overlay.set_rect(self._current_rect)
                self.update()
            return

        # Existing Interaction Logic
        # Map back to phone resolution
        pix = self.preview_lbl.pixmap()
        if pix and not pix.isNull():
            # Center-scaled math
            lbl_rect = self.preview_lbl.rect()
            pix_rect = pix.rect()
            # Offset if pix is smaller than lbl
            off_x = (lbl_rect.width() - pix_rect.width()) / 2
            off_y = (lbl_rect.height() - pix_rect.height()) / 2
            
            # Check if click is actually on the pixmap
            local_x = rel_pos.x() - off_x
            local_y = rel_pos.y() - off_y
            
            if 0 <= local_x <= pix_rect.width() and 0 <= local_y <= pix_rect.height():
                # Scale to native resolution
                dev_info = self.mobile_mgr.get_device_info(self.mobile_mgr.connected_device_ip)
                res_str = dev_info.get("resolution", "1080x1920") # Fallback
                try:
                    native_w, native_h = map(int, res_str.split("x"))
                    scale_x = native_w / pix_rect.width()
                    scale_y = native_h / pix_rect.height()
                    
                    nx = int(local_x * scale_x)
                    ny = int(local_y * scale_y)
                    
                    self.captured_native_pos.emit(nx, ny)
                    self.clicked_pos.emit(rel_pos.x(), rel_pos.y()) # For UI dots
                except: pass

        super().mousePressEvent(event)

    def _show_click_dot(self, x, y):
        """Shows a temporary visual indicator at the given preview coordinates."""
        # Offset slightly to center the 20x20 dot
        self.click_dot.move(x - 10, y - 10)
        self.click_dot.show()
        self.click_dot.raise_()
        self.click_dot_timer.start(600)

    def mouseMoveEvent(self, event):
        if self._is_selecting and self._start_pos is not None:
            pos = event.position().toPoint()
            rel_pos = self.preview_frame.mapFrom(self, pos)
            self._current_rect = QRect(self._start_pos, rel_pos).normalized()
            self.selection_overlay.set_rect(self._current_rect)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_selecting and self._start_pos is not None:
            if self._current_rect.width() > 10 and self._current_rect.height() > 10:
                # Map selected rect to native mobile resolution
                pix = self.preview_lbl.pixmap()
                if pix and not pix.isNull():
                    lbl_rect = self.preview_lbl.rect()
                    pix_rect = pix.rect()
                    off_x = (lbl_rect.width() - pix_rect.width()) / 2
                    off_y = (lbl_rect.height() - pix_rect.height()) / 2
                    
                    # Intersecting with pixmap
                    r = self._current_rect
                    local_x1 = max(0, r.left() - off_x)
                    local_y1 = max(0, r.top() - off_y)
                    local_x2 = min(pix_rect.width(), r.right() - off_x)
                    local_y2 = min(pix_rect.height(), r.bottom() - off_y)
                    
                    dev_info = self.mobile_mgr.get_device_info(self.mobile_mgr.connected_device_ip)
                    res_str = dev_info.get("resolution", "1080x1920")
                    try:
                        native_w, native_h = map(int, res_str.split("x"))
                        scale_x = native_w / pix_rect.width()
                        scale_y = native_h / pix_rect.height()
                        
                        region = {
                            "x1": int(local_x1 * scale_x),
                            "y1": int(local_y1 * scale_y),
                            "x2": int(local_x2 * scale_x),
                            "y2": int(local_y2 * scale_y)
                        }
                        self.add_region(region)
                    except: pass

            # Reset Selection Mode
            self._is_selecting = False
            self.selection_overlay.hide()
            self._start_pos = None
            self._current_rect = QRect()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.btn_define.setText("🎯 Add Area")
            self.btn_define.setStyleSheet(f"background: {C['purple']}; color: white; border-radius: 4px; font-weight: bold; border: none;")
            self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._is_selecting:
            # Map preview space to frame space if needed, 
            # but currently _current_rect is already in preview_frame space
            self.selection_overlay.setGeometry(self.preview_lbl.geometry())
