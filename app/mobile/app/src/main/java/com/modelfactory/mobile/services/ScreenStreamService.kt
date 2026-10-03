package com.modelfactory.mobile.services

import com.modelfactory.mobile.LogManager
import com.modelfactory.mobile.LogType

import android.app.*
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import java.io.ByteArrayOutputStream
import java.io.OutputStream
import java.net.ServerSocket
import java.net.Socket
import kotlin.concurrent.thread

class ScreenStreamService : Service() {

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var serverSocket: ServerSocket? = null
    private var isStreaming = false

    companion object {
        private const val TAG = "ScreenStreamService"
        private const val NOTIFICATION_ID = 1337
        private const val CHANNEL_ID = "ScreenStreamChannel"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_DATA = "data"
        const val PORT = 1234
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private var targetFps = 30
    private var targetHeight = 720

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED) ?: Activity.RESULT_CANCELED
        targetFps = intent?.getIntExtra("fps", 30) ?: 30
        targetHeight = intent?.getIntExtra("res_height", 720) ?: 720
        
        Log.d(TAG, "Starting stream: ${targetHeight}p @ ${targetFps} FPS")

        @Suppress("DEPRECATION")
        val data = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent?.getParcelableExtra(EXTRA_DATA, Intent::class.java)
        } else {
            intent?.getParcelableExtra(EXTRA_DATA)
        }

        if (resultCode == Activity.RESULT_OK && data != null) {
            startForegroundService()
            setupProjection(resultCode, data)
            startServer()
        } else {
            stopSelf()
        }

        return START_NOT_STICKY
    }

    private fun startForegroundService() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Screen Streaming Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("ModelFactory Streaming")
            .setContentText("Screen mirroring is active")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .build()

        startForeground(NOTIFICATION_ID, notification)
    }

    private fun setupProjection(resultCode: Int, data: Intent) {
        val mpManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjection = mpManager.getMediaProjection(resultCode, data)

        // Mandatory callback for Android 14+ to manage resources
        mediaProjection?.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                Log.d(TAG, "MediaProjection stopped")
                stopSelf()
            }
        }, null)

        val metrics = resources.displayMetrics
        val nativeWidth = metrics.widthPixels
        val nativeHeight = metrics.heightPixels
        val density = metrics.densityDpi

        // Scale proportionally: targetHeight (e.g., 480) -> calculate width
        var height = targetHeight
        var width = (targetHeight * nativeWidth) / nativeHeight
        
        // Ensure even dimensions (required by some display buffers)
        if (width % 2 != 0) width--
        if (height % 2 != 0) height--

        Log.d(TAG, "Streaming at scaled resolution: ${width}x${height}")

        imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        virtualDisplay = mediaProjection?.createVirtualDisplay(
            "ScreenStream",
            width, height, density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader?.surface, null, null
        )
    }

    private fun startServer() {
        if (isStreaming) return
        isStreaming = true

        thread {
            try {
                serverSocket = ServerSocket(PORT)
                Log.d(TAG, "Server started on port $PORT")

                while (isStreaming) {
                    val socket = serverSocket?.accept()
                    if (socket != null) {
                        handleClient(socket)
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Server error: ${e.message}")
            }
        }
    }

    private fun handleClient(socket: Socket) {
        thread {
            try {
                val inputStream = socket.getInputStream().bufferedReader()
                val outputStream = socket.getOutputStream().buffered()
                socket.tcpNoDelay = true 
                
                getMainHandler().post { LogManager.addLog("PC Client connected: ${socket.inetAddress}", LogType.CONN) }

                // --- READER THREAD (PC -> Mobile) ---
                thread {
                    try {
                        while (isStreaming && !socket.isClosed) {
                            val line = inputStream.readLine() ?: break
                            getMainHandler().post { 
                                LogManager.addLog(line, LogType.MODEL) 
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Reader loop error: ${e.message}")
                    }
                }

                // --- WRITER LOOP (Mobile -> PC) ---
                val frameInterval = (1000L / targetFps).coerceAtLeast(10L)
                while (isStreaming && !socket.isClosed) {
                    val bitmap = getLatestBitmap()
                    if (bitmap != null) {
                        sendFrame(outputStream, bitmap)
                        Thread.sleep(frameInterval) 
                    } else {
                        Thread.sleep(10)
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Client handler error: ${e.message}")
            } finally {
                try { socket.close() } catch (e: Exception) {}
                getMainHandler().post { LogManager.addLog("PC Client disconnected", LogType.CONN) }
            }
        }
    }

    private fun getMainHandler(): android.os.Handler {
        return android.os.Handler(android.os.Looper.getMainLooper())
    }

    private fun getLatestBitmap(): Bitmap? {
        val image = imageReader?.acquireLatestImage() ?: return null
        try {
            val planes = image.planes
            val buffer = planes[0].buffer
            val pixelStride = planes[0].pixelStride
            val rowStride = planes[0].rowStride
            val rowPadding = rowStride - pixelStride * image.width

            // Create bitmap with correct dimensions
            val bitmap = Bitmap.createBitmap(
                image.width + rowPadding / pixelStride,
                image.height, Bitmap.Config.ARGB_8888
            )
            bitmap.copyPixelsFromBuffer(buffer)
            
            // Return a cropped version without the padding
            return if (rowPadding > 0) {
                Bitmap.createBitmap(bitmap, 0, 0, image.width, image.height)
            } else {
                bitmap
            }
        } catch (e: Exception) {
            Log.e(TAG, "getLatestBitmap crash: ${e.message}")
            return null
        } finally {
            image.close()
        }
    }

    private fun sendFrame(out: OutputStream, bitmap: Bitmap) {
        val stream = ByteArrayOutputStream()
        // Lowering quality from 90 to 75 significantly reduces bandwidth/jitter
        bitmap.compress(Bitmap.CompressFormat.JPEG, 75, stream)
        val jpegData = stream.toByteArray()

        // Protocol: [4-byte length] [jpeg data]
        val lengthBytes = java.nio.ByteBuffer.allocate(4).putInt(jpegData.size).array()
        out.write(lengthBytes)
        out.write(jpegData)
        out.flush()
    }

    override fun onDestroy() {
        super.onDestroy()
        isStreaming = false
        virtualDisplay?.release()
        imageReader?.close()
        mediaProjection?.stop()
        serverSocket?.close()
        Log.d(TAG, "Service destroyed, resources released")
    }
}
