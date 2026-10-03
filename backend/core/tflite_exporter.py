import logging
import os
from pathlib import Path
import tensorflow as tf
import numpy as np

logger = logging.getLogger(__name__)

def convert_to_tflite(model_name: str, checkpoint_path: str, int8_quant: bool = True) -> str:
    """
    Converts a SavedModel to TFLite format.
    Optimized for mobile deployment (Xiaomi 14 / Android).
    """
    try:
        logger.info(f"Converting model {model_name} from {checkpoint_path} to TFLite...")
        
        # 1. Load the model
        # converter = tf.lite.TFLiteConverter.from_saved_model(checkpoint_path)
        # However, it's safer to build the model structure and load weights due to custom heads
        # and mixed precision context, especially in TF 2.10
        
        from backend.core.model_factory import load_model, IMG_SIZE
        model = load_model(checkpoint_path, "/CPU:0")
        
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        
        # 2. Optimization Settings
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        if int8_quant:
            # Requires representative dataset for calibration
            def representative_dataset():
                # Load a few samples from the compiled dataset results
                ds_path = Path("models") / model_name / "results" / "dataset.npz"
                if ds_path.exists():
                    data = np.load(ds_path)
                    x_val = data['x_val']
                    # Take up to 100 samples
                    num_samples = min(100, len(x_val))
                    for i in range(num_samples):
                        # Add batch dimension and ensure float32
                        img = x_val[i:i+1].astype(np.float32)
                        yield [img]
                else:
                    # Fallback to random data if dataset missing (less accurate but doesn't crash)
                    for _ in range(5):
                        yield [np.random.uniform(0, 1, (1, IMG_SIZE, IMG_SIZE, 3)).astype(np.float32)]
            
            converter.representative_dataset = representative_dataset
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            converter.inference_input_type = tf.uint8
            converter.inference_output_type = tf.uint8
        
        # 3. Convert
        tflite_model = converter.convert()
        
        # 4. Save
        export_dir = Path("models") / model_name / "mobile"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"{model_name}_optimized.tflite"
        
        with open(export_path, "wb") as f:
            f.write(tflite_model)
            
        logger.info(f"✓ Success: TFLite model saved to {export_path}")
        return str(export_path)
        
    except Exception as e:
        logger.error(f"TFLite conversion failed: {e}")
        raise e
