"""
Main application window.
Left sidebar navigation + right content area.
Matches the LiquidityAI screenshot layout exactly.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QSizePolicy,
    QLineEdit, QTextEdit, QCheckBox, QGridLayout, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette

from app.theme import C, FONT_UI, QSS
from app.pages.dashboard import DashboardPage, DEMO_MODELS
from app.pages.macro_dashboard import MacroDashboardPage
from app.pages.settings_page import SettingsPage
from app.pages.video_processing import VideoProcessingPage
from app.pages.results import ResultsPage
from app.pages.model_screen import ModelScreen
from app.macro.macro_builder import MacroBuilderPage
from app.widgets.create_model_dialog import CreateModelDialog
# from app.widgets.create_macro_dialog import CreateMacroDialog


class NavButton(QPushButton):
    """Left sidebar navigation button."""
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(f"  {icon}   {text}", parent)
        self.setObjectName("nav_btn")
        self.setProperty("active", False)
        self.setMinimumHeight(44)
        self.setCheckable(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class SubNavButton(QPushButton):
    """Indented sub-navigation button."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("nav_sub_btn")
        self.setMinimumHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class NavActionItem(QWidget):
    """
    A sidebar item that contains a name and action buttons (Rename, Delete).
    """
    def __init__(self, text: str, on_click=None, on_rename=None, on_delete=None, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 4, 0)
        self.layout.setSpacing(0)

        self.btn = SubNavButton(text)
        if on_click:
            self.btn.clicked.connect(on_click)
        self.layout.addWidget(self.btn, 1)

        # Action buttons on the RIGHT
        self.actions = QWidget()
        self.actions_layout = QHBoxLayout(self.actions)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(2)

        self.rename_btn = QPushButton("✏")
        self.rename_btn.setFixedSize(22, 22)
        self.rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rename_btn.setToolTip("Rename")
        self.rename_btn.setStyleSheet(f"color: {C['text_d']}; background: transparent; border: none; font-size: 13px;")
        if on_rename:
            self.rename_btn.clicked.connect(on_rename)

        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setFixedSize(22, 22)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setToolTip("Delete")
        self.delete_btn.setStyleSheet(f"color: {C['status_error']}; background: transparent; border: none; font-size: 13px;")
        if on_delete:
            self.delete_btn.clicked.connect(on_delete)

        self.actions_layout.addWidget(self.rename_btn)
        self.actions_layout.addWidget(self.delete_btn)
        self.layout.addWidget(self.actions)


