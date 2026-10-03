"""
GPU/CPU status bar shown at top of training pages.
Shows device name, VRAM used, utilization, temperature.
Updates every 3 seconds.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import QTimer
from app.theme import C, FONT_MONO
from backend.core.settings_manager import settings
from backend.core.gpu_manager import get_live_gpu_stats


class GpuBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(3000)
        self._refresh()

    def _build_ui(self):
        self.setStyleSheet(f"""
            background: {C['bg_panel']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            padding: 4px 12px;
        """)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 4, 12, 4)
        row.setSpacing(12)

        def lbl(text, color=C['text_d'], mono=False):
            l = QLabel(text)
            font_family = FONT_MONO if mono else "Segoe UI"
            l.setStyleSheet(f"color:{color}; font-size:11px; font-family:'{font_family}';")
            return l

        self.device_lbl  = lbl("CPU", C['purple_l'])
        self.mem_lbl     = lbl("VRAM: —", C['text_b'])
        self.util_lbl    = lbl("Util: —", C['text'])
        self.temp_lbl    = lbl("Temp: —", C['text'])
        
        self.vram_bar = QProgressBar()
        self.vram_bar.setFixedSize(100, 8)
        self.vram_bar.setTextVisible(False)
        self.vram_bar.setStyleSheet(f"""
            QProgressBar {{ background: {C['border']}; border-radius: 4px; border: none; }}
            QProgressBar::chunk {{ background: {C['purple']}; border-radius: 4px; }}
        """)
        
        self.train_dot = QLabel("●")
        self.train_dot.setStyleSheet(f"color: {C['green']}; font-size: 14px; margin-left: 10px;")
        self.train_lbl = lbl("TRAINING ACTIVE", C['green'])
        self.train_lbl.setGraphicsEffect(None) # Placeholder for pulse

        row.addWidget(lbl("COMPUTE:", C['text_d']))
        row.addWidget(self.device_lbl)
        # 15px spacer acts as the separator now
        row.addSpacing(15)
        row.addWidget(self.mem_lbl)
        row.addWidget(self.vram_bar)
        row.addSpacing(15)
        row.addWidget(self.util_lbl)
        row.addSpacing(15)
        row.addWidget(self.temp_lbl)
        row.addSpacing(15)
        
        row.addWidget(self.train_dot)
        row.addWidget(self.train_lbl)
        row.addStretch()
        self.setFixedHeight(44)
        
        self.train_dot.hide()
        self.train_lbl.hide()

    def set_training(self, active: bool):
        if active:
            self.train_dot.show()
            self.train_lbl.show()
        else:
            self.train_dot.hide()
            self.train_lbl.hide()

    def _refresh(self):
        device_id   = settings.get("compute_device_id", "cpu")
        device_name = settings.get("compute_device_name", "CPU")
        device_type = settings.get("compute_device_type", "cpu")

        self.device_lbl.setText(device_name)

        if device_type != "cpu":
            from backend.core.gpu_manager import ComputeDevice
            dev = ComputeDevice(
                id=device_id, name=device_name, device_type=device_type, 
                memory_mb=0, available=True, description="", tf_device_string=""
            )
            stats = get_live_gpu_stats(dev)
            if stats["mem_total"] > 0:
                pct = int(stats["mem_used"] / stats["mem_total"] * 100)
                self.mem_lbl.setText(
                    f"VRAM: {stats['mem_used']}MB / {stats['mem_total']}MB ({pct}%)"
                )
                self.vram_bar.setValue(pct)
                self.util_lbl.setText(f"Util: {stats['util_pct']}%")
                self.temp_lbl.setText(f"Temp: {stats['temp_c']}°C")
                
                # Temperature warnings
                if stats["temp_c"] > 90: self.temp_lbl.setStyleSheet(f"color: {C['status_error']};")
                elif stats["temp_c"] > 80: self.temp_lbl.setStyleSheet(f"color: {C['amber']};")
                else: self.temp_lbl.setStyleSheet(f"color: {C['text']};")
        else:
            self.mem_lbl.setText("System RAM")
            self.vram_bar.setValue(0)
            self.util_lbl.setText("CPU mode")
            self.temp_lbl.setText("")
