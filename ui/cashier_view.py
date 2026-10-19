"""
Cashier View - واجهة الكاشير (Passive View)
لا تحتوي على أي منطق أعمال - تعرض البيانات وترسل الأحداث للـ Controller
"""

import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QTableWidget,
    QMessageBox,
    QComboBox,
    QDoubleSpinBox,
    QHeaderView,
    QGroupBox,
    QDialog,
    QScrollArea,
    QFrame,
    QFormLayout,
    QSpinBox,
    QAbstractItemView,
    QDateEdit,
    QInputDialog,
    QToolButton,
    QMenu,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QShortcut, QKeySequence, QColor
from ui.styles import (
    GLOBAL_STYLE,
    get_button_style,
    COLORS,
    TABLE_STYLE,
    GROUP_BOX_STYLE,
    INPUT_STYLE,
    LABEL_STYLE_HEADER,
    PANEL_STYLE,
    TOTAL_DISPLAY_STYLE,
)
from controllers.cashier_controller import CashierController
from ui.customer_display_view import CustomerDisplayWindow
from ui.table_helpers import (
    actions_cell,
    center_item,
    configure_table,
    table_action_button,
)
from utils.permissions import PermissionPolicy
from services.whatsapp_share_service import WhatsAppShareService

logger = logging.getLogger(__name__)


