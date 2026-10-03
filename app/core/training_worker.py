"""
QThread-based training worker.
Runs the self-improving training loop in background.
Emits signals for UI updates — never blocks the UI thread.
"""
import time
import logging
import numpy as np
from datetime import datetime
import os

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


def _get_tf():
    try:
        import tensorflow as tf
        return tf
    except Exception as e:
        logger.error(f"Could not import TensorFlow: {e}")
        return None


class TrainingWorker(QThread):
    """
    Runs training loop in background thread.
    Uses Qt signals to send updates to UI safely.
    """

    # Signals — emitted from worker thread, received in UI thread
    log_line      = pyqtSignal(str, str)   # (model_name, log_text)
    status_update = pyqtSignal(dict)        # training status dict
    attempt_done  = pyqtSignal(str, float, int)  # (model_name, score, attempt)
    training_error = pyqtSignal(str, str)   # (model_name, error_msg)
    training_finished = pyqtSignal(str)     # model_name

    def __init__(self, model_config: dict, training_config: dict,
                 scoring_config: dict, device_string: str = "/CPU:0"):
        super().__init__()
        self.model_config   = model_config
        self.training_config = training_config
        self.scoring_config  = scoring_config
        self.device_string   = device_string
        self.model_name      = model_config.get("name", "model")

        self._running  = False
        self._paused   = False
        self._iteration = 0
        self._best_score = 0.0
        self._score_history = []

    def stop(self):
        self._running = False
        if hasattr(self, "_state_obj"):
            self._state_obj.running = False

    def pause(self):
        self._paused = True
        if hasattr(self, "_state_obj"):
            self._state_obj.paused = True

    def resume(self):
        self._paused = False
        if hasattr(self, "_state_obj"):
            self._state_obj.paused = False

    def run(self):
        """Main training loop — runs in background thread."""
        from backend.core.training_loop import run_training_loop, TrainingState
        from backend.core.gpu_manager import detect_all_devices, ComputeDevice

        self._running = True
        self._log(f"Training started on device: {self.device_string}")
        
        # 1. Resolve ComputeDevice
        devices = detect_all_devices()
        target_device = None
        for d in devices:
            if d.tf_device_string.lower() == self.device_string.lower():
                target_device = d
                break
        if not target_device:
            target_device = ComputeDevice(
                id="cpu", name="Fallback CPU", device_type="cpu", 
                memory_mb=4096, available=True, description="",
                tf_device_string=self.device_string
            )
            
        # 2. Setup State and Callbacks
        state = TrainingState()
        self._state_obj = state
        
        def _on_log(msg: str):
            # msg from run_training_loop is already formatted, just emit 
            self.log_line.emit(self.model_name, msg)
            
        def _on_status(status: dict):
            self.status_update.emit(status)
            if status.get("iteration", 0) > self._iteration:
                self._iteration = status["iteration"]
                self.attempt_done.emit(self.model_name, status.get("current_score", 0.0), self._iteration)

        try:
            run_training_loop(
                model_id=self.model_name,
                model_name=self.model_name,
                model_config=self.model_config,
                train_config=self.training_config,
                scoring_config=self.scoring_config,
                device=target_device,
                state=state,
                log_cb=_on_log,
                status_cb=_on_status
            )
        except Exception as e:
            logger.exception(f"Training error: {e}")
            self.training_error.emit(self.model_name, str(e))
        finally:
            self._running = False
            self.training_finished.emit(self.model_name)
            self._log("Training stopped.")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {msg}"
        self.log_line.emit(self.model_name, line)
