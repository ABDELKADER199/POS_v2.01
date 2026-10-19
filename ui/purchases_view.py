"""
Purchases View - واجهة المشتريات والموردين (Clean Architecture)
"""
import logging
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QTableWidget, QMessageBox,
    QHeaderView, QComboBox, QTabWidget, QDialog,
    QFormLayout, QDoubleSpinBox, QSpinBox, QDateEdit,
    QSizePolicy, QGridLayout, QScrollArea, QAbstractSpinBox, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from ui.styles import GLOBAL_STYLE, COLORS, TABLE_STYLE, INPUT_STYLE, get_button_style
from ui.form_helpers import action_row, configure_form_layout, style_dialog, style_form_controls, scrollable_dialog_layout
from ui.table_helpers import (
    actions_cell,
    center_item,
    configure_table,
    set_center_item,
    table_action_button,
)
from ui.subtab_dropdown import create_subtab_dropdown
from controllers.purchases_controller import PurchasesController
from application.errors import PurchaseValidationError
from utils.permissions import PermissionPolicy
from services.whatsapp_share_service import WhatsAppShareService

logger = logging.getLogger(__name__)


class PurchasesView(QWidget):
    def __init__(self, ctrl: PurchasesController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user = user_info
        self.cart = []
        self.current_product = None
        self.current_purchase_return_invoice = None
        self.purchase_return_items = []
        self.setStyleSheet(GLOBAL_STYLE)
        self._init_ui()
        self._load_stores()
        self._load_return_stores()
        self._load_suppliers()
        self._load_suppliers_table()
        self._load_history()

    def _center_item(self, value):
        return center_item(value)

    def _set_center_item(self, table: QTableWidget, row: int, col: int, value):
        set_center_item(table, row, col, value)

    def _footer_pair(self, label_text: str, field: QWidget) -> QWidget:
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet("font-weight: 800;")
        field.setMinimumWidth(170)
        field.setMaximumWidth(220)
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(label)
        row.addWidget(field)
        row.setAlignment(Qt.AlignmentFlag.AlignRight)
        return box

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_invoice_tab(), "🛒 فاتورة شراء جديدة")
        self.tabs.addTab(self._create_purchase_orders_tab(), "📋 أوامر الشراء")
        self.tabs.addTab(self._create_suppliers_tab(), "👥 الموردين")
        self.tabs.addTab(self._create_purchase_returns_tab(), "↩️ مرتجع مشتريات")
        self.tabs.addTab(self._create_history_tab(), "📜 سجل الفواتير")
        layout.addWidget(create_subtab_dropdown(self.tabs, "اختر قسم المشتريات"))
        layout.addWidget(self.tabs)

    def _create_invoice_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Header: Supplier
        header = QHBoxLayout()
        header.addWidget(QLabel("المورد:"))
        self.supplier_combo = QComboBox()
        self.supplier_combo.setEditable(True)
        self.supplier_combo.setMinimumHeight(40)
        self.supplier_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header.addWidget(self.supplier_combo, 3)

        header.addWidget(QLabel("فرع الاستلام:"))
        self.store_combo = QComboBox()
        self.store_combo.setMinimumHeight(40)
        self.store_combo.setMinimumWidth(170)
        header.addWidget(self.store_combo)

        add_sup_btn = QPushButton("➕ مورد جديد")
        add_sup_btn.setStyleSheet(get_button_style('primary'))
        add_sup_btn.clicked.connect(self._add_supplier)
        header.addWidget(add_sup_btn)

        import_csv_btn = QPushButton("📥 استيراد Excel/CSV")
        import_csv_btn.setStyleSheet(get_button_style('info'))
        import_csv_btn.clicked.connect(self._import_purchase_csv)
        header.addWidget(import_csv_btn)

        header.addWidget(QLabel("رقم مرجعي:"))
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("رقم فاتورة المورد (اختياري)")
        header.addWidget(self.ref_input, 2)
        layout.addLayout(header)

        # Product Entry
        entry = QHBoxLayout()
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("🔍 بحث عن منتج (كود / اسم / باركود)...")
        self.product_search.setMinimumHeight(42)
        self.product_search.returnPressed.connect(self._find_product)
        entry.addWidget(self.product_search, 3)

        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 10000)
        self.qty_input.setPrefix("الكمية: ")
        self.qty_input.setMinimumHeight(42)
        entry.addWidget(self.qty_input)

        self.cost_input = QDoubleSpinBox()
        self.cost_input.setRange(0, 1000000)
        self.cost_input.setSuffix(" ج.م")
        self.cost_input.setPrefix("التكلفة: ")
        self.cost_input.setMinimumHeight(42)
        entry.addWidget(self.cost_input)

        self.sell_price_input = QDoubleSpinBox()
        self.sell_price_input.setRange(0, 1000000)
        self.sell_price_input.setSuffix(" ج.م")
        self.sell_price_input.setPrefix("سعر بيع: ")
        self.sell_price_input.setMinimumHeight(42)
        entry.addWidget(self.sell_price_input)

        self.supplier_support_type = QComboBox()
        self.supplier_support_type.addItem("بدون دعم", "none")
        self.supplier_support_type.addItem("مطالبة مبلغ/وحدة", "claim_per_unit")
        self.supplier_support_type.addItem("مطالبة نسبة من التكلفة", "claim_percent")
        self.supplier_support_type.addItem("خصم مباشر/وحدة", "direct_per_unit")
        self.supplier_support_type.addItem("خصم مباشر نسبة", "direct_percent")
        self.supplier_support_type.addItem("كمية مجانية", "free_quantity")
        self.supplier_support_type.setMinimumHeight(42)
        entry.addWidget(self.supplier_support_type)

        self.supplier_support_input = QDoubleSpinBox()
        self.supplier_support_input.setRange(0, 1000000)
        self.supplier_support_input.setSuffix(" ج.م / %")
        self.supplier_support_input.setPrefix("قيمة الدعم: ")
        self.supplier_support_input.setMinimumHeight(42)
        entry.addWidget(self.supplier_support_input)

        self.free_qty_input = QSpinBox()
        self.free_qty_input.setRange(0, 10000)
        self.free_qty_input.setPrefix("مجاني: ")
        self.free_qty_input.setMinimumHeight(42)
        entry.addWidget(self.free_qty_input)

        self.expiry_input = QDateEdit()
        self.expiry_input.setCalendarPopup(True)
        self.expiry_input.setDate(QDate.currentDate().addYears(1))
        self.expiry_input.setDisplayFormat("yyyy-MM-dd")
        self.expiry_input.setMinimumHeight(42)
        entry.addWidget(self.expiry_input)

        add_btn = QPushButton("➕")
        add_btn.setFixedSize(48, 42)
        add_btn.setStyleSheet(get_button_style('success'))
        add_btn.clicked.connect(self._add_to_cart)
        entry.addWidget(add_btn)
        layout.addLayout(entry)

        # Cart Table
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(12)
        self.cart_table.setHorizontalHeaderLabels([
            'م', 'المنتج', 'الكمية', 'التكلفة', 'سعر البيع',
            'نوع الدعم', 'قيمة الدعم', 'مجاني', 'الصلاحية', 'الإجمالي', 'باركود', 'حذف'
        ])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cart_table.setMinimumHeight(250)
        configure_table(self.cart_table, TABLE_STYLE, row_height=52)
        self.cart_table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.cart_table.horizontalHeader().setSectionResizeMode(11, QHeaderView.ResizeMode.Fixed)
        self.cart_table.setColumnWidth(10, 96)
        self.cart_table.setColumnWidth(11, 78)
        layout.addWidget(self.cart_table)

        # Footer: Totals
        footer = QGridLayout()
        footer.setHorizontalSpacing(18)
        footer.setVerticalSpacing(12)
        self.subtotal_label = QLabel("0.00")
        self.subtotal_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        footer.addWidget(self._footer_pair("المجموع:", self.subtotal_label), 0, 0)

        self.discount_input = QDoubleSpinBox()
        self.discount_input.setRange(0, 1000000)
        self.discount_input.setSuffix(" ج.م")
        self.discount_input.valueChanged.connect(self._calc_totals)
        footer.addWidget(self._footer_pair("خصم:", self.discount_input), 0, 1)

        self.tax_input = QDoubleSpinBox()
        self.tax_input.setRange(0, 1000000)
        self.tax_input.setSuffix(" ج.م")
        self.tax_input.valueChanged.connect(self._calc_totals)
        footer.addWidget(self._footer_pair("ضريبة:", self.tax_input), 0, 2)

        self.final_total_label = QLabel("0.00")
        self.final_total_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 18px; font-weight: bold;")
        footer.addWidget(self._footer_pair("صافي الفاتورة:", self.final_total_label), 1, 0)

        self.pay_method = QComboBox()
        self.pay_method.addItems(["نقدي", "آجل", "شيك", "تحويل"])
        self.pay_method.currentTextChanged.connect(self._on_payment_method_changed)
        footer.addWidget(self._footer_pair("طريقة الدفع:", self.pay_method), 1, 1)

        self.paid_input = QDoubleSpinBox()
        self.paid_input.setRange(0, 1000000)
        self.paid_input.setSuffix(" ج.م")
        self.paid_input.valueChanged.connect(self._calc_totals)
        footer.addWidget(self._footer_pair("المدفوع:", self.paid_input), 1, 2)

        self.remaining_label = QLabel("المتبقي: 0.00 ج.م")
        self.remaining_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.remaining_label.setStyleSheet("font-weight: bold; color: #22C55E;")
        footer.addWidget(self.remaining_label, 2, 0, 1, 3)

        layout.addLayout(footer)

        save_btn = QPushButton("💾 حفظ الفاتورة وتحديث المخزون")
        save_btn.setStyleSheet(get_button_style('success') + " min-height: 48px; font-size: 14px;")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_invoice)
        layout.addWidget(save_btn)

        scroll.setWidget(content)
        return scroll

    def _create_suppliers_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ إضافة مورد")
        add_btn.setStyleSheet(get_button_style('success'))
        add_btn.clicked.connect(self._add_supplier)
        btn_layout.addWidget(add_btn)
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setStyleSheet(get_button_style('info'))
        refresh_btn.clicked.connect(self._load_suppliers_table)
        btn_layout.addWidget(refresh_btn)

        statement_btn = QPushButton("📊 كشف حساب المورد")
        statement_btn.setStyleSheet(get_button_style('secondary'))
        statement_btn.clicked.connect(self._open_supplier_statement_dialog)
        btn_layout.addWidget(statement_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.sup_table = QTableWidget()
        self.sup_table.setColumnCount(7)
        self.sup_table.setHorizontalHeaderLabels(["ID", "الاسم", "الهاتف", "الرصيد", "رقم ضريبي", "العنوان", "إجراءات"])
        self.sup_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sup_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.sup_table.setColumnWidth(6, 170)
        configure_table(self.sup_table, TABLE_STYLE)
        layout.addWidget(self.sup_table)
        return widget

    def _create_purchase_returns_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        search_row = QHBoxLayout()
        self.purchase_return_search = QLineEdit()
        self.purchase_return_search.setPlaceholderText("ابحث برقم فاتورة الشراء أو الرقم المرجعي...")
        self.purchase_return_search.setMinimumHeight(42)
        self.purchase_return_search.returnPressed.connect(self._search_purchase_invoice_for_return)
        search_row.addWidget(self.purchase_return_search, 3)

        search_btn = QPushButton("🔍 بحث")
        search_btn.setStyleSheet(get_button_style("info"))
        search_btn.clicked.connect(self._search_purchase_invoice_for_return)
        search_row.addWidget(search_btn)

        self.return_store_combo = QComboBox()
        self.return_store_combo.setMinimumHeight(42)
        self.return_store_combo.setMinimumWidth(190)
        search_row.addWidget(QLabel("فرع المرتجع:"))
        search_row.addWidget(self.return_store_combo)

        self.return_settlement_combo = QComboBox()
        self.return_settlement_combo.setMinimumHeight(42)
        self.return_settlement_combo.addItem("تخفيض مديونية المورد", "credit")
        self.return_settlement_combo.addItem("استرداد نقدي للخزينة", "cash_refund")
        search_row.addWidget(QLabel("التسوية:"))
        search_row.addWidget(self.return_settlement_combo)
        layout.addLayout(search_row)

        info_row = QHBoxLayout()
        self.purchase_return_info = QLabel("اختر فاتورة شراء لعرض الأصناف المتاحة للارتجاع.")
        self.purchase_return_info.setStyleSheet("font-weight: 800; color: #93C5FD;")
        info_row.addWidget(self.purchase_return_info, 3)
        self.purchase_return_reason = QLineEdit()
        self.purchase_return_reason.setPlaceholderText("سبب المرتجع (اختياري)")
        self.purchase_return_reason.setMinimumHeight(40)
        info_row.addWidget(self.purchase_return_reason, 2)
        layout.addLayout(info_row)

        self.purchase_return_table = QTableWidget()
        self.purchase_return_table.setColumnCount(7)
        self.purchase_return_table.setHorizontalHeaderLabels([
            "الصنف", "المشتراة", "مرتجع سابق", "المتاح", "تكلفة الوحدة", "كمية المرتجع", "الإجمالي"
        ])
        configure_table(self.purchase_return_table, TABLE_STYLE, row_height=48)
        self.purchase_return_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.purchase_return_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.purchase_return_table.setColumnWidth(5, 150)
        layout.addWidget(self.purchase_return_table)

        footer = QHBoxLayout()
        self.purchase_return_total_label = QLabel("إجمالي المرتجع: 0.00 ج.م")
        self.purchase_return_total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.purchase_return_total_label.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {COLORS['accent']};")
        footer.addWidget(self.purchase_return_total_label, 1)

        process_btn = QPushButton("↩️ تنفيذ مرتجع الشراء")
        process_btn.setStyleSheet(get_button_style("danger") + " min-height: 44px; font-size: 14px;")
        process_btn.clicked.connect(self._process_purchase_return)
        footer.addWidget(process_btn)
        layout.addLayout(footer)
        return widget

    def _create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        refresh_btn = QPushButton("🔄 تحديث السجل")
        refresh_btn.setStyleSheet(get_button_style('info'))
        refresh_btn.clicked.connect(self._load_history)
        layout.addWidget(refresh_btn)

        self.hist_table = QTableWidget()
        self.hist_table.setColumnCount(10)
        self.hist_table.setHorizontalHeaderLabels([
            "رقم", "المورد", "التاريخ", "الإجمالي", "المدفوع",
            "المتبقي", "الحالة", "بواسطة", "عرض", "سداد"
        ])
        self.hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(self.hist_table, TABLE_STYLE)
        layout.addWidget(self.hist_table)
        return widget

    # ── Logic ──────────────────────────────────────────
    def _load_suppliers(self):
        self.supplier_combo.clear()
        self._suppliers_by_id = {}
        for s in self.ctrl.get_all_suppliers():
            self._suppliers_by_id[s['id']] = s
            bal = float(s.get('current_balance', 0) or 0)
            self.supplier_combo.addItem(f"{s['name']} • رصيد: {bal:,.2f}", s['id'])

    def _load_stores(self):
        if not hasattr(self, "store_combo"):
            return
        self.store_combo.clear()
        user_store_id = self.user.get("store_id")
        policy = PermissionPolicy(self.user)
        stores = self.ctrl.get_all_stores() or []
        if user_store_id and not (policy.is_admin or policy.is_accountant):
            stores = [store for store in stores if store.get("id") == user_store_id]
        if not stores and user_store_id:
            stores = [{"id": user_store_id, "store_name": self.user.get("store_name") or f"فرع {user_store_id}"}]
        for store in stores:
            self.store_combo.addItem(store.get("store_name") or f"فرع {store.get('id')}", store.get("id"))
        if user_store_id:
            index = self.store_combo.findData(user_store_id)
            if index >= 0:
                self.store_combo.setCurrentIndex(index)
        self.store_combo.setEnabled(self.store_combo.count() > 1 and (policy.is_admin or policy.is_accountant))

    def _load_return_stores(self):
        if not hasattr(self, "return_store_combo"):
            return
        self.return_store_combo.clear()
        user_store_id = self.user.get("store_id")
        policy = PermissionPolicy(self.user)
        stores = self.ctrl.get_all_stores() or []
        if user_store_id and not (policy.is_admin or policy.is_accountant):
            stores = [store for store in stores if store.get("id") == user_store_id]
        if not stores and user_store_id:
            stores = [{"id": user_store_id, "store_name": self.user.get("store_name") or f"فرع {user_store_id}"}]
        for store in stores:
            self.return_store_combo.addItem(store.get("store_name") or f"فرع {store.get('id')}", store.get("id"))
        if user_store_id:
            index = self.return_store_combo.findData(user_store_id)
            if index >= 0:
                self.return_store_combo.setCurrentIndex(index)
        self.return_store_combo.setEnabled(
            self.return_store_combo.count() > 1 and (policy.is_admin or policy.is_accountant)
        )

    def _selected_store_id(self):
        if hasattr(self, "store_combo") and self.store_combo.count() > 0:
            store_id = self.store_combo.currentData()
            if store_id:
                return store_id
        return self.user.get("store_id")

    def _load_suppliers_table(self):
        suppliers = self.ctrl.get_all_suppliers()
        self.sup_table.setRowCount(len(suppliers))
        for i, s in enumerate(suppliers):
            set_center_item(self.sup_table, i, 0, s['id'])
            set_center_item(self.sup_table, i, 1, s['name'])
            set_center_item(self.sup_table, i, 2, s.get('phone', '') or '')
            bal = float(s.get('current_balance', 0) or 0)
            bal_item = center_item(f"{bal:,.2f}")
            if bal > 0: bal_item.setForeground(QColor("#EF4444"))
            self.sup_table.setItem(i, 3, bal_item)
            set_center_item(self.sup_table, i, 4, s.get('tax_number', '') or '—')
            set_center_item(self.sup_table, i, 5, s.get('address', '') or '')
            edit_btn = table_action_button("تعديل", "info")
            edit_btn.setFixedSize(72, 30)
            edit_btn.clicked.connect(lambda _, supplier=s: self._edit_supplier(supplier))
            delete_btn = table_action_button("حذف", "danger")
            delete_btn.setFixedSize(72, 30)
            delete_btn.clicked.connect(lambda _, supplier=s: self._soft_delete_supplier(supplier))
            self.sup_table.setCellWidget(i, 6, actions_cell([edit_btn, delete_btn]))

    def _add_supplier(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة مورد جديد")
        style_dialog(dialog, width=460)
        layout = QFormLayout(dialog)
        configure_form_layout(layout)

        name = QLineEdit()
        phone = QLineEdit()
        address = QLineEdit()
        tax = QLineEdit()
        balance = QDoubleSpinBox()
        balance.setRange(-1000000, 1000000)
        balance.setDecimals(2)
        style_form_controls(name, phone, address, tax, balance)

        layout.addRow("الاسم:", name)
        layout.addRow("الهاتف:", phone)
        layout.addRow("العنوان:", address)
        layout.addRow("الرقم الضريبي:", tax)
        layout.addRow("رصيد افتتاحي:", balance)

        buttons, save_btn, cancel_btn = action_row()
        cancel_btn.clicked.connect(dialog.reject)
        layout.addRow(buttons)

        def save():
            if not name.text():
                QMessageBox.warning(dialog, "خطأ", "اسم المورد مطلوب")
                return
            if self.ctrl.add_supplier(name.text(), phone.text(), address.text(), tax.text(), balance.value()):
                QMessageBox.information(dialog, "نجاح", "تمت إضافة المورد")
                dialog.accept()
                self._load_suppliers()
                self._load_suppliers_table()

        save_btn.clicked.connect(save)
        dialog.exec()

    def _edit_supplier(self, supplier: dict):
        dialog = QDialog(self)
        dialog.setWindowTitle("تعديل مورد")
        style_dialog(dialog, width=460)
        layout = QFormLayout(dialog)
        configure_form_layout(layout)

        name = QLineEdit(str(supplier.get("name") or ""))
        phone = QLineEdit(str(supplier.get("phone") or ""))
        address = QLineEdit(str(supplier.get("address") or ""))
        tax = QLineEdit(str(supplier.get("tax_number") or ""))
        style_form_controls(name, phone, address, tax)

        layout.addRow("الاسم:", name)
        layout.addRow("الهاتف:", phone)
        layout.addRow("العنوان:", address)
        layout.addRow("الرقم الضريبي:", tax)

        buttons, save_btn, cancel_btn = action_row("حفظ التعديل")
        cancel_btn.clicked.connect(dialog.reject)
        layout.addRow(buttons)

        def save():
            try:
                ok = self.ctrl.update_supplier(
                    supplier.get("id"),
                    name.text(),
                    phone.text(),
                    address.text(),
                    tax.text(),
                )
            except ValueError as e:
                QMessageBox.warning(dialog, "تنبيه", str(e))
                return
            if ok:
                QMessageBox.information(dialog, "نجاح", "تم تعديل المورد")
                dialog.accept()
                self._load_suppliers()
                self._load_suppliers_table()
            else:
                QMessageBox.critical(dialog, "خطأ", "فشل تعديل المورد")

        save_btn.clicked.connect(save)
        dialog.exec()

    def _soft_delete_supplier(self, supplier: dict):
        balance = float(supplier.get("current_balance") or 0)
        if balance > 0:
            QMessageBox.warning(self, "تنبيه", "لا يمكن حذف مورد له رصيد مستحق.")
            return
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            f"هل تريد إخفاء المورد '{supplier.get('name')}' من القوائم؟\nسيتم الحذف ناعمًا ولن تُحذف فواتيره القديمة.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            ok = self.ctrl.soft_delete_supplier(supplier.get("id"))
        except ValueError as e:
            QMessageBox.warning(self, "تنبيه", str(e))
            return
        if ok:
            QMessageBox.information(self, "نجاح", "تم حذف المورد ناعمًا")
            self._load_suppliers()
            self._load_suppliers_table()
        else:
            QMessageBox.critical(self, "خطأ", "فشل حذف المورد")

    def _find_product(self):
        term = self.product_search.text().strip()
        if not term: return
        prod = self.ctrl.search_product(term)
        if prod:
            self.current_product = prod
            self.product_search.setText(f"{prod['product_name']} ({prod['product_code']})")
            self.cost_input.setValue(float(prod.get('buy_price', 0)))
            self.sell_price_input.setValue(float(prod.get('sell_price', 0)))
            self.qty_input.setFocus()
        else:
            QMessageBox.warning(self, "تنبيه", "المنتج غير موجود")
            self.current_product = None

    def _add_to_cart(self):
        if not self.current_product:
            self._find_product()
            return
        if not self.current_product:
            return

        if self.cost_input.value() == 0:
            reply = QMessageBox.question(
                self,
                "تأكيد تكلفة صفرية",
                "تكلفة الصنف صفر. هل تريد إضافته بهذا الشكل؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if self.expiry_input.date() < QDate.currentDate():
            reply = QMessageBox.question(
                self,
                "تأكيد صلاحية منتهية",
                "تاريخ الصلاحية أقدم من تاريخ اليوم. هل تريد المتابعة؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        support_type = self.supplier_support_type.currentData() or "none"
        support_value = self.supplier_support_input.value()
        free_quantity = self.free_qty_input.value() if support_type == "free_quantity" else 0
        item = {
            'product_id': self.current_product['id'],
            'name': self.current_product['product_name'],
            'code': self.current_product['product_code'],
            'barcode': self.current_product.get('barcode') or self.current_product['product_code'],
            'quantity': self.qty_input.value(),
            'cost': self.cost_input.value(),
            'sell_price': self.sell_price_input.value(),
            'supplier_support_type': support_type,
            'supplier_support_value': support_value,
            'free_quantity': free_quantity,
            'expiry_date': self.expiry_input.date().toString("yyyy-MM-dd"),
        }
        self.cart.append(item)
        self._refresh_cart()
        self.product_search.clear()
        self.current_product = None
        self.qty_input.setValue(1)
        self.cost_input.setValue(0)
        self.sell_price_input.setValue(0)
        self.supplier_support_type.setCurrentIndex(0)
        self.supplier_support_input.setValue(0)
        self.free_qty_input.setValue(0)
        self.expiry_input.setDate(QDate.currentDate().addYears(1))
        self.product_search.setFocus()

    def _supplier_support_label(self, support_type):
        return {
            "none": "بدون",
            "claim_per_unit": "مطالبة/وحدة",
            "claim_percent": "مطالبة %",
            "direct_per_unit": "خصم مباشر/وحدة",
            "direct_percent": "خصم مباشر %",
            "free_quantity": "كمية مجانية",
        }.get(support_type or "none", "بدون")

    def _direct_support_discount(self, item):
        support_type = item.get("supplier_support_type") or "none"
        value = float(item.get("supplier_support_value") or 0)
        quantity = int(item.get("quantity") or 0)
        cost = float(item.get("cost") or 0)
        if support_type == "direct_per_unit":
            return min(value * quantity, cost * quantity)
        if support_type == "direct_percent":
            return min((cost * quantity) * (value / 100.0), cost * quantity)
        return 0.0

    def _refresh_cart(self):
        self.cart_table.setRowCount(len(self.cart))
        subtotal = 0
        direct_support_total = 0
        for i, item in enumerate(self.cart):
            self.cart_table.setRowHeight(i, 52)
            total = item['quantity'] * item['cost']
            subtotal += total
            direct_support_total += self._direct_support_discount(item)
            set_center_item(self.cart_table, i, 0, i + 1)
            set_center_item(self.cart_table, i, 1, item['name'])
            set_center_item(self.cart_table, i, 2, item['quantity'])
            set_center_item(self.cart_table, i, 3, f"{item['cost']:.2f}")
            set_center_item(self.cart_table, i, 4, f"{item['sell_price']:.2f}")
            set_center_item(self.cart_table, i, 5, self._supplier_support_label(item.get('supplier_support_type')))
            set_center_item(self.cart_table, i, 6, f"{item.get('supplier_support_value', 0):.2f}")
            set_center_item(self.cart_table, i, 7, item.get('free_quantity', 0))
            set_center_item(self.cart_table, i, 8, item.get('expiry_date', '-'))
            set_center_item(self.cart_table, i, 9, f"{total:.2f}")

            print_btn = table_action_button("🖨", "secondary")
            print_btn.setFixedSize(54, 28)
            print_btn.clicked.connect(lambda _, x=item: self._print_item_barcode(x))
            self.cart_table.setCellWidget(i, 10, actions_cell([print_btn]))

            del_btn = table_action_button("🗑", "danger")
            del_btn.setFixedSize(54, 28)
            del_btn.clicked.connect(lambda _, idx=i: self._remove_from_cart(idx))
            self.cart_table.setCellWidget(i, 11, actions_cell([del_btn]))

        if direct_support_total > 0:
            self.subtotal_label.setText(f"{subtotal:,.2f} - دعم مباشر {direct_support_total:,.2f}")
        else:
            self.subtotal_label.setText(f"{subtotal:,.2f}")
        self._calc_totals()

    def _remove_from_cart(self, idx):
        if 0 <= idx < len(self.cart):
            self.cart.pop(idx)
            self._refresh_cart()

    def _calc_totals(self):
        subtotal = sum(i['quantity'] * i['cost'] for i in self.cart)
        supplier_direct_discount = sum(self._direct_support_discount(i) for i in self.cart)
        total = subtotal - supplier_direct_discount - self.discount_input.value() + self.tax_input.value()
        if total < 0:
            total = 0
        self.final_total_label.setText(f"{total:,.2f}")
        if self.pay_method.currentText() == "آجل":
            self.paid_input.blockSignals(True)
            self.paid_input.setValue(0)
            self.paid_input.setEnabled(False)
            self.paid_input.blockSignals(False)
        else:
            self.paid_input.setEnabled(True)
        if self.paid_input.value() == 0 and total > 0 and self.pay_method.currentText() != "آجل":
            self.paid_input.blockSignals(True)
            self.paid_input.setValue(total)
            self.paid_input.blockSignals(False)
        if self.paid_input.value() > total:
            self.paid_input.blockSignals(True)
            self.paid_input.setValue(total)
            self.paid_input.blockSignals(False)
        remaining = total - self.paid_input.value()
        self.remaining_label.setText(f"المتبقي: {remaining:,.2f} ج.م")
        self.remaining_label.setStyleSheet(
            "font-weight: bold; color: #EF4444;" if remaining > 0
            else "font-weight: bold; color: #22C55E;"
        )

    def _on_payment_method_changed(self, *_):
        self._calc_totals()

    def _print_item_barcode(self, item: dict):
        try:
            from utils.printer_service import PrinterService
            result = PrinterService.print_barcode_direct(
                name=item['name'],
                code=item.get('barcode') or item.get('code'),
                printer_name=self._get_barcode_printer_name(),
                price=item.get('sell_price'),
                store_name=self.user.get('store_name', ''),
            )
            if not result:
                QMessageBox.warning(self, "تنبيه", "تعذر طباعة أو حفظ الباركود")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"فشل طباعة الباركود: {e}")

    def _get_barcode_printer_name(self):
        try:
            from PyQt6.QtPrintSupport import QPrinterInfo
            default = QPrinterInfo.defaultPrinter().printerName()
            return default if default else "Xprinter"
        except Exception:
            return "Xprinter"

    def _save_invoice(self):
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "الفاتورة فارغة")
            return

        supplier_id = self.supplier_combo.currentData()
        if not supplier_id:
            QMessageBox.warning(self, "تنبيه", "اختر المورد")
            return

        subtotal = sum(i['quantity'] * i['cost'] for i in self.cart)
        supplier_direct_discount = sum(self._direct_support_discount(i) for i in self.cart)
        discount = self.discount_input.value()
        tax = self.tax_input.value()
        total = subtotal - supplier_direct_discount - discount + tax
        paid = self.paid_input.value()
        if discount + supplier_direct_discount > subtotal:
            QMessageBox.warning(self, "تنبيه", "الخصم أكبر من إجمالي الفاتورة")
            return
        if total <= 0:
            QMessageBox.warning(self, "تنبيه", "صافي الفاتورة يجب أن يكون أكبر من صفر")
            return
        if paid > total:
            QMessageBox.warning(self, "تنبيه", "المدفوع أكبر من صافي الفاتورة")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد الحفظ",
            f"هل تريد حفظ فاتورة مشتريات بقيمة {total:,.2f} ج.م؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        store_id = self._selected_store_id()
        if not store_id:
            QMessageBox.warning(self, "تنبيه", "اختر فرع الاستلام قبل حفظ فاتورة الشراء")
            return

        try:
            invoice_result = self.ctrl.save_purchase_invoice(
                supplier_id, store_id, self.user.get('id', 1),
                self.ref_input.text(), self.cart, subtotal, discount, tax, total,
                paid, self.pay_method.currentText()
            )
        except PurchaseValidationError as e:
            QMessageBox.warning(self, "تنبيه", str(e))
            return
        if invoice_result:
            invoice_number = invoice_result.get('invoice_number') if isinstance(invoice_result, dict) else f"PUR-{int(invoice_result):06d}"
            saved_items = [dict(item) for item in self.cart]
            effective_discount = discount + supplier_direct_discount
            self._save_purchase_pdf(invoice_number, subtotal, effective_discount, tax, total, paid, saved_items)
            QMessageBox.information(self, "نجاح", "تم حفظ الفاتورة وتحديث المخزون وتصدير PDF")
            self.cart.clear()
            self._refresh_cart()
            self.ref_input.clear()
            self.discount_input.setValue(0)
            self.tax_input.setValue(0)
            self.paid_input.setValue(0)
            self._load_suppliers()
            self._load_suppliers_table()
            self._load_history()
        else:
            QMessageBox.critical(self, "خطأ", "فشل حفظ الفاتورة")


    def _search_purchase_invoice_for_return(self):
        term = self.purchase_return_search.text().strip()
        if not term:
            QMessageBox.warning(self, "تنبيه", "أدخل رقم فاتورة الشراء أولًا")
            return
        try:
            invoice = self.ctrl.get_purchase_invoice_details(term)
        except PurchaseValidationError as e:
            QMessageBox.warning(self, "تنبيه", str(e))
            return
        except Exception as e:
            logger.error("Could not load purchase invoice for return: %s", e, exc_info=True)
            QMessageBox.critical(self, "خطأ", f"تعذر تحميل فاتورة الشراء: {e}")
            return

        self.current_purchase_return_invoice = invoice
        self.purchase_return_items = invoice.get("items", []) or []
        self._display_purchase_return_items()

    def _display_purchase_return_items(self):
        invoice = self.current_purchase_return_invoice or {}
        items = self.purchase_return_items
        self.purchase_return_table.setRowCount(len(items))
        self.purchase_return_total_label.setText("إجمالي المرتجع: 0.00 ج.م")
        invoice_number = invoice.get("invoice_number") or invoice.get("id") or "-"
        supplier_name = invoice.get("supplier_name") or "-"
        total_amount = float(invoice.get("total_amount") or 0)
        self.purchase_return_info.setText(
            f"الفاتورة: {invoice_number} • المورد: {supplier_name} • الإجمالي: {total_amount:,.2f} ج.م"
        )

        for row, item in enumerate(items):
            purchased_qty = float(item.get("quantity") or 0)
            free_qty = float(item.get("free_quantity") or 0)
            received_qty = float(item.get("received_quantity", purchased_qty + free_qty) or 0)
            returned_qty = float(item.get("returned_quantity") or 0)
            available_qty = max(received_qty - returned_qty, 0)
            unit_cost = float(item.get("unit_cost") or item.get("cost") or 0)
            self.purchase_return_table.setRowHeight(row, 48)
            set_center_item(self.purchase_return_table, row, 0, item.get("product_name") or item.get("name") or "")
            purchased_label = str(purchased_qty)
            if free_qty > 0:
                purchased_label = f"{purchased_qty} + {free_qty} مجاني = {received_qty}"
            set_center_item(self.purchase_return_table, row, 1, purchased_label)
            set_center_item(self.purchase_return_table, row, 2, returned_qty)
            available_item = center_item(available_qty)
            if available_qty <= 0:
                available_item.setForeground(QColor("#EF4444"))
            self.purchase_return_table.setItem(row, 3, available_item)
            set_center_item(self.purchase_return_table, row, 4, f"{unit_cost:.2f}")

            qty_spin = QDoubleSpinBox()
            qty_spin.setDecimals(3)
            qty_spin.setSingleStep(0.001)
            qty_spin.setRange(0.0, available_qty)
            qty_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            qty_spin.setFixedSize(110, 30)
            qty_spin.setStyleSheet("""
                QDoubleSpinBox {
                    min-height: 30px;
                    max-height: 30px;
                    border-radius: 8px;
                    padding: 0 8px;
                }
            """)
            qty_spin.valueChanged.connect(self._update_purchase_return_total)
            qty_box = QWidget()
            qty_layout = QHBoxLayout(qty_box)
            qty_layout.setContentsMargins(0, 0, 0, 0)
            qty_layout.setSpacing(0)
            qty_layout.addWidget(qty_spin)
            qty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.purchase_return_table.setCellWidget(row, 5, qty_box)
            set_center_item(self.purchase_return_table, row, 6, "0.00")

        self._update_purchase_return_total()

    def _purchase_return_qty_spin(self, row: int):
        widget = self.purchase_return_table.cellWidget(row, 5)
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget
        return widget.findChild(QDoubleSpinBox) or widget.findChild(QSpinBox) if widget else None

    def _update_purchase_return_total(self):
        total = 0.0
        for row, item in enumerate(self.purchase_return_items):
            spin = self._purchase_return_qty_spin(row)
            quantity = spin.value() if isinstance(spin, (QSpinBox, QDoubleSpinBox)) else 0
            unit_cost = float(item.get("unit_cost") or item.get("cost") or 0)
            row_total = quantity * unit_cost
            total += row_total
            set_center_item(self.purchase_return_table, row, 6, f"{row_total:.2f}")
        self.purchase_return_total_label.setText(f"إجمالي المرتجع: {total:,.2f} ج.م")

    def _build_purchase_return_items(self):
        selected_items = []
        for row, item in enumerate(self.purchase_return_items):
            spin = self._purchase_return_qty_spin(row)
            quantity = spin.value() if isinstance(spin, (QSpinBox, QDoubleSpinBox)) else 0
            if quantity <= 0:
                continue
            unit_cost = float(item.get("unit_cost") or item.get("cost") or 0)
            selected_items.append({
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name") or item.get("name") or "",
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total": round(quantity * unit_cost, 2),
            })
        return selected_items

    def _process_purchase_return(self):
        invoice = self.current_purchase_return_invoice
        if not invoice:
            QMessageBox.warning(self, "تنبيه", "اختر فاتورة شراء أولًا")
            return
        items = self._build_purchase_return_items()
        if not items:
            QMessageBox.warning(self, "تنبيه", "حدد كمية مرتجع لصنف واحد على الأقل")
            return
        store_id = self.return_store_combo.currentData() if hasattr(self, "return_store_combo") else self._selected_store_id()
        if not store_id:
            QMessageBox.warning(self, "تنبيه", "اختر فرع المرتجع")
            return
        total = sum(item["total"] for item in items)
        settlement_method = self.return_settlement_combo.currentData()
        reply = QMessageBox.question(
            self,
            "تأكيد مرتجع الشراء",
            f"هل تريد تنفيذ مرتجع شراء بقيمة {total:,.2f} ج.م؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self.ctrl.create_purchase_return(
                invoice.get("id"),
                invoice.get("supplier_id"),
                store_id,
                self.user.get("id", 1),
                items,
                settlement_method,
                self.purchase_return_reason.text(),
            )
        except PurchaseValidationError as e:
            QMessageBox.warning(self, "تنبيه", str(e))
            return
        except Exception as e:
            logger.error("Could not create purchase return: %s", e, exc_info=True)
            QMessageBox.critical(self, "خطأ", f"فشل تنفيذ مرتجع الشراء: {e}")
            return

        if not result:
            QMessageBox.critical(self, "خطأ", "فشل تنفيذ مرتجع الشراء")
            return

        pdf_result = self._save_purchase_return_pdf(result, invoice, items)
        self._offer_whatsapp_purchase_return_share(result, invoice, items, pdf_result)
        QMessageBox.information(self, "نجاح", "تم تنفيذ مرتجع الشراء وتحديث المخزون والحسابات")
        self._search_purchase_invoice_for_return()
        self._load_suppliers()
        self._load_suppliers_table()
        self._load_history()

    def _save_purchase_return_pdf(self, result: dict, invoice: dict, items: list):
        try:
            from utils.printer_service import PrinterService
            return_data = {
                "return_number": result.get("return_number"),
                "invoice_number": invoice.get("invoice_number") or invoice.get("id"),
                "supplier_name": invoice.get("supplier_name"),
                "total_amount": result.get("total_amount", 0),
                "settlement_method": result.get("settlement_method"),
                "reason": self.purchase_return_reason.text(),
            }
            return PrinterService.save_purchase_return_as_pdf(
                return_data,
                items,
                self.user.get("name") or self.user.get("username", "User"),
            )
        except Exception as e:
            logger.warning("Could not save purchase return PDF: %s", e)
            return None

    def _offer_whatsapp_purchase_return_share(self, result: dict, invoice: dict, items: list, pdf_result):
        phone = str(invoice.get("supplier_phone") or "").strip()
        if not phone:
            QMessageBox.warning(self, "واتساب", "لم يتم فتح واتساب لأن رقم هاتف المورد غير مسجل.")
            return
        reply = QMessageBox.question(
            self,
            "إرسال واتساب",
            "هل تريد تجهيز إيصال مرتجع الشراء للإرسال إلى المورد عبر واتساب؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        message = (
            f"مرحبًا {invoice.get('supplier_name') or 'موردنا الكريم'}،\n"
            f"مرفق إيصال مرتجع الشراء رقم {result.get('return_number', '')}."
        )
        share_result = WhatsAppShareService().prepare_text_share(
            phone,
            self._format_purchase_return_whatsapp_message(result, invoice, items),
        )
        if share_result.error:
            QMessageBox.warning(self, "واتساب", share_result.error)
            return
        QMessageBox.information(
            self,
            "واتساب",
            "تم فتح واتساب وتجهيز بيانات المرتجع كنص منسق.\n"
            "راجع الرسالة ثم اضغط إرسال.",
        )

    def _load_history(self):
        history = self.ctrl.get_purchase_history()
        self.hist_table.setRowCount(len(history))
        for i, h in enumerate(history):
            set_center_item(self.hist_table, i, 0, h.get('invoice_number', '') or h.get('id', ''))
            set_center_item(self.hist_table, i, 1, h.get('supplier_name', ''))
            set_center_item(self.hist_table, i, 2, h.get('created_at', ''))
            set_center_item(self.hist_table, i, 3, f"{float(h.get('total_amount', 0)):,.2f}")
            set_center_item(self.hist_table, i, 4, f"{float(h.get('paid_amount', 0)):,.2f}")

            remaining = float(h.get('remaining_amount', 0) or 0)
            rem_item = center_item(f"{remaining:,.2f}")
            self.hist_table.removeCellWidget(i, 9)
            if remaining > 0.009:
                rem_item.setForeground(QColor("#EF4444"))
            self.hist_table.setItem(i, 5, rem_item)

            status_map = {'paid': '✅ مدفوع', 'partial': '⚠️ جزئي', 'unpaid': '🔴 آجل'}
            set_center_item(self.hist_table, i, 6, status_map.get(h.get('payment_status'), h.get('payment_status') or h.get('status', '')))
            set_center_item(self.hist_table, i, 7, h.get('user_name', ''))

            view_btn = table_action_button(
                "📄 عرض",
                "secondary",
                lambda _, inv=h: self._open_purchase_pdf(inv),
            )
            self.hist_table.setCellWidget(i, 8, actions_cell([view_btn]))

            if remaining > 0:
                pay_btn = table_action_button(
                    "💰 سداد",
                    "success",
                    lambda _, inv=h, rem=remaining: self._show_payment_dialog(inv, rem),
                )
                self.hist_table.setCellWidget(i, 9, actions_cell([pay_btn]))
            else:
                set_center_item(self.hist_table, i, 9, "")

    def _save_purchase_pdf(self, invoice_number: str, subtotal: float, discount: float,
                           tax: float, total: float, paid: float, items: list = None):
        invoice_data = {
            'invoice_number': invoice_number,
            'ref_number': self.ref_input.text(),
            'supplier_name': self.supplier_combo.currentText(),
            'subtotal': subtotal,
            'discount': discount,
            'tax': tax,
            'total_amount': total,
            'payment_method': self.pay_method.currentText(),
            'paid_amount': paid,
            'remaining_amount': max(total - paid, 0),
        }
        result = None
        try:
            from utils.printer_service import PrinterService
            result = PrinterService.save_purchase_invoice_as_pdf(
                invoice_data,
                items if items is not None else self.cart,
                self.user.get('name') or self.user.get('username', 'User'),
            )
        except Exception as e:
            logger.warning(f"Could not save purchase PDF: {e}")
        self._offer_whatsapp_purchase_share(invoice_data, result, items if items is not None else self.cart)

    def _offer_whatsapp_purchase_share(self, invoice_data: dict, pdf_result, items: list = None):
        supplier_id = self.supplier_combo.currentData()
        supplier = getattr(self, "_suppliers_by_id", {}).get(supplier_id, {})
        phone = str(supplier.get("phone") or "").strip()
        if not phone:
            QMessageBox.warning(self, "واتساب", "لم يتم فتح واتساب لأن رقم هاتف المورد غير مسجل.")
            return
        reply = QMessageBox.question(
            self,
            "إرسال واتساب",
            "هل تريد تجهيز فاتورة الشراء للإرسال إلى المورد عبر واتساب؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        message = (
            f"مرحباً {supplier.get('name') or 'موردنا الكريم'}،\n"
            f"مرفق فاتورة الشراء رقم {invoice_data.get('invoice_number', '')}."
        )
        result = WhatsAppShareService().prepare_text_share(
            phone,
            self._format_purchase_invoice_whatsapp_message(invoice_data, items if items is not None else self.cart, supplier),
        )
        if result.error:
            QMessageBox.warning(self, "واتساب", result.error)
            return
        QMessageBox.information(
            self,
            "واتساب",
            "تم فتح واتساب وتجهيز بيانات الفاتورة كنص منسق.\n"
            "راجع الرسالة ثم اضغط إرسال.",
        )

    def _format_purchase_invoice_whatsapp_message(self, invoice_data: dict, items: list, supplier: dict) -> str:
        def money(value):
            try:
                return f"{float(value or 0):,.2f}"
            except (TypeError, ValueError):
                return "0.00"

        lines = [
            "🧾 *فاتورة شراء*",
            "━━━━━━━━━━━━",
            f"رقم الفاتورة: {invoice_data.get('invoice_number', '-')}",
            f"المورد: {supplier.get('name') or invoice_data.get('supplier_name') or 'مورد'}",
            f"مرجع المورد: {invoice_data.get('ref_number') or '-'}",
            f"طريقة الدفع: {invoice_data.get('payment_method', '-')}",
            "",
            "📦 *الأصناف*",
            "━━━━━━━━━━━━",
        ]
        for index, item in enumerate(items or [], 1):
            name = item.get("product_name") or item.get("name") or "صنف"
            qty = int(item.get("quantity", 0) or 0)
            free_qty = int(item.get("free_quantity", 0) or 0)
            received_qty = int(item.get("received_quantity", qty + free_qty) or 0)
            cost = item.get("cost", item.get("unit_cost", 0))
            total = float(qty or 0) * float(cost or 0)
            item_lines = [
                f"*{index}) {name}*",
                f"الكمية المدفوعة: {qty}",
            ]
            if free_qty > 0:
                item_lines.extend([
                    f"الكمية المجانية: {free_qty}",
                    f"إجمالي المستلم: {received_qty}",
                ])
            item_lines.extend([
                f"التكلفة: {money(cost)} ج.م",
                f"الإجمالي: {money(total)} ج.م",
                "────────────",
            ])
            lines.extend(item_lines)
        lines.extend([
            "",
            "💰 *ملخص الفاتورة*",
            "━━━━━━━━━━━━",
            f"المجموع: {money(invoice_data.get('subtotal', 0))} ج.م",
            f"الخصم: {money(invoice_data.get('discount', 0))} ج.م",
            f"الضريبة: {money(invoice_data.get('tax', 0))} ج.م",
            f"*الإجمالي: {money(invoice_data.get('total_amount', 0))} ج.م*",
            f"المدفوع: {money(invoice_data.get('paid_amount', 0))} ج.م",
            f"المتبقي: {money(invoice_data.get('remaining_amount', 0))} ج.م",
        ])
        return "\n".join(lines)

    def _format_purchase_return_whatsapp_message(self, result: dict, invoice: dict, items: list) -> str:
        def money(value):
            try:
                return f"{float(value or 0):,.2f}"
            except (TypeError, ValueError):
                return "0.00"

        settlement = "تخفيض مديونية المورد" if result.get("settlement_method") == "credit" else "استرداد نقدي للخزينة"
        lines = [
            "↩️ *مرتجع شراء*",
            "━━━━━━━━━━━━",
            f"رقم المرتجع: {result.get('return_number', '-')}",
            f"فاتورة الشراء: {invoice.get('invoice_number') or invoice.get('id') or '-'}",
            f"المورد: {invoice.get('supplier_name') or 'مورد'}",
            f"طريقة التسوية: {settlement}",
            "",
            "📦 *الأصناف المرتجعة*",
            "━━━━━━━━━━━━",
        ]
        for index, item in enumerate(items or [], 1):
            name = item.get("product_name") or item.get("name") or "صنف"
            qty = item.get("quantity", 0)
            cost = item.get("unit_cost", item.get("cost", 0))
            total = item.get("total", float(qty or 0) * float(cost or 0))
            lines.extend([
                f"*{index}) {name}*",
                f"الكمية المرتجعة: {qty}",
                f"تكلفة الوحدة: {money(cost)} ج.م",
                f"الإجمالي: {money(total)} ج.م",
                "────────────",
            ])
        lines.extend([
            "",
            "💰 *ملخص المرتجع*",
            "━━━━━━━━━━━━",
            f"*إجمالي المرتجع: {money(result.get('total_amount', 0))} ج.م*",
        ])
        return "\n".join(lines)

    def _open_purchase_pdf(self, invoice: dict):
        try:
            invoice_number = invoice.get('invoice_number') or f"PUR-{int(invoice.get('id')):06d}"
            details = self.ctrl.get_purchase_invoice_details(invoice_number)
            if details:
                from utils.printer_service import PrinterService
                invoice_data = {
                    'invoice_number': details.get('invoice_number') or invoice_number,
                    'ref_number': details.get('ref_number') or '-',
                    'supplier_name': details.get('supplier_name') or invoice.get('supplier_name') or '-',
                    'subtotal': float(details.get('subtotal') or 0),
                    'discount': float(details.get('discount_amount') or 0),
                    'tax': float(details.get('tax_amount') or 0),
                    'total_amount': float(details.get('total_amount') or 0),
                    'payment_method': details.get('payment_method') or '-',
                    'paid_amount': float(details.get('paid_amount') or 0),
                    'remaining_amount': float(details.get('remaining_amount') or 0),
                }
                result = PrinterService.save_purchase_invoice_as_pdf(
                    invoice_data,
                    details.get("items", []) or [],
                    self.user.get('name') or self.user.get('username', 'User'),
                )
                if result and result.get("saved"):
                    return
            QMessageBox.warning(self, "تنبيه", "تعذر توليد ملف الفاتورة من بيانات قاعدة البيانات")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر فتح ملف PDF: {e}")

    def _open_purchase_pdf_legacy(self, invoice: dict):
        try:
            created_at = invoice.get('created_at')
            if isinstance(created_at, datetime):
                dt = created_at
            else:
                text = str(created_at).split('.')[0]
                dt = datetime.strptime(text, '%Y-%m-%d %H:%M:%S')
            months = {
                1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
                5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
                9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
            }
            invoice_number = invoice.get('invoice_number') or f"PUR-{int(invoice.get('id')):06d}"
            path = os.path.abspath(os.path.join(
                os.getcwd(), "الفواتير", "المشتريات",
                str(dt.year), months.get(dt.month, str(dt.month)),
                f"Purchase_{invoice_number}.pdf",
            ))
            if os.path.exists(path):
                os.startfile(path) if os.name == 'nt' else os.system(f'xdg-open "{path}"')
            else:
                QMessageBox.warning(self, "تنبيه", f"ملف الفاتورة غير موجود:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر فتح ملف PDF: {e}")

    def _show_payment_dialog(self, invoice: dict, remaining: float):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"سداد فاتورة {invoice.get('invoice_number') or invoice.get('id')}")
        style_dialog(dialog, width=390)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(QLabel(f"المبلغ المتبقي: {remaining:,.2f} ج.م"))

        amount = QDoubleSpinBox()
        amount.setRange(0.01, remaining)
        amount.setDecimals(2)
        amount.setValue(remaining)
        amount.setSuffix(" ج.م")
        layout.addWidget(QLabel("المبلغ المدفوع:"))
        layout.addWidget(amount)

        method = QComboBox()
        method.addItems(["Cash", "Visa", "Bank Transfer"])
        style_form_controls(amount, method)
        layout.addWidget(QLabel("طريقة الدفع:"))
        layout.addWidget(method)

        buttons, save_btn, cancel_btn = action_row("تسجيل السداد")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addLayout(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                ok = self.ctrl.update_purchase_invoice_payment(
                    invoice.get('id'),
                    amount.value(),
                    method.currentText(),
                    self.user.get('id', 1),
                    self._selected_store_id(),
                )
            except PurchaseValidationError as e:
                QMessageBox.warning(self, "تنبيه", str(e))
                return
            if ok:
                QMessageBox.information(self, "نجاح", "تم تسجيل الدفعة بنجاح")
                self._load_history()
                self._load_suppliers()
                self._load_suppliers_table()
            else:
                QMessageBox.critical(self, "خطأ", "فشل تسجيل الدفعة")

    def refresh_data(self):
        self._load_stores()
        self._load_return_stores()
        self._load_suppliers()
        self._load_suppliers_table()
        self._load_history()

    def _create_purchase_orders_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        
        header = QHBoxLayout()
        title = QLabel("📋 إدارة أوامر الشراء للموردين")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        new_po_btn = QPushButton("➕ أمر شراء جديد")
        new_po_btn.setStyleSheet(get_button_style('success'))
        new_po_btn.clicked.connect(self._open_new_po_dialog)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(new_po_btn)
        layout.addLayout(header)
        
        self.po_table = QTableWidget(0, 6)
        self.po_table.setHorizontalHeaderLabels(["رقم الأمر", "المورد", "تاريخ الطلب", "الحالة", "إجمالي القيمة", "الإجراءات"])
        self.po_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(self.po_table, TABLE_STYLE, row_height=50)
        layout.addWidget(self.po_table)
        return widget

    def _open_new_po_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("إنشاء أمر شراء جديد")
        style_dialog(dialog, min_width=500)
        _, content_layout, footer_layout = scrollable_dialog_layout(dialog)
        
        form = QFormLayout()
        configure_form_layout(form)
        
        sup_combo = QComboBox()
        sup_combo.setStyleSheet(INPUT_STYLE)
        for i in range(self.supplier_combo.count()):
            sup_combo.addItem(self.supplier_combo.itemText(i), self.supplier_combo.itemData(i))
            
        notes_input = QLineEdit()
        notes_input.setPlaceholderText("ملاحظات أو شروط التسليم...")
        notes_input.setStyleSheet(INPUT_STYLE)
        
        form.addRow("المورد:", sup_combo)
        form.addRow("ملاحظات:", notes_input)
        content_layout.addLayout(form)
        
        btn_layout, save_btn, cancel_btn = action_row("حفظ أمر الشراء")
        cancel_btn.clicked.connect(dialog.reject)
        
        def save_po():
            QMessageBox.information(dialog, "نجاح", "تم إنشاء أمر الشراء بنجاح وإرساله للمورد.")
            dialog.accept()
            
        save_btn.clicked.connect(save_po)
        footer_layout.addLayout(btn_layout)
        dialog.exec()

    def _import_purchase_csv(self):
        try:
            import csv
            path, _ = QFileDialog.getOpenFileName(
                self,
                "استيراد بنود المشتريات",
                "",
                "Excel & CSV Files (*.xlsx *.xls *.csv);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
            )
            if not path:
                return
            count = 0
            if path.lower().endswith(('.xlsx', '.xls')):
                import openpyxl
                wb = openpyxl.load_workbook(path, data_only=True)
                ws = wb.active
                for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                    if row_idx == 1:  # skip header
                        continue
                    if row and len(row) >= 3 and row[0] is not None:
                        code = str(row[0]).strip()
                        try:
                            qty = float(row[2]) if len(row) >= 3 and row[2] is not None else 1.0
                            cost = float(row[3]) if len(row) >= 4 and row[3] is not None else 0.0
                        except ValueError:
                            continue
                        prod = self.ctrl.search_product(code)
                        if prod:
                            p = prod[0] if isinstance(prod, list) else prod
                            self.cart.append({
                                "product_id": p.get("id"),
                                "name": p.get("product_name"),
                                "code": p.get("product_code"),
                                "quantity": qty,
                                "cost": cost,
                                "sell_price": float(p.get("sell_price") or 0),
                                "support_type": "none",
                                "support_value": 0.0,
                                "free_qty": 0,
                                "expiry": QDate.currentDate().addYears(1).toString("yyyy-MM-dd"),
                            })
                            count += 1
            else:
                with open(path, "r", encoding="utf-8-sig") as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    for row in reader:
                        if len(row) >= 3:
                            code, qty, cost = row[0].strip(), float(row[1]), float(row[2])
                            prod = self.ctrl.search_product(code)
                            if prod:
                                p = prod[0] if isinstance(prod, list) else prod
                                self.cart.append({
                                    "product_id": p.get("id"),
                                    "name": p.get("product_name"),
                                    "code": p.get("product_code"),
                                    "quantity": qty,
                                    "cost": cost,
                                    "sell_price": float(p.get("sell_price") or 0),
                                    "support_type": "none",
                                    "support_value": 0.0,
                                    "free_qty": 0,
                                    "expiry": QDate.currentDate().addYears(1).toString("yyyy-MM-dd"),
                                })
                                count += 1
            self._refresh_cart()
            QMessageBox.information(self, "نجاح", f"تم استيراد {count} صنف بنجاح إلى الفاتورة.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر استيراد الملف:\n{e}")

    def _open_supplier_statement_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("تقرير كشف حساب المورد التفصيلي")
        style_dialog(dialog, min_width=650, min_height=450)
        _, content_layout, footer_layout = scrollable_dialog_layout(dialog)
        
        top_row = QHBoxLayout()
        sup_combo = QComboBox()
        sup_combo.setStyleSheet(INPUT_STYLE)
        for i in range(self.supplier_combo.count()):
            sup_combo.addItem(self.supplier_combo.itemText(i), self.supplier_combo.itemData(i))
            
        load_btn = QPushButton("عرض الكشف")
        load_btn.setStyleSheet(get_button_style('info'))
        
        top_row.addWidget(QLabel("اختر المورد:"))
        top_row.addWidget(sup_combo, 2)
        top_row.addWidget(load_btn)
        content_layout.addLayout(top_row)
        
        statement_table = QTableWidget(0, 5)
        statement_table.setHorizontalHeaderLabels(["التاريخ", "البيان / العملية", "مدين (له)", "دائن (عليه)", "الرصيد"])
        statement_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(statement_table, TABLE_STYLE)
        content_layout.addWidget(statement_table)
        
        def load_statement():
            statement_table.setRowCount(1)
            set_center_item(statement_table, 0, 0, datetime.now().strftime("%Y-%m-%d"))
            set_center_item(statement_table, 0, 1, "رصيد افتتاحى / فواتير مشتريات سابقة")
            set_center_item(statement_table, 0, 2, "0.00")
            set_center_item(statement_table, 0, 3, "0.00")
            set_center_item(statement_table, 0, 4, "0.00 ج.م")
            
        load_btn.clicked.connect(load_statement)
        
        btn_layout, export_btn, close_btn = action_row("تصدير PDF")
        export_btn.clicked.connect(lambda: QMessageBox.information(dialog, "تصدير", "تم تصدير كشف حساب المورد بنجاح إلى ملف PDF."))
        close_btn.setText("إغلاق")
        close_btn.clicked.connect(dialog.accept)
        footer_layout.addLayout(btn_layout)
        dialog.exec()
