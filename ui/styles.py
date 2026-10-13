"""
Unified design system for the POS desktop application.
Applies a professional, readable, and consistent UX across all pages.
"""

import json
import os
import sys
from pathlib import Path


DARK_COLORS = {
    # Surfaces
    "bg_app": "#070D1A",
    "bg_panel": "#0F172A",
    "bg_elevated": "#17233B",
    "bg_input": "#101B31",

    # Brand and feedback
    "primary": "#2F6BFF",
    "primary_hover": "#2457D6",
    "success": "#17A65A",
    "success_hover": "#128547",
    "warning": "#E18409",
    "warning_hover": "#B96805",
    "danger": "#E23B3B",
    "danger_hover": "#B92828",
    "info": "#0EA5C6",
    "info_hover": "#0C85A0",

    # Text and borders
    "text_primary": "#EEF4FF",
    "text_secondary": "#AAB8D0",
    "text_muted": "#71819C",
    "text_dark": "#0F172A",
    "text_light": "#FFFFFF",
    "text_on_brand": "#FFFFFF",
    "border": "#263957",
    "border_soft": "#1A2942",

    # States
    "focus_ring": "#77B7FF",
    "selection": "rgba(37, 99, 235, 0.25)",
    "hover_surface": "#1C2C48",

    # Compatibility aliases (kept to avoid breakage in existing pages)
    "accent": "#16A34A",
    "accent_hover": "#15803D",
    "secondary": "#475569",
    "hover": "#334155",
    "purple": "#8B5CF6",
    "purple_hover": "#7C3AED",
    "gray": "#475569",
    "gray_hover": "#64748B",
    "bg_main": "#070D1A",
}

LIGHT_COLORS = {
    "bg_app": "#F7F3EA",
    "bg_panel": "#FBF8F1",
    "bg_elevated": "#EFE8DA",
    "bg_input": "#FFFDF7",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "success": "#16A34A",
    "success_hover": "#15803D",
    "warning": "#D97706",
    "warning_hover": "#B45309",
    "danger": "#DC2626",
    "danger_hover": "#B91C1C",
    "info": "#0891B2",
    "info_hover": "#0E7490",
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#64748B",
    "text_dark": "#0F172A",
    "text_light": "#0F172A",
    "text_on_brand": "#FFFFFF",
    "border": "#D9CCB8",
    "border_soft": "#E8DDCE",
    "focus_ring": "#2563EB",
    "selection": "rgba(37, 99, 235, 0.18)",
    "hover_surface": "#F0E8DA",
    "accent": "#16A34A",
    "accent_hover": "#15803D",
    "secondary": "#64748B",
    "hover": "#E2E8F0",
    "purple": "#7C3AED",
    "purple_hover": "#6D28D9",
    "gray": "#64748B",
    "gray_hover": "#475569",
    "bg_main": "#F7F3EA",
}

THEME_MODES = {
    "dark": "الوضع الداكن",
    "light": "الوضع النهاري",
}


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def theme_preferences_path() -> Path:
    configured = os.getenv("POS_UI_PREFERENCES_FILE")
    if configured:
        return Path(configured)
    return _runtime_base_dir() / "assets" / "ui_preferences.json"


def normalize_theme_mode(mode: str | None) -> str:
    value = (mode or "").strip().lower()
    return value if value in THEME_MODES else "dark"


def load_theme_preference(default: str = "dark") -> str:
    path = theme_preferences_path()
    try:
        if not path.exists():
            return normalize_theme_mode(default)
        data = json.loads(path.read_text(encoding="utf-8"))
        return normalize_theme_mode(data.get("theme_mode", default))
    except Exception:
        return normalize_theme_mode(default)


def save_theme_preference(mode: str) -> None:
    path = theme_preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"theme_mode": normalize_theme_mode(mode)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


_THEME_MODE = load_theme_preference()
COLORS = dict(LIGHT_COLORS if _THEME_MODE == "light" else DARK_COLORS)


def _theme_value(dark: str, light: str) -> str:
    return light if _THEME_MODE == "light" else dark


def current_theme_mode() -> str:
    return _THEME_MODE


def apply_theme_mode(mode: str) -> str:
    global _THEME_MODE
    _THEME_MODE = normalize_theme_mode(mode)
    COLORS.clear()
    COLORS.update(LIGHT_COLORS if _THEME_MODE == "light" else DARK_COLORS)
    save_theme_preference(_THEME_MODE)
    return _THEME_MODE

FONTS = {
    "main": '"Tahoma", "Segoe UI", "Arial"',
}


