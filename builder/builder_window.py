"""
DeveloperBuilderWindow – the main Qt window for the Developer Builder tool.

Responsibilities handled here:
    - Feature / permission tree management
    - Preset application
    - Build orchestration (delegates actual work to ``BuildWorker``)
    - Profile save / load / preview
    - Build-history logging
    - Input validation (delegates rules to ``config``)

All static data lives in ``builder.config``.
All background work lives in ``builder.build_worker``.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from builder.build_worker import BuildWorker
from builder.config import (
    EDITION_PRESETS,
    FEATURE_GROUP_LABELS,
    PERMISSION_LABELS,
    ROLE_LABELS,
    sanitize_filename,
    validate_all,
)
from utils.permissions import ROLE_DEVELOPER, ROLE_ADMIN
from ui.styles import COLORS, GLOBAL_STYLE, INPUT_STYLE, get_button_style
from utils.feature_flags import FEATURE_CATALOG, CONFIG_FILE_NAME
from utils.permissions import ROLE_PERMISSIONS

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ────────────────────────────────────────────────────────────────────────────
# Main window
# ────────────────────────────────────────────────────────────────────────────

class DeveloperBuilderWindow(QMainWindow):
    """Developer-facing tool for producing customised client builds."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HyperPOS Developer Builder")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(1500, 900)
        self.setMinimumSize(1280, 760)
        self.setStyleSheet(GLOBAL_STYLE)

        # State
        self.feature_items: dict[str, QTreeWidgetItem] = {}
        self.feature_group_items: dict[str, QTreeWidgetItem] = {}
        self.permission_items: dict[int, dict[str, QTreeWidgetItem]] = {}
        self.feature_dialog: QDialog | None = None
        self.permissions_dialog: QDialog | None = None
        self.features_summary_label: QLabel | None = None
        self.permissions_summary_label: QLabel | None = None
        self.worker: BuildWorker | None = None

        self._build_ui()
        self._select_all()

    # ── UI construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header
        header = QLabel("أداة المطور لإنتاج نسخة عميل مخصصة")
        header.setFont(QFont("Arial", 26, QFont.Weight.Black))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"color: {COLORS['text_on_brand']}; padding: 14px;")
        layout.addWidget(header)

        # ── Meta form ───────────────────────────────────────────────────
        meta_box = QGroupBox("بيانات النسخة")
        meta_form = QFormLayout(meta_box)
        meta_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText("اسم العميل أو السوبرماركت")
        self.client_name_input.setStyleSheet(INPUT_STYLE)
        meta_form.addRow("اسم العميل:", self.client_name_input)

        self.app_name_input = QLineEdit("HyperPOS")
        self.app_name_input.setStyleSheet(INPUT_STYLE)
        meta_form.addRow("اسم ملف التطبيق:", self.app_name_input)

        preset_widget = QWidget()
        preset_layout = QHBoxLayout(preset_widget)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        self.edition_combo = QComboBox()
        for key, preset in EDITION_PRESETS.items():
            self.edition_combo.addItem(preset["label"], key)
        self.edition_combo.setStyleSheet(INPUT_STYLE)
        preset_layout.addWidget(self.edition_combo, 1)
        apply_preset_btn = QPushButton("تطبيق القالب")
        apply_preset_btn.setStyleSheet(get_button_style("warning"))
        apply_preset_btn.clicked.connect(self._apply_selected_preset)
        preset_layout.addWidget(apply_preset_btn)
        meta_form.addRow("قالب النسخة:", preset_widget)

        self.store_scope_combo = QComboBox()
        self.store_scope_combo.setStyleSheet(INPUT_STYLE)
        self._load_store_scope_choices()
        meta_form.addRow("فرع النسخة:", self.store_scope_combo)

        self.build_mode_combo = QComboBox()
        self.build_mode_combo.addItem("إنتاج ملف EXE بواسطة PyInstaller", "exe")
        self.build_mode_combo.setCurrentIndex(0)
        self.build_mode_combo.setStyleSheet(INPUT_STYLE)
        meta_form.addRow("طريقة الإنتاج:", self.build_mode_combo)
        layout.addWidget(meta_box)

        # ── Feature / permission trees (built but kept off-screen) ──────
        self.feature_tree = QTreeWidget()
        self.feature_tree.setHeaderLabels(["الصفحات والمميزات التفصيلية"])
        self.feature_tree.itemChanged.connect(self._on_feature_changed)
        self.feature_tree.itemChanged.connect(lambda *_: self._refresh_selector_summaries())
        self._populate_features()

        self.role_tree = QTreeWidget()
        self.role_tree.setHeaderLabels(["الصلاحيات حسب الدور"])
        self.role_tree.itemChanged.connect(lambda *_: self._refresh_selector_summaries())
        self._populate_roles()

        # ── Selector cards ──────────────────────────────────────────────
        selectors = QHBoxLayout()
        selectors.setSpacing(16)
        self.features_summary_label = QLabel()
        self.permissions_summary_label = QLabel()
        selectors.addWidget(
            self._selector_card(
                "اختيار الصفحات والمميزات",
                "افتح نافذة كبيرة لاختيار كل صفحة وكل ميزة صغيرة داخل التطبيق.",
                self.features_summary_label,
                "فتح اختيار المميزات",
                self._open_features_dialog,
            )
        )
        selectors.addWidget(
            self._selector_card(
                "اختيار صلاحيات المستخدمين",
                "افتح نافذة كبيرة لتحديد صلاحيات كل دور داخل النسخة المنتجة.",
                self.permissions_summary_label,
                "فتح اختيار الصلاحيات",
                self._open_permissions_dialog,
            )
        )
        layout.addLayout(selectors, 1)
        self._refresh_selector_summaries()

        # ── Action buttons ──────────────────────────────────────────────
        buttons = QHBoxLayout()

        select_all_btn = QPushButton("تحديد الكل")
        select_all_btn.setStyleSheet(get_button_style("success"))
        select_all_btn.clicked.connect(self._select_all)
        buttons.addWidget(select_all_btn)

        clear_btn = QPushButton("إلغاء الكل")
        clear_btn.setStyleSheet(get_button_style("danger"))
        clear_btn.clicked.connect(self._clear_all)
        buttons.addWidget(clear_btn)

        load_btn = QPushButton("تحميل إعدادات عميل")
        load_btn.setStyleSheet(get_button_style("purple"))
        load_btn.clicked.connect(self._load_config)
        buttons.addWidget(load_btn)

        save_btn = QPushButton("حفظ إعدادات العميل")
        save_btn.setStyleSheet(get_button_style("info"))
        save_btn.clicked.connect(self._save_config)
        buttons.addWidget(save_btn)

        preview_btn = QPushButton("معاينة الإعدادات")
        preview_btn.setStyleSheet(get_button_style("secondary"))
        preview_btn.clicked.connect(self._preview_config)
        buttons.addWidget(preview_btn)

        build_btn = QPushButton("إنتاج التطبيق")
        build_btn.setStyleSheet(get_button_style("primary"))
        build_btn.clicked.connect(self._produce_application)
        buttons.addWidget(build_btn)

        self.cancel_btn = QPushButton("إلغاء الإنتاج")
        self.cancel_btn.setStyleSheet(get_button_style("danger"))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_build)
        buttons.addWidget(self.cancel_btn)

        layout.addLayout(buttons)

        # ── Progress bar ────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("جاري الإنتاج... %p%")
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(28)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                text-align: center;
                color: {COLORS['text_on_brand']};
                font-weight: 900;
                font-size: 13px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 9px;
            }}
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # ── Log panel ───────────────────────────────────────────────────
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        self.log.setStyleSheet(
            f"background: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 12px; padding: 8px;"
        )
        layout.addWidget(self.log)

        self.setCentralWidget(root)

        # ── Status bar ──────────────────────────────────────────────────
        self.statusBar().setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 800;"
        )
        self._set_status("جاهز للإنتاج")

    # ── Selector card helper ────────────────────────────────────────────

    def _selector_card(
        self,
        title: str,
        description: str,
        summary_label: QLabel,
        button_text: str,
        callback,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("SelectorCard")
        card.setStyleSheet(f"""
            QFrame#SelectorCard {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['border']};
                border-radius: 22px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            f"color: {COLORS['text_on_brand']}; font-size: 26px; font-weight: 900;"
        )
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 17px; font-weight: 800;"
        )
        layout.addWidget(desc_label)

        summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_label.setMinimumHeight(72)
        summary_label.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; color: {COLORS['accent']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 16px; "
            "font-size: 20px; font-weight: 900; padding: 14px;"
        )
        layout.addWidget(summary_label)

        open_btn = QPushButton(button_text)
        open_btn.setMinimumHeight(62)
        open_btn.setStyleSheet(get_button_style("primary") + "font-size: 18px; font-weight: 900;")
        open_btn.clicked.connect(callback)
        layout.addWidget(open_btn)
        layout.addStretch()
        return card

    # ── Dialog helpers ──────────────────────────────────────────────────

    def _open_features_dialog(self) -> None:
        if self.feature_dialog is None:
            self.feature_dialog = self._build_tree_dialog(
                "اختيار الصفحات والمميزات التفصيلية",
                self.feature_tree,
                with_search=True,
            )
        self._show_dialog(self.feature_dialog)

    def _open_permissions_dialog(self) -> None:
        if self.permissions_dialog is None:
            self.permissions_dialog = self._build_tree_dialog(
                "اختيار صلاحيات المستخدمين حسب الدور",
                self.role_tree,
            )
        self._show_dialog(self.permissions_dialog)

    def _build_tree_dialog(
        self,
        title: str,
        tree: QTreeWidget,
        *,
        with_search: bool = False,
    ) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.resize(1180, 760)
        dialog.setMinimumSize(980, 640)
        dialog.setStyleSheet(GLOBAL_STYLE)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Optional search bar
        if with_search:
            search_input = QLineEdit()
            search_input.setPlaceholderText("🔍 بحث في المميزات...")
            search_input.setStyleSheet(INPUT_STYLE)
            search_input.textChanged.connect(
                lambda text: self._filter_feature_tree(text)
            )
            layout.addWidget(search_input)

        layout.addWidget(self._wrap(title, tree), 1)

        close_btn = QPushButton("إغلاق")
        close_btn.setMinimumHeight(52)
        close_btn.setStyleSheet(get_button_style("secondary") + "font-size: 16px; font-weight: 900;")
        close_btn.clicked.connect(dialog.hide)
        layout.addWidget(close_btn)
        return dialog

    @staticmethod
    def _show_dialog(dialog: QDialog) -> None:
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    # ── Feature tree search / filter ────────────────────────────────────

    def _filter_feature_tree(self, text: str) -> None:
        """Show only features whose label contains *text*."""
        query = text.strip().lower()
        if not query:
            # Show everything
            for item in self.feature_items.values():
                item.setHidden(False)
            for gi in self.feature_group_items.values():
                gi.setHidden(False)
            return

        for group_key, group_item in self.feature_group_items.items():
            any_visible = False
            for i in range(group_item.childCount()):
                child = group_item.child(i)
                match = query in child.text(0).lower()
                child.setHidden(not match)
                if match:
                    any_visible = True
            group_item.setHidden(not any_visible)

    # ── Summary refresh ─────────────────────────────────────────────────

    def _refresh_selector_summaries(self) -> None:
        if self.features_summary_label:
            selected = len(self._enabled_features())
            total = len(self.feature_items)
            self.features_summary_label.setText(f"المحدد: {selected} من {total} ميزة وصفحة")

        if self.permissions_summary_label:
            selected_permissions = sum(
                1
                for items in self.permission_items.values()
                for item in items.values()
                if item.checkState(0) == Qt.CheckState.Checked
            )
            total_permissions = sum(len(items) for items in self.permission_items.values())
            active_roles = len([
                row
                for row in range(self.role_tree.topLevelItemCount())
                if self.role_tree.topLevelItem(row).checkState(0) == Qt.CheckState.Checked
            ])
            self.permissions_summary_label.setText(
                f"الأدوار المفعلة: {active_roles} | الصلاحيات: {selected_permissions} من {total_permissions}"
            )

    # ── Tree frame wrapper ──────────────────────────────────────────────

    def _wrap(self, title: str, widget: QWidget) -> QFrame:
        frame = QFrame()
        frame.setObjectName("BuilderCard")
        frame.setStyleSheet(
            f"QFrame#BuilderCard {{ background-color: {COLORS['bg_panel']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 20px; }}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumHeight(58)
        label.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; color: {COLORS['text_on_brand']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 16px; "
            "font-size: 22px; font-weight: 900; padding: 12px;"
        )
        layout.addWidget(label)

        if isinstance(widget, QTreeWidget):
            widget.setIndentation(30)
            widget.setUniformRowHeights(False)
            widget.setAlternatingRowColors(True)
            widget.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setStyleSheet(
            f"QTreeWidget {{ background-color: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 18px; padding: 12px; "
            "font-size: 16px; font-weight: 800; }"
            "QTreeWidget::item { padding: 10px; }"
            f"QTreeWidget::item:selected {{ background-color: {COLORS['primary']}; color: {COLORS['text_on_brand']}; }}"
            f"QHeaderView::section {{ background-color: {COLORS['bg_elevated']}; color: {COLORS['text_on_brand']}; "
            f"border: 1px solid {COLORS['border']}; font-size: 18px; font-weight: 900; padding: 12px; }}"
        )
        layout.addWidget(widget)
        return frame

    # ── Feature tree ────────────────────────────────────────────────────

    def _populate_features(self) -> None:
        self.feature_tree.clear()
        self.feature_items.clear()
        self.feature_group_items.clear()
        for feature in FEATURE_CATALOG:
            group_key = self._feature_group_key(feature.key)
            group_item = self.feature_group_items.get(group_key)
            if group_item is None:
                group_item = QTreeWidgetItem([FEATURE_GROUP_LABELS.get(group_key, group_key)])
                group_item.setFlags(group_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                group_item.setCheckState(0, Qt.CheckState.Checked)
                group_item.setFont(0, self._tree_font(16, QFont.Weight.Black))
                group_item.setForeground(0, QBrush(QColor(COLORS["accent"])))
                group_item.setBackground(0, QBrush(QColor(COLORS["bg_elevated"])))
                self.feature_tree.addTopLevelItem(group_item)
                self.feature_group_items[group_key] = group_item

            item = QTreeWidgetItem([f"{feature.label} — {feature.description}"])
            item.setData(0, Qt.ItemDataRole.UserRole, feature.key)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked)
            item.setFont(0, self._tree_font(14, QFont.Weight.Bold))
            group_item.addChild(item)
            self.feature_items[feature.key] = item

            for permission in feature.permissions:
                child = QTreeWidgetItem([PERMISSION_LABELS.get(permission, permission)])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setData(0, Qt.ItemDataRole.UserRole, permission)
                child.setCheckState(0, Qt.CheckState.Checked)
                child.setFont(0, self._tree_font(13, QFont.Weight.Bold))
                child.setForeground(0, QBrush(QColor(COLORS["text_secondary"])))
                item.addChild(child)
        self.feature_tree.expandAll()

    @staticmethod
    def _feature_group_key(feature_key: str) -> str:
        return feature_key.split(".", 1)[0]

    @staticmethod
    def _tree_font(size: int, weight: QFont.Weight) -> QFont:
        font = QFont("Arial")
        font.setPointSize(max(int(size), 1))
        font.setWeight(weight)
        return font

    # ── Role / permission tree ──────────────────────────────────────────

    def _populate_roles(self) -> None:
        self.role_tree.clear()
        self.permission_items.clear()
        for role_id, label in ROLE_LABELS.items():
            role_item = QTreeWidgetItem([label])
            role_item.setData(0, Qt.ItemDataRole.UserRole, role_id)
            role_item.setFlags(role_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            role_item.setCheckState(0, Qt.CheckState.Checked)
            role_item.setFont(0, self._tree_font(16, QFont.Weight.Black))
            role_item.setForeground(0, QBrush(QColor(COLORS["accent"])))
            role_item.setBackground(0, QBrush(QColor(COLORS["bg_elevated"])))
            self.role_tree.addTopLevelItem(role_item)
            self.permission_items[role_id] = {}
            for permission in sorted(ROLE_PERMISSIONS.get(role_id, set())):
                child = QTreeWidgetItem([PERMISSION_LABELS.get(permission, permission)])
                child.setData(0, Qt.ItemDataRole.UserRole, permission)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                child.setFont(0, self._tree_font(14, QFont.Weight.Bold))
                role_item.addChild(child)
                self.permission_items[role_id][permission] = child
        self.role_tree.expandAll()

    # ── Tree state helpers ──────────────────────────────────────────────

    def _on_feature_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if item.childCount() == 0:
            return
        state = item.checkState(column)
        self._set_item_children_state(item, state)

    @staticmethod
    def _set_item_children_state(item: QTreeWidgetItem, state: Qt.CheckState) -> None:
        for index in range(item.childCount()):
            child = item.child(index)
            child.setCheckState(0, state)
            DeveloperBuilderWindow._set_item_children_state(child, state)

    @staticmethod
    def _iter_children(item: QTreeWidgetItem):
        for index in range(item.childCount()):
            yield item.child(index)

    def _select_all(self) -> None:
        self._set_tree_state(self.feature_tree, Qt.CheckState.Checked)
        self._set_tree_state(self.role_tree, Qt.CheckState.Checked)
        self._refresh_selector_summaries()

    def _clear_all(self) -> None:
        self._set_tree_state(self.feature_tree, Qt.CheckState.Unchecked)
        self._set_tree_state(self.role_tree, Qt.CheckState.Unchecked)
        self._refresh_selector_summaries()

    def _set_tree_state(self, tree: QTreeWidget, state: Qt.CheckState) -> None:
        for row in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(row)
            item.setCheckState(0, state)
            self._set_item_children_state(item, state)

    # ── Presets ─────────────────────────────────────────────────────────

    def _apply_selected_preset(self) -> None:
        preset_key = self.edition_combo.currentData()
        preset = EDITION_PRESETS.get(preset_key, EDITION_PRESETS["full"])
        feature_keys = preset.get("features")
        role_keys = preset.get("roles")
        if feature_keys is None:
            self._select_all()
            self._append_log(f"تم تطبيق القالب: {preset['label']}")
            return

        self.feature_tree.blockSignals(True)
        self.role_tree.blockSignals(True)
        try:
            self._clear_all()
            for key in feature_keys:
                item = self.feature_items.get(key)
                if item:
                    item.setCheckState(0, Qt.CheckState.Checked)
                    parent = item.parent()
                    while parent:
                        parent.setCheckState(0, Qt.CheckState.Checked)
                        parent = parent.parent()
                    self._set_item_children_state(item, Qt.CheckState.Checked)

            enabled_permissions = set(self._enabled_permissions())
            for role_id, perm_items in self.permission_items.items():
                role_allowed = role_keys is None or role_id in role_keys
                for permission, item in perm_items.items():
                    checked = role_allowed and permission in enabled_permissions
                    item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                role_item = self._find_role_item(role_id)
                if role_item:
                    role_item.setCheckState(
                        0, Qt.CheckState.Checked if role_allowed else Qt.CheckState.Unchecked
                    )
        finally:
            self.feature_tree.blockSignals(False)
            self.role_tree.blockSignals(False)
        self._refresh_selector_summaries()
        self._append_log(f"تم تطبيق القالب: {preset['label']}")

    def _find_role_item(self, role_id: int) -> QTreeWidgetItem | None:
        for row in range(self.role_tree.topLevelItemCount()):
            item = self.role_tree.topLevelItem(row)
            if item.data(0, Qt.ItemDataRole.UserRole) == role_id:
                return item
        return None

    # ── Data extraction ─────────────────────────────────────────────────

    def _enabled_features(self) -> list[str]:
        return [
            key
            for key, item in self.feature_items.items()
            if item.checkState(0) == Qt.CheckState.Checked
        ]

    def _enabled_permissions(self) -> list[str]:
        enabled: set[str] = set()
        for item in self.feature_items.values():
            if item.checkState(0) != Qt.CheckState.Checked:
                continue
            for child in self._iter_children(item):
                if child.checkState(0) == Qt.CheckState.Checked:
                    enabled.add(str(child.data(0, Qt.ItemDataRole.UserRole)))
        return sorted(enabled)

    def _role_permissions(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        globally_enabled = set(self._enabled_permissions())
        for role_id, items in self.permission_items.items():
            role_item = self._find_role_item(role_id)
            if role_item and role_item.checkState(0) != Qt.CheckState.Checked:
                result[str(role_id)] = []
                continue
            selected = [
                permission
                for permission, item in items.items()
                if item.checkState(0) == Qt.CheckState.Checked
            ]
            if globally_enabled:
                selected = [p for p in selected if p in globally_enabled]
            result[str(role_id)] = sorted(selected)
        return result

    def _allowed_roles(self) -> list[int]:
        return [
            int(self.role_tree.topLevelItem(row).data(0, Qt.ItemDataRole.UserRole))
            for row in range(self.role_tree.topLevelItemCount())
            if self.role_tree.topLevelItem(row).checkState(0) == Qt.CheckState.Checked
        ]

    def _client_slug(self) -> str:
        raw = self.client_name_input.text().strip()
        return sanitize_filename(raw, fallback="client")

    def _app_name(self) -> str:
        raw = self.app_name_input.text().strip()
        return sanitize_filename(raw, fallback="HyperPOS")

    def _load_store_scope_choices(self) -> None:
        self.store_scope_combo.clear()
        self.store_scope_combo.addItem("كل الفروع - للمطور والإدارة", None)
        try:
            from repositories.admin_repo import AdminRepository

            repo = AdminRepository()
            stores = repo.get_all_stores(include_inactive=False)
            for store in stores:
                store_type = (store.get("store_type") or "Branch").strip()
                if store_type != "Branch":
                    continue
                store_id = store.get("id")
                if store_id is None:
                    continue
                self.store_scope_combo.addItem(
                    store.get("store_name") or f"فرع {store_id}",
                    {
                        "id": int(store_id),
                        "name": store.get("store_name") or "",
                    },
                )
        except Exception as exc:
            if hasattr(self, "log"):
                self._append_log(f"تعذر تحميل الفروع من قاعدة البيانات: {exc}")

    def _selected_store_scope(self) -> dict | None:
        value = self.store_scope_combo.currentData()
        return value if isinstance(value, dict) else None

    def _payload(self) -> dict:
        preset = EDITION_PRESETS.get(
            self.edition_combo.currentData(), EDITION_PRESETS["full"]
        )
        role_overrides = preset.get("role_overrides") or {}
        # Prevent accidentally forcing privileged roles (developer/admin)
        # to be remapped in customer_features.json unless explicitly desired.
        # Removing these overrides avoids changing login privileges for
        # developer/admin accounts in produced builds.
        filtered_overrides = {
            str(int(src)): int(tgt)
            for src, tgt in role_overrides.items()
            if int(src) not in (ROLE_DEVELOPER, ROLE_ADMIN)
        }
        return {
            "client_name": self.client_name_input.text().strip(),
            "edition": self.edition_combo.currentData(),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "enabled_features": self._enabled_features(),
            "enabled_permissions": self._enabled_permissions(),
            "role_permissions": self._role_permissions(),
            "allowed_roles": self._allowed_roles(),
            "role_overrides": filtered_overrides,
            "store_scope": self._selected_store_scope(),
        }

    # ── Validation ──────────────────────────────────────────────────────

    def _validate(self) -> bool:
        """Run input validation and show a single error dialog if invalid."""
        ok, errors = validate_all(
            client_name=self.client_name_input.text(),
            app_name=self.app_name_input.text(),
            enabled_features=self._enabled_features(),
            allowed_roles=self._allowed_roles(),
        )
        if not ok:
            QMessageBox.warning(
                self,
                "تحقق من البيانات",
                "\n".join(f"⚠ {e}" for e in errors),
            )
        return ok

    # ── Profile save / load / preview ───────────────────────────────────

    def _profile_dir(self) -> Path:
        return PROJECT_ROOT / "build_profiles" / self._client_slug()

    def _save_config(self) -> Path | None:
        if not self._validate():
            return None
        profile_dir = self._profile_dir()
        profile_dir.mkdir(parents=True, exist_ok=True)
        path = profile_dir / CONFIG_FILE_NAME
        path.write_text(
            json.dumps(self._payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._append_log(f"تم حفظ إعدادات العميل: {path}")
        self._set_status(f"✅ تم حفظ إعدادات العميل: {self._client_slug()}")
        return path

    def _load_config(self) -> None:
        """Load a previously saved client profile from disk."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف إعدادات العميل",
            str(PROJECT_ROOT / "build_profiles"),
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"فشل قراءة الملف:\n{exc}")
            return
        self._apply_config_data(data)
        self._append_log(f"تم تحميل إعدادات العميل من: {path}")
        self._set_status(f"✅ تم تحميل إعدادات العميل")

    def _apply_config_data(self, data: dict) -> None:
        """Apply a loaded config dict to the UI trees."""
        self.client_name_input.setText(data.get("client_name", ""))
        edition = data.get("edition", "full")
        idx = self.edition_combo.findData(edition)
        if idx >= 0:
            self.edition_combo.setCurrentIndex(idx)

        store_scope = data.get("store_scope") or {}
        store_id = store_scope.get("id") if isinstance(store_scope, dict) else None
        if store_id is None:
            self.store_scope_combo.setCurrentIndex(0)
        else:
            for index in range(self.store_scope_combo.count()):
                value = self.store_scope_combo.itemData(index)
                if isinstance(value, dict) and value.get("id") == store_id:
                    self.store_scope_combo.setCurrentIndex(index)
                    break

        # Features
        feature_set = set(data.get("enabled_features") or [])
        self.feature_tree.blockSignals(True)
        try:
            if not feature_set:
                self._set_tree_state(self.feature_tree, Qt.CheckState.Checked)
            else:
                self._set_tree_state(self.feature_tree, Qt.CheckState.Unchecked)
                for key in feature_set:
                    item = self.feature_items.get(key)
                    if item:
                        item.setCheckState(0, Qt.CheckState.Checked)
                        parent = item.parent()
                        while parent:
                            parent.setCheckState(0, Qt.CheckState.Checked)
                            parent = parent.parent()
                        self._set_item_children_state(item, Qt.CheckState.Checked)
        finally:
            self.feature_tree.blockSignals(False)

        # Roles & permissions
        allowed = set(data.get("allowed_roles") or [])
        role_perms = data.get("role_permissions") or {}
        self.role_tree.blockSignals(True)
        try:
            for role_id, perm_items in self.permission_items.items():
                role_allowed = not allowed or int(role_id) in {int(r) for r in allowed}
                role_item = self._find_role_item(role_id)
                if role_item:
                    role_item.setCheckState(
                        0, Qt.CheckState.Checked if role_allowed else Qt.CheckState.Unchecked
                    )
                saved_perms = set(role_perms.get(str(role_id), []))
                for perm, item in perm_items.items():
                    checked = role_allowed and (not saved_perms or perm in saved_perms)
                    item.setCheckState(
                        0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                    )
        finally:
            self.role_tree.blockSignals(False)
        self._refresh_selector_summaries()

    def _preview_config(self) -> None:
        """Show JSON preview of the current configuration."""
        payload = self._payload()
        text = json.dumps(payload, ensure_ascii=False, indent=2)

        dialog = QDialog(self)
        dialog.setWindowTitle("معاينة إعدادات النسخة")
        dialog.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        dialog.resize(800, 600)
        dialog.setStyleSheet(GLOBAL_STYLE)

        layout = QVBoxLayout(dialog)
        preview = QPlainTextEdit(text)
        preview.setReadOnly(True)
        preview.setStyleSheet(
            f"background: {COLORS['bg_input']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 12px; "
            "padding: 12px; font-family: Consolas, monospace; font-size: 14px;"
        )
        layout.addWidget(preview)

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet(get_button_style("secondary"))
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.exec()

    # ── Build orchestration ─────────────────────────────────────────────

    def _produce_application(self) -> None:
        if not self._validate():
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "تأكيد الإنتاج",
            f"هل تريد إنتاج نسخة للعميل: {self.client_name_input.text().strip()}؟\n"
            f"المميزات المحددة: {len(self._enabled_features())} ميزة\n"
            f"الأدوار المفعلة: {len(self._allowed_roles())} دور",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        config_path = self._save_config()
        if config_path is None:
            return
        self.build_mode_combo.setCurrentIndex(0)
        self._append_log(f"تم تجهيز إعدادات النسخة داخل ملف الإنتاج: {config_path}")

        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "تنبيه", "هناك عملية إنتاج تعمل بالفعل.")
            return

        app_name = f"{self._app_name()}_{self._client_slug()}"
        config_add_data = f"{config_path}{os.pathsep}."
        schema_path = PROJECT_ROOT / "database_schema_complete.sql"
        hooks_dir = PROJECT_ROOT / "pyinstaller_hooks"
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            app_name,
            "--additional-hooks-dir",
            str(hooks_dir),
            "--collect-all",
            "mysql.connector",
            "--collect-submodules",
            "mysql.connector.locales",
            "--hidden-import",
            "mysql.connector.locales.eng.client_error",
            "--exclude-module",
            "django",
            "--exclude-module",
            "pytest",
            "--add-data",
            config_add_data,
            "--add-data",
            f"{schema_path}{os.pathsep}.",
        ]
        command.append("main.py")

        self._append_log("بدء إنتاج التطبيق:")
        self._append_log(" ".join(command))

        # UI state
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.cancel_btn.setEnabled(True)
        self._set_status("⏳ جاري إنتاج التطبيق...")

        self.worker = BuildWorker(command, PROJECT_ROOT)
        self.worker.log_line.connect(self._append_log)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished_ok.connect(self._build_ok)
        self.worker.failed.connect(self._build_failed)
        self.worker.start()

    def _cancel_build(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)
            self._append_log("جاري إلغاء عملية الإنتاج...")
            self._set_status("⛔ تم إلغاء عملية الإنتاج")

    def _build_ok(self, message: str) -> None:
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self._set_status("✅ تم إنتاج التطبيق بنجاح")

        exe_name = f"{self._app_name()}_{self._client_slug()}.exe"
        dist_dir = PROJECT_ROOT / "dist"

        # Save build history
        self._save_build_history(success=True)

        self._append_log(message)
        path = dist_dir / exe_name

        reply = QMessageBox.question(
            self,
            "تم الإنتاج",
            f"{message}\n{path}\n\nهل تريد فتح مجلد الإنتاج؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.startfile(str(dist_dir))

    def _build_failed(self, message: str) -> None:
        self.cancel_btn.setEnabled(False)
        self.progress_bar.hide()
        self._set_status("❌ فشل الإنتاج")

        self._save_build_history(success=False)

        self._append_log(message)
        QMessageBox.critical(
            self,
            "فشل الإنتاج",
            f"{message}\n\nإذا لم تكن PyInstaller مثبتة نفذ:\npython -m pip install pyinstaller",
        )

    # ── Build history ───────────────────────────────────────────────────

    def _save_build_history(self, *, success: bool) -> None:
        """Persist a JSON log of each build attempt."""
        try:
            log_dir = self._profile_dir() / "build_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"build_{datetime.now():%Y%m%d_%H%M%S}.json"
            log_file.write_text(
                json.dumps(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "success": success,
                        "app_name": self._app_name(),
                        "edition": self.edition_combo.currentData(),
                        "features_count": len(self._enabled_features()),
                        "roles_count": len(self._allowed_roles()),
                        "log_excerpt": self.log.toPlainText()[-2000:],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._append_log(f"تم حفظ سجل البناء: {log_file}")
        except OSError as exc:
            self._append_log(f"⚠️ فشل حفظ سجل البناء: {exc}")

    # ── Logging / status helpers ────────────────────────────────────────

    def _append_log(self, line: str) -> None:
        self.log.appendPlainText(line)

    def _set_status(self, text: str) -> None:
        self.statusBar().showMessage(text)
