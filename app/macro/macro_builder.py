"""
Visual flowchart editor for macros.
Renders nodes directly via a custom QGraphicsView widget.
Provides a palette of available node types and a properties inspector.
"""
import json
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
    QScrollArea, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QMessageBox,
    QToolBar, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QBrush

from app.widgets.node_canvas import NodeCanvas, ConnectionLine
from app.theme import C
from backend.macro.node_types import NODE_REGISTRY
from backend.macro.manager import save_macro, load_macro
from backend.core.model_manager import list_models

logger = logging.getLogger(__name__)


class MacroBuilderPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_macro_id = None
        self.current_macro_name = "Unnamed Macro"
        self.current_macro_desc = ""

        # Global selected node
        self.selected_node_id = None
        self.selected_node_data = None
        self.selected_conn = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ──
        toolbar = QToolBar("Macro Builder")
        toolbar.setStyleSheet(f"""
            QToolBar {{
                background: {C['bg_panel']};
                border-bottom: 1px solid {C['border']};
                padding: 4px;
            }}
            QPushButton {{
                background: {C['bg_card']};
                color: {C['text_b']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                padding: 6px 12px;
                margin-right: 8px;
            }}
            QPushButton:hover {{
                background: {C['purple']};
                color: white;
            }}
        """)

        btn_new  = QPushButton("New")
        btn_new.clicked.connect(self.action_new_macro)
        
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.action_save_macro)
        
        btn_settings = QPushButton("Macro Settings")
        btn_settings.clicked.connect(lambda: self.inspector_stack.setCurrentIndex(1))

        self.lbl_title = QLabel(f"Editing: {self.current_macro_name}")
        self.lbl_title.setStyleSheet(f"font-weight: bold; font-size: 14px; margin-left: 10px; color: {C['white']};")

        toolbar.addWidget(btn_new)
        toolbar.addWidget(btn_save)
        toolbar.addWidget(btn_settings)
        toolbar.addWidget(self.lbl_title)
        layout.addWidget(toolbar)

        # ── Main Splitter ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: var(--border);
                width: 2px;
            }
        """)

        # 1. Left Palette
        palette_widget = self._build_palette()
        splitter.addWidget(palette_widget)

        # 2. Center Canvas
        self.canvas = NodeCanvas()
        self.canvas.node_selected.connect(self.on_node_selected)
        self.canvas.connection_selected.connect(self.on_connection_selected)
        splitter.addWidget(self.canvas)

        # 3. Right Inspector
        inspector_widget = self._build_inspector()
        splitter.addWidget(inspector_widget)

        # Set stretch factors (Palette, Canvas, Inspector)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 2)

        layout.addWidget(splitter)

    # ── PALETTE ──

    def _build_palette(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel("Node Palette")
        lbl.setStyleSheet(f"font-weight: bold; padding: 10px; background: {C['bg_sidebar']}; color: {C['purple_l']}; border-bottom: 1px solid {C['border']}; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;")
        
        self.palette_list = QListWidget()
        self.palette_list.setStyleSheet(f"""
            QListWidget {{
                background: {C['bg_darkest']};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px;
                margin: 4px 8px;
                background: {C['bg_panel']};
                border-radius: 6px;
                border: 1px solid {C['border']};
                color: {C['text_b']};
            }}
            QListWidget::item:hover {{
                background: {C['bg_card']};
                border-color: {C['purple']};
                color: {C['white']};
            }}
        """)

        # Populate palette from registry
        for n_type, cls in NODE_REGISTRY.items():
            icon = getattr(cls, "NODE_ICON", "⚙")
            name = n_type.replace("_", " ").title()
            
            item = QListWidgetItem(f"{icon}  {name}")
            item.setData(Qt.ItemDataRole.UserRole, n_type)
            self.palette_list.addItem(item)
            
        self.palette_list.itemDoubleClicked.connect(self.on_palette_double_click)

        layout.addWidget(lbl)
        layout.addWidget(self.palette_list)
        return container

    def on_palette_double_click(self, item: QListWidgetItem):
        n_type = item.data(Qt.ItemDataRole.UserRole)
        # Tell canvas to add a new node of this type in the center
        self.canvas.add_node_type(n_type)

    # ── INSPECTOR ──

    def _build_inspector(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.inspector_stack = QStackedWidget()
        
        # Page 0: Node Properties
        node_page = QWidget()
        node_layout = QVBoxLayout(node_page)
        node_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_node = QLabel("Node Properties")
        lbl_node.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {C['white']};")
        node_layout.addWidget(lbl_node)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        self.props_container = QWidget()
        self.props_layout = QFormLayout(self.props_container)
        self.props_layout.setContentsMargins(0, 0, 0, 0)
        self.props_layout.setSpacing(12)
        
        scroll.setWidget(self.props_container)
        node_layout.addWidget(scroll)
        
        # Standard generic fields - no longer members to avoid deletion issues
        
        btn_delete = QPushButton("Delete Node")
        btn_delete.setStyleSheet("background: #ef4444; color: white;")
        btn_delete.clicked.connect(self.on_delete_node)
        node_layout.addWidget(btn_delete)

        # Page 1: Global Macro Settings
        macro_page = QWidget()
        macro_layout = QFormLayout(macro_page)
        macro_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_macro = QLabel("Macro Settings")
        lbl_macro.setStyleSheet(f"font-weight: bold; font-size: 14px; margin-bottom: 10px; color: {C['white']};")
        macro_layout.addRow(lbl_macro)
        
        self.input_macro_name = QLineEdit(self.current_macro_name)
        self.input_macro_name.textChanged.connect(self._sync_macro_settings)
        
        self.input_macro_desc = QLineEdit(self.current_macro_desc)
        self.input_macro_desc.textChanged.connect(self._sync_macro_settings)
        
        macro_layout.addRow("Name:", self.input_macro_name)
        macro_layout.addRow("Description:", self.input_macro_desc)

        # Page 2: Connection Properties
        conn_page = QWidget()
        conn_layout = QVBoxLayout(conn_page)
        conn_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_conn = QLabel("Connection Properties")
        lbl_conn.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {C['white']};")
        conn_layout.addWidget(lbl_conn)

        self.conn_info = QLabel("No connection selected")
        self.conn_info.setStyleSheet(f"color: {C['text_b']}; margin: 10px 0;")
        self.conn_info.setWordWrap(True)
        conn_layout.addWidget(self.conn_info)

        btn_del_conn = QPushButton("Delete Branch")
        btn_del_conn.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_card']};
                color: #ef4444;
                border: 1px solid #ef4444;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #ef4444;
                color: white;
            }}
        """)
        btn_del_conn.clicked.connect(self.on_delete_connection)
        conn_layout.addWidget(btn_del_conn)
        conn_layout.addStretch()

        self.inspector_stack.addWidget(node_page)  # Index 0
        self.inspector_stack.addWidget(macro_page) # Index 1
        self.inspector_stack.addWidget(conn_page)  # Index 2
        
        layout.addWidget(self.inspector_stack)
        return container

    def _sync_macro_settings(self):
        self.current_macro_name = self.input_macro_name.text()
        self.current_macro_desc = self.input_macro_desc.text()
        self.lbl_title.setText(f"Editing: {self.current_macro_name}")

    def on_node_selected(self, node_id: str, node_data: dict):
        self.selected_node_id = node_id
        self.selected_node_data = node_data
        self.selected_conn = None
        self.inspector_stack.setCurrentIndex(0)  # Show node props
        self._populate_properties()

    def on_connection_selected(self, conn_item):
        self.selected_conn = conn_item
        self.selected_node_id = None
        self.selected_node_data = None
        
        src_name = conn_item.src_p.node.label_text
        src_port = conn_item.src_p.name
        dst_name = conn_item.dst_p.node.label_text
        dst_port = conn_item.dst_p.name
        
        self.conn_info.setText(
            f"<b>From:</b> {src_name} ({src_port})<br>"
            f"<b>To:</b> {dst_name} ({dst_port})"
        )
        self.inspector_stack.setCurrentIndex(2) # Show connection props

    def _populate_properties(self):
        # Clear layout safely
        while self.props_layout.count():
            item = self.props_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.selected_node_id:
            return

        data = self.selected_node_data
        config = data.get("config", {})

        # 1. Label
        self._inp_label = QLineEdit(data.get("label", data.get("type")))
        self._inp_label.textChanged.connect(self.on_prop_changed)
        self.props_layout.addRow("Label", self._inp_label)

        # 2. Dynamic properties generic based on type.
        # Ideally, each Node class defines a SCHEMA, but for this robust backend
        # we will render a JSON blob editor or specific fields if known.
        
        n_type = data.get("type", "")
        
        # Example dynamic fields based on type
        if n_type == "model":
            # Replacement: Use a dropdown for available models
            models = list_models()
            model_names = [m["name"] for m in models]
            
            inp_model = QComboBox()
            inp_model.addItems(model_names)
            
            current_model = config.get("model_name", "")
            if current_model in model_names:
                inp_model.setCurrentText(current_model)
            
            def handle_model_change(model_name):
                self._update_config("model_name", model_name)
                # Also update the node label to match the model name as requested
                self._inp_label.setText(model_name)
                self.on_prop_changed()

            inp_model.currentTextChanged.connect(handle_model_change)
            self.props_layout.addRow("Select Model", inp_model)
            
            inp_thresh = QDoubleSpinBox()
            inp_thresh.setMaximum(1.0)
            inp_thresh.setSingleStep(0.05)
            inp_thresh.setValue(config.get("confidence_threshold", 0.65))
            inp_thresh.valueChanged.connect(lambda v: self._update_config("confidence_threshold", v))
            self.props_layout.addRow("Conf. Threshold", inp_thresh)
            
        elif n_type == "click":
            combo = QComboBox()
            combo.addItems(["click", "double_click", "right_click"])
            combo.setCurrentText(config.get("click_type", "click"))
            combo.currentTextChanged.connect(lambda t: self._update_config("click_type", t))
            self.props_layout.addRow("Click Type", combo)
            
            # Simple X Y handling could go here
            
        elif n_type == "wait":
            spin = QDoubleSpinBox()
            spin.setRange(0, 3600)
            spin.setValue(config.get("seconds", 1.0))
            spin.valueChanged.connect(lambda v: self._update_config("seconds", v))
            self.props_layout.addRow("Wait (sec)", spin)
            
        elif n_type == "wait_for_image":
            inp_path = QLineEdit(config.get("template_path", ""))
            inp_path.setPlaceholderText("path/to/image.png")
            inp_path.textChanged.connect(lambda t: self._update_config("template_path", t))
            self.props_layout.addRow("Template Path", inp_path)
            
            inp_thresh = QDoubleSpinBox()
            inp_thresh.setRange(0, 1)
            inp_thresh.setSingleStep(0.05)
            inp_thresh.setValue(config.get("match_threshold", 0.8))
            inp_thresh.valueChanged.connect(lambda v: self._update_config("match_threshold", v))
            self.props_layout.addRow("Threshold", inp_thresh)

        # Add generic JSON dump for anything else
        lbl = QLabel("Raw Config:")
        lbl.setStyleSheet("margin-top: 10px; color: var(--text-secondary);")
        self.props_layout.addRow(lbl)
        
        raw_inp = QLineEdit(json.dumps(config))
        # Use a local reference to avoid member shadowing issues
        raw_inp.editingFinished.connect(lambda: self._save_raw_config_obj(raw_inp))
        self.props_layout.addRow(raw_inp)

    def _update_config(self, key: str, value):
        if not self.selected_node_id: return
        config = self.selected_node_data.get("config", {})
        config[key] = value
        self.selected_node_data["config"] = config
        # We don't sync back to the raw JSON field here to avoid complexity
        # and potential recursion/crash since that field is recreated on every select.
        self.canvas.update_node_data(self.selected_node_id, self.selected_node_data)

    def _save_raw_config_obj(self, widget: QLineEdit):
        if not self.selected_node_id: return
        try:
            val = json.loads(widget.text())
            if isinstance(val, dict):
                self.selected_node_data["config"] = val
                self.canvas.update_node_data(self.selected_node_id, self.selected_node_data)
        except json.JSONDecodeError:
            pass # Invalid JSON, ignore

    def on_prop_changed(self):
        if not self.selected_node_id or not hasattr(self, "_inp_label"): return
        self.selected_node_data["label"] = self._inp_label.text()
        self.canvas.update_node_data(self.selected_node_id, self.selected_node_data)

    def on_delete_node(self):
        if self.selected_node_id:
            self.canvas.delete_node(self.selected_node_id)
            self.selected_node_id = None
            self.selected_node_data = None
            self.inspector_stack.setCurrentIndex(1) # Back to macro settings

    def on_delete_connection(self):
        if self.selected_conn:
            # Tell canvas to remove this connection
            self.canvas.scene.removeItem(self.selected_conn)
            if self.selected_conn in self.canvas.scene.connections:
                self.canvas.scene.connections.remove(self.selected_conn)
            self.selected_conn = None
            self.inspector_stack.setCurrentIndex(1) # Back to macro settings

    # ── FILE IO ──

    def action_new_macro(self):
        self.current_macro_id = None
        self.input_macro_name.setText("Unnamed Macro")
        self.input_macro_desc.setText("")
        self.canvas.clear()
        self.inspector_stack.setCurrentIndex(1)

    def action_save_macro(self):
        # Sync any globals
        self._sync_macro_settings()
        
        pipeline_data = self.canvas.get_pipeline_json()
        payload = {
            "id": self.current_macro_id,
            "name": self.current_macro_name,
            "description": self.current_macro_desc,
            "nodes": pipeline_data.get("nodes", []),
            "connections": pipeline_data.get("connections", [])
        }
        
        success = save_macro(payload)
        if success:
            self.current_macro_id = payload.get("id")
            QMessageBox.information(self, "Saved", "Macro saved successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to save macro.")

    def load_macro(self, macro_id: str):
        payload = load_macro(macro_id)
        if payload:
            self.current_macro_id = payload.get("id")
            # Set values manually before setText to ensure immediate sync
            self.current_macro_name = payload.get("name", "Unnamed Macro")
            self.current_macro_desc = payload.get("description", "")
            
            # Update inputs (might trigger signals, but we already set the state)
            self.input_macro_name.setText(self.current_macro_name)
            self.input_macro_desc.setText(self.current_macro_desc)
            
            # Update canvas and UI (pass full payload for connections)
            self.canvas.load_pipeline_json(payload)
            self.inspector_stack.setCurrentIndex(1)
            self.lbl_title.setText(f"Editing: {self.current_macro_name}")
            logger.info(f"Loaded macro {macro_id} successfully.")
        else:
            logger.error(f"Failed to load macro {macro_id}")