class CashierView(QWidget):
    """واجهة الكاشير - عرض فقط (Passive View)"""

    sale_completed = pyqtSignal()

    def __init__(
        self, controller: CashierController, user_info: dict = None, parent=None
    ):
        super().__init__(parent)
        self.setStyleSheet(GLOBAL_STYLE)
        self.ctrl = controller
        self.user_info = user_info or {}
        initial_store_id = self._resolve_drawer_store_id()
        if initial_store_id:
            self.ctrl.set_store(initial_store_id)
        self.current_order_id = None
        self.current_held_invoice_id = None
        self.customer_display = None
        self._status_serial = 0
        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self):
        """بناء الواجهة"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setMaximumWidth(1450)
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        main = QHBoxLayout(content)
        main.setSpacing(15)
        main.setContentsMargins(10, 10, 10, 10)

        # Left Panel (62%)
        self._build_left_panel()
        main.addWidget(self.left_panel, 62)

        # Right Panel (38%)
        self._build_right_panel()
        main.addWidget(self.right_panel, 38)

        self._load_discount_companies()
        self.scan_input.setFocus()

    def _user_store_id(self, default=None):
        store_id = self.user_info.get("store_id")
        try:
            return int(store_id) if store_id else default
        except (TypeError, ValueError):
            return default

    def _branch_store_ids(self):
        stores = (
            self.ctrl.get_operational_stores()
            if hasattr(self.ctrl, "get_operational_stores")
            else []
        )
        ids = set()
        for store in stores or []:
            try:
                ids.add(int(store.get("id")))
            except (TypeError, ValueError):
                continue
        return ids

    def _is_branch_store_id(self, store_id) -> bool:
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return False
        return store_id in self._branch_store_ids()

    def _resolve_drawer_store_id(self, ask_when_missing: bool = False):
        store_id = self._user_store_id()
        if store_id and self._is_branch_store_id(store_id):
            return store_id
        if not ask_when_missing:
            return None

        stores = (
            self.ctrl.get_operational_stores()
            if hasattr(self.ctrl, "get_operational_stores")
            else []
        )
        if not stores:
            QMessageBox.warning(
                self,
                "تنبيه",
                "لا يوجد فرع أو مخزن فعّال يمكن فتح درج عليه. راجع إعدادات الفروع.",
            )
            return None

        if len(stores) == 1:
            return int(stores[0].get("id"))

        labels = []
        store_by_label = {}
        for store in stores:
            label = (
                f"{store.get('store_name', '')} ({store.get('store_type', 'Branch')})"
            )
            labels.append(label)
            store_by_label[label] = store

        selected, ok = QInputDialog.getItem(
            self,
            "اختيار الفرع",
            "اختر الفرع أو المخزن الذي سيتم فتح درج الكاشير عليه:",
            labels,
            0,
            False,
        )
        if not ok or not selected:
            return None
        return int(store_by_label[selected].get("id"))

    def _active_cashier_store_id(self, ask_when_missing: bool = False):
        store_id = self._resolve_drawer_store_id(ask_when_missing=ask_when_missing)
        store_drawer = self._get_shared_open_drawer(store_id)
        if store_drawer and store_drawer.get("store_id"):
            return int(store_drawer.get("store_id"))
        return store_id

    # ── Left Panel ─────────────────────────────────────────

    def _build_left_panel(self):
        self.left_panel = QFrame()
        self.left_panel.setObjectName("LeftPanel")
        self.left_panel.setStyleSheet(PANEL_STYLE)
        layout = QVBoxLayout(self.left_panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        title = QLabel("🛒 فاتورة جديدة")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_on_brand']};")
        toolbar_layout.addWidget(title)

        self.drawer_status_label = QLabel()
        self.drawer_status_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-weight: 900; padding: 7px 10px; "
            f"background-color: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; border-radius: 10px;"
        )
        toolbar_layout.addWidget(self.drawer_status_label)

        self.admin_menu_btn = QToolButton()
        self.admin_menu_btn.setText("🛠️ إدارة الدرج والأمان")
        self.admin_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.admin_menu_btn.setStyleSheet(
            get_button_style("warning")
            + " font-size: 12px; font-weight: 900; min-height: 34px; padding: 4px 12px;"
        )
        self.admin_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        menu = QMenu(self)
        menu.setStyleSheet(GLOBAL_STYLE)
        menu.addAction("🔓 فتح درج", self._open_drawer_from_cashier)
        menu.addAction("🔒 غلق درج", self._close_drawer_from_cashier)
        menu.addSeparator()
        menu.addAction("🔒 قفل الشاشة", self._open_lock_screen_dialog)
        self.admin_menu_btn.setMenu(menu)
        toolbar_layout.addWidget(self.admin_menu_btn)

        toolbar_layout.addStretch()

        btns = [
            ("📦 الطلبات", self._open_orders_dialog, "warning"),
            ("⏸️ المعلقة", self._open_held_bills_dialog, "primary"),
            ("📜 السجل", self._open_history_dialog, "outline"),
            ("🔍 استعلام", self._open_product_inquiry, "info"),
            ("🖥️ شاشة العميل", self._toggle_customer_display, "primary"),
        ]
        for text, slot, style_key in btns:
            btn = QPushButton(text)
            btn.setFixedWidth(126)
            btn.setStyleSheet(
                get_button_style(style_key)
                + " font-size: 12px; font-weight: 900; min-height: 34px;"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            toolbar_layout.addWidget(btn)

        layout.addLayout(toolbar_layout)
        layout.addSpacing(10)
        QTimer.singleShot(0, self._refresh_drawer_status)

        # Search Bar
        search_layout = QHBoxLayout()
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("🔍 امسح الباركود أو ابحث بالاسم...")
        self.scan_input.setStyleSheet(
            INPUT_STYLE + "min-height: 50px; font-size: 16px; border-radius: 16px;"
        )
        self.scan_input.returnPressed.connect(self._on_scan)
        search_layout.addWidget(self.scan_input)
        layout.addLayout(search_layout)

        # Search Results
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(
            ["الكود", "المنتج", "السعر", "الضريبة%", "إضافة"]
        )
        configure_table(self.products_table, TABLE_STYLE, row_height=44)
        self.products_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.products_table.setMaximumHeight(180)
        self.products_table.hide()
        layout.addWidget(self.products_table)

        # Invoice Table
        lbl = QLabel("🛒 الفاتورة الحالية")
        lbl.setStyleSheet(LABEL_STYLE_HEADER)
        layout.addWidget(lbl)

        self.invoice_table = QTableWidget()
        self.invoice_table.setColumnCount(6)
        self.invoice_table.setHorizontalHeaderLabels(
            ["الكود", "المنتج", "السعر", "الكمية", "الإجمالي", "حذف"]
        )
        configure_table(self.invoice_table, TABLE_STYLE, row_height=46)
        self.invoice_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.invoice_table.setColumnWidth(3, 110)
        self.invoice_table.setColumnWidth(5, 86)
        layout.addWidget(self.invoice_table)

        self.items_count_label = QLabel("عدد الأصناف: 0")
        self.items_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.items_count_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-weight: 700;"
        )
        layout.addWidget(self.items_count_label)

    # ── Right Panel ────────────────────────────────────────

    def _build_right_panel(self):
        self.right_panel = QFrame()
        self.right_panel.setObjectName("RightPanel")
        self.right_panel.setStyleSheet(PANEL_STYLE)
        self.right_panel.setMinimumWidth(360)
        self.right_panel.setMaximumWidth(430)
        layout = QVBoxLayout(self.right_panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Customer Info
        cust_group = QGroupBox("👤 بيانات العميل")
        cust_group.setStyleSheet(GROUP_BOX_STYLE)
        cust_layout = QFormLayout()
        self.customer_name = QLineEdit()
        self.customer_name.setPlaceholderText("اسم العميل (اختياري)")
        self.customer_name.setStyleSheet(INPUT_STYLE)
        cust_layout.addRow("الاسم:", self.customer_name)

        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("رقم الهاتف")
        self.customer_phone.setStyleSheet(INPUT_STYLE)
        self.customer_phone.textChanged.connect(self._on_phone_changed)
        cust_layout.addRow("الهاتف:", self.customer_phone)

        self.customer_address = QLineEdit()
        self.customer_address.setPlaceholderText("العنوان")
        self.customer_address.setStyleSheet(INPUT_STYLE)
        cust_layout.addRow("العنوان:", self.customer_address)
        cust_group.setLayout(cust_layout)
        layout.addWidget(cust_group)

        # Payment
        pay_group = QGroupBox("💳 تفاصيل الدفع")
        pay_group.setStyleSheet(GROUP_BOX_STYLE)
        pay_layout = QFormLayout()

        self.discount_company_combo = QComboBox()
        self.discount_company_combo.setStyleSheet(INPUT_STYLE)
        self.discount_company_combo.addItem("بدون خصم شركة", None)
        self.discount_company_combo.currentIndexChanged.connect(
            self._on_discount_company_changed
        )
        pay_layout.addRow("خصم الشركة:", self.discount_company_combo)

        self.payment_combo = QComboBox()
        self.payment_combo.addItems(
            ["Cash (كاش)", "Card (فيزا)", "Credit (آجل)", "Mixed (مختلط)"]
        )
        self.payment_combo.setStyleSheet(INPUT_STYLE)
        self.payment_combo.currentIndexChanged.connect(self._on_payment_method_changed)
        pay_layout.addRow("نوع الدفع:", self.payment_combo)

        self.split_payment_widget = QWidget()
        split_layout = QHBoxLayout(self.split_payment_widget)
        split_layout.setContentsMargins(0, 0, 0, 0)
        self.cash_amount_input = QDoubleSpinBox()
        self.cash_amount_input.setMaximum(1000000)
        self.cash_amount_input.setPrefix("نقدًا: ")
        self.cash_amount_input.setStyleSheet(INPUT_STYLE)
        self.cash_amount_input.valueChanged.connect(self._update_change)
        self.card_amount_input = QDoubleSpinBox()
        self.card_amount_input.setMaximum(1000000)
        self.card_amount_input.setPrefix("فيزا: ")
        self.card_amount_input.setStyleSheet(INPUT_STYLE)
        self.card_amount_input.valueChanged.connect(self._update_change)
        split_layout.addWidget(self.cash_amount_input)
        split_layout.addWidget(self.card_amount_input)
        self.split_payment_label = QLabel("تقسيم الدفع:")
        self.split_payment_label.hide()
        self.split_payment_widget.hide()
        pay_layout.addRow(self.split_payment_label, self.split_payment_widget)

        self.paid_amount_input = QDoubleSpinBox()
        self.paid_amount_input.setMaximum(1000000)
        self.paid_amount_input.setStyleSheet(INPUT_STYLE)
        self.paid_amount_input.valueChanged.connect(self._update_change)
        pay_layout.addRow("المدفوع:", self.paid_amount_input)

        pay_group.setLayout(pay_layout)
        layout.addWidget(pay_group)

        self.promo_label = QLabel("")
        self.promo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.promo_label.setStyleSheet(
            f"background: {COLORS['success']}; color: {COLORS['text_on_brand']}; padding: 8px; "
            "border-radius: 8px; font-size: 13px; font-weight: bold;"
        )
        self.promo_label.hide()
        layout.addWidget(self.promo_label)

        # Totals Display
        summary = QFormLayout()
        self.lbl_subtotal = QLabel("0.00 ج.م")
        self.lbl_subtotal.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        summary.addRow(QLabel("المجموع الفرعي:"), self.lbl_subtotal)

        self.lbl_tax = QLabel("0.00 ج.م")
        self.lbl_tax.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        summary.addRow(QLabel("ضريبة (VAT):"), self.lbl_tax)
        layout.addLayout(summary)

        self.total_label = QLabel("0.00 ج.م")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.total_label.setStyleSheet(TOTAL_DISPLAY_STYLE + "border-radius: 16px;")
        layout.addWidget(self.total_label)

        self.change_label = QLabel("الباقي: 0.00 ج.م")
        self.change_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.change_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.change_label.setStyleSheet(
            f"color: {COLORS['success']}; padding: 5px; background-color: {COLORS['bg_panel']}; border-radius: 8px;"
        )
        layout.addWidget(self.change_label)

        # Action Buttons
        btns = QVBoxLayout()
        btns.setSpacing(10)

        checkout_btn = QPushButton("✅ دفع وطباعة (F12)")
        checkout_btn.setMinimumHeight(52)
        checkout_btn.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        checkout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        checkout_btn.setStyleSheet(
            get_button_style("success") + "border-radius: 16px; font-size: 15px;"
        )
        checkout_btn.clicked.connect(lambda: self._on_checkout(as_pdf=False))
        btns.addWidget(checkout_btn)

        pdf_btn = QPushButton("📄 دفع وحفظ PDF")
        pdf_btn.setMinimumHeight(44)
        pdf_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        pdf_btn.setStyleSheet(
            f"background-color: {COLORS['secondary']}; color: {COLORS['text_on_brand']}; border-radius: 14px; padding: 7px; font-weight: 900;"
        )
        pdf_btn.clicked.connect(lambda: self._on_checkout(as_pdf=True))
        btns.addWidget(pdf_btn)

        sub = QHBoxLayout()

        self.tax_invoice_btn = QPushButton("🧾 فاتورة ضريبية")
        self.tax_invoice_btn.setMinimumHeight(42)
        self.tax_invoice_btn.setStyleSheet(
            f"background-color: #7C3AED; color: {COLORS['text_on_brand']}; border-radius: 8px; "
            "font-weight: bold; font-size: 13px; padding: 5px;"
        )
        self.tax_invoice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tax_invoice_btn.clicked.connect(self._on_tax_invoice)
        sub.addWidget(self.tax_invoice_btn)

        hold_btn = QPushButton("⏸️ تعليق")
        hold_btn.setMinimumHeight(42)
        hold_btn.setStyleSheet(get_button_style("warning"))
        hold_btn.clicked.connect(self._hold_invoice)
        sub.addWidget(hold_btn)

        clear_btn = QPushButton("🗑️ مسح")
        clear_btn.setMinimumHeight(42)
        clear_btn.setStyleSheet(get_button_style("danger"))
        clear_btn.clicked.connect(self._on_clear)
        sub.addWidget(clear_btn)

        btns.addLayout(sub)
        layout.addLayout(btns)

        self.operation_status_label = QLabel("جاهز للبيع")
        self.operation_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.operation_status_label.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; color: {COLORS['text_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 8px; "
            "font-weight: 700;"
        )
        layout.addWidget(self.operation_status_label)

    # ── Shortcuts ──────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            self.scan_input.setFocus
        )
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._hold_invoice)
        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(
            self._open_held_bills_dialog
        )
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(
            self._open_product_inquiry
        )
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(
            self._open_orders_dialog
        )
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self).activated.connect(
            self._remove_selected_item
        )
        QShortcut(QKeySequence(Qt.Key.Key_F12), self).activated.connect(
            lambda: self._on_checkout(as_pdf=False)
        )
        # Fast payment method selection shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_F1), self).activated.connect(lambda: self.payment_combo.setCurrentIndex(0))
        QShortcut(QKeySequence(Qt.Key.Key_F2), self).activated.connect(lambda: self.payment_combo.setCurrentIndex(1))
        QShortcut(QKeySequence(Qt.Key.Key_F3), self).activated.connect(lambda: self.payment_combo.setCurrentIndex(2))
        QShortcut(QKeySequence(Qt.Key.Key_F4), self).activated.connect(lambda: self.payment_combo.setCurrentIndex(3))

    # ── Event Handlers (تنادي الـ Controller) ─────────────

    def _not_implemented(self):
        QMessageBox.information(
            self,
            "تحت التطوير",
            "هذه الميزة قيد التطوير وسيتم نقلها قريباً للمعمارية الجديدة.",
        )

    def _focus_scan(self):
        self.scan_input.setFocus()
        self.scan_input.selectAll()

    def _set_operation_status(
        self, message: str, kind: str = "info", timeout_ms: int = 6000
    ):
        self._status_serial += 1
        status_serial = self._status_serial
        colors = {
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "danger": COLORS["danger"],
            "info": COLORS["info"],
        }
        color = colors.get(kind, COLORS["info"])
        self.operation_status_label.setText(message)
        self.operation_status_label.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; color: {color}; "
            f"border: 1px solid {color}; border-radius: 8px; padding: 8px; "
            "font-weight: 800;"
        )
        if timeout_ms:
            QTimer.singleShot(
                timeout_ms,
                lambda: (
                    self._set_operation_status("جاهز للبيع", "info", 0)
                    if status_serial == self._status_serial
                    else None
                ),
            )

    def _print_result_message(self, result, as_pdf: bool) -> tuple[str, str]:
        if as_pdf:
            if isinstance(result, dict):
                saved = bool(result.get("saved"))
                return (
                    (
                        "تم حفظ الفاتورة PDF بنجاح"
                        if saved
                        else "تم البيع لكن تعذر حفظ PDF"
                    ),
                    "success" if saved else "warning",
                )
            return (
                "تم حفظ الفاتورة PDF بنجاح" if result else "تم البيع لكن تعذر حفظ PDF",
                "success" if result else "warning",
            )
        if isinstance(result, dict):
            if result.get("printed"):
                return "تم البيع والطباعة بنجاح", "success"
            if result.get("saved"):
                return "تم البيع وحُفظ PDF تلقائيًا لعدم توفر طابعة فعلية", "warning"
            return "تم البيع لكن تعذرت الطباعة وحفظ PDF", "warning"
        return (
            "تم البيع والطباعة بنجاح" if result else "تم البيع لكن تعذرت الطباعة",
            "success" if result else "warning",
        )

    def _toggle_customer_display(self):
        display = self._ensure_customer_display()
        if display.isVisible():
            display.close()
            return
        display.open_on_customer_screen()
        self._schedule_customer_totals()

    def _ensure_customer_display(self):
        if self.customer_display is None:
            self.customer_display = CustomerDisplayWindow()
            self.customer_display.destroyed.connect(
                lambda: setattr(self, "customer_display", None)
            )
        return self.customer_display

    def _customer_display_is_active(self) -> bool:
        return bool(self.customer_display and self.customer_display.isVisible())

    def _notify_customer_item(self, product_id: int):
        if not self._customer_display_is_active():
            return
        item = next(
            (
                cart_item
                for cart_item in self.ctrl.current_items
                if cart_item.product_id == product_id
            ),
            None,
        )
        if not item:
            return
        self.customer_display.show_item(
            item.product_name, item.unit_price, item.quantity, item.net_total
        )
        self.customer_display.schedule_totals(self.ctrl.calculate_totals())

    def _schedule_customer_totals(self):
        if not self._customer_display_is_active():
            return
        if not self.ctrl.current_items:
            self.customer_display.reset()
            return
        self.customer_display.schedule_totals(self.ctrl.calculate_totals())

    def _on_scan(self):
        """عند مسح باركود"""
        code = self.scan_input.text().strip()
        if not code:
            return

        qty = 1.0
        if '*' in code:
            parts = code.split('*', 1)
            try:
                qty = float(parts[0])
                code = parts[1].strip()
            except ValueError:
                pass

        try:
            store_id = self._active_cashier_store_id()
            if store_id:
                self.ctrl.set_store(store_id)
            result = self.ctrl.scan_item(code, qty)
            if result.added:
                self._refresh_invoice()
                self._notify_customer_item(result.product.id)
                self.scan_input.clear()
                self._focus_scan()
            else:
                self._show_search_results(result.search_results)
        except ValueError as exc:
            QMessageBox.warning(self, "تنبيه", str(exc))
            self._focus_scan()

    def _show_search_results(self, products):
        """عرض نتائج البحث"""
        if not products:
            QMessageBox.warning(self, "غير موجود", "لم يتم العثور على المنتج")
            return
        self.products_table.show()
        self.products_table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.products_table.setItem(row, 0, center_item(p.product_code))
            self.products_table.setItem(row, 1, center_item(p.product_name))
            self.products_table.setItem(row, 2, center_item(f"{p.sell_price:.2f}"))
            self.products_table.setItem(
                row, 3, center_item(f"{p.tax_percent:.0f}%")
            )
            btn = QPushButton("إضافة")
            btn.setStyleSheet(get_button_style("success"))
            btn.clicked.connect(lambda _, prod=p: self._add_search_result(prod))
            self.products_table.setCellWidget(row, 4, btn)

    def _add_search_result(self, product):
        """إضافة منتج من نتائج البحث"""
        try:
            store_id = self._active_cashier_store_id()
            if store_id:
                self.ctrl.set_store(store_id)
            self.ctrl.add_item(product)
            self._refresh_invoice()
            self._notify_customer_item(product.id)
            self.products_table.hide()
            self.scan_input.clear()
            self.scan_input.setFocus()
        except ValueError as exc:
            QMessageBox.warning(self, "تنبيه", str(exc))

    def _on_discount_company_changed(self):
        company = self.discount_company_combo.currentData()
        self.ctrl.set_discount_company(company)
        self._update_totals()
        self._schedule_customer_totals()

    def _load_discount_companies(self):
        try:
            selected_id = (
                (self.discount_company_combo.currentData() or {}).get("id")
                if self.discount_company_combo.currentData()
                else None
            )
            self.discount_company_combo.blockSignals(True)
            self.discount_company_combo.clear()
            self.discount_company_combo.addItem("بدون خصم شركة", None)
            for company in self.ctrl.get_discount_companies():
                self.discount_company_combo.addItem(
                    f"{company.get('name', '')} - {float(company.get('discount_percent') or 0):g}%",
                    company,
                )
            if selected_id:
                for index in range(self.discount_company_combo.count()):
                    if (self.discount_company_combo.itemData(index) or {}).get(
                        "id"
                    ) == selected_id:
                        self.discount_company_combo.setCurrentIndex(index)
                        break
        except Exception as exc:
            self._set_operation_status("تعذر تحميل قائمة خصومات الشركات", "warning")
        finally:
            self.discount_company_combo.blockSignals(False)

    def _on_phone_changed(self):
        phone = self.customer_phone.text().strip()
        if len(phone) < 8:
            self.customer_name.setProperty("auto_filled", False)
            self.customer_address.setProperty("auto_filled", False)
            return
        customer = self.ctrl.get_customer_by_phone(phone)
        if not customer:
            return
        if not self.customer_name.text().strip() or self.customer_name.property(
            "auto_filled"
        ):
            self.customer_name.setText(customer.get("customer_name", "") or "")
            self.customer_name.setProperty("auto_filled", True)
        if not self.customer_address.text().strip() or self.customer_address.property(
            "auto_filled"
        ):
            self.customer_address.setText(customer.get("customer_address", "") or "")
            self.customer_address.setProperty("auto_filled", True)

    def _on_payment_method_changed(self):
        totals = self.ctrl.calculate_totals()
        total = totals["total"]
        payment = self._selected_payment_method()
        is_mixed_payment = payment == "Mixed"
        self.split_payment_label.setVisible(is_mixed_payment)
        self.split_payment_widget.setVisible(is_mixed_payment)
        if payment == "Card":
            self.paid_amount_input.setValue(total)
        elif payment == "Credit":
            self.paid_amount_input.setValue(0)
        elif payment == "Mixed":
            self.cash_amount_input.setValue(total)
            self.card_amount_input.setValue(0)
            self.paid_amount_input.setValue(total)
        else:
            self.paid_amount_input.setValue(total)
        self._update_change()

    def _selected_payment_method(self):
        method_map = {0: "Cash", 1: "Card", 2: "Credit", 3: "Mixed"}
        return method_map.get(self.payment_combo.currentIndex(), "Cash")

    def _on_tax_invoice(self):
        """فتح نافذة الفاتورة الضريبية"""
        dialog = QDialog(self)
        dialog.setWindowTitle("🧾 بيانات الفاتورة الضريبية")
        dialog.resize(450, 400)
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['bg_main']}; }}
            QLabel {{ color: {COLORS['text_primary']}; font-weight: bold; font-size: 13px; }}
            QLineEdit {{ {INPUT_STYLE} min-height: 40px; font-size: 13px; }}
        """)
        layout = QFormLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🏢 بيانات الشركة المشترية")
        title.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['accent']}; margin-bottom: 10px;")
        layout.addRow(title)

        fields = {}
        for key, label, placeholder in [
            ("company_name", "اسم الشركة:", "اسم الشركة أو المنشأة"),
            ("tax_id_number", "رقم البطاقة الضريبية:", "مثل: 123-456-789"),
            ("commercial_registry", "السجل التجاري:", "رقم السجل التجاري"),
            ("company_address", "العنوان:", "عنوان الشركة"),
            ("company_phone", "الهاتف:", "رقم هاتف الشركة"),
        ]:
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            if self.ctrl.tax_invoice_data:
                inp.setText(getattr(self.ctrl.tax_invoice_data, key, ""))
            layout.addRow(label, inp)
            fields[key] = inp

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("✅ حفظ")
        save_btn.setStyleSheet(get_button_style("success") + "min-height: 45px;")
        remove_btn = QPushButton("🗑️ إلغاء الضريبية")
        remove_btn.setStyleSheet(get_button_style("danger") + "min-height: 45px;")
        cancel_btn = QPushButton("✖ إغلاق")
        cancel_btn.setStyleSheet(get_button_style("outline") + "min-height: 45px;")

        def save():
            name = fields["company_name"].text().strip()
            if not name:
                QMessageBox.warning(dialog, "تنبيه", "يجب إدخال اسم الشركة على الأقل")
                return
            self.ctrl.set_tax_invoice({k: v.text().strip() for k, v in fields.items()})
            self.tax_invoice_btn.setStyleSheet(
                f"background-color: {COLORS['success_hover']}; color: {COLORS['text_on_brand']}; border-radius: 8px; "
                f"font-weight: bold; font-size: 13px; padding: 5px; border: 2px solid {COLORS['success']};"
            )
            self.tax_invoice_btn.setText("✅ فاتورة ضريبية")
            dialog.accept()

        def remove():
            self.ctrl.clear_tax_invoice()
            self.tax_invoice_btn.setStyleSheet(
                f"background-color: {COLORS['purple']}; color: {COLORS['text_on_brand']}; border-radius: 8px; "
                "font-weight: bold; font-size: 13px; padding: 5px;"
            )
            self.tax_invoice_btn.setText("🧾 فاتورة ضريبية")
            dialog.accept()

        save_btn.clicked.connect(save)
        remove_btn.clicked.connect(remove)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        dialog.show()
        # Store reference to prevent garbage collection if not parented correctly
        setattr(self, f"_{dialog.windowTitle()}_dialog", dialog)

    def _refresh_drawer_status(self):
        store_id = self._resolve_drawer_store_id()
        store_drawer = self._get_shared_open_drawer(store_id)
        if store_drawer:
            self.ctrl.set_store(store_drawer.get("store_id") or store_id)
            opener = store_drawer.get("cashier_name", "غير معروف")
            store_name = (
                store_drawer.get("store_name")
                or f"فرع {store_drawer.get('store_id', '')}"
            )
            self.drawer_status_label.setText(f"درج مفتوح: {opener} - {store_name}")
            self.drawer_status_label.setStyleSheet(
                f"color: {COLORS['success']}; font-weight: 800; padding: 4px 8px;"
            )
        else:
            self.drawer_status_label.setText("لا يوجد درج مفتوح")
            self.drawer_status_label.setStyleSheet(
                f"color: {COLORS['warning']}; font-weight: 800; padding: 4px 8px;"
            )
            if store_id:
                self.ctrl.set_store(store_id)

    def _can_use_any_branch_drawer(self) -> bool:
        policy = PermissionPolicy(self.user_info)
        return policy.is_admin or policy.is_developer

    def _get_shared_open_drawer(self, store_id: int = None):
        store_id = store_id or self._resolve_drawer_store_id()
        store_drawer = self.ctrl.get_store_open_drawer(store_id) if store_id else None
        if store_drawer:
            return store_drawer
        if self._can_use_any_branch_drawer() and hasattr(
            self.ctrl, "get_any_open_drawer"
        ):
            return self.ctrl.get_any_open_drawer()
        return None

    def _open_drawer_from_cashier(self):
        store_id = self._resolve_drawer_store_id(ask_when_missing=True)
        if not store_id:
            return
        user_id = self.user_info.get("id", 1)

        existing = self._get_shared_open_drawer(store_id)
        if existing:
            store_name = (
                existing.get("store_name") or f"فرع {existing.get('store_id', '')}"
            )
            QMessageBox.information(
                self,
                "تنبيه",
                f"يوجد درج مفتوح بالفعل بواسطة {existing.get('cashier_name', 'غير معروف')} في {store_name} وسيتم استخدامه كنقطة مشاركة.",
            )
            self._refresh_drawer_status()
            return

        balance, ok = QInputDialog.getDouble(
            self,
            "فتح درج",
            "رصيد بداية الدرج:",
            0,
            0,
            1000000,
            2,
        )
        if not ok:
            return

        if self.ctrl.open_drawer(store_id, user_id, balance):
            self._set_operation_status("تم فتح درج الكاشير بنجاح", "success")
        else:
            QMessageBox.warning(
                self, "تنبيه", "تعذر فتح الدرج. ربما يوجد درج مفتوح بالفعل."
            )
        self._refresh_drawer_status()
        QTimer.singleShot(0, self._focus_scan)

    def _close_drawer_from_cashier(self):
        store_id = self._resolve_drawer_store_id()
        user_id = self.user_info.get("id", 1)
        store_drawer = self._get_shared_open_drawer(store_id)
        if not store_drawer:
            QMessageBox.information(self, "تنبيه", "لا يوجد درج مفتوح متاح للاستخدام")
            self._refresh_drawer_status()
            return

        if (
            store_drawer.get("cashier_id") != user_id
            and not PermissionPolicy(self.user_info).can_close_shared_drawer()
        ):
            QMessageBox.warning(
                self, "صلاحية مرفوضة", "لا يمكنك غلق درج مفتوح بواسطة مستخدم آخر"
            )
            return

        from ui.denomination_dialog import DenominationDialog
        dialog = DenominationDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        cash, card, details = dialog.get_results()

        drawer_store_id = store_drawer.get("store_id") or store_id
        if self.ctrl.close_drawer(
            store_drawer.get("id"), cash, card, user_id, drawer_store_id, details
        ):
            QMessageBox.information(self, "تم", "تم غلق درج الكاشير بنجاح")
        else:
            QMessageBox.warning(self, "خطأ", "تعذر غلق الدرج")
        self._refresh_drawer_status()

    def _on_checkout(self, as_pdf=False):
        """إتمام البيع عبر الـ Controller"""
        if not self.ctrl.current_items:
            QMessageBox.warning(self, "تنبيه", "لا توجد أصناف في الفاتورة")
            return

        totals = self.ctrl.calculate_totals()
        total = totals["total"]
        payment = self._selected_payment_method()

        if payment == "Mixed":
            cash = self.cash_amount_input.value()
            card = self.card_amount_input.value()
            if (cash + card) < total - 0.01:
                QMessageBox.warning(
                    self, "تنبيه", "مجموع النقدي والفيزا يجب أن يغطي إجمالي الفاتورة على الأقل"
                )
                return
        elif payment == "Card":
            cash = 0
            card = total
        elif payment == "Credit":
            cash = self.paid_amount_input.value()
            card = 0
        else:
            cash = self.paid_amount_input.value()
            card = 0
        if payment == "Cash" and cash == 0:
            cash = total

        try:
            store_id = self._resolve_drawer_store_id()
            user_id = self.user_info.get("id", 1)
            drawer_id = None
            drawer_status = self.ctrl.get_drawer_status(user_id)
            if drawer_status and drawer_status.get("is_open"):
                drawer_id = drawer_status.get("id")
                store_id = drawer_status.get("store_id") or store_id
            else:
                store_drawer = self._get_shared_open_drawer(store_id)
                if store_drawer:
                    if (
                        store_drawer.get("cashier_id") != user_id
                        and not PermissionPolicy(self.user_info).can_use_shared_drawer()
                    ):
                        QMessageBox.warning(
                            self,
                            "تنبيه",
                            f"هذا الدرج مفتوح بواسطة {store_drawer.get('cashier_name', 'كاشير آخر')}.\nلا تملك صلاحية استخدام درج مشترك.",
                        )
                        return
                    drawer_id = store_drawer.get("id")
                    store_id = store_drawer.get("store_id") or store_id
                else:
                    reply = QMessageBox.question(
                        self,
                        "تنبيه",
                        "لا يوجد درج كاشير مفتوح في هذا الفرع.\nهل تريد فتح درج الآن؟",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                    self._open_drawer_from_cashier()
                    store_drawer = self._get_shared_open_drawer(store_id)
                    if not store_drawer:
                        return
                    drawer_id = store_drawer.get("id")
                    store_id = store_drawer.get("store_id") or store_id

            invoice_number = self.ctrl.checkout(
                store_id=store_id,
                cashier_id=user_id,
                drawer_id=drawer_id,
                payment_method=payment,
                cash_amount=cash,
                card_amount=card,
                customer_name=self.customer_name.text(),
                customer_phone=self.customer_phone.text(),
                customer_address=self.customer_address.text(),
            )

            # Printing
            print_data, items = self.ctrl.get_print_data(
                invoice_number,
                drawer_id,
                payment,
                cash,
                card,
                self.paid_amount_input.value(),
                self.customer_name.text(),
                self.customer_phone.text(),
                self.customer_address.text(),
            )

            user_name = self.user_info.get("full_name", "Cashier")

            print_message = "تم حفظ الفاتورة بنجاح"
            print_kind = "success"
            try:
                print_result = self.ctrl.print_receipt(
                    print_data, items, user_name, as_pdf
                )
                print_message, print_kind = self._print_result_message(
                    print_result, as_pdf
                )
                self._offer_whatsapp_invoice_share(print_data, items)
            except Exception as print_error:
                print_message = f"تم البيع لكن فشلت الطباعة: {print_error}"
                print_kind = "warning"

            if self.current_order_id:
                self.ctrl.mark_order_delivered(self.current_order_id)
            if self.current_held_invoice_id:
                self.ctrl.delete_resumed_held_invoice(self.current_held_invoice_id)

            self._refresh_drawer_status()
            self.sale_completed.emit()
            self._on_clear()
            self._set_operation_status(
                f"فاتورة #{invoice_number} - {print_message}", print_kind
            )

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ: {str(e)}")

    def _offer_whatsapp_invoice_share(self, invoice_data: dict, items: list):
        phone = str(
            invoice_data.get("customer_phone") or self.customer_phone.text() or ""
        ).strip()
        if not phone:
            return
        reply = QMessageBox.question(
            self,
            "إرسال واتساب",
            "هل تريد تجهيز فاتورة البيع للإرسال عبر واتساب؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        result = WhatsAppShareService().prepare_text_share(
            phone,
            self._format_sales_invoice_whatsapp_message(invoice_data, items),
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

    def _format_sales_invoice_whatsapp_message(
        self, invoice_data: dict, items: list
    ) -> str:
        def money(value):
            try:
                return f"{float(value or 0):,.2f}"
            except (TypeError, ValueError):
                return "0.00"

        lines = [
            "🧾 *فاتورة بيع*",
            "━━━━━━━━━━━━",
            f"رقم الفاتورة: {invoice_data.get('invoice_number', '-')}",
            f"التاريخ: {invoice_data.get('date') or invoice_data.get('created_at') or '-'}",
            f"العميل: {invoice_data.get('customer_name') or 'عميل نقدي'}",
        ]
        if invoice_data.get("customer_phone"):
            lines.append(f"هاتف العميل: {invoice_data.get('customer_phone')}")
        lines.extend(
            [
                f"طريقة الدفع: {invoice_data.get('payment_method', '-')}",
                "",
                "📦 *الأصناف*",
                "━━━━━━━━━━━━",
            ]
        )
        for index, item in enumerate(items or [], 1):
            name = item.get("product_name") or item.get("name") or "صنف"
            qty = item.get("quantity", 0)
            price = item.get("price", item.get("unit_price", 0))
            gross_total = item.get("gross_total", float(qty or 0) * float(price or 0))
            line_discount = float(
                item.get("line_discount") or item.get("discount") or 0
            )
            total = item.get("total", gross_total - line_discount)
            lines.extend(
                [
                    f"*{index}) {name}*",
                    f"الكمية: {qty}",
                    f"السعر: {money(price)} ج.م",
                ]
            )
            if line_discount > 0:
                lines.extend(
                    [
                        f"قبل الخصم: {money(gross_total)} ج.م",
                        f"خصم الصنف/العرض: {money(line_discount)} ج.م",
                        f"صافي الصنف: {money(total)} ج.م",
                    ]
                )
            else:
                lines.append(f"الإجمالي: {money(total)} ج.م")
            lines.append("────────────")
        lines.extend(
            [
                "",
                "💰 *ملخص الفاتورة*",
                "━━━━━━━━━━━━",
                f"قبل الخصم: {money(invoice_data.get('gross_total', invoice_data.get('total_amount', 0)))} ج.م",
                f"خصم يدوي: {money(invoice_data.get('discount', 0))} ج.م",
                f"خصم عروض: {money(invoice_data.get('promo_discount', 0))} ج.م",
                f"إجمالي الخصم: {money(invoice_data.get('total_discount', 0))} ج.م",
                f"ضريبة: {money(invoice_data.get('tax_amount', invoice_data.get('tax', 0)))} ج.م",
                f"*الصافي: {money(invoice_data.get('total_amount', 0))} ج.م*",
            ]
        )
        if float(invoice_data.get("tendered", 0) or 0) > 0:
            lines.append(f"المدفوع: {money(invoice_data.get('tendered'))} ج.م")
            lines.append(f"الباقي: {money(invoice_data.get('change'))} ج.م")
        lines.extend(["", "شكرًا لتعاملكم معنا."])
        return "\n".join(lines)

    def _on_clear(self):
        """مسح الفاتورة"""
        self.ctrl.clear_cart()
        self.current_order_id = None
        self.current_held_invoice_id = None
        self.invoice_table.setRowCount(0)
        self.scan_input.clear()
        self.customer_name.clear()
        self.customer_phone.clear()
        self.customer_address.clear()
        self.discount_company_combo.blockSignals(True)
        self.discount_company_combo.setCurrentIndex(0)
        self.discount_company_combo.blockSignals(False)
        self.ctrl.clear_discount_company()
        self.paid_amount_input.setValue(0)
        self.cash_amount_input.setValue(0)
        self.card_amount_input.setValue(0)
        self.split_payment_label.hide()
        self.split_payment_widget.hide()
        self.total_label.setText("0.00 ج.م")
        self.lbl_subtotal.setText("0.00 ج.م")
        self.lbl_tax.setText("0.00 ج.م")
        self.change_label.setText("الباقي: 0.00 ج.م")
        self.payment_combo.setCurrentIndex(0)
        self.tax_invoice_btn.setStyleSheet(
            f"background-color: #7C3AED; color: {COLORS['text_on_brand']}; border-radius: 8px; "
            "font-weight: bold; font-size: 13px; padding: 5px;"
        )
        self.tax_invoice_btn.setText("🧾 فاتورة ضريبية")
        self.products_table.hide()
        self.promo_label.hide()
        self.items_count_label.setText("عدد الأصناف: 0")
        if self._customer_display_is_active():
            self.customer_display.reset()
        self.scan_input.setFocus()

    # ── UI Refresh Methods ─────────────────────────────────

    def _refresh_invoice(self):
        """تحديث جدول الفاتورة من الـ Controller"""
        items = self.ctrl.current_items
        self.invoice_table.setRowCount(len(items))

        for row, item in enumerate(items):
            self.invoice_table.setRowHeight(row, 46)
            self.invoice_table.setItem(row, 0, center_item(item.product_code))
            self.invoice_table.setItem(row, 1, center_item(item.product_name))
            self.invoice_table.setItem(
                row, 2, center_item(f"{item.unit_price:.2f}")
            )

            qty_spin = QDoubleSpinBox()
            qty_spin.setDecimals(3)
            qty_spin.setMinimum(0.001)
            qty_spin.setSingleStep(0.001)
            qty_spin.setMaximum(
                max(
                    float(item.quantity or 0),
                    float(self.ctrl.get_stock(item.product_id) or 0),
                )
            )
            qty_spin.setKeyboardTracking(False)
            qty_spin.setValue(float(item.quantity or 0))
            qty_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_spin.setFixedSize(96, 30)
            qty_spin.setStyleSheet(self._compact_quantity_style())
            qty_spin.valueChanged.connect(
                lambda value, i=row: self._update_item_quantity(i, value)
            )
            self.invoice_table.setCellWidget(row, 3, actions_cell([qty_spin]))

            self.invoice_table.setItem(
                row, 4, center_item(f"{item.net_total:.2f}")
            )

            del_btn = table_action_button("🗑", "danger")
            del_btn.setFixedSize(52, 28)
            del_btn.clicked.connect(lambda _, i=row: self._remove_item(i))
            self.invoice_table.setCellWidget(row, 5, actions_cell([del_btn]))

        self.items_count_label.setText(
            f"عدد الأصناف: {len(items)} | الكميات: {self._format_quantity(sum(float(item.quantity or 0) for item in items))}"
        )
        self._update_totals()

    def _compact_quantity_style(self) -> str:
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 9px;
                padding: 0px 8px;
                min-height: 28px;
                max-height: 28px;
                font-size: 12px;
                font-weight: 700;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {COLORS['focus_ring']};
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 0px;
                height: 0px;
                border: none;
            }}
        """

    def _format_quantity(self, quantity: float) -> str:
        return f"{quantity:.3f}".rstrip("0").rstrip(".")

    def _update_item_quantity(self, index: int, quantity: float):
        if not self._verify_manager_pin("تعديل كمية صنف في الفاتورة"):
            self._refresh_invoice()
            return
        try:
            self.ctrl.update_item_quantity(index, quantity)
            item = self.ctrl.current_items[index]
            self.invoice_table.setItem(
                index, 4, center_item(f"{item.net_total:.2f}")
            )
            self.items_count_label.setText(
                f"عدد الأصناف: {len(self.ctrl.current_items)} | الكميات: {self._format_quantity(sum(float(i.quantity or 0) for i in self.ctrl.current_items))}"
            )
            self._update_totals()
            self._notify_customer_item(item.product_id)
        except ValueError as exc:
            QMessageBox.warning(self, "تنبيه", str(exc))
            self._refresh_invoice()

    def _remove_item(self, index):
        """حذف بند من الفاتورة"""
        if not self._verify_manager_pin("حذف صنف من الفاتورة (Void Item)"):
            return
        reason, ok = QInputDialog.getText(self, "سبب الحذف", "أدخل سبب حذف الصنف من الفاتورة:")
        if not ok or not reason.strip():
            QMessageBox.warning(self, "تنبيه", "سبب الحذف إلزامي.")
            return
        try:
            logger.info("Item removed by user %s: reason=%s", self.user_info.get("id"), reason)
        except Exception:
            pass
        self.ctrl.remove_item(index)
        self._refresh_invoice()
        self._schedule_customer_totals()
        QTimer.singleShot(0, self._focus_scan)

    def _remove_selected_item(self):
        row = self.invoice_table.currentRow()
        if row >= 0:
            self._remove_item(row)

    def _update_totals(self):
        """تحديث المجموعات من الـ Controller"""
        totals = self.ctrl.calculate_totals()
        self.lbl_subtotal.setText(f"{totals['subtotal']:.2f} ج.م")
        self.lbl_tax.setText(f"{totals['tax_total']:.2f} ج.م")
        self.total_label.setText(f"{totals['total']:.2f} ج.م")
        if self.ctrl.applied_promos:
            names = sorted(
                {promo.get("promo_name", "عرض") for promo in self.ctrl.applied_promos}
            )
            company = self.ctrl.discount_company
            company_text = (
                f" | خصم {company.get('name')}: {totals.get('company_discount', 0):.2f} ج.م"
                if company
                else ""
            )
            self.promo_label.setText(
                f"🏷️ عروض مطبقة: {', '.join(names)} | الخصم: {self.ctrl.promo_discount:.2f} ج.م{company_text}"
            )
            self.promo_label.show()
        elif self.ctrl.discount_company:
            company = self.ctrl.discount_company
            self.promo_label.setText(
                f"🏢 خصم {company.get('name')}: {totals.get('company_discount', 0):.2f} ج.م"
            )
            self.promo_label.show()
        else:
            self.promo_label.hide()
        self._update_change()

    def _update_change(self):
        """حساب الباقي"""
        try:
            totals = self.ctrl.calculate_totals()
            payment = self._selected_payment_method()
            paid = (
                self.cash_amount_input.value() + self.card_amount_input.value()
                if payment == "Mixed"
                else self.paid_amount_input.value()
            )
            change = paid - totals["total"]
            if paid > 0 and change >= 0:
                self.change_label.setText(f"الباقي: {change:.2f} ج.م")
                self.change_label.setStyleSheet(
                    f"color: {COLORS['success']}; padding: 5px; background-color: {COLORS['bg_panel']}; border-radius: 8px;"
                )
            elif paid > 0:
                self.change_label.setText(f"متبقي: {abs(change):.2f} ج.م")
                self.change_label.setStyleSheet(
                    f"color: {COLORS['danger']}; padding: 5px; background-color: {COLORS['bg_panel']}; border-radius: 8px;"
                )
            else:
                self.change_label.setText("الباقي: 0.00 ج.م")
                self.change_label.setStyleSheet(
                    f"color: {COLORS['text_muted']}; padding: 5px; background-color: {COLORS['bg_panel']}; border-radius: 8px;"
                )
        except Exception:
            pass

    def _hold_invoice(self):
        if not self.ctrl.current_items:
            QMessageBox.warning(self, "تنبيه", "لا توجد أصناف لتعليقها")
            return
        store_id = self._active_cashier_store_id(ask_when_missing=True)
        if not store_id:
            QMessageBox.warning(self, "تنبيه", "لا يوجد فرع بيع صالح لتعليق الفاتورة")
            return
        ok = self.ctrl.save_held_invoice(
            store_id,
            self.user_info.get("id", 1),
            self.customer_name.text(),
            self.customer_phone.text(),
            self.customer_address.text(),
        )
        if ok:
            QMessageBox.information(self, "تم", "تم تعليق الفاتورة بنجاح")
            self._on_clear()
        else:
            QMessageBox.critical(self, "خطأ", "فشل تعليق الفاتورة")

    def _open_held_bills_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("الفواتير المعلقة / Held Bills")
        dialog.resize(850, 480)
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("بحث:"))
        search_input = QLineEdit()
        search_input.setPlaceholderText("بحث بكود الفاتورة أو اسم العميل أو الهاتف...")
        search_input.setStyleSheet(INPUT_STYLE)
        search_layout.addWidget(search_input)
        layout.addLayout(search_layout)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            ["الكود", "التاريخ", "العميل", "الهاتف", "الإجمالي", "الكاشير"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet(TABLE_STYLE)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(table)

        def load_bills():
            store_id = self._active_cashier_store_id()
            held = (
                self.ctrl.get_held_invoices(
                    store_id, search_input.text().strip() or None
                )
                if store_id
                else []
            )
            table.setRowCount(len(held))
            for row, bill in enumerate(held):
                table.setItem(
                    row, 0, center_item(bill.get("temp_invoice_code", ""))
                )
                table.setItem(row, 1, center_item(str(bill.get("saved_at", ""))))
                table.setItem(
                    row, 2, center_item(bill.get("customer_name", "") or "ضيف")
                )
                table.setItem(
                    row, 3, center_item(bill.get("customer_phone", "") or "-")
                )
                table.setItem(
                    row,
                    4,
                    center_item(f"{float(bill.get('total_amount') or 0):,.2f}"),
                )
                table.setItem(
                    row, 5, center_item(bill.get("cashier_name", "") or "-")
                )
                table.item(row, 0).setData(Qt.ItemDataRole.UserRole, bill.get("id"))
                table.item(row, 0).setData(
                    Qt.ItemDataRole.UserRole + 1, bill.get("customer_name", "") or ""
                )
                table.item(row, 0).setData(
                    Qt.ItemDataRole.UserRole + 2, bill.get("customer_phone", "") or ""
                )
                table.item(row, 0).setData(
                    Qt.ItemDataRole.UserRole + 3, bill.get("customer_address", "") or ""
                )

        actions = QHBoxLayout()
        load_btn = QPushButton("استرجاع المحدد")
        load_btn.setStyleSheet(get_button_style("primary"))
        delete_btn = QPushButton("حذف الفاتورة")
        delete_btn.setStyleSheet(get_button_style("danger"))
        if not PermissionPolicy(self.user_info).can_delete_held_invoice():
            delete_btn.setEnabled(False)
        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet(get_button_style("secondary"))
        actions.addWidget(load_btn)
        actions.addWidget(delete_btn)
        actions.addWidget(close_btn)
        layout.addLayout(actions)

        def load_selected():
            row = table.currentRow()
            if row < 0:
                return
            temp_id = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if self.ctrl.resume_held_invoice(temp_id):
                self.current_held_invoice_id = temp_id
                self.customer_name.setText(
                    table.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)
                )
                self.customer_phone.setText(
                    table.item(row, 0).data(Qt.ItemDataRole.UserRole + 2)
                )
                self.customer_address.setText(
                    table.item(row, 0).data(Qt.ItemDataRole.UserRole + 3)
                )
                self._refresh_invoice()
                dialog.accept()

        def delete_selected():
            row = table.currentRow()
            if row < 0:
                QMessageBox.warning(dialog, "تنبيه", "الرجاء تحديد فاتورة")
                return
            if (
                QMessageBox.warning(
                    dialog,
                    "تأكيد الحذف",
                    "هل أنت متأكد من حذف هذه الفاتورة نهائياً؟",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                == QMessageBox.StandardButton.Yes
            ):
                temp_id = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if self.ctrl.delete_held_invoice(temp_id):
                    load_bills()
                    QMessageBox.information(dialog, "نجاح", "تم حذف الفاتورة")

        table.doubleClicked.connect(load_selected)
        search_input.textChanged.connect(load_bills)
        load_btn.clicked.connect(load_selected)
        delete_btn.clicked.connect(delete_selected)
        close_btn.clicked.connect(dialog.reject)
        load_bills()
        dialog.show()
        # Store reference to prevent garbage collection if not parented correctly
        setattr(self, f"_{dialog.windowTitle()}_dialog", dialog)

    def _open_history_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("سجل الفواتير / Invoices History")
        dialog.resize(1050, 650)
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)

        info = QGroupBox("معلومات الوردية الحالية")
        info.setStyleSheet(GROUP_BOX_STYLE)
        info_layout = QHBoxLayout(info)
        info_layout.addWidget(
            QLabel(f"الفرع: {self.user_info.get('store_name', 'غير معروف')}")
        )
        info_layout.addWidget(
            QLabel(
                f"الكاشير: {self.user_info.get('name', self.user_info.get('full_name', 'غير معروف'))}"
            )
        )
        info_layout.addStretch()
        layout.addWidget(info)

        filters = QGroupBox("بحث وتصفية")
        filters.setStyleSheet(GROUP_BOX_STYLE)
        filter_layout = QHBoxLayout(filters)
        search_input = QLineEdit()
        search_input.setPlaceholderText("بحث برقم الفاتورة أو اسم العميل أو الهاتف...")
        search_input.setStyleSheet(INPUT_STYLE)
        date_from = QDateEdit(QDate.currentDate().addDays(-30))
        date_to = QDateEdit(QDate.currentDate())
        for date_input in (date_from, date_to):
            date_input.setCalendarPopup(True)
            date_input.setDisplayFormat("yyyy-MM-dd")
            date_input.setStyleSheet(INPUT_STYLE)
        search_btn = QPushButton("🔍 بحث")
        search_btn.setStyleSheet(get_button_style("primary"))
        reset_btn = QPushButton("↺ ريست")
        reset_btn.setStyleSheet(get_button_style("secondary"))
        filter_layout.addWidget(QLabel("بحث:"))
        filter_layout.addWidget(search_input, 2)
        filter_layout.addWidget(QLabel("من:"))
        filter_layout.addWidget(date_from)
        filter_layout.addWidget(QLabel("إلى:"))
        filter_layout.addWidget(date_to)
        filter_layout.addWidget(search_btn)
        filter_layout.addWidget(reset_btn)
        layout.addWidget(filters)

        table = QTableWidget(0, 7)
        table.setHorizontalHeaderLabels(
            [
                "رقم الفاتورة",
                "التاريخ",
                "العميل",
                "الدفع",
                "الإجمالي",
                "المدفوع",
                "المتبقي",
            ]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet(TABLE_STYLE)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(table)

        def load_invoices():
            invoices = self.ctrl.get_completed_invoices(
                self.user_info.get("store_id", 1),
                search_input.text().strip() or None,
                date_from.date().toString("yyyy-MM-dd"),
                date_to.date().toString("yyyy-MM-dd"),
            )
            table.setRowCount(len(invoices))
            for row, invoice in enumerate(invoices):
                table.setItem(
                    row, 0, center_item(invoice.get("invoice_number", ""))
                )
                table.setItem(
                    row, 1, center_item(str(invoice.get("invoice_date", "")))
                )
                table.setItem(
                    row, 2, center_item(invoice.get("customer_name", "") or "ضيف")
                )
                table.setItem(
                    row, 3, center_item(invoice.get("payment_method", ""))
                )
                table.setItem(
                    row,
                    4,
                    center_item(f"{float(invoice.get('total_amount') or 0):,.2f}"),
                )
                table.setItem(
                    row,
                    5,
                    center_item(f"{float(invoice.get('paid_amount') or 0):,.2f}"),
                )
                table.setItem(
                    row,
                    6,
                    center_item(
                        f"{float(invoice.get('remaining_amount') or 0):,.2f}"
                    ),
                )
                table.item(row, 0).setData(Qt.ItemDataRole.UserRole, invoice.get("id"))

        def selected_invoice_id():
            row = table.currentRow()
            if row < 0:
                QMessageBox.warning(dialog, "تنبيه", "الرجاء تحديد فاتورة")
                return None
            return table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        def view_details():
            invoice_id = selected_invoice_id()
            if not invoice_id:
                return
            invoice = self.ctrl.get_invoice_by_id(invoice_id) or {}
            items = self.ctrl.get_invoice_items_by_id(invoice_id)
            details = QDialog(dialog)
            details.setWindowTitle(
                f"تفاصيل الفاتورة # {invoice.get('invoice_number', '')}"
            )
            details.resize(700, 520)
            details.setStyleSheet(GLOBAL_STYLE)
            d_layout = QVBoxLayout(details)
            cust_group = QGroupBox("بيانات العميل")
            cust_group.setStyleSheet(GROUP_BOX_STYLE)
            cust_layout = QFormLayout(cust_group)
            cust_layout.addRow("الاسم:", QLabel(invoice.get("customer_name") or "ضيف"))
            cust_layout.addRow("الهاتف:", QLabel(invoice.get("customer_phone") or "-"))
            cust_layout.addRow(
                "العنوان:", QLabel(invoice.get("customer_address") or "-")
            )
            d_layout.addWidget(cust_group)
            items_table = QTableWidget(0, 4)
            items_table.setHorizontalHeaderLabels(
                ["المنتج", "السعر", "الكمية", "الإجمالي"]
            )
            items_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            items_table.setStyleSheet(TABLE_STYLE)
            items_table.setRowCount(len(items))
            for row, item in enumerate(items):
                items_table.setItem(
                    row, 0, center_item(item.get("product_name", ""))
                )
                items_table.setItem(
                    row,
                    1,
                    center_item(f"{float(item.get('unit_price') or 0):,.2f}"),
                )
                items_table.setItem(
                    row, 2, center_item(str(item.get("quantity", 0)))
                )
                items_table.setItem(
                    row,
                    3,
                    center_item(f"{float(item.get('total_price') or 0):,.2f}"),
                )
            d_layout.addWidget(items_table)
            ok_btn = QPushButton("موافق")
            ok_btn.setStyleSheet(get_button_style("primary"))
            ok_btn.clicked.connect(details.accept)
            d_layout.addWidget(ok_btn)
            details.exec()

        def print_selected(as_pdf=False):
            invoice_id = selected_invoice_id()
            if not invoice_id:
                return
            invoice = self.ctrl.get_invoice_by_id(invoice_id)
            items = self.ctrl.get_invoice_items_by_id(invoice_id)
            if not invoice:
                return
            formatted_items = [
                {
                    "product_name": item.get("product_name", ""),
                    "quantity": item.get("quantity", 0),
                    "price": float(item.get("unit_price") or 0),
                    "total": float(item.get("total_price") or 0),
                }
                for item in items
            ]
            try:
                cashier_name = invoice.get("cashier_name") or self.user_info.get(
                    "name", "Cashier"
                )
                self.ctrl.print_receipt(invoice, formatted_items, cashier_name, as_pdf)
                QMessageBox.information(dialog, "نجاح", "تم تنفيذ أمر الطباعة/الحفظ")
            except Exception as exc:
                QMessageBox.critical(dialog, "خطأ", str(exc))

        actions = QHBoxLayout()
        details_btn = QPushButton("📄 عرض التفاصيل")
        details_btn.setStyleSheet(get_button_style("primary"))
        print_btn = QPushButton("🖨️ إعادة طباعة")
        print_btn.setStyleSheet(get_button_style("warning"))
        pdf_btn = QPushButton("📄 حفظ PDF")
        pdf_btn.setStyleSheet(get_button_style("info"))
        if not PermissionPolicy(self.user_info).can_reprint_invoices():
            print_btn.setEnabled(False)
            pdf_btn.setEnabled(False)
            print_btn.setToolTip("إعادة الطباعة متاحة للمدير فقط")
            pdf_btn.setToolTip("حفظ PDF متاح للمدير فقط")
        refresh_btn = QPushButton("تحديث")
        refresh_btn.setStyleSheet(get_button_style("secondary"))
        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet(get_button_style("secondary"))
        for button in (details_btn, print_btn, pdf_btn, refresh_btn, close_btn):
            actions.addWidget(button)
        layout.addLayout(actions)

        details_btn.clicked.connect(view_details)
        table.doubleClicked.connect(view_details)
        print_btn.clicked.connect(lambda: print_selected(False))
        pdf_btn.clicked.connect(lambda: print_selected(True))
        search_btn.clicked.connect(load_invoices)
        refresh_btn.clicked.connect(load_invoices)
        reset_btn.clicked.connect(
            lambda: (
                search_input.clear(),
                date_from.setDate(QDate.currentDate()),
                date_to.setDate(QDate.currentDate()),
                load_invoices(),
            )
        )
        close_btn.clicked.connect(dialog.accept)
        load_invoices()
        dialog.show()
        # Store reference to prevent garbage collection if not parented correctly
        setattr(self, f"_{dialog.windowTitle()}_dialog", dialog)

    def _open_product_inquiry(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("🔍 الاستعلام عن توافر صنف")
        dialog.resize(760, 520)
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)

        title = QLabel("🔍 استعلام عن توافر صنف في كل الفروع")
        title.setStyleSheet(LABEL_STYLE_HEADER)
        layout.addWidget(title)

        search_layout = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("أدخل كود المنتج أو الباركود أو الاسم...")
        search_input.setStyleSheet(INPUT_STYLE)
        search_input.setText(self.scan_input.text().strip())
        search_btn = QPushButton("بحث")
        search_btn.setStyleSheet(get_button_style("primary"))
        search_layout.addWidget(search_input)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        info_box = QGroupBox("بيانات الصنف")
        info_box.setStyleSheet(GROUP_BOX_STYLE)
        info_layout = QHBoxLayout(info_box)
        name_label = QLabel("الاسم: -")
        price_label = QLabel("السعر: -")
        price_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: 800;")
        info_layout.addWidget(name_label)
        info_layout.addStretch()
        info_layout.addWidget(price_label)
        info_box.hide()
        layout.addWidget(info_box)

        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["الفرع", "الكمية المتاحة", "تنبيه"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet(TABLE_STYLE)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(table)

        def search_product():
            term = search_input.text().strip()
            if not term:
                return
            result = self.ctrl.get_product_cross_branch_stock(term)
            product = result.get("product") if result else None
            stocks = result.get("stocks", []) if result else []
            if not product:
                info_box.hide()
                table.setRowCount(0)
                return
            name_label.setText(
                f"الاسم: {product.get('product_name')} ({product.get('product_code')})"
            )
            price_label.setText(
                f"السعر: {float(product.get('sell_price') or 0):,.2f} ج.م"
            )
            info_box.show()
            table.setRowCount(len(stocks))
            current_store_id = self._active_cashier_store_id()
            for row, stock in enumerate(stocks):
                store_name = stock.get("store_name", "")
                if stock.get("store_id") == current_store_id:
                    store_name += " (الفرع الحالي)"
                qty = float(stock.get("quantity") or 0)
                alert_text = ""
                if qty <= 0:
                    alert_text = "نفد المخزون"
                elif qty <= float(stock.get("minimum_quantity") or 5):
                    alert_text = "كمية محدودة"
                name_item = center_item(store_name)
                qty_item = center_item(self._format_quantity(qty))
                alert_item = center_item(alert_text)
                if stock.get("store_id") == current_store_id:
                    for item in (name_item, qty_item, alert_item):
                        item.setBackground(QColor("#1a3a4a"))
                        item.setForeground(QColor(COLORS["text_on_brand"]))
                if qty <= 0:
                    qty_item.setForeground(QColor(COLORS["danger"]))
                table.setItem(row, 0, name_item)
                table.setItem(row, 1, qty_item)
                table.setItem(row, 2, alert_item)

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet(get_button_style("secondary"))
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        search_btn.clicked.connect(search_product)
        search_input.returnPressed.connect(search_product)
        if search_input.text().strip():
            search_product()
        dialog.show()
        # Store reference to prevent garbage collection if not parented correctly
        setattr(self, f"_{dialog.windowTitle()}_dialog", dialog)

    def _open_orders_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("طلبات الكول سنتر / Call Center Orders")
        dialog.resize(900, 520)
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("بحث:"))
        search_input = QLineEdit()
        search_input.setPlaceholderText("بحث برقم الطلب، اسم العميل، أو الهاتف...")
        search_input.setStyleSheet(INPUT_STYLE)
        search_layout.addWidget(search_input)
        layout.addLayout(search_layout)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            [
                "رقم الطلب",
                "اسم العميل",
                "رقم الهاتف",
                "التاريخ",
                "الحالة",
                "المصدر/الكول سنتر",
            ]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet(TABLE_STYLE)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(table)

        def load_orders():
            store_id = self._active_cashier_store_id()
            orders = (
                self.ctrl.get_open_orders(store_id, search_input.text().strip() or None)
                if store_id
                else []
            )
            table.setRowCount(len(orders))
            for row, order in enumerate(orders):
                table.setItem(row, 0, center_item(order.get("order_number", "")))
                table.setItem(row, 1, center_item(order.get("customer_name", "")))
                table.setItem(row, 2, center_item(order.get("customer_phone", "")))
                table.setItem(
                    row, 3, center_item(str(order.get("order_date", "")))
                )
                table.setItem(row, 4, center_item(order.get("status", "")))
                table.setItem(
                    row,
                    5,
                    center_item(order.get("call_center_agent", "") or "N/A"),
                )
                table.item(row, 0).setData(Qt.ItemDataRole.UserRole, order.get("id"))
                table.item(row, 0).setData(
                    Qt.ItemDataRole.UserRole + 1,
                    order.get("customer_address", "") or "",
                )

        actions = QHBoxLayout()
        select_btn = QPushButton("تحميل الطلب المحدد")
        select_btn.setStyleSheet(get_button_style("success"))
        refresh_btn = QPushButton("تحديث القائمة")
        refresh_btn.setStyleSheet(get_button_style("secondary"))
        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet(get_button_style("secondary"))
        actions.addWidget(select_btn)
        actions.addWidget(refresh_btn)
        actions.addWidget(close_btn)
        layout.addLayout(actions)

        def select_order():
            row = table.currentRow()
            if row < 0:
                QMessageBox.warning(dialog, "تنبيه", "الرجاء تحديد طلب أولاً")
                return
            if (
                QMessageBox.question(
                    dialog,
                    "تأكيد",
                    "هل تريد تحميل هذا الطلب للفاتورة؟",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
            order_id = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            try:
                if self.ctrl.load_order_items(order_id):
                    self.current_order_id = order_id
                    self.customer_name.setText(table.item(row, 1).text())
                    self.customer_phone.setText(table.item(row, 2).text())
                    self.customer_address.setText(
                        table.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)
                    )
                    self._refresh_invoice()
                    self._schedule_customer_totals()
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, "تنبيه", "لا توجد بنود لهذا الطلب")
            except ValueError as exc:
                QMessageBox.warning(dialog, "تنبيه", str(exc))

        search_input.textChanged.connect(load_orders)
        table.doubleClicked.connect(select_order)
        select_btn.clicked.connect(select_order)
        refresh_btn.clicked.connect(load_orders)
        close_btn.clicked.connect(dialog.reject)
        load_orders()
        dialog.show()
        # Store reference to prevent garbage collection if not parented correctly
        setattr(self, f"_{dialog.windowTitle()}_dialog", dialog)

    def _open_lock_screen_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("🔒 قفل الشاشة - تبديل الكاشير السريع")
        dialog.setFixedWidth(400)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setStyleSheet(GLOBAL_STYLE)
        dialog.reject = lambda: None
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        lbl = QLabel("الشاشة مقفولة حالياً لأسباب أمنية.\nأدخل بيانات الكاشير الجديد أو المشرف لفتح النظام:")
        lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl)
        
        form = QFormLayout()
        user_input = QLineEdit()
        user_input.setPlaceholderText("اسم المستخدم / البريد الإلكتروني...")
        user_input.setStyleSheet(INPUT_STYLE)
        
        pass_input = QLineEdit()
        pass_input.setPlaceholderText("كلمة المرور...")
        pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        pass_input.setStyleSheet(INPUT_STYLE)
        
        form.addRow("المستخدم:", user_input)
        form.addRow("كلمة المرور:", pass_input)
        layout.addLayout(form)
        
        from PyQt6.QtWidgets import QApplication
        from ui.form_helpers import action_row
        btn_layout, unlock_btn, cancel_btn = action_row("🔓 إلغاء القفل")
        cancel_btn.setText("خروج من البرنامج")
        cancel_btn.clicked.connect(lambda: QApplication.quit())
        
        def authenticate():
            username = user_input.text().strip()
            password = pass_input.text().strip()
            if not username or not password:
                QMessageBox.warning(dialog, "تنبيه", "يرجى إدخال اسم المستخدم وكلمة المرور.")
                return
            try:
                from repositories.user_repo import UserRepository
                user_repo = UserRepository()
                user = user_repo.authenticate(username, password)
                if user:
                    user_dict = user.to_dict() if hasattr(user, "to_dict") else {"id": getattr(user, "id", 1), "name": getattr(user, "name", "User"), "role": getattr(user, "role", "cashier")}
                    self.user_info = user_dict
                    uname = user_dict.get("name") or user_dict.get("username") or "مستخدم"
                    QMessageBox.information(dialog, "نجاح", f"مرحباً بك مجدداً، {uname}")
                    dialog.reject = lambda: super(QDialog, dialog).reject()
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, "خطأ أمني", "اسم المستخدم أو كلمة المرور غير صحيحة.")
            except Exception as exc:
                logger.error("Lock screen auth error: %s", exc, exc_info=True)
                QMessageBox.critical(dialog, "خطأ", f"تعذر التحقق من بيانات الدخول:\n{exc}")
                
        unlock_btn.clicked.connect(authenticate)
        layout.addLayout(btn_layout)
        dialog.exec()

    def _verify_manager_pin(self, action_name: str) -> bool:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"موافقة إدارية مطلوبة - {action_name}")
        dialog.setFixedWidth(380)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setStyleSheet(GLOBAL_STYLE)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        lbl = QLabel(f"هذا الإجراء ({action_name}) يتطلب صلاحية مشرف / مدير:\nأدخل كلمة المرور للاعتماد (أو اضغط إلغاء للتراجع):")
        lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl)
        
        form = QFormLayout()
        user_input = QLineEdit()
        user_input.setPlaceholderText("اسم المستخدم المشرف...")
        user_input.setStyleSheet(INPUT_STYLE)
        
        pass_input = QLineEdit()
        pass_input.setPlaceholderText("كلمة المرور...")
        pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        pass_input.setStyleSheet(INPUT_STYLE)
        
        form.addRow("المشرف:", user_input)
        form.addRow("كلمة المرور:", pass_input)
        layout.addLayout(form)
        
        from ui.form_helpers import action_row
        btn_layout, ok_btn, cancel_btn = action_row("اعتماد")
        cancel_btn.setText("إلغاء")
        
        verified = [False]
        def check():
            u = user_input.text().strip()
            p = pass_input.text().strip()
            if not u or not p:
                QMessageBox.warning(dialog, "تنبيه", "أدخل اسم المستخدم وكلمة المرور.")
                return
            try:
                from repositories.user_repo import UserRepository
                repo = UserRepository()
                usr = repo.authenticate(u, p)
                if usr:
                    usr_dict = usr.to_dict() if hasattr(usr, "to_dict") else {"id": getattr(usr, "id", 1), "role": getattr(usr, "role", "cashier")}
                    if usr_dict.get("role") in ("admin", "manager") or PermissionPolicy(usr_dict).can_manage_users():
                        verified[0] = True
                        dialog.accept()
                    else:
                        QMessageBox.warning(dialog, "خطأ أمني", "حساب غير مصرح له بهذه الصلاحية.")
                else:
                    QMessageBox.warning(dialog, "خطأ أمني", "اسم المستخدم أو كلمة المرور غير صحيحة.")
            except Exception as e:
                QMessageBox.critical(dialog, "خطأ", f"خطأ في التحقق:\n{e}")
                
        ok_btn.clicked.connect(check)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addLayout(btn_layout)
        dialog.exec()
        return verified[0]

    def closeEvent(self, event):
        if self.customer_display:
            self.customer_display.close()
            self.customer_display = None
        super().closeEvent(event)
