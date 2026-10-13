from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QStackedWidget, QTabWidget

from ui.styles import COLORS, INPUT_STYLE


def create_subtab_dropdown(tab_widget: QTabWidget, title: str = "القسم") -> QFrame:
    """Create a compact dropdown controller for an internal QTabWidget."""
    tab_widget.tabBar().hide()

    combo = _create_combo()
    for index in range(tab_widget.count()):
        combo.addItem(tab_widget.tabText(index), index)

    combo.currentIndexChanged.connect(tab_widget.setCurrentIndex)
    tab_widget.currentChanged.connect(
        lambda index: combo.setCurrentIndex(index)
        if combo.currentIndex() != index and 0 <= index < combo.count()
        else None
    )

    return _create_dropdown_header(title, combo)


def create_stack_dropdown(
    stack_widget: QStackedWidget,
    titles: list[str],
    title: str = "القسم",
    on_changed=None,
) -> QFrame:
    """Create a dropdown controller for pages backed by QStackedWidget."""
    combo = _create_combo()
    for index, text in enumerate(titles):
        combo.addItem(text, index)

    def change_page(index: int):
        stack_widget.setCurrentIndex(index)
        if on_changed:
            on_changed(index)

    combo.currentIndexChanged.connect(change_page)
    return _create_dropdown_header(title, combo)


def _create_combo() -> QComboBox:
    combo = QComboBox()
    combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    combo.setMinimumWidth(280)
    combo.setMaximumWidth(420)
    combo.setStyleSheet(INPUT_STYLE)
    combo.setCursor(Qt.CursorShape.PointingHandCursor)
    return combo


def _create_dropdown_header(title: str, combo: QComboBox) -> QFrame:
    header = QFrame()
    header.setObjectName("SubtabDropdownHeader")
    header.setStyleSheet(
        f"""
        QFrame#SubtabDropdownHeader {{
            background-color: {COLORS['bg_panel']};
            border: 1px solid {COLORS['border']};
            border-radius: 14px;
        }}
        """
    )

    layout = QHBoxLayout(header)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(10)

    label = QLabel(title)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    label.setStyleSheet(
        f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 900;"
    )

    layout.addStretch()
    layout.addWidget(combo)
    layout.addWidget(label)
    return header
