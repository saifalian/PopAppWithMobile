"""
Create New Model Dialog.
Handles identity, task classification, outputs, and auto folder creation.
"""
import os
import uuid
import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QCheckBox, QRadioButton, QButtonGroup,
    QTextEdit, QMessageBox, QScrollArea, QWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.theme import C, FONT_UI
from backend.database.models import ModelRecord
from backend.database.db import SessionLocal

class CreateModelDialog(QDialog):
    model_created = pyqtSignal(str) # Emits model ID on success

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Agent Model")
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        self.setStyleSheet(f"background: {C['bg_panel']}; color: {C['white']};")
        
        self.task_radios = {}
        self.output_checkboxes = {}
        
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # TITLE
        title = QLabel("Initialize New Vision Agent")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {C['purple']};")
        layout.addWidget(title)
        
        # SCROLL AREA
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {C['bg_panel']};")
        
        content = QWidget()
        clayout = QVBoxLayout(content)
        clayout.setSpacing(20)
        
        # ── IDENTITY ──────────────────────────────────────────────────
        id_group = QGroupBox("1. Identity & Metadata")
        id_group.setStyleSheet(f"QGroupBox {{ font-size: 14px; font-weight: bold; padding-top: 20px; border: 1px solid {C['border']}; border-radius: 4px;}}")
        il = QVBoxLayout(id_group)
        
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("e.g. my_trading_helper or social_bot")
        self.inp_name.setStyleSheet(f"background: {C['bg_darkest']}; padding: 8px; border: 1px solid {C['border_light']}; border-radius: 4px;")
        
        self.inp_desc = QTextEdit()
        self.inp_desc.setPlaceholderText("Describe the purpose and expected environment for this model...")
        self.inp_desc.setFixedHeight(60)
        self.inp_desc.setStyleSheet(f"background: {C['bg_darkest']}; padding: 8px; border: 1px solid {C['border_light']}; border-radius: 4px;")
        
        il.addWidget(QLabel("Model Name (Internal Identifier):"))
        il.addWidget(self.inp_name)
        il.addWidget(QLabel("Description:"))
        il.addWidget(self.inp_desc)
        clayout.addWidget(id_group)

        # ── TASK CLASSIFICATION ───────────────────────────────────────
        task_group = QGroupBox("2. Core Task Classification")
        task_group.setStyleSheet(f"QGroupBox {{ font-size: 14px; font-weight: bold; padding-top: 20px; border: 1px solid {C['border']}; border-radius: 4px;}}")
        tl = QVBoxLayout(task_group)
        self.task_bg = QButtonGroup(self)
        
        tasks = [
            ("visual_detection", "Visual Detection (Finding objects/patterns)"),
            ("click_navigation", "Click / Navigation (Interacting with UI)"),
            ("data_extraction", "Data Extraction (Reading text/values)"),
            ("decision_making", "Decision Making (Logic/Branching)"),
        ]
        
        for i, (tid, label) in enumerate(tasks):
            rb = QRadioButton(label)
            rb.setStyleSheet("font-weight: normal; font-size: 13px;")
            self.task_bg.addButton(rb, i)
            self.task_radios[tid] = rb
            tl.addWidget(rb)
            
        clayout.addWidget(task_group)

        # ── OUTPUT CAPABILITIES ───────────────────────────────────────
        out_group = QGroupBox("3. Action Output Capabilities (Select multiples)")
        out_group.setStyleSheet(f"QGroupBox {{ font-size: 14px; font-weight: bold; padding-top: 20px; border: 1px solid {C['border']}; border-radius: 4px;}}")
        ol = QVBoxLayout(out_group)
        
        outputs = [
            ("click_coords", "Click Coordinates (x, y)"),
            ("keyboard_input", "Keyboard Input"),
            ("scroll_amount", "Scroll / Drag Amount"),
            ("yes_no", "Yes / No classification"),
            ("extracted_text", "Extracted Text (OCR / Value)"),
            ("numeric", "Numeric Value Check"),
            ("conditional_branch", "Conditional Branch Target"),
            ("wait_duration", "Dynamic Wait Duration")
        ]
        
        for oid, label in outputs:
            cb = QCheckBox(label)
            cb.setStyleSheet("font-weight: normal; font-size: 13px;")
            self.output_checkboxes[oid] = cb
            ol.addWidget(cb)
            
        clayout.addWidget(out_group)
        clayout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # ── BUTTONS ───────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"background: transparent; color: {C['text']}; padding: 8px 16px; border: 1px solid {C['border']}; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        
        create_btn = QPushButton("Initialize Model & Folders")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(f"background: {C['violet']}; color: white; padding: 8px 16px; border: none; border-radius: 4px; font-weight: bold;")
        create_btn.clicked.connect(self._handle_create)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(create_btn)
        layout.addLayout(btn_layout)

    def _handle_create(self):
        name = self.inp_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Model Name is required.")
            return
            
        # Clean name
        clean_name = "".join(c if c.isalnum() or c in "_" else "_" for c in name).lower()
        
        # Check if exists
        model_dir = Path("models") / clean_name
        if model_dir.exists():
            QMessageBox.warning(self, "Conflict", f"A model named '{clean_name}' already exists.")
            return

        # Get Tasks
        selected_tasks = [tid for tid, rb in self.task_radios.items() if rb.isChecked()]
        if not selected_tasks:
            QMessageBox.warning(self, "Missing Task", "Please select a core task classification.")
            return
            
        # Get Outputs
        selected_outputs = [oid for oid, cb in self.output_checkboxes.items() if cb.isChecked()]
        if not selected_outputs:
            QMessageBox.warning(self, "Missing Outputs", "Please select at least one output capability.")
            return

        try:
            # 1. Create 14 folder structure
            self._create_folder_structure(model_dir)
            
            # 2. Add to database
            db = SessionLocal()
            model_id = str(uuid.uuid4())
            record = ModelRecord(
                id=model_id,
                name=clean_name,
                description=self.inp_desc.toPlainText().strip(),
                task_types=selected_tasks,
                output_types=selected_outputs,
                status="untrained",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # 3. Create config.json
            config_path = model_dir / "config.json"
            conf_data = {
                "id": model_id,
                "name": clean_name,
                "task_type": selected_tasks[0],
                "output_type": selected_outputs[0]
            }
            with open(config_path, "w") as f:
                json.dump(conf_data, f, indent=2)
                
            db.add(record)
            db.commit()
            db.close()
            
            self.model_created.emit(model_id)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create model: {e}")

    def _create_folder_structure(self, base_dir: Path):
        folders = [
            "reference",          # Static images used for comparison
            "extracted",          # Raw frames extracted from video
            "labeled",            # Where labels.json lives
            "augmented",          # Cached augmented variants
            "goals",              # Goal state screenshots
            "checkpoints",        # Auto-saved weights
            "best",               # Best weights only
            "logs",               # TensorBoard / metrics
            "attempts",           # Logs for every training attempt
            "test_data",          # The locked 5% split
            "live_recordings",    # Videos recorded by the user
            "results",            # Compiled dataset.npz
            "macros",             # Linked scripts
            "exports"             # SavedModel, ONNX, TFLite drops
        ]
        
        base_dir.mkdir(parents=True, exist_ok=True)
        for f in folders:
            (base_dir / f).mkdir(exist_ok=True)
