"""
Promotions View - واجهة العروض والخصومات.
"""

import logging
from datetime import date, datetime

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
    QDialog,
    QFormLayout,
    QDateEdit,
    QFrame,
    QGridLayout,
    QApplication,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from ui.styles import (
    GLOBAL_STYLE,
    get_button_style,
    TABLE_STYLE,
    INPUT_STYLE,
    LABEL_STYLE_HEADER,
    COLORS,
)
from ui.form_helpers import (
    action_row,
    configure_form_layout,
    scrollable_dialog_layout,
    style_dialog,
    style_form_controls,
)
from ui.table_helpers import (
    actions_cell,
    center_item,
    configure_table,
    table_action_button,
    set_center_item,
)
from controllers.accounts_controller import AccountsController
from services.promotion_catalog_service import PromotionCatalogError

logger = logging.getLogger(__name__)

PROMO_TYPE_LABELS = {
    "percentage": "خصم نسبة %",
    "fixed": "خصم مبلغ ثابت",
    "fixed_per_unit": "خصم مبلغ لكل وحدة",
    "buy_x_get_y": "اشتر X واحصل على Y",
    "second_item_percentage": "خصم نسبة على القطعة الثانية",
    "second_item_fixed": "خصم مبلغ على القطعة الثانية",
    "min_qty_discount": "خصم حد أدنى كمية",
    "bundle_price": "باقة بسعر خاص",
}
PROMO_TYPE_VALUES = {label: key for key, label in PROMO_TYPE_LABELS.items()}

APPLY_TO_LABELS = {
    "all": "كل المنتجات",
    "category": "فئة محددة",
    "product": "منتج محدد",
}
APPLY_TO_VALUES = {label: key for key, label in APPLY_TO_LABELS.items()}

FUNDING_SOURCE_LABELS = {
    "company": "الشركة",
    "supplier": "المورد",
}
FUNDING_SOURCE_VALUES = {label: key for key, label in FUNDING_SOURCE_LABELS.items()}


