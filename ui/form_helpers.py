"""
مساعدات موحدة للنماذج والحوارات داخل واجهة التطبيق.

الهدف هو جعل الحقول والأزرار وحوارات الإدخال متسقة في صفحات التشغيل اليومية
بدون تكرار CSS أو إعدادات Layout داخل كل صفحة.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.styles import COLORS, GLOBAL_STYLE, INPUT_STYLE, get_button_style


FORM_LABEL_STYLE = f"""
    QLabel {{
        color: {COLORS['text_primary']};
        font-size: 12px;
        font-weight: 700;
    }}
"""


def style_dialog(dialog: QDialog, width: int | None = None, min_width: int | None = None):
    dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    dialog.setStyleSheet(f"""
        {GLOBAL_STYLE}
        QDialog {{
            background-color: {COLORS['bg_panel']};
            color: {COLORS['text_primary']};
        }}
        {FORM_LABEL_STYLE}
    """)
    if width:
        dialog.setFixedWidth(width)
    if min_width:
        dialog.setMinimumWidth(min_width)


def scrollable_dialog_layout(
    dialog: QDialog,
    margins: tuple[int, int, int, int] = (14, 14, 14, 14),
    spacing: int = 12,
) -> tuple[QVBoxLayout, QVBoxLayout, QVBoxLayout]:
    dialog.setMinimumHeight(420)
    dialog.resize(max(dialog.width(), dialog.minimumWidth(), 620), min(720, dialog.height() or 720))

    root_layout = QVBoxLayout(dialog)
    root_layout.setContentsMargins(*margins)
    root_layout.setSpacing(spacing)

    scroll = QScrollArea(dialog)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet(f"""
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: {COLORS['bg_main']};
            width: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background: {COLORS['primary']};
            min-height: 36px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
            background: transparent;
        }}
    """)

    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(spacing)
    scroll.setWidget(content)

    footer_layout = QVBoxLayout()
    footer_layout.setContentsMargins(0, 0, 0, 0)
    footer_layout.setSpacing(8)

    root_layout.addWidget(scroll, 1)
    root_layout.addLayout(footer_layout, 0)
    return root_layout, content_layout, footer_layout


def configure_form_layout(layout: QFormLayout):
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)
    layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)


def style_form_controls(*widgets):
    for widget in widgets:
        if widget is None:
            continue
        widget.setStyleSheet(INPUT_STYLE)
        if isinstance(widget, (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit)):
            widget.setMinimumHeight(36)
        if isinstance(widget, QLineEdit):
            widget.setAlignment(Qt.AlignmentFlag.AlignRight)
            widget.setClearButtonEnabled(True)


def action_row(
    save_text: str = "حفظ",
    cancel_text: str = "إلغاء",
    save_style: str = "success",
    cancel_style: str = "outline",
) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
    layout = QHBoxLayout()
    layout.setContentsMargins(0, 8, 0, 0)
    layout.setSpacing(8)

    save_btn = QPushButton(save_text)
    save_btn.setStyleSheet(get_button_style(save_style))
    save_btn.setCursor(Qt.CursorShape.PointingHandCursor)

    cancel_btn = QPushButton(cancel_text)
    cancel_btn.setStyleSheet(get_button_style(cancel_style))
    cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)

    layout.addStretch()
    layout.addWidget(cancel_btn)
    layout.addWidget(save_btn)
    return layout, save_btn, cancel_btn


def numeric_text(line_edit: QLineEdit, default: float = 0.0) -> float:
    text = (
        line_edit.text()
        .strip()
        .replace("٬", "")
        .replace(",", ".")
        .replace("٫", ".")
    )
    return float(text) if text else default
