from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from controllers.inventory_count_controller import InventoryCountController
from services.inventory_count_pdf_report_service import InventoryCountPdfReportService
from ui.styles import COLORS, GLOBAL_STYLE, INPUT_STYLE, TABLE_STYLE, get_button_style
from ui.table_helpers import actions_cell, center_item, configure_table, table_action_button
from utils.permissions import PermissionPolicy

logger = logging.getLogger(__name__)


TABLE_EDITOR_STYLE = f"""
    QLineEdit, QSpinBox {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 3px 8px;
        min-height: 26px;
        max-height: 26px;
        font-size: 12px;
        font-weight: 700;
    }}
    QLineEdit:focus, QSpinBox:focus {{
        border-color: {COLORS['focus_ring']};
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        width: 0px;
        border: none;
    }}
"""


PRODUCT_SUGGESTIONS_MENU_STYLE = f"""
    QMenu {{
        background-color: {COLORS['bg_panel']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 6px;
        font-size: 12px;
        font-weight: 700;
    }}
    QMenu::item {{
        padding: 8px 12px;
        border-radius: 7px;
        margin: 2px;
    }}
    QMenu::item:selected {{
        background-color: {COLORS['primary']};
        color: {COLORS['text_on_brand']};
    }}
"""


class InventoryCountView(QWidget):
    def __init__(self, ctrl: InventoryCountController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user = user_info
        self.current_session = None
        self.product_suggestions_menu = None
        self.setStyleSheet(GLOBAL_STYLE)
        self._init_ui()
        self._load_stores()
        self._load_sessions()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        title = QLabel("📋 جرد المخزون")
        title.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {COLORS['text_on_brand']};")
        layout.addWidget(title)

        controls = QHBoxLayout()
        self.store_combo = QComboBox()
        self.store_combo.setStyleSheet(INPUT_STYLE)
        self.store_combo.setMinimumWidth(220)

        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet(INPUT_STYLE)
        self.type_combo.addItem("جرد جزئي", "partial")
        self.type_combo.addItem("جرد كامل", "full")
        self.type_combo.addItem("جرد دوري", "cycle")
        self.type_combo.addItem("جرد سريع", "spot")

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("ملاحظات الجرد...")
        self.notes_input.setStyleSheet(INPUT_STYLE)

        start_btn = QPushButton("بدء جرد")
        start_btn.setStyleSheet(get_button_style("success"))
        start_btn.clicked.connect(self._start_session)

        refresh_btn = QPushButton("تحديث")
        refresh_btn.setStyleSheet(get_button_style("info"))
        refresh_btn.clicked.connect(self._refresh_all)

        controls.addWidget(QLabel("الفرع:"))
        controls.addWidget(self.store_combo)
        controls.addWidget(QLabel("النوع:"))
        controls.addWidget(self.type_combo)
        controls.addWidget(self.notes_input, 1)
        controls.addWidget(start_btn)
        controls.addWidget(refresh_btn)
        layout.addLayout(controls)

        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(9)
        self.sessions_table.setHorizontalHeaderLabels([
            "رقم الجرد", "الفرع", "النوع", "الحالة", "الأصناف",
            "المعدود", "الفروقات", "قيمة الفرق", "إجراءات",
        ])
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(self.sessions_table, TABLE_STYLE, row_height=46)
        layout.addWidget(self.sessions_table, 1)

        item_tools = QHBoxLayout()
        self.session_label = QLabel("لا توجد جلسة محددة")
        self.session_label.setStyleSheet(f"color: {COLORS['text_on_brand']}; font-weight: 900;")
        self.item_search = QLineEdit()
        self.item_search.setPlaceholderText("بحث داخل أصناف الجرد...")
        self.item_search.setStyleSheet(INPUT_STYLE)
        self.item_search.returnPressed.connect(self._load_items)

        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("إضافة صنف بالباركود / الكود / الاسم...")
        self.product_search.setStyleSheet(INPUT_STYLE)
        self.product_search.returnPressed.connect(self._add_product_by_search)
        self.product_search.textChanged.connect(self._on_product_search_changed)
        self.product_search_timer = QTimer(self)
        self.product_search_timer.setSingleShot(True)
        self.product_search_timer.setInterval(2000)
        self.product_search_timer.timeout.connect(self._show_product_suggestions)

        search_btn = QPushButton("بحث")
        search_btn.setStyleSheet(get_button_style("info"))
        search_btn.clicked.connect(self._load_items)

        add_btn = QPushButton("إضافة للصنف")
        add_btn.setStyleSheet(get_button_style("primary"))
        add_btn.clicked.connect(self._add_product_by_search)

        approve_btn = QPushButton("اعتماد الجرد")
        approve_btn.setStyleSheet(get_button_style("success"))
        approve_btn.clicked.connect(self._approve_session)

        cancel_btn = QPushButton("إلغاء الجلسة")
        cancel_btn.setStyleSheet(get_button_style("danger"))
        cancel_btn.clicked.connect(self._cancel_session)

        item_tools.addWidget(self.session_label)
        item_tools.addWidget(self.item_search, 1)
        item_tools.addWidget(search_btn)
        item_tools.addWidget(self.product_search, 1)
        item_tools.addWidget(add_btn)
        item_tools.addWidget(approve_btn)
        item_tools.addWidget(cancel_btn)
        layout.addLayout(item_tools)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(9)
        self.items_table.setHorizontalHeaderLabels([
            "الكود", "الصنف", "الدفتري", "الفعلي", "الفرق",
            "قيمة الفرق", "التكلفة", "ملاحظة", "حفظ",
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        configure_table(self.items_table, TABLE_STYLE, row_height=48)
        layout.addWidget(self.items_table, 2)

    def _load_stores(self):
        self.store_combo.clear()
        stores = self.ctrl.get_stores(self.user)
        for store in stores:
            self.store_combo.addItem(store.get("store_name", str(store.get("id"))), store.get("id"))
        user_store_id = self.user.get("store_id")
        index = self.store_combo.findData(user_store_id)
        if index >= 0 and not PermissionPolicy(self.user).can_view_all_inventory():
            self.store_combo.setCurrentIndex(index)
            self.store_combo.setEnabled(False)

    def _refresh_all(self):
        self._load_sessions()
        self._load_items()

    def _load_sessions(self):
        store_id = self.store_combo.currentData()
        sessions = self.ctrl.get_sessions(self.user, store_id=store_id, status=None)
        self.sessions_table.setRowCount(len(sessions))
        for row, session in enumerate(sessions):
            values = [
                session.get("count_number", ""),
                session.get("store_name", ""),
                self._count_type_label(session.get("count_type")),
                self._status_label(session.get("status")),
                str(session.get("item_count") or 0),
                str(session.get("counted_count") or 0),
                str(session.get("variance_count") or 0),
                f"{float(session.get('variance_value') or 0):,.2f}",
            ]
            for col, value in enumerate(values):
                self.sessions_table.setItem(row, col, center_item(value))
            open_btn = table_action_button("فتح", "primary", lambda checked=False, s=session: self._select_session(s))
            self.sessions_table.setCellWidget(row, 8, actions_cell([open_btn]))

    def _select_session(self, session: dict):
        self.current_session = session
        self.session_label.setText(
            f"الجلسة: {session.get('count_number')} - {session.get('store_name')} - {self._status_label(session.get('status'))}"
        )
        self._load_items()

    def _load_items(self):
        if not self.current_session:
            self.items_table.setRowCount(0)
            return
        items = self.ctrl.get_items(
            self.current_session["id"],
            self.item_search.text().strip(),
        )
        editable = self.current_session.get("status") == "open" and PermissionPolicy(self.user).can_count_inventory()
        self.items_table.setRowCount(len(items))
        for row, item in enumerate(items):
            book_qty = float(item.get("book_quantity") or 0)
            actual = item.get("actual_quantity")
            variance = float(item.get("variance") or 0) if actual is not None else 0.0
            unit_cost = float(item.get("unit_cost") or 0)
            values = [
                item.get("product_code", ""),
                item.get("product_name", ""),
                str(book_qty),
            ]
            for col, value in enumerate(values):
                self.items_table.setItem(row, col, center_item(value))

            qty_spin = QDoubleSpinBox()
            qty_spin.setRange(0, 999999)
            qty_spin.setDecimals(3)
            qty_spin.setValue(float(actual if actual is not None else book_qty))
            qty_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_spin.setEnabled(editable)
            qty_spin.setFixedHeight(30)
            qty_spin.setStyleSheet(TABLE_EDITOR_STYLE)
            qty_spin.valueChanged.connect(
                lambda value, r=row, b=book_qty, c=unit_cost: self._update_preview_variance(r, value, b, c)
            )
            self.items_table.setCellWidget(row, 3, self._center_cell_widget(qty_spin))

            self.items_table.setItem(row, 4, center_item(str(variance)))
            self.items_table.setItem(row, 5, center_item(f"{variance * unit_cost:,.2f}"))
            self.items_table.setItem(row, 6, center_item(f"{unit_cost:,.2f}"))

            note_input = QLineEdit(str(item.get("notes") or ""))
            note_input.setEnabled(editable)
            note_input.setFixedHeight(30)
            note_input.setStyleSheet(TABLE_EDITOR_STYLE)
            self.items_table.setCellWidget(row, 7, self._center_cell_widget(note_input))

            save_btn = table_action_button(
                "حفظ",
                "success",
                lambda checked=False, x=item, q=qty_spin, n=note_input: self._save_item(x, q, n),
            )
            save_btn.setEnabled(editable)
            self.items_table.setCellWidget(row, 8, actions_cell([save_btn]))

    def _center_cell_widget(self, widget: QWidget) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(0)
        layout.addStretch()
        layout.addWidget(widget)
        layout.addStretch()
        return cell

    def _update_preview_variance(self, row: int, actual: float, book_qty: float, unit_cost: float):
        variance = float(actual or 0) - float(book_qty or 0)
        self.items_table.setItem(row, 4, center_item(str(variance)))
        self.items_table.setItem(row, 5, center_item(f"{variance * float(unit_cost or 0):,.2f}"))

    def _start_session(self):
        ok, message, session_id = self.ctrl.start_session(
            self.user,
            self.store_combo.currentData(),
            self.type_combo.currentData(),
            self.notes_input.text().strip(),
        )
        if ok:
            QMessageBox.information(self, "تم", message)
            self.notes_input.clear()
            self._load_sessions()
            for row in range(self.sessions_table.rowCount()):
                if self.sessions_table.item(row, 0) and session_id:
                    break
        else:
            QMessageBox.warning(self, "تعذر بدء الجرد", message)

    def _add_product_by_search(self):
        if not self.current_session:
            QMessageBox.warning(self, "تنبيه", "افتح جلسة جرد أولًا.")
            return
        if self.current_session.get("status") != "open":
            QMessageBox.warning(self, "تنبيه", "لا يمكن إضافة صنف إلى جلسة غير مفتوحة.")
            return
        products = self.ctrl.search_products(
            self.product_search.text().strip(),
            self.current_session.get("store_id"),
        )
        if not products:
            QMessageBox.information(self, "بحث", "لم يتم العثور على صنف مطابق.")
            return
        product = products[0]
        self._add_selected_product(product)

    def _on_product_search_changed(self):
        if self.product_suggestions_menu:
            self.product_suggestions_menu.close()
            self.product_suggestions_menu = None
        self.product_search_timer.stop()
        term = self.product_search.text().strip()
        if len(term) < 2:
            return
        if not self.current_session or self.current_session.get("status") != "open":
            return
        self.product_search_timer.start()

    def _show_product_suggestions(self):
        if not self.current_session or self.current_session.get("status") != "open":
            return
        term = self.product_search.text().strip()
        if len(term) < 2:
            return
        try:
            products = self.ctrl.search_products(term, self.current_session.get("store_id"))
        except Exception as exc:
            logger.error("Error loading inventory count product suggestions: %s", exc, exc_info=True)
            return
        if not products or self.product_search.text().strip() != term:
            return

        menu = QMenu(self)
        menu.setStyleSheet(PRODUCT_SUGGESTIONS_MENU_STYLE)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        for product in products[:12]:
            action = menu.addAction(self._product_suggestion_label(product))
            action.triggered.connect(
                lambda checked=False, selected_product=product: self._add_selected_product(selected_product)
            )
        self.product_suggestions_menu = menu
        menu.popup(self.product_search.mapToGlobal(self.product_search.rect().bottomLeft()))

    def _product_suggestion_label(self, product: dict) -> str:
        name = product.get("product_name") or "صنف بدون اسم"
        code = product.get("product_code") or product.get("barcode") or "-"
        quantity = int(product.get("quantity_in_stock") or 0)
        return f"{name}  |  الكود: {code}  |  المتاح: {quantity}"

    def _add_selected_product(self, product: dict):
        if self.product_suggestions_menu:
            self.product_suggestions_menu.close()
            self.product_suggestions_menu = None
        ok, message = self.ctrl.add_item(self.user, self.current_session["id"], product["id"])
        if ok:
            self.item_search.setText(product.get("product_code") or product.get("barcode") or "")
            self.product_search.clear()
            self._load_items()
        else:
            QMessageBox.warning(self, "تعذر الإضافة", message)

    def _save_item(self, item: dict, qty_spin: QDoubleSpinBox, note_input: QLineEdit):
        ok, message = self.ctrl.update_item(
            self.user,
            self.current_session["id"],
            item["product_id"],
            qty_spin.value(),
            note_input.text().strip(),
        )
        if ok:
            self._load_items()
            self._load_sessions()
        else:
            QMessageBox.warning(self, "تعذر الحفظ", message)

    def _approve_session(self):
        if not self.current_session:
            QMessageBox.warning(self, "تنبيه", "افتح جلسة جرد أولًا.")
            return
        reply = QMessageBox.question(
            self,
            "اعتماد الجرد",
            "سيتم تعديل كميات المخزون للأصناف المعدودة فقط. هل تريد المتابعة؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        session = dict(self.current_session)
        ok, message = self.ctrl.approve_session(self.user, self.current_session["id"])
        if ok:
            report_items = self.ctrl.get_items(session["id"], "", limit=9999999)
            report_message = self._create_approval_report(session, report_items)
            QMessageBox.information(self, "تم", f"{message}\n{report_message}")
            self.current_session = None
            self.session_label.setText("لا توجد جلسة محددة")
            self._refresh_all()
        else:
            QMessageBox.warning(self, "تعذر الاعتماد", message)

    def _create_approval_report(self, session: dict, items: list[dict]) -> str:
        try:
            session["status"] = "approved"
            result = InventoryCountPdfReportService().create_pdf(session, items, self.user)
            if result.get("saved"):
                return f"تم حفظ تقرير الجرد PDF بنجاح:\n{result.get('pdf_path')}"
            return "تم اعتماد الجرد، لكن تعذر حفظ تقرير PDF."
        except Exception as exc:
            logger.error("Error creating inventory count approval PDF: %s", exc, exc_info=True)
            return f"تم اعتماد الجرد، لكن حدث خطأ أثناء إنشاء تقرير PDF:\n{exc}"

    def _cancel_session(self):
        if not self.current_session:
            QMessageBox.warning(self, "تنبيه", "افتح جلسة جرد أولًا.")
            return
        reply = QMessageBox.question(
            self,
            "إلغاء الجرد",
            "هل تريد إلغاء جلسة الجرد؟ لا يمكن إلغاء جرد معتمد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        ok, message = self.ctrl.cancel_session(self.user, self.current_session["id"])
        if ok:
            QMessageBox.information(self, "تم", message)
            self.current_session = None
            self.session_label.setText("لا توجد جلسة محددة")
            self._refresh_all()
        else:
            QMessageBox.warning(self, "تعذر الإلغاء", message)

    def _status_label(self, status: str) -> str:
        return {
            "open": "مفتوح",
            "review": "قيد المراجعة",
            "approved": "معتمد",
            "cancelled": "ملغي",
        }.get(status or "", status or "-")

    def _count_type_label(self, count_type: str) -> str:
        return {
            "full": "كامل",
            "partial": "جزئي",
            "cycle": "دوري",
            "spot": "سريع",
        }.get(count_type or "", count_type or "-")
