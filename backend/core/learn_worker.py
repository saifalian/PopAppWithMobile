import logging
import time
import os
import traceback
from pathlib import Path
from typing import Optional

import numpy as np
import tensorflow as tf
from PyQt6.QtCore import QThread, pyqtSignal

from backend.core.gpu_manager import ComputeDevice, configure_tensorflow, get_live_gpu_stats
from backend.core.model_factory import build_model, unfreeze_backbone, save_model, load_model
from backend.data.dataset_builder import load_tf_datasets

logger = logging.getLogger(__name__)

class LearnWorker(QThread):
    log_line = pyqtSignal(str)
    progress = pyqtSignal(float, str)
    epoch_end = pyqtSignal(int, dict)  # epoch, logs
    gpu_stats = pyqtSignal(dict)
    finished = pyqtSignal(bool, str)

    def __init__(
        self,
        model_name: str,
        model_config: dict,
        learn_config: dict,
        device: ComputeDevice,
        mobile_mgr=None,
        serial=None
    ):
        super().__init__()
        self.model_name = model_name
        self.config = model_config
        self.learn_config = learn_config
        self.device = device
        self.mobile_mgr = mobile_mgr
        self.serial = serial
        self._stop_flag = False
        self._paused_for_thermal = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            self.log_line.emit(f"Starting Supervised Learning for model: {self.model_name}")
            self.progress.emit(0.05, "Configuring GPU...")
            
            if not configure_tensorflow(self.device):
                self.finished.emit(False, "Failed to configure TensorFlow device.")
                return

            self.progress.emit(0.1, "Loading dataset...")
            batch_size = self.learn_config.get("batch_size", 32)
            train_ds, val_ds = load_tf_datasets(
                self.model_name,
                batch_size=batch_size,
                augment=self.learn_config.get("augment", True),
                streaming=self.learn_config.get("streaming", False),
            )

            mode = self.learn_config.get("mode", "imitation")
            self.progress.emit(0.2, f"Initializing model ({mode} mode)...")
            
            lr = self.learn_config.get("learning_rate", 0.001)
            model = self._init_model(mode, lr)
            
            if model is None:
                self.finished.emit(False, "Failed to initialize model architecture.")
                return

            epochs = self.learn_config.get("epochs", 10)
            class_weights = None
            if self.learn_config.get("apply_balance", False):
                self.log_line.emit("Calculating class weights to fix imbalance...")
                class_weights = self._calculate_class_weights(train_ds)
            
            # Custom Callback for UI updates
            worker_ref = self
            class UICallback(tf.keras.callbacks.Callback):
                def __init__(self, worker):
                    self.worker = worker
                
                def on_epoch_end(self, epoch, logs=None):
                    self.worker.epoch_end.emit(epoch + 1, logs or {})
                    self.worker.progress.emit(
                        0.2 + (0.7 * (epoch + 1) / epochs),
                        f"Epoch {epoch + 1}/{epochs} - loss: {logs.get('loss', 0):.4f}"
                    )
                    
                    # 1. GPU Stats
                    stats = get_live_gpu_stats(self.worker.device)
                    self.worker.gpu_stats.emit(stats)
                    
                    # 2. Thermal Guard (Android only)
                    self.worker._check_thermal_safety()
                    
                    if self.worker._stop_flag:
                        self.model.stop_training = True

            callback = UICallback(self)
            
            history = model.fit(
                train_ds,
                validation_data=val_ds,
                epochs=epochs,
                callbacks=[callback],
                class_weight=class_weights,
                verbose=0
            )

            if self._stop_flag:
                self.log_line.emit("⏹ Training stopped.")
                self.finished.emit(False, "Stopped")
                return

            self.progress.emit(0.95, "Saving trained model...")
            save_path = Path("models") / self.model_name / "checkpoints" / f"learn_{int(time.time())}"
            save_model(model, str(save_path))
            
            self.log_line.emit(f"✅ Training complete. Model saved to: {save_path.name}")
            self.progress.emit(1.0, "Finished")
            self.finished.emit(True, str(save_path))

        except Exception as e:
            err_msg = f"Learning Error: {str(e)}\n{traceback.format_exc()}"
            logger.error(err_msg)
            self.log_line.emit(f"❌ ERROR: {str(e)}")
            self.finished.emit(False, err_msg)

    def _check_thermal_safety(self):
        """Thermal Guard implementation for Android devices."""
        if not self.mobile_mgr or not self.serial:
            return

        try:
            info = self.mobile_mgr.get_device_info(self.serial)
            temp_str = info.get("temp", "N/C").replace("°C", "")
            if temp_str == "N/C": return
            
            temp = float(temp_str)
            threshold = 45.0 # Max safe operating temp for generic Android battery
            
            if temp >= threshold:
                self.log_line.emit(f"⚠️ THERMAL PAUSE: Device is too hot ({temp}°C). Cooling down...")
                self._paused_for_thermal = True
                
                # Wait until temp drops below 40°C
                cool_limit = 40.0
                while temp > cool_limit and not self._stop_flag:
                    time.sleep(30) # Check every 30 seconds
                    info = self.mobile_mgr.get_device_info(self.serial)
                    temp = float(info.get("temp", "0").replace("°C", ""))
                    self.log_line.emit(f"... Cooling: {temp}°C")
                
                if not self._stop_flag:
                    self.log_line.emit(f"✅ Temperature safe ({temp}°C). Resuming learning.")
                self._paused_for_thermal = False
        except Exception as e:
            logger.error(f"Thermal check error: {e}")

    def _init_model(self, mode: str, lr: float) -> Optional[tf.keras.Model]:
        task_type = self.config.get("task_type", "visual_detection")
        output_type = self.config.get("output_type", "click_coords")
        num_classes = len(self.config.get("label_set", ["no_action", "click"]))
        
        meta_path = Path("models") / self.model_name / "results" / "dataset_meta.json"
        if meta_path.exists():
            import json
            with open(meta_path) as f:
                meta = json.load(f)
                num_classes = meta.get("n_classes", num_classes)

        if mode == "imitation":
            model = build_model(task_type, output_type, num_classes, self.device.tf_device_string, lr)
            transfer_from = self.learn_config.get("transfer_model")
            if transfer_from:
                self._apply_transfer_weights(model, transfer_from)
            return model

        elif mode in ("fine_tune", "backbone_opt"):
            model_path = self._find_latest_checkpoint()
            if not model_path: return self._init_model("imitation", lr)
            model = load_model(str(model_path), self.device.tf_device_string)
            if mode == "backbone_opt":
                end_count = self.learn_config.get("unfreeze_layer", 50)
                from_layer = max(0, 154 - end_count)
                model = unfreeze_backbone(model, from_layer, lr, self.device.tf_device_string)
            else:
                model.optimizer.learning_rate.assign(lr)
            return model
        return None

    def _apply_transfer_weights(self, target_model, source_model_name):
        try:
            source_dir = Path("models") / source_model_name / "production" / "model"
            if not source_dir.exists():
                ckpts = sorted((Path("models") / source_model_name / "checkpoints").glob("*"), reverse=True)
                if not ckpts: return False
                source_dir = ckpts[0]
            source_model = load_model(str(source_dir), "/CPU:0")
            sb = next((l for l in source_model.layers if "mobilenetv2" in l.name), None)
            tb = next((l for l in target_model.layers if "mobilenetv2" in l.name), None)
            if sb and tb:
                tb.set_weights(sb.get_weights())
                self.log_line.emit(f"✓ Weights transferred from {source_model_name}")
                return True
        except: pass
        return False

    def _find_latest_checkpoint(self):
        prod = self.model_dir() / "production" / "model"
        if prod.exists(): return prod
        ckpt_dir = self.model_dir() / "checkpoints"
        if ckpt_dir.exists():
            ckpts = sorted(ckpt_dir.glob("*"), key=os.path.getmtime, reverse=True)
            if ckpts: return ckpts[0]
        return None

    def model_dir(self):
        return Path("models") / self.model_name

    def _calculate_class_weights(self, dataset):
        try:
            meta_path = Path("models") / self.model_name / "results" / "dataset_meta.json"
            if not meta_path.exists(): return None
            import json
            with open(meta_path) as f:
                meta = json.load(f)
            labels = np.argmax(np.array(meta["train"]["labels"]), axis=1)
            ns = len(labels); uc = np.unique(labels); nc = len(uc)
            counts = np.bincount(labels)
            return {int(cls): float(ns/(nc*counts[cls])) if counts[cls]>0 else 1.0 for cls in uc}
        except: return None
