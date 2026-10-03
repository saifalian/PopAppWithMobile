"""
Live log terminal widget matching the screenshot.
Dark background, monospace font, auto-scroll.
"""
from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtGui import QFont, QColor, QTextCursor
from PyQt6.QtCore import Qt
from app.theme import C, FONT_MONO


class TerminalWidget(QWidget):
    """Live scrolling log terminal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._max_lines = 500
        self._auto_scroll = True
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        from PyQt6.QtWidgets import QLabel, QButtonGroup
        title = QLabel("TERMINAL — LIVE LOGS")
        title.setStyleSheet(f"color: {C['text_b']}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        header.addWidget(title)
        header.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet(f"color: {C['text']}; border: none; background: transparent;")
        self.clear_btn.clicked.connect(self.clear)
        header.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.setStyleSheet(f"color: {C['text']}; border: none; background: transparent;")
        header.addWidget(self.export_btn)
        
        self.pause_scroll_btn = QPushButton("⏸ Pause Scroll")
        self.pause_scroll_btn.setCheckable(True)
        self.pause_scroll_btn.setStyleSheet(f"""
            QPushButton {{ color: {C['text']}; border: none; background: transparent; }}
            QPushButton:checked {{ color: {C['amber']}; }}
        """)
        self.pause_scroll_btn.toggled.connect(self._toggle_scroll)
        header.addWidget(self.pause_scroll_btn)
        
        layout.addLayout(header)

        # Tab Bar for filtering
        self.tab_container = QWidget()
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(10)
        self.tabs = ["ALL", "click_clusters", "read_popup", "assess_chart"]
        
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        
        for t in self.tabs:
            b = QPushButton(t)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setCheckable(True)
            if t == "ALL": b.setChecked(True)
            b.setStyleSheet(f"""
                QPushButton {{ 
                    background: transparent; 
                    color: {C['text']}; 
                    border: none; 
                    font-size: 11px; 
                    font-weight: bold; 
                    padding: 8px 14px;
                    border-radius: 6px;
                }}
                QPushButton:hover {{ background: {C['bg_input']}; color: {C['white']}; }}
                QPushButton:checked {{ 
                    background: {C['bg_input']};
                    color: {C['white']}; 
                    border-bottom: 3px solid {C['purple']}; 
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                }}
            """)
            self.tab_group.addButton(b)
            tab_layout.addWidget(b)
        tab_layout.addStretch()
        layout.addWidget(self.tab_container)

        # Text area
        self.text = QTextEdit()
        self.text.setObjectName("terminal")
        self.text.setReadOnly(True)
        self.text.setFont(QFont(FONT_MONO, 11))
        self.text.setMinimumHeight(100)
        self.text.setPlaceholderText("Unsupervised training logs will appear here ...")
        layout.addWidget(self.text)

    def _toggle_scroll(self, paused: bool):
        self._auto_scroll = not paused

    def append(self, line: str, level: str = "info"):
        """Add log line with color coding."""
        color_map = {
            "info":    C["text"],
            "success": C["status_confident"],
            "warning": C["amber"],
            "error":   C["status_error"],
            "best":    C["purple_l"],
        }
        # Auto-detect level from content
        if any(x in line.lower() for x in ["✓", "success", "new best", "saved", "complete"]):
            level = "success"
        elif any(x in line.lower() for x in ["error", "failed", "✗", "crashed"]):
            level = "error"
        elif any(x in line.lower() for x in ["warning", "⚠", "drift", "retry", "skip"]):
            level = "warning"
        elif any(x in line.lower() for x in ["score", "best", "pts"]):
            level = "best"

        color = color_map.get(level, C["text"])
        html  = f'<span style="color:{color}; font-family:Consolas;">{line}</span>'
        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text.setTextCursor(cursor)
        self.text.insertHtml(html + "<br>")

        # Trim old lines
        doc = self.text.document()
        if doc.blockCount() > self._max_lines:
            cursor = self.text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

        if self._auto_scroll:
            self.text.verticalScrollBar().setValue(
                self.text.verticalScrollBar().maximum()
            )

    def clear(self):
        self.text.clear()
