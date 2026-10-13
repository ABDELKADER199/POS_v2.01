"""
Call Center View - واجهة الكول سنتر (Clean Architecture)
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QTableWidget, QMessageBox,
    QComboBox, QSpinBox, QTextEdit, QHeaderView,
    QTabWidget, QGroupBox, QFrame, QScrollArea, QGridLayout,
    QDialog, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.styles import (GLOBAL_STYLE, get_button_style, COLORS, TABLE_STYLE,
                       GROUP_BOX_STYLE, INPUT_STYLE, LABEL_STYLE_HEADER)
from ui.table_helpers import center_item, configure_table
from controllers.callcenter_controller import CallCenterController
from application.use_cases.callcenter import DELIVERY_STATUS_TRANSITIONS

logger = logging.getLogger(__name__)


class CallCenterView(QWidget):
    def __init__(self, ctrl: CallCenterController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user = user_info
        self.cart = []
        self.setStyleSheet(GLOBAL_STYLE)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._search_products)
        self._init_ui()
        self._load_stores()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("☎️ Call Center - إدارة الأوامر")
        title.setStyleSheet(LABEL_STYLE_HEADER)
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_new_order_tab(), "📝 أمر جديد")
        self.tabs.addTab(self._create_pending_tab(), "⏳ الأوامر المعلقة")
        self.tabs.addTab(self._create_completed_tab(), "✅ الأوامر المنجزة")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

    # ═══════════ New Order Tab ═══════════
    def _create_new_order_tab(self):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setSpacing(10)

        # Column 1: Product Search (35%)
        col1 = QFrame()
        col1_layout = QVBoxLayout(col1)
        col1_layout.setContentsMargins(5, 5, 5, 5)

        search_group = QGroupBox("🔍 الأصناف")
        search_group.setStyleSheet(GROUP_BOX_STYLE)
        search_inner = QVBoxLayout()

        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("ابحث باسم الصنف أو الكود...")
        self.product_search.setStyleSheet(INPUT_STYLE)
        self.product_search.textChanged.connect(lambda: self.search_timer.start(300))
        search_inner.addWidget(self.product_search)

        self.products_scroll = QScrollArea()
        self.products_scroll.setWidgetResizable(True)
        self.products_scroll.setStyleSheet("border: none; background: transparent;")
        self.products_container = QWidget()
        self.products_grid = QGridLayout(self.products_container)
        self.products_grid.setSpacing(10)
        self.products_scroll.setWidget(self.products_container)
        search_inner.addWidget(self.products_scroll)

        search_group.setLayout(search_inner)
        col1_layout.addWidget(search_group)

        # Column 2: Cart (40%)
        col2 = QFrame()
        col2_layout = QVBoxLayout(col2)
        col2_layout.setContentsMargins(5, 5, 5, 5)

        cart_group = QGroupBox("🛒 فاتورة الطلب")
        cart_group.setStyleSheet(GROUP_BOX_STYLE)
        cart_inner = QVBoxLayout()

        self.order_table = QTableWidget(0, 5)
        self.order_table.setHorizontalHeaderLabels(["كود", "الصنف", "السعر", "الكمية", "حذف"])
        h = self.order_table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.order_table.setColumnWidth(3, 85)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.order_table.setColumnWidth(4, 60)
        configure_table(self.order_table, TABLE_STYLE, row_height=55)
        cart_inner.addWidget(self.order_table)

        total_frame = QFrame()
        total_frame.setStyleSheet(f"background: {COLORS.get('bg_input', '#1E293B')}; border-radius: 12px;")
        total_layout = QHBoxLayout(total_frame)
        self.total_label = QLabel("إجمالي الطلب: 0.00 ج.م")
        self.total_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 18px; font-weight: 800;")
        total_layout.addWidget(self.total_label)
        cart_inner.addWidget(total_frame)

        cart_group.setLayout(cart_inner)
        col2_layout.addWidget(cart_group)

        # Column 3: Customer Info (25%)
        col3 = QGroupBox("📋 بيانات العميل")
        col3.setStyleSheet(GROUP_BOX_STYLE)
        col3_layout = QVBoxLayout()
        col3_layout.setSpacing(8)

        col3_layout.addWidget(QLabel("رقم الهاتف:"))
        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("01xxxxxxxxx")
        self.customer_phone.setStyleSheet(INPUT_STYLE)
        self.customer_phone.textChanged.connect(self._on_phone_changed)
        col3_layout.addWidget(self.customer_phone)

        col3_layout.addWidget(QLabel("اسم العميل:"))
        self.customer_name = QLineEdit()
        self.customer_name.setStyleSheet(INPUT_STYLE)
        col3_layout.addWidget(self.customer_name)

        col3_layout.addWidget(QLabel("العنوان بالتفصيل:"))
        self.customer_address = QTextEdit()
        self.customer_address.setPlaceholderText("المنطقة، الشارع...")
        self.customer_address.setStyleSheet(INPUT_STYLE)
        self.customer_address.setMaximumHeight(80)
        col3_layout.addWidget(self.customer_address)

        col3_layout.addWidget(QLabel("توجيه إلى فرع:"))
        self.store_combo = QComboBox()
        self.store_combo.setStyleSheet(INPUT_STYLE)
        col3_layout.addWidget(self.store_combo)

        col3_layout.addStretch()

        save_btn = QPushButton("✅ حفظ وإرسال الطلب")
        save_btn.setStyleSheet(get_button_style("success"))
        save_btn.setMinimumHeight(50)
        save_btn.clicked.connect(self._save_order)
        col3_layout.addWidget(save_btn)

        col3.setLayout(col3_layout)

        main_layout.addWidget(col1, 25)
        main_layout.addWidget(col2, 50)
        main_layout.addWidget(col3, 25)

        return widget

    # ═══════════ Pending Tab ═══════════
    def _create_pending_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        f = QHBoxLayout()
        f.addWidget(QLabel("تصفية حسب الفرع:"))
        self.pending_store_filter = QComboBox()
        self.pending_store_filter.setStyleSheet(INPUT_STYLE)
        self.pending_store_filter.currentIndexChanged.connect(self._load_pending)
        f.addWidget(self.pending_store_filter)
        f.addWidget(QLabel("بحث:"))
        self.pending_search = QLineEdit()
        self.pending_search.setPlaceholderText("رقم الطلب، العميل، الهاتف...")
        self.pending_search.setStyleSheet(INPUT_STYLE)
        self.pending_search.textChanged.connect(self._load_pending)
        f.addWidget(self.pending_search, 2)
        f.addStretch()
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setStyleSheet(get_button_style('info'))
        refresh_btn.clicked.connect(self._load_pending)
        f.addWidget(refresh_btn)
        layout.addLayout(f)

        self.pending_table = QTableWidget(0, 9)
        self.pending_table.setHorizontalHeaderLabels(
            ["رقم الأمر", "العميل", "الهاتف", "الفرع", "التاريخ", "الإجمالي", "المندوب", "الحالة", "إجراء"])
        self.pending_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(self.pending_table, TABLE_STYLE, row_height=50)
        self.pending_table.doubleClicked.connect(lambda: self._show_order_details(self.pending_table))
        layout.addWidget(self.pending_table)
        return w

    # ═══════════ Completed Tab ═══════════
    def _create_completed_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        f = QHBoxLayout()
        f.addWidget(QLabel("تصفية حسب الفرع:"))
        self.completed_store_filter = QComboBox()
        self.completed_store_filter.setStyleSheet(INPUT_STYLE)
        self.completed_store_filter.currentIndexChanged.connect(self._load_completed)
        f.addWidget(self.completed_store_filter)
        f.addWidget(QLabel("بحث:"))
        self.completed_search = QLineEdit()
        self.completed_search.setPlaceholderText("رقم الطلب، العميل، الهاتف...")
        self.completed_search.setStyleSheet(INPUT_STYLE)
        self.completed_search.textChanged.connect(self._load_completed)
        f.addWidget(self.completed_search, 2)
        f.addStretch()
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setStyleSheet(get_button_style('info'))
        refresh_btn.clicked.connect(self._load_completed)
        f.addWidget(refresh_btn)
        layout.addLayout(f)

        self.completed_table = QTableWidget(0, 8)
        self.completed_table.setHorizontalHeaderLabels(
            ["رقم الأمر", "العميل", "الهاتف", "الفرع", "التاريخ", "الإجمالي", "المندوب", "الحالة"])
        self.completed_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(self.completed_table, TABLE_STYLE, row_height=50)
        self.completed_table.doubleClicked.connect(lambda: self._show_order_details(self.completed_table))
        layout.addWidget(self.completed_table)
        return w

    # ═══════════ Logic ═══════════
    def _load_stores(self):
        stores = self.ctrl.get_all_stores()
        for combo in [self.store_combo]:
            combo.clear()
            for s in stores:
                combo.addItem(s['store_name'], s['id'])

        for combo in [self.pending_store_filter, self.completed_store_filter]:
            combo.clear()
            combo.addItem("جميع الفروع", None)
            for s in stores:
                combo.addItem(s['store_name'], s['id'])

    def _on_phone_changed(self):
        phone = self.customer_phone.text().strip()
        if len(phone) == 11 and phone.isdigit():
            cust = self.ctrl.get_customer_by_phone(phone)
            if cust:
                self.customer_name.setText(cust.get('customer_name', ''))
                self.customer_address.setPlainText(cust.get('address', '') or '')

    def _search_products(self):
        term = self.product_search.text().strip()
        # Clear grid
        while self.products_grid.count():
            item = self.products_grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if not term or len(term) < 2:
            return

        products = self.ctrl.search_products(term)
        for i, p in enumerate(products):
            card = self._create_product_card(p)
            self.products_grid.addWidget(card, i, 0)

    def _create_product_card(self, product):
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setMinimumHeight(90)
        card.setObjectName("ProductCard")
        card.setStyleSheet(f"""
            QFrame#ProductCard {{
                background-color: {COLORS['primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
            QFrame#ProductCard:hover {{
                background-color: {COLORS['hover_surface']};
                border-color: {COLORS['accent']};
            }}
        """)
        layout = QVBoxLayout(card)
        name = QLabel(product['product_name'])
        name.setWordWrap(True)
        name.setStyleSheet(f"font-weight: bold; color: {COLORS['text_on_brand']};")
        price = QLabel(f"{float(product['sell_price']):,.2f} ج.م")
        price.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold;")
        code = QLabel(product.get('product_code', ''))
        code.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(name)
        layout.addWidget(price)
        layout.addWidget(code)
        card.mousePressEvent = lambda _: self._add_to_cart(product)
        return card

    def _add_to_cart(self, product):
        # Check if already in cart
        for item in self.cart:
            if item['product_id'] == product['id']:
                item['quantity'] += 1
                self._refresh_cart()
                return

        self.cart.append({
            'product_id': product['id'],
            'code': product.get('product_code', ''),
            'name': product['product_name'],
            'price': float(product['sell_price']),
            'quantity': 1
        })
        self._refresh_cart()

    def _refresh_cart(self):
        self.order_table.setRowCount(len(self.cart))
        total = 0
        for i, item in enumerate(self.cart):
            line_total = item['price'] * item['quantity']
            total += line_total

            code_item = center_item(item['code'])
            code_item.setData(Qt.ItemDataRole.UserRole, item['product_id'])
            self.order_table.setItem(i, 0, code_item)
            self.order_table.setItem(i, 1, center_item(item['name']))
            self.order_table.setItem(i, 2, center_item(f"{item['price']:,.2f}"))

            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setRange(0.001, 99999.0)
            spin.setSingleStep(0.5)
            spin.setValue(item['quantity'])
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.setStyleSheet(INPUT_STYLE)
            spin.valueChanged.connect(lambda v, idx=i: self._update_qty(idx, v))
            self.order_table.setCellWidget(i, 3, spin)

            del_btn = QPushButton("✖")
            del_btn.setStyleSheet(get_button_style("danger"))
            del_btn.clicked.connect(lambda _, idx=i: self._remove_from_cart(idx))
            self.order_table.setCellWidget(i, 4, del_btn)

        self.total_label.setText(f"إجمالي الطلب: {total:,.2f} ج.م")

    def _update_qty(self, idx, value):
        if 0 <= idx < len(self.cart):
            self.cart[idx]['quantity'] = value
            self._refresh_cart()

    def _remove_from_cart(self, idx):
        if 0 <= idx < len(self.cart):
            self.cart.pop(idx)
            self._refresh_cart()

    def _save_order(self):
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "لا يوجد أصناف في الطلب")
            return

        name = self.customer_name.text().strip()
        phone = self.customer_phone.text().strip()
        address = self.customer_address.toPlainText().strip()
        store_id = self.store_combo.currentData()

        if not name or not phone:
            QMessageBox.warning(self, "تنبيه", "اسم العميل ورقم الهاتف مطلوبان")
            return

        total = sum(i['price'] * i['quantity'] for i in self.cart)

        user_id = self.user.get('id')
        if not user_id:
            QMessageBox.critical(self, "خطأ", "بيانات الجلسة غير مكتملة، يرجى إعادة تسجيل الدخول.")
            return
            
        order_num = self.ctrl.save_order(
            name, phone, address, store_id, self.cart, total,
            user_id, self.user.get('store_id')
        )

        if order_num:
            QMessageBox.information(self, "نجاح", f"تم حفظ الطلب بنجاح\nرقم الطلب: {order_num}")
            self.cart.clear()
            self._refresh_cart()
            self.customer_name.clear()
            self.customer_phone.clear()
            self.customer_address.clear()
        else:
            QMessageBox.critical(self, "خطأ", "فشل حفظ الطلب")

    def _on_tab_changed(self, index):
        if index == 1:
            self._load_pending()
        elif index == 2:
            self._load_completed()



    def _status_widget(self, status):
        color_map = {
            'Pending': COLORS['primary'],
            'Confirmed': COLORS['success'],
            'Prepared': COLORS['warning'],
            'Delivered': COLORS['success'],
            'Cancelled': COLORS['danger'],
        }
        text_map = {
            'Pending': 'قيد الانتظار',
            'Confirmed': 'تم القبول',
            'Prepared': 'جاري التحضير',
            'Delivered': 'تم التسليم',
            'Cancelled': 'ملغي',
        }
        label = QLabel(f"● {text_map.get(status, status)}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color: {color_map.get(status, COLORS['text_secondary'])}; "
            "font-weight: bold; font-size: 13px; padding: 5px;"
        )
        return label

    def _load_orders_table(self, table, orders, show_actions=False):
        table.setRowCount(len(orders))
        for i, o in enumerate(orders):
            table.setItem(i, 0, center_item(o.get('order_number', '')))
            table.item(i, 0).setData(Qt.ItemDataRole.UserRole, o.get('id'))
            table.setItem(i, 1, center_item(o.get('customer_name', '')))
            table.setItem(i, 2, center_item(o.get('customer_phone', '')))
            table.setItem(i, 3, center_item(o.get('target_store', '') or o.get('source_store', '')))
            table.setItem(i, 4, center_item(str(o.get('order_date', o.get('created_at', '')))))
            table.setItem(i, 5, center_item(f"{float(o.get('total_amount', 0)):,.2f}"))
            table.setItem(i, 6, center_item(o.get('delivery_agent_name', '') or '-'))

            status = o.get('status', 'Pending')
            table.setCellWidget(i, 7, self._status_widget(status))

            if show_actions:
                actions = QWidget()
                a_layout = QHBoxLayout(actions)
                a_layout.setContentsMargins(4, 4, 4, 4)

                for s_key, s_label, s_color in [
                    ('Accepted', '✅ قبول', COLORS['success']),
                    ('Processing', '🔄 تحضير', COLORS['warning']),
                    ('Delivered', '🚚 تسليم', COLORS['info']),
                    ('Cancelled', '❌ إلغاء', COLORS['danger']),
                ]:
                    btn = QPushButton(s_label)
                    btn.setFixedHeight(30)
                    btn.setStyleSheet(f"background: {s_color}; color: {COLORS['text_on_brand']}; border: none; border-radius: 6px; padding: 2px 6px; font-size: 10px;")
                    btn.clicked.connect(lambda _, oid=o['id'], ns=s_key: self._update_status(oid, ns))
                    a_layout.addWidget(btn)

                assign_btn = QPushButton("👤 مندوب")
                assign_btn.setFixedHeight(30)
                assign_btn.clicked.connect(lambda _, oid=o['id']: self._assign_delivery_agent(oid))
                a_layout.addWidget(assign_btn)

                tracking_btn = QPushButton("🚚 تتبع")
                tracking_btn.setFixedHeight(30)
                tracking_btn.clicked.connect(lambda _, oid=o['id']: self._update_delivery_tracking(oid))
                a_layout.addWidget(tracking_btn)
                table.setCellWidget(i, 8, actions)

    def _assign_delivery_agent(self, order_id):
        order = self.ctrl.get_order_by_id(order_id) or {}
        store_id = order.get('destination_store_id') or order.get('source_store_id')
        agents = self.ctrl.get_delivery_agents(store_id)
        if not agents:
            QMessageBox.information(self, "المندوبون", "لا يوجد مندوبون نشطون لهذا الفرع")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("تعيين مندوب التوصيل")
        dialog.setStyleSheet(GLOBAL_STYLE)
        form = QFormLayout(dialog)
        combo = QComboBox()
        combo.setStyleSheet(INPUT_STYLE)
        for agent in agents:
            combo.addItem(agent.get('name', ''), agent.get('id'))
        form.addRow("المندوب:", combo)
        buttons = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setStyleSheet(get_button_style("success"))
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet(get_button_style("secondary"))
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        form.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.ctrl.assign_delivery_agent(order_id, combo.currentData(), store_id):
                self._load_pending()
                self._load_completed()
            else:
                QMessageBox.critical(self, "خطأ", "فشل تعيين مندوب التوصيل")

    def _update_delivery_tracking(self, order_id):
        order = self.ctrl.get_order_by_id(order_id) or {}
        current_status = order.get('delivery_status') or 'Unassigned'
        next_statuses = sorted(DELIVERY_STATUS_TRANSITIONS.get(current_status, set()))
        if not next_statuses:
            QMessageBox.information(self, "التوصيل", "لا توجد حالة تالية متاحة لهذا الطلب")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("تحديث تتبع التوصيل")
        dialog.setStyleSheet(GLOBAL_STYLE)
        form = QFormLayout(dialog)
        status_combo = QComboBox()
        status_combo.setStyleSheet(INPUT_STYLE)
        status_combo.addItems(next_statuses)
        notes = QLineEdit()
        notes.setStyleSheet(INPUT_STYLE)
        form.addRow("الحالة التالية:", status_combo)
        form.addRow("ملاحظات:", notes)
        buttons = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setStyleSheet(get_button_style("success"))
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet(get_button_style("secondary"))
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        form.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.ctrl.update_delivery_status(order_id, status_combo.currentText(), notes.text()):
                self._load_pending()
                self._load_completed()
            else:
                QMessageBox.critical(self, "خطأ", "فشل تحديث حالة التوصيل")

    def _show_order_details(self, table):
        row = table.currentRow()
        if row < 0 or not table.item(row, 0):
            return
        order_id = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        order = self.ctrl.get_order_by_id(order_id) or {}
        items = self.ctrl.get_order_details(order_id)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"تفاصيل الطلب {order.get('order_number', '')}")
        dialog.resize(760, 520)
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)

        info = QGroupBox("بيانات الطلب والعميل")
        info.setStyleSheet(GROUP_BOX_STYLE)
        form = QFormLayout(info)
        form.addRow("رقم الطلب:", QLabel(order.get('order_number', '')))
        form.addRow("العميل:", QLabel(order.get('customer_name', '')))
        form.addRow("الهاتف:", QLabel(order.get('customer_phone', '')))
        form.addRow("العنوان:", QLabel(order.get('customer_address', '') or '-'))
        form.addRow("فرع الاستلام:", QLabel(order.get('target_store', '') or '-'))
        form.addRow("الحالة:", QLabel(order.get('status', '')))
        form.addRow("مندوب التوصيل:", QLabel(order.get('delivery_agent_name', '') or '-'))
        form.addRow("حالة التوصيل:", QLabel(order.get('delivery_status', '') or 'Unassigned'))
        layout.addWidget(info)

        items_table = QTableWidget(0, 4)
        items_table.setHorizontalHeaderLabels(["الصنف", "السعر", "الكمية", "الإجمالي"])
        items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(items_table, TABLE_STYLE, row_height=44)
        items_table.setRowCount(len(items))
        for i, item in enumerate(items):
            items_table.setItem(i, 0, center_item(item.get('product_name', '')))
            items_table.setItem(i, 1, center_item(f"{float(item.get('unit_price') or 0):,.2f}"))
            items_table.setItem(i, 2, center_item(str(item.get('quantity', 0))))
            items_table.setItem(i, 3, center_item(f"{float(item.get('total_price') or 0):,.2f}"))
        layout.addWidget(items_table)

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet(get_button_style("secondary"))
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def _load_pending(self):
        store_id = self.pending_store_filter.currentData() if hasattr(self, 'pending_store_filter') else None
        search = self.pending_search.text().strip() if hasattr(self, 'pending_search') else None
        orders = self.ctrl.get_orders(status='Pending', store_id=store_id, search=search)
        self._load_orders_table(self.pending_table, orders, show_actions=True)

    def _load_completed(self):
        store_id = self.completed_store_filter.currentData() if hasattr(self, 'completed_store_filter') else None
        search = self.completed_search.text().strip() if hasattr(self, 'completed_search') else None
        orders = self.ctrl.get_orders(status='Completed', store_id=store_id, search=search)
        self._load_orders_table(self.completed_table, orders)

    def _update_status(self, order_id, new_status):
        if self.ctrl.update_order_status(order_id, new_status):
            QMessageBox.information(self, "تم", "تم تحديث حالة الطلب")
            self._load_pending()
            self._load_completed()
        else:
            QMessageBox.critical(self, "خطأ", "فشل تحديث الحالة")

    def refresh_data(self):
        self._load_stores()
        self._load_pending()
        self._load_completed()
