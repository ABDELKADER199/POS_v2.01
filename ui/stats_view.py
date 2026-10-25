"""
Stats View - واجهة الإحصائيات والتقارير (Clean Architecture)
تعتمد فقط على StatsController وتصمم الواجهة بنفس مستوى النظام القديم
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QHeaderView, QGridLayout, QFrame,
    QScrollArea, QPushButton, QDateEdit,
    QComboBox, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.custom_charts import SimpleBarChart, DonutChart

from ui.styles import COLORS, TABLE_STYLE, GLOBAL_STYLE, get_button_style
from ui.table_helpers import center_item, configure_table
from controllers.stats_controller import StatsController

logger = logging.getLogger(__name__)


class StatsView(QWidget):
    """واجهة عرض إحصائيات المبيعات - Clean Architecture"""

    def __init__(self, ctrl: StatsController, user_info: dict, backup_controller=None, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user_info = user_info
        self.backup_controller = backup_controller
        self.view_sections = {}
        self.last_dashboard_data = None
        self.last_dashboard_context = None
        self.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        self._init_ui()
        self._load_stores()
        self.refresh_data()

        # Real-time refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(10000) # Every 10 seconds

    # ═══════════════════════════════════════════════════
    #  UI Construction
    # ═══════════════════════════════════════════════════

    def _init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        self._build_header()
        self._build_metrics()
        self._build_charts_placeholder()
        self._build_tables()

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 0, 6, 0)
        outer.addWidget(scroll)

    # ── Header & Filters ──────────────────────────────

    def _build_header(self):
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                border-radius: 16px;
                border: 1px solid {COLORS['border']};
                padding: 15px;
            }}
        """)
        header_layout = QHBoxLayout(header_frame)

        title = QLabel("📊 لوحة القيادة")
        title.setStyleSheet(f"color: {COLORS['text_on_brand']}; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Store Filter
        self.store_label = QLabel("الفرع:")
        self.store_label.setStyleSheet("color: #94A3B8; font-weight: bold;")
        header_layout.addWidget(self.store_label)
        self.store_combo = QComboBox()
        self.store_combo.setStyleSheet(GLOBAL_STYLE)
        self.store_combo.setMinimumWidth(150)
        self.store_combo.addItem("الكل", None)
        header_layout.addWidget(self.store_combo)

        # Date Presets
        for name, func in [("اليوم", self._set_today), ("أسبوع", self._set_week), ("شهر", self._set_month)]:
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['secondary']};
                    color: {COLORS['text_on_brand']}; border: none; padding: 6px 12px; border-radius: 6px; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {COLORS['hover']}; }}
            """)
            btn.clicked.connect(func)
            header_layout.addWidget(btn)

        # Date Range
        self.date_from = QDateEdit(QDate.currentDate())
        self.date_to = QDateEdit(QDate.currentDate())
        for d in [self.date_from, self.date_to]:
            d.setDisplayFormat("yyyy-MM-dd")
            d.setCalendarPopup(True)
            d.setStyleSheet(GLOBAL_STYLE)
            d.setFixedWidth(110)

        header_layout.addWidget(QLabel("من:", styleSheet="color: #94A3B8;"))
        header_layout.addWidget(self.date_from)
        header_layout.addWidget(QLabel("إلى:", styleSheet="color: #94A3B8;"))
        header_layout.addWidget(self.date_to)

        # Apply
        apply_btn = QPushButton("🔄 تحديث")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: {COLORS['text_on_brand']}; border: none; padding: 6px 20px; border-radius: 6px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #059669; }}
        """)
        apply_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(apply_btn)

        # مسافة لدفع الأزرار الإضافية لأقصى اليسار
        header_layout.addStretch()

        # Extra Buttons like old app
        self.btn_export_pdf = QPushButton("📄 تقرير PDF")
        self.btn_export_pdf.setStyleSheet(get_button_style("primary"))
        self.btn_export_pdf.clicked.connect(self._export_stats_pdf)
        header_layout.addWidget(self.btn_export_pdf)

        self.btn_pl = QPushButton("قائمة الدخل (PL)")
        self.btn_pl.setStyleSheet(get_button_style("purple"))
        self.btn_pl.clicked.connect(self._show_pl)
        header_layout.addWidget(self.btn_pl)

        btn_cust = QPushButton("تخصيص")
        btn_cust.setStyleSheet(get_button_style("gray"))
        btn_cust.clicked.connect(self._show_customize)
        header_layout.addWidget(btn_cust)

        self.btn_backup = QPushButton("نسخة احتياطية")
        self.btn_backup.setStyleSheet(get_button_style("info"))
        self.btn_backup.clicked.connect(self._show_backup)
        header_layout.addWidget(self.btn_backup)

        self.main_layout.addWidget(header_frame)

    # ── Metric Cards ──────────────────────────────────

    def _build_metrics(self):
        self.metrics_grid = QGridLayout()
        self.metrics_grid.setSpacing(15)

        # Row 0: Sales & Profits
        self.card_sales = self._create_card("إجمالي المبيعات", "0.00 ج.م", "#10B981", "💰")
        self.card_profit = self._create_card("صافي الربح", "0.00 ج.م", "#8B5CF6", "📈")
        self.card_atv = self._create_card("متوسط البيع (ATV)", "0.00 ج.م", "#3B82F6", "🛍️")
        self.card_margin = self._create_card("هامش الربح", "0%", "#F59E0B", "📊")

        # Row 1: Invoices & Returns
        self.card_orders = self._create_card("عدد الفواتير", "0", "#06B6D4", "🧾")
        self.card_returns = self._create_card("المرتجعات", "0.00 ج.م", "#EF4444", "↩️")
        self.card_ret_rate = self._create_card("معدل الارتجاع", "0%", "#F43F5E", "📉")
        self.card_retention = self._create_card("الاحتفاظ بالعملاء", "0%", "#8B5CF6", "👥")

        # Row 2: Cash Movements
        self.card_cash_in = self._create_card("إجمالي المقبوضات النقدي", "0.00 ج.م", "#10B981", "📥")
        self.card_cash_out = self._create_card("إجمالي المدفوعات النقدي", "0.00 ج.م", "#F43F5E", "📤")
        self.card_cash_net = self._create_card("صافي الحركة النقدية", "0.00 ج.م", "#F59E0B", "💱")
        self.card_liquidity = self._create_card("السيولة الفعلية (حالياً)", "0.00 ج.م", "#10B981", "🏦")

        # Row 3: Liabilities & Inventory
        self.card_inv_val = self._create_card("إجمالي تكلفة البضاعة", "0.00 ج.م", "#6366F1", "📦")
        self.card_paid_total = self._create_card("إجمالي المسدد (للآن)", "0.00 ج.م", "#10B981", "💸")
        self.card_debt_total = self._create_card("إجمالي المديونية (للآن)", "0.00 ج.م", "#F43F5E", "🤝")
        self.card_discounts = self._create_card("إجمالي الخصومات والعروض", "0.00 ج.م", "#EAB308", "🏷️")

        self.metrics_grid.addWidget(self.card_sales, 0, 0)
        self.metrics_grid.addWidget(self.card_profit, 0, 1)
        self.metrics_grid.addWidget(self.card_atv, 0, 2)
        self.metrics_grid.addWidget(self.card_margin, 0, 3)

        self.metrics_grid.addWidget(self.card_orders, 1, 0)
        self.metrics_grid.addWidget(self.card_returns, 1, 1)
        self.metrics_grid.addWidget(self.card_ret_rate, 1, 2)
        self.metrics_grid.addWidget(self.card_inv_val, 1, 3)

        self.metrics_grid.addWidget(self.card_cash_in, 2, 0)
        self.metrics_grid.addWidget(self.card_cash_out, 2, 1)
        self.metrics_grid.addWidget(self.card_cash_net, 2, 2)
        self.metrics_grid.addWidget(self.card_liquidity, 2, 3)

        self.metrics_grid.addWidget(self.card_paid_total, 3, 0)
        self.metrics_grid.addWidget(self.card_debt_total, 3, 1)
        self.metrics_grid.addWidget(self.card_discounts, 3, 2)
        self.metrics_grid.addWidget(self.card_retention, 3, 3)

        self.main_layout.addLayout(self.metrics_grid)

    def _create_card(self, title: str, value: str, color: str, icon: str) -> QFrame:
        card = QFrame()
        card.setMinimumHeight(160)
        card.setMinimumWidth(220)

        stack_layout = QGridLayout(card)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.setSpacing(0)

        card.setStyleSheet(f"""
            QFrame {{
                background-color: #020617;
                border: 2px solid {COLORS['border']};
                border-radius: 20px;
            }}
            QFrame:hover {{
                border: 2px solid {color};
                background-color: #0F172A;
            }}
        """)

        # Layer 1: Background Icon
        bg_icon = QLabel(icon)
        bg_icon.setStyleSheet(f"font-size: 160px; color: {color}66; background: transparent; border: none;")
        bg_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bg_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        stack_layout.addWidget(bg_icon, 0, 0)

        # Layer 2: Darkening Overlay
        overlay = QFrame()
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); border-radius: 20px; border: none;")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        stack_layout.addWidget(overlay, 0, 0)

        # Layer 3: Content
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent; border: none;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(25, 25, 25, 25)
        content_layout.setSpacing(5)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94A3B8; font-size: 16px; font-weight: bold; background: transparent;")
        content_layout.addWidget(lbl_title)

        lbl_value = QLabel(value)
        lbl_value.setObjectName("value_label")
        lbl_value.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: 900; background: transparent;")
        content_layout.addWidget(lbl_value)

        stack_layout.addWidget(content_widget, 0, 0)
        return card

    # ── Charts Placeholder ────────────────────────────

    def _build_charts_placeholder(self):
        """الرسوم البيانية باستخدام custom_charts"""
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(15)

        # Payment Method Chart (Donut)
        self.payment_chart = DonutChart(title="توزيع طرق الدفع")
        container3 = self._wrap_container(self.payment_chart)
        container3.setMinimumWidth(300)
        charts_layout.addWidget(container3, stretch=1)

        # Hourly Sales Chart (Bar)
        self.hourly_chart = SimpleBarChart(title="ذروة المبيعات حسب الساعة")
        self.hourly_chart.bar_color = QColor("#10B981")
        container2 = self._wrap_container(self.hourly_chart)
        charts_layout.addWidget(container2, stretch=2)

        # Daily Trend Chart (Bar)
        self.trend_chart = SimpleBarChart(title="اتجاه المبيعات اليومية")
        self.trend_chart.bar_color = QColor("#3B82F6")
        container1 = self._wrap_container(self.trend_chart)
        charts_layout.addWidget(container1, stretch=2)

        self.main_layout.addLayout(charts_layout)

    # ── Detail Tables ─────────────────────────────────

    def _build_tables(self):
        self.branch_cards_widget = QWidget()
        branch_layout = QVBoxLayout(self.branch_cards_widget)
        branch_layout.setContentsMargins(0, 0, 0, 0)
        self.branch_cards_layout = QGridLayout()
        self.branch_cards_layout.setSpacing(12)
        branch_layout.addLayout(self.branch_cards_layout)
        branch_container = self._wrap_container(self.branch_cards_widget, "🏢 أداء الفروع")
        self.view_sections["أداء الفروع"] = branch_container
        self.main_layout.addWidget(branch_container)

        grid = QGridLayout()
        grid.setSpacing(15)

        # Row 0
        self.store_sales_table = self._create_table(["الفرع", "المبيعات", "عدد الفواتير"])
        store_container = self._wrap_container(self.store_sales_table, "🏢 تفاصيل مبيعات الفروع")
        self.view_sections["تفاصيل مبيعات الفروع"] = store_container
        grid.addWidget(store_container, 0, 0, 1, 2)

        # Row 1
        self.most_returned_table = self._create_table(["المنتج", "الكمية المرتجعة"])
        c_returns = self._wrap_container(self.most_returned_table, "↩️ الأكثر ارتجاعاً")
        self.view_sections["المنتجات الأكثر ارتجاعاً"] = c_returns
        grid.addWidget(c_returns, 1, 0)

        self.top_products_table = self._create_table(["المنتج", "الكمية", "الإيراد"])
        top_products_container = self._wrap_container(self.top_products_table, "🏆 الأكثر مبيعاً")
        self.view_sections["المنتجات الأكثر مبيعاً"] = top_products_container
        grid.addWidget(top_products_container, 1, 1)

        # Row 2
        self.top_customers_table = self._create_table(["العميل", "الهاتف", "إجمالي الشراء", "المنتج المفضل"])
        top_customers_container = self._wrap_container(self.top_customers_table, "👥 كبار العملاء")
        self.view_sections["كبار العملاء"] = top_customers_container
        grid.addWidget(top_customers_container, 2, 0)
        
        self.return_reasons_table = self._create_table(["سبب المرتجع", "التكرار"])
        c_reasons = self._wrap_container(self.return_reasons_table, "📝 أسباب المرتجع")
        self.view_sections["أسباب المرتجعات"] = c_reasons
        grid.addWidget(c_reasons, 2, 1)

        # Row 3
        self.supplier_stats_table = self._create_table(["المورد", "إجمالي المشتريات", "إجمالي المسدد", "الرصيد المتبقي", "عدد الأصناف", "عدد الفواتير"])
        c_suppliers = self._wrap_container(self.supplier_stats_table, "🤝 إحصائيات الموردين")
        self.supplier_stats_section = c_suppliers
        c_suppliers.hide()
        self.view_sections["إحصائيات الموردين"] = c_suppliers
        grid.addWidget(c_suppliers, 3, 0, 1, 2)

        self.product_sales_table = self._create_table(["الكود", "اسم الصنف", "الفرع", "التاريخ", "الكمية", "الإيراد", "إجمالي التكلفة"])
        self.product_sales_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        c_product_sales = self._wrap_container(self.product_sales_table, "📦 مبيعات الأصناف اليومية")
        self.product_sales_section = c_product_sales
        c_product_sales.hide()
        self.view_sections["مبيعات الأصناف اليومية"] = c_product_sales
        grid.addWidget(c_product_sales, 4, 0, 1, 2)

        self.inventory_table = self._create_table(["كود الصنف", "اسم الصنف", "الكمية بالمخزن", "سعر الشراء", "إجمالي القيمة"])
        self.inventory_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        c_inventory = self._wrap_container(self.inventory_table, "📦 تقييم البضاعة بالمخازن (حسب الكميات)")
        self.inventory_section = c_inventory
        c_inventory.hide()
        self.view_sections["تقييم البضاعة بالمخازن"] = c_inventory
        grid.addWidget(c_inventory, 5, 0, 1, 2)

        self.discounts_table = self._create_table(["نوع الخصم / العرض", "إجمالي المبلغ", "الوصف والتفاصيل"])
        self.discounts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.discounts_table.itemDoubleClicked.connect(self._on_discount_row_double_clicked)
        self.store_sales_table.itemDoubleClicked.connect(self._on_store_row_double_clicked)
        c_discounts = self._wrap_container(self.discounts_table, "🏷️ تفاصيل الخصومات والعروض الترويجية")
        self.view_sections["تفاصيل الخصومات والعروض"] = c_discounts
        grid.addWidget(c_discounts, 6, 0, 1, 2)

        self.main_layout.addLayout(grid)

    # ═══════════════════════════════════════════════════
    #  Helpers
    # ═══════════════════════════════════════════════════

    def _create_table(self, headers: list) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setMinimumHeight(55)
        configure_table(table, f"""
            {TABLE_STYLE}
            QTableWidget {{
                background-color: transparent;
                border: none;
            }}
            QHeaderView::section {{
                background-color: rgba(15, 23, 42, 0.8);
                color: {COLORS['success']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """, row_height=50)
        table.setMinimumHeight(200)
        return table

    def _wrap_container(self, widget, title: str = None) -> QFrame:
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(30, 41, 59, 0.5);
                border-radius: 20px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        if title:
            lbl = QLabel(title)
            lbl.setStyleSheet(f"color: {COLORS['text_on_brand']}; font-size: 16px; font-weight: bold; margin-bottom: 15px;")
            layout.addWidget(lbl)
        layout.addWidget(widget)
        return container

    def _populate_table(self, table: QTableWidget, data: list, keys: list):
        table.setRowCount(0)
        for row_idx, item in enumerate(data):
            table.insertRow(row_idx)
            for col_idx, key in enumerate(keys):
                val = item.get(key, '')
                if isinstance(val, (int, float)):
                    text = f"{val:,.2f}" if isinstance(val, float) else str(val)
                else:
                    text = str(val) if val else ''
                table.setItem(row_idx, col_idx, center_item(text))

    # ═══════════════════════════════════════════════════
    #  Data Loading
    # ═══════════════════════════════════════════════════

    def _load_stores(self):
        stores = self.ctrl.get_stores(self.user_info)
        self.store_combo.clear()
        if len(stores) == 1:
            store = stores[0]
            self.store_combo.addItem(store.get('store_name', 'فرعي'), store.get('id'))
            self.store_combo.setEnabled(False)
            self.store_label.setText("الفرع:")
            return
        self.store_combo.addItem("الكل", None)
        for s in stores:
            self.store_combo.addItem(s['store_name'], s['id'])

    def refresh_data(self):
        """تحديث جميع البيانات من Controller"""
        s_date = self.date_from.date().toString("yyyy-MM-dd")
        e_date = self.date_to.date().toString("yyyy-MM-dd")
        store_id = self.store_combo.currentData()

        # A failed refresh invalidates the previous result.  Export must never
        # relabel stale data with the newly selected period or store.
        self.last_dashboard_data = None
        self.last_dashboard_context = None
        try:
            data = self.ctrl.get_dashboard_data(s_date, e_date, store_id, self.user_info)
        except Exception as e:
            logger.error("Error fetching dashboard data in view: %s", e, exc_info=True)
            QMessageBox.critical(self, "خطأ في جلب الإحصائيات", "تعذر تحميل بيانات الإحصائيات. حاول مرة أخرى لاحقًا.")
            return

        self.last_dashboard_data = data
        self.last_dashboard_context = (s_date, e_date, store_id)
        capabilities = data.get("capabilities", {})
        self.btn_pl.setVisible(bool(capabilities.get("can_view_detailed_stats")))
        self.btn_export_pdf.setVisible(True)
        self.supplier_stats_section.setVisible(bool(capabilities.get("can_view_all_stats")))
        self.product_sales_section.setVisible(bool(capabilities.get("can_view_detailed_stats")))
        self.inventory_section.setVisible(bool(capabilities.get("can_view_detailed_stats")))
        m = data.get('metrics') or {}

        # Update Cards
        sales_growth = m.get('sales_growth', 0)
        profit_growth = m.get('profit_growth', 0)
        disc_growth = m.get('discounts_growth', 0)

        self._update_card(self.card_sales, f"{m.get('total_sales', 0):,.2f} ج.م\n({sales_growth:+.1f}% مقارنة بالسابقة)")
        self._update_card(self.card_profit, f"{m.get('net_profit', 0):,.2f} ج.م\n({profit_growth:+.1f}% مقارنة بالسابقة)")
        self._update_card(self.card_atv, f"{m.get('avg_ticket', 0):,.2f} ج.م")
        self._update_card(self.card_margin, f"{m.get('profit_margin', 0):.1f}%")
        self._update_card(self.card_orders, f"{m.get('invoice_count', 0)}")
        self._update_card(self.card_returns, f"{m.get('total_returns', 0):,.2f} ج.م")
        self._update_card(self.card_ret_rate, f"{m.get('return_rate', 0):.1f}%")
        self._update_card(self.card_inv_val, f"{m.get('inventory_value', 0):,.2f} ج.م")
        
        # New 7 metrics:
        self._update_card(self.card_cash_in, f"{m.get('cash_in', 0):,.2f} ج.م")
        self._update_card(self.card_cash_out, f"{m.get('cash_out', 0):,.2f} ج.م")
        self._update_card(self.card_cash_net, f"{m.get('net_cash', 0):,.2f} ج.م")
        self._update_card(self.card_liquidity, f"{m.get('vault_liquidity', 0):,.2f} ج.م")
        self._update_card(self.card_paid_total, f"{m.get('total_paid', 0):,.2f} ج.م")
        self._update_card(self.card_debt_total, f"{m.get('total_debt', 0):,.2f} ج.م")
        self._update_card(self.card_retention, f"{m.get('retention_rate', 0):.1f}%")
        self._update_card(self.card_discounts, f"{m.get('total_discounts', 0):,.2f} ج.م\n({disc_growth:+.1f}% مقارنة بالسابقة)")

        # Update Graphical Charts
        self.trend_chart.set_data(data['daily_chart'])
        self.hourly_chart.set_data(data['hourly_chart'])
        
        payment_formatted = [
            {"label": r.get('payment_method', 'Unknown'), "total": r.get('total', 0)}
            for r in data['payment_chart']
        ]
        self.payment_chart.set_data(payment_formatted)

        # Update Tables
        self._populate_table(self.store_sales_table, data['store_sales'],
                             ['store_name', 'total_sales', 'invoice_count'])
        self._populate_table(self.top_products_table, data['top_products'],
                             ['product_name', 'total_qty', 'total_revenue'])
        self._populate_table(self.top_customers_table, data['top_customers'],
                             ['customer_name', 'customer_phone', 'total_spent', 'favorite_product'])
        self._populate_table(self.most_returned_table, data['most_returned'],
                             ['product', 'returned_qty'])
        self._populate_table(self.return_reasons_table, data['return_reasons'],
                             ['reason', 'reason_count'])
        self._populate_table(self.supplier_stats_table, data['supplier_stats'],
                             ['supplier_name', 'total_purchases', 'total_paid', 'remaining_balance', 'items_count', 'invoice_count'])
        self._populate_table(self.product_sales_table, data.get('product_sales_report', []),
                             ['product_code', 'product_name', 'store_name', 'sale_date', 'total_qty', 'total_revenue', 'total_cost'])
                             
        self._populate_table(self.inventory_table, data.get('inventory_details', []),
                             ['product_code', 'product_name', 'qty', 'buy_price', 'total_product_value'])
        self._populate_table(self.discounts_table, data.get('discount_breakdown', []),
                             ['discount_type', 'amount', 'description'])

        self._refresh_branch_cards(data['store_sales'])

    def _update_card(self, card: QFrame, text: str):
        lbl = card.findChild(QLabel, "value_label")
        if lbl:
            lbl.setText(text)

    def _refresh_branch_cards(self, stores: list):
        while self.branch_cards_layout.count():
            item = self.branch_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for index, store in enumerate(stores[:8]):
            sales = float(store.get('total_sales', 0) or 0)
            invoices = int(store.get('invoice_count', 0) or 0)
            color = "#10B981" if sales > 5000 else "#3B82F6" if sales > 0 else "#64748B"

            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #020617;
                    border: 1px solid {color};
                    border-radius: 14px;
                }}
            """)
            layout = QVBoxLayout(card)
            name = QLabel(str(store.get('store_name', '')))
            name.setStyleSheet(f"color: {COLORS['text_on_brand']}; font-weight: bold; font-size: 13px;")
            amount = QLabel(f"{sales:,.0f} ج.م")
            amount.setStyleSheet(f"color: {color}; font-weight: 900; font-size: 18px;")
            count = QLabel(f"{invoices} فاتورة")
            count.setStyleSheet("color: #94A3B8; font-size: 12px;")
            layout.addWidget(name)
            layout.addWidget(amount)
            layout.addWidget(count)
            self.branch_cards_layout.addWidget(card, index // 4, index % 4)

    # ── Extra Button Actions ──────────────────────────
    def _export_stats_pdf(self):
        try:
            if not self.last_dashboard_data:
                self.refresh_data()
            if not self.last_dashboard_data:
                QMessageBox.warning(self, "تنبيه", "لا توجد بيانات إحصائيات متاحة للتصدير.")
                return

            s_date = self.date_from.date().toString("yyyy-MM-dd")
            e_date = self.date_to.date().toString("yyyy-MM-dd")
            selected_store_id = self.store_combo.currentData()
            if self.last_dashboard_context != (s_date, e_date, selected_store_id):
                QMessageBox.warning(self, "تنبيه", "يجب تحديث التقرير الحالي قبل التصدير.")
                return
            store_name = self.store_combo.currentText() or "كل الفروع"
            user_name = self.user_info.get("name") or self.user_info.get("username") or "مستخدم"

            result = self.ctrl.export_dashboard(
                s_date, e_date, selected_store_id, self.user_info, store_name, user_name
            )
            if result.get("saved"):
                QMessageBox.information(
                    self,
                    "تم التصدير",
                    f"تم حفظ تقرير الإحصائيات PDF بنجاح:\n{result.get('pdf_path')}",
                )
            else:
                QMessageBox.warning(self, "تنبيه", "تعذر حفظ تقرير الإحصائيات PDF.")
        except Exception as e:
            logger.error("Error exporting stats PDF: %s", e, exc_info=True)
            QMessageBox.critical(self, "خطأ", "تعذر تصدير تقرير الإحصائيات.")

    def _show_pl(self):
        from ui.profit_loss_dialog import ProfitLossDialog
        s_date = self.date_from.date().toString("yyyy-MM-dd")
        e_date = self.date_to.date().toString("yyyy-MM-dd")
        store_id = self.store_combo.currentData()
        
        dialog = ProfitLossDialog(s_date, e_date, store_id, self.ctrl, self.user_info, self)
        dialog.exec()

    def _show_customize(self):
        from PyQt6.QtWidgets import QMenu, QWidget
        from PyQt6.QtGui import QAction
        
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background-color: #1E293B; color: {COLORS['text_on_brand']}; padding: 5px; border: 1px solid #334155; }} QMenu::item:selected {{ background-color: #3B82F6; }}")
        
        sections = {
            **self.view_sections,
            "توزيع طرق الدفع": self.payment_chart.parent(),
            "ذروة المبيعات بالساعة": self.hourly_chart.parent(),
            "اتجاه المبيعات": self.trend_chart.parent(),
        }
        
        for name, widget in sections.items():
            if not isinstance(widget, QWidget):
                continue
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(widget.isVisible())
            # Use default argument binding for late binding issue in loop
            action.triggered.connect(lambda checked, w=widget: w.setVisible(checked))
            menu.addAction(action)
            
        # Show at button pos
        btn = self.sender()
        if btn:
            menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _show_backup(self):
        try:
            if self.backup_controller is None:
                raise RuntimeError("Backup controller is not configured")
            self.setCursor(Qt.CursorShape.WaitCursor)
            created_by = self.user_info.get('id', 1) if self.user_info else 1
            success, message = self.backup_controller.execute_backup(backup_type='manual', created_by=created_by)
            self.setCursor(Qt.CursorShape.ArrowCursor)

            if success:
                QMessageBox.information(self, "نجاح", f"تم إنشاء النسخة الاحتياطية بنجاح:\n{message}")
            else:
                QMessageBox.critical(self, "خطأ", f"فشل إنشاء النسخة الاحتياطية:\n{message}")
        except Exception as e:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            logger.error("Error executing backup from stats view: %s", e, exc_info=True)
            QMessageBox.critical(self, "خطأ", "تعذر إنشاء النسخة الاحتياطية.")

    # ── Filter Presets ────────────────────────────────

    def _set_today(self):
        self.date_from.setDate(QDate.currentDate())
        self.date_to.setDate(QDate.currentDate())
        self.refresh_data()

    def _set_week(self):
        today = QDate.currentDate()
        self.date_from.setDate(today.addDays(-6))
        self.date_to.setDate(today)
        self.refresh_data()

    def _set_month(self):
        today = QDate.currentDate()
        self.date_from.setDate(QDate(today.year(), today.month(), 1))
        self.date_to.setDate(QDate(today.year(), today.month(), today.daysInMonth()))
        self.refresh_data()

    def _on_discount_row_double_clicked(self, item):
        row = item.row()
        disc_type_item = self.discounts_table.item(row, 0)
        amount_item = self.discounts_table.item(row, 1)
        desc_item = self.discounts_table.item(row, 2)
        if disc_type_item and amount_item:
            QMessageBox.information(
                self,
                "تفاصيل الخصم (Drill-Down)",
                f"نوع الخصم: {disc_type_item.text()}\n"
                f"إجمالي المبلغ: {amount_item.text()}\n"
                f"الوصف والتفاصيل: {desc_item.text() if desc_item else ''}\n\n"
                "💡 يمكنك مراجعة الفواتير المفصلة عبر تقارير المبيعات وسجل الفواتير."
            )

    def _on_store_row_double_clicked(self, item):
        row = item.row()
        store_item = self.store_sales_table.item(row, 0)
        sales_item = self.store_sales_table.item(row, 1)
        invoices_item = self.store_sales_table.item(row, 2)
        if store_item:
            QMessageBox.information(
                self,
                "تفاصيل أداء الفرع (Drill-Down)",
                f"الفرع: {store_item.text()}\n"
                f"إجمالي المبيعات: {sales_item.text() if sales_item else '0'}\n"
                f"عدد الفواتير: {invoices_item.text() if invoices_item else '0'}"
            )
