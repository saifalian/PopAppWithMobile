"""
Settings page — including full CPU/GPU/DirectML device picker.
This is the key new feature: choose compute device with live detection.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QCheckBox, QLineEdit, QSpinBox,
    QDoubleSpinBox, QScrollArea, QFrame, QSizePolicy, QRadioButton,
    QButtonGroup, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QBrush

from app.theme import C, FONT_UI, FONT_MONO
from backend.core.gpu_manager import detect_all_devices, ComputeDevice, get_live_gpu_stats
from backend.core.settings_manager import settings
from app.core.gpu_manager import TFDeviceSetup


class DeviceDetectionThread(QThread):
    """Background thread for device detection (can take a few seconds)."""
    detected = pyqtSignal(list)  # emits list of ComputeDevice

    def run(self):
        devices = detect_all_devices()
        self.detected.emit(devices)


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices: list[ComputeDevice] = []
        self._selected_device: ComputeDevice | None = None
        self._build_ui()
        self._load_current_settings()
        self._detect_devices()

    def _build_ui(self):
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── SETTINGS HEADER ──────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(f"background: {C['bg_darkest']}; border-bottom: 1px solid {C['border']};")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(28, 20, 28, 20)
        
        title_row = QHBoxLayout()
        title_icon = QLabel("⚙")
        title_icon.setStyleSheet(f"color: {C['white']}; font-size: 22px;")
        title_lbl = QLabel("Settings")
        title_lbl.setStyleSheet(f"color: {C['white']}; font-size: 22px; font-weight: bold;")
        title_row.addWidget(title_icon)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        hl.addLayout(title_row)
        
        subtitle = QLabel("Configure ModelFactory, compute devices, training defaults, and system options.")
        subtitle.setStyleSheet(f"color: {C['text_d']}; font-size: 12px;")
        hl.addWidget(subtitle)
        layout.addWidget(header)


        # ── SCROLLABLE CONTENT ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {C['bg_darkest']};")
        
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(28, 20, 28, 40)
        self.main_layout.setSpacing(32)

        # SECTION 1 — COMPUTE DEVICE
        self._setup_section_compute()
        
        # SECTION 2 — APPLICATION PATHS
        self._setup_section_paths()
        
        # SECTION 3 — TRAINING DEFAULTS
        self._setup_section_training_defaults()

        # SECTION 4 — TRAINING SCHEDULER
        self._setup_section_scheduler()
        
        # SECTION 5 — BACKUP SYSTEM
        self._setup_section_backup()
        
        # SECTION 6 — DRIFT DETECTION
        self._setup_section_drift()

        # SECTION 7 — OLLAMA
        self._setup_section_ollama()
        
        # SECTION 8 — SCREEN CAPTURE
        self._setup_section_screen_capture()
        
        # SECTION 9 — UI CALIBRATION
        self._setup_section_calibration()
        
        # SECTION 10 — PERFORMANCE & LOGGING
        self._setup_section_performance()
        
        # SECTION 11 — ABOUT & DIAGNOSTICS
        self._setup_section_about()

        # Bottom row
        self._setup_bottom_row()
        
        self.main_layout.addStretch()
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _setup_section_compute(self):
        group = self._section_card("COMPUTE DEVICE", "Select the processor used for model training. GPU is 8–15× faster than CPU.")
        gl = group.layout()
        
        row1 = QHBoxLayout()
        self.detect_btn = QPushButton("🔍 Detect Devices")
        self.detect_btn.setFixedSize(160, 32)
        self.detect_btn.setStyleSheet(f"border: 1px solid {C['purple']}; color: {C['purple_l']}; border-radius: 4px;")
        self.detect_btn.clicked.connect(self._detect_devices)
        row1.addWidget(self.detect_btn)
        
        self.detect_status = QLabel("Ready")
        self.detect_status.setStyleSheet(f"color: {C['text_d']}; font-size: 13px; font-weight: 500; margin-left: 10px;")
        row1.addWidget(self.detect_status)
        row1.addStretch()
        gl.addLayout(row1)
        gl.addSpacing(10)
        
        self.device_cards_layout = QVBoxLayout()
        gl.addLayout(self.device_cards_layout)
        
        # Batch size
        gl.addWidget(self._h_sep())
        row, self.batch_size = self._num_field("BATCH SIZE", 32, 1, 256)
        gl.addLayout(row)
        
        self.selected_info = QLabel("No device selected")
        self.selected_info.setStyleSheet(f"color: {C['purple_l']}; font-size: 13px; font-weight: 600; padding: 10px 0;")
        gl.addWidget(self.selected_info)
        
        # Mixed Precision
        gl.addWidget(self._h_sep())
        mp_row = QHBoxLayout()
        self.mixed_prec = QCheckBox(" MIXED PRECISION (float16 / float32)")
        self.mixed_prec.setStyleSheet(f"color: {C['white']}; font-size: 14px; font-weight: 700;")
        mp_row.addWidget(self.mixed_prec)
        mp_row.addStretch()
        gl.addLayout(mp_row)
        
        mp_sub = QLabel("Uses float16 for compute, float32 for model variables. 30-50% faster, requires Tensor Cores (RTX).")
        mp_sub.setStyleSheet(f"color: {C['text_d']}; font-size: 12px; padding-left: 28px;")
        gl.addWidget(mp_sub)
        
        self.main_layout.addWidget(group)

    def _setup_section_paths(self):
        group = self._section_card("APPLICATION PATHS", "Specify locations for models, datasets, and logs.")
        gl = group.layout()
        
        row1, self.path_models = self._path_field("Models Directory", r"C:\ModelFactory\Models")
        gl.addLayout(row1)
        row2, self.path_datasets = self._path_field("Datasets Directory", r"C:\ModelFactory\Datasets")
        gl.addLayout(row2)
        row3, self.path_logs = self._path_field("Logs Directory", r"C:\ModelFactory\Logs")
        gl.addLayout(row3)
        row4, self.path_macros = self._path_field("Macros Directory", r"data\macros")
        gl.addLayout(row4)
        
        self.main_layout.addWidget(group)

    def _setup_section_training_defaults(self):
        group = self._section_card("TRAINING DEFAULTS", "Default parameters for new training runs.")
        gl = group.layout()
        
        # Removed redundant batch_size here, it's in Section 1
        
        row, self.max_attempts = self._num_field("Max Attempts", 200, 10, 10000)
        gl.addLayout(row)
        
        row, self.confidence = self._float_field("Default Confidence", 0.65, 0.0, 1.0)
        gl.addLayout(row)
        
        row, self.attempt_timeout = self._num_field("Attempt Timeout (s)", 60, 10, 600)
        gl.addLayout(row)
        
        self.main_layout.addWidget(group)
        
    def _setup_section_scheduler(self):
        group = self._section_card("TRAINING SCHEDULER", "Run training automatically while you sleep.")
        gl = group.layout()
        
        row, self.sched_enabled = self._toggle_field("ENABLE SCHEDULER", False)
        gl.addLayout(row)
        gl.addWidget(self._h_sep())
        
        row1, self.sched_start = self._text_field("Start training at:", "02:00 AM", 120)
        gl.addLayout(row1)
        row2, self.sched_stop = self._text_field("Stop training by:", "06:00 AM", 120)
        gl.addLayout(row2)
        gl.addLayout(self._num_field("Max attempts per run", 50, 1, 1000)[0])
        
        self.main_layout.addWidget(group)

    def _setup_section_backup(self):
        group = self._section_card("BACKUP SYSTEM", "Automatically backs up model weights and history.")
        gl = group.layout()
        
        row, self.backup_enabled = self._toggle_field("ENABLE BACKUPS", True)
        gl.addLayout(row)
        gl.addWidget(self._h_sep())
        
        row, self.backup_path = self._path_field("Backup Location", r"D:\Backups\ModelFactory")
        gl.addLayout(row)
        
        btn_row = QHBoxLayout()
        btn_row.addWidget(QPushButton("Backup Now"))
        btn_row.addWidget(QPushButton("View History"))
        btn_row.addStretch()
        gl.addLayout(btn_row)
        
        self.main_layout.addWidget(group)

    def _setup_section_drift(self):
        group = self._section_card("DRIFT DETECTION", "Monitors model confidence during live deployment.")
        gl = group.layout()
        
        row, self.drift_enabled = self._toggle_field("ENABLE DRIFT DETECTION", True)
        gl.addLayout(row)
        gl.addWidget(self._h_sep())
        
        gl.addLayout(self._num_field("Alert threshold (%)", 15, 1, 50)[0])
        gl.addLayout(self._num_field("Check frequency (runs)", 20, 1, 100)[0])
        
        self.main_layout.addWidget(group)

    def _setup_section_ollama(self):
        group = self._section_card("OLLAMA (OPTIONAL)", "Local LLM for results summary and analysis.")
        gl = group.layout()
        
        row, self.ollama_enabled = self._toggle_field("ENABLE OLLAMA", False)
        gl.addLayout(row)
        gl.addWidget(self._h_sep())
        
        row, self.ollama_host = self._text_field("Ollama Host", "http://localhost:11434")
        gl.addLayout(row)
        
        self.main_layout.addWidget(group)

    def _setup_section_screen_capture(self):
        group = self._section_card("SCREEN CAPTURE", "Configure how ModelFactory sees your screen.")
        gl = group.layout()
        
        cb = QComboBox()
        cb.addItems(["mss (Recommended)", "PIL ImageGrab", "Win32 GDI"])
        gl.addWidget(QLabel("CAPTURE METHOD"))
        gl.addWidget(cb)
        
        self.main_layout.addWidget(group)

    def _setup_section_calibration(self):
        group = self._section_card("UI CALIBRATION", "Calibrates screen coordinates of external UI elements.")
        gl = group.layout()
        
        status = QLabel("Last calibrated: Never")
        status.setStyleSheet(f"color: {C['amber']}; font-weight: bold;")
        gl.addWidget(status)
        
        btn = QPushButton("Re-Calibrate Now")
        btn.setFixedSize(160, 32)
        btn.setStyleSheet(f"background: {C['purple']}; color: white; border-radius: 4px;")
        gl.addWidget(btn)
        
        self.main_layout.addWidget(group)

    def _setup_section_performance(self):
        group = self._section_card("PERFORMANCE & LOGGING", "Log levels and TensorFlow engine settings.")
        gl = group.layout()
        
        gl.addLayout(self._toggle_field("TF MEMORY GROWTH", True)[0])
        gl.addLayout(self._toggle_field("SUPPRESS TF WARNINGS", True)[0])
        
        self.main_layout.addWidget(group)

    def _setup_section_about(self):
        group = self._section_card("ABOUT & DIAGNOSTICS", "System information and health checks.")
        gl = group.layout()
        
        info = QLabel("ModelFactory v1.0.0\nPython 3.10.x\nTensorFlow 2.10.0")
        info.setStyleSheet(f"color: {C['text']}; font-family: {FONT_MONO};")
        gl.addWidget(info)
        
        btn = QPushButton("Run Full Diagnostics")
        btn.setFixedSize(160, 32)
        gl.addWidget(btn)
        
        self.main_layout.addWidget(group)

    def _setup_bottom_row(self):
        row = QFrame()
        rl = QHBoxLayout(row)
        rl.addStretch()
        
        btn_reset = QPushButton("↺ Reset to Defaults")
        btn_reset.setStyleSheet(f"color: {C['text_d']}; border: 1px solid {C['border']}; padding: 8px 16px; border-radius: 4px;")
        rl.addWidget(btn_reset)
        
        btn_save = QPushButton("💾 Save All Settings")
        btn_save.setStyleSheet(f"background: {C['green']}; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        btn_save.clicked.connect(self._save_settings)
        rl.addWidget(btn_save)
        
        self.main_layout.addWidget(row)

    def _toggle_field(self, label, checked):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        cb = QCheckBox()
        cb.setChecked(checked)
        row.addWidget(cb)
        return row, cb

    def _text_field(self, label, default, width=320):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        edit = QLineEdit(default)
        edit.setFixedWidth(width)
        row.addWidget(edit)
        return row, edit

    def _h_sep(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet(f"color: {C['border']}; margin-top: 10px; margin-bottom: 10px;")
        return sep

    def _section_card(self, title: str, subtitle: str = None):
        box = QGroupBox(title, self)
        box.setStyleSheet(f"""
            QGroupBox {{
                color: {C['purple_l']};
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 2px;
                border: 1px solid {C['border']};
                border-radius: 12px;
                margin-top: 20px;
                padding: 24px;
                background: {C['bg_panel']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 24px;
                padding: 0 12px;
                background: {C['bg_panel']};
            }}
        """)
        layout = QVBoxLayout(box)
        layout.setSpacing(10)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {C['text_d']}; font-size: 12px;")
            sub.setWordWrap(True)
            layout.addWidget(sub)
        return box

    def _detect_devices(self):
        self.detect_btn.setEnabled(False)
        self.detect_status.setText("Scanning for CPU, CUDA, DirectML devices...")
        self._det_thread = DeviceDetectionThread()
        self._det_thread.detected.connect(self._on_devices_detected)
        self._det_thread.start()

    def _on_devices_detected(self, devices: list):
        self._devices = devices
        self.detect_btn.setEnabled(True)
        self.detect_status.setText(f"Found {len(devices)} device(s)")

        # Clear old cards
        while self.device_cards_layout.count():
            item = self.device_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Current selection
        current_id = settings.get("compute_device_id", "cpu")

        for device in devices:
            card = DeviceCard(device, selected=(device.id == current_id))
            card.clicked.connect(self._on_device_selected)
            self.device_cards_layout.addWidget(card)
            if device.id == current_id:
                self._selected_device = device

        self._update_selected_info()

    def _on_device_selected(self, device: ComputeDevice):
        self._selected_device = device
        # Update all cards
        for i in range(self.device_cards_layout.count()):
            w = self.device_cards_layout.itemAt(i).widget()
            if isinstance(w, DeviceCard):
                w.set_selected(w.device.id == device.id)
        self._update_selected_info()

    def _update_selected_info(self):
        if self._selected_device:
            d = self._selected_device
            type_icons = {"cpu": "🧠", "cuda": "🚀", "directml": "⚡"}
            icon = type_icons.get(d.device_type, "💻")
            self.selected_info.setText(
                f"{icon}  Selected: {d.name}  |  {d.description}"
            )
        else:
            self.selected_info.setText("No device selected")

    def _save_settings(self):
        if self._selected_device:
            settings.set_device(self._selected_device)
            # Configure TF immediately
            TFDeviceSetup.configure(self._selected_device)

        settings.set("batch_size",    self.batch_size.value())
        settings.set("max_attempts",  self.max_attempts.value())
        settings.set("default_confidence", self.confidence.value())
        settings.set("attempt_timeout", self.attempt_timeout.value())
        settings.set("mixed_precision", self.mixed_prec.isChecked())
        settings.set("ollama_enabled",  self.ollama_enabled.isChecked())
        settings.set("backup_enabled",  self.backup_enabled.isChecked())
        settings.set("scheduler_enabled", self.sched_enabled.isChecked())
        settings.set("drift_enabled", self.drift_enabled.isChecked())
        settings.set("models_path", self.path_models.text())
        settings.set("datasets_path", self.path_datasets.text())
        settings.set("logs_path", self.path_logs.text())
        settings.set("macros_path", self.path_macros.text())
        settings.save()

        self.detect_status.setText("✓ Settings saved")
        QTimer.singleShot(2000, lambda: self.detect_status.setText(
            f"Found {len(self._devices)} device(s)"))

    def _load_current_settings(self):
        self.batch_size.setValue(settings.get("batch_size", 32))
        self.max_attempts.setValue(settings.get("max_attempts", 200))
        self.confidence.setValue(settings.get("default_confidence", 0.65))
        self.attempt_timeout.setValue(settings.get("attempt_timeout", 60))
        self.mixed_prec.setChecked(settings.get("mixed_precision", True))
        self.ollama_enabled.setChecked(settings.get("ollama_enabled", False))
        self.backup_enabled.setChecked(settings.get("backup_enabled", True))
        self.sched_enabled.setChecked(settings.get("scheduler_enabled", False))
        self.drift_enabled.setChecked(settings.get("drift_enabled", True))
        self.path_models.setText(settings.get("models_path", r"C:\ModelFactory\Models"))
        self.path_datasets.setText(settings.get("datasets_path", r"C:\ModelFactory\Datasets"))
        self.path_logs.setText(settings.get("logs_path", r"C:\ModelFactory\Logs"))
        self.path_macros.setText(settings.get("macros_path", "data/macros"))

    def _num_field(self, label: str, default: int, min_v: int, max_v: int):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['white']}; font-size: 13px; font-weight: 600; min-width: 200px;")
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(default)
        spin.setFixedWidth(120)
        spin.setFixedHeight(36)
        spin.setStyleSheet(f"""
            QSpinBox {{ 
                background: {C['bg_darkest']}; 
                border: 1px solid {C['border']}; 
                border-radius: 6px; 
                padding: 4px 10px; 
                font-size: 13px; 
                color: {C['white']};
            }}
            QSpinBox:hover {{ border-color: {C['purple']}; }}
        """)
        row.addWidget(lbl)
        row.addWidget(spin)
        row.addStretch()
        return row, spin

    def _float_field(self, label: str, default: float, min_v: float, max_v: float):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['white']}; font-size: 13px; font-weight: 600; min-width: 200px;")
        spin = QDoubleSpinBox()
        spin.setRange(min_v, max_v)
        spin.setSingleStep(0.05)
        spin.setValue(default)
        spin.setFixedWidth(120)
        spin.setFixedHeight(36)
        spin.setStyleSheet(f"""
            QDoubleSpinBox {{ 
                background: {C['bg_darkest']}; 
                border: 1px solid {C['border']}; 
                border-radius: 6px; 
                padding: 4px 10px; 
                font-size: 13px; 
                color: {C['white']};
            }}
            QDoubleSpinBox:hover {{ border-color: {C['purple']}; }}
        """)
        row.addWidget(lbl)
        row.addWidget(spin)
        row.addStretch()
        return row, spin

    def _path_field(self, label: str, default: str):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['white']}; font-size: 13px; font-weight: 600; min-width: 200px;")
        edit = QLineEdit(default)
        edit.setMinimumWidth(320)
        edit.setFixedHeight(36)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background: {C['bg_darkest']}; 
                border: 1px solid {C['border']}; 
                border-radius: 6px; 
                padding: 4px 12px; 
                font-size: 12px; 
                font-family: {FONT_MONO};
                color: {C['text_b']};
            }}
            QLineEdit:focus {{ border-color: {C['purple']}; }}
        """)
        btn = QPushButton("Browse")
        btn.setFixedSize(80, 36)
        btn.setStyleSheet(f"background: {C['bg_sidebar']}; border: 1px solid {C['border']}; color: {C['white']}; border-radius: 6px; font-weight: 600;")
        row.addWidget(lbl)
        row.addWidget(edit)
        row.addWidget(btn)
        row.addStretch()
        return row, edit


