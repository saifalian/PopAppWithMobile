from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QCheckBox, 
                             QComboBox, QTextEdit, QProgressBar, QRadioButton, 
                             QButtonGroup, QSpinBox, QDoubleSpinBox, QGridLayout,
                             QApplication, QSlider)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor

from app.theme import C, FONT_MONO
from app.widgets.trend_chart import TrendChart
from pathlib import Path

class SectionHeader(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; font-weight: bold; letter-spacing: 1.5px; margin-top: 15px; margin-bottom: 5px;")

class ModernCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 6px;")

class LearnTab(QWidget):
    # Signals for ModelScreen to handle
    train_requested = pyqtSignal(str) # 'cpu' or 'gpu'
    stop_requested = pyqtSignal()
    export_requested = pyqtSignal()
    wizard_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_name = ""
        self.config = {}
        self.worker = None
        
        # Split layout: Left (Config) / Right (Monitor)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- LEFT COLUMN (CONFIG) ---
        self.left_scroll = QScrollArea()
        self.left_scroll.setFixedWidth(340)
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.left_scroll.setStyleSheet(f"background: {C['bg_sidebar']}; border-right: 1px solid {C['border']};")
        
        left_widget = QWidget()
        self.left_vbox = QVBoxLayout(left_widget)
        self.left_vbox.setContentsMargins(20, 20, 20, 20)
        self.left_vbox.setSpacing(15)
        
        self._setup_left_column()
        self.left_scroll.setWidget(left_widget)
        self.main_layout.addWidget(self.left_scroll)
        
        # --- RIGHT COLUMN (MONITOR) ---
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background: {C['bg_darkest']};")
        self.right_vbox = QVBoxLayout(right_panel)
        self.right_vbox.setContentsMargins(30, 20, 30, 20)
        self.right_vbox.setSpacing(15)
        
        self._setup_right_column()
        self.main_layout.addWidget(right_panel)
        
        # Status update timer (to refresh stats)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_dataset_stats)
        self.refresh_timer.start(5000)

    def _setup_left_column(self):
        # SECTION 1: DATASET STATUS
        self.left_vbox.addWidget(SectionHeader("Dataset Status"))
        self.stats_card = ModernCard()
        sl = QVBoxLayout(self.stats_card)
        self.lbl_vid_count = QLabel("Videos: 0")
        self.lbl_frame_count = QLabel("Frames: 0")
        self.lbl_label_count = QLabel("Labeled: 0 (0%)")
        self.lbl_compile_status = QLabel("Compiled: ❌ NO")
        for lbl in [self.lbl_vid_count, self.lbl_frame_count, self.lbl_label_count, self.lbl_compile_status]:
            lbl.setStyleSheet(f"color: {C['text']}; font-size: 12px; border: none;")
            sl.addWidget(lbl)
            
        self.imbalance_warning = QLabel("")
        self.imbalance_warning.setWordWrap(True)
        self.imbalance_warning.setStyleSheet(f"color: {C['amber']}; font-size: 10px; font-weight: bold; border: none;")
        sl.addWidget(self.imbalance_warning)
        
        self.btn_go_label = QPushButton("Go to Label Tab →")
        self.btn_go_label.setStyleSheet(f"color: {C['cyan']}; background: transparent; border: none; font-size: 11px; text-decoration: underline;")
        self.btn_go_label.setCursor(Qt.CursorShape.PointingHandCursor)
        sl.addWidget(self.btn_go_label)
        self.left_vbox.addWidget(self.stats_card)
        
        # SECTION 2: LEARNING MODE
        self.left_vbox.addWidget(SectionHeader("Learning Mode"))
        self.mode_group = QButtonGroup(self)
        self.rdo_imitation = QRadioButton("Imitation Learning (Fresh)")
        self.rdo_fine_tune = QRadioButton("Fine-tune (Current Best)")
        self.rdo_backbone = QRadioButton("Backbone Optimization")
        
        for i, rdo in enumerate([self.rdo_imitation, self.rdo_fine_tune, self.rdo_backbone]):
            rdo.setStyleSheet(f"color: {C['text']}; font-size: 12px;")
            self.mode_group.addButton(rdo, i)
            self.left_vbox.addWidget(rdo)
        self.rdo_imitation.setChecked(True)
        
        # SECTION 3: TRANSFER LEARNING
        self.left_vbox.addWidget(SectionHeader("Transfer Learning"))
        self.combo_transfer = QComboBox()
        self.combo_transfer.addItem("None (ImageNet weights)")
        self.combo_transfer.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['white']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 5px;")
        self.left_vbox.addWidget(self.combo_transfer)
        
        # SECTION 4: HYPERPARAMETERS
        self.left_vbox.addWidget(SectionHeader("Hyperparameters"))
        params_grid = QGridLayout()
        params_grid.setSpacing(10)
        
        params_grid.addWidget(QLabel("Epochs:"), 0, 0)
        self.spin_epochs = QSpinBox()
        self.spin_epochs.setRange(1, 1000)
        self.spin_epochs.setValue(20)
        params_grid.addWidget(self.spin_epochs, 0, 1)
        
        params_grid.addWidget(QLabel("Batch:"), 1, 0)
        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(1, 128)
        self.spin_batch.setValue(8)
        self.spin_batch.valueChanged.connect(self._update_vram_estimation)
        params_grid.addWidget(self.spin_batch, 1, 1)
        
        params_grid.addWidget(QLabel("LR:"), 2, 0)
        self.spin_lr = QDoubleSpinBox()
        self.spin_lr.setRange(0.000001, 0.1)
        self.spin_lr.setDecimals(6)
        self.spin_lr.setValue(0.0005)
        params_grid.addWidget(self.spin_lr, 2, 1)
        
        for i in range(params_grid.count()):
            w = params_grid.itemAt(i).widget()
            if isinstance(w, QLabel): w.setStyleSheet(f"color: {C['text_d']}; font-size: 11px;")
            else: w.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['white']}; border: 1px solid {C['border']}; padding: 3px;")
            
        self.left_vbox.addLayout(params_grid)
        
        self.vram_est = QLabel("Estimated VRAM: 1.2 GB")
        self.vram_est.setStyleSheet(f"color: {C['cyan']}; font-size: 10px;")
        self.left_vbox.addWidget(self.vram_est)

        self.chk_balance = QCheckBox("Apply Class Balancing (Weights)")
        self.chk_balance.setStyleSheet(f"color: {C['text']}; font-size: 11px;")
        self.chk_balance.setToolTip("Automatically calculates loss weights to compensate for imbalanced data classes.")
        self.left_vbox.addWidget(self.chk_balance)

        self.lbl_unfreeze = QLabel("Unfreeze Layers (from end): 50")
        self.lbl_unfreeze.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; margin-top: 5px;")
        self.left_vbox.addWidget(self.lbl_unfreeze)
        self.slider_unfreeze = QSlider(Qt.Orientation.Horizontal)
        self.slider_unfreeze.setRange(0, 150)
        self.slider_unfreeze.setValue(50)
        self.slider_unfreeze.valueChanged.connect(lambda v: self.lbl_unfreeze.setText(f"Unfreeze Layers (from end): {v}"))
        self.left_vbox.addWidget(self.slider_unfreeze)
        self.slider_unfreeze.hide()
        
        # Show/Hide slider based on mode
        self.mode_group.idClicked.connect(self._on_mode_changed)
        
        # SECTION 5: PRE-FLIGHT & START
        self.left_vbox.addStretch()
        self.chk_valid = QCheckBox("Dataset is Ready ✓")
        self.chk_valid.setEnabled(False)
        self.chk_valid.setStyleSheet(f"color: {C['green']}; font-size: 11px;")
        self.left_vbox.addWidget(self.chk_valid)
        
        self.btn_gpu = QPushButton("🚀 START LEARNING (GPU)")
        self.btn_gpu.setFixedHeight(45)
        self.btn_gpu.setStyleSheet(f"background: {C['purple']}; color: white; border-radius: 6px; font-weight: bold; font-size: 14px;")
        self.btn_gpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gpu.clicked.connect(lambda: self.train_requested.emit('gpu'))
        self.left_vbox.addWidget(self.btn_gpu)
        
        self.btn_cpu = QPushButton("🖥️ Start Learning (CPU)")
        self.btn_cpu.setFixedHeight(35)
        self.btn_cpu.setStyleSheet(f"background: transparent; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 6px; font-size: 12px;")
        self.btn_cpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cpu.clicked.connect(lambda: self.train_requested.emit('cpu'))
        self.left_vbox.addWidget(self.btn_cpu)
        
        self.left_vbox.addSpacing(20)
        self.btn_wizard = QPushButton("🌙 Overnight Training Wizard")
        self.btn_wizard.setFixedHeight(45)
        self.btn_wizard.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['cyan']}; border: 1px solid {C['cyan']}; border-radius: 6px; font-weight: bold; font-size: 13px;")
        self.btn_wizard.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_wizard.clicked.connect(self.wizard_requested.emit)
        self.left_vbox.addWidget(self.btn_wizard)

    def _setup_right_column(self):
        # SECTION 6: MONITOR
        stats_row = QHBoxLayout()
        self.lbl_epoch = QLabel("0 / 0")
        self.lbl_best_acc = QLabel("0.0%")
        self.lbl_vram = QLabel("0 / 0 MB")
        
        for title, val, color in [("EPOCH", self.lbl_epoch, C['cyan']), 
                                  ("VAL ACCURACY", self.lbl_best_acc, C['green']), 
                                  ("VRAM USED", self.lbl_vram, C['amber'])]:
            card = ModernCard()
            cl = QVBoxLayout(card)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 10px; border: none;")
            val.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold; border: none;")
            cl.addWidget(val, alignment=Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(t_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
            stats_row.addWidget(card)
        self.right_vbox.addLayout(stats_row)
        
        self.right_vbox.addWidget(SectionHeader("Learning Progress"))
        self.chart = TrendChart()
        self.right_vbox.addWidget(self.chart)
        
        # SECTION 7: TERMINAL
        self.right_vbox.addWidget(SectionHeader("Learning Log"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['text']}; font-family: '{FONT_MONO}'; font-size: 11px; border: 1px solid {C['border']};")
        self.right_vbox.addWidget(self.log)
        
        # SECTION 8: CONTROLS
        self.ctrl_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {C['purple']}; }}")
        self.ctrl_row.addWidget(self.progress_bar)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setFixedWidth(80)
        self.btn_stop.setStyleSheet(f"background: {C['red']}22; color: {C['red']}; border: 1px solid {C['red']}; border-radius: 4px; font-weight: bold;")
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        self.btn_stop.setEnabled(False)
        self.ctrl_row.addWidget(self.btn_stop)
        self.right_vbox.addLayout(self.ctrl_row)

        # SECTION 9: COMPLETION
        self.completion_panel = ModernCard()
        self.completion_panel.hide()
        cl = QVBoxLayout(self.completion_panel)
        self.lbl_result = QLabel("Learning Complete!")
        self.lbl_result.setWordWrap(True)
        cl.addWidget(self.lbl_result)
        
        h_row = QHBoxLayout()
        self.btn_save_prod = QPushButton("🏆 Set as Production")
        self.btn_save_prod.setStyleSheet(f"background: {C['green']}; color: white; padding: 10px; font-weight: bold;")
        h_row.addWidget(self.btn_save_prod)
        
        self.btn_export = QPushButton("📱 Export to TFLite")
        self.btn_export.setStyleSheet(f"background: {C['cyan']}; color: white; padding: 10px; font-weight: bold;")
        self.btn_export.clicked.connect(self.export_requested.emit)
        h_row.addWidget(self.btn_export)
        cl.addLayout(h_row)
        self.right_vbox.addWidget(self.completion_panel)

    def _on_mode_changed(self, mode_id):
        # 2 is backbone_opt
        self.slider_unfreeze.setVisible(mode_id == 2)
        self.lbl_unfreeze.setVisible(mode_id == 2)
        self._update_vram_estimation()

    def set_model(self, name, config):
        self.model_name = name
        self.config = config
        self._refresh_dataset_stats()
        self._refresh_transfer_models()
        self._update_vram_estimation()

    def _refresh_dataset_stats(self):
        if not self.model_name: return
        try:
            from backend.data.label_manager import LabelManager
            from backend.data.dataset_builder import get_compile_status
            
            lm = LabelManager(self.model_name)
            stats = lm.get_extended_stats()
            comp_status = get_compile_status(self.model_name)
            
            self.lbl_vid_count.setText(f"Videos: {stats['video_count']}")
            self.lbl_frame_count.setText(f"Frames: {stats['total_frames']}")
            self.lbl_label_count.setText(f"Labeled: {stats['labeled']} ({stats['pct_complete']}%)")
            
            if comp_status['compiled']:
                s = comp_status['split_counts']
                self.lbl_compile_status.setText(f"Compiled: ✅ {s['train']}/{s['val']}/{s['test']}")
                self.lbl_compile_status.setStyleSheet(f"color: {C['green']};")
                self.chk_valid.setChecked(True)
                self.btn_gpu.setEnabled(True)
            else:
                self.lbl_compile_status.setText("Compiled: ❌ NO")
                self.lbl_compile_status.setStyleSheet(f"color: {C['status_error']};")
                self.chk_valid.setChecked(False)
                self.btn_gpu.setEnabled(False)
                
            if stats['imbalance_warnings']:
                self.imbalance_warning.setText(stats['imbalance_warnings'][0])
            else:
                self.imbalance_warning.setText("")
        except Exception as e:
            print(f"DEBUG: LearnTab stats error: {e}")

    def _refresh_transfer_models(self):
        import os
        self.combo_transfer.clear()
        self.combo_transfer.addItem("None (ImageNet weights)")
        try:
            models_dir = Path("models")
            for m in os.listdir(models_dir):
                if m != self.model_name and os.path.isdir(models_dir / m):
                    if (models_dir / m / "production" / "model").exists():
                        self.combo_transfer.addItem(f"{m} (Compatibility ✓)")
        except: pass

    def append_log(self, text):
        self.log.append(text)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def update_progress(self, val, msg):
        self.progress_bar.setValue(int(val * 100))
        if msg: self.append_log(msg)
        
    def on_epoch_end(self, epoch, logs):
        self.lbl_epoch.setText(f"{epoch} / {self.spin_epochs.value()}")
        acc = logs.get('val_accuracy', logs.get('val_mae', 0))
        if 'accuracy' in logs or 'val_accuracy' in logs:
            self.lbl_best_acc.setText(f"{acc*100:.1f}%")
        else:
            self.lbl_best_acc.setText(f"{acc:.3f}")
            
        if not hasattr(self, '_history'): self._history = []
        self._history.append(acc)
        self.chart.set_data(self._history)
        
    def on_gpu_stats(self, stats):
        if stats.get('available'):
            self.lbl_vram.setText(f"{stats['mem_used']} / {stats['mem_total']} MB")
        else:
            self.lbl_vram.setText("N/A")

    def set_learning_state(self, is_learning: bool):
        self.btn_gpu.setEnabled(not is_learning)
        self.btn_cpu.setEnabled(not is_learning)
        self.btn_stop.setEnabled(is_learning)
        self.spin_epochs.setEnabled(not is_learning)
        self.spin_batch.setEnabled(not is_learning)
        self.spin_lr.setEnabled(not is_learning)
        self.mode_group.setEnabled(not is_learning)
        self.combo_transfer.setEnabled(not is_learning)
        
        if is_learning:
            self.completion_panel.hide()
            self._history = []
            self.log.clear()
        else:
            self.progress_bar.setValue(0)

    def _update_vram_estimation(self):
        batch = self.spin_batch.value()
        # Rough estimate for MobileNetV2 with task heads at 224x224
        # Base: ~450MB, Each batch unit adds ~30MB (mixed precision)
        base_mb = 450
        mode_id = self.mode_group.checkedId()
        # id 0: imitation, 1: fine_tune, 2: backbone_opt
        if mode_id == 2:
            base_mb += 200 # More gradients
            
        est_mb = base_mb + (batch * 30)
        est_gb = est_mb / 1024.0
        self.vram_est.setText(f"Estimated VRAM: {est_gb:.1f} GB")
        
        if est_gb > 3.0: # Warning for 3050i (4GB)
            self.vram_est.setStyleSheet(f"color: {C['amber']}; font-size: 10px; font-weight: bold;")
            self.vram_est.setText(f"Estimated VRAM: {est_gb:.1f} GB ⚠️ High")
        else:
            self.vram_est.setStyleSheet(f"color: {C['cyan']}; font-size: 10px;")
