import logging
import time
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional

logger = logging.getLogger(__name__)

class MobileMonitor(QThread):
    """
    Background monitor for any connected Android device.
    Tracks temperature, CPU, and app status for safety (Thermal Guard).
    """
    stats_updated = pyqtSignal(dict)
    thermal_warning = pyqtSignal(float) # Current temp
    critical_thermal = pyqtSignal(float) # Temp that triggered pause
    
    def __init__(self, mobile_mgr, parent=None):
        super().__init__(parent)
        self.mobile_mgr = mobile_mgr
        self.running = True
        self.pause_threshold = 46.0 # Default safety threshold for Snapdragon 8 Gen 3/generic
        self.resume_threshold = 40.0
        self.check_interval = 3.0
        
    def run(self):
        logger.info("Mobile Performance Monitor started.")
        while self.running:
            if self.mobile_mgr.is_connected:
                serial = self.mobile_mgr.connected_device_ip
                if serial:
                    stats = self.mobile_mgr.get_device_info(serial)
                    self.stats_updated.emit(stats)
                    
                    # Thermal Guard Logic
                    try:
                        temp_str = stats.get("temp", "0.0°C").replace("°C", "")
                        if temp_str != "N/C":
                            temp = float(temp_str)
                            if temp >= self.pause_threshold:
                                logger.warning(f"CRITICAL THERMAL DETECTED: {temp}°C")
                                self.critical_thermal.emit(temp)
                            elif temp >= self.pause_threshold - 5:
                                self.thermal_warning.emit(temp)
                    except Exception as e:
                        logger.error(f"Thermal parsing error: {e}")
            
            time.sleep(self.check_interval)

    def stop(self):
        self.running = False
        self.wait()
