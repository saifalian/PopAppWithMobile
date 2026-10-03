import threading
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QLineEdit, QScrollArea, 
                             QStackedWidget, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from app.theme import C

logger = logging.getLogger(__name__)

class ConnectPhonePage(QWidget):
    """Guided wizard for linking Android devices via USB or Wireless Debugging."""
    pair_finished = pyqtSignal(bool)
    connect_finished = pyqtSignal(bool)
    
    def __init__(self, mobile_mgr, parent=None):
        super().__init__(parent)
        self.mobile_mgr = mobile_mgr
        self.init_ui()
        
        # Connect signals
        self.pair_finished.connect(self._on_pair_done)
        self.connect_finished.connect(self._on_connect_done)
        
        # 1-second polling for device status
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._poll_status)
        self.status_timer.start(1000)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        # ── HEADER ──
        header = QWidget()
        hl = QVBoxLayout(header); hl.setContentsMargins(0, 0, 0, 0)
        title = QLabel("🔌 Device Connection Wizard")
        title.setStyleSheet(f"color: {C['white']}; font-size: 26px; font-weight: bold;")
        desc = QLabel("Step-by-step guide to link your Android device for smooth mirroring.")
        desc.setStyleSheet(f"color: {C['text_d']}; font-size: 14px;")
        hl.addWidget(title); hl.addWidget(desc)
        main_layout.addWidget(header)

        # ── STATUS BANNER ──
        self.banner = QFrame()
        self.banner.setFixedHeight(80)
        self.banner.setObjectName("status_banner")
        self.banner.setStyleSheet(f"QFrame#status_banner {{ background: {C['bg_darkest']}; border-left: 5px solid {C['border']}; border-radius: 6px; }}")
        bl = QHBoxLayout(self.banner); bl.setContentsMargins(20, 0, 20, 0)
        
        self.banner_icon = QLabel("📡")
        self.banner_icon.setStyleSheet("font-size: 22px; min-width: 40px;")
        self.banner_lbl = QLabel("No device connected.")
        self.banner_lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 15px; font-weight: bold;")
        bl.addWidget(self.banner_icon)
        bl.addWidget(self.banner_lbl, 1)
        
        self.disconn_btn = QPushButton("DISCONNECT")
        self.disconn_btn.setFixedSize(120, 32)
        self.disconn_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.disconn_btn.setStyleSheet(f"background: {C['red']}22; color: {C['red']}; border: 1px solid {C['red']}; border-radius: 4px; font-weight: bold;")
        self.disconn_btn.clicked.connect(self.mobile_mgr.disconnect)
        self.disconn_btn.hide()
        bl.addWidget(self.disconn_btn)
        main_layout.addWidget(self.banner)

        # ── PAGE STACK ──
        self.stack = QStackedWidget()
        
        # PAGE 0: CHOOSER (REDESIGNED)
        self.chooser_page = QWidget()
        ch_layout = QVBoxLayout(self.chooser_page); ch_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Container for side-by-side buttons
        btn_box = QHBoxLayout(); btn_box.setSpacing(30); btn_box.setContentsMargins(0, 50, 0, 50)
        
        def create_choice_btn(title, icon, sub, color, callback, name):
            card = QFrame()
            card.setObjectName(name)
            card.setMinimumSize(350, 400) # Increased size back to "big"
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Base Style + Hover Glow
            style = f"""
                QFrame#{name} {{
                    background: {C['bg_panel']};
                    border: 2px solid {C['border']};
                    border-radius: 24px;
                }}
                QFrame#{name}:hover {{
                    border-color: {C['purple']};
                    background: {C['purple']}15;
                }}
                QFrame#{name}:pressed {{
                    background: {C['purple']}25;
                    border-color: {C['purple']};
                }}
            """
            card.setStyleSheet(style)
            
            cl = QVBoxLayout(card); cl.setContentsMargins(40, 50, 40, 50); cl.setSpacing(12); cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Use WA_TransparentForMouseEvents so the labels don't "steal" the click/hover from the card
            i = QLabel(icon); i.setStyleSheet("font-size: 72px; background: transparent; margin-bottom: 10px; border:none;")
            i.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            t = QLabel(title); t.setStyleSheet(f"color: {C['white']}; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border:none;")
            t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            s = QLabel(sub); s.setStyleSheet(f"color: {C['text_d']}; font-size: 13px; background: transparent; text-transform: uppercase; letter-spacing: 1px; border:none;")
            s.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            cl.addWidget(i); cl.addWidget(t); cl.addWidget(s)
            card.mousePressEvent = lambda e: callback()
            return card

        self.usb_btn = create_choice_btn("USB CABLE", "🔌", "Fastest / Low Latency", C['purple'], self._show_usb_wizard, "usb_choice")
        self.wifi_btn = create_choice_btn("WIRELESS", "📡", "No Cables / Convenient", C['purple'], self._show_wifi_wizard, "wifi_choice")
        
        btn_box.addWidget(self.usb_btn)
        btn_box.addWidget(self.wifi_btn)
        
        # Center the choice box vertically in the page
        ch_layout.addStretch(1)
        ch_layout.addLayout(btn_box)
        ch_layout.addStretch(1)
        
        self.stack.addWidget(self.chooser_page)

        # PAGE 1: USB WIZARD
        self.usb_wizard = QWidget()
        uwl = QVBoxLayout(self.usb_wizard); uwl.setSpacing(15)
        uwl.addWidget(self._wizard_header("USB Connection Setup", self._show_chooser))
        
        steps = [
            "1. Connect your phone via USB cable.",
            "2. Settings > About Phone > Tap 'Build Number' 7 times.",
            "3. Developer Options > Enable 'USB Debugging'.",
            "4. Accept the 'Allow USB Debugging?' popup on your phone."
        ]
        for s in steps:
            l = QLabel(s); l.setStyleSheet(f"color: {C['text']}; font-size: 14px;"); uwl.addWidget(l)
        
        uwl.addSpacing(20)
        uwl.addWidget(self._section_title("Detected USB Devices"))
        self.usb_list_layout = QVBoxLayout()
        uwl.addLayout(self.usb_list_layout)
        self.usb_empty_lbl = QLabel("Searching for devices...")
        self.usb_empty_lbl.setStyleSheet(f"color: {C['text_d']}; font-style: italic;")
        uwl.addWidget(self.usb_empty_lbl)
        uwl.addStretch()
        self.stack.addWidget(self.usb_wizard)

        # PAGE 2: WIFI WIZARD
        self.wifi_wizard = QWidget()
        wwl = QVBoxLayout(self.wifi_wizard); wwl.setSpacing(15)
        wwl.addWidget(self._wizard_header("Wireless Connection Setup", self._show_chooser))
        
        for text in ["1. Connect Phone and PC to the SAME Wi-Fi.", "2. Enable 'Wireless Debugging' in Developer Options.", "3. Tap 'Pair device with pairing code'."]:
            wwl.addWidget(QLabel(text))
        
        form_frame = QFrame()
        form_frame.setStyleSheet(f"background: {C['bg_panel']}; border: 1px solid {C['border']}; border-radius: 8px;")
        fl = QGridLayout(form_frame); fl.setContentsMargins(20, 20, 20, 20); fl.setSpacing(15)
        
        self.ip_input = QLineEdit(); self.ip_input.setPlaceholderText("IP Address"); self.ip_input.setStyleSheet(self._input_style())
        self.pair_port = QLineEdit(); self.pair_port.setPlaceholderText("Pair Port"); self.pair_port.setStyleSheet(self._input_style())
        self.code_input = QLineEdit(); self.code_input.setPlaceholderText("Pairing Code"); self.code_input.setStyleSheet(self._input_style())
        self.conn_port = QLineEdit(); self.conn_port.setPlaceholderText("Connect Port"); self.conn_port.setStyleSheet(self._input_style())
        
        fl.addWidget(QLabel("IP:"), 0, 0); fl.addWidget(self.ip_input, 0, 1)
        fl.addWidget(QLabel("Pair Port:"), 1, 0); fl.addWidget(self.pair_port, 1, 1)
        fl.addWidget(QLabel("Code:"), 2, 0); fl.addWidget(self.code_input, 2, 1)
        fl.addWidget(QLabel("Connect Port:"), 3, 0); fl.addWidget(self.conn_port, 3, 1)
        wwl.addWidget(form_frame)
        
        row = QHBoxLayout()
        self.pair_btn = QPushButton("🔗 PAIR"); self.pair_btn.setStyleSheet(self._primary_btn_style(C['purple'])); self.pair_btn.clicked.connect(self._on_pair_clicked)
        self.connect_btn = QPushButton("🔌 CONNECT"); self.connect_btn.setStyleSheet(self._primary_btn_style(C['cyan'])); self.connect_btn.clicked.connect(self._on_connect_clicked)
        row.addWidget(self.pair_btn); row.addWidget(self.connect_btn)
        wwl.addLayout(row)
        wwl.addStretch()
        self.stack.addWidget(self.wifi_wizard)

        main_layout.addWidget(self.stack, 1)

    # ── HELPER UI ──
    def _wizard_header(self, title, on_back):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0, 0, 0, 10)
        btn = QPushButton("← Back"); btn.setStyleSheet(f"color: {C['text']}; border: none; font-weight: bold; background: transparent;")
        btn.clicked.connect(on_back); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl = QLabel(title); lbl.setStyleSheet(f"color: {C['white']}; font-size: 18px; font-weight: bold;")
        l.addWidget(btn); l.addWidget(lbl); l.addStretch(); return w

    def _primary_btn_style(self, color):
        return f"QPushButton {{ background: {color}22; color: {color}; border: 1px solid {color}; border-radius: 6px; font-weight: bold; height: 40px; }} QPushButton:hover {{ background: {color}33; }}"

    def _input_style(self):
        return f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 10px; color: {C['white']};"

    def _section_title(self, text):
        lbl = QLabel(text.upper()); lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; font-weight: bold; letter-spacing: 1px;"); return lbl

    def _show_chooser(self): self.stack.setCurrentIndex(0)
    def _show_usb_wizard(self): self.stack.setCurrentIndex(1)
    def _show_wifi_wizard(self): self.stack.setCurrentIndex(2)

    # ── LOGIC ──
    def _poll_status(self):
        is_conn = self.mobile_mgr.is_connected
        device = self.mobile_mgr.connected_device_ip
        # Fixed: Use connection_type instead of the non-existent is_wireless
        is_wireless = self.mobile_mgr.connection_type == "Wireless"
        
        # 1. Update Banner
        if is_conn:
            self.banner.setStyleSheet(f"QFrame#status_banner {{ background: {C['bg_darkest']}; border-left: 5px solid {C['green']}; border-radius: 6px; }}")
            self.banner_icon.setText("🟢"); self.banner_lbl.setText(f"Connected to <b>{device}</b>")
            self.disconn_btn.show()
        else:
            self.banner.setStyleSheet(f"QFrame#status_banner {{ background: {C['bg_darkest']}; border-left: 5px solid {C['orange']}; border-radius: 6px; }}")
            self.banner_icon.setText("📡"); self.banner_lbl.setText("No device connected.")
            self.disconn_btn.hide()
            
        # 2. Update Choice Button Glows (Unified Purple Theme)
        self._update_btn_style(self.usb_btn, C['purple'], is_conn and not is_wireless, "usb_choice")
        self._update_btn_style(self.wifi_btn, C['purple'], is_conn and is_wireless, "wifi_choice")
        
        self._update_usb_list(is_conn, device)

    def _update_btn_style(self, btn, theme_color, is_active, name):
        # Determine the glow color based on the button's theme (Always Purple for unify)
        border = theme_color if is_active else C['border']
        bg = f"{theme_color}11" if is_active else C['bg_panel']
            
        style = f"""
            QFrame#{name} {{
                background: {bg};
                border: 2px solid {border};
                border-radius: 24px;
            }}
            QFrame#{name}:hover {{
                border-color: {theme_color};
                background: {theme_color}22;
            }}
            QFrame#{name}:pressed {{
                background: {theme_color}33;
                border-color: {theme_color};
            }}
        """
        btn.setStyleSheet(style)

    def _update_usb_list(self, is_conn, connected_serial):
        devices = self.mobile_mgr.discover_devices()
        usb_devices = [d for d in devices if not d["is_wireless"] and d["serial"] != connected_serial]
        
        while self.usb_list_layout.count():
            item = self.usb_list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not usb_devices:
            self.usb_empty_lbl.show()
        else:
            self.usb_empty_lbl.hide()
            for d in usb_devices:
                row = QWidget(); rl = QHBoxLayout(row); rl.setContentsMargins(0, 0, 0, 0)
                info = QLabel(f"📱 <b>{d['model']}</b> <font color='#666'>[{d['serial']}]</font>")
                info.setStyleSheet(f"color: {C['white']}; font-size: 13px;"); rl.addWidget(info, 1)
                
                btn = QPushButton("CONNECT"); btn.setFixedSize(90, 26)
                if d['state'] == 'device':
                    btn.setStyleSheet(self._primary_btn_style(C['cyan'])); btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.clicked.connect(lambda c, s=d['serial']: self._on_usb_connect_clicked(s))
                else:
                    btn.setStyleSheet("background: #333; color: #666; border-radius: 4px; font-size: 10px;"); btn.setEnabled(False)
                rl.addWidget(btn); self.usb_list_layout.addWidget(row)

    def _on_pair_clicked(self):
        ip = self.ip_input.text().strip(); port = self.pair_port.text().strip(); code = self.code_input.text().strip()
        if not ip or not port or not code: return
        self.pair_btn.setText("Pairing..."); self.pair_btn.setEnabled(False)
        threading.Thread(target=lambda: self.pair_finished.emit(self.mobile_mgr.pair_device(f"{ip}:{port}", code)), daemon=True).start()

    def _on_pair_done(self, success):
        self.pair_btn.setText("Success!" if success else "Failed"); self.pair_btn.setEnabled(True)

    def _on_connect_clicked(self):
        ip = self.ip_input.text().strip(); port = self.conn_port.text().strip()
        if not ip or not port: return
        self.connect_btn.setText("Connecting..."); self.connect_btn.setEnabled(False)
        threading.Thread(target=lambda: self.connect_finished.emit(self.mobile_mgr.connect_wireless(ip, int(port) if port.isdigit() else 5555)), daemon=True).start()

    def _on_usb_connect_clicked(self, serial):
        threading.Thread(target=lambda: self.connect_finished.emit(self.mobile_mgr.connect_usb(serial)), daemon=True).start()

    def _on_connect_done(self, success):
        self.connect_btn.setEnabled(True); self.connect_btn.setText("Connected!" if success else "Connect Now")
