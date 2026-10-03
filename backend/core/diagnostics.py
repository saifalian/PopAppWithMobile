"""
Full System Diagnostics Runner.
Checks Python version, TF version/plugins, CUDA availability,
folder permissions, OCR installation, etc.
"""
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def run_full_diagnostics(
    settings_manager,
    progress_cb: Optional[Callable[[str, str], None]] = None
) -> dict:
    """
    Run all system checks.
    progress_cb(check_name, status)
    Returns dictated results.
    """
    results = {}

    def check(name: str, fn):
        if progress_cb:
            progress_cb(name, "running...")
        try:
            res = fn()
            results[name] = {"status": res[0], "details": res[1]}
            if progress_cb:
                progress_cb(name, res[0])
        except Exception as e:
            results[name] = {"status": "error", "details": str(e)}
            if progress_cb:
                progress_cb(name, "error")

    # 1. Python Environment
    check("Python Version", _check_python)
    check("TensorFlow", _check_tensorflow)
    check("DirectML Plugin", _check_directml)

    # 2. System Dependencies
    check("Tesseract OCR", _check_tesseract)
    check("Ollama Connection", lambda: _check_ollama(settings_manager))

    # 3. App Directories
    check("Workspace Paths", lambda: _check_paths(settings_manager))

    # 4. Hardware
    check("Hardware Resources", _check_hardware)

    overall = "ok"
    for r in results.values():
        if r["status"] == "error":
            overall = "error"
            break
        if r["status"] == "warning" and overall != "error":
            overall = "warning"

    return {
        "status":  overall,
        "details": results
    }

# ── Individual Checks ──────────────────────────────────────────

def _check_python():
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major != 3 or v.minor < 10:
        return ("error", f"Requires Python 3.10+. Found {ver_str}")
    return ("ok", f"Python {ver_str} in {sys.prefix}")

def _check_tensorflow():
    try:
        import tensorflow as tf
        v = tf.__version__
        if v != "2.10.0":
            return ("warning", f"TF {v} detected. Using TF 2.10.0 is recommended for Native Windows GPU support.")
        return ("ok", f"TensorFlow {v}")
    except ImportError:
        return ("error", "TensorFlow not installed.")

def _check_directml():
    try:
        import tensorflow_directml  # type: ignore
        return ("ok", "tensorflow-directml is installed.")
    except ImportError:
        return ("warning", "tensorflow-directml plugin not found. GPU acceleration might not be available on AMD/Intel.")

def _check_tesseract():
    # Common windows paths
    paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    ]
    tess_path = None
    for p in paths:
        if os.path.exists(p):
            tess_path = p
            break
            
    if not tess_path:
        # Check PATH
        tess_path = shutil.which("tesseract")

    if tess_path:
        try:
            res = subprocess.run(
                [tess_path, "--version"],
                capture_output=True, text=True, check=True
            )
            v = res.stdout.splitlines()[0]
            return ("ok", f"Found at {tess_path}\n{v}")
        except Exception as e:
            return ("error", f"Tesseract found but failed to run: {e}")

    return ("warning", "Tesseract-OCR not found. Screen text reading will be impaired. Install it to C:\\Program Files\\Tesseract-OCR.")

def _check_ollama(settings):
    if not settings.get("ollama_enabled"):
        return ("ok", "Ollama integration is disabled in settings.")
    try:
        import requests
        host = settings.get("ollama_host", "http://localhost:11434")
        res = requests.get(f"{host}/api/tags", timeout=3.0)
        res.raise_for_status()
        data = res.json()
        models = [m['name'] for m in data.get('models', [])]
        if not models:
            return ("warning", f"Ollama is running at {host} but no models are downloaded.")
        return ("ok", f"Connected to {host}. Available models: {len(models)}")
    except requests.exceptions.ConnectionError:
        return ("error", "Ollama connection failed. Is the Ollama desktop app running?")
    except requests.exceptions.Timeout:
        return ("error", "Ollama connection timeout.")
    except Exception as e:
        return ("error", f"Ollama error: {e}")

def _check_paths(settings):
    paths = [
        settings.get("models_path", "models"),
        settings.get("datasets_path", "datasets"),
        settings.get("logs_path", "logs"),
        settings.get("backup_path", "backups")
    ]
    errs = []
    for p in paths:
        path_obj = Path(p)
        try:
            path_obj.mkdir(parents=True, exist_ok=True)
            # test write
            test_file = path_obj / ".test_write"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            errs.append(f"Failed to access {p}: {e}")
            
    if errs:
        return ("error", "\n".join(errs))
    return ("ok", "All application directories are created and writable.")

def _check_hardware():
    try:
        import psutil
        mem = psutil.virtual_memory()
        RAM_gb = mem.total / (1024**3)
        disk = psutil.disk_usage('/')
        FreeSpace_gb = disk.free / (1024**3)
        
        issues = []
        if RAM_gb < 7:
            issues.append(f"Low RAM: {RAM_gb:.1f}GB total (8GB+ recommended)")
        if FreeSpace_gb < 10:
            issues.append(f"Low Disk Space: {FreeSpace_gb:.1f}GB free on C: (10GB+ recommended)")
            
        if issues:
            return ("warning", " Hardware constraints:\n" + "\n".join(issues))
        return ("ok", f"RAM: {RAM_gb:.1f}GB, Free Disk: {FreeSpace_gb:.1f}GB")
    except ImportError:
         return ("warning", "psutil not installed, cannot check hardware.")
    except Exception as e:
         return ("error", f"Hardware check failed: {e}")
