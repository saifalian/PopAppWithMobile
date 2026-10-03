package com.modelfactory.mobile.engine

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.gpu.GpuDelegate
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

class TFLiteEngine(private val context: Context) {
    private var interpreter: Interpreter? = null
    private var isInitialized = false

    /**
     * Loads a model file from the app's internal storage.
     */
    fun loadModel(modelName: String = "model.tflite") {
        try {
            val modelFile = File(context.filesDir, "models/$modelName")
            if (!modelFile.exists()) {
                Log.e("TFLiteEngine", "Model file not found: ${modelFile.absolutePath}")
                return
            }

            val options = Interpreter.Options()
            
            // Enable GPU acceleration if supported (Recommended for Snapdragon 8 Gen 3)
            val compatList = CompatibilityList()
            if (compatList.isDelegateSupportedOnThisDevice) {
                val delegateOptions = compatList.bestOptionsForThisDevice
                val gpuDelegate = GpuDelegate(delegateOptions)
                options.addDelegate(gpuDelegate)
                Log.d("TFLiteEngine", "GPU Acceleration Enabled")
            }

            interpreter = Interpreter(modelFile, options)
            isInitialized = true
            Log.d("TFLiteEngine", "Model loaded successfully: $modelName")
        } catch (e: Exception) {
            Log.e("TFLiteEngine", "Error loading model: ${e.message}")
        }
    }

    /**
     * Performs inference on a bitmap image.
     * Returns the predicted tap coordinates (x, y) normalized 0.0 to 1.0.
     */
    fun predict(bitmap: Bitmap): Pair<Float, Float>? {
        if (!isInitialized || interpreter == null) return null

        try {
            // Preprocess bitmap to 224x224
            val resizedBitmap = Bitmap.createScaledBitmap(bitmap, 224, 224, true)
            val inputBuffer = bitmapToByteBuffer(resizedBitmap)

            // Prepare output buffer
            val output = Array(1) { FloatArray(2) }
            
            interpreter?.run(inputBuffer, output)

            val x = output[0][0]
            val y = output[0][1]
            
            Log.d("TFLiteEngine", "Prediction: X=$x, Y=$y")
            return Pair(x, y)
        } catch (e: Exception) {
            Log.e("TFLiteEngine", "Inference error: ${e.message}")
            return null
        }
    }

    private fun bitmapToByteBuffer(bitmap: Bitmap): ByteBuffer {
        val byteBuffer = ByteBuffer.allocateDirect(4 * 224 * 224 * 3)
        byteBuffer.order(ByteOrder.nativeOrder())

        val intValues = IntArray(224 * 224)
        bitmap.getPixels(intValues, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)

        for (pixelValue in intValues) {
            byteBuffer.putFloat(((pixelValue shr 16 and 0xFF) - 127.5f) / 127.5f)
            byteBuffer.putFloat(((pixelValue shr 8 and 0xFF) - 127.5f) / 127.5f)
            byteBuffer.putFloat(((pixelValue and 0xFF) - 127.5f) / 127.5f)
        }
        return byteBuffer
    }

    fun close() {
        interpreter?.close()
        isInitialized = false
    }
}
