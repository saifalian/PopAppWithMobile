import time
import logging
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

class DeviceMonitorWorker(QThread):
    """
    Background worker that periodically fetches device information (battery, apps, 
    temp, etc.) via ADB to avoid blocking the main UI thread.
    """
    info_received = pyqtSignal(dict)
    
    def __init__(self, mobile_mgr, serial: str, parent=None):
        super().__init__(parent)
        self.mobile_mgr = mobile_mgr
        self.serial = serial
        self.running = False
        self._live_interval = 6.0 # Foreground App check: 6s
        self._perf_interval = 30.0 # Performance poll (CPU/RAM): 30s
        self._full_interval = 120.0 # Full stats poll (Battery/Temp): 120s (2m)
        self._last_full_poll = 0
        self._last_perf_poll = 0

    def run(self):
        self.running = True
        logger.info(f"DeviceMonitorWorker started for {self.serial}")
        
        # 0. Initial ONCE: Fetch static info (Model, Resolution)
        try:
            static_info = self.mobile_mgr.get_device_static_info(self.serial)
            if static_info:
                self.info_received.emit(static_info)
        except Exception as e:
            logger.error(f"Error fetching static info in Worker: {e}")

        while self.running:
            if not self.serial or not self.mobile_mgr.is_connected:
                time.sleep(1.0)
                continue
                
            try:
                # 1. LIVE: Fetch foreground app activity
                app_name = self.mobile_mgr.get_foreground_app(self.serial)
                
                # Data dictionary for this pulse
                pulse_data = {"app": app_name, "partial": True}
                now = time.time()

                # 2. PERFORMANCE: Fetch CPU/RAM every 30s
                if now - self._last_perf_poll > self._perf_interval:
                    perf = self.mobile_mgr.get_performance_stats(self.serial)
                    pulse_data.update(perf)
                    self._last_perf_poll = now

                # 3. PERIODIC: Fetch dynamic info (battery, temp, etc.) every 60s
                if now - self._last_full_poll > self._full_interval:
                    dynamic = self.mobile_mgr.get_device_dynamic_info(self.serial)
                    pulse_data.update(dynamic)
                    pulse_data["partial"] = False # Mark as full pulse
                    self._last_full_poll = now
                
                self.info_received.emit(pulse_data)
                    
            except Exception as e:
                logger.error(f"Error in DeviceMonitorWorker for {self.serial}: {e}")
            
            # Wait for next live interval
            for _ in range(int(self._live_interval * 10)):
                if not self.running: break
                time.sleep(0.1)
                
        logger.info(f"DeviceMonitorWorker stopped for {self.serial}")

    def stop(self):
        self.running = False
        self.wait()
