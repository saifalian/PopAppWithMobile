"""
Builds TensorFlow model architectures.
MobileNetV2 backbone with task-specific heads.
Mixed precision for GPU training.
Python 3.10, TensorFlow 2.10.
"""
import logging
from pathlib import Path
import tensorflow as tf
from tensorflow.keras import mixed_precision

logger = logging.getLogger(__name__)

IMG_SIZE  = 224
IMG_SHAPE = (IMG_SIZE, IMG_SIZE, 3)


def build_model(
    task_type:   str,
    output_type: str,
    num_classes: int = 2,
    device_string: str = "/CPU:0",
    learning_rate: float = 0.001,
    dense_units:   int = 256,
    dropout_rate:  float = 0.3,
) -> tf.keras.Model:
    """
    Build model for given task and output type.
    Places all ops on specified device.

    task_type options:
        visual_detection, click_navigation, data_extraction,
        decision_making, settings_adjustment, sequence

    output_type options:
        click_coords   → 2 neurons, sigmoid (normalized x,y)
        yes_no         → 2 neurons, softmax
        numeric        → 1 neuron, linear
        extracted_text → num_classes neurons, softmax (OCR class)
        ranked_list    → num_classes neurons, softmax
        conditional    → 2 neurons, softmax
        scroll_amount  → 1 neuron, linear
    """
    logger.info(
        f"Building model: task={task_type} output={output_type} "
        f"classes={num_classes} device={device_string}"
    )

    # Targeted fix for "Multiple OpKernel registrations" clash
    # Force the random weight initialization to CPU to avoid GPU op priority conflict
    with tf.device('/CPU:0'):
        backbone = tf.keras.applications.MobileNetV2(
            input_shape=IMG_SHAPE,
            include_top=False,
            weights='imagenet'
        )
        backbone.trainable = False

    with tf.device(device_string):

        # ── INPUT ────────────────────────────────────────────────
        inputs = tf.keras.Input(shape=IMG_SHAPE, name="image_input")
        x = tf.keras.applications.mobilenet_v2.preprocess_input(inputs)

        # ── FEATURE EXTRACTION ───────────────────────────────────
        x = backbone(x, training=False)
        x = tf.keras.layers.GlobalAveragePooling2D(name="gap")(x)

        # ── TASK-SPECIFIC HEAD ───────────────────────────────────
        if task_type == "data_extraction":
            x = tf.keras.layers.Dense(512, name="fc1")(x)
            x = tf.keras.layers.BatchNormalization(name="bn1")(x)
            x = tf.keras.layers.Activation('relu', name="relu1")(x)
            x = tf.keras.layers.Dropout(dropout_rate, name="drop1")(x)
            x = tf.keras.layers.Dense(256, name="fc2")(x)
            x = tf.keras.layers.Activation('relu', name="relu2")(x)
            x = tf.keras.layers.Dropout(0.2, name="drop2")(x)

        elif task_type in (
            "visual_detection", "click_navigation", "settings_adjustment"
        ):
            x = tf.keras.layers.Dense(dense_units, name="fc1")(x)
            x = tf.keras.layers.BatchNormalization(name="bn1")(x)
            x = tf.keras.layers.Activation('relu', name="relu1")(x)
            x = tf.keras.layers.Dropout(dropout_rate, name="drop1")(x)

        else:
            x = tf.keras.layers.Dense(128, name="fc1")(x)
            x = tf.keras.layers.Activation('relu', name="relu1")(x)
            x = tf.keras.layers.Dropout(0.2, name="drop1")(x)

        # ── OUTPUT ───────────────────────────────────────────────
        # IMPORTANT: output MUST be float32 even with mixed precision
        if output_type == "click_coords":
            outputs = tf.keras.layers.Dense(
                2, activation='sigmoid',
                dtype='float32', name="click_output"
            )(x)
        elif output_type in ("numeric", "scroll_amount"):
            outputs = tf.keras.layers.Dense(
                1, activation='linear',
                dtype='float32', name="numeric_output"
            )(x)
        else:
            outputs = tf.keras.layers.Dense(
                num_classes, activation='softmax',
                dtype='float32', name="class_output"
            )(x)

        model = tf.keras.Model(
            inputs=inputs, outputs=outputs,
            name=f"mf_{task_type}_{output_type}"
        )

    # ── COMPILE ──────────────────────────────────────────────────
    optimizer = tf.keras.optimizers.Adam(
        learning_rate=learning_rate,
        beta_1=0.9,
        beta_2=0.999,
        epsilon=1e-7
    )

    # Loss-scale optimizer for mixed precision stability
    if device_string != "/CPU:0":
        try:
            optimizer = mixed_precision.LossScaleOptimizer(optimizer)
        except Exception as e:
            logger.warning(f"LossScaleOptimizer failed, using standard: {e}")

    loss    = ('mse' if output_type in ('click_coords', 'numeric', 'scroll_amount')
               else 'categorical_crossentropy')
    metrics = (['mae'] if loss == 'mse' else ['accuracy'])

    model.compile(optimizer=optimizer, loss=loss, metrics=metrics)

    params = model.count_params()
    logger.info(f"Model built: {params:,} parameters")
    return model


def unfreeze_backbone(
    model: tf.keras.Model,
    from_layer: int = 100,
    learning_rate: float = 0.0001,
    device_string: str = "/CPU:0"
) -> tf.keras.Model:
    """
    Unfreeze top layers of MobileNetV2 for fine-tuning.
    Call after imitation learning converges (50+ attempts).
    """
    try:
        backbone = model.get_layer('mobilenetv2_1.00_224')
        backbone.trainable = True
        for layer in backbone.layers[:from_layer]:
            layer.trainable = False
        trainable = sum(1 for l in backbone.layers if l.trainable)
        logger.info(f"Backbone unfrozen: {trainable} layers from {from_layer}")
    except Exception as e:
        logger.warning(f"Unfreeze failed: {e}")

    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    if device_string != "/CPU:0":
        try:
            optimizer = mixed_precision.LossScaleOptimizer(optimizer)
        except Exception:
            pass

    model.compile(
        optimizer=optimizer,
        loss=model.loss,
        metrics=model.metrics_names[1:]
    )
    return model


def save_model(model: tf.keras.Model, path: str):
    """Save in SavedModel format. Required for mixed precision."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    model.save(path, save_format='tf')
    logger.info(f"Model saved: {path}")


def load_model(path: str, device_string: str = "/CPU:0") -> tf.keras.Model:
    """Load model back to specified device."""
    with tf.device(device_string):
        model = tf.keras.models.load_model(path)
    logger.info(f"Model loaded from: {path}")
    return model
