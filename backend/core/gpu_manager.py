"""
Detects and configures compute devices.
Supports CPU, CUDA (NVIDIA), and DirectML (any DX12 GPU).
Python 3.10, TensorFlow 2.10.
"""
import os
import subprocess
import logging
import platform
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# Singleton state to prevent multiple TF initializations
_CONFIGURED_DEVICE = None


@dataclass
class ComputeDevice:
    id: str
    name: str
    device_type: str
    memory_mb: int
    available: bool
    description: str
    tf_device_string: str


def detect_all_devices() -> List[ComputeDevice]:
    devices = []
    devices.append(_make_cpu_device())
    devices.extend(_detect_cuda_devices())
    dml = _detect_directml_devices()
    existing_names = {d.name for d in devices}
    for d in dml:
        if d.name not in existing_names:
            devices.append(d)
    return devices


def _make_cpu_device() -> ComputeDevice:
    import psutil
    ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    name = _get_cpu_name()
    return ComputeDevice(
        id="cpu", name=name, device_type="cpu",
        memory_mb=int(ram_gb * 1024), available=True,
        description=f"System RAM: {ram_gb} GB · Always works · Slowest",
        tf_device_string="/CPU:0"
    )


def _get_cpu_name() -> str:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        )
        name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        return name.strip()
    except Exception:
        return platform.processor() or "CPU"


def _detect_cuda_devices() -> List[ComputeDevice]:
    devices = []
    try:
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        import tensorflow as tf
        
        # Check for CUDA runtime DLLs on Windows
        if platform.system() == "Windows":
            import ctypes
            try:
                ctypes.WinDLL("cudart64_110.dll")
            except Exception:
                logger.debug("CUDA runtime DLL (cudart64_110.dll) not found in PATH.")
                return []

        gpus = tf.config.list_physical_devices('GPU')
        for i, gpu in enumerate(gpus):
            name = _nvidia_smi_query(i, "name") or f"NVIDIA GPU {i}"
            mem  = _nvidia_smi_query(i, "memory.total")
            mem_mb = int(mem) if mem and mem.isdigit() else 4096
            devices.append(ComputeDevice(
                id=f"cuda:{i}", name=name, device_type="cuda",
                memory_mb=mem_mb, available=True,
                description=(
                    f"CUDA · {mem_mb//1024:.1f} GB VRAM · "
                    f"Verified for TF 2.10 (Requires toolkit 11.2+)"
                ),
                tf_device_string=f"/GPU:{i}"
            ))
    except Exception as e:
        logger.debug(f"CUDA detection skipped: {e}")
    return devices


def _detect_directml_devices() -> List[ComputeDevice]:
    devices = []
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-WmiObject Win32_VideoController | '
             'Select-Object Name,AdapterRAM | ConvertTo-Json'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return devices
        import json
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]
        for i, gpu in enumerate(data):
            name     = gpu.get('Name', f'GPU {i}')
            ram_b    = gpu.get('AdapterRAM', 0) or 0
            ram_mb   = int(ram_b) // (1024 * 1024)
            if ram_mb <= 0:
                ram_mb = 4096
            devices.append(ComputeDevice(
                id=f"dml:{i}",
                name=name,
                device_type="directml",
                memory_mb=ram_mb,
                available=_check_dml_plugin(),
                description=(
                    f"DirectML · {ram_mb//1024:.1f} GB VRAM · "
                    f"No CUDA needed · pip install only"
                ),
                tf_device_string=f"/GPU:{i}"
            ))
    except Exception as e:
        logger.debug(f"DirectML detection skipped: {e}")
    return devices


def _check_dml_plugin() -> bool:
    try:
        # Check if the plugins directory is disabled or missing
        from pathlib import Path
        import site
        for s in site.getsitepackages():
            p = Path(s) / "tensorflow-plugins"
            if not p.exists():
                return False
        
        import tensorflow_directml_plugin  # noqa
        return True
    except ImportError:
        return False


