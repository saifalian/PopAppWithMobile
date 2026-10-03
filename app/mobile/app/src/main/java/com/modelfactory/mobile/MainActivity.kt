package com.modelfactory.mobile

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import com.modelfactory.mobile.services.ScreenStreamService
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.BackHandler
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.contract.ActivityResultContracts.GetContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.snapshots.SnapshotStateList
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.net.NetworkInterface
import java.util.Collections

// Theme Colors
val BgDarkest = Color(0xFF0B0E1A)
val BgPanel = Color(0xFF141828)
val Cyan = Color(0xFF06B6D4)
val Purple = Color(0xFF7C3AED)
val TextGray = Color(0xFF8892B0)
val White = Color(0xFFE6F1FF)
val Green = Color(0xFF10B981)

enum class LogType { SYSTEM, CONN, MODEL }
data class LogEntry(val message: String, val type: LogType, val timestamp: Long = System.currentTimeMillis())

object LogManager {
    val logs = mutableStateListOf<LogEntry>()
    
    fun addLog(msg: String, type: LogType = LogType.SYSTEM) {
        logs.add(LogEntry(msg, type))
        if (logs.size > 500) logs.removeAt(0) // Keep buffer manageable
    }

    fun clear() {
        logs.clear()
        addLog("Logs cleared", LogType.SYSTEM)
    }
}

data class ModelData(val id: String, val name: String, val path: String)

object ModelManager {
    val models = mutableStateListOf<ModelData>()
    
    fun addModel(name: String, path: String) {
        val id = java.util.UUID.randomUUID().toString()
        models.add(ModelData(id, name, path))
    }

    fun deleteModel(id: String) {
        models.removeIf { it.id == id }
    }

    fun renameModel(id: String, newName: String) {
        val idx = models.indexOfFirst { it.id == id }
        if (idx != -1) {
            val oldModel = models[idx]
            models[idx] = oldModel.copy(name = newName)
        }
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SimpleConnectionTheme {
                AppNavigation()
            }
        }
    }
}

@Composable
fun SimpleConnectionTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Cyan,
            background = BgDarkest,
            surface = BgPanel
        ),
        content = content
    )
}

@Composable
fun AppNavigation() {
    var currentScreen by remember { mutableStateOf("menu") }
    var selectedModel by remember { mutableStateOf<ModelData?>(null) }

    when (currentScreen) {
        "menu" -> MainMenuScreen(onNavigate = { currentScreen = it })
        "debug_choice" -> DebugChoiceScreen(onNavigate = { currentScreen = it }, onBack = { currentScreen = "menu" })
        "train_usb" -> USBStandbyScreen(onBack = { currentScreen = "debug_choice" })
        "train_wireless" -> WirelessStandbyScreen(onBack = { currentScreen = "debug_choice" })
        "run" -> RunModelListScreen(
            onNavigate = { screen, model -> 
                currentScreen = screen
                selectedModel = model 
            }, 
            onBack = { currentScreen = "menu" }
        )
        "run_detail" -> RunModelDetailScreen(
            model = selectedModel!!,
            onBack = { currentScreen = "run" }
        )
    }
}

