"""
Accounts View - واجهة الحسابات والمالية (Clean Architecture)
يجمع: حسابات العملاء/الموردين + المصروفات + السجل المالي + الخزينة + العروض + تحليل الديون
"""

import os, logging
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
    QSpinBox,
    QHeaderView,
    QTabWidget,
    QGroupBox,
    QFrame,
    QDialog,
    QFormLayout,
    QDateEdit,
    QCheckBox,
    QGridLayout,
    QScrollArea,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.styles import (
    GLOBAL_STYLE,
    get_button_style,
    COLORS,
    TABLE_STYLE,
    GROUP_BOX_STYLE,
    INPUT_STYLE,
    LABEL_STYLE_HEADER,
)
from controllers.accounts_controller import AccountsController
from controllers.purchases_controller import PurchasesController
from application.errors import AccountsValidationError
from ui.form_helpers import (
    action_row,
    configure_form_layout,
    style_dialog,
    style_form_controls,
)
from ui.table_helpers import center_item, configure_table
from ui.purchases_view import PurchasesView
from ui.promotions_view import PromotionsView
from ui.subtab_dropdown import create_subtab_dropdown
from utils.permissions import PermissionPolicy

logger = logging.getLogger(__name__)


class AccountsView(QWidget):
    def __init__(self, ctrl: AccountsController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user = user_info
        self.policy = PermissionPolicy(user_info)
        self.purchases_ctrl = PurchasesController()
        self.setStyleSheet(GLOBAL_STYLE)
        self._init_ui()
        self.refresh_data()

    def _safe_user_id(self):
        """Return user ID or show error and return None if session is invalid."""
        uid = self.user.get("id")
        if not uid:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "خطأ", "بيانات الجلسة غير مكتملة، يرجى إعادة تسجيل الدخول.")
        return uid

    def _table_item(self, value, color=None):
        item = center_item(value)
        if color:
            item.setForeground(color)
        return item

    def _money_item(self, value, color=None):
        return self._table_item(f"{float(value or 0):,.2f}", color)

    def _prepare_table(self, table, row_height=52):
        configure_table(table, TABLE_STYLE, row_height)
        table.setWordWrap(False)

    def _scrollable_tab(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_panel']};
                width: 12px;
                margin: 3px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                min-height: 36px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['focus_ring']};
            }}
            QScrollBar:horizontal {{
                background: {COLORS['bg_panel']};
                height: 12px;
                margin: 3px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: {COLORS['border']};
                min-width: 36px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {COLORS['focus_ring']};
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                width: 0px;
                height: 0px;
            }}
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: transparent;
            }}
        """)
        scroll.setWidget(widget)
        return scroll

    def _action_button(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setMinimumWidth(78)
        btn.setStyleSheet(
            f"background: {color}; color: {COLORS['text_on_brand']}; border: none; "
            "border-radius: 7px; padding: 2px 8px; font-weight: 600;"
        )
        return btn

    def _table_actions_widget(self, minimum_width: int) -> tuple[QWidget, QHBoxLayout]:
        widget = QWidget()
        widget.setMinimumWidth(minimum_width)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        layout.addStretch()
        return widget, layout

    def _create_summary_card(self, title, value="0.00", color=COLORS["text_secondary"]):
        card = QFrame()
        card.setObjectName("ProductCard")
        card.setMinimumHeight(86)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("CardTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_lbl = QLabel(value)
        value_lbl.setObjectName("CardPrice")
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_lbl.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: 900;")

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        return card, value_lbl

    def _create_overview_panel(self):
        panel = QFrame()
        panel.setObjectName("FinanceOverviewPanel")
        panel.setStyleSheet(
            f"QFrame#FinanceOverviewPanel {{ background-color: {COLORS['bg_panel']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 14px; padding: 8px; }}"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        cards = QHBoxLayout()
        self.treasury_summary_card, self.treasury_summary_value = (
            self._create_summary_card("رصيد الخزينة", "0.00", COLORS["success"])
        )
        self.customer_debt_card, self.customer_debt_value = self._create_summary_card(
            "ديون العملاء", "0.00", COLORS["danger"]
        )
        self.supplier_debt_card, self.supplier_debt_value = self._create_summary_card(
            "مستحقات الموردين", "0.00", COLORS["warning"]
        )
        self.net_obligation_card, self.net_obligation_value = self._create_summary_card(
            "صافي الالتزام", "0.00", COLORS["info"]
        )
        for card in (
            self.treasury_summary_card,
            self.customer_debt_card,
            self.supplier_debt_card,
            self.net_obligation_card,
        ):
            cards.addWidget(card)
        layout.addLayout(cards)

        return panel

    def _refresh_overview(self):
        if not hasattr(self, "treasury_summary_value"):
            return
        debts = self.ctrl.get_debt_totals()
        treasury_balance = self.ctrl.get_treasury_balance()
        customer_debt = float(debts.get("customer_debt", 0) or 0)
        supplier_debt = float(debts.get("supplier_debt", 0) or 0)
        net_obligation = supplier_debt - customer_debt
        self.treasury_summary_value.setText(f"{treasury_balance:,.2f} ج.م")
        self.customer_debt_value.setText(f"{customer_debt:,.2f} ج.م")
        self.supplier_debt_value.setText(f"{supplier_debt:,.2f} ج.م")
        self.net_obligation_value.setText(f"{net_obligation:,.2f} ج.م")
        net_color = COLORS["warning"] if net_obligation > 0 else COLORS["success"]
        self.net_obligation_value.setStyleSheet(
            f"color: {net_color}; font-size: 18px; font-weight: 900;"
        )

    def _view_attachment(self, path):
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "تنبيه", "ملف المرفق غير موجود")
            return
        os.startfile(path)

    def _init_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel(
            "📝 مصروفات الفرع"
            if self.policy.can_access_branch_expenses()
            else "💰 إدارة الحسابات والمالية"
        )
        title.setStyleSheet(LABEL_STYLE_HEADER)
        subtitle_text = (
            "تسجيل ومراجعة مصروفات الفرع الحالي فقط"
            if self.policy.can_access_branch_expenses()
            else "مركز موحد للخزينة، الديون، الموردين، المصروفات، والسجل المالي"
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 600;"
        )
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch()
        refresh_btn = QPushButton("تحديث البيانات")
        refresh_btn.setStyleSheet(get_button_style("info"))
        refresh_btn.clicked.connect(self.refresh_data)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        if self.policy.can_access_full_accounts():
            layout.addWidget(self._create_overview_panel())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        if self.policy.can_access_full_accounts():
            self.tabs.addTab(
                self._scrollable_tab(self._create_treasury_tab()), "الخزينة"
            )
            self.tabs.addTab(
                self._scrollable_tab(self._create_customers_tab()), "العملاء"
            )
            self.tabs.addTab(
                self._scrollable_tab(self._create_suppliers_tab()), "الموردون"
            )
            self.tabs.addTab(
                self._scrollable_tab(PurchasesView(self.purchases_ctrl, self.user)),
                "المشتريات",
            )
            self.tabs.addTab(
                self._scrollable_tab(PromotionsView(self.ctrl, self.user)), "العروض"
            )
            self.tabs.addTab(
                self._scrollable_tab(self._create_discount_companies_tab()),
                "خصومات الشركات",
            )
            self.tabs.addTab(
                self._scrollable_tab(self._create_expenses_tab()), "المصروفات"
            )
            self.tabs.addTab(
                self._scrollable_tab(self._create_ledger_tab()), "السجل المالي"
            )
            self.tabs.addTab(
                self._scrollable_tab(self._create_debt_analysis_tab()), "تحليل الديون"
            )
        elif self.policy.can_access_branch_expenses():
            self.tabs.addTab(
                self._scrollable_tab(self._create_expenses_tab()), "مصروفات الفرع"
            )
        layout.addWidget(create_subtab_dropdown(self.tabs, "اختر قسم الحسابات"))
        layout.addWidget(self.tabs, 1)

    def _create_discount_companies_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        header = QHBoxLayout()
        header.addWidget(QLabel("إدارة الشركات ونسب الخصم المتاحة للكاشير"))
        header.addStretch()
        add_btn = QPushButton("إضافة شركة خصم")
        add_btn.setStyleSheet(get_button_style("success"))
        add_btn.clicked.connect(lambda: self._discount_company_dialog())
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.discount_companies_table = QTableWidget(0, 4)
        self.discount_companies_table.setHorizontalHeaderLabels(
            ["الشركة", "نسبة الخصم", "الحالة", "إجراءات"]
        )
        self.discount_companies_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.discount_companies_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Fixed
        )
        self.discount_companies_table.setColumnWidth(3, 220)
        self._prepare_table(self.discount_companies_table, 48)
        layout.addWidget(self.discount_companies_table)
        self._load_discount_companies()
        return widget

    def _load_discount_companies(self):
        if not hasattr(self, "discount_companies_table"):
            return
        try:
            companies = self.ctrl.get_discount_companies()
            self.discount_companies_table.setRowCount(len(companies))
            for row, company in enumerate(companies):
                self.discount_companies_table.setItem(
                    row, 0, self._table_item(company.get("name", ""))
                )
                self.discount_companies_table.setItem(
                    row,
                    1,
                    self._table_item(
                        f"{float(company.get('discount_percent') or 0):g}%"
                    ),
                )
                self.discount_companies_table.setItem(
                    row,
                    2,
                    self._table_item("نشط" if company.get("is_active") else "متوقف"),
                )
                actions = QWidget()
                actions_layout = QHBoxLayout(actions)
                actions_layout.setContentsMargins(4, 3, 4, 3)
                edit_btn = self._action_button("تعديل", COLORS["primary"])
                edit_btn.clicked.connect(
                    lambda _, data=company: self._discount_company_dialog(data)
                )
                delete_btn = self._action_button("حذف", COLORS["danger"])
                delete_btn.clicked.connect(
                    lambda _, cid=company.get("id"): self._delete_discount_company(cid)
                )
                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(delete_btn)
                self.discount_companies_table.setCellWidget(row, 3, actions)
        except Exception as exc:
            logger.error("Error loading discount companies: %s", exc, exc_info=True)

    def _discount_company_dialog(self, company=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("تعديل شركة خصم" if company else "إضافة شركة خصم")
        dialog.setMinimumSize(700, 620)
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ─── Company Info Section ───
        info_group = QGroupBox("بيانات الشركة")
        info_group.setStyleSheet(GROUP_BOX_STYLE)
        info_form = QFormLayout(info_group)
        name = QLineEdit(company.get("name", "") if company else "")
        name.setStyleSheet(INPUT_STYLE)
        name.setPlaceholderText("اسم شركة الخصم")
        percent = QDoubleSpinBox()
        percent.setRange(0.01, 100)
        percent.setDecimals(2)
        percent.setSuffix(" %")
        percent.setStyleSheet(INPUT_STYLE)
        percent.setValue(float(company.get("discount_percent", 0) if company else 0))
        active = QCheckBox("نشطة في الكاشير")
        active.setChecked(bool(company.get("is_active", True) if company else True))
        info_form.addRow("اسم الشركة:", name)
        info_form.addRow("نسبة الخصم:", percent)
        info_form.addRow(active)
        layout.addWidget(info_group)

        # ─── Products Section ───
        products_group = QGroupBox("الأصناف المستهدفة بالخصم")
        products_group.setStyleSheet(GROUP_BOX_STYLE)
        products_layout = QVBoxLayout(products_group)
        products_layout.setSpacing(8)

        # Search bar
        search_row = QHBoxLayout()
        product_search = QLineEdit()
        product_search.setPlaceholderText("🔍 بحث باسم المنتج أو الباركود...")
        product_search.setStyleSheet(INPUT_STYLE)
        search_row.addWidget(product_search)
        products_layout.addLayout(search_row)

        # Info label
        info_label = QLabel(
            "⚠️ تظهر فقط المنتجات التي سعر بيعها أعلى من سعر شرائها — "
            "المنتجات ذات هامش الربح الكافي بعد تطبيق نسبة الخصم."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; padding: 4px 8px; "
            f"background: {COLORS['bg_panel']}; border-radius: 6px;"
        )
        products_layout.addWidget(info_label)

        # Products list
        products_list = QListWidget()
        products_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        products_list.setStyleSheet(
            f"QListWidget {{ font-size: 12px; }} "
            f"QListWidget::item {{ padding: 5px 8px; border-bottom: 1px solid {COLORS['border']}; }}"
        )
        products_layout.addWidget(products_list, 1)

        # Status bar
        status_bar = QHBoxLayout()
        products_count_label = QLabel("")
        products_count_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600;"
        )
        select_all_btn = QPushButton("تحديد الكل")
        select_all_btn.setFixedHeight(28)
        select_all_btn.setStyleSheet(
            f"background: {COLORS['info']}; color: {COLORS['text_on_brand']}; "
            "border: none; border-radius: 6px; padding: 2px 12px; font-weight: 600; font-size: 11px;"
        )
        deselect_all_btn = QPushButton("إلغاء الكل")
        deselect_all_btn.setFixedHeight(28)
        deselect_all_btn.setStyleSheet(
            f"background: {COLORS['border']}; color: {COLORS['text_primary']}; "
            "border: none; border-radius: 6px; padding: 2px 12px; font-weight: 600; font-size: 11px;"
        )
        status_bar.addWidget(products_count_label)
        status_bar.addStretch()
        status_bar.addWidget(select_all_btn)
        status_bar.addWidget(deselect_all_btn)
        products_layout.addLayout(status_bar)

        layout.addWidget(products_group, 1)

        # ─── Populate & Filter Logic ───
        selected_ids = set(company.get("product_ids", []) if company else [])
        _all_products_cache = {}

        def _populate_products(search_term=""):
            nonlocal _all_products_cache
            discount_pct = percent.value()
            products_list.clear()
            _all_products_cache.clear()

            try:
                products = self.ctrl.search_discount_eligible_products(
                    search_term, min_margin_percent=discount_pct
                )
            except Exception:
                products = [
                    p for p in self.ctrl.search_promotion_products(search_term)
                    if float(p.get("sell_price") or 0) > float(p.get("buy_price") or 0) > 0
                ]

            checked_count = 0
            for product in products:
                pid = product.get("id")
                sell = float(product.get("sell_price") or 0)
                buy = float(product.get("buy_price") or 0)

                if sell <= 0 or buy <= 0 or sell <= buy:
                    continue

                profit_pct = ((sell - buy) / sell) * 100
                after_discount_price = sell * (1 - discount_pct / 100)
                remaining_margin = ((after_discount_price - buy) / sell) * 100 if sell > 0 else 0

                # Color code based on remaining margin after discount
                if remaining_margin >= 10:
                    margin_color = "#16a34a"  # green — safe
                    margin_icon = "🟢"
                elif remaining_margin >= 3:
                    margin_color = "#d97706"  # orange — thin margin
                    margin_icon = "🟡"
                else:
                    margin_color = "#dc2626"  # red — risky
                    margin_icon = "🔴"

                label = (
                    f"{product.get('product_name', '')}  |  "
                    f"شراء: {buy:.2f}  |  بيع: {sell:.2f}  |  "
                    f"{margin_icon} هامش بعد الخصم: {remaining_margin:.1f}%"
                )

                product_item = QListWidgetItem(label)
                product_item.setData(Qt.ItemDataRole.UserRole, pid)
                product_item.setFlags(
                    product_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                is_checked = pid in selected_ids
                product_item.setCheckState(
                    Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked
                )
                if is_checked:
                    checked_count += 1

                product_item.setForeground(QColor(margin_color))
                products_list.addItem(product_item)
                _all_products_cache[pid] = product_item

            total = products_list.count()
            products_count_label.setText(
                f"📦 {total} منتج مؤهل  |  ✅ {checked_count} محدد"
            )

        def _on_item_changed(item):
            pid = item.data(Qt.ItemDataRole.UserRole)
            if item.checkState() == Qt.CheckState.Checked:
                selected_ids.add(pid)
            else:
                selected_ids.discard(pid)
            # Update counter
            checked = sum(
                1 for i in range(products_list.count())
                if products_list.item(i).checkState() == Qt.CheckState.Checked
            )
            products_count_label.setText(
                f"📦 {products_list.count()} منتج مؤهل  |  ✅ {checked} محدد"
            )

        def _select_all():
            for i in range(products_list.count()):
                item = products_list.item(i)
                item.setCheckState(Qt.CheckState.Checked)
                selected_ids.add(item.data(Qt.ItemDataRole.UserRole))
            products_count_label.setText(
                f"📦 {products_list.count()} منتج مؤهل  |  ✅ {products_list.count()} محدد"
            )

        def _deselect_all():
            for i in range(products_list.count()):
                item = products_list.item(i)
                item.setCheckState(Qt.CheckState.Unchecked)
                selected_ids.discard(item.data(Qt.ItemDataRole.UserRole))
            products_count_label.setText(
                f"📦 {products_list.count()} منتج مؤهل  |  ✅ 0 محدد"
            )

        # Debounced search
        _search_timer = QTimer()
        _search_timer.setSingleShot(True)
        _search_timer.setInterval(300)
        _search_timer.timeout.connect(lambda: _populate_products(product_search.text().strip()))
        product_search.textChanged.connect(lambda: _search_timer.start())

        # Re-filter when discount percent changes
        percent.valueChanged.connect(lambda: _populate_products(product_search.text().strip()))
        products_list.itemChanged.connect(_on_item_changed)
        select_all_btn.clicked.connect(_select_all)
        deselect_all_btn.clicked.connect(_deselect_all)

        # Initial load
        _populate_products()

        # ─── Action Buttons ───
        buttons, save_btn, cancel_btn = action_row()
        save_btn.clicked.connect(
            lambda: self._save_discount_company(
                dialog, company, name, percent, active, products_list
            )
        )
        cancel_btn.clicked.connect(dialog.reject)
        layout.addLayout(buttons)
        dialog.exec()

    def _save_discount_company(
        self, dialog, company, name, percent, active, products_list
    ):
        product_ids = [
            products_list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(products_list.count())
            if products_list.item(index).checkState() == Qt.CheckState.Checked
        ]
        if company:
            ok = self.ctrl.update_discount_company(
                company["id"],
                name.text(),
                percent.value(),
                active.isChecked(),
                product_ids,
            )
        else:
            ok = self.ctrl.add_discount_company(
                name.text(), percent.value(), product_ids
            )
        if not ok:
            QMessageBox.warning(
                dialog,
                "خطأ",
                self.ctrl.get_last_discount_company_error() or "تعذر حفظ شركة الخصم",
            )
            return
        dialog.accept()
        self._load_discount_companies()

    def _delete_discount_company(self, company_id):
        if (
            QMessageBox.question(self, "تأكيد", "حذف شركة الخصم؟")
            != QMessageBox.StandardButton.Yes
        ):
            return
        if not self.ctrl.delete_discount_company(company_id):
            QMessageBox.warning(
                self,
                "خطأ",
                self.ctrl.get_last_discount_company_error() or "تعذر حذف شركة الخصم",
            )
            return
        self._load_discount_companies()

    # ═══════════ Customers ═══════════
    def _create_customers_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        section_title = QLabel("إدارة أرصدة العملاء والتحصيلات")
        section_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 700;"
        )
        layout.addWidget(section_title)
        f = QHBoxLayout()
        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("🔍 بحث باسم العميل...")
        self.cust_search.setStyleSheet(INPUT_STYLE)
        self.cust_search.textChanged.connect(self._load_customers)
        f.addWidget(self.cust_search)
        self.cust_filter_debt = QComboBox()
        self.cust_filter_debt.addItems(["الكل", "عليهم مديونية", "ليس عليهم ديون"])
        self.cust_filter_debt.setStyleSheet(INPUT_STYLE)
        self.cust_filter_debt.currentIndexChanged.connect(self._load_customers)
        f.addWidget(self.cust_filter_debt)
        layout.addLayout(f)

        self.cust_table = QTableWidget(0, 6)
        self.cust_table.setHorizontalHeaderLabels(
            ["ID", "الاسم", "الهاتف", "الرصيد", "الحد الائتماني", "إجراءات"]
        )
        self.cust_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.cust_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Fixed
        )
        self.cust_table.setColumnWidth(5, 360)
        self._prepare_table(self.cust_table)
        layout.addWidget(self.cust_table)
        return w

    def _load_customers(self):
        term = self.cust_search.text().lower()
        debt_filter = (
            self.cust_filter_debt.currentText()
            if hasattr(self, "cust_filter_debt")
            else "الكل"
        )
        customers = self.ctrl.get_customer_accounts()
        filtered = []
        for c in customers:
            balance = float(c.get("current_balance", 0) or 0)
            matches_search = (
                not term
                or term in c.get("name", "").lower()
                or term in (c.get("phone", "") or "")
            )
            matches_debt = (
                debt_filter == "الكل"
                or (debt_filter == "عليهم مديونية" and balance > 0)
                or (debt_filter == "ليس عليهم ديون" and balance <= 0)
            )
            if matches_search and matches_debt:
                filtered.append(c)
        self.cust_table.setRowCount(len(filtered))
        for i, c in enumerate(filtered):
            self.cust_table.setItem(i, 0, self._table_item(c["id"]))
            self.cust_table.setItem(i, 1, self._table_item(c["name"]))
            self.cust_table.setItem(i, 2, self._table_item(c.get("phone", "") or "-"))
            bal = float(c.get("current_balance", 0) or 0)
            self.cust_table.setItem(
                i, 3, self._money_item(bal, Qt.GlobalColor.red if bal > 0 else None)
            )
            limit = float(c.get("credit_limit", 0) or 0)
            self.cust_table.setItem(
                i, 4, self._table_item(f"{limit:,.2f}" if limit > 0 else "-")
            )

            actions, a_layout = self._table_actions_widget(340)

            pay_btn = self._action_button("تحصيل", "#16a34a")
            pay_btn.clicked.connect(
                lambda _, cid=c["id"], n=c["name"]: self._payment_dialog(
                    "Customer", cid, n
                )
            )
            a_layout.addWidget(pay_btn)

            settle_btn = self._action_button("تسوية", "#7c3aed")
            settle_btn.clicked.connect(
                lambda _, cid=c["id"], n=c["name"]: self._settlement_dialog(
                    "Customer", cid, n
                )
            )
            a_layout.addWidget(settle_btn)

            limit_btn = self._action_button("حد", "#475569")
            limit_btn.clicked.connect(
                lambda _, cid=c["id"], n=c["name"], lim=limit: self._limit_dialog(
                    cid, n, lim
                )
            )
            a_layout.addWidget(limit_btn)

            hist_btn = self._action_button("كشف", "#0284c7")
            hist_btn.clicked.connect(
                lambda _, cid=c["id"], n=c["name"]: self._view_history(
                    "Customer", cid, n
                )
            )
            a_layout.addWidget(hist_btn)
            a_layout.addStretch()

            self.cust_table.setCellWidget(i, 5, actions)

    # ═══════════ Suppliers ═══════════
    def _create_suppliers_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        section_title = QLabel("إدارة مستحقات الموردين والمدفوعات")
        section_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 700;"
        )
        layout.addWidget(section_title)
        f = QHBoxLayout()
        self.supp_search = QLineEdit()
        self.supp_search.setPlaceholderText("🔍 بحث باسم المورد...")
        self.supp_search.setStyleSheet(INPUT_STYLE)
        self.supp_search.textChanged.connect(self._load_suppliers)
        f.addWidget(self.supp_search)
        layout.addLayout(f)

        self.supp_table = QTableWidget(0, 5)
        self.supp_table.setHorizontalHeaderLabels(
            ["ID", "الاسم", "الهاتف", "الرصيد المستحق", "إجراءات"]
        )
        self.supp_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.supp_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Fixed
        )
        self.supp_table.setColumnWidth(4, 280)
        self._prepare_table(self.supp_table)
        layout.addWidget(self.supp_table)
        return w

    def _load_suppliers(self):
        term = self.supp_search.text().lower()
        suppliers = self.ctrl.get_all_suppliers()
        filtered = [
            s for s in suppliers if not term or term in s.get("name", "").lower()
        ]
        self.supp_table.setRowCount(len(filtered))
        for i, s in enumerate(filtered):
            self.supp_table.setItem(i, 0, self._table_item(s["id"]))
            self.supp_table.setItem(i, 1, self._table_item(s["name"]))
            self.supp_table.setItem(i, 2, self._table_item(s.get("phone", "") or "-"))
            bal = float(s.get("current_balance", 0) or 0)
            self.supp_table.setItem(
                i, 3, self._money_item(bal, Qt.GlobalColor.red if bal > 0 else None)
            )

            actions, a_layout = self._table_actions_widget(260)
            pay_btn = self._action_button("دفع", "#c2410c")
            pay_btn.clicked.connect(
                lambda _, sid=s["id"], n=s["name"]: self._payment_dialog(
                    "Supplier", sid, n
                )
            )
            a_layout.addWidget(pay_btn)

            settle_btn = self._action_button("تسوية", "#7c3aed")
            settle_btn.clicked.connect(
                lambda _, sid=s["id"], n=s["name"]: self._settlement_dialog(
                    "Supplier", sid, n
                )
            )
            a_layout.addWidget(settle_btn)

            hist_btn = self._action_button("كشف", "#0284c7")
            hist_btn.clicked.connect(
                lambda _, sid=s["id"], n=s["name"]: self._view_history(
                    "Supplier", sid, n
                )
            )
            a_layout.addWidget(hist_btn)
            a_layout.addStretch()
            self.supp_table.setCellWidget(i, 4, actions)

    # ═══════════ Expenses ═══════════
    def _create_expenses_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        section_title = QLabel("تسجيل المصروفات ومراجعة أثرها على الخزينة")
        section_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 700;"
        )
        layout.addWidget(section_title)

        form_group = QGroupBox("إضافة مصروف جديد")
        form_group.setStyleSheet(GROUP_BOX_STYLE)
        form = QGridLayout()

        store_label = QLabel("الفرع:")
        self.exp_store_combo = QComboBox()
        self.exp_store_combo.setStyleSheet(INPUT_STYLE)
        form.addWidget(store_label, 0, 0)
        form.addWidget(self.exp_store_combo, 0, 1)

        self.exp_type = QComboBox()
        self.exp_type.setEditable(True)
        self.exp_type.addItems(
            ["كهرباء", "إيجار", "رواتب", "نثريات", "صيانة", "بضاعة", "شخصي"]
        )
        self.exp_type.setStyleSheet(INPUT_STYLE)
        form.addWidget(QLabel("النوع:"), 0, 2)
        form.addWidget(self.exp_type, 0, 3)

        self.exp_amount = QLineEdit()
        self.exp_amount.setPlaceholderText("المبلغ")
        self.exp_amount.setStyleSheet(INPUT_STYLE)
        form.addWidget(QLabel("المبلغ:"), 1, 0)
        form.addWidget(self.exp_amount, 1, 1)

        self.exp_desc = QLineEdit()
        self.exp_desc.setPlaceholderText("وصف (اختياري)")
        self.exp_desc.setStyleSheet(INPUT_STYLE)
        form.addWidget(QLabel("الوصف:"), 1, 2)
        form.addWidget(self.exp_desc, 1, 3)

        self.is_personal = QCheckBox("مصروف شخصي")
        self.is_personal.setStyleSheet(f"font-weight: bold; color: {COLORS['danger']};")
        add_btn = QPushButton("➕ إضافة")
        add_btn.setStyleSheet(get_button_style("success"))
        add_btn.clicked.connect(self._add_expense)
        bottom = QHBoxLayout()
        bottom.addWidget(self.is_personal)
        bottom.addStretch()
        bottom.addWidget(add_btn)
        form.addLayout(bottom, 2, 0, 1, 4)

        form_group.setLayout(form)
        layout.addWidget(form_group)

        report_group = QGroupBox("ملخص مالي للفترة")
        report_group.setStyleSheet(GROUP_BOX_STYLE)
        report_layout = QGridLayout(report_group)
        self.report_start_date = QDateEdit()
        self.report_start_date.setCalendarPopup(True)
        self.report_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.report_start_date.setStyleSheet(INPUT_STYLE)
        self.report_end_date = QDateEdit()
        self.report_end_date.setCalendarPopup(True)
        self.report_end_date.setDate(QDate.currentDate())
        self.report_end_date.setStyleSheet(INPUT_STYLE)
        report_btn = QPushButton("عرض التقرير")
        report_btn.setStyleSheet(get_button_style("info"))
        report_btn.clicked.connect(self._load_financial_report)
        self.report_sales_lbl = QLabel("المبيعات: 0.00")
        self.report_expenses_lbl = QLabel("المصروفات: 0.00")
        self.report_personal_lbl = QLabel("الشخصي: 0.00")
        self.report_net_lbl = QLabel("الصافي: 0.00")
        self.report_net_lbl.setStyleSheet(
            f"font-weight: bold; color: {COLORS['success']};"
        )
        report_layout.addWidget(QLabel("من:"), 0, 0)
        report_layout.addWidget(self.report_start_date, 0, 1)
        report_layout.addWidget(QLabel("إلى:"), 0, 2)
        report_layout.addWidget(self.report_end_date, 0, 3)
        report_layout.addWidget(report_btn, 0, 4)
        report_layout.addWidget(self.report_sales_lbl, 1, 0)
        report_layout.addWidget(self.report_expenses_lbl, 1, 1)
        report_layout.addWidget(self.report_personal_lbl, 1, 2)
        report_layout.addWidget(self.report_net_lbl, 1, 3, 1, 2)
        layout.addWidget(report_group)

        self.exp_table = QTableWidget(0, 7)
        self.exp_table.setHorizontalHeaderLabels(
            ["ID", "التاريخ", "النوع", "شخصي؟", "المبلغ", "الوصف", "بواسطة"]
        )
        self.exp_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._prepare_table(self.exp_table, 48)
        self.exp_table.setMinimumHeight(350)
        layout.addWidget(self.exp_table)

        btn_layout = QHBoxLayout()
        del_btn = QPushButton("إلغاء المحدد")
        del_btn.setStyleSheet(get_button_style("danger"))
        del_btn.clicked.connect(self._delete_expense)
        btn_layout.addStretch()
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)

        return w

    def _load_expenses(self):
        stores = self.ctrl.get_all_stores()
        self.exp_store_combo.clear()
        if self.policy.can_access_branch_expenses():
            user_store_id = self.user.get("store_id")
            user_store = next((s for s in stores if s.get("id") == user_store_id), None)
            self.exp_store_combo.addItem(
                user_store.get("store_name", "فرعي") if user_store else "فرعي",
                user_store_id,
            )
            self.exp_store_combo.setEnabled(False)
        else:
            for s in stores:
                self.exp_store_combo.addItem(s["store_name"], s["id"])

        store_id = self.user.get("store_id")
        if not store_id and self.exp_store_combo.count() > 0:
            store_id = self.exp_store_combo.currentData()
        if not store_id:
            return

        expenses = self.ctrl.get_expenses(store_id)
        self.exp_table.setRowCount(len(expenses))
        for i, e in enumerate(expenses):
            self.exp_table.setItem(i, 0, self._table_item(e["id"]))
            self.exp_table.setItem(i, 1, self._table_item(e.get("expense_date", "")))
            self.exp_table.setItem(i, 2, self._table_item(e.get("expense_type", "")))
            self.exp_table.setItem(
                i, 3, self._table_item("نعم" if e.get("is_personal") else "لا")
            )
            self.exp_table.setItem(
                i, 4, self._money_item(e.get("amount", 0), Qt.GlobalColor.red)
            )
            self.exp_table.setItem(
                i, 5, self._table_item(e.get("description", "") or "-")
            )
            self.exp_table.setItem(i, 6, self._table_item(e.get("user_name", "")))

    def _load_financial_report(self):
        store_id = (
            self.exp_store_combo.currentData()
            if hasattr(self, "exp_store_combo")
            else self.user.get("store_id")
        )
        if self.policy.can_access_branch_expenses():
            store_id = self.policy.scoped_store_id(store_id)
        if not store_id:
            return
        report = self.ctrl.get_financial_report(
            store_id,
            self.report_start_date.date().toString("yyyy-MM-dd"),
            self.report_end_date.date().toString("yyyy-MM-dd"),
        )
        if not report:
            QMessageBox.warning(self, "تنبيه", "تعذر تحميل التقرير المالي")
            return
        self.report_sales_lbl.setText(f"المبيعات: {report.get('total_sales', 0):,.2f}")
        self.report_expenses_lbl.setText(
            f"المصروفات: {report.get('total_expenses', 0):,.2f}"
        )
        self.report_personal_lbl.setText(
            f"الشخصي: {report.get('personal_expenses', 0):,.2f}"
        )
        self.report_net_lbl.setText(f"الصافي: {report.get('net_cash', 0):,.2f}")

    def _add_expense(self):
        amount_text = self.exp_amount.text().strip()
        if not amount_text:
            QMessageBox.warning(self, "تنبيه", "أدخل المبلغ")
            return
        try:
            amount = float(amount_text)
        except ValueError:
            QMessageBox.warning(self, "خطأ", "المبلغ يجب أن يكون رقماً")
            return

        store_id = self.exp_store_combo.currentData()
        if self.policy.can_access_branch_expenses():
            store_id = self.policy.scoped_store_id(store_id)
        if not store_id:
            store_id = self.user.get("store_id")

        try:
            if self.ctrl.add_expense(
                store_id,
                self._safe_user_id(),
                self.exp_type.currentText(),
                amount,
                self.exp_desc.text(),
                self.is_personal.isChecked(),
            ):
                QMessageBox.information(self, "نجاح", "تم إضافة المصروف")
                self.exp_amount.clear()
                self.exp_desc.clear()
                self._load_expenses()
                if hasattr(self, "treasury_table"):
                    self._load_treasury()
                if hasattr(self, "ledger_table"):
                    self._load_ledger()
                self._load_financial_report()
        except AccountsValidationError as e:
            QMessageBox.warning(self, "تنبيه", str(e))

    def _delete_expense(self):
        row = self.exp_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "حدد مصروفاً للإلغاء")
            return
        exp_id = int(self.exp_table.item(row, 0).text())
        if (
            QMessageBox.question(
                self,
                "تأكيد",
                "سيتم إلغاء المصروف بقيد عكسي دون حذف أثره. هل تريد المتابعة؟",
            )
            == QMessageBox.StandardButton.Yes
        ):
            try:
                if self.ctrl.delete_expense(
                    exp_id, self._safe_user_id(), "إلغاء من شاشة المصروفات"
                ):
                    self._load_expenses()
                    if hasattr(self, "treasury_table"):
                        self._load_treasury()
                    if hasattr(self, "ledger_table"):
                        self._load_ledger()
                    self._load_financial_report()
            except AccountsValidationError as e:
                QMessageBox.warning(self, "تنبيه", str(e))

    # ═══════════ Ledger ═══════════
    def _create_ledger_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        section_title = QLabel("دفتر حركة الحسابات والمرفقات")
        section_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 700;"
        )
        layout.addWidget(section_title)

        summary = QHBoxLayout()
        self.total_cust_debt_lbl = QLabel("ديون العملاء: 0.00")
        self.total_cust_debt_lbl.setStyleSheet(
            f"font-weight: bold; color: {COLORS['danger']}; font-size: 14px;"
        )
        summary.addWidget(self.total_cust_debt_lbl)
        self.total_supp_debt_lbl = QLabel("مستحقات الموردين: 0.00")
        self.total_supp_debt_lbl.setStyleSheet(
            f"font-weight: bold; color: {COLORS['warning']}; font-size: 14px;"
        )
        summary.addWidget(self.total_supp_debt_lbl)
        layout.addLayout(summary)

        f = QHBoxLayout()
        self.ledger_search = QLineEdit()
        self.ledger_search.setPlaceholderText("بحث...")
        self.ledger_search.setStyleSheet(INPUT_STYLE)
        self.ledger_search.textChanged.connect(self._load_ledger)
        f.addWidget(self.ledger_search)

        self.ledger_type_filter = QComboBox()
        self.ledger_type_filter.addItems(["الكل", "Customer", "Supplier", "Expense"])
        self.ledger_type_filter.setStyleSheet(INPUT_STYLE)
        self.ledger_type_filter.currentIndexChanged.connect(self._load_ledger)
        f.addWidget(self.ledger_type_filter)
        layout.addLayout(f)

        self.ledger_table = QTableWidget(0, 8)
        self.ledger_table.setHorizontalHeaderLabels(
            [
                "التاريخ",
                "النوع",
                "الاسم",
                "العملية",
                "المبلغ",
                "المرجع",
                "الوصف",
                "المرفق",
            ]
        )
        self.ledger_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.ledger_table.horizontalHeader().setSectionResizeMode(
            7, QHeaderView.ResizeMode.ResizeToContents
        )
        self._prepare_table(self.ledger_table, 48)
        layout.addWidget(self.ledger_table)
        return w

    def _load_ledger(self):
        search = self.ledger_search.text() if hasattr(self, "ledger_search") else ""
        acc_type = (
            self.ledger_type_filter.currentText()
            if hasattr(self, "ledger_type_filter")
            else ""
        )
        logs = self.ctrl.get_financial_ledger(search, acc_type)
        self.ledger_table.setRowCount(len(logs))
        for i, l in enumerate(logs):
            self.ledger_table.setItem(
                i, 0, self._table_item(l.get("transaction_date", ""))
            )
            self.ledger_table.setItem(i, 1, self._table_item(l.get("account_type", "")))
            self.ledger_table.setItem(
                i,
                2,
                self._table_item(l.get("name", "") or str(l.get("account_id", ""))),
            )
            self.ledger_table.setItem(
                i, 3, self._table_item(l.get("transaction_type", ""))
            )
            amt = float(l.get("amount", 0))
            color = (
                Qt.GlobalColor.red
                if l.get("transaction_type") == "Credit"
                else Qt.GlobalColor.green
            )
            self.ledger_table.setItem(i, 4, self._money_item(amt, color))
            self.ledger_table.setItem(
                i,
                5,
                self._table_item(
                    f"{l.get('reference_type', '')} #{l.get('reference_id', '')}"
                ),
            )
            self.ledger_table.setItem(
                i, 6, self._table_item(l.get("description", "") or "")
            )
            attachment = l.get("attachment_path")
            if attachment:
                attach_btn = self._action_button("فتح", "#2563eb")
                attach_btn.clicked.connect(
                    lambda _, path=attachment: self._view_attachment(path)
                )
                self.ledger_table.setCellWidget(i, 7, attach_btn)
            else:
                self.ledger_table.setItem(i, 7, self._table_item("-"))

        debts = self.ctrl.get_debt_totals()
        self.total_cust_debt_lbl.setText(f"ديون العملاء: {debts['customer_debt']:,.2f}")
        self.total_supp_debt_lbl.setText(
            f"مستحقات الموردين: {debts['supplier_debt']:,.2f}"
        )

    # ═══════════ Treasury ═══════════
    def _create_treasury_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        summary_card = QFrame()
        summary_card.setObjectName("ProductCard")
        summary_layout = QHBoxLayout(summary_card)
        summary_layout.setContentsMargins(14, 10, 14, 10)
        self.treasury_balance_lbl = QLabel("رصيد الخزينة: 0.00")
        self.treasury_balance_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {COLORS['success']};"
        )
        summary_layout.addWidget(self.treasury_balance_lbl)
        summary_layout.addStretch()
        add_btn = QPushButton("+ تسجيل حركة")
        add_btn.setStyleSheet(get_button_style("primary"))
        add_btn.clicked.connect(self._treasury_dialog)
        summary_layout.addWidget(add_btn)
        layout.addWidget(summary_card)

        self.treasury_table = QTableWidget(0, 6)
        self.treasury_table.setHorizontalHeaderLabels(
            ["التاريخ", "النوع", "المبلغ", "المصدر", "الوصف", "المستخدم"]
        )
        self.treasury_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._prepare_table(self.treasury_table, 48)
        layout.addWidget(self.treasury_table)
        return w

    def _load_treasury(self):
        txns = self.ctrl.get_treasury_transactions()
        self.treasury_table.setRowCount(len(txns))
        for i, t in enumerate(txns):
            self.treasury_table.setItem(i, 0, self._table_item(t.get("created_at", "")))
            self.treasury_table.setItem(
                i, 1, self._table_item(t.get("transaction_type", ""))
            )
            amt = float(t.get("amount", 0))
            color = (
                Qt.GlobalColor.green
                if t.get("transaction_type") == "In"
                else Qt.GlobalColor.red
            )
            self.treasury_table.setItem(i, 2, self._money_item(amt, color))
            self.treasury_table.setItem(
                i, 3, self._table_item(t.get("source_type", ""))
            )
            self.treasury_table.setItem(
                i, 4, self._table_item(t.get("description", "") or "")
            )
            self.treasury_table.setItem(
                i, 5, self._table_item(t.get("user_name", "") or "-")
            )

        bal = self.ctrl.get_treasury_balance()
        self.treasury_balance_lbl.setText(f"رصيد الخزينة: {bal:,.2f} ج.م")

    def _treasury_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("تسجيل حركة خزينة")
        style_dialog(dialog, width=420)
        layout = QFormLayout(dialog)
        configure_form_layout(layout)
        type_cb = QComboBox()
        type_cb.addItems(["In", "Out"])
        layout.addRow("النوع:", type_cb)
        amt = QDoubleSpinBox()
        amt.setRange(1, 1000000)
        amt.setDecimals(2)
        layout.addRow("المبلغ:", amt)
        desc = QLineEdit()
        layout.addRow("الوصف:", desc)
        style_form_controls(type_cb, amt, desc)
        buttons, save_btn, cancel_btn = action_row()
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.ctrl.record_treasury_transaction(
                (self.user.get("store_id") or self._safe_user_id()),
                type_cb.currentText(),
                amt.value(),
                "Adjustment",
                None,
                desc.text(),
                self._safe_user_id(),
            )
            self._load_treasury()
            self._refresh_overview()

    def _create_debt_analysis_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        section_title = QLabel("تحليل الديون وأعمار أرصدة العملاء")
        section_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 700;"
        )
        layout.addWidget(section_title)

        self.debt_summary_table = QTableWidget(0, 3)
        self.debt_summary_table.setHorizontalHeaderLabels(["البند", "القيمة", "ملاحظة"])
        self.debt_summary_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._prepare_table(self.debt_summary_table, 44)
        layout.addWidget(self.debt_summary_table)

        self.debt_aging_table = QTableWidget(0, 3)
        self.debt_aging_table.setHorizontalHeaderLabels(
            ["العميل", "الرصيد", "آخر بيع منذ"]
        )
        self.debt_aging_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._prepare_table(self.debt_aging_table, 44)
        layout.addWidget(self.debt_aging_table)

        refresh_btn = QPushButton("تحديث تحليل الديون")
        refresh_btn.setStyleSheet(get_button_style("info"))
        refresh_btn.clicked.connect(self._load_debt_analysis)
        layout.addWidget(refresh_btn)
        return w

    def _load_debt_analysis(self):
        if not hasattr(self, "debt_summary_table"):
            return
        debts = self.ctrl.get_debt_totals()
        rows = [
            ("ديون العملاء", debts.get("customer_debt", 0), "مبالغ مستحقة على العملاء"),
            (
                "مستحقات الموردين",
                debts.get("supplier_debt", 0),
                "مبالغ مستحقة للموردين",
            ),
            (
                "صافي الالتزام",
                debts.get("supplier_debt", 0) - debts.get("customer_debt", 0),
                "موجب يعني التزام أعلى للموردين",
            ),
        ]
        self.debt_summary_table.setRowCount(len(rows))
        for row, (label, value, note) in enumerate(rows):
            self.debt_summary_table.setItem(row, 0, self._table_item(label))
            self.debt_summary_table.setItem(row, 1, self._money_item(value))
            self.debt_summary_table.setItem(row, 2, self._table_item(note))

        aging = self.ctrl.get_debt_aging_report()
        self.debt_aging_table.setRowCount(len(aging))
        for row, item in enumerate(aging):
            self.debt_aging_table.setItem(
                row, 0, self._table_item(item.get("name", ""))
            )
            self.debt_aging_table.setItem(
                row,
                1,
                self._money_item(item.get("current_balance", 0), Qt.GlobalColor.red),
            )
            self.debt_aging_table.setItem(
                row,
                2,
                self._table_item(f"{int(item.get('days_since_last_sale') or 0)} يوم"),
            )

    # ═══════════ Common Dialogs ═══════════
    def _payment_dialog(self, account_type, account_id, name):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"تسجيل دفع: {name}")
        style_dialog(dialog, width=480)
        layout = QFormLayout(dialog)
        configure_form_layout(layout)

        amt = QDoubleSpinBox()
        amt.setRange(0.01, 1000000)
        amt.setSuffix(" ج.م")
        layout.addRow("المبلغ:", amt)

        desc = QLineEdit()
        desc.setPlaceholderText("الوصف")
        layout.addRow("الوصف:", desc)
        style_form_controls(amt, desc)

        attachment = {"path": ""}
        attachment_lbl = QLabel("لا يوجد مرفق")
        attach_btn = QPushButton("اختيار مرفق")
        attach_btn.setStyleSheet(get_button_style("info"))

        def choose_attachment():
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "اختيار مرفق",
                "",
                "Images/PDF (*.png *.jpg *.jpeg *.pdf);;All Files (*.*)",
            )
            if file_path:
                attachment["path"] = file_path
                attachment_lbl.setText(os.path.basename(file_path))

        attach_btn.clicked.connect(choose_attachment)
        attach_row = QHBoxLayout()
        attach_row.addWidget(attach_btn)
        attach_row.addWidget(attachment_lbl)
        layout.addRow("المرفق:", attach_row)

        btns, save_btn, cancel_btn = action_row()
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                if self.ctrl.record_payment(
                    account_type,
                    account_id,
                    amt.value(),
                    self._safe_user_id(),
                    desc.text(),
                    attachment["path"],
                ):
                    QMessageBox.information(self, "تم", "تم تسجيل العملية بنجاح")
                    self.refresh_data()
            except AccountsValidationError as e:
                QMessageBox.warning(self, "تنبيه", str(e))

    def _settlement_dialog(self, account_type, account_id, name):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"تسوية حساب: {name}")
        style_dialog(dialog, width=480)
        layout = QFormLayout(dialog)
        configure_form_layout(layout)

        amount = QDoubleSpinBox()
        amount.setRange(0.01, 1000000)
        amount.setSuffix(" ج.م")
        layout.addRow("مبلغ التسوية:", amount)

        desc = QLineEdit()
        desc.setPlaceholderText("سبب التسوية")
        layout.addRow("الوصف:", desc)
        style_form_controls(amount, desc)

        attachment = {"path": ""}
        attachment_lbl = QLabel("لا يوجد مرفق")
        attach_btn = QPushButton("اختيار مرفق")
        attach_btn.setStyleSheet(get_button_style("info"))

        def choose_attachment():
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "اختيار مرفق",
                "",
                "Images/PDF (*.png *.jpg *.jpeg *.pdf);;All Files (*.*)",
            )
            if file_path:
                attachment["path"] = file_path
                attachment_lbl.setText(os.path.basename(file_path))

        attach_btn.clicked.connect(choose_attachment)
        attach_row = QHBoxLayout()
        attach_row.addWidget(attach_btn)
        attach_row.addWidget(attachment_lbl)
        layout.addRow("المرفق:", attach_row)

        btns, save_btn, cancel_btn = action_row("حفظ التسوية", save_style="purple")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                if self.ctrl.record_settlement(
                    account_type,
                    account_id,
                    amount.value(),
                    desc.text(),
                    self._safe_user_id(),
                    attachment["path"],
                ):
                    QMessageBox.information(self, "تم", "تم تسجيل التسوية")
                    self.refresh_data()
            except AccountsValidationError as e:
                QMessageBox.warning(self, "تنبيه", str(e))

    def _limit_dialog(self, customer_id, name, current_limit):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"تعديل الحد الائتماني: {name}")
        style_dialog(dialog, width=420)
        layout = QFormLayout(dialog)
        configure_form_layout(layout)

        limit = QDoubleSpinBox()
        limit.setRange(0, 10000000)
        limit.setValue(float(current_limit or 0))
        limit.setSuffix(" ج.م")
        layout.addRow("الحد الائتماني:", limit)
        style_form_controls(limit)

        btns, save_btn, cancel_btn = action_row()
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.ctrl.update_credit_limit(customer_id, limit.value()):
                QMessageBox.information(self, "تم", "تم تحديث الحد الائتماني")
                self.refresh_data()

    def _view_history(self, account_type, account_id, name):
        history = self.ctrl.get_account_history(account_type, account_id)
        if not history:
            QMessageBox.information(self, "تنبيه", "لا يوجد سجل لهذا الحساب")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"كشف حساب: {name}")
        dialog.resize(850, 420)
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)

        table = QTableWidget(len(history), 6)
        table.setHorizontalHeaderLabels(
            ["التاريخ", "النوع", "المبلغ", "المرجع", "الوصف", "المرفق"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )
        self._prepare_table(table, 44)
        for i, h in enumerate(history):
            table.setItem(i, 0, self._table_item(h.get("transaction_date", "")))
            table.setItem(i, 1, self._table_item(h.get("transaction_type", "")))
            table.setItem(i, 2, self._money_item(h.get("amount", 0)))
            table.setItem(
                i,
                3,
                self._table_item(
                    f"{h.get('reference_type', '')} #{h.get('reference_id', '')}"
                ),
            )
            table.setItem(i, 4, self._table_item(h.get("description", "") or ""))
            attachment = h.get("attachment_path")
            if attachment:
                attach_btn = self._action_button("فتح", "#2563eb")
                attach_btn.clicked.connect(
                    lambda _, path=attachment: self._view_attachment(path)
                )
                table.setCellWidget(i, 5, attach_btn)
            else:
                table.setItem(i, 5, self._table_item("-"))
        layout.addWidget(table)

        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    # ═══════════ Refresh ═══════════
    def refresh_data(self):
        try:
            if hasattr(self, "cust_table"):
                self._load_customers()
            if hasattr(self, "sup_table"):
                self._load_suppliers()
            self._load_expenses()
            if hasattr(self, "report_start_date"):
                self._load_financial_report()
            if hasattr(self, "ledger_table"):
                self._load_ledger()
            if hasattr(self, "treasury_table"):
                self._load_treasury()
            if hasattr(self, "aging_table"):
                self._load_debt_analysis()
            if hasattr(self, "customer_debt_card"):
                self._refresh_overview()
            if hasattr(self, "discount_companies_table"):
                self._load_discount_companies()
        except Exception as e:
            logger.error(f"Error refreshing accounts: {e}")
