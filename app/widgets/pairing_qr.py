from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, 
                             QHBoxLayout, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
from app.theme import C

class ManualConnectionOverlay(QWidget):
    """A thread-safe, manual-only data entry popup with real-time feedback."""
    closed = pyqtSignal()
    manual_pair_requested = pyqtSignal(str, str, str) # ip, port, code
    connect_requested = pyqtSignal(str, str) # ip, port
    
    # Internal signal for thread-safe UI updates
    _status_signal = pyqtSignal(str, bool, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.hide()
        self.setStyleSheet(f"background-color: rgba(11, 14, 26, 248); color: {C['white']};")
        self._status_signal.connect(self._handle_status_update)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.frame = QFrame()
        self.frame.setFixedWidth(380)
        self.frame.setStyleSheet("background: #111520; border-radius: 12px; border: 1px solid #1e2233;")
        
        f_layout = QVBoxLayout(self.frame)
        f_layout.setContentsMargins(25, 25, 25, 20)
        f_layout.setSpacing(12)
        f_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        
        # Header
        title = QLabel("DEVICE SETUP")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {C['cyan']}; letter-spacing: 2px; margin-bottom: 5px;")
        f_layout.addWidget(title)

        # 1. IP
        f_layout.addWidget(self._section_label("1. Phone IP Address"))
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("IP (e.g. 192.168.1.5)")
        self.ip_input.setStyleSheet(f"background: {C['bg_darkest']}; color: white; border: 1px solid {C['border']}; border-radius: 4px; padding: 10px; font-size: 13px;")
        f_layout.addWidget(self.ip_input)
        
        line1 = QFrame(); line1.setFrameShape(QFrame.Shape.HLine); line1.setStyleSheet(f"background: {C['border']}; margin: 5px 0;")
        f_layout.addWidget(line1)

        # 2. PAIRING
        f_layout.addWidget(self._section_label("2. Step One: Pairing"))
        row_p = QHBoxLayout()
        self.pair_port = QLineEdit(); self.pair_port.setPlaceholderText("Pair Port")
        self.pair_port.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 8px; font-size: 12px;")
        row_p.addWidget(self.pair_port)
        
        self.pair_code = QLineEdit(); self.pair_code.setPlaceholderText("Code")
        self.pair_code.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 8px; font-size: 12px;")
        row_p.addWidget(self.pair_code)
        f_layout.addLayout(row_p)
        
        self.btn_pair = QPushButton("⚡ PAIR DEVICE")
        self.btn_pair.setFixedHeight(34); self.btn_pair.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pair.setStyleSheet(f"QPushButton {{ background: {C['purple']}; color: white; border-radius: 4px; font-weight: bold; font-size: 11px; }}")
        self.btn_pair.clicked.connect(self._on_pair_click)
        f_layout.addWidget(self.btn_pair)
        
        line2 = QFrame(); line2.setFrameShape(QFrame.Shape.HLine); line2.setStyleSheet(f"background: {C['border']}; margin: 5px 0;")
        f_layout.addWidget(line2)

        # 3. CONNECT
        f_layout.addWidget(self._section_label("3. Step Two: Connect"))
        lbl_hint = QLabel("(Port found on main Wireless Debugging screen)")
        lbl_hint.setStyleSheet(f"color: {C['text_d']}; font-size: 8px; margin-bottom: 2px;")
        f_layout.addWidget(lbl_hint)
        
        row_c = QHBoxLayout()
        self.conn_port = QLineEdit("5555"); self.conn_port.setPlaceholderText("Main Port")
        self.conn_port.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 10px; font-size: 14px; font-weight: bold;")
        row_c.addWidget(self.conn_port, 1)
        
        self.btn_connect = QPushButton("🟢 CONNECT")
        self.btn_connect.setFixedHeight(40); self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.setStyleSheet(f"QPushButton {{ background: {C['bg_sidebar']}; color: {C['cyan']}; border: 1px solid {C['cyan']}; border-radius: 4px; font-weight: bold; font-size: 12px; }}")
        self.btn_connect.clicked.connect(self._on_connect_click)
        row_c.addWidget(self.btn_connect, 2)
        f_layout.addLayout(row_c)
        
        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("font-size: 10px; font-weight: bold; margin-top: 5px;")
        f_layout.addWidget(self.status_lbl)

        btn_close = QPushButton("Cancel / Close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; border: none; margin-top: 5px;")
        btn_close.clicked.connect(self._on_close)
        f_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.frame)

    def _section_label(self, text):
        lbl = QLabel(text.upper()); lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 9px; font-weight: bold;")
        return lbl

    def show_status(self, msg, success=True, hide_after=True):
        """Thread-safe status update trigger."""
        self._status_signal.emit(msg, success, hide_after)

    @pyqtSlot(str, bool, bool)
    def _handle_status_update(self, msg, success, hide_after):
        """Internal handler running ALWAYS on Main GUI thread."""
        color = C['green'] if success else "#ef4444"
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold; margin-top: 5px;")
        if success and hide_after:
            # Safe to start timer here as we are in the GUI thread
            QTimer.singleShot(1500, self.hide)

    def _on_pair_click(self):
        self.status_lbl.setText("Pairing..."); self.status_lbl.setStyleSheet(f"color: {C['white']};")
        ip = self.ip_input.text().strip(); port = self.pair_port.text().strip(); code = self.pair_code.text().strip()
        if ip and port and code: self.manual_pair_requested.emit(ip, port, code)

    def _on_connect_click(self):
        self.status_lbl.setText("Connecting..."); self.status_lbl.setStyleSheet(f"color: {C['white']};")
        ip = self.ip_input.text().strip(); port = self.conn_port.text().strip()
        if ip and port: self.connect_requested.emit(ip, port)

    def show_popup(self, default_ip=""):
        self.status_lbl.setText("")
        self.ip_input.setText(default_ip)
        self.pair_port.clear()
        self.pair_code.clear()
        if self.parentWidget(): self.setGeometry(0, 0, self.parentWidget().width(), self.parentWidget().height())
        self.show(); self.raise_()

    def _on_close(self):
        self.hide(); self.closed.emit()
