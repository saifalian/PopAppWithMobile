"""
Saves and loads training checkpoints.
Never overwrites — full history preserved.
Three resume modes: from stop point / from best / start fresh.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

import tensorflow as tf
import shutil

logger = logging.getLogger(__name__)


class CheckpointManager:
    def __init__(self, model_dir: Path):
        self.checkpoints_dir = model_dir / "checkpoints"
        self.best_dir        = model_dir / "best"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.best_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        model:         tf.keras.Model,
        attempt:       int,
        score:         float,
        best_score:    float,
        score_history: list,
        reason:        str = "auto",
        is_best:       bool = False,
    ) -> str:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"ckpt_{reason}_att{attempt:04d}_{ts}"
        ckpt = self.checkpoints_dir / name
        ckpt.mkdir(parents=True, exist_ok=True)

        # Save weights in SavedModel format (required for mixed precision)
        weights_path = str(ckpt / "weights")
        model.save(weights_path, save_format='tf')

        # Save state JSON
        state = {
            "attempt":       attempt,
            "score":         round(score, 4),
            "best_score":    round(best_score, 4),
            "score_history": score_history[-100:],
            "reason":        reason,
            "is_best":       is_best,
            "timestamp":     datetime.utcnow().isoformat(),
        }
        with open(ckpt / "state.json", "w") as f:
            json.dump(state, f, indent=2)

        logger.debug(f"Checkpoint saved: {name}")
        
        # Auto-convert to TFLite if model is intended for mobile
        self.export_tflite(ckpt / "weights", ckpt / "model.tflite")
        
        return str(ckpt)

    def export_tflite(self, saved_model_dir: Path, output_path: Path, quantize: bool = True):
        """Converts a SavedModel to a TFLite flatbuffer."""
        try:
            logger.info(f"Converting {saved_model_dir} to TFLite...")
            converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model_dir))
            
            if quantize:
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
                # Note: For Snapdragon 8 NPUs, INT8 quantization is best.
                # Here we use basic dynamic range quantization as a start.
                
            tflite_model = converter.convert()
            with open(output_path, "wb") as f:
                f.write(tflite_model)
            
            logger.info(f"TFLite model saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"TFLite conversion failed: {e}")
            return False

    def list_checkpoints(self) -> list:
        result = []
        for d in sorted(self.checkpoints_dir.iterdir(), reverse=True):
            sf = d / "state.json"
            if sf.exists():
                with open(sf) as f:
                    s = json.load(f)
                s["path"] = str(d)
                s["name"] = d.name
                result.append(s)
        return result

    def load(self, path: str, device_string: str = "/CPU:0"):
        weights = str(Path(path) / "weights")
        with tf.device(device_string):
            model = tf.keras.models.load_model(weights)
        sf = Path(path) / "state.json"
        state = json.load(open(sf)) if sf.exists() else {}
        return model, state

    def load_best(self, device_string: str = "/CPU:0"):
        best_weights = str(self.best_dir / "model")
        with tf.device(device_string):
            model = tf.keras.models.load_model(best_weights)
        return model
