import numpy as np
import tensorflow as tf

IMG_SIZE = 224


def preprocess_single(
    image_array: np.ndarray,
    device_string: str = "/CPU:0"
) -> tf.Tensor:
    with tf.device(device_string):
        t = tf.cast(image_array, tf.float32)
        t = tf.image.resize(t, [IMG_SIZE, IMG_SIZE])
        # t = t / 255.0  <-- REMOVED: model contains preprocess_input
        t = tf.expand_dims(t, 0)
    return t


def preprocess_batch(
    arrays: list,
    device_string: str = "/CPU:0"
) -> tf.Tensor:
    with tf.device(device_string):
        tensors = [tf.cast(a, tf.float32) for a in arrays]
        batch   = tf.stack(tensors)
        batch   = tf.image.resize(batch, [IMG_SIZE, IMG_SIZE])
        # batch   = batch / 255.0  <-- REMOVED: model contains preprocess_input
    return batch