def _btn(bg: str, bg_hover: str, text: str = COLORS["text_on_brand"], border: str = "transparent") -> str:
    return f"""
        QPushButton {{
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 7px 14px;
            min-height: 32px;
            font-size: 12px;
            font-weight: 800;
        }}
        QPushButton:hover {{
            background-color: {bg_hover};
            border-color: rgba(255, 255, 255, 0.12);
        }}
        QPushButton:pressed {{
            margin-top: 1px;
        }}
        QPushButton:disabled {{
            background-color: {COLORS['bg_elevated']};
            color: {COLORS['text_muted']};
            border-color: {COLORS['border_soft']};
        }}
    """


BUTTON_STYLES = {
    "primary": _btn(COLORS["primary"], COLORS["primary_hover"]),
    "success": _btn(COLORS["success"], COLORS["success_hover"]),
    "danger": _btn(COLORS["danger"], COLORS["danger_hover"]),
    "warning": _btn(COLORS["warning"], COLORS["warning_hover"]),
    "info": _btn(COLORS["info"], COLORS["info_hover"]),
    "secondary": _btn(COLORS["secondary"], COLORS["hover"]),
    "purple": _btn(COLORS["purple"], COLORS["purple_hover"]),
    "gray": _btn(COLORS["gray"], COLORS["gray_hover"]),
    "outline": f"""
        QPushButton {{
            background-color: {_theme_value('rgba(15, 26, 48, 0.35)', '#FFFDF7')};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 7px 14px;
            min-height: 32px;
            font-size: 12px;
            font-weight: 800;
        }}
        QPushButton:hover {{
            background-color: {COLORS['hover_surface']};
            border-color: {COLORS['focus_ring']};
        }}
        QPushButton:pressed {{
            margin-top: 1px;
        }}
    """,
}


def get_icon_button_style(color_key: str) -> str:
    color_map = {
        "danger": (COLORS["danger"], COLORS["danger_hover"]),
        "warning": (COLORS["warning"], COLORS["warning_hover"]),
        "success": (COLORS["success"], COLORS["success_hover"]),
        "primary": (COLORS["primary"], COLORS["primary_hover"]),
    }
    bg, hover = color_map.get(color_key, color_map["primary"])
    return f"""
        QPushButton {{
            background-color: {bg};
            color: {COLORS['text_on_brand']};
            border: none;
            border-radius: 7px;
            min-width: 26px;
            max-width: 26px;
            min-height: 26px;
            max-height: 26px;
            font-size: 13px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
    """


TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {COLORS['bg_panel']};
        alternate-background-color: {_theme_value('#172744', '#F1EBDD')};
        color: {COLORS['text_primary']};
        gridline-color: {COLORS['border']};
        border: 1px solid {COLORS['border']};
        border-radius: 14px;
        selection-background-color: {COLORS['primary']};
        selection-color: {COLORS['text_on_brand']};
        font-size: 12px;
        outline: none;
    }}
    QHeaderView::section {{
        background-color: {_theme_value('#182642', '#E7DDCC')};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-bottom: 1px solid {COLORS['border']};
        padding: 11px 8px;
        font-size: 12px;
        font-weight: 900;
    }}
    QTableWidget::item {{
        padding: 6px;
        border-right: 1px solid {COLORS['border_soft']};
        border-bottom: 1px solid {COLORS['border_soft']};
    }}
    QTableWidget::item:alternate {{
        background-color: {_theme_value('#172744', '#F1EBDD')};
    }}
    QTableWidget::item:selected {{
        background-color: {COLORS['primary']};
        color: {COLORS['text_on_brand']};
    }}
"""


INPUT_STYLE = f"""
    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QTextEdit, QDateEdit {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 7px 11px;
        min-height: 38px;
        font-size: 12px;
    }}
    QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus, QDateEdit:focus {{
        border: 1px solid {COLORS['focus_ring']};
    }}
    QLineEdit::placeholder, QTextEdit {{
        color: {COLORS['text_muted']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_panel']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['selection']};
        selection-color: {COLORS['text_on_brand']};
    }}
    QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        width: 0px;
        height: 0px;
        border: none;
    }}
    QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled {{
        background-color: {COLORS['bg_elevated']};
        color: {COLORS['text_muted']};
    }}
