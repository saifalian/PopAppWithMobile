package com.modelfactory.mobile.recording

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream

class ExperienceRecorder(private val context: Context) {
    private var currentRunData = JSONArray()
    private var runId = ""

    fun startNewRun(name: String) {
        runId = "${name}_${System.currentTimeMillis()}"
        currentRunData = JSONArray()
    }

    /**
     * Records a single step: The screen seen and the action taken.
     */
    fun recordStep(bitmap: Bitmap, x: Float, y: Float, confidence: Float) {
        val stepId = System.currentTimeMillis()
        val stepFile = saveBitmap(bitmap, "step_$stepId.jpg")
        
        val stepJson = JSONObject().apply {
            put("timestamp", stepId)
            put("image_path", stepFile?.name)
            put("predicted_x", x)
            put("predicted_y", y)
            put("confidence", confidence)
        }
        currentRunData.put(stepJson)
    }

    private fun saveBitmap(bitmap: Bitmap, filename: String): File? {
        return try {
            val dir = File(context.filesDir, "replays/$runId")
            dir.mkdir()
            val file = File(dir, filename)
            val out = FileOutputStream(file)
            bitmap.compress(Bitmap.CompressFormat.JPEG, 80, out)
            out.flush()
            out.close()
            file
        } catch (e: Exception) {
            Log.e("ExperienceRecorder", "Error saving frame: ${e.message}")
            null
        }
    }

    fun finalizeRun(): File? {
        return try {
            val dir = File(context.filesDir, "replays/$runId")
            val metaFile = File(dir, "metadata.json")
            metaFile.writeText(currentRunData.toString(2))
            Log.d("ExperienceRecorder", "Run finalized: $runId")
            dir
        } catch (e: Exception) {
            null
        }
    }
}
