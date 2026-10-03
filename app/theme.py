"""
All colors, fonts, and QSS stylesheet.
Matches the LiquidityAI screenshot exactly.
Dark navy theme with purple/violet accents.
"""

# ── COLOR PALETTE ────────────────────────────────────────────────────
C = {
    # Backgrounds
    "bg_darkest":  "#0b0e1a",   # main window background
    "bg_sidebar":  "#0d1021",   # left sidebar
    "bg_panel":    "#141828",   # cards and panels
    "bg_card":     "#1a1f35",   # model cards
    "bg_input":    "#0d1021",   # input fields, terminal
    "bg_tab":      "#111525",   # tab bar background

    # Borders
    "border":      "#1e2440",
    "border_b":    "#2a3158",

    # Accents
    "purple":      "#7c3aed",   # primary accent
    "purple_l":    "#8b5cf6",   # light purple
    "purple_d":    "#5b21b6",   # dark purple
    "violet":      "#6d28d9",   # violet
    "pink":        "#db2777",   # pink accent
    "orange":      "#f59e0b",   # logo/warning color
    "green":       "#10b981",   # confident/success
    "amber":       "#f59e0b",   # training/warning
    "red":         "#ef4444",   # error
    "cyan":        "#06b6d4",   # info

    # Text
    "text":        "#8892b0",   # body text
    "text_b":      "#ccd6f6",   # bright text
    "text_d":      "#4a5480",   # muted text
    "text_muted":  "#4a5480",   # 10/10: Mapping for UI components
    "white":       "#e6f1ff",   # headings

    # Nav active
    "nav_active_bg": "#1e2a4a",
    "nav_active_border": "#7c3aed",

    # Status
    "status_confident": "#10b981",
    "status_training":  "#f59e0b",
    "status_error":     "#ef4444",
    "status_idle":      "#4a5480",
}

FONT_MONO = "Consolas"
FONT_UI   = "Segoe UI"

