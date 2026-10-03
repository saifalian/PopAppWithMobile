import os
import json
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QInputDialog, QMessageBox, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont

from app.theme import C

logger = logging.getLogger(__name__)

class MobileCalibrationDialog(QDialog):
    """
    Interactive tool to map UI elements across multiple mobile screens.
    Now supports both Click and Swipe detection with Live Sync.
    """
    markers_changed = pyqtSignal(list)

    def __init__(self, mobile_mgr, model_name, parent=None):
        super().__init__(parent)
        self.mobile_mgr = mobile_mgr
        self.model_name = model_name
        self.setWindowTitle(f"Manual Calibration - {model_name}")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(f"background: {C['bg_sidebar']}; color: {C['white']};")
        
        self.points = [] # List of {"name", "x", "y", "screen_w", "screen_h"}
        self.current_pixmap = None
        self.screen_res = (0, 0)
        
        self._load_existing_points()
        self._build_ui()
        self._capture_screen() # Initial capture

    def _load_existing_points(self):
        """Load existing UI elements from config.json."""
        try:
            path = Path("models") / self.model_name / "config.json"
            if path.exists():
                with open(path, "r") as f:
                    conf = json.load(f)
                    self.points = conf.get("mobile", {}).get("ui_elements", [])
        except Exception as e:
            logger.error(f"Error loading calibration points: {e}")

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Left: Toolbar ---
        toolbar = QFrame()
        toolbar.setFixedWidth(220)
        toolbar.setStyleSheet(f"background: {C['bg_panel']}; border-right: 1px solid {C['border']};")
        tl = QVBoxLayout(toolbar)
        tl.setContentsMargins(15, 20, 15, 20)
        tl.setSpacing(15)
        
        title = QLabel("CALIBRATION")
        title.setStyleSheet(f"color: {C['purple_l']}; font-weight: bold; font-size: 14px; letter-spacing: 2px;")
        tl.addWidget(title)
        
        desc = QLabel("1. Navigate on phone\n2. Click 'Capture Screen'\n3. Click for Tap, Drag for Swipe")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {C['text_d']}; font-size: 11px;")
        tl.addWidget(desc)
        
        self.btn_capture = QPushButton("📸 CAPTURE SCREEN")
        self.btn_capture.setFixedHeight(40)
        self.btn_capture.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_capture.setStyleSheet(f"background: {C['purple']}; color: white; border-radius: 4px; font-weight: bold;")
        self.btn_capture.clicked.connect(self._capture_screen)
        tl.addWidget(self.btn_capture)
        
        tl.addSpacing(10)
        tl.addWidget(QLabel("MAPPED ELEMENTS:"))
        
        self.points_list = QWidget()
        self.points_layout = QVBoxLayout(self.points_list)
        self.points_layout.setContentsMargins(0,0,0,0)
        self.points_layout.setSpacing(5)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.points_list)
        tl.addWidget(scroll)
        
        self.btn_save = QPushButton("💾 SAVE ALL")
        self.btn_save.setFixedHeight(40)
        self.btn_save.setStyleSheet(f"background: {C['green']}; color: black; border-radius: 4px; font-weight: bold;")
        self.btn_save.clicked.connect(self._save_and_exit)
        tl.addWidget(self.btn_save)
        
        layout.addWidget(toolbar)
        
        # --- Right: Image Viewer ---
        self.viewer = QLabel()
        self.viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer.setCursor(Qt.CursorShape.CrossCursor)
        self.viewer.mousePressEvent = self._on_viewer_pressed
        self.viewer.mouseReleaseEvent = self._on_viewer_released
        
        self._start_point = None # Used for drag detection
        
        view_scroll = QScrollArea()
        view_scroll.setWidgetResizable(True)
        view_scroll.setWidget(self.viewer)
        layout.addWidget(view_scroll)

        self._refresh_points_list()

    def _capture_screen(self):
        """Get fresh screenshot from phone."""
        self.btn_capture.setText("⏳ CAPTURING...")
        self.btn_capture.setEnabled(False)
        self.repaint()
        
        # We manually process events to show the wait state
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        data = self.mobile_mgr.get_screenshot()
        if data:
            image = QImage.fromData(data)
            if not image.isNull():
                self.screen_res = (image.width(), image.height())
                # Store native pixmap for overlay logic
                self.native_pixmap = QPixmap.fromImage(image)
                self._draw_overlay()
            else:
                QMessageBox.warning(self, "Capture Failed", "Received empty or invalid image data.")
        else:
            QMessageBox.warning(self, "Connection Error", "Could not capture phone screen. Is ADB connected?")
            
        self.btn_capture.setText("📸 CAPTURE SCREEN")
        self.btn_capture.setEnabled(True)

    def _on_viewer_pressed(self, event):
        if not self.current_pixmap: return
        self._start_point = event.pos()

    def _on_viewer_released(self, event):
        if not self._start_point or not self.current_pixmap: return
        
        end_p = event.pos()
        dist = ((end_p.x() - self._start_point.x())**2 + (end_p.y() - self._start_point.y())**2)**0.5
        
        # 1. Map widget coordinates to display-pixmap coordinates
        v_w, v_h = self.viewer.width(), self.viewer.height()
        i_w, i_h = self.current_pixmap.width(), self.current_pixmap.height()
        off_x = (v_w - i_w) // 2 if v_w > i_w else 0
        off_y = (v_h - i_h) // 2 if v_h > i_h else 0
        
        def map_p(p):
            return p.x() - off_x, p.y() - off_y

        ax1, ay1 = map_p(self._start_point)
        ax2, ay2 = map_p(end_p)

        # Basic bounds check (must be on image)
        if not (0 <= ax1 <= i_w and 0 <= ay1 <= i_h): return

        # 2. Convert display-pixmap coords → native phone resolution
        #    self.screen_res holds the actual pixel dimensions of the phone screenshot
        native_w, native_h = self.screen_res
        if i_w > 0 and i_h > 0 and native_w > 0 and native_h > 0:
            scale_x = native_w / i_w
            scale_y = native_h / i_h
        else:
            scale_x = scale_y = 1.0

        is_swipe = dist > 20
        type_str = "Swipe" if is_swipe else "Tap"
        
        nx1 = int(ax1 * scale_x)
        ny1 = int(ay1 * scale_y)
        if is_swipe:
            nx2 = int(ax2 * scale_x)
            ny2 = int(ay2 * scale_y)
        else:
            # Force tap to be a single coordinate point
            nx2 = nx1
            ny2 = ny1
        
        # Auto-name: "Tap 1", "Swipe 2", etc.
        index = len(self.points) + 1
        name = f"{type_str} {index}"
        
        new_pt = {
            "name": name,
            # Native phone coordinates — used directly by remote_tap / remote_swipe
            "x1": nx1, "y1": ny1,
            "x2": nx2, "y2": ny2,
            "x": nx1, "y": ny1,           # shorthand for tap
            "type": type_str.lower(),
            # Store native resolution so _draw_overlay can scale back correctly
            "sw": native_w, "sh": native_h
        }
        
        self.points.append(new_pt)
        self._live_save()
        self._draw_overlay()
        self._refresh_points_list()
        self.markers_changed.emit(self.points)
        
        self._start_point = None

    def _live_save(self):
        """Immediately save to config.json."""
        try:
            from backend.core.model_manager import save_model_config, load_model_config
            conf = load_model_config(self.model_name)
            if "mobile" not in conf: conf["mobile"] = {}
            conf["mobile"]["ui_elements"] = self.points
            save_model_config(self.model_name, conf)
        except Exception as e:
            logger.error(f"Live Save failed: {e}")

    def _draw_overlay(self):
        if not hasattr(self, "native_pixmap") or not self.native_pixmap: return
        
        # 1. Scale native pixmap to fit the viewer's current size
        # Subtract some padding to avoid scrollbars triggering
        target_w = self.viewer.parent().width() - 20
        target_h = self.viewer.parent().height() - 20
        
        scaled_pixmap = self.native_pixmap.scaled(
            target_w, target_h, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.current_pixmap = scaled_pixmap # This is what the click-logic uses
        
        canvas = scaled_pixmap.copy()
        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 2. Draw markers (scaled to current view)
        for pt in self.points:
            # Scale point from native (sw, sh) to current canvas size
            scale_x = canvas.width() / pt["sw"]
            scale_y = canvas.height() / pt["sh"]
            x1, y1 = int(pt["x1"] * scale_x), int(pt["y1"] * scale_y)
            x2, y2 = int(pt["x2"] * scale_x), int(pt["y2"] * scale_y)
            
            p.setPen(QPen(QColor(C['purple_l']), 2)) # Thinner pen for cleaner circles
            p.setBrush(QColor(C['purple_l'] + "33"))
            
            p_type = pt.get("type", "tap").lower()
            if p_type == "swipe":
                # Draw arrow for swipe
                p.drawLine(x1, y1, x2, y2)
                # Draw simple arrowhead
                import math
                angle = math.atan2(y2 - y1, x2 - x1)
                arrow_size = 10
                p.drawLine(x2, y2, int(x2 - arrow_size * math.cos(angle - math.pi/6)), int(y2 - arrow_size * math.sin(angle - math.pi/6)))
                p.drawLine(x2, y2, int(x2 - arrow_size * math.cos(angle + math.pi/6)), int(y2 - arrow_size * math.sin(angle + math.pi/6)))
                # Start circle
                p.drawEllipse(QPoint(x1, y1), 4, 4)
            else:
                # Draw persistent marker for tap
                p.drawEllipse(QPoint(x1, y1), 8, 8)
            
            # Label
            p.setPen(QColor(C['white']))
            p.setFont(QFont("Inter", 10, QFont.Weight.Bold))
            p.drawText(x1 + 12, y1 + 5, pt["name"])
            
        p.end()
        self.viewer.setPixmap(canvas)

    def _refresh_points_list(self):
        """Update the markers list in the sidebar of the popup."""
        # Clear current safely (including spacers)
        while self.points_layout.count():
            item = self.points_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for i, pt in enumerate(self.points):
            item = QWidget()
            il = QHBoxLayout(item); il.setContentsMargins(5, 2, 5, 2)
            il.setSpacing(2)
            
            lbl = QLabel(f"{i+1}. {pt['name']}")
            lbl.setStyleSheet("color: white; font-size: 11px;")
            il.addWidget(lbl, 1)
            
            btn_rename = QPushButton("✏️")
            btn_rename.setFixedSize(20, 20)
            btn_rename.setStyleSheet(f"background: transparent; color: {C['text_d']}; border: none; font-size: 10px;")
            btn_rename.clicked.connect(lambda _, idx=i: self._rename_point(idx))
            il.addWidget(btn_rename)
            
            btn_del = QPushButton("×")
            btn_del.setFixedSize(20, 20)
            btn_del.setStyleSheet(f"background: {C['red']}33; color: {C['red']}; border: none; border-radius: 3px;")
            btn_del.clicked.connect(lambda _, idx=i: self._remove_point(idx))
            il.addWidget(btn_del)
            
            self.points_layout.addWidget(item)
        self.points_layout.addStretch()

    def _rename_point(self, idx):
        if 0 <= idx < len(self.points):
            old_name = self.points[idx]["name"]
            new_name, ok = QInputDialog.getText(self, "Rename Element", "New name for this element:", text=old_name)
            if ok and new_name:
                self.points[idx]["name"] = new_name
                self._live_save()
                self._draw_overlay()
                self._refresh_points_list()
                self.markers_changed.emit(self.points)

    def _remove_point(self, idx):
        if 0 <= idx < len(self.points):
            self.points.pop(idx)
            self._live_save()
            self._draw_overlay()
            self._refresh_points_list()
            self.markers_changed.emit(self.points)

    def _save_and_exit(self):
        # We already save live, so just close
        self.accept()
