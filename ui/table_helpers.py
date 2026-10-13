"""
مساعدات موحدة للجداول وأزرار الإجراءات داخل صفحات التطبيق.

الهدف: تقليل تكرار تنسيق QTableWidget وأزرار الإجراءات، والحفاظ على شكل
واحد مناسب للتشغيل اليومي داخل السوبرماركت.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from ui.styles import COLORS, TABLE_STYLE


COMPACT_TABLE_BUTTON_COLORS = {
    "warning": (COLORS["warning"], COLORS["warning_hover"]),
    "info": (COLORS["info"], COLORS["info_hover"]),
    "danger": (COLORS["danger"], COLORS["danger_hover"]),
    "success": (COLORS["success"], COLORS["success_hover"]),
    "primary": (COLORS["primary"], COLORS["primary_hover"]),
    "secondary": (COLORS["secondary"], COLORS["hover"]),
}


def configure_table(table: QTableWidget, style: str = None, row_height: int = 52):
    table.setStyleSheet(style or TABLE_STYLE)
    table.setAlternatingRowColors(True)
    table.setShowGrid(True)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(row_height)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
    table.horizontalHeader().setHighlightSections(False)


def center_item(value) -> QTableWidgetItem:
    item = QTableWidgetItem("" if value is None else str(value))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return item


def set_center_item(table: QTableWidget, row: int, column: int, value):
    table.setItem(row, column, center_item(value))


def actions_cell(buttons: list[QPushButton]) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(3, 3, 3, 3)
    layout.setSpacing(6)
    layout.addStretch()
    for button in buttons:
        layout.addWidget(button)
    layout.addStretch()
    return widget


def table_action_button(text: str, style_key: str, callback=None) -> QPushButton:
    bg, hover = COMPACT_TABLE_BUTTON_COLORS.get(
        style_key,
        COMPACT_TABLE_BUTTON_COLORS["primary"],
    )
    button = QPushButton(text)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setStyleSheet(f"""
        QPushButton {{
            background-color: {bg};
            color: {COLORS['text_on_brand']};
            border: none;
            border-radius: 7px;
            padding: 2px 8px;
            min-height: 24px;
            max-height: 24px;
            font-size: 11px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:disabled {{
            background-color: {COLORS['bg_elevated']};
            color: {COLORS['text_muted']};
        }}
    """)
    button.setFixedHeight(26)
    button.setMinimumWidth(max(58, len(text) * 9))
    if callback:
        button.clicked.connect(callback)
    return button
