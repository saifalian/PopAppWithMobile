import logging

try:
    import tensorflow as tf
    from tensorflow.keras import layers, models, mixed_precision
    HAS_TF = True
except Exception:
    HAS_TF = False

logger = logging.getLogger(__name__)

class ModelFactory:
    @staticmethod
    def build_visual_model(num_classes=2, input_shape=(224, 224, 3)):
        """
        Build a MobileNetV2-based classification model.
        """
        if not HAS_TF:
            logger.error("TensorFlow not available — cannot build model")
            return None
            
        logger.info(f"Building visual model with {num_classes} classes")
        
        backbone = tf.keras.applications.MobileNetV2(
            input_shape=input_shape,
            include_top=False,
            weights='imagenet'
        )
        backbone.trainable = False
        
        model = models.Sequential([
            layers.Input(shape=input_shape),
            layers.Lambda(tf.keras.applications.mobilenet_v2.preprocess_input),
            backbone,
            layers.GlobalAveragePooling2D(),
            layers.Dense(256, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(num_classes, activation='softmax', dtype='float32')
        ])
        
        return model

    @staticmethod
    def compile_model(model, learning_rate=0.001, use_mixed_precision=True):
        opt = tf.keras.optimizers.Adam(learning_rate=learning_rate)
        if use_mixed_precision:
            try:
                opt = mixed_precision.LossScaleOptimizer(opt)
            except Exception:
                pass
                
        model.compile(
            optimizer=opt,
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        return model
