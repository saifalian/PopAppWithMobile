"""
Detects available compute devices: CPU, CUDA GPU, DirectML GPU.
Configures TensorFlow accordingly.
Provides device list for Settings UI.
"""
import os
import logging
import subprocess
import platform
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ComputeDevice:
    id: str              # e.g. "cpu", "gpu:0", "dml:0"
    name: str            # human-readable e.g. "NVIDIA RTX 3050i"
    device_type: str     # "cpu", "cuda", "directml"
    memory_mb: int = 0
    available: bool = True
    description: str = ""


def detect_all_devices() -> List[ComputeDevice]:
    """
    Detect all available compute devices on this Windows machine.
    Returns list of ComputeDevice objects for Settings UI.
    """
    devices = []

    # Always add CPU
    import psutil
    cpu_name = _get_cpu_name()
    ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    devices.append(ComputeDevice(
        id="cpu",
        name=f"CPU — {cpu_name}",
        device_type="cpu",
        memory_mb=int(ram_gb * 1024),
        description=f"System RAM: {ram_gb} GB · Slow but always works"
    ))

    # Try CUDA (TensorFlow native GPU)
    cuda_devices = _detect_cuda_devices()
    devices.extend(cuda_devices)

    # Try DirectML (works on NVIDIA + AMD + Intel without CUDA)
    dml_devices = _detect_directml_devices()
    # Only add DirectML devices not already found via CUDA
    cuda_names = {d.name for d in cuda_devices}
    for d in dml_devices:
        if d.name not in cuda_names:
            devices.append(d)

    logger.info(f"Detected {len(devices)} compute device(s)")
    for d in devices:
        logger.info(f"  [{d.device_type}] {d.name} — {d.description}")

    return devices


def _get_cpu_name() -> str:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        return name.strip()
    except Exception:
        return platform.processor() or "Unknown CPU"


def _detect_cuda_devices() -> List[ComputeDevice]:
    """Detect NVIDIA GPUs natively via nvidia-smi to avoid TF DirectML plugin pollution."""
    devices = []
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                if not line.strip() or "No devices" in line:
                    continue
                parts = line.split(',')
                name = parts[0].strip()
                mem_mb = int(parts[1].strip()) if len(parts) > 1 else 4096
                devices.append(ComputeDevice(
                    id=f"cuda:{i}",
                    name=name,
                    device_type="cuda",
                    memory_mb=mem_mb,
                    description=f"CUDA · {mem_mb//1024:.1f} GB VRAM · Fastest · Requires CUDA 11.8 + cuDNN 8.6"
                ))
    except Exception as e:
        logger.debug(f"CUDA native detection failed: {e}")
    return devices


def _detect_directml_devices() -> List[ComputeDevice]:
    """Detect DirectX 12 capable GPUs for DirectML."""
    devices = []
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-WmiObject Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
            for i, gpu in enumerate(data):
                name = gpu.get('Name', f'GPU {i}')
                ram_bytes = gpu.get('AdapterRAM', 0)
                ram_mb = int(ram_bytes or 0) // (1024 * 1024)
                if ram_mb <= 0:
                    ram_mb = 4096  # fallback estimate
                devices.append(ComputeDevice(
                    id=f"dml:{i}",
                    name=name,
                    device_type="directml",
                    memory_mb=ram_mb,
                    description=f"DirectML · {ram_mb//1024:.1f} GB VRAM · No CUDA needed"
                ))
    except Exception as e:
        logger.debug(f"DirectML detection: {e}")
    return devices


def _nvidia_smi_name(index: int = 0) -> str:
    try:
        result = subprocess.run(
            ['nvidia-smi', f'--query-gpu=name',
             '--format=csv,noheader', f'--id={index}'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.stdout.strip() and "No devices" not in result.stdout else f"NVIDIA GPU {index}"
    except Exception:
        return f"NVIDIA GPU {index}"


def _nvidia_smi_memory(index: int = 0) -> int:
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total',
             '--format=csv,noheader,nounits', f'--id={index}'],
            capture_output=True, text=True, timeout=5
        )
        return int(result.stdout.strip())
    except Exception:
        return 4096


def get_gpu_live_stats(device_id: str) -> dict:
    """Get live GPU memory and utilization stats."""
    if device_id.startswith("cuda") or device_id.startswith("dml"):
        idx = int(device_id.split(":")[1]) if ":" in device_id else 0
        try:
            result = subprocess.run(
                ['nvidia-smi',
                 '--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu',
                 '--format=csv,noheader,nounits', f'--id={idx}'],
                capture_output=True, text=True, timeout=5
            )
            parts = [p.strip() for p in result.stdout.strip().split(',')]
            return {
                "mem_used": int(parts[0]),
                "mem_total": int(parts[1]),
                "util_pct": int(parts[2]),
                "temp_c": int(parts[3]),
            }
        except Exception:
            pass
    return {"mem_used": 0, "mem_total": 0, "util_pct": 0, "temp_c": 0}


class TFDeviceSetup:
    """Configure TensorFlow for selected device."""

    @staticmethod
    def configure(device: ComputeDevice) -> bool:
        """
        Configure TensorFlow to use the selected device.
        Returns True if successful.
        """
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

        try:
            import tensorflow as tf
            from tensorflow.keras import mixed_precision

            if device.device_type == "cpu":
                # Force CPU only
                tf.config.set_visible_devices([], 'GPU')
                logger.info("TF configured for CPU")
                return True

            elif device.device_type == "cuda":
                gpus = tf.config.list_physical_devices('GPU')
                if gpus:
                    try:
                        # Set memory growth to avoid locking all VRAM
                        tf.config.experimental.set_memory_growth(gpus[0], True)
                        # Enable mixed precision for speed on RTX
                        mixed_precision.set_global_policy('mixed_float16')
                        logger.info(f"TF configured for CUDA: {device.name}")
                        return True
                    except Exception as e:
                        logger.warning(f"CUDA runtime config error: {e}")
                return False

            elif device.device_type == "directml":
                try:
                    import tensorflow_directml_plugin  # noqa
                    gpus = tf.config.list_physical_devices('GPU')
                    if gpus:
                        # DirectML usually doesn't need memory_growth config
                        # but we enable mixed precision if possible
                        try:
                            mixed_precision.set_global_policy('mixed_float16')
                        except Exception:
                            pass
                        logger.info(f"TF configured for DirectML: {device.name}")
                        return True
                    else:
                        logger.error("DirectML plugin loaded but no GPU found")
                        return False
                except ImportError:
                    logger.error("tensorflow-directml-plugin not installed")
                    return False

            return False
        except Exception as e:
            logger.error(f"Error during TF device configuration: {e}")
            return False

    @staticmethod
    def get_tf_device_string(device: ComputeDevice) -> str:
        """Get TF device string like '/GPU:0' or '/CPU:0'."""
        if device.device_type == "cpu":
            return "/CPU:0"
        elif device.device_type in ("cuda", "directml"):
            return "/GPU:0"
        return "/CPU:0"