QSS = f"""
/* ── GLOBAL ─────────────────────────────────────────────────────── */
* {{
    font-family: "{FONT_UI}";
}}

QMainWindow, QWidget {{
    background-color: {C['bg_darkest']};
    color: {C['text_b']};
    font-family: "{FONT_UI}";
    font-size: 13px;
    outline: none;
}}

/* ── SCROLLBAR ───────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {C['bg_darkest']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {C['border_b']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── SIDEBAR ─────────────────────────────────────────────────────── */
#sidebar {{
    background-color: {C['bg_sidebar']};
    border-right: 1px solid {C['border']};
    min-width: 210px;
    max-width: 210px;
}}

/* ── NAV BUTTONS ─────────────────────────────────────────────────── */
#nav_btn {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    color: {C['text']};
    font-size: 13px;
    font-family: "{FONT_UI}";
    text-align: left;
    padding: 11px 16px 11px 14px;
}}
QPushButton#nav_btn:hover {{
    background-color: {C['nav_active_bg']}66;
    color: {C['white']};
}}
QPushButton#nav_btn[active="true"] {{
    background-color: {C['nav_active_bg']};
    color: {C['white']};
    border-left: 3px solid {C['nav_active_border']};
}}

/* Sub-nav button */
QPushButton#nav_sub_btn {{
    background: transparent;
    color: {C['text']};
    text-align: left;
    padding-left: 48px;
    border: none;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#nav_sub_btn:hover {{
    color: {C['purple_l']};
    background: {C['bg_sidebar']};
}}

/* Arrow toggle */
QPushButton#nav_arrow {{
    background: transparent;
    border: none;
    color: {C['text_d']};
    font-size: 14px;
    font-weight: bold;
}}
QPushButton#nav_arrow:hover {{
    color: {C['white']};
}}
/* The original #nav_btn[active=true] had font-weight: 600; which is now applied to the new active state. */
/* The original #nav_btn:hover had different styles, which are now updated. */

/* ── CONTENT AREA ────────────────────────────────────────────────── */
#content_area {{
    background-color: {C['bg_darkest']};
}}

/* ── PAGE TITLE ──────────────────────────────────────────────────── */
#page_title {{
    font-size: 22px;
    font-weight: 700;
    color: {C['white']};
    font-family: "{FONT_UI}";
}}

/* ── TABS ────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {C['border']};
    background: {C['bg_panel']};
    border-radius: 0px 4px 4px 4px;
}}
QTabBar::tab {{
    background: transparent;
    color: {C['text']};
    padding: 8px 20px;
    font-size: 13px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {C['white']};
    border-bottom: 3px solid {C['purple']};
    background: {C['bg_panel']};
    font-weight: 700;
}}
QTabBar::tab:hover:!selected {{
    color: {C['text_b']};
    border-bottom: 2px solid {C['purple_d']};
}}

/* ── MODEL CARD ──────────────────────────────────────────────────── */
#model_card {{
    background-color: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 14px;
}}
#model_card:hover {{
    border-color: {C['purple_l']};
    background-color: {C['bg_panel']};
}}

/* ── BUTTONS ─────────────────────────────────────────────────────── */
    QPushButton#model_action_btn {{
        background: #1a1f35;
        color: #06b6d4;
        border: 1px solid #2a3158;
        border-radius: 8px;
        font-size: 15px;
        font-weight: bold;
    }}
    QPushButton#model_action_btn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #06b6d433, stop:1 #06b6d411);
        color: white;
        border: 1px solid #06b6d4;
    }}
    QPushButton#model_action_btn:pressed {{
        background: #06b6d444;
    }}
    
    QPushButton#model_action_btn_danger {{
        background: #1a1f35;
        color: #ef4444;
        border: 1px solid #2a3158;
        border-radius: 8px;
        font-size: 15px;
        font-weight: bold;
    }}
    QPushButton#model_action_btn_danger:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef444433, stop:1 #ef444411);
        color: white;
        border: 1px solid #ef4444;
    }}
    QPushButton#model_action_btn_danger:pressed {{
        background: #ef444444;
    }}
#btn_cpu {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f46e5, stop:1 #7c3aed);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    font-family: "{FONT_UI}";
}}
#btn_cpu:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:1 #8b5cf6);
}}
#btn_cpu:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4338ca, stop:1 #6d28d9);
}}

#btn_gpu {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c3aed, stop:1 #db2777);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    font-family: "{FONT_UI}";
}}
#btn_gpu:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #8b5cf6, stop:1 #ec4899);
}}
#btn_gpu:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6d28d9, stop:1 #be185d);
}}

#btn_stop {{
    background-color: #2a2e42;
    color: {C['text']};
    border: 1px solid {C['border_b']};
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    font-family: "{FONT_UI}";
}}
#btn_stop:hover {{
    background-color: #353a52;
    color: {C['text_b']};
}}

#btn_primary {{
    background-color: {C['purple']};
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 18px;
}}
#btn_primary:hover {{ background-color: {C['purple_l']}; }}

#btn_secondary {{
    background-color: transparent;
    color: {C['purple_l']};
    border: 1px solid {C['purple_d']};
    border-radius: 6px;
    font-size: 13px;
    padding: 7px 16px;
}}
#btn_secondary:hover {{
    background-color: {C['nav_active_bg']};
    border-color: {C['purple']};
}}

#btn_danger {{
    background-color: #3f1515;
    color: {C['red']};
    border: 1px solid #7f1d1d;
    border-radius: 6px;
    font-size: 13px;
    padding: 7px 16px;
}}
#btn_danger:hover {{ background-color: #4f1a1a; }}

#btn_save {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {C['purple']}, stop:1 {C['violet']});
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    font-family: "{FONT_UI}";
}}
#btn_save:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {C['purple_l']}, stop:1 {C['purple']});
}}
#btn_save:pressed {{
    background: {C['purple_d']};
}}

/* ── TERMINAL ────────────────────────────────────────────────────── */
#terminal {{
    background-color: {C['bg_input']};
    color: #64748b;
    border: 1px solid {C['border']};
    border-radius: 6px;
    font-family: "{FONT_MONO}";
    font-size: 12px;
    padding: 10px;
}}

/* ── INPUT FIELDS ────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {C['bg_input']};
    color: {C['text_b']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: {C['purple_d']};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {C['purple']};
}}

/* ── COMBO BOX ───────────────────────────────────────────────────── */
QComboBox {{
    background-color: {C['bg_input']};
    color: {C['text_b']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
    min-width: 160px;
}}
QComboBox:focus {{ border-color: {C['purple']}; }}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {C['bg_panel']};
    color: {C['text_b']};
    border: 1px solid {C['border_b']};
    selection-background-color: {C['purple_d']};
}}

/* ── CHECKBOX ────────────────────────────────────────────────────── */
QCheckBox, QRadioButton {{
    color: {C['text_b']};
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {C['border_b']};
    border-radius: 3px;
    background: {C['bg_input']};
}}
QCheckBox::indicator:checked {{
    background: {C['purple']};
    border-color: {C['purple']};
}}

/* ── SLIDER ──────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {C['border']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {C['purple']};
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}}
QSlider::sub-page:horizontal {{
    background: {C['purple']};
    border-radius: 2px;
}}

/* ── LABELS ──────────────────────────────────────────────────────── */
#label_section {{
    color: {C['text_d']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}}
#label_value {{
    color: {C['white']};
    font-size: 20px;
    font-weight: 700;
    font-family: "{FONT_MONO}";
}}
#label_muted {{
    color: {C['text_d']};
    font-size: 11px;
}}

/* ── PROGRESS BAR ────────────────────────────────────────────────── */
QProgressBar {{
    background: {C['border']};
    border-radius: 2px;
    height: 4px;
    text-align: center;
    font-size: 1px;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {C['purple']};
    border-radius: 2px;
}}

/* ── SEPARATOR ───────────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {C['border']};
}}

/* ── GROUP BOX ───────────────────────────────────────────────────── */
QGroupBox {{
    color: {C['text_d']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    border: 1px solid {C['border']};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    background: {C['bg_panel']};
    color: {C['text_d']};
}}

/* ── TOOLTIP ─────────────────────────────────────────────────────── */
QToolTip {{
    background: {C['bg_panel']};
    color: {C['text_b']};
    border: 1px solid {C['border_b']};
    padding: 4px 8px;
    border-radius: 4px;
}}

/* ── SPLITTER ────────────────────────────────────────────────────── */
QSplitter::handle {{
    background: {C['border']};
    width: 1px;
    height: 1px;
}}
"""
