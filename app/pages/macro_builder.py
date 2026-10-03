from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QStackedWidget, QProgressBar, QGridLayout,
    QLineEdit, QTextEdit, QCheckBox, QSlider, QComboBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPen

from app.theme import C, FONT_UI, FONT_MONO

class MacroBuilderHeader(QFrame):
    """Fixed header for Macro Builder."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("macro_header")
        self.setFixedHeight(80)
        self.setStyleSheet(f"""
            #macro_header {{
                background-color: {C['bg_sidebar']};
                border-bottom: 2px solid {C['border']};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Left: Icon and Name
        left = QVBoxLayout()
        title = QLabel("⬡ MACRO BUILDER")
        title.setStyleSheet(f"color: {C['purple_l']}; font-weight: bold; font-size: 14px;")
        left.addWidget(title)
        
        self.name_input = QLineEdit("coinglass_full_agent")
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {C['white']};
                font-size: 18px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid transparent;
            }}
            QLineEdit:hover, QLineEdit:focus {{ border-bottom: 1px solid {C['purple_l']}; }}
        """)
        left.addWidget(self.name_input)
        layout.addLayout(left)
        
        layout.addStretch()
        
        # Right: Action Buttons
        actions = QHBoxLayout()
        actions.setSpacing(10)
        
        def btn(text, color):
            b = QPushButton(text)
            b.setFixedSize(120, 36)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {color};
                    border: 1px solid {color}88;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background: {color}22; }}
            """)
            return b

        self.dry_run_btn = btn("▶ Dry Run", C['purple_l'])
        self.save_btn = btn("💾 Save Macro", C['amber'])
        
        self.launch_btn = QPushButton("🚀 Launch Agent")
        self.launch_btn.setFixedSize(140, 36)
        self.launch_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {C['green']}, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {C['green']}; }}
        """)
        
        actions.addWidget(self.dry_run_btn)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.launch_btn)
        
        layout.addLayout(actions)

    def _section_header(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text_d']}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        return l


class LeftPanel(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"background: {C['bg_sidebar']}; border-right: 1px solid {C['border']};")
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(20)
        
        # Add Node Types
        layout.addWidget(self._section_header("ADD TO PIPELINE"))
        grid = QGridLayout()
        grid.setSpacing(8)
        nodes = [
            ("⊞", "Model", C['green']),
            ("◆", "Condition", C['amber']),
            ("↺", "Loop", C['cyan']),
            ("⟦⟧", "Parallel", C['purple_l']),
            ("⚙", "Action", C['text']),
            ("⏱", "Wait", C['cyan'])
        ]
        for i, (icon, text, color) in enumerate(nodes):
            b = QPushButton(f"{icon} {text}")
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {C['text_b']};
                    border: 1px solid {color}44;
                    border-radius: 4px;
                    padding: 10px 5px;
                    font-size: 11px;
                }}
                QPushButton:hover {{ border-color: {color}; background: {color}11; }}
            """)
            grid.addWidget(b, i // 2, i % 2)
        layout.addLayout(grid)
        
        # Your Models
        layout.addWidget(self._section_header("YOUR MODELS"))
        models = [
            ("click_clusters", "Visual Detection · 94.2", "trained"),
            ("read_popup", "Data Extraction · 91.7", "trained"),
            ("assess_chart", "Visual Detection · 61.0", "training"),
        ]
        for name, desc, status in models:
            m_row = QFrame()
            m_row.setStyleSheet(f"background: {C['bg_panel']}44; border-radius: 4px;")
            ml = QVBoxLayout(m_row)
            ml.setContentsMargins(8, 8, 8, 8)
            title_row = QHBoxLayout()
            dot = QLabel("●" if status == "trained" else "◐")
            dot.setStyleSheet(f"color: {C['green'] if status == 'trained' else C['amber']}; font-size: 14px;")
            title_row.addWidget(dot)
            title_row.addWidget(QLabel(name), 1)
            add_b = QPushButton("+ Add")
            add_b.setStyleSheet(f"color: {C['purple_l']}; font-size: 11px; border: none;")
            title_row.addWidget(add_b)
            ml.addLayout(title_row)
            ml.addWidget(QLabel(desc))
            layout.addWidget(m_row)
            
        layout.addStretch()
        self.setWidget(widget)

    def _section_header(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text_d']}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        return l


class NodeWidget(QFrame):
    """A node on the canvas."""
    def __init__(self, type_name, name, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(220, 90)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_panel']};
                border: 1px solid {C['border']};
                border-left: 4px solid {color};
                border-radius: 6px;
                color: {C['text_b']};
            }}
        """)
        l = QVBoxLayout(self)
        l.setContentsMargins(12, 10, 12, 10)
        
        title = QLabel(name)
        title.setStyleSheet(f"font-weight: bold; font-size: 13px; border: none;")
        l.addWidget(title)
        
        desc = QLabel(type_name)
        desc.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; border: none;")
        l.addWidget(desc)
        
        meta = QLabel("On fail: Retry 3×")
        meta.setStyleSheet(f"color: {C['text_d']}; font-size: 10px; border: none;")
        l.addWidget(meta)


class CanvasArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: #080a14;") # Almost black
        
        # Main vertical layout for nodes
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.setContentsMargins(0, 60, 0, 60)
        self.main_layout.setSpacing(50)
        
        self._add_fixed_nodes()
        
    def _add_fixed_nodes(self):
        # Start Node
        start = QFrame()
        start.setFixedSize(120, 34)
        start.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 4px; color: {C['text_d']};")
        sl = QVBoxLayout(start)
        sl.setContentsMargins(0, 0, 0, 0)
        l = QLabel("START")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.setStyleSheet("font-weight: bold; border: none;")
        sl.addWidget(l)
        self.main_layout.addWidget(start, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Nodes
        self.main_layout.addWidget(NodeWidget("Visual Detection", "open_coinglass", C['green']), alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(NodeWidget("Visual Detection", "click_clusters", C['green']), alignment=Qt.AlignmentFlag.AlignCenter)
        
        # End Node
        end = QFrame()
        end.setFixedSize(120, 34)
        end.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 4px; color: {C['text_d']};")
        el = QVBoxLayout(end)
        el.setContentsMargins(0, 0, 0, 0)
        l = QLabel("END")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.setStyleSheet("font-weight: bold; border: none;")
        el.addWidget(l)
        self.main_layout.addWidget(end, alignment=Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw dot grid
        painter.setPen(QColor("#1e2440"))
        grid_size = 20
        for x in range(0, self.width(), grid_size):
            for y in range(0, self.height(), grid_size):
                painter.drawPoint(x, y)
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(C['border']), 2)
        painter.setPen(pen)
        # Real connections would be calculated from node positions
        # For prototype, we'll just show the grid and nodes


class CanvasToolbar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(f"background: {C['bg_sidebar']}; border-bottom: 1px solid {C['border']};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        
        # Node quick add
        for icon, color in [("⊞", C['green']), ("◆", C['amber']), ("↺", C['cyan']), ("⟦⟧", C['purple_l']), ("⚙", C['text'])]:
            b = QPushButton(icon)
            b.setFixedSize(24, 24)
            b.setStyleSheet(f"color: {color}; font-weight: bold; border: 1px solid {color}44; border-radius: 3px;")
            layout.addWidget(b)
            
        layout.addSpacing(10)
        line = QFrame()
        line.setFixedWidth(1)
        line.setStyleSheet(f"background: {C['border']}; margin: 8px 0;")
        layout.addWidget(line)
        layout.addSpacing(10)
        
        # Undo/Redo/Zoom
        for text in ["↩", "↪", "|", "🔍-", "100%", "🔍+", "|", "⟳"]:
            if text == "|":
                line = QFrame()
                line.setFixedWidth(1)
                line.setStyleSheet(f"background: {C['border']}; margin: 8px 0;")
                layout.addWidget(line)
            else:
                b = QPushButton(text)
                b.setStyleSheet(f"color: {C['text']}; border: none; background: transparent;")
                layout.addWidget(b)
        
        layout.addStretch()


class MacroBuilderPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.header = MacroBuilderHeader()
        main_layout.addWidget(self.header)
        
        # 3-Column Layout
        cols = QSplitter(Qt.Orientation.Horizontal)
        cols.setHandleWidth(1)
        cols.setStyleSheet(f"QSplitter::handle {{ background: {C['border']}; }}")
        
        self.left_panel = LeftPanel()
        cols.addWidget(self.left_panel)
        
        # Center: Toolbar + Canvas
        center_widget = QWidget()
        cv_layout = QVBoxLayout(center_widget)
        cv_layout.setContentsMargins(0, 0, 0, 0)
        cv_layout.setSpacing(0)
        
        self.toolbar = CanvasToolbar()
        cv_layout.addWidget(self.toolbar)
        
        self.canvas = QScrollArea()
        self.canvas.setWidgetResizable(True)
        self.canvas.setFrameShape(QFrame.Shape.NoFrame)
        self.canvas_widget = CanvasArea()
        self.canvas.setWidget(self.canvas_widget)
        cv_layout.addWidget(self.canvas)
        
        cols.addWidget(center_widget)
        
        self.right_panel = QWidget()
        self.right_panel.setFixedWidth(260)
        self.right_panel.setStyleSheet(f"background: {C['bg_sidebar']}; border-left: 1px solid {C['border']};")
        r_layout = QVBoxLayout(self.right_panel)
        r_layout.setContentsMargins(15, 20, 15, 20)
        r_layout.setSpacing(20)
        
        r_layout.addWidget(self.header._section_header("PROPERTIES"))
        nothing_lbl = QLabel("Click any node in the pipeline\nto configure its properties.")
        nothing_lbl.setWordWrap(True)
        nothing_lbl.setStyleSheet(f"color: {C['text_d']}; font-style: italic; line-height: 1.5;")
        r_layout.addWidget(nothing_lbl)
        
        r_layout.addStretch()
        
        r_layout.addWidget(self.header._section_header("PIPELINE SUMMARY"))
        stats = QLabel("Steps: 4\nTrained: 2\nUntrained: 2")
        stats.setStyleSheet(f"color: {C['text']}; line-height: 1.8;")
        r_layout.addWidget(stats)
        
        export_btn = QPushButton("Export Standalone Agent")
        export_btn.setStyleSheet(f"background: {C['bg_card']}; color: {C['purple_l']}; border: 1px solid {C['purple']}; padding: 10px; border-radius: 4px; font-weight: bold;")
        r_layout.addWidget(export_btn)
        
        cols.addWidget(self.right_panel)
        
        cols.setStretchFactor(1, 1)
        main_layout.addWidget(cols, 1)
        
        # Collapsible Bottom Panel
        self.bottom_panel = QFrame()
        self.bottom_panel.setFixedHeight(180) # Expanded for now to show content
        self.bottom_panel.setStyleSheet(f"background: {C['bg_panel']}; border-top: 2px solid {C['border']};")
        bl = QVBoxLayout(self.bottom_panel)
        
        head = QLabel("▾ MACRO SETTINGS")
        head.setStyleSheet(f"color: {C['white']}; font-weight: bold; margin-bottom: 10px;")
        bl.addWidget(head)
        
        settings_grid = QGridLayout()
        settings_grid.addWidget(QLabel("Global on-step-fail:"), 0, 0)
        settings_grid.addWidget(QComboBox(), 0, 1)
        settings_grid.addWidget(QLabel("Max total time:"), 1, 0)
        settings_grid.addWidget(QLineEdit("120"), 1, 1)
        bl.addLayout(settings_grid)
        
        bl.addStretch()
        main_layout.addWidget(self.bottom_panel)