@Composable
fun MainMenuScreen(onNavigate: (String) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDarkest)
            .padding(16.dp)
    ) {
        // Large Train Option
        MenuOption(
            title = "TRAIN MODEL",
            subtitle = "Connect to PC and start data collection",
            icon = Icons.Default.Build,
            color = Purple,
            modifier = Modifier.weight(1f),
            onClick = { onNavigate("debug_choice") }
        )

        Spacer(Modifier.height(16.dp))

        // Large Run Option
        MenuOption(
            title = "RUN MODEL",
            subtitle = "Deploy and execute autonomous agent",
            icon = Icons.Default.PlayArrow,
            color = Cyan,
            modifier = Modifier.weight(1f),
            onClick = { onNavigate("run") }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DebugChoiceScreen(onNavigate: (String) -> Unit, onBack: () -> Unit) {
    var selectedFilter by remember { mutableStateOf<LogType?>(null) }
    
    BackHandler { onBack() }
    
    LaunchedEffect(Unit) {
        if (LogManager.logs.isEmpty()) {
            LogManager.addLog("ModelFactory Hub v1.0.0 Ready", LogType.SYSTEM)
            LogManager.addLog("Awaiting manual connection...", LogType.CONN)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDarkest)
            .padding(16.dp)
    ) {
        // --- HEADER & BACK ---
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Text("←", color = TextGray, fontSize = 20.sp)
            }
            Text("Connection Manager", color = White, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        }

        Spacer(Modifier.height(16.dp))

        // --- COMPACT BUTTONS (TOP) ---
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(
                onClick = { onNavigate("train_usb") ; LogManager.addLog("USB Wizard started", LogType.CONN)},
                colors = ButtonDefaults.buttonColors(containerColor = Cyan),
                modifier = Modifier.weight(1f).height(60.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("🔌 USB", fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
            Button(
                onClick = { onNavigate("train_wireless") ; LogManager.addLog("Wireless Wizard started", LogType.CONN)},
                colors = ButtonDefaults.buttonColors(containerColor = Purple),
                modifier = Modifier.weight(1f).height(60.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("📡 WIRELESS", fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
        }

        Spacer(Modifier.height(24.dp))

        // --- LOG MONITOR (BOTTOM) ---
        Text("LIVE ACTIVITY CONSOLE", color = TextGray, fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
        Spacer(Modifier.height(8.dp))
        
        TerminalLogMonitor(
            modifier = Modifier.weight(1f),
            selectedType = selectedFilter,
            onFilterChange = { selectedFilter = it }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TerminalLogMonitor(
    modifier: Modifier = Modifier,
    selectedType: LogType?,
    onFilterChange: (LogType?) -> Unit
) {
    val listState = rememberLazyListState()
    val filteredLogs = if (selectedType == null) LogManager.logs else LogManager.logs.filter { it.type == selectedType }

    // Auto-scroll logic
    LaunchedEffect(filteredLogs.size) {
        if (filteredLogs.isNotEmpty()) {
            listState.animateScrollToItem(filteredLogs.size - 1)
        }
    }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = BgPanel.copy(alpha = 0.5f)),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, CGray)
    ) {
        Column(Modifier.fillMaxSize()) {
            // Filter Bar
            Row(
                modifier = Modifier.fillMaxWidth().padding(8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChip(
                    selected = selectedType == null,
                    onClick = { onFilterChange(null) },
                    label = { Text("ALL", fontSize = 10.sp) },
                    shape = RoundedCornerShape(20.dp)
                )
                LogType.values().forEach { type ->
                    FilterChip(
                        selected = selectedType == type,
                        onClick = { onFilterChange(type) },
                        label = { Text(type.name, fontSize = 10.sp) },
                        shape = RoundedCornerShape(20.dp)
                    )
                }
                Spacer(Modifier.weight(1f))
                TextButton(onClick = { LogManager.clear() }, contentPadding = PaddingValues(0.dp)) {
                    Text("CLEAR", fontSize = 10.sp, color = Color.Red.copy(alpha = 0.6f))
                }
            }

            Divider(color = CGray, thickness = 0.5.dp)

            // Log Console
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize().background(Color(0xFF0D1021)).padding(10.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                items(filteredLogs) { entry ->
                    LogEntryRow(entry)
                }
            }
        }
    }
}

@Composable
fun LogEntryRow(entry: LogEntry) {
    val tagColor = when (entry.type) {
        LogType.SYSTEM -> TextGray
        LogType.CONN -> Cyan
        LogType.MODEL -> Green
    }
    
    val timestamp = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault()).format(java.util.Date(entry.timestamp))

    Row(modifier = Modifier.fillMaxWidth()) {
        Text("[$timestamp] ", color = TextGray.copy(alpha = 0.5f), fontSize = 11.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
        Text("[${entry.type.name}] ", color = tagColor, fontSize = 11.sp, fontWeight = FontWeight.Bold, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
        Text(entry.message, color = White, fontSize = 12.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
    }
}

val CGray = Color(0xFF1E2440)

@Composable
fun MenuOption(
    title: String,
    subtitle: String,
    icon: ImageVector,
    color: Color,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = BgPanel),
        shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, color.copy(alpha = 0.3f))
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = color,
                modifier = Modifier.size(64.dp)
            )
            Spacer(Modifier.height(16.dp))
            Text(
                title,
                color = White,
                fontSize = 24.sp,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = 1.sp
            )
            Spacer(Modifier.height(8.dp))
            Text(
                subtitle,
                color = TextGray,
                fontSize = 14.sp,
                textAlign = TextAlign.Center
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun USBStandbyScreen(onBack: () -> Unit) {
    MirroringScreen(
        title = "USB Connection Ready",
        activeTitle = "USB Mirroring Active",
        icon = "🔌",
        btnColor = Cyan,
        onBack = onBack
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WirelessStandbyScreen(onBack: () -> Unit) {
    val ip = remember { getIPAddress() ?: "Not Connected to Wi-Fi" }
    MirroringScreen(
        title = "Wireless Debugging",
        activeTitle = "Wireless Mirroring Active",
        subtitle = "Device IP: $ip",
        icon = "📡",
        btnColor = Purple,
        onBack = onBack
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MirroringScreen(
    title: String,
    activeTitle: String,
    subtitle: String = "",
    icon: String,
    btnColor: Color,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val mpManager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
    
    // Persistence
    val prefs = remember { context.getSharedPreferences("mirror_prefs", Context.MODE_PRIVATE) }
    var fps by remember { mutableStateOf(prefs.getInt("fps", 30)) }
    var resHeight by remember { mutableStateOf(prefs.getInt("res_height", 720)) }
    var isStreaming by remember { mutableStateOf(false) }
    
    var selectedFilter by remember { mutableStateOf<LogType?>(null) }

    BackHandler { 
        if (isStreaming) {
            context.stopService(Intent(context, ScreenStreamService::class.java))
        }
        onBack() 
    }

    var showSettings by remember { mutableStateOf(false) }

    val startMediaProjection = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val intent = Intent(context, ScreenStreamService::class.java).apply {
                putExtra(ScreenStreamService.EXTRA_RESULT_CODE, result.resultCode)
                putExtra(ScreenStreamService.EXTRA_DATA, result.data)
                putExtra("fps", fps)
                putExtra("res_height", resHeight)
            }
            context.startForegroundService(intent)
            isStreaming = true
            LogManager.addLog("MediaProjection started: ${resHeight}p @ $fps FPS", LogType.SYSTEM)
        }
    }

    Box(Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(BgDarkest)
                .padding(24.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(Modifier.height(40.dp))
            Text(icon, fontSize = 48.sp)
            Spacer(Modifier.height(16.dp))
            Text(
                if (isStreaming) activeTitle else title,
                color = if (isStreaming) Cyan else White,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold
            )
            if (subtitle.isNotEmpty()) {
                Text(subtitle, color = TextGray, fontSize = 14.sp)
            }
            
            Spacer(Modifier.height(24.dp))

            // -- SETTINGS TOGGLE BUTTON --
            if (!isStreaming) {
                OutlinedButton(
                    onClick = { showSettings = !showSettings },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = TextGray),
                    border = androidx.compose.foundation.BorderStroke(1.dp, CGray)
                ) {
                    Icon(Icons.Default.Settings, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(if (showSettings) "HIDE MIRROR SETTINGS" else "SHOW MIRROR SETTINGS", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }

                Spacer(Modifier.height(12.dp))

                AnimatedVisibility(visible = showSettings) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = BgPanel),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(Modifier.padding(16.dp)) {
                            Text("FPS SETTINGS", color = Cyan, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                                listOf(15, 30, 45, 60).forEach { value ->
                                    FilterChip(
                                        selected = fps == value,
                                        onClick = { fps = value; prefs.edit().putInt("fps", value).apply() },
                                        label = { Text("$value") }
                                    )
                                }
                            }
                            
                            Spacer(Modifier.height(16.dp))
                            
                            Text("RESOLUTION (HEIGHT)", color = Cyan, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                                listOf(240, 480, 720, 1080).forEach { value ->
                                    FilterChip(
                                        selected = resHeight == value,
                                        onClick = { resHeight = value; prefs.edit().putInt("res_height", value).apply() },
                                        label = { Text("${value}p") }
                                    )
                                }
                            }
                        }
                    }
                }
                
                Spacer(Modifier.height(16.dp))

                Button(
                    onClick = { startMediaProjection.launch(mpManager.createScreenCaptureIntent()) },
                    colors = ButtonDefaults.buttonColors(containerColor = btnColor),
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("START MIRRORING", fontWeight = FontWeight.ExtraBold)
                }
            } else {
                Button(
                    onClick = {
                        context.stopService(Intent(context, ScreenStreamService::class.java))
                        isStreaming = false
                        LogManager.addLog("Manual mirror stop requested", LogType.SYSTEM)
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color.Red.copy(alpha = 0.6f)),
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("STOP MIRROR", fontWeight = FontWeight.ExtraBold, color = White)
                }
            }

            Spacer(Modifier.height(32.dp))

            // --- LIVE MONITOR ---
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
                Text("REAL-TIME ACTIVITY", color = TextGray, fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                if (isStreaming) {
                    Text("SYNC ACTIVE", color = Green, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
            }
            Spacer(Modifier.height(8.dp))
            TerminalLogMonitor(
                modifier = Modifier.height(350.dp), // Fixed height inside scrollable area
                selectedType = selectedFilter,
                onFilterChange = { selectedFilter = it }
            )
            
            Spacer(Modifier.height(40.dp))
        }
        
        TextButton(
            onClick = {
                if (isStreaming) {
                    context.stopService(Intent(context, ScreenStreamService::class.java))
                }
                onBack()
            },
            modifier = Modifier.align(Alignment.TopStart).padding(16.dp)
        ) {
            Text("← Back", color = TextGray)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RunModelListScreen(onNavigate: (String, ModelData?) -> Unit, onBack: () -> Unit) {
    BackHandler { onBack() }
    
    val importLauncher = rememberLauncherForActivityResult(GetContent()) { uri ->
        uri?.let {
            val name = it.lastPathSegment ?: "Imported Model"
            ModelManager.addModel(name, it.toString())
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDarkest)
            .padding(16.dp)
    ) {
        // --- HEADER ---
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = null, tint = TextGray)
            }
            Text("Model Hub", color = White, fontSize = 20.sp, fontWeight = FontWeight.Bold)
            
            var showMenu by remember { mutableStateOf(false) }
            Box {
                IconButton(onClick = { showMenu = true }) {
                    Icon(Icons.Default.MoreVert, contentDescription = null, tint = TextGray)
                }
                DropdownMenu(
                    expanded = showMenu,
                    onDismissRequest = { showMenu = false },
                    modifier = Modifier.background(BgPanel)
                ) {
                    DropdownMenuItem(
                        text = { Text("Settings (Future)", color = White) },
                        onClick = { showMenu = false }
                    )
                }
            }
        }

        Spacer(Modifier.height(24.dp))

        // --- MODEL LIST ---
        if (ModelManager.models.isEmpty()) {
            Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("No Models Imported", color = TextGray, fontSize = 14.sp)
                    Spacer(Modifier.height(16.dp))
                    FloatingActionButton(
                        onClick = { importLauncher.launch("*/*") },
                        containerColor = Cyan,
                        contentColor = White
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null)
                    }
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(ModelManager.models) { model ->
                    ModelListItem(
                        model = model,
                        onClick = { onNavigate("run_detail", model) },
                        onDelete = { ModelManager.deleteModel(model.id) },
                        onRename = { 
                            // Simple prompt simulation or direct rename for now
                            ModelManager.renameModel(model.id, model.name + " (R)")
                        }
                    )
                }
                item {
                    Spacer(Modifier.height(16.dp))
                    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                        FloatingActionButton(
                            onClick = { importLauncher.launch("*/*") },
                            containerColor = Cyan,
                            contentColor = White,
                            modifier = Modifier.size(56.dp)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ModelListItem(
    model: ModelData,
    onClick: () -> Unit,
    onDelete: () -> Unit,
    onRename: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = BgPanel),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                model.name,
                color = White,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                IconButton(onClick = { /* TODO: Open Overlay */ }, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.PlayArrow, contentDescription = null, tint = Cyan, modifier = Modifier.size(18.dp))
                }
                IconButton(onClick = onRename, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Edit, contentDescription = null, tint = TextGray, modifier = Modifier.size(18.dp))
                }
                IconButton(onClick = onDelete, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Delete, contentDescription = null, tint = Color.Red.copy(alpha = 0.6f), modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RunModelDetailScreen(model: ModelData, onBack: () -> Unit) {
    BackHandler { onBack() }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDarkest)
            .padding(16.dp)
    ) {
        // --- HEADER ---
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Default.ArrowBack, contentDescription = null, tint = TextGray)
                }
                
                // Title + Rename
                Text(model.name, color = White, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                IconButton(onClick = { ModelManager.renameModel(model.id, model.name + " (R)") }) {
                    Icon(Icons.Default.Edit, contentDescription = null, tint = TextGray, modifier = Modifier.size(16.dp))
                }
            }

            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { /* TODO: Open Overlay */ }) {
                    Icon(Icons.Default.PlayArrow, contentDescription = null, tint = Cyan)
                }
                
                var showMenu by remember { mutableStateOf(false) }
                Box {
                    IconButton(onClick = { showMenu = true }) {
                        Icon(Icons.Default.MoreVert, contentDescription = null, tint = TextGray)
                    }
                    DropdownMenu(
                        expanded = showMenu,
                        onDismissRequest = { showMenu = false },
                        modifier = Modifier.background(BgPanel)
                    ) {
                        DropdownMenuItem(
                            text = { Text("Delete Model", color = Color.Red) },
                            onClick = { 
                                ModelManager.deleteModel(model.id)
                                showMenu = false
                                onBack()
                            }
                        )
                    }
                }
            }
        }

        Spacer(Modifier.height(24.dp))

        Text("MODEL ACTIVITY CONSOLE", color = TextGray, fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
        Spacer(Modifier.height(8.dp))

        // We'll use the same terminal monitor but filter it or show model logs
        var selectedFilter by remember { mutableStateOf<LogType?>(LogType.MODEL) }
        TerminalLogMonitor(
            modifier = Modifier.weight(1f),
            selectedType = selectedFilter,
            onFilterChange = { selectedFilter = it }
        )
    }
}

fun getIPAddress(): String? {
    try {
        val interfaces = NetworkInterface.getNetworkInterfaces()
        for (ni in Collections.list(interfaces)) {
            val addresses = ni.inetAddresses
            for (address in Collections.list(addresses)) {
                if (!address.isLoopbackAddress && address is java.net.Inet4Address) {
                    return address.hostAddress
                }
            }
        }
    } catch (e: Exception) {}
    return null
}
