import time
import logging
import subprocess
import struct
import socket
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage
from backend.core.mobile_manager import MobileManager

logger = logging.getLogger(__name__)

class MirrorWorker(QThread):
    """
    Background worker that connects to the Mobile App's streaming socket
    via ADB forwarding and emits frames to the UI.
    """
    frame_captured = pyqtSignal(QImage)
    ui_diff_detected = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(self, mobile_mgr: MobileManager, parent=None):
        super().__init__(parent)
        self.mobile_mgr = mobile_mgr
        self.running = False
        self.paused = False
        self._sock = None
        self._prev_data = None
        self.target_serial = None
        self.target_port = 1234
        self._wake_up_count = 0

    def run(self):
        self.running = True
        logger.info("Mobile App Mirror Worker started.")
        
        while self.running:
            if self.paused or not self.mobile_mgr.is_connected or not self.target_serial:
                self._cleanup_sock()
                time.sleep(0.5)
                continue

            try:
                if not self._sock:
                    # 1. Setup ADB Forwarding (Local: target_port -> Remote: 1234)
                    if not self.mobile_mgr.setup_forwarding(self.target_port, 1234, self.target_serial):
                        time.sleep(1.0)
                        continue
                    
                    # 2. Connect to local port (forwarded by ADB)
                    self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) # Reduce latency
                    self._sock.settimeout(3.0)
                    self._sock.connect(("127.0.0.1", self.target_port))
                    logger.info(f"Connected to Mobile Stream on port {self.target_port}.")
                    self._wake_up_count = 0 # Reset wake-up counter on success

                # 3. Read Frame Length (4 bytes)
                len_bytes = self._read_exactly(4)
                if not len_bytes:
                    raise Exception("Socket closed by remote (empty head)")
                
                frame_len = struct.unpack(">I", len_bytes)[0]
                
                # 4. Read JPEG Data
                jpeg_data = self._read_exactly(frame_len)
                if not jpeg_data:
                    raise Exception("Socket closed by remote (empty data)")
                
                # 5. Emit Image & Calc Diff
                image = QImage.fromData(jpeg_data)
                if not image.isNull():
                    self.frame_captured.emit(image)
                    
                    if self._prev_data:
                        if jpeg_data == self._prev_data:
                            self.ui_diff_detected.emit(0.0)
                        else:
                            self.ui_diff_detected.emit(1.0)
                    self._prev_data = jpeg_data
                
            except Exception as e:
                # If we get 'empty head' or similar, try to 'wake up' the service on the phone
                msg = str(e)
                if "empty head" in msg or "Connection refused" in msg or "Connection reset" in msg:
                    self._wake_up_count += 1
                    # Less aggressive wake-up: every 5 attempts (every 20s with 4s wait)
                    if self._wake_up_count % 5 == 1:
                        self.mobile_mgr.start_streaming_service(self.target_serial)
                        
                logger.warning(f"Mirror error ({self.target_serial}): {e}. Retrying in 4s...")
                self._cleanup_sock()
                time.sleep(4.0) 

        self._cleanup_sock()
        logger.info("Mobile Mirror Worker stopped.")

    def send_status(self, message: str):
        """Send a status string back to the mobile app's log monitor."""
        if self._sock:
            try:
                # Append newline so the phone's readLine() picks it up
                self._sock.sendall((message + "\n").encode("utf-8"))
            except Exception as e:
                logger.error(f"Failed to send status to mobile: {e}")

    def _cleanup_sock(self):
        if self._sock:
            try: self._sock.close()
            except: pass
            self._sock = None

    def _read_exactly(self, n):
        """Helper to read exactly n bytes from the socket."""
        data = bytearray()
        while len(data) < n:
            try:
                chunk = self._sock.recv(n - len(data))
                if not chunk:
                    return None
                data.extend(chunk)
            except socket.timeout:
                if not self.running: return None
                continue
        return data

    def stop(self):
        self.running = False
        self.wait()
