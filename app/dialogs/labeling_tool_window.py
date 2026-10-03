"""
10/10 Smart Labeling Tool
=========================
Professional annotation workspace with:
- Left Sidebar: All frames grouped by action (with frame counts)
- "Unlabeled" group always shown so user knows what needs work
- Center Canvas: High-res view for drawing bounding boxes
- Bottom Gallery: Filmstrip of filtered frames
- Toolbar: AI Auto-Label, Search Similar, Interpolate, Track
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QListWidget, QListWidgetItem, QGridLayout,
    QSplitter, QMessageBox, QInputDialog, QGraphicsView, QProgressBar,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtGui import QPixmap, QColor, QPen, QBrush, QFont, QPainter, QPolygonF
from PyQt6.QtCore import Qt, QSize, pyqtSignal, pyqtSlot, QRectF, QPointF, QThread
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from app.theme import C
from backend.data.label_manager import LabelManager
from backend.data.interpolator import Interpolator


# ── LOADING OVERLAY ─────────────────────────────────────────────────────────

class LoadingOverlay(QWidget):
    """Sleek, centered 10/10 Loading Screen with percentage."""
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # 🧪 10/10 OVERLAY: Make it a frameless, transparent shield that covers the window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Panel
        self.panel = QFrame(self)
        self.panel.setFixedSize(420, 260)
        self.panel.setStyleSheet(f"background: {C['bg_panel']}; border: 2px solid {C['border']}; border-radius: 16px;")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(15)
        
        self.title = QLabel("🤖 AI Mission Setup")
        self.title.setStyleSheet(f"color: {C['white']}; font-weight: bold; font-size: 18px; border: none; background: transparent;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.title)
        
        # Setup
        self.setup_box = QWidget()
        setup_layout = QVBoxLayout(self.setup_box)
        setup_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_sens = QLabel("Precision Sensitivity: 85%")
        self.lbl_sens.setStyleSheet(f"color: {C['cyan']}; font-size: 12px; border: none; background: transparent;")
        setup_layout.addWidget(self.lbl_sens)
        
        from PyQt6.QtWidgets import QSlider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 100); self.slider.setValue(85)
        self.slider.setStyleSheet(f"QSlider::handle:horizontal {{ background: {C['cyan']}; }}")
        self.slider.valueChanged.connect(lambda v: self.lbl_sens.setText(f"Precision Sensitivity: {v}%"))
        setup_layout.addWidget(self.slider)
        
        self.start_btn = QPushButton("🚀 LAUNCH AI ENGINE")
        self.start_btn.setStyleSheet(f"QPushButton {{ background: {C['cyan']}22; color: white; border: 1px solid {C['cyan']}; border-radius: 6px; padding: 12px; font-weight: bold; }} QPushButton:hover {{ background: {C['cyan']}; color: black; }}")
        setup_layout.addWidget(self.start_btn)
        panel_layout.addWidget(self.setup_box)
        
        # Loading
        self.loading_box = QWidget()
        loading_layout = QVBoxLayout(self.loading_box)
        loading_layout.setContentsMargins(0, 0, 0, 0)
        self.bar = QProgressBar()
        self.bar.setFixedHeight(10); self.bar.setTextVisible(False)
        self.bar.setStyleSheet(f"QProgressBar {{ background: {C['bg_darkest']}; border-radius: 5px; }} QProgressBar::chunk {{ background: {C['cyan']}; border-radius: 5px; }}")
        loading_layout.addWidget(self.bar)
        self.status = QLabel("Processing Pixels...")
        self.status.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; border: none; background: transparent;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.status)
        self.cancel_btn = QPushButton("Abort Process")
        self.cancel_btn.setStyleSheet(f"color: {C['red']}; border: none; background: transparent;")
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        loading_layout.addWidget(self.cancel_btn)
        panel_layout.addWidget(self.loading_box)
        self.loading_box.hide()
        
        self.hide()


    def show_setup(self, task_name, icon="🤖", callback=None):
        self.title.setText(f"{icon} {task_name}")
        self.setup_box.show(); self.loading_box.hide()
        try: self.start_btn.clicked.disconnect()
        except: pass
        self.start_btn.clicked.connect(lambda: callback(self.slider.value() / 100.0))
        self.sync_geometry()
        self.show()

    def show_loading(self, text="Processing..."):
        self.setup_box.hide(); self.loading_box.show()
        self.status.setText(text)

    def sync_geometry(self):
        """🧬 10/10 ABSOLUTE CENTER: Fill parent and center the panel mathematically."""
        if self.parentWidget():
            p_rect = self.parentWidget().rect()
            self.setGeometry(p_rect)
            self.panel.move(
                (p_rect.width() - self.panel.width()) // 2,
                (p_rect.height() - self.panel.height()) // 2
            )
            self.raise_()

    def showEvent(self, event):
        self.sync_geometry()
        super().showEvent(event)

    def resizeEvent(self, event):
        self.sync_geometry()
        super().resizeEvent(event)

    def paintEvent(self, event):
        """🧬 10/10 MANIFEST: Render the dark backdrop and enforce panel styling."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(5, 5, 10, 210))
        # Support custom style sheets for child frames
        from PyQt6.QtWidgets import QStyle, QStyleOption
        opt = QStyleOption(); opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

    def update_progress(self, current, total, text=""):
        pct = int((current / total) * 100) if total > 0 else 0
        self.bar.setValue(pct)
        # 🧪 No more double percentages: Use the message or a default
        self.status.setText(text if text else f"Task Progress: {pct}% complete")


# ── AI WORKER ────────────────────────────────────────────────────────────

class AIWorker(QThread):
    """Background thread to keep UI smooth while AI handles pixels."""
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object) 
    error = pyqtSignal(str)

    def __init__(self, task_type, lm, func_args=None):
        super().__init__()
        self.task_type = task_type
        self.lm = lm
        self.args = func_args or {}
        self.is_running = True

    def _relay(self, p, msg="Processing"):
        tp = self.task_type.capitalize()
        self.progress.emit(p, 100, f"{tp}: {msg} ({p}%)")
        return self.is_running

    def run(self):
        try:
            if self.task_type == "auto":
                count = self.lm.auto_label_from_extracted(progress_cb=self._relay)
                self.finished.emit(count)
            
            elif self.task_type == "search":
                results = Interpolator.search_similar(
                    self.lm.ext_dir, Path(self.args['frame']), self.args['label'],
                    threshold=self.args.get('threshold', 0.85),
                    progress_cb=self._relay
                )
                self.finished.emit(results)
            
            elif self.task_type == "track":
                # 🧬 10/10 SEQUENCE: Build the frame list from start + count
                all_f = self.lm.get_all_frame_names()
                start_frame = self.args['frame']
                count = self.args.get('count', 10)
                
                try:
                    s_idx = all_f.index(start_frame)
                    # 🧬 10/10 SYNC: Include the master anchor frame so the tracker can 'Lock On' first
                    track_subset = all_f[s_idx : s_idx + 1 + count]
                    
                    results = Interpolator.track_object(
                        self.lm.ext_dir, track_subset, self.args['label'],
                        threshold=self.args.get('threshold', 0.85),
                        progress_cb=self._relay
                    )
                    self.finished.emit(results)
                except ValueError:
                    raise Exception(f"Start frame {start_frame} not found in project.")
            
            elif self.task_type == "interp":
                easing = self.args.get("easing", "ease_out")
                results = Interpolator.linear_interpolate(
                    self.args['sl'], self.args['el'], len(self.args['gap']),
                    easing=easing, progress_cb=self._relay
                )
                # Batch-save interpolated labels
                for i, entry in enumerate(results):
                    frame_name = self.args['gap'][i]
                    entry['label'] = self.args['act']
                    if 'type' in entry: entry['g_type'] = entry.pop('type')
                    existing = self.lm.get_labels(frame_name)
                    if not any(l.get('label') == self.args['act'] and l.get('source') == 'manual' for l in existing):
                        self.lm.set_label(frame_name, **entry)
                self.lm.save()
                self.finished.emit(len(results))
                
        except Exception as e:
            logger.error(f"AI Worker Error: {e}")
            self.error.emit(str(e))

    def stop(self):
        self.is_running = False


# ── BULK REVIEW DIALOG ────────────────────────────────────────────────────────