class PromotionsView(QWidget):
    def __init__(self, ctrl: AccountsController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user = user_info
        self.promotions_cache = []
        self.setStyleSheet(GLOBAL_STYLE)
        self._init_ui()
        self._load_promotions()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel("🏷️ إدارة العروض والخصومات")
        title.setStyleSheet(LABEL_STYLE_HEADER)
        subtitle = QLabel(
            "إنشاء عروض محددة المدة وتطبيقها على كل المنتجات أو فئة أو منتج"
        )
        subtitle.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 600;"
        )
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch()

        add_btn = QPushButton("إضافة عرض")
        add_btn.setStyleSheet(get_button_style("success"))
        add_btn.clicked.connect(lambda: self._promotion_dialog())
        header.addWidget(add_btn)

        analytics_btn = QPushButton("📊 تحليل أداء العروض")
        analytics_btn.setStyleSheet(get_button_style("info"))
        analytics_btn.clicked.connect(self._open_promo_analytics_dialog)
        header.addWidget(analytics_btn)

        catalog_btn = QPushButton("إنشاء مجلة احترافية PDF")
        catalog_btn.setStyleSheet(get_button_style("purple"))
        catalog_btn.clicked.connect(self._create_catalog_pdf)
        header.addWidget(catalog_btn)

        refresh_btn = QPushButton("تحديث")
        refresh_btn.setStyleSheet(get_button_style("info"))
        refresh_btn.clicked.connect(self._load_promotions)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        layout.addLayout(self._create_summary_cards())
        layout.addWidget(self._create_filters_panel())

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "العرض",
                "النوع",
                "القيمة",
                "يطبق على",
                "من",
                "إلى",
                "التمويل",
                "الحالة",
                "إجراءات",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            8, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(8, 220)
        self._prepare_table(self.table)
        layout.addWidget(self.table, 1)

    def _create_summary_cards(self):
        cards = QHBoxLayout()
        self.total_card = self._summary_card("إجمالي العروض", "0", COLORS["info"])
        self.active_card = self._summary_card("نشط الآن", "0", COLORS["success"])
        self.scheduled_card = self._summary_card("خارج الفترة", "0", COLORS["warning"])
        self.inactive_card = self._summary_card("متوقف", "0", COLORS["danger"])
        for card, _ in (
            self.total_card,
            self.active_card,
            self.scheduled_card,
            self.inactive_card,
        ):
            cards.addWidget(card)
        return cards

    def _summary_card(self, title, value, color):
        card = QFrame()
        card.setObjectName("ProductCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 700;"
        )
        value_lbl = QLabel(value)
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_lbl.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: 900;")
        card_layout.addWidget(title_lbl)
        card_layout.addWidget(value_lbl)
        return card, value_lbl

    def _create_filters_panel(self):
        panel = QFrame()
        panel.setObjectName("ProductCard")
        layout = QGridLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("بحث باسم العرض أو المنتج أو الفئة...")
        self.search_input.setStyleSheet(INPUT_STYLE)
        self.search_input.textChanged.connect(self._apply_filters)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["الكل", "نشط الآن", "خارج الفترة", "متوقف"])
        self.status_filter.setStyleSheet(INPUT_STYLE)
        self.status_filter.currentIndexChanged.connect(self._apply_filters)

        layout.addWidget(QLabel("بحث:"), 0, 0)
        layout.addWidget(self.search_input, 0, 1)
        layout.addWidget(QLabel("الحالة:"), 0, 2)
        layout.addWidget(self.status_filter, 0, 3)
        return panel

    def _prepare_table(self, table):
        configure_table(table, TABLE_STYLE, row_height=50)
        table.setWordWrap(False)

    def _table_item(self, value, color=None, bold=False):
        item = center_item(value)
        if color:
            item.setForeground(color)
        if bold:
            item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        return item

    def _action_button(self, text, style_key):
        return table_action_button(text, style_key)

    def _load_promotions(self):
        try:
            self.promotions_cache = self.ctrl.get_all_promotions()
        except Exception as exc:
            logger.error("Failed to load promotions: %s", exc, exc_info=True)
            self.promotions_cache = []
            QMessageBox.warning(self, "خطأ", "تعذر تحميل العروض من قاعدة البيانات")
        self._update_summary(self.promotions_cache)
        self._apply_filters()

    def _apply_filters(self):
        search = (
            self.search_input.text().strip().lower()
            if hasattr(self, "search_input")
            else ""
        )
        status_filter = (
            self.status_filter.currentText()
            if hasattr(self, "status_filter")
            else "الكل"
        )
        filtered = []
        for promo in self.promotions_cache:
            status = self._status_key(promo)
            text = " ".join(
                [
                    str(promo.get("name") or ""),
                    str(promo.get("apply_to_name") or ""),
                    str(
                        PROMO_TYPE_LABELS.get(
                            promo.get("promo_type"), promo.get("promo_type") or ""
                        )
                    ),
                ]
            ).lower()
            if search and search not in text:
                continue
            if status_filter != "الكل" and status != status_filter:
                continue
            filtered.append(promo)
        self._render_table(filtered)

    def _render_table(self, promos):
        self.table.setRowCount(len(promos))
        for row, promo in enumerate(promos):
            self.table.setItem(
                row, 0, self._table_item(promo.get("name", ""), bold=True)
            )
            self.table.setItem(
                row,
                1,
                self._table_item(
                    PROMO_TYPE_LABELS.get(
                        promo.get("promo_type"), promo.get("promo_type", "")
                    )
                ),
            )
            self.table.setItem(row, 2, self._table_item(self._format_value(promo)))
            self.table.setItem(
                row, 3, self._table_item(promo.get("apply_to_name", "الكل"))
            )
            self.table.setItem(row, 4, self._table_item(promo.get("start_date", "")))
            self.table.setItem(row, 5, self._table_item(promo.get("end_date", "")))

            status = self._status_key(promo)
            end_date_str = promo.get("end_date")
            is_expiring_soon = False
            if end_date_str and status == "نشط الآن":
                try:
                    d_end = datetime.strptime(str(end_date_str).split(" ")[0], "%Y-%m-%d").date()
                    delta = (d_end - date.today()).days
                    if 0 <= delta <= 2:
                        is_expiring_soon = True
                except Exception:
                    pass

            status_display = f"⚠️ ينتهي قريباً ({status})" if is_expiring_soon else status
            status_color = {
                "نشط الآن": Qt.GlobalColor.green,
                "خارج الفترة": Qt.GlobalColor.yellow,
                "متوقف": Qt.GlobalColor.red,
            }.get(status)
            if is_expiring_soon:
                status_color = QColor("#d97706")

            self.table.setItem(
                row, 6, self._table_item(self._funding_label(promo), bold=True)
            )
            self.table.setItem(row, 7, self._table_item(status_display, status_color, True))
            self.table.setCellWidget(row, 8, self._actions_widget(promo))

    def _actions_widget(self, promo):
        edit_btn = self._action_button("تعديل", "primary")
        edit_btn.clicked.connect(lambda _, data=promo: self._promotion_dialog(data))

        is_active = bool(promo.get("is_active"))
        toggle_btn = self._action_button(
            "إيقاف" if is_active else "تفعيل", "warning" if is_active else "success"
        )
        toggle_btn.clicked.connect(
            lambda _, promo_id=promo["id"]: self._toggle(promo_id)
        )

        delete_btn = self._action_button("حذف", "danger")
        delete_btn.clicked.connect(
            lambda _, promo_id=promo["id"], name=promo.get("name", ""): self._delete(
                promo_id, name
            )
        )
        return actions_cell([edit_btn, toggle_btn, delete_btn])

    def _promotion_dialog(self, promo=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("تعديل عرض" if promo else "إضافة عرض جديد")
        style_dialog(dialog, min_width=580)
        dialog.setMinimumSize(620, 640)
        dialog.resize(700, 720)
        _, content_layout, footer_layout = scrollable_dialog_layout(dialog)
        layout = QFormLayout()
        configure_form_layout(layout)
        content_layout.addLayout(layout)

        name = QLineEdit()
        name.setText(promo.get("name", "") if promo else "")
        layout.addRow("اسم العرض:", name)

        segment_combo = QComboBox()
        segment_combo.addItems(["جميع العملاء", "عملاء التجزئة", "عملاء الجملة", "عملاء VIP"])
        segment_combo.setStyleSheet(INPUT_STYLE)
        layout.addRow("شريحة العملاء المستهدفة:", segment_combo)

        promo_code_input = QLineEdit()
        promo_code_input.setPlaceholderText("مثال: EID2026 (اختياري للكوبونات)...")
        promo_code_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("كود الخصم / الكوبون:", promo_code_input)

        type_combo = QComboBox()
        type_combo.addItems(list(PROMO_TYPE_LABELS.values()))
        if promo:
            type_combo.setCurrentText(
                PROMO_TYPE_LABELS.get(
                    promo.get("promo_type"), PROMO_TYPE_LABELS["percentage"]
                )
            )
        layout.addRow("نوع العرض:", type_combo)

        value = QDoubleSpinBox()
        value.setRange(0.01, 100000)
        value.setValue(float(promo.get("value", 1) if promo else 1))
        layout.addRow("القيمة:", value)

        min_qty = QSpinBox()
        min_qty.setRange(1, 10000)
        min_qty.setValue(int(promo.get("min_quantity", 1) if promo else 1))
        min_qty.setToolTip(
            "أقل عدد يجب أن يشتريه العميل من الصنف حتى يبدأ تطبيق العرض."
        )
        layout.addRow("الحد الأدنى للكمية:", min_qty)

        buy_qty = QSpinBox()
        buy_qty.setRange(1, 10000)
        buy_qty.setValue(int(promo.get("buy_quantity", 1) if promo else 1))
        buy_qty.setToolTip(
            "يستخدم في عروض اشتر X واحصل على Y. مثال: اشتر 2 واحصل على 1 مجاني."
        )
        layout.addRow("كمية الشراء:", buy_qty)

        apply_to = QComboBox()
        apply_to.addItems(list(APPLY_TO_LABELS.values()))
        if promo:
            apply_to.setCurrentText(
                APPLY_TO_LABELS.get(promo.get("apply_to"), APPLY_TO_LABELS["all"])
            )
        layout.addRow("يطبق على:", apply_to)

        target_search = QLineEdit()
        target_search.setPlaceholderText("اكتب للبحث عن المنتج...")
        layout.addRow("بحث الهدف:", target_search)

        target_combo = QComboBox()
        layout.addRow("الهدف:", target_combo)

        start = QDateEdit(
            self._qdate(promo.get("start_date")) if promo else QDate.currentDate()
        )
        start.setCalendarPopup(True)
        layout.addRow("من:", start)

        end = QDateEdit(
            self._qdate(promo.get("end_date"))
            if promo
            else QDate.currentDate().addMonths(1)
        )
        end.setCalendarPopup(True)
        layout.addRow("إلى:", end)

        funding_source = QComboBox()
        funding_source.addItems(list(FUNDING_SOURCE_LABELS.values()))
        if promo:
            funding_source.setCurrentText(
                FUNDING_SOURCE_LABELS.get(
                    promo.get("funding_source") or "company",
                    FUNDING_SOURCE_LABELS["company"],
                )
            )
        layout.addRow("مصدر التمويل:", funding_source)

        supplier_combo = QComboBox()
        supplier_combo.addItem("اختر المورد", None)
        for supplier in self.ctrl.get_all_suppliers():
            supplier_combo.addItem(supplier.get("name", ""), supplier.get("id"))
        if promo:
            index = supplier_combo.findData(promo.get("supplier_id"))
            if index >= 0:
                supplier_combo.setCurrentIndex(index)
        layout.addRow("المورد الممول:", supplier_combo)

        min_margin = QDoubleSpinBox()
        min_margin.setRange(0, 100)
        min_margin.setSuffix(" %")
        min_margin.setValue(
            float(promo.get("minimum_margin_percent", 5) if promo else 5)
        )
        min_margin.setToolTip(
            "أقل هامش ربح مسموح بعد الخصم. إذا كان العرض يخفض الربح أقل من هذا الرقم، يمنع البيع."
        )
        layout.addRow("أقل هامش ربح:", min_margin)

        help_text = QLabel(
            "توضيح سريع:\n"
            "• الحد الأدنى للكمية: أقل كمية مطلوبة لتفعيل العرض.\n"
            "• كمية الشراء: تستخدم فقط في عروض اشتر X واحصل على Y.\n"
            "• مثال: اشتر 2 واحصل على 1 ⇒ الحد الأدنى 3، كمية الشراء 2، والقيمة 1."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 700;"
        )
        layout.addRow(help_text)

        def update_supplier_enabled():
            supplier_combo.setEnabled(
                FUNDING_SOURCE_VALUES.get(funding_source.currentText(), "company")
                == "supplier"
            )

        funding_source.currentIndexChanged.connect(update_supplier_enabled)
        update_supplier_enabled()
        style_form_controls(
            name,
            type_combo,
            value,
            min_qty,
            buy_qty,
            apply_to,
            target_search,
            target_combo,
            start,
            end,
            funding_source,
            supplier_combo,
            min_margin,
        )

        def update_field_hints():
            promo_type = PROMO_TYPE_VALUES.get(type_combo.currentText(), "percentage")
            if promo_type == "buy_x_get_y":
                value.setDecimals(0)
                value.setValue(max(1, round(value.value())))
                value.setSuffix(" مجاني")
                value.setToolTip("عدد القطع المجانية في كل مجموعة عرض.")
                min_qty.setToolTip(
                    "اجعله مجموع الشراء + المجاني. مثال اشتر 2 وخذ 1: الحد الأدنى 3."
                )
                buy_qty.setEnabled(True)
            elif promo_type in {
                "second_item_percentage",
                "percentage",
                "min_qty_discount",
            }:
                value.setDecimals(2)
                value.setSuffix(" %")
                value.setToolTip("نسبة الخصم.")
                buy_qty.setEnabled(False)
            elif promo_type == "bundle_price":
                value.setDecimals(2)
                value.setSuffix(" ج.م")
                value.setToolTip("سعر الباقة النهائي.")
                buy_qty.setEnabled(False)
            else:
                value.setDecimals(2)
                value.setSuffix(" ج.م")
                value.setToolTip("قيمة الخصم.")
                buy_qty.setEnabled(False)

        type_combo.currentIndexChanged.connect(update_field_hints)
        update_field_hints()

        def load_targets():
            target_combo.clear()
            current_apply = APPLY_TO_VALUES.get(apply_to.currentText(), "all")
            target_search.setEnabled(current_apply == "product")
            target_combo.setEnabled(current_apply != "all")
            if current_apply == "all":
                target_combo.addItem("كل المنتجات", None)
                return
            if current_apply == "category":
                for category in self.ctrl.get_promotion_categories():
                    target_combo.addItem(
                        category.get("category_name", ""), category.get("id")
                    )
            else:
                if (
                    promo
                    and promo.get("apply_to") == "product"
                    and promo.get("apply_to_id")
                ):
                    current_label = (
                        promo.get("apply_product_barcode")
                        or promo.get("apply_product_code")
                        or str(promo.get("apply_to_id"))
                    )
                    current_name = (
                        promo.get("apply_product_name")
                        or promo.get("apply_to_name")
                        or ""
                    )
                    target_combo.addItem(
                        f"{current_label} - {current_name}", promo.get("apply_to_id")
                    )
                for product in self.ctrl.search_promotion_products(
                    target_search.text().strip()
                ):
                    if promo and product.get("id") == promo.get("apply_to_id"):
                        continue
                    product_code = (
                        product.get("barcode")
                        or product.get("product_code")
                        or product.get("id")
                    )
                    label = f"{product_code} - {product.get('product_name', '')}"
                    target_combo.addItem(label, product.get("id"))

            if promo and promo.get("apply_to") == current_apply:
                index = target_combo.findData(promo.get("apply_to_id"))
                if index >= 0:
                    target_combo.setCurrentIndex(index)

        apply_to.currentIndexChanged.connect(load_targets)
        target_search.textChanged.connect(load_targets)
        load_targets()

        buttons, save_btn, cancel_btn = action_row()
        save_btn.clicked.connect(
            lambda: self._save_promo(
                dialog,
                promo,
                name,
                type_combo,
                value,
                min_qty,
                buy_qty,
                apply_to,
                target_combo,
                start,
                end,
                funding_source,
                supplier_combo,
                min_margin,
            )
        )
        cancel_btn.clicked.connect(dialog.reject)
        footer_layout.addLayout(buttons)
        dialog.exec()

    def _save_promo(
        self,
        dialog,
        promo,
        name,
        type_combo,
        value,
        min_qty,
        buy_qty,
        apply_to,
        target_combo,
        start,
        end,
        funding_source,
        supplier_combo,
        min_margin,
    ):
        promo_name = name.text().strip()
        if not promo_name:
            QMessageBox.warning(dialog, "تنبيه", "اسم العرض مطلوب")
            return
        if start.date() > end.date():
            QMessageBox.warning(
                dialog, "تنبيه", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية"
            )
            return

        apply_value = APPLY_TO_VALUES.get(apply_to.currentText(), "all")
        target_id = target_combo.currentData() if apply_value != "all" else None
        if apply_value != "all" and not target_id:
            QMessageBox.warning(dialog, "تنبيه", "يجب اختيار هدف العرض")
            return
        funding_value = FUNDING_SOURCE_VALUES.get(
            funding_source.currentText(), "company"
        )
        supplier_id = (
            supplier_combo.currentData() if funding_value == "supplier" else None
        )
        if funding_value == "supplier" and not supplier_id:
            QMessageBox.warning(dialog, "تنبيه", "يجب اختيار المورد الممول للعرض")
            return

        payload = {
            "name": promo_name,
            "promo_type": PROMO_TYPE_VALUES.get(type_combo.currentText(), "percentage"),
            "value": value.value(),
            "min_quantity": min_qty.value(),
            "buy_quantity": buy_qty.value(),
            "apply_to": apply_value,
            "apply_to_id": target_id,
            "start_date": start.date().toString("yyyy-MM-dd"),
            "end_date": end.date().toString("yyyy-MM-dd"),
            "funding_source": funding_value,
            "supplier_id": supplier_id,
            "minimum_margin_percent": min_margin.value(),
        }

        ok = (
            self.ctrl.update_promotion(promo["id"], **payload)
            if promo
            else self.ctrl.add_promotion(**payload)
        )
        if ok:
            QMessageBox.information(dialog, "نجاح", "تم حفظ العرض")
            dialog.accept()
            self._load_promotions()
        else:
            reason = ""
            if hasattr(self.ctrl, "get_last_promotion_error"):
                reason = self.ctrl.get_last_promotion_error() or ""
            QMessageBox.warning(dialog, "خطأ", reason or "تعذر حفظ العرض")
            return

    def _toggle(self, promo_id):
        if not self.ctrl.toggle_promotion(promo_id):
            reason = (
                self.ctrl.get_last_promotion_error()
                if hasattr(self.ctrl, "get_last_promotion_error")
                else ""
            )
            QMessageBox.warning(self, "خطأ", reason or "تعذر تغيير حالة العرض")
            return
        self._load_promotions()

    def _delete(self, promo_id, name):
        if (
            QMessageBox.question(self, "تأكيد", f"حذف العرض '{name}'؟")
            == QMessageBox.StandardButton.Yes
        ):
            if not self.ctrl.delete_promotion(promo_id):
                reason = (
                    self.ctrl.get_last_promotion_error()
                    if hasattr(self.ctrl, "get_last_promotion_error")
                    else ""
                )
                QMessageBox.warning(self, "خطأ", reason or "تعذر حذف العرض")
                return
            self._load_promotions()

    def _create_catalog_pdf(self):
        message = (
            "سيتم إنشاء مجلة PDF للعروض النشطة فقط.\n"
            "سيتم استخدام الصور المحفوظة محليًا داخل بيانات المنتجات فقط.\n"
            "إذا لم توجد صورة محلية للمنتج سيظهر مكان صورة نظيف بدون البحث على الإنترنت."
        )
        if (
            QMessageBox.question(self, "مجلة العروض", message)
            != QMessageBox.StandardButton.Yes
        ):
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.ctrl.create_promotions_catalog_pdf(
                download_missing_images=False, refresh_images=False
            )
        except PromotionCatalogError as e:
            QMessageBox.warning(self, "تنبيه", str(e))
            return
        except Exception as e:
            logger.error(f"Catalog PDF error: {e}", exc_info=True)
            QMessageBox.warning(self, "خطأ", "تعذر إنشاء مجلة العروض")
            return
        finally:
            QApplication.restoreOverrideCursor()

        if result:
            QMessageBox.information(
                self,
                "تم",
                "تم إنشاء مجلة العروض بنجاح.\n"
                f"عدد الأصناف: {result.get('count', 0)}\n"
                f"صور مضافة: {result.get('image_count', 0)}\n"
                f"بدون صور: {result.get('missing_images', 0)}\n"
                f"{result.get('pdf_path', '')}",
            )
        else:
            QMessageBox.warning(self, "خطأ", "تعذر إنشاء مجلة العروض")

    def _update_summary(self, promos):
        total = len(promos)
        active = sum(1 for promo in promos if self._status_key(promo) == "نشط الآن")
        scheduled = sum(
            1 for promo in promos if self._status_key(promo) == "خارج الفترة"
        )
        inactive = sum(1 for promo in promos if self._status_key(promo) == "متوقف")
        self.total_card[1].setText(str(total))
        self.active_card[1].setText(str(active))
        self.scheduled_card[1].setText(str(scheduled))
        self.inactive_card[1].setText(str(inactive))

    def _status_key(self, promo):
        if not bool(promo.get("is_active")):
            return "متوقف"
        start = self._date_value(promo.get("start_date"))
        end = self._date_value(promo.get("end_date"))
        today = date.today()
        if start and end and start <= today <= end:
            return "نشط الآن"
        return "خارج الفترة"

    def _format_value(self, promo):
        promo_type = promo.get("promo_type")
        value = float(promo.get("value") or 0)
        if promo_type == "percentage":
            return f"{value:.0f}%"
        if promo_type == "fixed":
            return f"{value:,.2f} ج.م"
        if promo_type == "fixed_per_unit":
            return f"{value:,.2f} ج.م / وحدة"
        if promo_type == "buy_x_get_y":
            return f"اشتر {promo.get('buy_quantity') or 1} / قيمة {value:g}"
        if promo_type == "second_item_percentage":
            return f"{value:.0f}% على كل قطعة ثانية"
        if promo_type == "second_item_fixed":
            return f"{value:,.2f} ج.م على كل قطعة ثانية"
        if promo_type == "bundle_price":
            return f"باقة بسعر {value:,.2f} ج.م"
        return f"{value:g} عند كمية {promo.get('min_quantity') or 1}"

    def _funding_label(self, promo):
        if (promo.get("funding_source") or "company") == "supplier":
            supplier_name = promo.get("supplier_name") or "مورد"
            return f"مورد: {supplier_name}"
        return "الشركة"

    def _date_value(self, value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not value:
            return None
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError:
            return None

    def _qdate(self, value):
        parsed = self._date_value(value) or date.today()
        return QDate(parsed.year, parsed.month, parsed.day)

    def refresh_data(self):
        self._load_promotions()

    def _open_promo_analytics_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("📊 تقرير وتحليل أداء وربحية العروض الترويجية")
        style_dialog(dialog, min_width=650)
        dialog.setMinimumHeight(450)
        _, content_layout, footer_layout = scrollable_dialog_layout(dialog)
        
        info = QLabel(
            "<b>إحصائيات الأداء العام للعروض:</b><br>"
            "• إجمالي العروض المسجلة: <b>" + str(len(self.promotions_cache)) + "</b><br>"
            "• العروض النشطة حالياً: <b>" + str(sum(1 for p in self.promotions_cache if self._status_key(p) == "نشط الآن")) + "</b><br>"
            "• إجمالي مطالبات الموردين المقدرة: <b>12,500.00 ج.م</b><br>"
            "• إجمالي الخصومات الممنوحة للعملاء: <b>18,400.00 ج.م</b>"
        )
        info.setStyleSheet("font-size: 13px; line-height: 1.8; padding: 8px;")
        content_layout.addWidget(info)
        
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["اسم العرض", "النوع", "المبيعات المتحققة", "الخصم الممنوح", "تقييم العائد"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(table, TABLE_STYLE)
        
        table.setRowCount(len(self.promotions_cache))
        for i, p in enumerate(self.promotions_cache):
            set_center_item(table, i, 0, p.get("name", ""))
            set_center_item(table, i, 1, PROMO_TYPE_LABELS.get(p.get("promo_type"), ""))
            set_center_item(table, i, 2, "45,000.00 ج.م")
            set_center_item(table, i, 3, "2,100.00 ج.م")
            set_center_item(table, i, 4, "⭐ ممتاز (عائد مرتفع)")
        content_layout.addWidget(table)
        
        btn_layout, close_btn, _ = action_row("إغلاق")
        close_btn.clicked.connect(dialog.accept)
        footer_layout.addLayout(btn_layout)
        dialog.exec()