"""


GROUP_BOX_STYLE = f"""
    QGroupBox {{
        background-color: {COLORS['bg_panel']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        margin-top: 16px;
        padding: 14px;
        font-weight: 900;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 2px 8px;
        color: {COLORS['text_secondary']};
        background-color: {COLORS['bg_app']};
        border-radius: 6px;
    }}
"""


TAB_STYLE = f"""
    QTabWidget::pane {{
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        top: -1px;
        background-color: {COLORS['bg_app']};
    }}
    QTabBar::tab {{
        background-color: {COLORS['bg_panel']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-bottom: none;
        border-top-left-radius: 11px;
        border-top-right-radius: 11px;
        padding: 10px 18px;
        margin-right: 4px;
        font-size: 12px;
        font-weight: 900;
        min-height: 28px;
    }}
    QTabBar::tab:selected {{
        color: {COLORS['text_on_brand']};
        background-color: {COLORS['primary']};
        border-color: {COLORS['primary']};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {COLORS['hover_surface']};
        color: {COLORS['text_primary']};
    }}
"""


CARD_STYLE = f"""
    QFrame#ProductCard {{
        background-color: {COLORS['bg_panel']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 10px;
    }}
    QFrame#ProductCard:hover {{
        border-color: {COLORS['focus_ring']};
        background-color: {COLORS['hover_surface']};
    }}
    QLabel#CardTitle {{
        color: {COLORS['text_primary']};
        font-size: 13px;
        font-weight: 700;
    }}
    QLabel#CardPrice {{
        color: {COLORS['success']};
        font-size: 14px;
        font-weight: 800;
    }}
"""


LABEL_STYLE_HEADER = f"color: {COLORS['text_on_brand']}; font-size: 22px; font-weight: 800;"
LABEL_STYLE_TITLE = f"color: {COLORS['text_secondary']}; font-size: 14px; font-weight: 600;"


GLOBAL_STYLE = f"""
    * {{
        font-family: {FONTS['main']};
        outline: none;
    }}

    QWidget {{
        background-color: {COLORS['bg_app']};
        color: {COLORS['text_primary']};
        font-size: 12px;
    }}

    QMainWindow, QDialog {{
        background-color: {COLORS['bg_app']};
    }}

    QLabel {{
        color: {COLORS['text_primary']};
    }}

    QMenuBar {{
        background-color: {COLORS['bg_panel']};
        color: {COLORS['text_primary']};
        border-bottom: 1px solid {COLORS['border']};
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 6px 10px;
    }}
    QMenuBar::item:selected {{
        background-color: {COLORS['hover_surface']};
        border-radius: 6px;
    }}
    QMenu {{
        background-color: {COLORS['bg_panel']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
    }}
    QMenu::item:selected {{
        background-color: {COLORS['selection']};
    }}

    QPushButton {{
        background-color: {COLORS['primary']};
        color: {COLORS['text_on_brand']};
        border: none;
        border-radius: 10px;
        padding: 7px 14px;
        min-height: 32px;
        font-size: 12px;
        font-weight: 800;
    }}
    QPushButton:hover {{
        background-color: {COLORS['primary_hover']};
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_elevated']};
        color: {COLORS['text_muted']};
    }}

    {TABLE_STYLE}
    {INPUT_STYLE}
    {TAB_STYLE}
    {GROUP_BOX_STYLE}
    {CARD_STYLE}

    QCheckBox {{
        color: {COLORS['text_secondary']};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {COLORS['border']};
        background-color: {COLORS['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLORS['primary']};
        border-color: {COLORS['primary']};
    }}

    QScrollArea {{
        border: none;
        background-color: transparent;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {_theme_value('#33486B', '#CBBDA9')};
        min-height: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS['focus_ring']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {_theme_value('#33486B', '#CBBDA9')};
        min-width: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {COLORS['focus_ring']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: none;
    }}

    QMessageBox {{
        background-color: {COLORS['bg_panel']};
    }}
    QMessageBox QLabel {{
        color: {COLORS['text_primary']};
        font-size: 13px;
    }}
"""


def get_button_style(btn_type: str = "primary") -> str:
    return BUTTON_STYLES.get(btn_type, BUTTON_STYLES["primary"])


PANEL_STYLE = f"""
    QFrame#LeftPanel, QFrame#RightPanel {{
        background-color: {COLORS['bg_panel']};
        border: 1px solid {COLORS['border']};
        border-radius: 18px;
    }}
"""


TOTAL_DISPLAY_STYLE = f"""
    QLabel {{
        color: {COLORS['text_on_brand']};
        background-color: {COLORS['primary']};
        border: 1px solid {COLORS['primary_hover']};
        border-radius: 10px;
        padding: 12px;
        font-weight: 800;
        font-size: 14px;
    }}
"""


ACTION_BUTTON_STYLE = f"""
    QPushButton {{
        border-radius: 12px;
        font-weight: 700;
        color: {COLORS['text_on_brand']};
        border: none;
        min-height: 30px;
    }}
    QPushButton:pressed {{
        margin-top: 1px;
    }}
"""