class BulkReviewDialog(QMainWindow):
    """
    10/10 Tier 2 Bulk Review: Grid of candidate matches for fast approve/reject.
    Keyboard shortcuts: Space=Approve+Next, X=Reject+Next, A=Approve All, R=Reject All.
    """
    def __init__(self, candidates: list, frames_dir: Path, action_name: str, parent=None):
        super().__init__(parent)
        self.candidates  = candidates
        self.frames_dir  = frames_dir
        self.action_name = action_name
        self.decisions   = {}   # {fname: True/False}

        self.setWindowTitle(f"🟡 Bulk Review — {action_name} ({len(candidates)} matches)")
        self.resize(1100, 680)
        self.setStyleSheet(f"background: {C['bg_darkest']}; color: {C['white']};")

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(8)

        # Header
        hdr = QLabel(
            f"  🟡 Tier 2 Review: {len(candidates)} medium-confidence matches  |  "
            "Space=Approve+Next    X=Reject+Next    A=Approve All    R=Reject All"
        )
        hdr.setStyleSheet(f"color: {C['amber']}; font-size: 11px; border: none; padding: 4px;")
        root_layout.addWidget(hdr)

        # Grid scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {C['bg_panel']}; border: none; }}")
        grid_w = QWidget()
        self.grid = QGridLayout(grid_w)
        self.grid.setSpacing(8)
        scroll.setWidget(grid_w)
        root_layout.addWidget(scroll, stretch=1)

        # Bottom bar
        bottom = QFrame()
        bottom.setFixedHeight(52)
        bottom.setStyleSheet(f"background: {C['bg_sidebar']}; border-top: 1px solid {C['border']};")
        bot_layout = QHBoxLayout(bottom)
        bot_layout.setContentsMargins(16, 0, 16, 0)

        self.progress_lbl = QLabel("0 / 0 reviewed")
        self.progress_lbl.setStyleSheet(f"color: {C['text_muted']}; border: none;")
        bot_layout.addWidget(self.progress_lbl)
        bot_layout.addStretch()

        for txt, cb in [("✅  Approve All", self._approve_all), ("❌  Reject All", self._reject_all), ("💾  Done", self.close)]:
            btn = QPushButton(txt)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background: {C['bg_panel']}; color: {C['white']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 0 14px;")
            btn.clicked.connect(cb)
            bot_layout.addWidget(btn)
        root_layout.addWidget(bottom)

        self._build_grid()

    def _build_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        cols = 4
        for idx, cand in enumerate(self.candidates[:16]):
            fname    = cand.get("frame", "")
            conf     = cand.get("confidence", 0.0)
            approved = self.decisions.get(fname, None)

            cell = QFrame()
            border_col = C['green'] if approved is True else (C['red'] if approved is False else C['border'])
            cell.setStyleSheet(f"background: {C['bg_panel']}; border: 2px solid {border_col}; border-radius: 6px;")
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(4, 4, 4, 4)
            cell_layout.setSpacing(4)

            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_lbl.setFixedHeight(100)
            img_path = self.frames_dir / fname
            if img_path.exists():
                pix = QPixmap(str(img_path)).scaled(160, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img_lbl.setPixmap(pix)
            cell_layout.addWidget(img_lbl)

            info = QLabel(f"{fname[-12:-4]}  |  {conf:.0%}")
            info.setStyleSheet(f"font-size: 9px; color: {C['cyan']}; border: none;")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.addWidget(info)

            btn_row = QHBoxLayout()
            for symbol, decision in [("✅", True), ("❌", False)]:
                btn = QPushButton(symbol)
                btn.setFixedHeight(24)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; border-radius: 3px; font-size: 12px;")
                btn.clicked.connect(lambda _, f=fname, d=decision: self._decide(f, d))
                btn_row.addWidget(btn)
            cell_layout.addLayout(btn_row)
            self.grid.addWidget(cell, idx // cols, idx % cols)

        self._update_progress()

    def _decide(self, fname, approved):
        self.decisions[fname] = approved
        self._build_grid()

    def _approve_all(self):
        for c in self.candidates[:16]:
            self.decisions[c.get("frame", "")] = True
        self._build_grid()

    def _reject_all(self):
        for c in self.candidates[:16]:
            self.decisions[c.get("frame", "")] = False
        self._build_grid()

    def _update_progress(self):
        self.progress_lbl.setText(f"{len(self.decisions)} / {len(self.candidates)} reviewed")

    def keyPressEvent(self, event):
        remaining = [c for c in self.candidates if c.get("frame") not in self.decisions]
        if remaining:
            fname = remaining[0].get("frame", "")
            if event.key() == Qt.Key.Key_Space: self._decide(fname, True)
            elif event.key() == Qt.Key.Key_X:   self._decide(fname, False)
        if event.key() == Qt.Key.Key_A:   self._approve_all()
        elif event.key() == Qt.Key.Key_R:  self._reject_all()

    def exec(self):
        self.show()
        from PyQt6.QtWidgets import QApplication
        while self.isVisible():
            QApplication.processEvents()


# ── GESTURE DIALOG ──────────────────────────────────────────────────────────

class ActionTypeDialog(QInputDialog):
    """Custom 10/10 dialog to pick Interaction Recipes."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Interaction Recipe")
        self.setLabelText("Select the interaction DNA for this action:")
        # 10/10: Ordered by your professional requirements
        self.setComboBoxItems([
            "🔘 Click Only",
            "🏹 Swipe Only",
            "🟦 Rectangle Only",
            "🟦 + 🔘 Hybrid: Area + Click",
            "🟦 + 🏹 Hybrid: Area + Swipe",
            "🔘 + 🏹 Hybrid: Click + Swipe",
            "🟦 + 🔘 + 🏹 Hybrid: Area + Click + Swipe",
            "📍 State: Visual Context / Landmark"
        ])
        self.setComboBoxEditable(False)
        self.setOkButtonText("Create Action")
        self.setStyleSheet(f"background: {C['bg_panel']}; color: {C['white']};")


# ── GESTURE ITEMS ───────────────────────────────────────────────────────────

class GestureArrowItem(QGraphicsLineItem):
    """10/10 Weighted Arrow for Swipes."""
    def __init__(self, x1, y1, x2, y2, pen, parent=None):
        super().__init__(x1, y1, x2, y2, parent)
        self.setPen(pen)
        self.setFlags(QGraphicsLineItem.GraphicsItemFlag.ItemIsSelectable | 
                     QGraphicsLineItem.GraphicsItemFlag.ItemIsMovable)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        # Draw Arrow Head
        line = self.line()
        if line.length() < 5: return
        
        painter.setPen(self.pen())
        painter.setBrush(QBrush(self.pen().color()))
        
        angle = np.arctan2(-line.dy(), line.dx())
        arrow_size = 12
        p1 = line.p2()
        
        pa = p1 + QPointF(np.sin(angle - np.pi/4) * arrow_size, np.cos(angle - np.pi/4) * arrow_size)
        pb = p1 + QPointF(np.sin(angle - 3*np.pi/4) * arrow_size, np.cos(angle - 3*np.pi/4) * arrow_size)
        
        from PyQt6.QtGui import QPolygonF
        painter.drawPolygon(QPolygonF([p1, pa, pb]))

class GesturePointItem(QGraphicsEllipseItem):
    """10/10 Target Ring for Clicks."""
    def __init__(self, x, y, pen, parent=None):
        # Center the ellipse on x,y
        r = 8
        super().__init__(x - r, y - r, r*2, r*2, parent)
        self.setPen(pen)
        self.setFlags(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable | 
                     QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable)
        
        # Inner dot
        inner_r = 2
        self.inner = QGraphicsEllipseItem(x - inner_r, y - inner_r, inner_r*2, inner_r*2, self)
        self.inner.setBrush(QBrush(pen.color()))
        self.inner.setPen(QPen(Qt.PenStyle.NoPen))

class WorkbenchItem(QFrame):
    """Sleek 10/10 Item for the Right Sidebar Interaction Pipeline."""
    clicked = pyqtSignal(dict) 
    checkChanged = pyqtSignal(str, bool) # 10/10: Mirror Highlighting

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Determine Status/Colors
        action = data.get("label", "Draft")
        is_bound = "label" in data
        color = C['cyan'] if is_bound else C['text_muted']
        
        self.setStyleSheet(f"""
            QFrame {{ 
                background: {C['bg_sidebar']}; 
                border: 1px solid {C['border']}; 
                border-radius: 6px; 
            }}
            QFrame:hover {{ border-color: {color}; }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # Checkbox for Binding
        from PyQt6.QtWidgets import QCheckBox
        self.check = QCheckBox()
        self.check.setStyleSheet(f"QCheckBox::indicator {{ width: 14px; height: 14px; }}")
        layout.addWidget(self.check)
        
        # Icon
        g_type = data.get("type", "rect")
        icon_map = {"point": "🔘", "swipe": "🏹", "rect": "🟦"}
        icon = QLabel(icon_map.get(g_type, "💠"))
        icon.setStyleSheet("font-size: 14px; border: none;")
        layout.addWidget(icon)
        
        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(1)
        # 10/10: Better display for atomized components
        parent_action = data.get("parent_label", None)
        status_text = f"{parent_action.upper()} » {g_type.upper()}" if parent_action else f"DRAFT {g_type.upper()}"
        
        self.tag = QLabel(status_text)
        self.tag.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {color}; border: none;")
        info_vbox.addWidget(self.tag)
        
        coords = f"x:{data.get('x',0)} y:{data.get('y',0)}"
        if g_type == "rect": coords += f" w:{data.get('w',0)} h:{data.get('h',0)}"
        elif g_type == "swipe": coords += f" ➝ x2:{data.get('x2',0)} y2:{data.get('y2',0)}"
        
        self.loc = QLabel(coords)
        self.loc.setStyleSheet(f"font-size: 11px; color: {C['text_d']}; border: none;")
        info_vbox.addWidget(self.loc)
        
        layout.addLayout(info_vbox)
        layout.addStretch()
        self.setFixedHeight(50) 
        
        # 10/10: Connect check signal
        self.check.stateChanged.connect(lambda s: self.checkChanged.emit(data.get("cid",""), s == 2))

    def mousePressEvent(self, event):
        self.clicked.emit(self.data)
        super().mousePressEvent(event)

class LabelCanvas(QGraphicsView):
    """Drawing area — Multi-Gesture (Rect, Point, Swipe) + Smart Mode + Zoom + Ghost Overlay."""
    gesture_drawn = pyqtSignal(dict)
    coords_updated = pyqtSignal(int, int) # For live crosshair status

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']};")
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        self.drawing_mode = "rect"  # "rect", "point", "swipe", "smart"
        self._start_pos = None
        self._temp_item = None
        self._press_time = 0
        self._ghost_labels = []  # Previous frame labels for ghost overlay
        
        self.rect_pen   = QPen(QColor(C['cyan']), 2, Qt.PenStyle.SolidLine)
        self.point_pen  = QPen(QColor(C['amber']), 2, Qt.PenStyle.SolidLine)
        self.swipe_pen  = QPen(QColor(C['violet']), 2, Qt.PenStyle.SolidLine)
        self.auto_pen   = QPen(QColor(C['white']), 1, Qt.PenStyle.DashLine)
        self.ghost_pen  = QPen(QColor(255, 255, 255, 50), 1, Qt.PenStyle.DashDotLine)
        
        self._resize_item = None
        self.setMouseTracking(True)
        
        # 🔍 Zoom transform
        self._zoom_level = 1.0

    def load_frame(self, path: Path, labels: list, drafts: list = None, highlighted_cids: set = None):
        """Standard Frame Load + Ghost Overlay + 10/10 Highlight Support."""
        self.scene().clear()
        self.highlighted_cids = highlighted_cids or set()
        
        pix = QPixmap(str(path))
        if pix.isNull(): return
        
        self.scene().addPixmap(pix)
        self.setSceneRect(QRectF(pix.rect()))
        
        # 0. Draw Ghost Overlay from Previous Frame (20% opacity)
        if self._ghost_labels:
            saved_pens = (self.rect_pen, self.point_pen, self.swipe_pen)
            self.rect_pen = self.ghost_pen
            self.point_pen = self.ghost_pen
            self.swipe_pen = self.ghost_pen
            for ghost in self._ghost_labels:
                self._draw_gesture(ghost, source="ghost")
            self.rect_pen, self.point_pen, self.swipe_pen = saved_pens
        
        # 1. Draw Bound Labels
        for lbl in labels:
            if lbl.get("type") == "hybrid":
                for comp in lbl.get("components", []):
                    comp["parent_label"] = lbl.get("label")
                    self._draw_gesture(comp, source=lbl.get("source"))
            else:
                self._draw_gesture(lbl)
            
        # 2. Draw Draft Components
        if drafts:
            for d in drafts:
                # Ghost style for drafts UNLESS highlighted
                is_hi = d.get("cid") in self.highlighted_cids
                old_pens = (self.rect_pen, self.point_pen, self.swipe_pen)
                
                if not is_hi:
                    ghost_col = QColor(255, 255, 255, 180)
                    self.rect_pen = QPen(ghost_col, 1, Qt.PenStyle.DashLine)
                    self.point_pen = QPen(ghost_col, 1, Qt.PenStyle.DashLine)
                    self.swipe_pen = QPen(ghost_col, 1, Qt.PenStyle.DashLine)
                
                self._draw_gesture(d)
                self.rect_pen, self.point_pen, self.swipe_pen = old_pens
        
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _draw_gesture(self, data: dict, source=None):
        g_type = data.get("type", "rect")
        src    = source or data.get("source", "manual")
        cid    = data.get("cid")
        is_hi  = cid is not None and cid in getattr(self, "highlighted_cids", set())
        
        # 🧪 10/10 RECIPE ENGINE: Handle specific component-based interaction types
        recipe_types = ["hybrid", "rect_click", "rect_swipe", "click_swipe", "rect_click_swipe"]
        
        if g_type in recipe_types:
            # Mirror the hybrid drawing logic for all recipe types 🧬
            for comp in data.get("components", []):
                # Recursively call with component data but keep parent label
                comp_with_meta = {**comp, "label": data.get("label"), "source": src}
                self._draw_gesture(comp_with_meta)
            return

        x, y   = float(data.get("x", 0)), float(data.get("y", 0))
        
        # 10/10 SURGICAL HIGHLIGHT: Bold Red if checked in workbench
        if is_hi:
            pen = QPen(Qt.GlobalColor.red, 4, Qt.PenStyle.SolidLine)
        else:
            base_pen = self.rect_pen if g_type == "rect" else (self.swipe_pen if g_type == "swipe" else self.point_pen)
            pen = base_pen if src == "manual" else self.auto_pen

        color = pen.color()
        
        item = None
        if g_type == "rect":
            w, h = float(data.get("w", 60)), float(data.get("h", 30))
            item = QGraphicsRectItem(x, y, w, h)
            fill = QColor(color)
            fill.setAlpha(25)
            item.setBrush(QBrush(fill))
        elif g_type == "swipe":
            x2, y2 = float(data.get("x2", x+50)), float(data.get("y2", y+50))
            item = GestureArrowItem(x, y, x2, y2, pen)
        elif g_type == "point":
            item = GesturePointItem(x, y, pen)

        if not item: return

        item.setData(0, data)
        self.scene().addItem(item)

        # Label tag
        lbl_text = data.get("label", "unknown")
        txt = self.scene().addText(lbl_text, QFont("Segoe UI", 8, QFont.Weight.Bold))
        txt.setDefaultTextColor(QColor(C['white']))
        txt.setPos(x, y - 18)
        txt.setParentItem(item) # Attach to item so it moves with it
        
        # Background for text
        bg_col = QColor(color)
        bg_col.setAlpha(160)
        bg = self.scene().addRect(x, y - 18, txt.boundingRect().width(), 16, QPen(Qt.PenStyle.NoPen), QBrush(bg_col))
        bg.setZValue(txt.zValue() - 1)
        bg.setParentItem(item) # Attach to item

    def wheelEvent(self, event):
        """🔍 Scroll-wheel zoom for precise coordinate placement."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_zoom = self._zoom_level * factor
        if 0.2 <= new_zoom <= 10.0:
            self._zoom_level = new_zoom
            self.setTransform(self.transform().scale(factor, factor))

    def mousePressEvent(self, event):
        # 10/10 RESIZE: Auto-Commit (Click anywhere to finish)
        if self._resize_item:
            scene_rect = self._resize_item.mapToScene(self._resize_item.rect()).boundingRect()
            data = self._resize_item.data(0)
            main_win = self.window()
            if hasattr(main_win, "_on_resize_finished"):
                main_win._on_resize_finished(data, scene_rect)
            self._resize_item = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            import time
            self._press_time = time.time()
            self._start_pos = self.mapToScene(event.pos())
            
            # Smart mode starts with a point as preview
            active_mode = self.drawing_mode
            if active_mode == "smart":
                self._temp_item = GesturePointItem(self._start_pos.x(), self._start_pos.y(), self.point_pen)
            elif active_mode == "rect":
                self._temp_item = QGraphicsRectItem()
                self._temp_item.setPen(self.rect_pen)
            elif active_mode == "swipe":
                self._temp_item = QGraphicsLineItem()
                self._temp_item.setPen(self.swipe_pen)
            elif active_mode == "point":
                self._temp_item = GesturePointItem(self._start_pos.x(), self._start_pos.y(), self.point_pen)
            
            if self._temp_item:
                self.scene().addItem(self._temp_item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Live pixel coordinate broadcast for crosshair status bar
        scene_pos = self.mapToScene(event.pos())
        self.coords_updated.emit(int(scene_pos.x()), int(scene_pos.y()))
        
        # 10/10 RESIZE: Track mouse for real-time stretching
        if self._resize_item:
            pos_item = self._resize_item.mapFromScene(scene_pos)
            rect = self._resize_item.rect()
            new_w = max(10, pos_item.x() - rect.x())
            new_h = max(10, pos_item.y() - rect.y())
            self._resize_item.setRect(rect.x(), rect.y(), new_w, new_h)
            return

        if self._start_pos and self._temp_item:
            curr = scene_pos
            active_mode = self.drawing_mode

            if active_mode == "smart" and self._start_pos:
                # Real-time preview: show what shape will be created
                dist = np.sqrt((curr.x()-self._start_pos.x())**2 + (curr.y()-self._start_pos.y())**2)
                if dist > 80:  # Swipe preview
                    if not isinstance(self._temp_item, QGraphicsLineItem):
                        if self._temp_item.scene(): self.scene().removeItem(self._temp_item)
                        self._temp_item = QGraphicsLineItem()
                        self._temp_item.setPen(self.swipe_pen)
                        self.scene().addItem(self._temp_item)
                    self._temp_item.setLine(self._start_pos.x(), self._start_pos.y(), curr.x(), curr.y())
                elif dist > 15:  # Rect preview
                    if not isinstance(self._temp_item, QGraphicsRectItem):
                        if self._temp_item.scene(): self.scene().removeItem(self._temp_item)
                        self._temp_item = QGraphicsRectItem()
                        self._temp_item.setPen(self.rect_pen)
                        self.scene().addItem(self._temp_item)
                    self._temp_item.setRect(QRectF(self._start_pos, curr).normalized())
            elif active_mode == "rect":
                self._temp_item.setRect(QRectF(self._start_pos, curr).normalized())
            elif active_mode == "swipe":
                self._temp_item.setLine(self._start_pos.x(), self._start_pos.y(), curr.x(), curr.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._start_pos:
            import time
            curr = self.mapToScene(event.pos())
            duration = time.time() - self._press_time
            
            active_mode = self.drawing_mode
            dist = np.sqrt((curr.x()-self._start_pos.x())**2 + (curr.y()-self._start_pos.y())**2)
            velocity = dist / max(duration, 0.001)

            # 🤖 10/10 SMART MODE: Detect intent from gesture physics
            if active_mode == "smart":
                if dist < 15:
                    active_mode = "point"
                elif velocity > 200 or dist > 80:
                    active_mode = "swipe"
                else:
                    active_mode = "rect"

            g_data = {"type": active_mode}
            
            valid = False
            if active_mode == "rect":
                rect = QRectF(self._start_pos, curr).normalized()
                if rect.width() > 5 and rect.height() > 5:
                    g_data.update({"x": int(rect.x()), "y": int(rect.y()), "w": int(rect.width()), "h": int(rect.height())})
                    valid = True
            elif active_mode == "swipe":
                if dist > 10:
                    g_data.update({"x": int(self._start_pos.x()), "y": int(self._start_pos.y()), "x2": int(curr.x()), "y2": int(curr.y())})
                    valid = True
            elif active_mode == "point":
                g_data.update({"x": int(self._start_pos.x()), "y": int(self._start_pos.y())})
                valid = True

            if valid:
                self.gesture_drawn.emit(g_data)
            
            try:
                if self._temp_item and self._temp_item.scene():
                    self.scene().removeItem(self._temp_item)
            except RuntimeError:
                pass # Pre-emptively deleted by refresh
            
            self._temp_item = None
            self._start_pos = None
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, QGraphicsRectItem):
            from PyQt6.QtWidgets import QMenu
            menu = QMenu(self)
            menu.setStyleSheet(f"background: {C['bg_panel']}; color: {C['text']}; border: 1px solid {C['border']};")
            
            # Options
            resize_act = menu.addAction("📐 Resize This Box")
            del_act = menu.addAction("🗑️ Delete This Box")
            
            choice = menu.exec(event.globalPos())
            if choice == del_act:
                data = item.data(0)
                main_win = self.window()
                if hasattr(main_win, "_on_box_delete_requested"):
                    main_win._on_box_delete_requested(data)
            
            elif choice == resize_act:
                self._resize_item = item
                color = QColor(C['amber'])
                color.setAlpha(50)
                item.setBrush(QBrush(color)) # Visual feedback
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                
        else:
            super().contextMenuEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # 🧬 10/10 SYNC: Force overlay to follow the window geometry
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.setGeometry(self.rect())


# ── THUMBNAIL ─────────────────────────────────────────────────────────────────

class FrameThumb(QFrame):
    """Single frame thumbnail in the bottom gallery."""
    clicked = pyqtSignal(str)

    def __init__(self, fname: str, img_path: Path, label_data: dict = None):
        super().__init__()
        self.fname = fname
        self.setFixedSize(130, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        src = (label_data or {}).get("source", "")
        if src == "manual":
            border = C['cyan']
        elif src:
            border = C['violet']
        else:
            border = C['border']
        self.setStyleSheet(
            f"QFrame {{ background: {C['bg_panel']}; border: 2px solid {border}; border-radius: 4px; }}"
            f"QFrame:hover {{ background: {C['bg_darkest']}; border-color: {C['white']}; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Image Label (Thumbnail)
        self.img_lbl = QLabel()
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setMinimumHeight(60)
        if img_path.exists():
            pix = QPixmap(str(img_path))
            # Scale to fit while keeping aspect ratio
            scaled = pix.scaled(120, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.img_lbl.setPixmap(scaled)
        layout.addWidget(self.img_lbl)

        # Footer (Label name + Frame #)
        footer = QFrame()
        footer.setStyleSheet("background: rgba(0,0,0,60); border: none; border-top: 1px solid rgba(255,255,255,10);")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(6, 2, 6, 2)
        
        lbl_name = (label_data or {}).get("label", "—")
        tag = QLabel(lbl_name)
        tag.setStyleSheet(f"font-size: 9px; color: {C['cyan'] if src == 'manual' else C['text_d']}; border: none;")
        f_layout.addWidget(tag)
        
        f_layout.addStretch()
        
        frame_num = QLabel(fname[-11:-4])
        frame_num.setStyleSheet(f"font-size: 8px; color: {C['text_d']}; border: none;")
        f_layout.addWidget(frame_num)
        
        layout.addWidget(footer)

    def mousePressEvent(self, event):
        self.clicked.emit(self.fname)


# ── MAIN WINDOW ──────────────────────────────────────────────────────────────

class LabelingToolWindow(QMainWindow):
    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        # 🧪 10/10 TYPOGRAPHY: Enforce Segoe UI to banish MS Sans Serif fallback
        self.setFont(QFont("Segoe UI", 10))
        
        self.model_name      = model_name
        self.lm = LabelManager(model_name)
        # 🧪 10/10 TYPOGRAPHY: Enforce Segoe UI to banish MS Sans Serif fallback
        self.setFont(QFont("Segoe UI", 10))
        # 🧬 10/10 SYNC: Load all category definitions into session state
        self.custom_actions = set(self.lm.get_action_meta().keys())
        self.current_frame = None
        self.current_filter  = None   # None = All
        self.drafts = [] # 10/10 Workbench Drafts: Temporary components for current frame
        self._is_recording = False    # Record Mode state
        self._record_worker = None    # ADB getevent thread

        self.setWindowTitle(f"🏷  Smart Label Tool  –  {model_name}")
        self.resize(1500, 950)
        self.setMinimumSize(1000, 700)
        # 🧪 10/10 BRANDING: Enforce consistent premium typography
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(f"* {{ font-family: 'Segoe UI'; }} background: {C['bg_darkest']}; color: {C['white']};")
        self._build_ui()
        self._refresh()
        
        # 10/10 PROGRESS: Shared loading overlay (Parented to CENTRAL WIDGET for visibility)
        self.overlay = LoadingOverlay(self.centralWidget())
        self.overlay.cancel_requested.connect(self._on_ai_cancel_requested)
        self._ai_worker = None
        
        # 🧠 Wire live coordinate display
        self.canvas.coords_updated.connect(lambda x, y: self.coord_lbl.setText(f"  x:{x} y:{y}"))

    # ── BUILD UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── TOP TOOLBAR ──────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setFixedHeight(52)
        toolbar.setStyleSheet(
            f"background: {C['bg_sidebar']}; border-bottom: 1px solid {C['border']};"
        )
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(16, 0, 16, 0)
        tb_layout.setSpacing(8)

        model_lbl = QLabel(f"  {self.model_name}")
        model_lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 13px; border: none; font-weight: bold;")
        tb_layout.addWidget(model_lbl)
        
        tb_layout.addSpacing(20)
        
        # 10/10 GESTURE TOOLBOX (Top-Left)
        self.tool_grp = QFrame()
        self.tool_grp.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 6px;")
        t_layout = QHBoxLayout(self.tool_grp)
        t_layout.setContentsMargins(4, 4, 4, 4)
        t_layout.setSpacing(4)
        
        self.btn_mode_click = self._make_mode_btn(t_layout, "🔘", "point")
        self.btn_mode_swipe = self._make_mode_btn(t_layout, "🏹", "swipe")
        self.btn_mode_rect  = self._make_mode_btn(t_layout, "🟦", "rect")
        self.btn_mode_smart = self._make_mode_btn(t_layout, "🎭", "smart", tooltip="Smart Mode: Auto-detects Point/Rect/Swipe from gesture")
        
        tb_layout.addWidget(self.tool_grp)
        tb_layout.addStretch()
        
        # Pixel coords display (crosshair readout)
        self.coord_lbl = QLabel("  x:--- y:---")
        self.coord_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 10px; font-family: monospace; border: none;")
        tb_layout.addWidget(self.coord_lbl)
        
        # 10/10: Track buttons for gated workspace
        self._btns = {}

        self.btn_auto = self._make_toolbar_btn(tb_layout, "🤖  Auto-Label", C['purple'], self._on_auto_label)
        self.btn_search = self._make_toolbar_btn(tb_layout, "🔍  Search Similar", C['violet'], self._on_search_similar)
        self.btn_interp = self._make_toolbar_btn(tb_layout, "🌉  Interpolate", C['cyan'], self._on_interpolate)
        self.btn_track = self._make_toolbar_btn(tb_layout, "🎯  AI Tracker", C['amber'], self._on_track)
        self.btn_record = self._make_toolbar_btn(tb_layout, "⏺  Record", C['red'], self._on_toggle_record)
        self._make_toolbar_btn(tb_layout, "💾  Save", C['green'], self._on_save, bold=True)

        root_layout.addWidget(toolbar)

        # ── MAIN CONTENT (Sidebar | Canvas + Gallery) ────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: " + C['border'] + "; width: 1px; }")

        # LEFT SIDEBAR ────────────────────────────────────────────────────────
        sidebar_container = QFrame()
        sidebar_container.setMinimumWidth(200)
        sidebar_container.setMaximumWidth(280)
        sidebar_container.setStyleSheet(
            f"background: {C['bg_sidebar']}; border-right: 1px solid {C['border']};"
        )
        sc_layout = QVBoxLayout(sidebar_container)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.setSpacing(0)

        # Sidebar header
        sb_header = QFrame()
        sb_header.setFixedHeight(44)
        sb_header.setStyleSheet(f"background: {C['bg_panel']}; border-bottom: 1px solid {C['border']};")
        sbh_layout = QHBoxLayout(sb_header)
        sbh_layout.setContentsMargins(12, 0, 8, 0)
        sbh_layout.addWidget(QLabel("🏷  Actions"))

        # "+" button to add a new action directly from sidebar
        add_btn = QPushButton("+  New Action")
        add_btn.setFixedHeight(26)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            f"QPushButton {{ background: {C['cyan']}22; color: {C['cyan']}; "
            f"border: 1px solid {C['cyan']}77; border-radius: 4px; "
            f"font-size: 11px; padding: 0 10px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {C['cyan']}44; border-color: {C['cyan']}; }}"
        )
        add_btn.clicked.connect(self._on_new_action)
        sbh_layout.addWidget(add_btn)
        sc_layout.addWidget(sb_header)

        self.sidebar_L = QListWidget()
        self.sidebar_L.setStyleSheet(QSS_SIDEBAR)
        self.sidebar_L.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sidebar_L.customContextMenuRequested.connect(self._on_sidebar_menu)
        self.sidebar_L.itemClicked.connect(self._on_sidebar_clicked)
        sc_layout.addWidget(self.sidebar_L)
        splitter.addWidget(sidebar_container)

        # CENTER PANEL (Canvas on top, Gallery on bottom) ──────────────────────
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # Status bar above canvas
        self.status_bar = QLabel("  Draw components on the frame, then bind them in the Workbench (Right).")
        self.status_bar.setFixedHeight(32)
        self.status_bar.setStyleSheet(
            f"background: {C['bg_panel']}; color: {C['text_d']}; "
            f"font-size: 11px; border-bottom: 1px solid {C['border']}; padding-left: 12px;"
        )
        center_layout.addWidget(self.status_bar)

        # ── CANVAS & VERDICT BAR ─────────────────────────────────────────────
        canvas_container = QWidget()
        canvas_vbox = QVBoxLayout(canvas_container)
        canvas_vbox.setContentsMargins(0, 0, 0, 0)
        canvas_vbox.setSpacing(0)
        
        self.canvas = LabelCanvas()
        self.canvas.gesture_drawn.connect(self._on_interaction_added) # Changed to interaction added
        canvas_vbox.addWidget(self.canvas)
        
        # Verdict Bar (True/False)
        self.verdict_bar = QFrame()
        self.verdict_bar.setFixedHeight(48)
        self.verdict_bar.setStyleSheet(f"background: {C['bg_sidebar']}; border-top: 1px solid {C['border']};")
        vb_layout = QHBoxLayout(self.verdict_bar)
        vb_layout.setContentsMargins(20, 0, 20, 0)
        
        vb_lbl = QLabel("🤖 AI Suggestion: Is this correct?")
        vb_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; border: none;")
        vb_layout.addWidget(vb_lbl)
        vb_layout.addStretch()
        
        btn_false = QPushButton("❌  False (Reject)")
        btn_false.setFixedSize(120, 28)
        btn_false.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_false.setStyleSheet(f"background: {C['red']}22; color: {C['red']}; border: 1px solid {C['red']}66; border-radius: 4px; font-weight: bold;")
        btn_false.clicked.connect(self._on_verdict_false)
        vb_layout.addWidget(btn_false)
        
        btn_true = QPushButton("✅  True (Confirm)")
        btn_true.setFixedSize(120, 28)
        btn_true.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_true.setStyleSheet(f"background: {C['green']}22; color: {C['green']}; border: 1px solid {C['green']}66; border-radius: 4px; font-weight: bold;")
        btn_true.clicked.connect(self._on_verdict_true)
        vb_layout.addWidget(btn_true)
        
        self.verdict_bar.hide()
        center_layout.addWidget(self.verdict_bar)
        center_layout.addWidget(canvas_container, stretch=3)

        # Gallery separator
        gallery_header = QFrame()
        gallery_header.setFixedHeight(32)
        gallery_header.setStyleSheet(
            f"background: {C['bg_panel']}; border-top: 1px solid {C['border']}; border-bottom: 1px solid {C['border']};"
        )
        gh_layout = QHBoxLayout(gallery_header)
        gh_layout.setContentsMargins(12, 0, 12, 0)
        self.gallery_label = QLabel("All Frames")
        self.gallery_label.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; border: none;")
        gh_layout.addWidget(self.gallery_label)
        center_layout.addWidget(gallery_header)

        # Gallery scroll area
        gallery_scroll = QScrollArea()
        gallery_scroll.setFixedHeight(130)
        gallery_scroll.setWidgetResizable(True)
        gallery_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        gallery_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        gallery_scroll.setStyleSheet(
            f"QScrollArea {{ background: {C['bg_panel']}; border: none; }}"
        )

        self.gallery_widget = QWidget()
        self.gallery_widget.setStyleSheet(f"background: {C['bg_panel']};")
        self.gallery_layout = QHBoxLayout(self.gallery_widget)
        self.gallery_layout.setContentsMargins(8, 4, 8, 4)
        self.gallery_layout.setSpacing(6)
        self.gallery_layout.addStretch()
        gallery_scroll.setWidget(self.gallery_widget)
        center_layout.addWidget(gallery_scroll, stretch=0)

        splitter.addWidget(center_panel)

        # RIGHT SIDEBAR (Interaction Pipeline) ────────────────────────────────
        self.sidebar_R = QFrame()
        self.sidebar_R.setMinimumWidth(220)
        self.sidebar_R.setMaximumWidth(320)
        self.sidebar_R.setStyleSheet(
            f"background: {C['bg_sidebar']}; border-left: 1px solid {C['border']};"
        )
        sr_layout = QVBoxLayout(self.sidebar_R)
        sr_layout.setContentsMargins(0, 0, 0, 0)
        sr_layout.setSpacing(0)

        # Sidebar-R header
        sbr_header = QFrame()
        sbr_header.setFixedHeight(44)
        sbr_header.setStyleSheet(f"background: {C['bg_panel']}; border-bottom: 1px solid {C['border']};")
        sbrh_layout = QHBoxLayout(sbr_header)
        sbrh_layout.setContentsMargins(12, 0, 8, 0)
        sbrh_layout.addWidget(QLabel("💠  Workbench"))
        
        btn_clr = QPushButton("Clear")
        btn_clr.setFixedSize(50, 22)
        btn_clr.setStyleSheet(f"font-size: 10px; color: {C['text_d']}; background: transparent; border: 1px solid {C['border']};")
        btn_clr.clicked.connect(self._on_clear_workbench)
        sbrh_layout.addWidget(btn_clr)
        sr_layout.addWidget(sbr_header)

        # Current Interactions List
        self.workbench = QListWidget()
        self.workbench.setSpacing(4)
        self.workbench.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.workbench.customContextMenuRequested.connect(self._on_workbench_menu)
        self.workbench.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; padding: 10px; }}
            QListWidget::item {{ 
                background: {C['bg_panel']}; 
                border-radius: 6px; 
                margin-bottom: 4px;
                padding: 10px;
            }}
        """)
        sr_layout.addWidget(self.workbench)

        # Footer Binding Button
        bind_footer = QFrame()
        bind_footer.setFixedHeight(60)
        bind_footer.setStyleSheet(f"background: {C['bg_panel']}; border-top: 1px solid {C['border']};")
        bf_layout = QVBoxLayout(bind_footer)
        bf_layout.setContentsMargins(12, 10, 12, 10)

        self.btn_bind = QPushButton("💾  Save to Action...")
        self.btn_bind.setFixedHeight(34)
        self.btn_bind.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bind.setStyleSheet(f"""
            QPushButton {{ 
                background: {C['cyan']}22; color: {C['cyan']}; 
                border: 2px solid {C['cyan']}77; border-radius: 6px; 
                font-weight: bold; font-size: 13px;
            }}
            QPushButton:hover {{ background: {C['cyan']}44; border-color: {C['cyan']}; }}
        """)
        self.btn_bind.clicked.connect(self._on_bind_requested)
        bf_layout.addWidget(self.btn_bind)
        sr_layout.addWidget(bind_footer)

        splitter.addWidget(self.sidebar_R)
        
        # Set Relative Sizes: Left (200), Center (Flexible), Right (220)
        splitter.setSizes([200, 1000, 220])
        root_layout.addWidget(splitter)

    def _make_mode_btn(self, layout, text, mode, tooltip=None):
        btn = QPushButton(text)
        btn.setFixedSize(32, 28)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; font-size: 14px; border-radius: 4px; }}
            QPushButton:hover {{ background: {C['bg_darkest']}; }}
            QPushButton:checked {{ background: {C['cyan']}44; border: 1px solid {C['cyan']}; }}
        """)
        btn.clicked.connect(lambda: self._set_drawing_mode(mode))
        layout.addWidget(btn)
        return btn

    def _set_drawing_mode(self, mode):
        self.canvas.drawing_mode = mode
        self.btn_mode_click.setChecked(mode == "point")
        self.btn_mode_swipe.setChecked(mode == "swipe")
        self.btn_mode_rect.setChecked(mode == "rect")
        self.btn_mode_smart.setChecked(mode == "smart")
        cursor = Qt.CursorShape.CrossCursor if mode == "point" else Qt.CursorShape.ArrowCursor
        self.canvas.setCursor(cursor)

    def _set_btn_opacity(self, btn, opacity):
        effect = QGraphicsOpacityEffect(btn)
        effect.setOpacity(opacity)
        btn.setGraphicsEffect(effect)

    def _make_toolbar_btn(self, layout, text, color, slot, bold=False):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(34)
        btn.setStyleSheet(
            f"QPushButton {{ background: {color}33; color: white; "
            f"border: 1px solid {color}88; border-radius: 6px; "
            f"font-size: 12px; padding: 0 16px; "
            f"font-weight: bold; }}"
            f"QPushButton:hover {{ background: {color}66; border-color: {color}; }}"
        )
        btn.clicked.connect(slot)
        layout.addWidget(btn)
        return btn

    # ── DATA REFRESH ─────────────────────────────────────────────────────────

    def _refresh(self):
        """Refresh sidebars and gallery."""
        self._refresh_sidebar()
        self._refresh_gallery()
        self._refresh_workbench()

    def _refresh_workbench(self):
        """10/10 Component Inventory: List atomized components for current frame."""
        self.workbench.clear()
        if not self.current_frame: return
        
        # 1. Add Components from Bound Actions (including Hybrid explosions)
        labels = self.lm.get_labels(self.current_frame)
        for i, lbl in enumerate(labels):
            if lbl.get("type") == "hybrid":
                for j, comp in enumerate(lbl.get("components", [])):
                    # 🧬 Surgical ID: labelName_index
                    cid = f"bound_{i}_{j}"
                    comp_data = {**comp, "parent_label": lbl.get("label"), "label": lbl.get("label"), "cid": cid}
                    self._add_workbench_item(comp_data)
            else:
                cid = f"bound_{i}"
                comp_data = {**lbl, "parent_label": lbl.get("label"), "cid": cid}
                self._add_workbench_item(comp_data)
            
        # 2. Add Draft Components
        for i, d in enumerate(self.drafts):
            cid = f"draft_{i}"
            d["cid"] = cid # Store ID in draft
            self._add_workbench_item(d)
            
        # UI state
        self.btn_bind.setEnabled(len(self.drafts) > 0)

    def _add_workbench_item(self, data):
        """Helper to create and add a WorkbenchItem with 10/10 Mirroring."""
        item = QListWidgetItem(self.workbench)
        widget = WorkbenchItem(data)
        item.setSizeHint(widget.sizeHint())
        
        # Connect Mirroring Signal 🧬
        widget.checkChanged.connect(self._on_workbench_checked)
        # Inherit checked state if already highlighted
        if data.get("cid") in getattr(self, "highlighted_cids", set()):
            widget.check.setChecked(True)
            
        self.workbench.setItemWidget(item, widget)

    def _on_workbench_checked(self, cid, is_checked):
        """10/10 Mirror: Update Red Highlighting on Canvas."""
        if not hasattr(self, "highlighted_cids"): self.highlighted_cids = set()
        
        if is_checked:
            self.highlighted_cids.add(cid)
        else:
            self.highlighted_cids.discard(cid)
            
        # Repaint Canvas with new highlights 🎨
        if self.current_frame:
            labels = self.lm.get_labels(self.current_frame)
            self.canvas.load_frame(self.lm.ext_dir / self.current_frame, labels, self.drafts, self.highlighted_cids)

    def _refresh_sidebar(self):
        self.sidebar_L.clear()

        # "All Frames" entry
        all_names = self.lm.get_all_frame_names()
        all_item = QListWidgetItem(f"📂  All Frames  [{len(all_names)}]")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        all_item.setFont(QFont("", 11, QFont.Weight.Bold))
        self.sidebar_L.addItem(all_item)

        # Per-action groups
        # 10/10 DNA ICONOGRAPHY
        counts = self.lm.get_counts()
        labeled_actions = [k for k in counts.keys() if k not in ["unlabeled", "unknown"]]
        # 🧬 10/10 STABILITY: Filter out None and empty strings before sorting
        labeled_actions = [a for a in labeled_actions if a and isinstance(a, str)]
        custom_actions  = [a for a in self.custom_actions if a and isinstance(a, str)]
        
        all_display_actions = sorted(list(set(labeled_actions) | set(custom_actions)))

        # 🧬 The 10/10 Recipe Icon Map
        icon_map = {
            "point": "🔘",
            "swipe": "🏹",
            "rect":  "🟦",
            "rect_click": "🟦🔘",
            "rect_swipe": "🟦🏹",
            "click_swipe": "🔘🏹",
            "rect_click_swipe": "🧬🔥",
            "state": "📍"
        }

        for action in all_display_actions:
            cnt = counts.get(action, 0)
            a_type = self.lm.get_action_type(action)
            icon = icon_map.get(a_type, "🏷")
            
            item = QListWidgetItem(f"{icon}  {action}  [{cnt}]")
            item.setData(Qt.ItemDataRole.UserRole, action)
            self.sidebar_L.addItem(item)

        # Unlabeled always at the bottom
        unlabeled = counts.get("unlabeled", 0)
        if unlabeled > 0:
            u_item = QListWidgetItem(f"❓  Unlabeled  [{unlabeled}]")
            u_item.setData(Qt.ItemDataRole.UserRole, "__unlabeled__")
            u_item.setForeground(QColor(C['amber']))
            self.sidebar_L.addItem(u_item)

        # Auto-select current filter
        for i in range(self.sidebar_L.count()):
            if self.sidebar_L.item(i).data(Qt.ItemDataRole.UserRole) == self.current_filter:
                self.sidebar_L.setCurrentRow(i)
                break
        else:
            self.sidebar_L.setCurrentRow(0)
        
        self._refresh_toolbar_states()

    def _refresh_gallery(self):
        # Remove all except the stretch at the end
        while self.gallery_layout.count() > 1:
            item = self.gallery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_names = self.lm.get_all_frame_names()

        if self.current_filter is None:
            frames = all_names
            label_text = f"All Frames  ({len(frames)})"
        elif self.current_filter == "__unlabeled__":
            frames = [f for f in all_names if not self.lm.get_label(f)]
            label_text = f"Unlabeled  ({len(frames)})"
        else:
            frames = []
            for fname in all_names:
                lbls = self.lm.get_labels(fname)
                if any(l.get("label") == self.current_filter for l in lbls):
                    frames.append(fname)
            label_text = f"{self.current_filter}  ({len(frames)})"

        self.gallery_label.setText(label_text)

        for fname in frames[:200]:   # cap at 200 for performance
            thumb = FrameThumb(fname, self.lm.ext_dir / fname, self.lm.get_label(fname))
            thumb.clicked.connect(self._on_frame_clicked)
            self.gallery_layout.insertWidget(self.gallery_layout.count() - 1, thumb)

    # ── EVENTS ───────────────────────────────────────────────────────────────

    def _on_sidebar_menu(self, pos):
        from PyQt6.QtWidgets import QMenu, QMessageBox  # hoisted: needed in all branches
        item = self.sidebar_L.itemAt(pos)
        if not item: return
        
        action_name = item.data(Qt.ItemDataRole.UserRole)
        # Don't allow renaming/deleting 'All Frames' or 'Unlabeled'
        if action_name in [None, "unlabeled"]: return

        menu = QMenu(self)
        menu.setStyleSheet(f"background: {C['bg_panel']}; color: {C['text']}; border: 1px solid {C['border']};")
        
        rename_act = menu.addAction("✏️ Rename Action")
        type_act   = menu.addAction("💠 Change Type")
        delete_act = menu.addAction("🗑️ Delete Action")
        
        action = menu.exec(self.sidebar_L.mapToGlobal(pos))
        
        if action == rename_act:
            new_name, ok = QInputDialog.getText(self, "Rename Action", f"New name for '{action_name}':")
            if ok and new_name and new_name != action_name:
                self.lm.rename_action(action_name, new_name)
                self._refresh()
                QMessageBox.information(self, "Success", f"Renamed '{action_name}' to '{new_name}'")

        if action == type_act:
            dlg = ActionTypeDialog(self)
            if dlg.exec():
                choice = dlg.textValue()
                # 🧬 10/10 DNA Matchmaking Map
                type_map = {
                    "🔘 Click Only": "point",
                    "🏹 Swipe Only": "swipe",
                    "🟦 Rectangle Only": "rect",
                    "🟦 + 🔘 Hybrid: Area + Click": "rect_click",
                    "🟦 + 🏹 Hybrid: Area + Swipe": "rect_swipe",
                    "🔘 + 🏹 Hybrid: Click + Swipe": "click_swipe",
                    "🟦 + 🔘 + 🏹 Hybrid: Area + Click + Swipe": "rect_click_swipe",
                    "📍 State: Visual Context / Landmark": "state"
                }
                new_type = type_map.get(choice, "rect")
                
                # 🧬 10/10 DNA AUDIT: Detect incompatible frames (Fixed: Use _labels)
                mismatched_frames = []
                for f_name, labels in self.lm._labels.items():
                    # Check if this frame has any labels of this category that don't match the new type
                    if any(l.get("label") == action_name and l.get("type", "rect") != new_type for l in labels):
                        mismatched_frames.append(f_name)

                if mismatched_frames:
                    count = len(mismatched_frames)
                    msg = (f"⚠️ INCOMPATIBLE DNA DETECTED\n\n"
                           f"The action '{action_name}' has {count} frame(s) labeled with a different interaction type.\n\n"
                           f"To change type to '{new_type}', you must DELETE these labeled frames from this category. Proceed?")
                    
                    btn = QMessageBox.warning(self, "Surgical Audit", msg, 
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                              QMessageBox.StandardButton.Cancel)
                    if btn == QMessageBox.StandardButton.Cancel:
                        self.status_bar.setText("  🛑 Type change cancelled to protect data.")
                        return
                    
                    # Surgical Purge 🗑️
                    for f_name in mismatched_frames:
                        self.lm.remove_label_instance(f_name, action_name)
                    self.status_bar.setText(f"  ✨ Purged {count} incompatible frames. DNA updated.")
                
                self.lm.set_action_type(action_name, new_type)
                self._refresh()
                self.status_bar.setText(f"  🧬 Updated DNA for '{action_name}' to {new_type}")
        
        if action == delete_act:
            btn = QMessageBox.warning(self, "Delete Action", 
                                      f"Are you sure you want to delete the '{action_name}' category?\n\n"
                                      "This will remove ALL labels in this category.",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if btn == QMessageBox.StandardButton.Yes:
                count = self.lm.delete_action(action_name)
                # If deleted, clear custom_actions too
                if action_name in self.custom_actions:
                    self.custom_actions.remove(action_name)
                self._refresh()
                QMessageBox.information(self, "Deleted", f"Removed category '{action_name}' and {count} labels.")

    def _on_box_delete_requested(self, label_data):
        """Remove a specific box from the data."""
        if not self.current_frame: return
        lbls = self.lm.get_labels(self.current_frame)
        if label_data in lbls:
            lbls.remove(label_data)
            self.lm.save()
            self._refresh()
            self._on_frame_clicked(self.current_frame)

    def _on_resize_finished(self, label_data, new_rect: QRectF):
        """Finalize the new size of a label."""
        if not self.current_frame: return
        lbls = self.lm.get_labels(self.current_frame)
        
        # Match using identity (id) to be 100% sure we find the right ref
        target = None
        for l in lbls:
            if id(l) == id(label_data):
                target = l
                break
                
        if target:
            # Update the original data object
            target["x"] = int(new_rect.x())
            target["y"] = int(new_rect.y())
            target["w"] = int(new_rect.width())
            target["h"] = int(new_rect.height())
            
            self.lm.save()
            # Clear canvas and reload THIS frame specifically
            self.canvas.load_frame(self.lm.ext_dir / self.current_frame, lbls)
            self.status_bar.setText(f"  💾 Locked resize for {self.current_frame}")

    def _on_sidebar_clicked(self, item):
        new_filter = item.data(Qt.ItemDataRole.UserRole)
        
        # 🧬 10/10 BINDING COMMIT 🧬
        if hasattr(self, "binding_queue") and self.binding_queue:
            if new_filter in [None, "__unlabeled__"]:
                QMessageBox.warning(self, "Invalid Action", "Select a real Action category to bind these components.")
                return
                
            # PERFORM BINDING
            self.lm.set_label(self.current_frame, new_filter, components=self.binding_queue)
            self.lm.save()
            
            # Cleanup
            self.binding_queue = []
            self.drafts = []
            self.sidebar_L.setStyleSheet(QSS_SIDEBAR) # Reset style
            
            self._refresh()
            self._on_frame_clicked(self.current_frame)
            QMessageBox.information(self, "Bound", f"Successfully bound components to '{new_filter}'.")
            return

        self.current_filter = new_filter
        
        # 10/10 AUTO-SWITCH: Set tool based on action type
        if self.current_filter not in ["all", "__unlabeled__"]:
            a_type = self.lm.get_action_type(self.current_filter)
            self._set_drawing_mode(a_type)
            
        self._refresh_gallery()
        self._refresh_toolbar_states()
        if self.current_frame:
            self._on_frame_clicked(self.current_frame)

    def _on_frame_clicked(self, fname: str):
        """10/10 Frame Transition: Mirror complete interaction inventory + Ghost Overlay."""
        if self.current_frame != fname:
            # 🔮 Store current labels as ghost before switching
            if self.current_frame:
                self.canvas._ghost_labels = self.lm.get_labels(self.current_frame)
            self.drafts = []  # Reset drafts on new frame
            
        self.current_frame = fname
        labels = self.lm.get_labels(fname)
        
        # Load Canvas with both Bound & Draft components
        self.canvas.load_frame(self.lm.ext_dir / fname, labels, self.drafts)
        
        # Update Workbench Inventory
        self._refresh_workbench()
        
        # Status Text
        if labels:
            lbl = labels[0]
            src_txt = f"  [{lbl.get('source','—')}]  {lbl.get('label','Unlabeled')} (+{len(labels)-1} more)" if len(labels) > 1 else f"  [{lbl.get('source','—')}]  {lbl.get('label','Unlabeled')}"
            self.status_bar.setText(f"  📂  {fname}{src_txt}")
        else:
            self.status_bar.setText(f"  📂  {fname} (Unlabeled)")
            
        self._refresh_toolbar_states()
        
        # AI Verdict Bar — Confidence-Stratified
        self.verdict_bar.hide()
        if labels and self.current_filter and self.current_filter not in ["all", "__unlabeled__"]:
            has_ai = any(l.get("label") == self.current_filter and l.get("source", "").startswith("auto") for l in labels)
            if has_ai: self.verdict_bar.show()


    def _on_new_action(self):
        """Create a placeholder action from the sidebar + button."""
        name, ok = QInputDialog.getText(self, "New Action", "Action name (label):")
        if not ok or not name.strip(): return
        name = name.strip()
        if name in self.custom_actions: return
        dlg = ActionTypeDialog(self)
        if dlg.exec():
            type_map = {
                "🔘 Click Only": "point", "🏹 Swipe Only": "swipe", "🟦 Rectangle Only": "rect",
                "🟦 + 🔘 Hybrid: Area + Click": "rect_click", "🟦 + 🏹 Hybrid: Area + Swipe": "rect_swipe",
                "🔘 + 🏹 Hybrid: Click + Swipe": "click_swipe",
                "🟦 + 🔘 + 🏹 Hybrid: Area + Click + Swipe": "rect_click_swipe",
                "📍 State: Visual Context / Landmark": "state"
            }
            a_type = type_map.get(dlg.textValue(), "rect")
            self.custom_actions.add(name)
            self.lm.set_action_type(name, a_type)
            self._refresh()
            self.status_bar.setText(f"  ✨ Created '{a_type}': {name}")
            for i in range(self.sidebar_L.count()):
                if self.sidebar_L.item(i).data(Qt.ItemDataRole.UserRole) == name:
                    self.sidebar_L.setCurrentRow(i); break

    def _refresh_toolbar_states(self):
        """10/10 Smart Gating: Only enable AI tools if an action/area is defined."""
        # 1. Check sidebar action
        selected_action = self.current_filter
        has_action = (selected_action is not None and selected_action not in ["all", "unlabeled", "unknown"])
        
        # 2. Check current frame box for that action
        has_box = False
        if has_action and self.current_frame:
            lbls = self.lm.get_labels(self.current_frame)
            has_box = any(l.get("label") == selected_action for l in lbls)
            
        # 3. Check for interpolation (requires at least 1 other boxed frame)
        has_neighbor = False
        if has_box:
            # We already have 1 box on current frame. Check if there are any others for THIS action.
            all_labels = self.lm.get_all_labels()
            other_frames = [f for f, lbls in all_labels.items() if any(l.get("label") == selected_action for l in lbls)]
            has_neighbor = len(other_frames) >= 2

        # Apply states
        self.btn_search.setEnabled(has_box)
        self._set_btn_opacity(self.btn_search, 1.0 if has_box else 0.4)
        
        self.btn_interp.setEnabled(has_neighbor)
        self._set_btn_opacity(self.btn_interp, 1.0 if has_neighbor else 0.4)
        
        self.btn_track.setEnabled(has_box)
        self._set_btn_opacity(self.btn_track, 1.0 if has_box else 0.4)
        
        # Auto-Label is always open for discovery
        self.btn_auto.setEnabled(True)
        self._set_btn_opacity(self.btn_auto, 1.0)

    # ── AI HELPERS ──────────────────────────────────────────────────────────

    def _on_ai_progress(self, current, total, text):
        self.overlay.update_progress(current, total, text)

    def _on_ai_finished(self, result):
        self.overlay.hide()
        if self._ai_worker:
            self._ai_worker = None
        
        # Specific completion logic
        if self.current_filter_task == "auto":
            self.lm.save()
            self._refresh()
            QMessageBox.information(self, "🤖 Auto-Label Done", f"AI processed all frames and updated labels!")
        elif self.current_filter_task == "search":
            if result:
                # 🤖 10/10 CONFIDENCE-STRATIFIED AUTO-LABELING
                TIER_HIGH   = 0.92   # Apply silently
                TIER_MEDIUM = 0.75   # Show in bulk review
                TIER_LOW    = 0.60   # Discard

                tier_high, tier_medium = [], []
                for r in result:
                    conf = r.get("confidence", 0.0)
                    if conf >= TIER_HIGH:
                        tier_high.append(r)
                    elif conf >= TIER_MEDIUM:
                        tier_medium.append(r)
                    # below TIER_LOW: silently dropped

                # Apply Tier 1 silently
                applied_high = 0
                for r in tier_high:
                    fname = r.get("frame")
                    if not fname: continue
                    action_name = r.get("label") or self.current_filter or "unlabeled"
                    r["label"] = action_name
                    if "type" in r: r["g_type"] = r.pop("type")
                    if "frame" in r: r.pop("frame")
                    self.lm.set_label(fname, **r)
                    applied_high += 1

                self.lm.save()
                self._refresh()

                # Show Tier 2 in Bulk Review dialog
                if tier_medium:
                    dlg = BulkReviewDialog(tier_medium, self.lm.ext_dir, self.current_filter or "action", self)
                    dlg.exec()
                    for fname, approved in dlg.decisions.items():
                        if approved:
                            for r in tier_medium:
                                if r.get("frame") == fname:
                                    r["label"] = self.current_filter or r.get("label") or "unlabeled"
                                    if "type" in r: r["g_type"] = r.pop("type")
                                    if "frame" in r: r.pop("frame")
                                    self.lm.set_label(fname, **r)
                    self.lm.save()
                    self._refresh()

                total_applied = applied_high + sum(1 for v in dlg.decisions.values() if v) if tier_medium else applied_high
                msg = (f"✅ Applied {applied_high} frames silently (Tier 1 ≥{int(TIER_HIGH*100)}%)\n"
                       f"🟡 Reviewed {len(tier_medium)} frames in Bulk Review (Tier 2)\n"
                       f"🚫 Discarded {len(result)-applied_high-len(tier_medium)} low-confidence frames")
                QMessageBox.information(self, "🔍 Search Complete", msg)
            else:
                QMessageBox.information(self, "🔍 Search Similar", "AI Finished: No similar visual landmarks were discovered.")

        elif self.current_filter_task == "track":
            if result:
                current_label = self.lm.get_label(self.current_frame)
                action_name = current_label["label"]
                all_f = self.lm.get_all_frame_names()
                s_idx = all_f.index(self.current_frame)
                for i, r in enumerate(result):
                    fname = all_f[s_idx + 1 + i]
                    r["label"] = action_name
                    # 🧬 10/10 REMAP: Translate AI 'type' to storage 'g_type'
                    if "type" in r: r["g_type"] = r.pop("type")
                    # 🧬 10/10 CLEANUP: Remove redundant 'frame' key
                    if "frame" in r: r.pop("frame")
                    
                    # 10/10 MERGE: Skip if already manual
                    existing = self.lm.get_labels(fname)
                    if any(l.get("label") == action_name and l.get("source") == "manual" for l in existing):
                        continue
                    self.lm.set_label(fname, **r)
                self.lm.save()
                self._refresh()
                QMessageBox.information(self, "🎯 AI Tracker", f"Tracked through {len(result)} frames successfully.")
            else:
                QMessageBox.information(self, "🎯 AI Tracker", "AI Finished: No matching objects could be tracked sequentially from this frame.")
        elif self.current_filter_task == "interp":
            self._refresh()
            QMessageBox.information(self, "Bridge Done", f"Successfully interpolated {result} frames.")

    def _on_ai_cancel_requested(self):
        if self._ai_worker:
            self._ai_worker.stop()
            self.status_bar.setText("  🛑 AI Task Cancelled")
            self._refresh_toolbar_states()

    def _on_verdict_true(self):
        """Confirm AI suggestion -> Manual."""
        if not self.current_frame or not self.current_filter: return
        labels = self.lm.get_labels(self.current_frame)
        for l in labels:
            if l.get("label") == self.current_filter and l.get("source", "").startswith("auto"):
                l["source"] = "manual"
                l["confidence"] = 1.0
        self.lm.save()
        self.verdict_bar.hide()
        self.canvas.load_frame(self.lm.ext_dir / self.current_frame, labels)
        self._refresh_toolbar_states()
        self.status_bar.setText(f"  ✅ Confirmed '{self.current_filter}' for {self.current_frame}")

    def _on_verdict_false(self):
        """Reject AI suggestion -> Delete."""
        if not self.current_frame or not self.current_filter: return
        labels = self.lm.get_labels(self.current_frame)
        new_labels = [l for l in labels if not (l.get("label") == self.current_filter and l.get("source", "").startswith("auto"))]
        self.lm._labels[self.current_frame] = new_labels
        self.lm.save()
        self.verdict_bar.hide()
        self.canvas.load_frame(self.lm.ext_dir / self.current_frame, new_labels)
        self._refresh_toolbar_states()
        self.status_bar.setText(f"  ❌ Rejected AI action for {self.current_frame}")

    # ── AI FEATURES ──────────────────────────────────────────────────────────

    def _start_ai_task(self, task_type, args=None):
        self.current_filter_task = task_type
        
        # 🧬 10/10 DYNAMIC BRANDING
        titles = {
            "search": ("AI Similarity Discovery", "🔍"),
            "track":  ("AI Motion Tracking", "🎯"),
            "interp": ("Bridging Frame DNA", "📐"),
            "auto":   ("Autonomous Labeling", "🤖")
        }
        title, icon = titles.get(task_type, ("AI Processing", "🤖"))
        
        # 🧪 MANIFEST: Ensure the overlay is perfectly centered before showing
        self.overlay.sync_geometry()
        self.overlay.show_loading(f"Initializing {title}...")
        self.overlay.title.setText(f"{icon} {title}")
        self.overlay.show()
        self.overlay.raise_()
        
        logger.info(f"AI Task Manifesting: {task_type}")
        
        self._ai_worker = AIWorker(task_type, self.lm, args)
        self._ai_worker.progress.connect(self._on_ai_progress)
        self._ai_worker.finished.connect(self._on_ai_finished)
        self._ai_worker.error.connect(self._on_ai_error)
        self._ai_worker.start()

    def _on_ai_progress(self, current, total, status):
        # 🧪 TYPOGRAPHY: Ensure status uses Segoe UI via stylesheet
        self.overlay.update_progress(current, total, status)

    def _on_ai_error(self, err_msg):
        self.overlay.hide()
        QMessageBox.critical(self, "AI Error", f"The AI engine encountered a surgical failure:\n\n{err_msg}")
        self._ai_worker = None

    def _on_auto_label(self):
        self._start_ai_task("auto")

    def _on_search_similar(self):
        """10/10 Hybrid Search: Uses the Area (Rectangle) component as the template."""
        if not self.current_frame: return
        
        # 🧬 DNA RETRIEVAL: Find the best template component based on current category
        labels = self.lm.get_labels(self.current_frame)
        label = None
        if self.current_filter:
            label = next((l for l in labels if l.get("label") == self.current_filter), None)
        else:
            label = labels[0] if labels else None

        if not label:
            QMessageBox.information(self, "No Anchor", "This action needs a Rectangle Area or State on the current frame to search.")
            return
            
        logger.info(f"Anchor found: Type={label.get('type')}")
        search_template = None
        l_type = label.get("type", "rect")

        # 🎯 High-Precision DNA Extraction
        if l_type in ["rect_click", "rect_swipe", "rect_click_swipe", "state"]:
            # Find the rectangle component within the complex bundle
            comps = label.get("components", [])
            rect_comp = next((c for c in comps if c.get("type") == "rect"), None)
            if rect_comp:
                # 🧬 10/10 SURGICAL DATA: Store the FULL bundle as a reference for search results
                search_template = {**rect_comp, "label": label.get("label"), "_full_bundle": label}
            else:
                QMessageBox.warning(self, "No Area", "This Interaction/State has no Rectangle component to search for.")
                return
        elif l_type == "point":
            # Points use a default 50x50 neighborhood search
            search_template = label.copy()
            search_template.update({"w": 50, "h": 50, "x": label["x"] - 25, "y": label["y"] - 25})
        else:
            # Default it to the label itself if it's a simple rect
            search_template = label.copy()
        
        # 🧬 10/10 MANIFEST: Show centered popup IMMEDIATELY
        def start_search(sens):
            self.overlay.show_loading("Scanning Project for Similar Elements...")
            args = {"frame": self.current_frame, "label": search_template, "threshold": sens}
            self._start_ai_task("search", args)

        self.overlay.show_setup("AI Similarity Sensitivity", "🔍", start_search)

    def _on_track(self):
        """10/10 Hybrid Track: Uses the Area (Rectangle) component for vision-tracking."""
        if not self.current_frame: return
        labels = self.lm.get_labels(self.current_frame)
        label = next((l for l in labels if l.get("label") == self.current_filter), None) if self.current_filter else (labels[0] if labels else None)
        if not label: return
            
        track_ref = label
        if label.get("type") == "hybrid":
            comps = label.get("components", [])
            rect_comp = next((c for c in comps if c.get("type") == "rect"), None)
            if rect_comp: track_ref = {**rect_comp, "type": "rect"}
            
        all_f = self.lm.get_all_frame_names()
        remaining = len(all_f)
        
        # 🧬 10/10 MANIFEST: Show centered popup IMMEDIATELY
        def start_tracking(sens):
            self.overlay.show_loading("Tracking Movement...")
            args = {"frame": self.current_frame, "label": track_ref, "count": remaining, "threshold": sens}
            self._start_ai_task("track", args)

        self.overlay.show_setup("AI Tracker Sensitivity", "🎯", start_tracking)

    def _on_interpolate(self):
        """10/10 AI Bridge: Interpolate labels between two sentinel frames."""
        if not self.current_frame:
            QMessageBox.information(self, "Select a Frame", "Click a frame first.")
            return
            
        current_lbl = self.lm.get_label(self.current_frame)
        if not current_lbl or "label" not in current_lbl:
            QMessageBox.warning(self, "No Action", "Current frame must have a label to interpolate.")
            return
            
        action_name = current_lbl["label"]
        all_f = self.lm.get_all_frame_names()
        curr_idx = all_f.index(self.current_frame)
        
        # Detect Neighbors with same label
        prev_f, next_f = None, None
        for i in range(curr_idx - 1, -1, -1):
            if any(l.get("label") == action_name for l in self.lm.get_labels(all_f[i])):
                prev_f = all_f[i]; break
        for i in range(curr_idx + 1, len(all_f)):
            if any(l.get("label") == action_name for l in self.lm.get_labels(all_f[i])):
                next_f = all_f[i]; break
                
        if not prev_f and not next_f:
            QMessageBox.warning(self, "Needs Neighbors", f"Need more frames labeled '{action_name}' to bridge.")
            return
            
        pair = (prev_f, next_f) if (prev_f and next_f) else ((prev_f, self.current_frame) if prev_f else (self.current_frame, next_f))
        s, e = pair
        gap = all_f[all_f.index(s) + 1 : all_f.index(e)]
        
        if not gap:
            QMessageBox.information(self, "No Gap", "No empty frames to bridge.")
            return
            
        sl = next(l for l in self.lm.get_labels(s) if l.get("label") == action_name)
        el = next(l for l in self.lm.get_labels(e) if l.get("label") == action_name)
        
        # 🎙️ 10/10 EASING SELECTOR: Let user pick physics mode before launching
        easing_items = [
            "linear — Constant speed (mechanical)",
            "ease_out — Fast start, soft settle (most mobile animations)",
            "ease_in — Slow start, fast end (slide-in elements)",
            "ease_in_out — Smooth S-curve (premium natural motion)",
        ]
        easing_choice, ok = QInputDialog.getItem(
            self, "🌉 Interpolation Physics",
            f"Bridge gap of {len(gap)} frames with what motion curve?",
            easing_items, 1, False
        )
        if not ok: return
        easing_key = easing_choice.split(" ")[0]  # extract 'linear', 'ease_out', etc.
        
        self._start_ai_task("interp", {"sl": sl, "el": el, "gap": gap, "act": action_name, "easing": easing_key})

    def _on_workbench_menu(self, pos):
        """10/10 Surgical Purge: Delete components."""
        item = self.workbench.itemAt(pos)
        if not item: return
        widget = self.workbench.itemWidget(item)
        if not widget or not widget.data: return
        
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"background: {C['bg_panel']}; color: {C['text']}; border: 1px solid {C['border']};")
        menu.addAction("🗑️ Delete Component")
        
        from PyQt6.QtGui import QCursor
        if menu.exec(QCursor.pos()):
            cid = widget.data.get("cid", "")
            if cid.startswith("draft_"):
                self.drafts = [d for d in self.drafts if d.get("cid") != cid]
                self.status_bar.setText(f"  🗑️ Purged draft component.")
            else:
                action_name = widget.data.get("parent_label", "Unknown")
                if QMessageBox.question(self, "Delete", f"Permanently delete '{action_name}'?") == QMessageBox.StandardButton.Yes:
                    self.lm.remove_label_instance(self.current_frame, action_name)
                    self.status_bar.setText(f"  🗑️ Deleted interaction: {action_name}")
            self._on_frame_clicked(self.current_frame)

    def _on_interaction_added(self, data):
        self.drafts.append(data)
        self._refresh_workbench()
        if self.current_frame: self._on_frame_clicked(self.current_frame)
        
    def _on_clear_workbench(self):
        self.drafts = []
        if self.current_frame: self._on_frame_clicked(self.current_frame)
        else: self._refresh_workbench()

    def _on_bind_requested(self):
        """10/10 Binding: Strict DNA Match Filtering."""
        selected_drafts = []
        for i in range(self.workbench.count()):
            w = self.workbench.itemWidget(self.workbench.item(i))
            if w and w.check.isChecked() and not "label" in w.data:
                selected_drafts.append(w.data)
                
        if not selected_drafts:
            QMessageBox.information(self, "Empty", "Check draft components to bind.")
            return

        # 🧬 10/10 DNA MATCHMAKING: Precise Recipe Detection
        sel_types = [d.get("type", "rect") for d in selected_drafts]
        is_hybrid = len(selected_drafts) > 1
        
        # Calculate DNA string for current selection 🧬
        current_dna = "rect" # Default 
        if not is_hybrid:
            current_dna = sel_types[0]
        elif len(sel_types) == 2:
            if "rect" in sel_types and "point" in sel_types: current_dna = "rect_click"
            elif "rect" in sel_types and "swipe" in sel_types: current_dna = "rect_swipe"
            elif "point" in sel_types and "swipe" in sel_types: current_dna = "click_swipe"
        elif len(sel_types) >= 3:
            current_dna = "rect_click_swipe"
            
        self.status_bar.setText(f"  🧬 Matchmaking DNA: {current_dna} (Hybrid: {is_hybrid})")

        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"background: {C['bg_panel']}; color: {C['white']}; border: 1px solid {C['border']};")
        # 🧪 TYPOGRAPHY: Force Segoe UI for this menu to avoid GDI errors
        menu.setFont(QFont("Segoe UI", 10))

        # 🧬 10/10 DNA ICONOGRAPHY
        icon_map = {
            "point": "🔘",
            "swipe": "🏹",
            "rect":  "🟦",
            "rect_click": "🟦🔘",
            "rect_swipe": "🟦🏹",
            "click_swipe": "🔘🏹",
            "rect_click_swipe": "🧬🔥",
            "state": "📍"
        }

        # 🧬 10/10 STRICT DNA MATCHMAKING
        menu.addSection(f"✨ Matching Actions ({current_dna})")
        matching_count = 0
        all_actions = sorted(list(self.custom_actions))
        
        for act in all_actions:
            a_type = self.lm.get_action_type(act)
            icon = icon_map.get(a_type, "🏷")
            # 🎯 🥇 10/10 Universal State Matching 🥇
            # A "State" always matches if any components are selected
            if a_type == current_dna or a_type == "state":
                menu.addAction(f"{icon}  {act}"); matching_count += 1
        
        if matching_count == 0:
            msg = menu.addAction(f"(No exact {current_dna} actions found)")
            msg.setEnabled(False)
            tip = menu.addAction("💡 Tip: Select an 'Other' action below to UPGRADE its DNA.")
            tip.setEnabled(False)
            tip.setFont(QFont("Segoe UI", 8, QFont.Weight.Light))
            
        menu.addSeparator()
        menu.addSection("📎 Other Actions (Different DNA)")
        for act in all_actions:
            a_type = self.lm.get_action_type(act)
            icon = icon_map.get(a_type, "🏷")
            if a_type != current_dna:
                menu.addAction(f"{icon}  {act}  [{a_type}]")

        menu.addSeparator()
        new_act = menu.addAction("➕  Create New Action...")
        
        from PyQt6.QtCore import QPoint
        pos = self.mapToGlobal(self.rect().center()) - QPoint(menu.sizeHint().width() // 2, menu.sizeHint().height() // 2)
        choice = menu.exec(pos)
        if not choice: return
        
        final_name = ""
        if choice == new_act:
            name, ok = QInputDialog.getText(self, "New Action", f"Name for this {current_dna} action:")
            if ok and name.strip():
                final_name = name.strip()
                self.custom_actions.add(final_name)
                self.lm.set_action_type(final_name, current_dna)
                self._refresh_sidebar() # 🧬 10/10 SYNC: Instant sidebar update
        elif choice.text().startswith("("):
            return # User clicked a hint
        else:
            # Extract name and clean DNA suffix if present
            # We need to handle icons like 🔘, 🏹, 🟦 (which might be multi-char)
            # Standard pattern: {icon}  {name}  [{type}]
            raw_text = choice.text()
            # Split by double space to isolate the name
            parts = raw_text.split("  ")
            if len(parts) >= 2:
                final_name = parts[1].strip()
            else:
                final_name = raw_text.replace("🏷  ", "").strip()
            
            # Remove any trailing "  [type]"
            final_name = final_name.split("  [")[0].strip()
            
            # 🧬 DNA CONFLICT RESOLUTION
            target_type = self.lm.get_action_type(final_name)
            # Note: 'state' acts as a universal receiver, so it rarely conflicts, 
            # but if we're moving AWAY from state or to a different specific hybrid, we audit.
            if target_type != current_dna and target_type != "state":
                msg = (f"🧬 DNA MISMATCH DETECTED\n\n"
                       f"Action '{final_name}' is currently type '{target_type}'.\n"
                       f"Your selection is type '{current_dna}'.\n\n"
                       f"Would you like to CHANGE '{final_name}' to '{current_dna}' to accommodate these components?")
                
                btn = QMessageBox.question(self, "Surgical DNA Upgrade", msg,
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if btn == QMessageBox.StandardButton.Yes:
                    self.lm.set_action_type(final_name, current_dna)
                    self.status_bar.setText(f"  🧬 Surgically upgraded '{final_name}' to {current_dna}")
                else:
                    return # User cancelled
            
            # 🧬 DNA SANITIZATION: Clean data before moving to LabelManager
            # selected_drafts[0] contains keys like "type" and "cid" which set_label doesn't want as kwargs
            save_data = {}
            if not is_hybrid:
                comp = selected_drafts[0]
                save_data = {k: v for k, v in comp.items() if k not in ["type", "cid", "icon"]}
                
            self.lm.set_label(self.current_frame, final_name, g_type=current_dna, 
                              components=selected_drafts if is_hybrid else None, 
                              **save_data)
            self.lm.save()
            self.drafts = [d for d in self.drafts if d not in selected_drafts]
            # Refresh everything
            self._on_frame_clicked(self.current_frame)
            self._refresh_sidebar()
            self.status_bar.setText(f"  ✅ Bound to '{final_name}' ({current_dna})")

    def _on_new_action(self):
        name, ok = QInputDialog.getText(self, "New Category", "Action Name:")
        if not ok or not name.strip(): return
        if name.strip() in self.custom_actions: return
        
        dlg = ActionTypeDialog(self)
        if dlg.exec():
            type_map = {
                "🔘 Click Only": "point", "🏹 Swipe Only": "swipe", "🟦 Rectangle Only": "rect",
                "🟦 + 🔘 Hybrid: Area + Click": "rect_click", "🟦 + 🏹 Hybrid: Area + Swipe": "rect_swipe",
                "🔘 + 🏹 Hybrid: Click + Swipe": "click_swipe",
                "🟦 + 🔘 + 🏹 Hybrid: Area + Click + Swipe": "rect_click_swipe",
                "📍 State: Visual Context / Landmark": "state"
            }
            a_type = type_map.get(dlg.textValue(), "rect")
            self.custom_actions.add(name.strip())
            self.lm.set_action_type(name.strip(), a_type)
            self._refresh(); self.status_bar.setText(f"  ✨ Created '{a_type}': {name}")

    def _on_save(self):
        self.lm.save()
        self.status_bar.setText("  💾 Saved successfully.")

    # ── RECORD MODE ──────────────────────────────────────────────────────────

    def _on_toggle_record(self):
        """
        10/10 Live Gesture Record Mode: Captures real touches via ADB getevent
        and auto-creates draft components on the current frame.
        """
        if self._is_recording:
            # ── STOP ──
            self._is_recording = False
            if self._record_worker:
                self._record_worker.stop()
                self._record_worker = None
            self.btn_record.setText("⏺  Record")
            self.btn_record.setStyleSheet(
                self.btn_record.styleSheet().replace(C['amber'], C['red'])
            )
            self.status_bar.setText("  ⏹️ Recording stopped.")
        else:
            # ── START ──
            if not self.current_frame:
                QMessageBox.warning(self, "No Frame", "Select a frame before recording.")
                return
            try:
                from backend.core.mobile_manager import MobileManager
                mgr = MobileManager.get_instance()
                if not mgr or not mgr.device_id:
                    QMessageBox.warning(self, "No Device", "Connect an Android device first.")
                    return
                device_id = mgr.device_id
            except Exception:
                QMessageBox.warning(self, "ADB Error", "Could not access MobileManager.")
                return

            self._is_recording = True
            self.btn_record.setText("⏹  Stop Rec")
            self.btn_record.setStyleSheet(
                self.btn_record.styleSheet().replace(C['red'], C['amber'])
            )
            self.status_bar.setText(f"  ⏺ Recording gestures on {self.current_frame}... Touch the device!")

            from PyQt6.QtCore import QThread
            import subprocess, re

            class RecordWorker(QThread):
                tap_detected = pyqtSignal(int, int)

                def __init__(self, device_id):
                    super().__init__()
                    self.device_id = device_id
                    self._running = True

                def run(self):
                    proc = subprocess.Popen(
                        ["adb", "-s", self.device_id, "shell", "getevent", "-l"],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
                    )
                    x, y = None, None
                    for line in proc.stdout:
                        if not self._running: break
                        if "ABS_MT_POSITION_X" in line:
                            try: x = int(line.split()[-1], 16)
                            except: pass
                        elif "ABS_MT_POSITION_Y" in line:
                            try: y = int(line.split()[-1], 16)
                            except: pass
                        elif "SYN_REPORT" in line and x is not None and y is not None:
                            self.tap_detected.emit(x, y)
                            x, y = None, None
                    proc.terminate()

                def stop(self):
                    self._running = False

            self._record_worker = RecordWorker(device_id)
            self._record_worker.tap_detected.connect(self._on_recorded_tap)
            self._record_worker.start()

    def _on_recorded_tap(self, x: int, y: int):
        """Receives a live tap from ADB getevent and adds it as a draft Point."""
        if not self.current_frame: return
        draft = {"type": "point", "x": x, "y": y, "source": "record"}
        self.drafts.append(draft)
        self._refresh_workbench()
        self._on_frame_clicked(self.current_frame)
        self.status_bar.setText(f"  ⏺ Captured tap: x={x} y={y}")

    # ── KEYBOARD NAVIGATION ───────────────────────────────────────────────────

    def keyPressEvent(self, event):
        """10/10 Keyboard Shortcuts for high-speed labeling."""
        all_names = self.lm.get_all_frame_names()
        key = event.key()

        if self.current_frame and all_names:
            idx = all_names.index(self.current_frame) if self.current_frame in all_names else -1

            # Arrow navigation
            if key == Qt.Key.Key_Right and idx < len(all_names) - 1:
                self._on_frame_clicked(all_names[idx + 1])
                return
            elif key == Qt.Key.Key_Left and idx > 0:
                self._on_frame_clicked(all_names[idx - 1])
                return

        # Verdict shortcuts
        if key == Qt.Key.Key_Y and self.verdict_bar.isVisible():
            self._on_verdict_true(); return
        if key == Qt.Key.Key_N and self.verdict_bar.isVisible():
            self._on_verdict_false(); return

        # Save shortcut
        if key == Qt.Key.Key_S and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._on_save(); return

        super().keyPressEvent(event)


# ── STYLESHEET ────────────────────────────────────────────────────────────────

QSS_SIDEBAR = f"""
QListWidget {{
    background: {C['bg_sidebar']};
    border: none;
    padding: 8px 6px;
    font-size: 13px;
    outline: none;
}}
QListWidget::item {{
    padding: 12px 14px;
    color: {C['text']};
    border-radius: 4px;
    margin: 2px 0px;
    border-left: 3px solid transparent;
}}
QListWidget::item:hover {{
    background: {C['bg_panel']};
    color: {C['white']};
}}
QListWidget::item:selected {{
    background: {C['purple']}44;
    color: {C['white']};
    font-weight: bold;
    border-left: 3px solid {C['cyan']};
    padding-left: 11px;
}}
"""
