"""
ModelFactory Desktop Application
Entry point — run with: python main.py
"""
import sys
import os
import logging

# Suppress TF startup noise and force Keras backend before any imports
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['KERAS_BACKEND'] = 'tensorflow'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0' # Prevents floating point variations causing kernel repeats

def setup_cuda_env():
    """Automatically find and load CUDA DLLs from pip packages."""
    if sys.platform != "win32": return
    import sysconfig
    site_packages = sysconfig.get_path('purelib')
    nvidia_base = os.path.join(site_packages, "nvidia")
    if not os.path.exists(nvidia_base): return
    
    # Add all nvidia/*/bin and nvidia/*/lib to DLL search path
    # This enables "CUDA-via-pip" without system-wide install
    for pkg in os.listdir(nvidia_base):
        pkg_path = os.path.join(nvidia_base, pkg)
        if not os.path.isdir(pkg_path): continue
        for sub in ['bin', 'lib']:
            dll_path = os.path.join(pkg_path, sub)
            if os.path.exists(dll_path):
                # os.add_dll_directory is required for Python 3.8+ on Windows
                try: 
                    os.add_dll_directory(dll_path)
                except Exception: 
                    pass
                os.environ['PATH'] = dll_path + os.pathsep + os.environ['PATH']

setup_cuda_env()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from app.app import create_app
from app.main_window import MainWindow
from app.core.settings_manager import settings
from backend.core.gpu_manager import detect_all_devices, configure_tensorflow, _make_cpu_device

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def configure_device_on_startup():
    """Apply saved device config at startup."""
    device_id = settings.get("compute_device_id", "cpu")
    
    # Get all devices to find the correct one
    devices = detect_all_devices()
    device = next((d for d in devices if d.id == device_id), None)
    
    if not device:
        device = _make_cpu_device()
        
    try:
        ok = configure_tensorflow(device)
        if ok:
            logger.info(f"Compute device initialized: {device.name}")
        else:
            logger.warning(f"Device init failed, falling back to CPU: {device.name}")
    except Exception as e:
        logger.warning(f"Device init error (using CPU): {e}")


def main():
    # Configure compute device from saved settings
    configure_device_on_startup()

    # Create and run QApplication
    app = create_app()
    
    # Create and show main window
    window = MainWindow()
    window.show()

    logger.info("ModelFactory started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
