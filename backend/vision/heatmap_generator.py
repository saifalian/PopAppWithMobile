"""
Confidence Heatmap Generator using Grad-CAM.
Shows where the model is confident vs uncertain on the chart.
Deep green = high confidence cluster here.
Yellow = uncertain.
Nothing = model sees nothing.
"""
import logging
from typing import Optional

import cv2
import numpy as np
import tensorflow as tf

logger = logging.getLogger(__name__)


def generate_gradcam_heatmap(
    model:         tf.keras.Model,
    image_array:   np.ndarray,
    device_string: str = "/CPU:0",
    layer_name:    str = "out_relu",
) -> Optional[np.ndarray]:
    """
    Generate Grad-CAM activation heatmap for an image.

    Args:
        model:        Trained Keras model
        image_array:  BGR numpy array of the screen region
        device_string: TF device string
        layer_name:   Name of last conv layer in MobileNetV2

    Returns:
        BGR numpy array with heatmap overlaid on original image.
        Same size as input image_array.
        Returns None on error.
    """
    try:
        # Preprocess input
        h_orig, w_orig = image_array.shape[:2]
        img_resized = cv2.resize(image_array, (224, 224))
        img_rgb     = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_tensor  = tf.cast(img_rgb, tf.float32) / 255.0
        img_tensor  = tf.expand_dims(img_tensor, 0)

        # Build grad model up to last conv layer
        grad_model = _build_grad_model(model, layer_name)
        if grad_model is None:
            return _fallback_heatmap(image_array, model, device_string)

        # Compute gradients
        with tf.device(device_string):
            with tf.GradientTape() as tape:
                conv_outputs, predictions = grad_model(img_tensor)
                # Use the highest-confidence class
                pred_index  = tf.argmax(predictions[0])
                class_channel = predictions[:, pred_index]

            grads = tape.gradient(class_channel, conv_outputs)

        # Pool gradients
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        # Weight the conv outputs
        conv_outputs = conv_outputs[0]
        heatmap      = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap      = tf.squeeze(heatmap)
        heatmap      = tf.maximum(heatmap, 0) / (
            tf.math.reduce_max(heatmap) + 1e-8
        )
        heatmap_np   = heatmap.numpy()

        # Resize to original image size
        heatmap_resized = cv2.resize(
            heatmap_np, (w_orig, h_orig)
        )

        # Apply colormap (green = high, yellow = medium, nothing = low)
        heatmap_uint8  = np.uint8(255 * heatmap_resized)
        colored_heatmap = cv2.applyColorMap(
            heatmap_uint8, cv2.COLORMAP_SUMMER
        )
        # COLORMAP_SUMMER gives green → yellow gradient

        # Threshold — hide very low confidence areas
        mask = (heatmap_resized > 0.25).astype(np.uint8) * 255
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        colored_heatmap = cv2.bitwise_and(colored_heatmap, mask_3ch)

        # Overlay on original image
        overlay = cv2.addWeighted(
            image_array, 0.55,
            colored_heatmap, 0.45,
            0
        )
        return overlay

    except Exception as e:
        logger.error(f"Grad-CAM error: {e}")
        return None


def _build_grad_model(
    model: tf.keras.Model,
    layer_name: str,
) -> Optional[tf.keras.Model]:
    """Build a model that outputs both conv layer and predictions."""
    try:
        last_conv = model.get_layer(layer_name)
        return tf.keras.Model(
            inputs  = model.inputs,
            outputs = [last_conv.output, model.output]
        )
    except Exception:
        # Try finding last Conv2D layer automatically
        for layer in reversed(model.layers):
            if isinstance(layer, tf.keras.layers.Conv2D):
                try:
                    return tf.keras.Model(
                        inputs  = model.inputs,
                        outputs = [layer.output, model.output]
                    )
                except Exception:
                    continue
    return None


def _fallback_heatmap(
    image_array:   np.ndarray,
    model:         tf.keras.Model,
    device_string: str,
) -> np.ndarray:
    """
    Fallback when Grad-CAM fails.
    Uses sliding window inference to build confidence map.
    Slower but more reliable.
    """
    h, w    = image_array.shape[:2]
    conf_map = np.zeros((h, w), dtype=np.float32)
    step     = 32
    patch_h  = patch_w = 64

    for y in range(0, h - patch_h, step):
        for x in range(0, w - patch_w, step):
            patch = image_array[y:y+patch_h, x:x+patch_w]
            patch_resized = cv2.resize(patch, (224, 224))
            patch_rgb     = cv2.cvtColor(patch_resized, cv2.COLOR_BGR2RGB)
            tensor        = tf.cast(patch_rgb, tf.float32) / 255.0
            tensor        = tf.expand_dims(tensor, 0)

            with tf.device(device_string):
                pred = model(tensor, training=False).numpy()[0]

            confidence = float(np.max(pred))
            conf_map[y:y+patch_h, x:x+patch_w] = np.maximum(
                conf_map[y:y+patch_h, x:x+patch_w], confidence
            )

    conf_uint8 = np.uint8(255 * conf_map)
    colored    = cv2.applyColorMap(conf_uint8, cv2.COLORMAP_SUMMER)
    mask       = (conf_map > 0.4).astype(np.uint8) * 255
    mask_3ch   = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    colored    = cv2.bitwise_and(colored, mask_3ch)
    return cv2.addWeighted(image_array, 0.55, colored, 0.45, 0)
