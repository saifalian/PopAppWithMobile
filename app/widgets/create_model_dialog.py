from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QCheckBox, QPushButton, 
                             QFrame, QGridLayout, QWidget, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from app.theme import C, FONT_UI

class CreateModelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(700, 800)
        self._setup_ui()
        self._validate_input()

    def _setup_ui(self):
        # Outer container with border and background
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("main_frame")
        self.main_frame.setStyleSheet(f"""
            #main_frame {{
                background-color: {C['bg_sidebar']};
                border: 1px solid {C['border_b']};
                border-radius: 12px;
            }}
        """)
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.main_frame)
        
        layout = QVBoxLayout(self.main_frame)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Header
        header = QHBoxLayout()
        title = QLabel("CREATE NEW MODEL")
        title.setStyleSheet(f"color: {C['white']}; font-size: 16px; font-weight: 800; letter-spacing: 1px;")
        header.addWidget(title)
        header.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ 
                color: {C['text_d']}; 
                border: none; 
                background: transparent; 
                font-size: 20px; 
            }}
            QPushButton:hover {{ color: {C['white']}; }}
        """)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Scroll Area for content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 10, 0) # Small margin for scrollbar
        self.scroll_layout.setSpacing(24)

        # Model Name
        self.scroll_layout.addWidget(self._create_label("MODEL NAME"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. click_clusters")
        self.name_input.setMinimumHeight(45)
        self.name_input.setStyleSheet(self._input_style())
        self.name_input.textChanged.connect(self._validate_input)
        self.scroll_layout.addWidget(self.name_input)
        
        # Folder Preview Label
        self.folder_preview = QLabel("Created folder:  models/...")
        self.folder_preview.setStyleSheet(f"color: {C['cyan']}; font-size: 10px; font-style: italic; margin-top: -15px; margin-bottom: 10px;")
        self.scroll_layout.addWidget(self.folder_preview)

        # Description
        self.scroll_layout.addWidget(self._create_label("DESCRIPTION"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("What does this model do?")
        self.desc_input.setMaximumHeight(100)
        self.desc_input.setStyleSheet(self._input_style())
        self.scroll_layout.addWidget(self.desc_input)

        # Task Type
        self.scroll_layout.addWidget(self._create_label("TASK TYPE (check all that apply)"))
        task_grid = QGridLayout()
        task_grid.setSpacing(10)
        tasks = [
            "Visual Detection", "Click / Navigation", "Data Extraction",
            "Settings Adjustment", "Yes / No Decision", "Sequence of Actions"
        ]
        self.task_checks = []
        for i, text in enumerate(tasks):
            chk = self._create_checkbox(text)
            chk.stateChanged.connect(self._validate_input)
            self.task_checks.append(chk)
            task_grid.addWidget(chk, i // 3, i % 3)
        self.scroll_layout.addLayout(task_grid)

        # Output Type
        self.scroll_layout.addWidget(self._create_label("OUTPUT TYPE (check all that apply)"))
        output_grid = QGridLayout()
        output_grid.setSpacing(10)
        outputs = [
            "Click coordinates (x,y)", "Swipe / Drag", "Scroll amount", "Keyboard input",
            "Type text", "Numeric value", "Yes / No", "Extracted text",
            "Ranked list", "Wait duration", "App action", "Conditional branch"
        ]
        self.output_checks = []
        for i, text in enumerate(outputs):
            chk = self._create_checkbox(text)
            self.output_checks.append(chk)
            output_grid.addWidget(chk, i // 4, i % 4)
        self.scroll_layout.addLayout(output_grid)

        # Footer hint
        footer_hint = QLabel("<b>Auto-creates:</b> models/model_name/<br/>"
                        "<span style='font-size: 10px; color: #4a5480;'>"
                        "reference/ · extracted/ · labeled/ · augmented/ · goals/ · checkpoints/ · best/ · logs/ · attempts/ · test_data/ · live_recordings/ · results/"
                        "</span>")
        footer_hint.setStyleSheet(f"color: {C['amber']}; font-size: 11px;")
        footer_hint.setWordWrap(True)
        
        footer_frame = QFrame()
        footer_frame.setStyleSheet(f"background: {C['bg_darkest']}; border: 1px solid {C['border']}; border-radius: 6px;")
        fl = QVBoxLayout(footer_frame)
        fl.addWidget(footer_hint)
        self.scroll_layout.addWidget(footer_frame)

        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        # Action Buttons (Fixed at bottom)
        actions = QHBoxLayout()
        actions.addStretch()
        
        cancel = QPushButton("Cancel")
        cancel.setFixedSize(100, 36)
        cancel.setStyleSheet(f"color: {C['text']}; border: none; background: transparent; font-weight: 600;")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        
        self.create_btn = QPushButton("Create Model")
        self.create_btn.setFixedSize(150, 36)
        self.create_btn.setEnabled(False)
        self.create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['purple']};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {C['purple_l']}; }}
            QPushButton:disabled {{ background-color: {C['bg_panel']}; color: {C['text_d']}; }}
        """)
        self.create_btn.clicked.connect(self._on_create_clicked)
        actions.addWidget(self.create_btn)
        layout.addLayout(actions)

    def _create_label(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text_d']}; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        return l

    def _create_checkbox(self, text):
        chk = QCheckBox(text)
        chk.setMinimumHeight(40)
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setStyleSheet(f"""
            QCheckBox {{
                background: {C['bg_panel']};
                color: {C['text_b']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                padding-left: 12px;
                font-size: 13px;
                spacing: 10px;
            }}
            QCheckBox:hover {{
                border-color: {C['border_b']};
                background: {C['nav_active_bg']}aa;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {C['border_b']};
                border-radius: 3px;
                background: {C['bg_darkest']};
            }}
            QCheckBox::indicator:checked {{
                background: {C['purple']};
                border-color: {C['purple']};
                image: none; /* Add a check icon if desired */
            }}
        """)
        return chk

    def _input_style(self):
        return f"""
            background-color: {C['bg_darkest']};
            color: {C['white']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            padding: 12px;
            font-size: 14px;
        """

    def _validate_input(self):
        name = self.name_input.text().strip()
        has_task = any(c.isChecked() for c in self.task_checks)
        
        # Update Folder Preview
        if name:
            safe_name = "".join([c if c.isalnum() or c in ("_","-") else "_" for c in name])
            self.folder_preview.setText(f"Created folder: models/{safe_name}/")
        else:
            self.folder_preview.setText("Created folder:  models/...")
            
        is_valid = len(name) >= 3 and has_task
        self.create_btn.setEnabled(is_valid)

    def _on_create_clicked(self):
        from pathlib import Path
        name = self.name_input.text().strip()
        safe_name = "".join([c if c.isalnum() or c in ("_","-") else "_" for c in name])
        path = Path("models") / safe_name
        
        if path.exists():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Conflict", f"A model named '{safe_name}' already exists. Please choose a different name.")
            return
            
        self.accept()

    def get_data(self):
        name = self.name_input.text().strip()
        safe_name = "".join([c if c.isalnum() or c in ("_","-") else "_" for c in name])
        return {
            "name": safe_name,
            "description": self.desc_input.toPlainText(),
            "tasks": [c.text() for c in self.task_checks if c.isChecked()],
            "outputs": [c.text() for c in self.output_checks if c.isChecked()]
        }

class EditModelDialog(CreateModelDialog):
    """Subclass of CreateModelDialog specifically for editing existing models."""
    def __init__(self, model_name, config, parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self.config = config
        
        self._populate_existing()

    def _populate_existing(self):
        # Override Title
        for lbl in self.findChildren(QLabel):
            if lbl.text() == "CREATE NEW MODEL":
                lbl.setText("EDIT MODEL CONFIG")
                break
                
        # Lock name input
        self.name_input.setText(self.model_name)
        self.name_input.setReadOnly(True)
        self.name_input.setStyleSheet(self._input_style() + f"color: {C['text_d']}; background-color: {C['bg_card']};")
        self.name_input.setToolTip("Model name cannot be modified after creation to preserve directory structures.")
        
        # Populate description
        self.desc_input.setText(self.config.get("description", ""))
        
        # Populate checked task types
        tasks_in = self.config.get("tasks", [])
        for chk in self.task_checks:
            if chk.text() in tasks_in:
                chk.setChecked(True)
                
        # Populate checked outputs
        outputs_in = self.config.get("outputs", [])
        for chk in self.output_checks:
            if chk.text() in outputs_in:
                chk.setChecked(True)
                
        # Swap Save Button text
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Create Model":
                btn.setText("Save Changes")
                break