def _nvidia_smi_query(idx: int, field: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ['nvidia-smi', f'--query-gpu={field}',
             '--format=csv,noheader,nounits', f'--id={idx}'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_live_gpu_stats(device: ComputeDevice) -> dict:
    if device.device_type == "cpu":
        import psutil
        return {
            "mem_used": 0, "mem_total": device.memory_mb,
            "util_pct": int(psutil.cpu_percent()),
            "temp_c": 0, "available": True
        }
    idx = int(device.id.split(":")[1]) if ":" in device.id else 0
    try:
        result = subprocess.run(
            ['nvidia-smi',
             '--query-gpu=memory.used,memory.total,'
             'utilization.gpu,temperature.gpu',
             '--format=csv,noheader,nounits', f'--id={idx}'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            p = [x.strip() for x in result.stdout.strip().split(',')]
            return {
                "mem_used":  int(p[0]),
                "mem_total": int(p[1]),
                "util_pct":  int(p[2]),
                "temp_c":    int(p[3]),
                "available": True
            }
    except Exception:
        pass
    return {
        "mem_used": 0, "mem_total": device.memory_mb,
        "util_pct": 0, "temp_c": 0, "available": False
    }


def configure_tensorflow(device: ComputeDevice) -> bool:
    global _CONFIGURED_DEVICE
    
    if _CONFIGURED_DEVICE is not None:
        logger.debug(f"TensorFlow already configured for {_CONFIGURED_DEVICE.name}. Skipping.")
        return True

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    os.environ['KERAS_BACKEND'] = 'tensorflow'
    
    if device.device_type == "cpu":
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        logger.info("TensorFlow configured for CPU")
        _CONFIGURED_DEVICE = device
        return True
        
    elif device.device_type == "cuda":
        idx = int(device.id.split(":")[1])
        # STRICT ISOLATION: Ensure only this GPU is seen by TF
        os.environ['CUDA_VISIBLE_DEVICES'] = str(idx)
        os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
        
        try:
            import tensorflow as tf
            from tensorflow.keras import mixed_precision
            
            # Additional environment-level memory growth (redundancy)
            os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'
            
            gpus = tf.config.list_physical_devices('GPU')
            if gpus:
                try:
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)
                except (ValueError, RuntimeError):
                    # Already initialized, ignore
                    pass
                
                # Force mixed precision for speed and to stabilize kernels
                try:
                    mixed_precision.set_global_policy('mixed_float16')
                    logger.info("Mixed precision: mixed_float16 enabled")
                except Exception:
                    pass
                    
                logger.info(f"TensorFlow configured for CUDA: {device.name}")
                _CONFIGURED_DEVICE = device
                return True
        except Exception as e:
            logger.error(f"CUDA TF config error: {e}")
        return False
    elif device.device_type == "directml":
        try:
            import tensorflow as tf
            # Try both names due to inconsistency in some pip versions
            try:
                import tensorflow_directml_plugin  # noqa
            except ImportError:
                try:
                    import importlib
                    importlib.import_module("tensorflow-directml-plugin")
                    logger.warning("DirectML plugin found with hyphenated name. Module naming may be inconsistent.")
                except ImportError:
                    raise ImportError("No DirectML module found.")

            # Detect potential "Multiple OpKernel" clash (DirectML + CUDA)
            gpus = tf.config.list_physical_devices('GPU')
            if len(gpus) > 1:
                logger.warning(
                    f"MULTIPLE GPUs DETECTED ({len(gpus)}). "
                    "This often causes 'Multiple OpKernel registrations' errors with DirectML plugin. "
                    "Recommend setting CUDA_VISIBLE_DEVICES='-1' manually if crashes occur."
                )

            logger.info(f"TensorFlow configured for DirectML: {device.name}")
            _CONFIGURED_DEVICE = device
            return True
        except Exception as e:
            logger.error(
                f"DirectML plugin initialization failed: {e}. "
                "Ensure 'pip install tensorflow-directml-plugin' was successful."
            )
            return False
    return False


def warmup_gpu(device: ComputeDevice):
    if device.device_type == "cpu":
        return
    try:
        import tensorflow as tf
        logger.info("GPU warmup starting...")
        with tf.device(device.tf_device_string):
            dummy = tf.zeros([1, 224, 224, 3])
            warmup = tf.keras.applications.MobileNetV2(
                input_shape=(224, 224, 3),
                include_top=False,
                weights=None
            )
            _ = warmup(dummy, training=False)
            del warmup, dummy
        logger.info("GPU warmup complete — CUDA kernels initialized")
    except Exception as e:
        logger.warning(f"GPU warmup failed (non-fatal): {e}")
