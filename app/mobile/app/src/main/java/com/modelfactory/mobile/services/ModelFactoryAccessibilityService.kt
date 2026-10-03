package com.modelfactory.mobile.services

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Bitmap
import android.view.accessibility.AccessibilityEvent
import android.util.Log
import com.modelfactory.mobile.engine.TFLiteEngine

class ModelFactoryAccessibilityService : AccessibilityService() {
    private lateinit var tfliteEngine: TFLiteEngine
    private var isAutoRunning = false

    override fun onCreate() {
        super.onCreate()
        tfliteEngine = TFLiteEngine(this)
        tfliteEngine.loadModel()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Handle events from Coinglass (window changes, clicks, etc.)
        event?.let {
            if (it.packageName == "com.coinglass.pro") {
                Log.d("ModelFactory", "Event from Coinglass: ${it.eventType}")
            }
        }
    }

    override fun onInterrupt() {
        Log.d("ModelFactory", "Accessibility Service Interrupted")
    }

    /**
     * Executes a tap gesture at the given coordinates.
     */
    fun tap(x: Float, y: Float) {
        val path = Path()
        path.moveTo(x, y)
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 50))
            .build()
        dispatchGesture(gesture, null, null)
    }

    /**
     * Executes a swipe gesture.
     */
    fun swipe(startX: Float, startY: Float, endX: Float, endY: Float, duration: Long = 300) {
        val path = Path()
        path.moveTo(startX, startY)
        path.lineTo(endX, endY)
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, duration))
            .build()
        dispatchGesture(gesture, null, null)
    }

    /**
     * Logic loop for autonomous control.
     * Takes a screenshot, predicts click location, and taps.
     */
    fun performAutonomousStep(screenshot: Bitmap) {
        if (!isAutoRunning) return

        val prediction = tfliteEngine.predict(screenshot)
        prediction?.let { (x, y) ->
            // Convert normalized (0..1) to screen pixels
            val metrics = resources.displayMetrics
            val screenX = x * metrics.widthPixels
            val screenY = y * metrics.heightPixels
            
            Log.d("ModelFactory", "Tapping predicted location: $screenX, $screenY")
            tap(screenX, screenY)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        tfliteEngine.close()
    }
}