class RadioIndicator(QWidget):
    """Circular radio-style indicator."""
    def __init__(self, selected=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self._selected = selected

    def set_selected(self, selected: bool):
        self._selected = selected
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Outer circle
        p.setPen(QPen(QColor(C["purple"] if self._selected else C["border_b"]), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(1, 1, 15, 15)

        # Inner dot
        if self._selected:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(C["purple"])))
            p.drawEllipse(4, 4, 9, 9)


class DeviceCard(QWidget):
    """Selectable device card for Settings page."""
    from PyQt6.QtCore import pyqtSignal as _sig
    clicked = _sig(object)  # emits ComputeDevice

    TYPE_ICONS = {"cpu": "🧠", "cuda": "🚀", "directml": "⚡"}
    TYPE_COLORS = {
        "cpu":       C["text_d"],
        "cuda":      C["green"],
        "directml":  C["cyan"],
    }

    def __init__(self, device: ComputeDevice, selected=False, parent=None):
        super().__init__(parent)
        self.device = device
        self._selected = selected
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Radio Dot
        self.radio = RadioIndicator(selected=self._selected)
        layout.addWidget(self.radio)

        # Type icon
        icon = QLabel(self.TYPE_ICONS.get(self.device.device_type, "💻"))
        icon.setStyleSheet("font-size: 20px;")
        icon.setFixedWidth(28)
        layout.addWidget(icon)

        # Info
        info = QVBoxLayout()
        name_lbl = QLabel(self.device.name)
        name_lbl.setStyleSheet(f"color: {C['white']}; font-size: 13px; font-weight: 700;")
        desc_lbl = QLabel(self.device.description)
        desc_lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 11px;")
        info.addWidget(name_lbl)
        info.addWidget(desc_lbl)
        layout.addLayout(info)
        layout.addStretch()

        # Type badge
        type_color = self.TYPE_COLORS.get(self.device.device_type, C["text_d"])
        badge = QLabel(self.device.device_type.upper())
        badge.setStyleSheet(f"""
            color: {type_color};
            background: {type_color}20;
            border: 1px solid {type_color}50;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 700;
        """)
        layout.addWidget(badge)

        # VRAM info
        if self.device.memory_mb > 0:
            mem_gb = self.device.memory_mb / 1024
            mem_lbl = QLabel(f"{mem_gb:.1f} GB")
            mem_lbl.setStyleSheet(f"color: {C['text_b']}; font-size: 13px; font-weight: 700; min-width: 60px; text-align: right;")
            layout.addWidget(mem_lbl)

    def _apply_style(self):
        border = C["purple"] if self._selected else C["border"]
        bg     = "#1c1c3c" if self._selected else C["bg_card"]
        thickness = "2px" if self._selected else "1px"
        self.setStyleSheet(f"""
            DeviceCard {{
                background: {bg};
                border: {thickness} solid {border};
                border-radius: 8px;
            }}
            DeviceCard:hover {{
                border-color: {C['purple_l']};
                background: {C['bg_panel']};
            }}
        """)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.radio.set_selected(selected)
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.device)
        super().mousePressEvent(event)
