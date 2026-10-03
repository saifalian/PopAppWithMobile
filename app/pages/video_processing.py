"""
Video Processing page.
Frame extraction, labeling, and dataset preparation.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QListWidget, QFrame, QSplitter, QTextEdit,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap
import os
from pathlib import Path
from app.theme import C, FONT_UI, FONT_MONO
from backend.core.settings_manager import settings
from backend.video.processor import VideoMetadata, VideoExtractionWorker


class VideoProcessingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.current_folder = settings.get("video_recordings_dir", "")
        self._build_ui()
        self._load_video_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        # ── Header ──────────────────────────────────────────────
        header_v = QVBoxLayout()
        header = QHBoxLayout()
        title = QLabel("Video Processing")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()
        
        self.btn_select_dir = QPushButton("📂  Select Recordings Folder")
        self.btn_select_dir.setStyleSheet(f"background: {C['bg_sidebar']}; color: {C['text_b']}; border: 1px solid {C['border']}; padding: 8px 16px; border-radius: 6px;")
        self.btn_select_dir.clicked.connect(self._on_select_dir)
        header.addWidget(self.btn_select_dir)
        header_v.addLayout(header)
        
        subtitle = QLabel("Extract labeled datasets from recording sessions for unsupervised or supervised training.")
        subtitle.setStyleSheet(f"color: {C['text_d']}; font-size: 13px;")
        header_v.addWidget(subtitle)
        
        root.addLayout(header_v)

        # ── Main Content Split ──────────────────────────────────
        content = QHBoxLayout()
        content.setSpacing(20)

        # ── Left: Video Selection ──────────────────────────────
        left_panel = QFrame()
        left_panel.setObjectName("panel_left")
        left_panel.setFixedWidth(320)
        left_panel.setStyleSheet(f"""
            #panel_left {{
                background: {C['bg_sidebar']};
                border-right: 1px solid {C['border']};
                border-radius: 8px;
            }}
        """)
        ll = QVBoxLayout(left_panel)
        ll.setContentsMargins(16, 20, 16, 20)
        ll.setSpacing(12)

        l_title = QLabel("RECORDED VIDEOS")
        l_title.setStyleSheet(f"color: {C['text_d']}; font-size: 10px; font-weight: 800; letter-spacing: 1.5px;")
        ll.addWidget(l_title)

        self.video_list = QListWidget()
        self.video_list.setObjectName("video_list")
        self.video_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {C['text']};
                font-size: 13px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: 4px;
                margin-bottom: 2px;
            }}
            QListWidget::item:hover {{
                background: {C['bg_panel']};
                color: {C['white']};
            }}
            QListWidget::item:selected {{
                background: {C['purple']}33;
                color: {C['white']};
                border-left: 3px solid {C['purple']};
            }}
        """)
        ll.addWidget(self.video_list)
        
        ll.addStretch()
        content.addWidget(left_panel)

        # ── Right: Operations ──────────────────────────────────
        right_panel = QFrame()
        right_panel.setObjectName("panel_right")
        right_panel.setStyleSheet(f"""
            #panel_right {{
                background: {C['bg_panel']};
                border: 1px solid {C['border']};
                border-radius: 8px;
            }}
        """)
        rl = QVBoxLayout(right_panel)
        rl.setContentsMargins(24, 24, 24, 24)
        rl.setSpacing(20)

        # 1. Info Bar & Thumbnail
        info_frame = QFrame()
        info_frame.setFixedHeight(320)
        info_frame.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; border-radius: 12px;")
        il = QVBoxLayout(info_frame)
        il.setContentsMargins(0, 0, 0, 0)
        
        # Thumbnail area
        self.thumb = QLabel()
        self.thumb.setFixedSize(600, 200)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setStyleSheet(f"background: #000; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        # Set placeholder (will update in _on_video_selected if I had real ones)
        self.thumb.setText("No Video Selected")
        il.addWidget(self.thumb)
        
        meta_area = QWidget()
        ml = QHBoxLayout(meta_area)
        ml.setContentsMargins(24, 16, 24, 16)
        
        vid_meta = QVBoxLayout()
        self.vid_name = QLabel("No video selected")
        self.vid_name.setStyleSheet(f"color: {C['white']}; font-size: 20px; font-weight: 800;")
        self.vid_details = QLabel("Select an MP4 from the list to begin.")
        self.vid_details.setStyleSheet(f"color: {C['text_d']}; font-size: 13px;")
        vid_meta.addWidget(self.vid_name)
        vid_meta.addWidget(self.vid_details)
        ml.addLayout(vid_meta)
        ml.addStretch()
        
        self.btn_play_preview = QPushButton("▶ PREVIEW")
        self.btn_play_preview.setFixedSize(110, 40)
        self.btn_play_preview.setStyleSheet(f"background: {C['bg_panel']}; color: {C['white']}; border: 1px solid {C['border_b']}; border-radius: 20px; font-weight: 800; font-size: 11px;")
        ml.addWidget(self.btn_play_preview)
        
        il.addWidget(meta_area)
        rl.addWidget(info_frame)

        # 2. Controls
        rl.addWidget(self._section_label("PROCESSING & EXTRACTION"))
        
        proc_box = QHBoxLayout()
        proc_box.setSpacing(16)
        
        self.extract_btn = QPushButton("🎞    Extract Frames")
        self.extract_btn.setObjectName("btn_cpu")
        self.extract_btn.setMinimumHeight(52)
        proc_box.addWidget(self.extract_btn, 1)
        
        self.label_btn = QPushButton("🏷    Auto-Label Session")
        self.label_btn.setObjectName("btn_gpu")
        self.label_btn.setMinimumHeight(52)
        proc_box.addWidget(self.label_btn, 1)
        rl.addLayout(proc_box)

        # 3. Progress
        rl.addSpacing(10)
        prog_header = QHBoxLayout()
        self.status_lbl = QLabel("READY")
        self.status_lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 11px; font-weight: 800;")
        prog_header.addWidget(self.status_lbl)
        prog_header.addStretch()
        self.prog_pct = QLabel("0%")
        self.prog_pct.setStyleSheet(f"color: {C['text_d']}; font-size: 11px;")
        prog_header.addWidget(self.prog_pct)
        rl.addLayout(prog_header)

        self.prog = QProgressBar()
        self.prog.setFixedHeight(6)
        rl.addWidget(self.prog)

        # 4. Logs
        rl.addWidget(self._section_label("EXTRACTION LOGS"))
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setStyleSheet(f"""
            background: {C['bg_darkest']};
            color: #64748b;
            border: 1px solid {C['border']};
            border-radius: 6px;
            font-family: "{FONT_MONO}";
            font-size: 11px;
            padding: 8px;
        """)
        rl.addWidget(self.logs, 1)

        content.addWidget(right_panel, 1)
        root.addLayout(content)

        # Connections
        self.video_list.currentTextChanged.connect(self._on_video_selected)
        self.extract_btn.clicked.connect(lambda: self._start_processing(auto_label=False))
        self.label_btn.clicked.connect(lambda: self._start_processing(auto_label=True))
        
    def _on_select_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video Recordings Folder", self.current_folder)
        if folder:
            self.current_folder = folder
            settings.set("video_recordings_dir", folder)
            settings.save()
            self._load_video_list()
            
    def _load_video_list(self):
        self.video_list.clear()
        if not self.current_folder or not os.path.exists(self.current_folder):
            self.logs.append(f"<span style='color: {C['amber']};'>[WARN]</span> Invalid directory set.")
            return
            
        count = 0
        for f in os.listdir(self.current_folder):
            if f.lower().endswith(('.mp4', '.avi', '.mkv', '.webm')):
                self.video_list.addItem(f)
                count += 1
                
        self.logs.append(f"<span style='color: {C['green']};'>[INFO]</span> Loaded {count} videos from {self.current_folder}")

    def _section_label(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text_d']}; font-size: 10px; font-weight: 800; letter-spacing: 1.5px;")
        return l

    def _on_video_selected(self, name):
        if not name or not self.current_folder: return
        self.vid_name.setText(name)
        
        full_path = os.path.join(self.current_folder, name)
        
        self.status_lbl.setText("LOADING METADATA...")
        self.status_lbl.setStyleSheet(f"color: {C['amber']}; font-size: 11px; font-weight: 800;")
        
        # This blocks UI momentarily, but it's okay for local files. 
        # For remote, it should be threaded.
        info = VideoMetadata.get_info(full_path)
        
        if "error" in info:
            self.vid_details.setText(f"Error loading metadata: {info['error']}")
            return
            
        self.vid_details.setText(f"Duration: {info['duration']}  ·  Resolution: {info['resolution']}  ·  Size: {info['size']}  ·  FPS: {info['fps']}")
        
        if info.get("thumb_path") and os.path.exists(info["thumb_path"]):
            self.thumb.setPixmap(QPixmap(info["thumb_path"]).scaled(600, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        
        self.status_lbl.setText("READY")
        self.status_lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 11px; font-weight: 800;")
        self.logs.append(f"<span style='color: {C['purple_l']};'>[INFO]</span> Selected source: <b>{name}</b>")

    def _start_processing(self, auto_label=False):
        name = self.video_list.currentItem().text() if self.video_list.currentItem() else None
        if not name:
            QMessageBox.warning(self, "No Video", "Please select a video first.")
            return
            
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.logs.append(f"<span style='color: {C['amber']};'>[PROC]</span> Stopping current worker...")
            self.worker.wait()
            
        full_path = os.path.join(self.current_folder, name)
            
        self.status_lbl.setText("EXTRACTING..." if not auto_label else "AUTO-LABELING...")
        self.status_lbl.setStyleSheet(f"color: {C['amber']}; font-size: 11px; font-weight: 800;")
        
        self.prog.setValue(0)
        self.prog_pct.setText("0%")
        
        self.worker = VideoExtractionWorker(full_path, extract_every_n_frames=30, auto_label=auto_label)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.log_msg.connect(self._on_worker_log)
        self.worker.finished.connect(self._on_worker_finished)
        
        self.extract_btn.setEnabled(False)
        self.label_btn.setText("⏹ Stop")
        
        # Disconnect old and reconnect to stop
        self.label_btn.clicked.disconnect()
        self.label_btn.clicked.connect(self._stop_processing)
        
        self.worker.start()
        
    def _stop_processing(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            
    def _on_worker_progress(self, pct):
        self.prog.setValue(pct)
        self.prog_pct.setText(f"{pct}%")
        
    def _on_worker_log(self, level, msg):
        color = C['text']
        if level == "error": color = C['status_error']
        elif level == "warning": color = C['amber']
        elif level == "success": color = C['green']
        elif level == "info": color = C['purple_l']
        
        self.logs.append(f"<span style='color: {color};'>[{level.upper()}]</span> {msg}")
        
    def _on_worker_finished(self, success, msg):
        self.extract_btn.setEnabled(True)
        self.label_btn.setText("🏷    Auto-Label Session")
        self.label_btn.clicked.disconnect()
        self.label_btn.clicked.connect(lambda: self._start_processing(auto_label=True))
        
        if success:
            self.status_lbl.setText("COMPLETE")
            self.status_lbl.setStyleSheet(f"color: {C['green']}; font-size: 11px; font-weight: 800;")
            self.prog.setValue(100)
            self.prog_pct.setText("100%")
        else:
            self.status_lbl.setText("FAILED / STOPPED")
            self.status_lbl.setStyleSheet(f"color: {C['status_error']}; font-size: 11px; font-weight: 800;")
