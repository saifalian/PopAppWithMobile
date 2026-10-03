import logging
import subprocess
import time
import socket
import random
from typing import Optional, Dict
from backend.core.adb_broadcaster import ADBServiceBroadcaster

logger = logging.getLogger(__name__)

class MobileManager:
    """Manages ADB connectivity and mobile device interaction."""
    
    def __init__(self, adb_path: str = r"D:\tools\platform-tools\adb.exe"):
        self.adb_path = adb_path
        self.connected_device_ip: Optional[str] = None
        self.is_connected: bool = False
        self.connection_type: Optional[str] = None # "USB" or "Wireless"
        self.max_fps: int = 30
        self.high_speed: bool = False
        self.device_owners: Dict[str, str] = {} # Tracks which model is currently "using" each device: {serial: model_name}
        self.adb_broadcaster: Optional[ADBServiceBroadcaster] = None
        self._last_wake_up: Dict[str, float] = {} # {serial: timestamp} to prevent wake-up loops
        
    def discover_devices(self) -> list:
        """Scan for devices connected via USB or already on ADB network."""
        try:
            result = subprocess.run([self.adb_path, "devices", "-l"], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split("\n")[1:]
            devices = []
            for line in lines:
                parts = line.split()
                if len(parts) < 2:
                    continue
                
                serial = parts[0]
                state = parts[1] # 'device', 'unauthorized', 'offline', etc.
                
                # We only want to 'connect' to 'device' state, but we should show others for debugging
                model = "Unknown Device"
                for p in parts:
                    if p.startswith("model:"):
                        model = p.split(":")[1].replace("_", " ")
                        break
                
                devices.append({
                    "serial": serial,
                    "model": model,
                    "state": state, # Added state
                    "is_wireless": ":" in serial
                })
            return devices
        except Exception as e:
            logger.error(f"ADB discovery error: {e}")
            return []

    def start_pairing_broadcast(self, code: str):
        """Start mDNS broadcast so the phone can find the PC for QR pairing."""
        self.stop_pairing_broadcast()
        # ADB pairing port is typically dynamic, but we'll use a standard one for mDNS search
        # Android's system QR pairing usually expects the PC to listen on a port.
        self.adb_broadcaster = ADBServiceBroadcaster(pairing_code=code, port=5555)
        self.adb_broadcaster.start()

    def stop_pairing_broadcast(self):
        """Stop mDNS broadcast."""
        if self.adb_broadcaster:
            self.adb_broadcaster.stop()
            self.adb_broadcaster = None

    def pair_device(self, ip_port: str, pairing_code: str) -> bool:
        """Pair with a device using Android 11+ Pairing Code system."""
        logger.info(f"Attempting ADB pairing with {ip_port} using code {pairing_code}...")
        try:
            cmd = [self.adb_path, "pair", ip_port, pairing_code]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if "successfully paired" in result.stdout.lower():
                logger.info(f"Pairing successful with {ip_port}")
                return True
            else:
                logger.error(f"Pairing failed: {result.stdout} {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"ADB pair error: {e}")
            return False

    def connect_wireless(self, ip: str, port: int = 5555) -> bool:
        """Connect to a device over Wi-Fi (requires Wireless Debugging enabled)."""
        if ":" in ip:
            target = ip
        else:
            target = f"{ip}:{port}"
            
        logger.info(f"Attempting ADB wireless connect to {target} using {self.adb_path}...")
        try:
            cmd = [self.adb_path, "connect", target]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if "connected to" in result.stdout.lower():
                self.connected_device_ip = target
                self.is_connected = True
                self.connection_type = "Wireless"
                logger.info(f"Successfully connected to {target}")
                return True
            else:
                logger.error(f"ADB connect failed: {result.stdout}")
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"ADB connect timed out for {target}")
            return False
        except Exception as e:
            logger.error(f"ADB connect error: {e}")
            return False

    def connect_usb(self, serial: str) -> bool:
        """Verify a USB device is still available and mark as connected."""
        logger.info(f"Verifying USB device {serial}...")
        devices = self.discover_devices()
        for d in devices:
            if d["serial"] == serial:
                self.connected_device_ip = serial
                self.is_connected = True
                self.connection_type = "USB"
                logger.info(f"USB device {serial} ready.")
                return True
        logger.error(f"USB device {serial} not found during connection.")
        return False

    def get_device_static_info(self, serial: str) -> Dict:
        """Fetch info that rarely changes: Brand, Model, Resolution."""
        info = {"model": "Unknown", "resolution": "N/A"}
        if not serial: return info
        try:
            # 1. Get Model & Brand
            cmd = [self.adb_path, "-s", serial, "shell", "getprop", "ro.product.brand; getprop ro.product.model"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            props = r.stdout.strip().split("\n")
            brand = props[0].capitalize() if len(props) > 0 else ""
            model = props[1] if len(props) > 1 else "Android Device"
            info["model"] = f"{brand} {model}"

            # 2. Resolution
            cmd_res = [self.adb_path, "-s", serial, "shell", "wm", "size"]
            r_res = subprocess.run(cmd_res, capture_output=True, text=True, timeout=3)
            if "Physical size:" in r_res.stdout:
                info["resolution"] = r_res.stdout.split(":")[1].strip()
            return info
        except Exception as e:
            logger.error(f"Error getting static info: {e}")
            return info

    def get_device_dynamic_info(self, serial: str) -> Dict:
        """Fetch info that changes: Battery, Temp, Storage, Ping."""
        info = {"battery": "0", "temp": "N/C", "storage": "N/A", "ping": "N/A"}
        if not serial: return info
        try:
            # 1. Battery Stats
            cmd_batt = [self.adb_path, "-s", serial, "shell", "dumpsys", "battery"]
            r_batt = subprocess.run(cmd_batt, capture_output=True, text=True, timeout=3)
            for line in r_batt.stdout.splitlines():
                if "level:" in line.lower():
                    info["battery"] = line.split(":")[1].strip()
                elif "temperature:" in line.lower():
                    t = float(line.split(":")[1].strip()) / 10
                    info["temp"] = f"{t:.1f}°C"
            
            # 2. Storage
            cmd_df = [self.adb_path, "-s", serial, "shell", "df", "/sdcard"]
            r_df = subprocess.run(cmd_df, capture_output=True, text=True, timeout=3)
            df_lines = r_df.stdout.strip().split("\n")
            if len(df_lines) > 1:
                parts = df_lines[1].split()
                for p in reversed(parts):
                    if p.endswith("G") or p.endswith("M"):
                        info["storage"] = f"{p} free"
                        break

            info["ping"] = self.ping_device(serial)
            return info
        except Exception as e:
            logger.error(f"Error getting dynamic info: {e}")
            return info

    def get_performance_stats(self, serial: str) -> Dict:
        """Fetch CPU and RAM usage stats."""
        stats = {"cpu": 0, "ram_used": 0, "ram_total": 0, "ram_percent": 0}
        if not serial: return stats
        try:
            # 1. CPU Usage (from top)
            # -n 1 (one iteration), -b (batch mode)
            cmd_cpu = [self.adb_path, "-s", serial, "shell", "top", "-n", "1", "-b", "-m", "1"]
            r_cpu = subprocess.run(cmd_cpu, capture_output=True, text=True, timeout=4)
            # Look for line like: %cpu 14% ... or similar depending on android version
            # Usually: "User 5%, System 4%, IOW 0%, IRQ 0%"
            for line in r_cpu.stdout.splitlines():
                if "User" in line and "System" in line:
                    # Very rough estimate of total load
                    parts = line.split(",")
                    u = int(parts[0].strip().split(" ")[1].replace("%", ""))
                    s = int(parts[1].strip().split(" ")[1].replace("%", ""))
                    stats["cpu"] = min(100, u + s)
                    break

            # 2. RAM Usage (from meminfo)
            cmd_ram = [self.adb_path, "-s", serial, "shell", "cat", "/proc/meminfo"]
            r_ram = subprocess.run(cmd_ram, capture_output=True, text=True, timeout=3)
            mem_total = 0
            mem_avail = 0
            for line in r_ram.stdout.splitlines():
                if "MemTotal:" in line:
                    mem_total = int(line.split(":")[1].strip().split(" ")[0])
                elif "MemAvailable:" in line:
                    mem_avail = int(line.split(":")[1].strip().split(" ")[0])
            
            if mem_total > 0:
                used = mem_total - mem_avail
                stats["ram_used"] = used / 1024 / 1024 # GB
                stats["ram_total"] = mem_total / 1024 / 1024 # GB
                stats["ram_percent"] = (used / mem_total) * 100
                
            return stats
        except Exception as e:
            logger.error(f"Error fetching performance stats: {e}")
            return stats

    def get_device_info(self, serial: Optional[str]) -> Dict:
        """Legacy method combining static and dynamic info."""
        if not serial: return {}
        static = self.get_device_static_info(serial)
        dynamic = self.get_device_dynamic_info(serial)
        app = self.get_foreground_app(serial)
        return {**static, **dynamic, "app": app}

    def get_foreground_app(self, serial: str) -> str:
        """Fetch the current foreground package reliably using dumpsys window and activity."""
        if not serial: return "None"
        try:
            # Try window focus first (usually fastest)
            cmd = [self.adb_path, "-s", serial, "shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            
            # Alternative: check resumed activities if focus is ambiguous (e.g. on system popups)
            cmd2 = [self.adb_path, "-s", serial, "shell", "dumpsys activity activities | grep 'mResumedActivity'"]
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=3)
            
            combined = (r.stdout + r2.stdout).lower()
            if "com.modelfactory.mobile" in combined:
                return "com.modelfactory.mobile"

            # Fallback parsing for specific package name if needed
            if "mcurrentfocus=" in r.stdout.lower():
                pkg = r.stdout.split(" ")[-1].split("/")[0].replace("}", "").strip()
                return pkg if pkg else "Home"
            return "Home"
        except:
            return "N/A"

    def ping_device(self, serial: str) -> str:
        """Measure ADB RTT latency."""
        start = time.time()
        try:
            subprocess.run([self.adb_path, "-s", serial, "shell", "echo", "1"], capture_output=True, timeout=2)
            rtt = (time.time() - start) * 1000
            return f"{int(rtt)}ms"
        except:
            return "N/A"

    def get_screenshot(self, serial: Optional[str] = None) -> Optional[bytes]:
        """Capture a high-resolution screenshot for calibration."""
        target = serial or self.connected_device_ip
        if not target: return None
        try:
            # Use exec-out on Windows to avoid binary corruption (binary-safe stdout)
            # Increased timeout to 40s for slow wireless connections
            cmd = [self.adb_path, "-s", target, "exec-out", "screencap", "-p"]
            result = subprocess.run(cmd, capture_output=True, timeout=40)
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception as e:
            logger.error(f"Failed to capture calibration screenshot: {e}")
            return None

    def remote_tap(self, x: int, y: int, humanize: bool = True):
        """Execute a remote tap using ADB input tap."""
        if not self.is_connected or not self.connected_device_ip:
            return
            
        final_x, final_y = x, y
        if humanize:
            # Subtle jitter for human-like behavior
            final_x += random.randint(-1, 1)
            final_y += random.randint(-1, 1)
        
        # Using native 'input tap' for maximum reliability and clean visual feedback
        cmd = ["shell", "input", "tap", str(int(final_x)), str(int(final_y))]
            
        logger.debug(f"Mobile Tap: ({final_x}, {final_y}) [humanize={humanize}]")
        subprocess.Popen([self.adb_path, "-s", self.connected_device_ip] + cmd)

    def remote_swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300, humanize: bool = True):
        """Execute a remote swipe with optional speed randomization."""
        if not self.is_connected or not self.connected_device_ip:
            return
            
        final_dur = duration
        if humanize:
            final_dur = int(duration * random.uniform(0.9, 1.2))
            
        logger.debug(f"Mobile Swipe: ({x1},{y1}) to ({x2},{y2}) dur={final_dur}")
        subprocess.Popen([self.adb_path, "-s", self.connected_device_ip, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(final_dur)])

    def deploy_model(self, local_tflite_path: str, remote_name: str = "model.tflite") -> bool:
        if not self.is_connected or not self.connected_device_ip:
            logger.error("Deploy failed: No device connected.")
            return False
        remote_path = f"/sdcard/Download/{remote_name}"
        try:
            cmd = [self.adb_path, "-s", self.connected_device_ip, "push", local_tflite_path, remote_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            return False

    def setup_forwarding(self, local_port: int, remote_port: int = 1234, serial: Optional[str] = None):
        """Setup ADB TCP forwarding for the mobile app stream."""
        target = serial or self.connected_device_ip
        if not self.is_connected or not target:
            return False
        try:
            # First, check if forwarding already exists
            result = subprocess.run([self.adb_path, "forward", "--list"], capture_output=True, text=True)
            if f"tcp:{local_port}" in result.stdout and target in result.stdout:
                # Already forwarded for this specific device/port
                return True
                
            cmd = [self.adb_path, "-s", target, "forward", f"tcp:{local_port}", f"tcp:{remote_port}"]
            subprocess.run(cmd, capture_output=True, timeout=5)
            logger.info(f"ADB Forwarding setup: Local {local_port} -> Remote {remote_port} (Device: {target})")
            return True
        except Exception as e:
            logger.error(f"Forwarding error: {e}")
            return False
    def start_streaming_service(self, serial: str):
        """Attempts to 'wake up' the mobile app via ADB shell, with a 60s cooldown to prevent loops."""
        if not serial: return
        
        # 1. Cooldown Check: Don't spam 'am start' more than once per minute per device
        now = time.time()
        last_time = self._last_wake_up.get(serial, 0)
        if now - last_time < 60:
            logger.debug(f"Wake-up cooldown active for {serial}. Skipping redundant request.")
            return

        # 2. Check if the app is already the active foreground window
        current_app = self.get_foreground_app(serial)
        if "com.modelfactory.mobile" in current_app:
            logger.debug(f"Streaming service wake-up skipped: App already in foreground on {serial}")
            self._last_wake_up[serial] = now # Still update timestamp to reset cooldown
            return

        logger.info(f"Attempting to bring streaming app to foreground on {serial}...")
        try:
            self._last_wake_up[serial] = now
            # Start the MainActivity (only if not already there)
            cmd_main = [self.adb_path, "-s", serial, "shell", "am", "start", "-n", "com.modelfactory.mobile/com.modelfactory.mobile.MainActivity"]
            subprocess.run(cmd_main, capture_output=True, timeout=5)
            
            # Secondary backup using monkey
            cmd_monkey = [self.adb_path, "-s", serial, "shell", "monkey", "-p", "com.modelfactory.mobile", "1"]
            subprocess.run(cmd_monkey, capture_output=True, timeout=5)
        except Exception as e:
            logger.warning(f"Failed to wake up streaming service: {e}")

    def disconnect(self):
        if self.connected_device_ip:
            # Global disconnect logic
            if self.connection_type == "Wireless":
                subprocess.run([self.adb_path, "disconnect", self.connected_device_ip])
            
            # Remove ownership for this device
            if self.connected_device_ip in self.device_owners:
                del self.device_owners[self.connected_device_ip]
                
            self.connected_device_ip = None
            self.is_connected = False
            self.connection_type = None

    def release_device(self, serial: Optional[str] = None):
        """Release the device from model-specific ownership without global disconnect."""
        target = serial or self.connected_device_ip
        if target and target in self.device_owners:
            owner = self.device_owners.pop(target)
            logger.info(f"Device {target} released from model {owner} ownership.")
        else:
            logger.info("No device to release or device not owned.")

    def is_device_locked(self, serial: str, model_name: str) -> Optional[str]:
        """Check if a device is owned by another model. Returns the owner's name if locked."""
        owner = self.device_owners.get(serial)
        if owner and owner != model_name:
            return owner
        return None

    def link_device(self, serial: str, model_name: str) -> bool:
        """Assign ownership of a device to a specific model."""
        if self.is_device_locked(serial, model_name):
            return False
        self.device_owners[serial] = model_name
        logger.info(f"Device {serial} linked to model {model_name}.")
        return True

    @property
    def owner_model(self):
        """Compatibility property: returns the owner of the currently connected device."""
        if self.connected_device_ip:
            return self.device_owners.get(self.connected_device_ip)
        return None