class ExpandableNavButton(QWidget):
    """Nav button with a toggle arrow on the left."""
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.arrow = QPushButton("⌵") # Down arrow by default
        self.arrow.setObjectName("nav_arrow")
        self.arrow.setFixedSize(30, 44)
        self.arrow.setCheckable(True)
        self.layout.addWidget(self.arrow)

        self.btn = NavButton(icon, text)
        # Ensure it doesn't have the standard NavButton padding if it's expandable
        self.btn.setStyleSheet("padding-left: 8px;") 
        self.layout.addWidget(self.btn, 1)



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ModelFactory")
        self.resize(1280, 820)
        self.setMinimumSize(1000, 700)
        self._active_nav: NavButton | None = None
        
        from backend.core.mobile_manager import MobileManager
        self.mobile_mgr = MobileManager(adb_path=r"D:\tools\platform-tools\adb.exe")
        
        self._build_ui()
        self._nav_click(self._nav_buttons[0], 0)

    def closeEvent(self, event):
        """Force cleanup on app close."""
        self.mobile_mgr.disconnect()
        event.accept()

    def _build_ui(self):
        # Apply stylesheet
        self.setStyleSheet(QSS)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────────────
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo area
        logo_widget = QWidget()
        logo_widget.setStyleSheet(f"""
            background: {C['bg_sidebar']};
            border-bottom: 1px solid {C['border']};
        """)
        logo_widget.setFixedHeight(72)
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(16, 12, 16, 12)

        logo_top = QHBoxLayout()
        lightning = QLabel("⚡")
        lightning.setStyleSheet(f"color: {C['orange']}; font-size: 20px;")
        name_lbl = QLabel("ModelFactory")
        name_lbl.setFont(QFont(FONT_UI, 14, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {C['white']};")
        logo_top.addWidget(lightning)
        logo_top.addSpacing(4)
        logo_top.addWidget(name_lbl)
        logo_top.addStretch()

        sub_lbl = QLabel("Autonomous Heatmap Agent")
        sub_lbl.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; padding-left: 28px;")

        logo_layout.addLayout(logo_top)
        logo_layout.addWidget(sub_lbl)
        sidebar_layout.addWidget(logo_widget)

        # Nav items
        nav_items = [
            ("📊", "Unsupervised Dashboard"),
            ("⬡", "Macro Builder"),
            ("🎬", "Video Processing"),
            ("⚙", "Settings"),
        ]

        self._nav_buttons = []
        self._pages = []

        nav_container = QWidget()
        nav_container.setStyleSheet(f"background: {C['bg_sidebar']};")
        nav_v = QVBoxLayout(nav_container)
        nav_v.setContentsMargins(0, 8, 0, 0)
        nav_v.setSpacing(0)

        # ── Navigation Items ───────────────────────────────────
        # 1. Unsupervised Dashboard
        dash_btn = NavButton("📊", "Unsupervised Dashboard")
        nav_v.addWidget(dash_btn)
        self._nav_buttons.append(dash_btn)
        dash_btn.clicked.connect(lambda: self._nav_click(dash_btn, 0))

        self.models_expand = ExpandableNavButton("➕", "Create a New Model")
        nav_v.addWidget(self.models_expand)
        self.sub_container = QWidget()
        self.sub_layout = QVBoxLayout(self.sub_container)
        self.sub_layout.setContentsMargins(0, 0, 0, 0)
        self.sub_layout.setSpacing(0)
        # Models will be loaded dynamically
        nav_v.addWidget(self.sub_container)
        self.models_expand.arrow.clicked.connect(self._toggle_dashboard_menu)
        self.models_expand.btn.clicked.connect(self._open_create_window)
        self.dashboard_arrow = self.models_expand.arrow

        # 2. Macro Builder
        macro_btn = NavButton("⬡", "Macro Builder")
        nav_v.addWidget(macro_btn)
        self._nav_buttons.append(macro_btn)
        macro_btn.clicked.connect(lambda: self._nav_click(macro_btn, 100))

        self.macro_create_expand = ExpandableNavButton("➕", "Create a New Macro")
        nav_v.addWidget(self.macro_create_expand)
        self.macro_create_expand.btn.clicked.connect(self._on_create_macro_request)
        self.macro_create_expand.arrow.clicked.connect(self._toggle_macro_menu)
        self.macro_dash_arrow = self.macro_create_expand.arrow
        
        self.macro_sub_container = QWidget()
        self.macro_sub_layout = QVBoxLayout(self.macro_sub_container)
        self.macro_sub_layout.setContentsMargins(0, 0, 0, 0)
        self.macro_sub_layout.setSpacing(0)
        # Macros will be loaded dynamically
        nav_v.addWidget(self.macro_sub_container)

        # 3. Video Processing
        video_btn = NavButton("🎬", "Video Processing")
        nav_v.addWidget(video_btn)
        self._nav_buttons.append(video_btn)
        video_btn.clicked.connect(lambda: self._nav_click(video_btn, 1))

        # 4. Connect Phone (NEW)
        connect_btn = NavButton("🔌", "Connect Phone")
        nav_v.addWidget(connect_btn)
        self._nav_buttons.append(connect_btn)
        connect_btn.clicked.connect(lambda: self._nav_click(connect_btn, 7)) # New Index

        # 5. Settings
        settings_btn = NavButton("⚙", "Settings")
        nav_v.addWidget(settings_btn)
        self._nav_buttons.append(settings_btn)
        settings_btn.clicked.connect(lambda: self._nav_click(settings_btn, 4))

        nav_v.addStretch()

        # Version label at bottom
        ver = QLabel("v1.0.0")
        ver.setStyleSheet(f"""
            color: {C['text_d']};
            font-size: 11px;
            padding: 10px 16px;
            background: {C['bg_sidebar']};
        """)
        nav_v.addWidget(ver)
        sidebar_layout.addWidget(nav_container)

        # ── CONTENT AREA ─────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setObjectName("content_area")

        # Pages — instantiate all
        self._page_dashboard = DashboardPage()
        self._page_video     = VideoProcessingPage()
        self._page_results   = ResultsPage()
        self._page_settings  = SettingsPage()
        self._page_model     = ModelScreen(self.mobile_mgr)
        self._page_model.fullscreen_requested.connect(self._on_fullscreen_requested)
        self._page_macro     = MacroBuilderPage()

        from app.pages.connect_phone_page import ConnectPhonePage
        self._page_connect   = ConnectPhonePage(self.mobile_mgr)
        self._page_macro_dash = MacroDashboardPage()
        self._page_macro_dash.main_window = self # For callbacks
        
        all_pages = [
            self._page_dashboard,
            self._page_video,
            self._page_macro,
            self._page_results,
            self._page_settings,
            self._page_model,
            self._page_macro_dash,
            self._page_connect, # Index 7
        ]
        self._macro_dash_index = len(all_pages) - 1
        for page in all_pages:
            self._stack.addWidget(page)
            self._pages.append(page)


        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._stack)
        
        # Connect Back button on Model Screen
        # self._page_model.header.back_btn.clicked.connect(lambda: self._nav_click(self._nav_buttons[0], 0))
        
        root.addWidget(self.sidebar)
        root.addWidget(content_container, 1)

        # INITIAL LOAD
        self._refresh_models_list()
        self._refresh_macros_list()

    def _refresh_models_list(self):
        """Reload models from backend and update sidebar."""
        from backend.core.model_manager import list_models
        # Clear existing
        while self.sub_layout.count():
            item = self.sub_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        models = list_models()
        for m in models:
            name = m['name']
            item = NavActionItem(
                f"• {name}",
                on_click=lambda checked, n=name: self._on_model_click(n),
                on_rename=lambda checked, n=name: self._on_rename_model(n),
                on_delete=lambda checked, n=name: self._on_delete_model(n)
            )
            self.sub_layout.addWidget(item)
        
        # Also update dashboard if it exists
        if hasattr(self, '_page_dashboard'):
            self._page_dashboard.refresh_models()

    def _refresh_macros_list(self):
        """Reload macros from backend and update sidebar."""
        from backend.macro.manager import list_macros
        # Clear existing
        while self.macro_sub_layout.count():
            item = self.macro_sub_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        macros = list_macros()
        for m in macros:
            m_id = m['id']
            m_name = m['name']
            item = NavActionItem(
                f"   ⬢  {m_name}",
                on_click=lambda checked, n=m_id: self._on_macro_click(n),
                on_rename=lambda checked, i=m_id, n=m_name: self._on_rename_macro(i, n),
                on_delete=lambda checked, i=m_id: self._on_delete_macro(i)
            )
            self.macro_sub_layout.addWidget(item)

    def _on_rename_model(self, name: str):
        new_name, ok = QInputDialog.getText(self, "Rename Model", f"Enter new name for '{name}':", text=name)
        if ok and new_name and new_name != name:
            from backend.core.model_manager import rename_model
            if rename_model(name, new_name):
                self._refresh_models_list()
                self._page_dashboard.terminal.append(f"✏  Renamed model: <b>{name}</b> → <b>{new_name}</b>", "info")
            else:
                QMessageBox.critical(self, "Error", "Failed to rename model. Check if name already exists.")

    def _on_delete_model(self, name: str):
        reply = QMessageBox.question(self, "Delete Model", f"Are you sure you want to permanently delete model '{name}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from backend.core.model_manager import delete_model
            if delete_model(name):
                self._refresh_models_list()
                self._page_dashboard.terminal.append(f"🗑  Deleted model: <b>{name}</b>", "warning")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete model.")

    def _on_rename_macro(self, macro_id: str, current_name: str):
        new_name, ok = QInputDialog.getText(self, "Rename Macro", f"Enter new name for macro:", text=current_name)
        if ok and new_name and new_name != current_name:
            from backend.macro.manager import rename_macro
            if rename_macro(macro_id, new_name):
                self._refresh_macros_list()
                self._page_dashboard.terminal.append(f"✏  Renamed macro to: <b>{new_name}</b>", "info")
            else:
                QMessageBox.critical(self, "Error", "Failed to rename macro.")

    def _on_delete_macro(self, macro_id: str):
        reply = QMessageBox.question(self, "Delete Macro", f"Are you sure you want to permanently delete this macro?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from backend.macro.manager import delete_macro
            if delete_macro(macro_id):
                self._refresh_macros_list()
                self._page_dashboard.terminal.append(f"🗑  Deleted macro", "warning")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete macro.")

    def _nav_click(self, btn: NavButton, index: int):
        if self._active_nav:
            self._active_nav.set_active(False)
        btn.set_active(True)
        self._active_nav = btn
        
        if index == 100: # Special index for Macro Dashboard
            self._stack.setCurrentIndex(self._macro_dash_index)
        else:
            self._stack.setCurrentIndex(index)

    def _on_fullscreen_requested(self, enabled: bool):
        """Hides/Shows the sidebar when requested by the model screen."""
        if hasattr(self, "sidebar"):
            self.sidebar.setVisible(not enabled)

    def _toggle_dashboard_menu(self):
        """Expand/collapse the dashboard sub-menu."""
        is_expanded = self.sub_container.isVisible()
        self.sub_container.setVisible(not is_expanded)
        self.dashboard_arrow.setText("⌵" if not is_expanded else "›")

    def _toggle_macro_menu(self):
        """Expand/collapse the macro sub-menu."""
        is_expanded = self.macro_sub_container.isVisible()
        self.macro_sub_container.setVisible(not is_expanded)
        self.macro_dash_arrow.setText("⌵" if not is_expanded else "›")

    def _on_create_macro_request(self):
        """Trigger macro creation popup from sidebar."""
        from app.widgets.create_macro_dialog import CreateMacroDialog
        dlg = CreateMacroDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            if data["name"]:
                self._on_macro_created(data["name"], data.get("description", ""))

    def _open_create_window(self):
        """Open the New Model dialog (modal popup)."""
        from app.widgets.create_model_dialog import CreateModelDialog
        from backend.core.model_manager import create_model

        dlg = CreateModelDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            name = data.get("name")
            if name:
                if create_model(
                    model_name=name,
                    description=data.get("description", ""),
                    tasks=data.get("tasks", []),
                    outputs=data.get("outputs", [])
                ):
                    self._refresh_models_list()
                    self._page_dashboard.terminal.append(f"✨  Created new model: <b>{name}</b>", "success")
                    # Optionally switch to the new model screen
                    self._on_model_click(name)
                else:
                    QMessageBox.critical(self, "Error", f"Failed to create model '{name}'. It might already exist.")

    def _on_macro_click(self, macro_id: str):
        """Handle clicking an existing macro in the sidebar or card."""
        self._page_macro.load_macro(macro_id)
        self._stack.setCurrentWidget(self._page_macro)
        
        # Unselect other nav buttons
        if self._active_nav:
            self._active_nav.set_active(False)
            self._active_nav = None
        
        # Get name for terminal
        from backend.macro.manager import load_macro
        m = load_macro(macro_id)
        name = m.get("name") if m else macro_id
        self._page_dashboard.terminal.append(f"⬡  Opening Macro Builder for: {name}", "info")

    def _on_macro_card_click(self, name: str):
        self._on_macro_click(name)

    def _on_macro_created(self, name, description=""):
        """Callback when a new macro is created from the dashboard."""
        from backend.macro.manager import save_macro
        
        # Save to disk immediately so it persists and shows up in refresh
        new_macro = {
            "name": name,
            "description": description,
            "nodes": []
        }
        if save_macro(new_macro):
            self._refresh_macros_list()
            # Ensure menu is expanded so user sees the new item
            self.macro_sub_container.setVisible(True)
            self.macro_dash_arrow.setText("⌵")
            
            self._page_dashboard.terminal.append(f"✨  New Macro Registered: <b>{name}</b>", "success")
            # Automatically open the builder for the new macro
            if "id" in new_macro:
                self._on_macro_click(new_macro["id"])
        else:
            QMessageBox.critical(self, "Error", "Failed to save new macro to disk.")

    def _on_model_click(self, name: str):
        """Handle clicking an existing model in the sidebar."""
        self._page_model.set_model(name)
        self._stack.setCurrentWidget(self._page_model)
        # Unselect other nav buttons
        if self._active_nav:
            self._active_nav.set_active(False)
            self._active_nav = None
        self._page_dashboard.terminal.append(f"📂  Opening Model Screen for: {name}", "info")

    def refresh_sidebar(self):
        """Public alias for refreshing models and macros lists."""
        self._refresh_models_list()
        self._refresh_macros_list()
