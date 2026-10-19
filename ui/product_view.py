"""
صفحة إدارة المنتجات والمخزون
Product Management View
"""

import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QTableWidget,
    QHeaderView,
    QMessageBox,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QDialog,
    QFormLayout,
    QTabWidget,
    QCheckBox,
    QFileDialog,
    QInputDialog,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QPolygon
from PyQt6.QtPrintSupport import QPrinterInfo
from controllers.transfers_controller import TransfersController
from ui.transfers_view import TransfersView
from ui.styles import COLORS, TABLE_STYLE, TAB_STYLE, INPUT_STYLE, get_button_style
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
    set_center_item,
    table_action_button,
)
from ui.subtab_dropdown import create_subtab_dropdown
from utils.barcode_service import BarcodeService
from utils.printer_service import BarcodePrintJob, PrinterService
from utils.permissions import PermissionPolicy

PRODUCT_TABLE_STYLE = TABLE_STYLE + f"""
    QTableWidget {{
        outline: 0;
        font-size: 13px;
    }}
    QTableWidget::item:selected {{
        border: none;
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: {COLORS['bg_input']};
        border: none;
        width: 10px;
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {COLORS['border']};
        border-radius: 5px;
        min-height: 24px;
        min-width: 24px;
    }}
"""


class FilterSortHeader(QHeaderView):
    filterClicked = pyqtSignal(int)
    sortClicked = pyqtSignal(int)

    def __init__(
        self, orientation, parent=None, filter_columns=None, sortable_columns=None
    ):
        super().__init__(orientation, parent)
        self.filter_columns = set(filter_columns or [])
        self.sortable_columns = set(sortable_columns or [])
        self.sort_states = {}
        self.setSectionsClickable(True)
        self.setHighlightSections(False)

    def set_sort_state(self, column, direction):
        self.sort_states = {}
        if column is not None and direction:
            self.sort_states[int(column)] = direction
        self.viewport().update()

    def _filter_rect(self, section_rect):
        size = 18
        left = section_rect.left() + 4
        top = section_rect.top() + max(4, (section_rect.height() - size) // 2)
        return QRect(left, top, size, size)

    def _sort_rect(self, section_rect):
        return QRect(
            section_rect.left() + 24, section_rect.top(), 18, section_rect.height()
        )

    def paintSection(self, painter, rect, logicalIndex):
        super().paintSection(painter, rect, logicalIndex)
        if not rect.isValid():
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon_color = QColor(COLORS.get("text_secondary", "#94A3B8"))
        active_color = QColor(COLORS.get("primary", "#2563EB"))

        if logicalIndex in self.filter_columns:
            filter_rect = self._filter_rect(rect)
            painter.setPen(QPen(icon_color, 1.4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(filter_rect, 5, 5)
            funnel = QPolygon(
                [
                    QPoint(filter_rect.left() + 5, filter_rect.top() + 5),
                    QPoint(filter_rect.right() - 5, filter_rect.top() + 5),
                    QPoint(filter_rect.center().x() + 2, filter_rect.center().y()),
                    QPoint(filter_rect.center().x() + 2, filter_rect.bottom() - 4),
                    QPoint(filter_rect.center().x() - 2, filter_rect.bottom() - 4),
                    QPoint(filter_rect.center().x() - 2, filter_rect.center().y()),
                ]
            )
            painter.drawPolyline(funnel)

        if logicalIndex in self.sortable_columns:
            direction = self.sort_states.get(logicalIndex)
            painter.setPen(active_color if direction else icon_color)
            arrow = "↑" if direction == "asc" else "↓" if direction == "desc" else "↕"
            painter.drawText(self._sort_rect(rect), Qt.AlignmentFlag.AlignCenter, arrow)
        painter.restore()

    def mousePressEvent(self, event):
        column = self.logicalIndexAt(event.position().toPoint())
        if column >= 0:
            rect = QRect(
                self.sectionViewportPosition(column),
                0,
                self.sectionSize(column),
                self.height(),
            )
            if column in self.filter_columns and self._filter_rect(rect).contains(
                event.position().toPoint()
            ):
                self.filterClicked.emit(column)
                return
            if column in self.sortable_columns:
                self.sortClicked.emit(column)
                return
        super().mousePressEvent(event)


class ProductDialog(QDialog):
    """نافذة إضافة/تعديل منتج"""

    def __init__(self, ctrl, parent=None, product=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.product = product
        self.selected_image_path = ""
        self.current_image_path = getattr(product, "image_path", "") if product else ""
        self.setWindowTitle("تعديل منتج" if product else "إضافة منتج جديد")
        style_dialog(self, min_width=520)

        self.init_ui()

    def init_ui(self):
        _, content_layout, footer_layout = scrollable_dialog_layout(self)
        layout = QFormLayout()
        configure_form_layout(layout)

        # Inputs
        self.code_input = QLineEdit()
        self.barcode_input = QLineEdit()
        self.name_input = QLineEdit()
        self.category_combo = QComboBox()
        self.supplier_combo = QComboBox()
        self.unit_combo = QComboBox()
        self.buy_price_input = QDoubleSpinBox()
        self.sell_price_input = QDoubleSpinBox()
        self.tax_input = QDoubleSpinBox()
        self.stock_input = QSpinBox()
        self.image_preview = QLabel("لا توجد صورة")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setFixedSize(150, 115)
        self.image_preview.setStyleSheet(
            f"background: {COLORS['bg_input']}; color: {COLORS['text_secondary']}; "
            f"border: 1px dashed {COLORS['border']}; border-radius: 10px;"
        )
        image_btn = QPushButton("اختيار صورة")
        image_btn.setStyleSheet(get_button_style("info"))
        image_btn.clicked.connect(self._choose_image)
        clear_image_btn = QPushButton("إزالة")
        clear_image_btn.setStyleSheet(get_button_style("secondary"))
        clear_image_btn.clicked.connect(self._clear_image)
        image_layout = QHBoxLayout()
        image_layout.addWidget(self.image_preview)
        image_actions = QVBoxLayout()
        image_actions.addWidget(image_btn)
        image_actions.addWidget(clear_image_btn)
        image_actions.addStretch()
        image_layout.addLayout(image_actions)

        # Configure Numerics
        for spin in (self.buy_price_input, self.sell_price_input):
            spin.setMaximum(999999)
            spin.setDecimals(2)
        self.tax_input.setMaximum(100)
        self.tax_input.setDecimals(2)
        self.stock_input.setMaximum(99999)
        if self.product:
            self.stock_input.setEnabled(False)  # Stock changes via inventory

        # Load Categories
        categories = self.ctrl.get_categories()
        for cat in categories:
            self.category_combo.addItem(cat["category_name"], cat["id"])

        self.supplier_combo.addItem("بدون مورد", None)
        for supplier in self.ctrl.get_suppliers():
            self.supplier_combo.addItem(supplier["name"], supplier["id"])

        self.unit_combo.setEditable(True)
        self.unit_combo.addItems(
            ["قطعة", "علبة", "كرتونة", "كجم", "جرام", "لتر", "متر"]
        )

        style_form_controls(
            self.code_input,
            self.barcode_input,
            self.name_input,
            self.category_combo,
            self.supplier_combo,
            self.unit_combo,
            self.buy_price_input,
            self.sell_price_input,
            self.tax_input,
            self.stock_input,
        )

        # Add to form
        layout.addRow("الكود:", self.code_input)
        layout.addRow("الباركود:", self.barcode_input)
        layout.addRow("الاسم:", self.name_input)
        layout.addRow("الفئة:", self.category_combo)
        layout.addRow("المورد:", self.supplier_combo)
        layout.addRow("الوحدة:", self.unit_combo)
        layout.addRow("سعر الشراء:", self.buy_price_input)
        layout.addRow("سعر البيع:", self.sell_price_input)
        layout.addRow("الضريبة %:", self.tax_input)
        layout.addRow("المخزون الافتتاحي:", self.stock_input)
        layout.addRow("صورة المنتج:", image_layout)

        # Populate if editing
        if self.product:
            self.code_input.setText(self.product.product_code)
            self.barcode_input.setText(
                self.product.barcode or self.product.product_code
            )
            self.name_input.setText(self.product.product_name)
            self.buy_price_input.setValue(self.product.buy_price)
            self.sell_price_input.setValue(self.product.sell_price)
            self.tax_input.setValue(self.product.tax_percent)
            idx = self.category_combo.findData(self.product.category_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            supplier_idx = self.supplier_combo.findData(self.product.supplier_id)
            if supplier_idx >= 0:
                self.supplier_combo.setCurrentIndex(supplier_idx)
            unit_idx = self.unit_combo.findText(self.product.unit)
            if unit_idx >= 0:
                self.unit_combo.setCurrentIndex(unit_idx)
            else:
                self.unit_combo.setEditText(self.product.unit)
            self._update_image_preview(self.current_image_path)

        btn_layout, save_btn, cancel_btn = action_row()
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        content_layout.addLayout(layout)
        footer_layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "product_code": self.code_input.text().strip(),
            "barcode": self.barcode_input.text().strip()
            or self.code_input.text().strip(),
            "product_name": self.name_input.text().strip(),
            "category_id": self.category_combo.currentData(),
            "supplier_id": self.supplier_combo.currentData(),
            "unit": self.unit_combo.currentText().strip() or "قطعة",
            "buy_price": self.buy_price_input.value(),
            "sell_price": self.sell_price_input.value(),
            "tax_percent": self.tax_input.value(),
            "initial_stock": self.stock_input.value(),
            "image_source": self.selected_image_path,
            "image_path": self.current_image_path,
        }

    def accept(self):
        if not self.code_input.text().strip():
            QMessageBox.warning(self, "تنبيه", "كود المنتج مطلوب")
            self.code_input.setFocus()
            return
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "تنبيه", "اسم المنتج مطلوب")
            self.name_input.setFocus()
            return
        if self.sell_price_input.value() < self.buy_price_input.value():
            QMessageBox.warning(self, "تنبيه", "سعر البيع أقل من سعر الشراء")
            self.sell_price_input.setFocus()
            return
        super().accept()

    def _choose_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختيار صورة المنتج",
            "",
            "Images (*.png *.jpg *.jpeg *.webp);;All Files (*.*)",
        )
        if file_path:
            self.selected_image_path = file_path
            self.current_image_path = file_path
            self._update_image_preview(file_path)

    def _clear_image(self):
        self.selected_image_path = ""
        self.current_image_path = ""
        self.image_preview.setPixmap(QPixmap())
        self.image_preview.setText("لا توجد صورة")

    def _update_image_preview(self, image_path):
        if not image_path or not os.path.exists(image_path):
            self.image_preview.setPixmap(QPixmap())
            self.image_preview.setText("لا توجد صورة")
            return
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.image_preview.setText("تعذر عرض الصورة")
            return
        self.image_preview.setText("")
        self.image_preview.setPixmap(
            pixmap.scaled(
                self.image_preview.width() - 8,
                self.image_preview.height() - 8,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class ProductImportPreviewDialog(QDialog):
    def __init__(self, preview: dict, parent=None):
        super().__init__(parent)
        self.preview = preview
        self.max_preview_rows = 1000
        self.setWindowTitle("مراجعة استيراد المنتجات")
        style_dialog(self, min_width=980)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        summary = QLabel(
            f"تمت قراءة {self.preview.get('processed', 0)} صف | "
            f"جاهز: {self.preview.get('ready', 0)} | "
            f"بدون سعر: {self.preview.get('needs_pricing', 0)} | "
            f"بدون تكلفة: {self.preview.get('needs_cost', 0)} | "
            f"مرفوض: {self.preview.get('blocked', 0)}"
        )
        summary.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: 900; font-size: 13px;"
        )
        layout.addWidget(summary)

        info = QLabel(
            "المنتجات بدون كود أخذت كودًا رقميًا فقط. المنتجات بدون سعر ستدخل كغير جاهزة للبيع."
        )
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        layout.addWidget(info)
        if len(self.preview.get("rows", [])) > self.max_preview_rows:
            limited = QLabel(
                f"سيتم عرض أول {self.max_preview_rows} صف فقط لتسريع الواجهة، وسيتم استيراد كل الصفوف."
            )
            limited.setStyleSheet(f"color: {COLORS['warning']}; font-weight: 800;")
            layout.addWidget(limited)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["الصف", "الكود", "الاسم", "التكلفة", "سعر البيع", "الحالة", "ملاحظات"]
        )
        configure_table(self.table, PRODUCT_TABLE_STYLE, row_height=38)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)
        self._load_rows()

        self.include_incomplete = QCheckBox("استيراد المنتجات الناقصة وحفظها للمراجعة")
        self.include_incomplete.setChecked(True)
        self.include_incomplete.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: 700;"
        )
        layout.addWidget(self.include_incomplete)

        btns = QHBoxLayout()
        btns.addStretch()
        save_btn = QPushButton("استيراد")
        save_btn.setStyleSheet(get_button_style("success"))
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet(get_button_style("outline"))
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _load_rows(self):
        rows = self.preview.get("rows", [])[: self.max_preview_rows]
        self.table.setRowCount(len(rows))
        status_labels = {
            "ready": "جاهز",
            "needs_pricing": "ناقص سعر",
            "needs_cost": "ناقص تكلفة",
            "duplicate": "مكرر",
            "invalid": "غير صالح",
        }
        for row_index, row in enumerate(rows):
            values = [
                row.get("row_number", ""),
                row.get("product_code", ""),
                row.get("product_name", ""),
                f"{float(row.get('buy_price') or 0):,.2f}",
                f"{float(row.get('sell_price') or 0):,.2f}",
                status_labels.get(
                    row.get("import_status"), row.get("import_status", "")
                ),
                row.get("import_notes", ""),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, center_item(value))

    def get_rows(self):
        return self.preview.get("rows", [])

    def should_include_incomplete(self):
        return self.include_incomplete.isChecked()


class ProductView(QWidget):
    """واجهة إدارة المنتجات والمخزون"""

    def __init__(self, ctrl, user_info, transfers_ctrl=None):
        super().__init__()
        self.ctrl = ctrl
        self.user_info = user_info
        self.transfers_ctrl = transfers_ctrl or TransfersController()

        # Pagination state
        self.current_page = 1
        self.per_page = 50
        self.inventory_page = 1
        self.inventory_per_page = 100
        self.inventory_total = 0
        self.product_sort_column = None
        self.product_sort_direction = None
        self.inventory_sort_column = None
        self.inventory_sort_direction = None

        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)

        products_tab = QWidget()
        product_layout = QVBoxLayout(products_tab)
        product_layout.setContentsMargins(0, 0, 0, 0)
        product_layout.setSpacing(10)

        # Header section (Search and Actions)
        header_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 ابحث برقم الكود أو اسم المنتج...")
        self.search_input.setStyleSheet(INPUT_STYLE)
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input, stretch=2)

        policy = PermissionPolicy(self.user_info)
        can_edit = policy.can_edit_products()
        can_view_buy = policy.can_view_buy_price()

        if can_edit:
            add_btn = QPushButton("➕ منتج جديد")
            add_btn.setStyleSheet(get_button_style("success"))
            add_btn.clicked.connect(self._on_add_product)
            header_layout.addWidget(add_btn)

            import_btn = QPushButton("📥 استيراد Excel")
            import_btn.setStyleSheet(get_button_style("info"))
            import_btn.clicked.connect(self._import_from_excel)
            header_layout.addWidget(import_btn)

            if can_view_buy:
                fix_costs_btn = QPushButton("🛠️ تصحيح التكاليف")
                fix_costs_btn.setStyleSheet(get_button_style("warning"))
                fix_costs_btn.setToolTip(
                    "تصحيح المنتجات التي سعر شرائها صفر باستخدام هامش ربح افتراضي"
                )
                fix_costs_btn.clicked.connect(self._fix_zero_costs)
                header_layout.addWidget(fix_costs_btn)

        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setStyleSheet(get_button_style("secondary"))
        refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(refresh_btn)

        product_layout.addLayout(header_layout)

        filters_layout = QHBoxLayout()
        filters_layout.addWidget(QLabel("الفئة:"))
        self.product_category_filter = QComboBox()
        self.product_category_filter.setStyleSheet(INPUT_STYLE)
        self.product_category_filter.currentIndexChanged.connect(
            self._on_product_filter_changed
        )
        filters_layout.addWidget(self.product_category_filter)

        filters_layout.addWidget(QLabel("المورد:"))
        self.product_supplier_filter = QComboBox()
        self.product_supplier_filter.setStyleSheet(INPUT_STYLE)
        self.product_supplier_filter.currentIndexChanged.connect(
            self._on_product_filter_changed
        )
        filters_layout.addWidget(self.product_supplier_filter)

        reset_filters_btn = QPushButton("إعادة ضبط")
        reset_filters_btn.setStyleSheet(get_button_style("outline"))
        reset_filters_btn.clicked.connect(self._reset_product_filters)
        filters_layout.addWidget(reset_filters_btn)
        filters_layout.addStretch()
        product_layout.addLayout(filters_layout)
        self._load_product_filters()

        # Table
        self.product_code_filter = QLineEdit()
        self.product_code_filter.setPlaceholderText("فلتر الكود")
        self.product_name_filter = QLineEdit()
        self.product_name_filter.setPlaceholderText("فلتر الاسم")
        self.product_unit_filter = QLineEdit()
        self.product_unit_filter.setPlaceholderText("الوحدة")
        self.product_min_buy_filter = QDoubleSpinBox()
        self.product_min_buy_filter.setRange(0, 999999)
        self.product_min_buy_filter.setDecimals(2)
        self.product_min_buy_filter.setSpecialValueText("من تكلفة")
        self.product_max_buy_filter = QDoubleSpinBox()
        self.product_max_buy_filter.setRange(0, 999999)
        self.product_max_buy_filter.setDecimals(2)
        self.product_max_buy_filter.setSpecialValueText("إلى تكلفة")
        self.product_min_sell_filter = QDoubleSpinBox()
        self.product_min_sell_filter.setRange(0, 999999)
        self.product_min_sell_filter.setDecimals(2)
        self.product_min_sell_filter.setSpecialValueText("من سعر")
        self.product_max_sell_filter = QDoubleSpinBox()
        self.product_max_sell_filter.setRange(0, 999999)
        self.product_max_sell_filter.setDecimals(2)
        self.product_max_sell_filter.setSpecialValueText("إلى سعر")
        self.product_status_filter = QComboBox()
        self.product_status_filter.addItem("كل الحالات", "")
        self.product_status_filter.addItem("جاهز", "ready")
        self.product_status_filter.addItem("ناقص سعر", "needs_pricing")
        self.product_status_filter.addItem("ناقص تكلفة", "needs_cost")
        for widget_filter in (
            self.product_code_filter,
            self.product_name_filter,
            self.product_unit_filter,
            self.product_min_buy_filter,
            self.product_max_buy_filter,
            self.product_min_sell_filter,
            self.product_max_sell_filter,
            self.product_status_filter,
        ):
            widget_filter.setStyleSheet(INPUT_STYLE)
        self.product_code_filter.textChanged.connect(self._on_product_filter_changed)
        self.product_name_filter.textChanged.connect(self._on_product_filter_changed)
        self.product_unit_filter.textChanged.connect(self._on_product_filter_changed)
        self.product_min_buy_filter.valueChanged.connect(
            self._on_product_filter_changed
        )
        self.product_max_buy_filter.valueChanged.connect(
            self._on_product_filter_changed
        )
        self.product_min_sell_filter.valueChanged.connect(
            self._on_product_filter_changed
        )
        self.product_max_sell_filter.valueChanged.connect(
            self._on_product_filter_changed
        )
        self.product_status_filter.currentIndexChanged.connect(
            self._on_product_filter_changed
        )
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "الكود",
                "اسم المنتج",
                "سعر الشراء",
                "سعر البيع",
                "الوحدة",
                "الحالة",
                "إجراءات",
            ]
        )
        product_header = FilterSortHeader(
            Qt.Orientation.Horizontal,
            self.table,
            filter_columns={0, 1, 2, 3, 4, 5},
            sortable_columns={3},
        )
        product_header.filterClicked.connect(self._open_product_header_filter)
        product_header.sortClicked.connect(self._toggle_product_sort)
        self.table.setHorizontalHeader(product_header)
        self._configure_table(self.table)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 150)

        product_layout.addWidget(self.table)

        # Pagination controls
        page_layout = QHBoxLayout()
        page_layout.setDirection(QHBoxLayout.Direction.LeftToRight)
        page_layout.addStretch()

        self.prev_btn = QPushButton("◀ السابق")
        self.prev_btn.setStyleSheet(get_button_style("secondary"))
        self.prev_btn.clicked.connect(self._prev_page)

        self.page_label = QLabel("صفحة 1")
        self.page_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: bold;"
        )

        self.next_btn = QPushButton("التالي ▶")
        self.next_btn.setStyleSheet(get_button_style("secondary"))
        self.next_btn.clicked.connect(self._next_page)

        page_layout.addWidget(self.prev_btn)
        page_layout.addWidget(self.page_label)
        page_layout.addWidget(self.next_btn)
        page_layout.addStretch()

        product_layout.addLayout(page_layout)

        self.tabs.addTab(products_tab, "المنتجات")
        self.tabs.addTab(self._create_inventory_tab(), "المخزون")
        if policy.can_transfer_inventory():
            self.tabs.addTab(
                TransfersView(self.transfers_ctrl, self.user_info), "إدارة التحويلات"
            )
        if can_edit:
            self.tabs.addTab(self._create_categories_tab(), "إدارة الفئات")
        self.tabs.addTab(self._create_barcode_tab(), "طباعة الباركود")
        layout.addWidget(create_subtab_dropdown(self.tabs, "اختر قسم المنتجات"))
        layout.addWidget(self.tabs)

    def _load_product_filters(self):
        self.product_category_filter.blockSignals(True)
        self.product_supplier_filter.blockSignals(True)

        current_category = self.product_category_filter.currentData()
        current_supplier = self.product_supplier_filter.currentData()

        self.product_category_filter.clear()
        self.product_category_filter.addItem("كل الفئات", None)
        for category in self.ctrl.get_categories():
            self.product_category_filter.addItem(
                category["category_name"], category["id"]
            )

        self.product_supplier_filter.clear()
        self.product_supplier_filter.addItem("كل الموردين", None)
        for supplier in self.ctrl.get_suppliers():
            self.product_supplier_filter.addItem(supplier["name"], supplier["id"])

        if current_category:
            idx = self.product_category_filter.findData(current_category)
            if idx >= 0:
                self.product_category_filter.setCurrentIndex(idx)
        if current_supplier:
            idx = self.product_supplier_filter.findData(current_supplier)
            if idx >= 0:
                self.product_supplier_filter.setCurrentIndex(idx)

        self.product_category_filter.blockSignals(False)
        self.product_supplier_filter.blockSignals(False)

    def _configure_table(self, table):
        configure_table(table, PRODUCT_TABLE_STYLE)

    def _get_store_id(self):
        if isinstance(self.user_info, dict):
            return self.user_info.get("store_id")
        return getattr(self.user_info, "store_id", None)

    def _get_role_id(self):
        if isinstance(self.user_info, dict):
            return self.user_info.get("role_id")
        return getattr(self.user_info, "role_id", None)

    def _get_user_id(self):
        if isinstance(self.user_info, dict):
            return self.user_info.get("id", 1)
        return getattr(self.user_info, "id", 1)

    def _product_column_filters(self):
        if not hasattr(self, "product_code_filter"):
            return {}
        min_buy = self.product_min_buy_filter.value()
        max_buy = self.product_max_buy_filter.value()
        min_sell = self.product_min_sell_filter.value()
        max_sell = self.product_max_sell_filter.value()
        return {
            "code": self.product_code_filter.text().strip(),
            "name": self.product_name_filter.text().strip(),
            "unit": self.product_unit_filter.text().strip(),
            "status": self.product_status_filter.currentData() or "",
            "min_buy": min_buy if min_buy > 0 else None,
            "max_buy": max_buy if max_buy > 0 else None,
            "min_sell": min_sell if min_sell > 0 else None,
            "max_sell": max_sell if max_sell > 0 else None,
            "sort_by": self.product_sort_column,
            "sort_direction": self.product_sort_direction,
        }

    def _setup_product_filter_row(self):
        if not hasattr(self, "table") or not hasattr(self, "product_code_filter"):
            return
        self.table.setRowHeight(0, 58)
        self.table.setCellWidget(0, 0, self.product_code_filter)
        self.table.setCellWidget(0, 1, self.product_name_filter)
        self.table.setCellWidget(0, 2, self.product_min_sell_filter)
        self.table.setCellWidget(0, 3, self.product_max_sell_filter)
        self.table.setCellWidget(0, 4, self.product_unit_filter)
        self.table.setCellWidget(0, 5, self.product_status_filter)
        clear_btn = getattr(self, "product_clear_filter_btn", None)
        if clear_btn is None:
            clear_btn = QPushButton("مسح")
            clear_btn.setStyleSheet(get_button_style("outline"))
            clear_btn.clicked.connect(self._reset_product_filters)
            self.product_clear_filter_btn = clear_btn
        self.table.setCellWidget(0, 6, actions_cell([clear_btn]))

    def _toggle_sort_state(self, current_column, current_direction, requested_column):
        if current_column != requested_column:
            return requested_column, "asc"
        if current_direction == "asc":
            return requested_column, "desc"
        if current_direction == "desc":
            return None, None
        return requested_column, "asc"

    def _toggle_product_sort(self, column):
        if column != 3:
            return
        self.product_sort_column, self.product_sort_direction = self._toggle_sort_state(
            self.product_sort_column,
            self.product_sort_direction,
            "sell_price",
        )
        header = self.table.horizontalHeader()
        if isinstance(header, FilterSortHeader):
            header.set_sort_state(
                3 if self.product_sort_column else None, self.product_sort_direction
            )
        self.current_page = 1
        self.load_data()

    def _toggle_inventory_sort(self, column):
        sort_key = {3: "quantity", 5: "sell_price"}.get(column)
        if not sort_key:
            return
        self.inventory_sort_column, self.inventory_sort_direction = (
            self._toggle_sort_state(
                self.inventory_sort_column,
                self.inventory_sort_direction,
                sort_key,
            )
        )
        active_column = None
        if self.inventory_sort_column == "quantity":
            active_column = 3
        elif self.inventory_sort_column == "sell_price":
            active_column = 5
        header = self.inventory_table.horizontalHeader()
        if isinstance(header, FilterSortHeader):
            header.set_sort_state(active_column, self.inventory_sort_direction)
        self._reset_inventory_page()

    def _set_text_filter(self, title, widget):
        value, ok = QInputDialog.getText(self, title, title, text=widget.text())
        if ok:
            widget.setText(value.strip())

    def _set_combo_filter(self, title, combo):
        labels = [combo.itemText(i) for i in range(combo.count())]
        current = combo.currentText()
        value, ok = QInputDialog.getItem(
            self, title, title, labels, combo.currentIndex(), False
        )
        if ok:
            index = combo.findText(value)
            if index >= 0:
                combo.setCurrentIndex(index)

    def _set_number_filter(self, title, spin, suffix=""):
        decimals = spin.decimals() if hasattr(spin, "decimals") else 0
        value, ok = QInputDialog.getDouble(
            self,
            title,
            title,
            spin.value(),
            spin.minimum(),
            spin.maximum(),
            decimals,
        )
        if ok:
            spin.setValue(value if decimals else int(value))

    def _set_price_range_filter(self, title, min_spin, max_spin):
        min_value, ok = QInputDialog.getDouble(
            self, f"{title} - من", "من:", min_spin.value(), 0, 999999, 2
        )
        if not ok:
            return
        max_value, ok = QInputDialog.getDouble(
            self, f"{title} - إلى", "إلى:", max_spin.value(), 0, 999999, 2
        )
        if not ok:
            return
        min_spin.blockSignals(True)
        max_spin.blockSignals(True)
        min_spin.setValue(min_value)
        max_spin.setValue(max_value)
        min_spin.blockSignals(False)
        max_spin.blockSignals(False)
        self.current_page = 1
        self.load_data()

    def _open_product_header_filter(self, column):
        if column == 0:
            self._set_text_filter("فلتر الكود / الباركود", self.product_code_filter)
        elif column == 1:
            self._set_text_filter("فلتر اسم المنتج", self.product_name_filter)
        elif column == 2:
            self._set_price_range_filter(
                "فلتر سعر الشراء",
                self.product_min_buy_filter,
                self.product_max_buy_filter,
            )
        elif column == 3:
            self._set_price_range_filter(
                "فلتر سعر البيع",
                self.product_min_sell_filter,
                self.product_max_sell_filter,
            )
        elif column == 4:
            self._set_text_filter("فلتر الوحدة", self.product_unit_filter)
        elif column == 5:
            self._set_combo_filter("فلتر الحالة", self.product_status_filter)

    def _open_inventory_header_filter(self, column):
        if column == 0:
            self._set_text_filter("فلتر الكود / الباركود", self.inventory_code_filter)
        elif column == 1:
            self._set_text_filter("فلتر اسم المنتج", self.inventory_name_filter)
        elif column == 2:
            self._set_combo_filter("فلتر الفرع", self.inventory_header_store_filter)
        elif column == 3:
            self._set_number_filter("كمية من", self.inventory_min_qty_filter)
        elif column == 5:
            self._set_number_filter("سعر حتى", self.inventory_max_price_filter)

    def _create_inventory_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("الفرع:"))
        self.inventory_store_filter = QComboBox()
        self.inventory_store_filter.setStyleSheet(INPUT_STYLE)
        self.inventory_store_filter.currentIndexChanged.connect(
            self._reset_inventory_page
        )
        filters.addWidget(self.inventory_store_filter)

        self.inventory_search_input = QLineEdit()
        self.inventory_search_input.setPlaceholderText(
            "🔍 بحث في المخزون بالاسم أو الكود..."
        )
        self.inventory_search_input.setStyleSheet(INPUT_STYLE)
        self.inventory_search_input.textChanged.connect(self._reset_inventory_page)
        filters.addWidget(self.inventory_search_input, stretch=2)
        self.inv_low_stock = QCheckBox("الأصناف تحت حد الأمان فقط")
        self.inv_low_stock.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: 600;"
        )
        self.inv_low_stock.stateChanged.connect(self._reset_inventory_page)
        filters.addWidget(self.inv_low_stock)
        refresh_btn = QPushButton("تحديث")
        refresh_btn.setStyleSheet(get_button_style("outline"))
        refresh_btn.clicked.connect(self._load_inventory)
        filters.addWidget(refresh_btn)
        filters.addStretch()
        layout.addLayout(filters)

        filter_bar = QFrame(w)
        self.inventory_filter_bar = filter_bar
        filter_bar.setObjectName("InventoryHeaderFilters")
        filter_bar.setStyleSheet(f"""
            QFrame#InventoryHeaderFilters {{
                background: {COLORS['bg_panel']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 6px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(8, 8, 8, 8)
        filter_layout.setSpacing(8)

        self.inventory_code_filter = QLineEdit()
        self.inventory_code_filter.setPlaceholderText("فلتر الكود / الباركود")
        self.inventory_code_filter.setStyleSheet(INPUT_STYLE)
        self.inventory_code_filter.textChanged.connect(self._reset_inventory_page)
        filter_layout.addWidget(self.inventory_code_filter, 2)

        self.inventory_name_filter = QLineEdit()
        self.inventory_name_filter.setPlaceholderText("فلتر اسم المنتج")
        self.inventory_name_filter.setStyleSheet(INPUT_STYLE)
        self.inventory_name_filter.textChanged.connect(self._reset_inventory_page)
        filter_layout.addWidget(self.inventory_name_filter, 3)

        self.inventory_header_store_filter = QComboBox()
        self.inventory_header_store_filter.setStyleSheet(INPUT_STYLE)
        self.inventory_header_store_filter.currentIndexChanged.connect(
            self._reset_inventory_page
        )
        filter_layout.addWidget(self.inventory_header_store_filter, 2)

        self.inventory_stock_status_filter = QComboBox()
        self.inventory_stock_status_filter.addItem("كل الحالات", "")
        self.inventory_stock_status_filter.addItem("متوفر", "available")
        self.inventory_stock_status_filter.addItem("تحت حد الأمان", "low")
        self.inventory_stock_status_filter.addItem("نفد المخزون", "out")
        self.inventory_stock_status_filter.setStyleSheet(INPUT_STYLE)
        self.inventory_stock_status_filter.currentIndexChanged.connect(
            self._reset_inventory_page
        )
        filter_layout.addWidget(self.inventory_stock_status_filter, 2)

        self.inventory_min_qty_filter = QSpinBox()
        self.inventory_min_qty_filter.setRange(0, 999999)
        self.inventory_min_qty_filter.setSpecialValueText("كمية من")
        self.inventory_min_qty_filter.setStyleSheet(INPUT_STYLE)
        self.inventory_min_qty_filter.valueChanged.connect(self._reset_inventory_page)
        filter_layout.addWidget(self.inventory_min_qty_filter, 1)

        self.inventory_max_price_filter = QDoubleSpinBox()
        self.inventory_max_price_filter.setRange(0, 1000000)
        self.inventory_max_price_filter.setDecimals(2)
        self.inventory_max_price_filter.setSpecialValueText("سعر حتى")
        self.inventory_max_price_filter.setStyleSheet(INPUT_STYLE)
        self.inventory_max_price_filter.valueChanged.connect(self._reset_inventory_page)
        filter_layout.addWidget(self.inventory_max_price_filter, 1)

        clear_inventory_filters = QPushButton("مسح الفلاتر")
        clear_inventory_filters.setStyleSheet(get_button_style("outline"))
        clear_inventory_filters.clicked.connect(self._clear_inventory_header_filters)
        filter_layout.addWidget(clear_inventory_filters)
        layout.addWidget(filter_bar)
        filter_bar.hide()

        self.inventory_table = QTableWidget(0, 7)
        self.inventory_table.setHorizontalHeaderLabels(
            ["الكود", "المنتج", "الفرع", "الكمية", "حد الأمان", "سعر البيع", "إجراءات"]
        )
        inventory_header = FilterSortHeader(
            Qt.Orientation.Horizontal,
            self.inventory_table,
            filter_columns={0, 1, 2, 3, 5},
            sortable_columns={3, 5},
        )
        inventory_header.filterClicked.connect(self._open_inventory_header_filter)
        inventory_header.sortClicked.connect(self._toggle_inventory_sort)
        self.inventory_table.setHorizontalHeader(inventory_header)
        self._configure_table(self.inventory_table)
        self.inventory_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.inventory_table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.Fixed
        )
        self.inventory_table.setColumnWidth(6, 230)
        layout.addWidget(self.inventory_table)

        inventory_page_layout = QHBoxLayout()
        inventory_page_layout.setDirection(QHBoxLayout.Direction.LeftToRight)
        inventory_page_layout.addStretch()
        self.inventory_prev_btn = QPushButton("◀ السابق")
        self.inventory_prev_btn.setStyleSheet(get_button_style("outline"))
        self.inventory_prev_btn.clicked.connect(self._prev_inventory_page)
        self.inventory_page_label = QLabel("صفحة 1")
        self.inventory_page_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: 900;"
        )
        self.inventory_next_btn = QPushButton("التالي ▶")
        self.inventory_next_btn.setStyleSheet(get_button_style("primary"))
        self.inventory_next_btn.clicked.connect(self._next_inventory_page)
        inventory_page_layout.addWidget(self.inventory_prev_btn)
        inventory_page_layout.addWidget(self.inventory_page_label)
        inventory_page_layout.addWidget(self.inventory_next_btn)
        inventory_page_layout.addStretch()
        layout.addLayout(inventory_page_layout)

        self._load_inventory_stores()
        self._load_inventory()
        return w

    def _load_inventory_stores(self):
        if not hasattr(self, "inventory_store_filter"):
            return

        user_store_id = self._get_store_id()
        can_view_all = PermissionPolicy(self.user_info).can_view_all_inventory()

        self.inventory_store_filter.blockSignals(True)
        self.inventory_store_filter.clear()
        if can_view_all:
            self.inventory_store_filter.addItem("كل الفروع", None)

        for store in self.transfers_ctrl.get_stores():
            store_id = store.get("id")
            if not can_view_all and store_id != user_store_id:
                continue
            label = f"{store.get('store_name', '')} ({store.get('store_type', '')})"
            self.inventory_store_filter.addItem(label, store_id)

        if not can_view_all:
            index = self.inventory_store_filter.findData(user_store_id)
            if index >= 0:
                self.inventory_store_filter.setCurrentIndex(index)

        self.inventory_store_filter.blockSignals(False)
        if hasattr(self, "inventory_header_store_filter"):
            self.inventory_header_store_filter.blockSignals(True)
            self.inventory_header_store_filter.clear()
            for index in range(self.inventory_store_filter.count()):
                self.inventory_header_store_filter.addItem(
                    self.inventory_store_filter.itemText(index),
                    self.inventory_store_filter.itemData(index),
                )
            if not can_view_all:
                index = self.inventory_header_store_filter.findData(user_store_id)
                if index >= 0:
                    self.inventory_header_store_filter.setCurrentIndex(index)
            self.inventory_header_store_filter.blockSignals(False)

    def _inventory_column_filters(self):
        if not hasattr(self, "inventory_code_filter"):
            return {}
        min_qty = self.inventory_min_qty_filter.value()
        max_price = self.inventory_max_price_filter.value()
        return {
            "code": self.inventory_code_filter.text().strip(),
            "name": self.inventory_name_filter.text().strip(),
            "stock_status": self.inventory_stock_status_filter.currentData() or "",
            "min_qty": min_qty if min_qty > 0 else None,
            "max_price": max_price if max_price > 0 else None,
            "sort_by": self.inventory_sort_column,
            "sort_direction": self.inventory_sort_direction,
        }

    def _clear_inventory_header_filters(self):
        if not hasattr(self, "inventory_code_filter"):
            return
        widgets = [
            self.inventory_code_filter,
            self.inventory_name_filter,
        ]
        for widget in widgets:
            widget.blockSignals(True)
            widget.clear()
            widget.blockSignals(False)
        for combo in (
            self.inventory_stock_status_filter,
            self.inventory_header_store_filter,
        ):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        for spin in (self.inventory_min_qty_filter, self.inventory_max_price_filter):
            spin.blockSignals(True)
            spin.setValue(0)
            spin.blockSignals(False)
        self.inventory_sort_column = None
        self.inventory_sort_direction = None
        if hasattr(self, "inventory_table") and isinstance(
            self.inventory_table.horizontalHeader(), FilterSortHeader
        ):
            self.inventory_table.horizontalHeader().set_sort_state(None, None)
        self._reset_inventory_page()

    def _load_inventory(self, *_args):
        if not hasattr(self, "inventory_table"):
            return
        store_id = (
            None
            if PermissionPolicy(self.user_info).can_view_all_inventory()
            else self._get_store_id()
        )
        if hasattr(self, "inventory_store_filter"):
            selected_store_id = self.inventory_store_filter.currentData()
            store_id = selected_store_id if selected_store_id else store_id
        if hasattr(self, "inventory_header_store_filter"):
            selected_store_id = self.inventory_header_store_filter.currentData()
            store_id = selected_store_id if selected_store_id else store_id
        search = self.inventory_search_input.text().strip()
        low_stock_only = self.inv_low_stock.isChecked()
        column_filters = self._inventory_column_filters()
        self.inventory_total = self.ctrl.get_inventory_count(
            store_id=store_id,
            low_stock_only=low_stock_only,
            search=search,
            filters=column_filters,
        )
        total_pages = max(
            1,
            (self.inventory_total + self.inventory_per_page - 1)
            // self.inventory_per_page,
        )
        if self.inventory_page > total_pages:
            self.inventory_page = total_pages
        rows = self.ctrl.get_inventory(
            store_id=store_id,
            low_stock_only=low_stock_only,
            page=self.inventory_page,
            per_page=self.inventory_per_page,
            search=search,
            filters=column_filters,
        )
        self.inventory_table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            product_id = item.get("id")
            item_store_id = item.get("store_id") or store_id
            current_qty = int(item.get("quantity_in_stock") or 0)
            min_qty = int(item.get("min_quantity", item.get("minimum_quantity", 0)) or 0)
            is_low = current_qty <= min_qty

            values = [
                item.get("product_code", ""),
                item.get("product_name", ""),
                item.get("store_name", ""),
                str(current_qty),
                str(min_qty),
                f"{float(item.get('sell_price', 0) or 0):,.2f}",
            ]
            for col, value in enumerate(values):
                table_item = center_item(value)
                if col == 3 and is_low:
                    table_item.setText(f"⚠️ {value} (منخفض)" if current_qty > 0 else f"🚨 {value} (نفد)")
                    table_item.setForeground(QColor("#dc2626"))
                if col == 0:
                    table_item.setData(
                        Qt.ItemDataRole.UserRole, (product_id, item_store_id)
                    )
                self.inventory_table.setItem(row_idx, col, table_item)

            edit_stock_btn = table_action_button(
                "تعديل",
                "warning",
                lambda checked=False, pid=product_id, sid=item_store_id, qty=current_qty: self._edit_inventory_stock(
                    pid, sid, qty
                ),
            )
            edit_stock_btn.setEnabled(
                bool(product_id and item_store_id)
                and PermissionPolicy(self.user_info).can_adjust_inventory()
            )
            transfer_btn = table_action_button(
                "تحويل",
                "info",
                lambda checked=False, pid=product_id, sid=item_store_id, qty=current_qty, name=item.get(
                    "product_name", ""
                ): self._transfer_inventory_stock(
                    pid, sid, qty, name
                ),
            )
            transfer_btn.setEnabled(
                bool(product_id and item_store_id)
                and PermissionPolicy(self.user_info).can_transfer_inventory()
            )
            self.inventory_table.setCellWidget(
                row_idx, 6, actions_cell([edit_stock_btn, transfer_btn])
            )
        self._update_inventory_pagination(total_pages)

    def _reset_inventory_page(self, *_args):
        self.inventory_page = 1
        self._load_inventory()

    def _update_inventory_pagination(self, total_pages: int):
        if not hasattr(self, "inventory_page_label"):
            return
        self.inventory_page_label.setText(
            f"صفحة {self.inventory_page} من {total_pages} - إجمالي {self.inventory_total:,} صف"
        )
        self.inventory_prev_btn.setEnabled(self.inventory_page > 1)
        self.inventory_next_btn.setEnabled(self.inventory_page < total_pages)

    def _prev_inventory_page(self):
        if self.inventory_page > 1:
            self.inventory_page -= 1
            self._load_inventory()

    def _next_inventory_page(self):
        self.inventory_page += 1
        self._load_inventory()

    def _edit_inventory_stock(self, product_id, store_id, current_qty):
        if not PermissionPolicy(self.user_info).can_adjust_inventory():
            QMessageBox.warning(
                self, "صلاحية مرفوضة", "لا تملك صلاحية تعديل المخزون يدويًا"
            )
            return
        if not product_id or not store_id:
            QMessageBox.warning(
                self, "تنبيه", "لا يمكن تعديل مخزون منتج غير مرتبط بفرع"
            )
            return

        quantity, ok = QInputDialog.getDouble(
            self,
            "تعديل المخزون",
            "الكمية الجديدة:",
            float(current_qty or 0),
            0.0,
            999999.0,
            3,
        )
        if not ok:
            return

        try:
            self.ctrl.update_stock(product_id, store_id, quantity, self._get_user_id())
            self._load_inventory()
            QMessageBox.information(self, "تم", "تم تحديث المخزون بنجاح")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر تحديث المخزون:\n{str(e)}")

    def _transfer_inventory_stock(
        self, product_id, from_store_id, current_qty, product_name
    ):
        if not PermissionPolicy(self.user_info).can_transfer_inventory():
            QMessageBox.warning(self, "صلاحية مرفوضة", "لا تملك صلاحية تحويل المخزون")
            return
        if not product_id or not from_store_id:
            QMessageBox.warning(self, "تنبيه", "لا يمكن تحويل منتج غير مرتبط بفرع")
            return
        if int(current_qty or 0) <= 0:
            QMessageBox.warning(
                self, "تنبيه", "لا توجد كمية متاحة للتحويل من هذا الفرع"
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("تحويل مخزون")
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet(
            f"background-color: {COLORS['bg_panel']}; color: {COLORS['text_primary']};"
        )

        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        form.setSpacing(10)

        product_label = QLabel(str(product_name or product_id))
        product_label.setStyleSheet(
            f"font-weight: 700; color: {COLORS['text_on_brand']};"
        )

        stores = self.transfers_ctrl.get_stores()
        from_store = next(
            (store for store in stores if store.get("id") == from_store_id), None
        )
        from_label = QLabel(
            from_store.get("store_name", str(from_store_id))
            if from_store
            else str(from_store_id)
        )

        to_store_combo = QComboBox()
        to_store_combo.setStyleSheet(INPUT_STYLE)
        for store in stores:
            if store.get("id") == from_store_id:
                continue
            label = f"{store.get('store_name', '')} ({store.get('store_type', '')})"
            to_store_combo.addItem(label, store.get("id"))

        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0.001, max(1.0, float(current_qty or 0)))
        qty_spin.setDecimals(3)
        qty_spin.setValue(1.0)
        qty_spin.setStyleSheet(INPUT_STYLE)

        notes_input = QLineEdit()
        notes_input.setPlaceholderText("ملاحظات اختيارية")
        notes_input.setStyleSheet(INPUT_STYLE)

        form.addRow("المنتج:", product_label)
        form.addRow("من فرع:", from_label)
        form.addRow("إلى فرع:", to_store_combo)
        form.addRow("الكمية المتاحة:", QLabel(str(current_qty)))
        form.addRow("كمية التحويل:", qty_spin)
        form.addRow("ملاحظات:", notes_input)
        layout.addLayout(form)

        actions = QHBoxLayout()
        save_btn = QPushButton("حفظ التحويل")
        save_btn.setStyleSheet(get_button_style("success"))
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet(get_button_style("outline"))
        cancel_btn.clicked.connect(dialog.reject)
        actions.addWidget(save_btn)
        actions.addWidget(cancel_btn)
        layout.addLayout(actions)

        if to_store_combo.count() == 0:
            QMessageBox.warning(self, "تنبيه", "لا توجد فروع أخرى متاحة للتحويل")
            return

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        ok, message = self.transfers_ctrl.create_transfer(
            product_id=product_id,
            from_store_id=from_store_id,
            to_store_id=to_store_combo.currentData(),
            quantity=qty_spin.value(),
            user_id=self._get_user_id(),
            notes=notes_input.text().strip(),
        )
        if ok:
            QMessageBox.information(self, "تم", message)
            self._load_inventory()
        else:
            QMessageBox.warning(self, "تعذر التحويل", message)

    def _create_categories_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        actions = QHBoxLayout()
        add_btn = QPushButton("➕ فئة جديدة")
        add_btn.setStyleSheet(get_button_style("success"))
        add_btn.clicked.connect(self._add_category)
        actions.addWidget(add_btn)
        refresh_btn = QPushButton("تحديث الفئات")
        refresh_btn.setStyleSheet(get_button_style("outline"))
        refresh_btn.clicked.connect(self._load_categories_table)
        actions.addWidget(refresh_btn)
        actions.addStretch()
        layout.addLayout(actions)

        self.categories_table = QTableWidget(0, 3)
        self.categories_table.setHorizontalHeaderLabels(["ID", "الفئة", "إجراءات"])
        self._configure_table(self.categories_table)
        self.categories_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.categories_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.categories_table)
        self._load_categories_table()
        return w

    def _load_categories_table(self):
        if not hasattr(self, "categories_table"):
            return
        categories = self.ctrl.get_categories()
        self.categories_table.setRowCount(len(categories))
        for row, cat in enumerate(categories):
            category_id = int(cat.get("id", 0) or 0)
            category_name = cat.get("category_name", "")
            set_center_item(self.categories_table, row, 0, category_id)
            set_center_item(self.categories_table, row, 1, category_name)

            edit_btn = table_action_button(
                "تعديل",
                "warning",
                lambda checked=False, cid=category_id, name=category_name: self._edit_category(
                    cid, name
                ),
            )
            delete_btn = table_action_button(
                "حذف",
                "danger",
                lambda checked=False, cid=category_id: self._delete_category(cid),
            )
            self.categories_table.setCellWidget(
                row, 2, actions_cell([edit_btn, delete_btn])
            )

    def _add_category(self):
        name, ok = QInputDialog.getText(self, "إضافة فئة", "اسم الفئة:")
        if not ok:
            return
        try:
            self.ctrl.add_category(name)
            self._load_categories_table()
            self._load_product_filters()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر إضافة الفئة:\n{str(e)}")

    def _edit_category(self, category_id, current_name):
        name, ok = QInputDialog.getText(
            self, "تعديل فئة", "اسم الفئة:", text=current_name
        )
        if not ok:
            return
        try:
            if self.ctrl.update_category(category_id, name):
                self._load_categories_table()
                self._load_product_filters()
            else:
                QMessageBox.warning(self, "خطأ", "لم يتم تعديل الفئة")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر تعديل الفئة:\n{str(e)}")

    def _delete_category(self, category_id):
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            "سيتم تعطيل الفئة فقط حتى لا تتأثر المنتجات المرتبطة بها. هل تريد المتابعة؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.ctrl.delete_category(category_id):
            self._load_categories_table()
            self._load_product_filters()
        else:
            QMessageBox.warning(self, "خطأ", "لم يتم حذف الفئة")

    def _create_barcode_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(16)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        manual_btn = QPushButton("📦 صنف جديد / مخصص")
        manual_btn.setStyleSheet(get_button_style("outline"))
        manual_btn.clicked.connect(self._open_manual_barcode_dialog)
        right_layout.addWidget(manual_btn)

        self._create_manual_barcode_dialog()

        existing_card = self._barcode_card("🔍 البحث في الأصناف الحالية")
        existing_layout = existing_card.layout()
        self.barcode_search_input = QLineEdit()
        self.barcode_search_input.setPlaceholderText("بحث بالحروف أو الكود...")
        self.barcode_search_input.setStyleSheet(INPUT_STYLE)
        self.barcode_search_input.textChanged.connect(self._load_barcode_products)
        existing_layout.addWidget(self.barcode_search_input)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("المورد:"))
        self.barcode_supplier_filter = QComboBox()
        self.barcode_supplier_filter.setStyleSheet(INPUT_STYLE)
        self.barcode_supplier_filter.currentIndexChanged.connect(
            self._load_barcode_products
        )
        filters.addWidget(self.barcode_supplier_filter)
        filters.addStretch()
        existing_layout.addLayout(filters)

        self.barcode_table = QTableWidget(0, 4)
        self.barcode_table.setHorizontalHeaderLabels(
            ["الرمز", "الاسم", "إجراء", "السعر"]
        )
        self.barcode_table.setColumnHidden(3, True)
        self._configure_table(self.barcode_table)
        self.barcode_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.barcode_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.barcode_table.itemSelectionChanged.connect(
            self._fill_barcode_from_selected_row
        )
        existing_layout.addWidget(self.barcode_table)

        self.barcode_page = 1
        self.barcode_per_page = 100

        page_layout = QHBoxLayout()
        self.prev_barcode_btn = QPushButton("◀ السابق")
        self.prev_barcode_btn.setStyleSheet(get_button_style("secondary"))
        self.prev_barcode_btn.clicked.connect(self._prev_barcode_page)

        self.barcode_page_label = QLabel("صفحة 1")
        self.barcode_page_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: bold;"
        )

        self.next_barcode_btn = QPushButton("التالي ▶")
        self.next_barcode_btn.setStyleSheet(get_button_style("secondary"))
        self.next_barcode_btn.clicked.connect(self._next_barcode_page)

        page_layout.addWidget(self.prev_barcode_btn)
        page_layout.addWidget(self.barcode_page_label)
        page_layout.addWidget(self.next_barcode_btn)
        page_layout.addStretch()
        existing_layout.addLayout(page_layout)

        right_layout.addWidget(existing_card, 1)

        left_panel = QWidget()
        left_panel.setFixedWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        preview_card = self._barcode_card("👀 المعاينة المباشرة")
        preview_layout = preview_card.layout()
        self.barcode_preview = QLabel("أدخل بيانات للمعاينة")
        self.barcode_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.barcode_preview.setMinimumHeight(160)
        self.barcode_preview.setStyleSheet(
            f"background-color: white; border: 1px solid {COLORS['border']}; "
            "border-radius: 8px; color: #111; padding: 8px;"
        )
        preview_layout.addWidget(self.barcode_preview)

        self.barcode_info_label = QLabel("")
        self.barcode_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.barcode_info_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: 700;"
        )
        preview_layout.addWidget(self.barcode_info_label)

        settings = QHBoxLayout()
        size_box = QVBoxLayout()
        size_box.addWidget(QLabel("📏 مقاس الملصق:"))
        self.barcode_size = QComboBox()
        self.barcode_size.addItems(["50x30", "40x25", "30x20"])
        self.barcode_size.setStyleSheet(INPUT_STYLE)
        self.barcode_size.currentTextChanged.connect(self._preview_barcode)
        size_box.addWidget(self.barcode_size)
        settings.addLayout(size_box)

        copies_box = QVBoxLayout()
        copies_box.addWidget(QLabel("🔢 عدد النسخ:"))
        self.barcode_copies = QSpinBox()
        self.barcode_copies.setRange(1, 100)
        self.barcode_copies.setValue(1)
        self.barcode_copies.setStyleSheet(INPUT_STYLE)
        copies_box.addWidget(self.barcode_copies)
        settings.addLayout(copies_box)
        preview_layout.addLayout(settings)

        template_box = QVBoxLayout()
        template_box.addWidget(QLabel("🎨 قالب الملصق:"))
        self.barcode_template = QComboBox()
        self.barcode_template.addItems(["قالب قياسي (كود + اسم)", "قالب عريض (مع السعر)", "قالب تفصيلي (اسم + باركود + سعر)"])
        self.barcode_template.setStyleSheet(INPUT_STYLE)
        template_box.addWidget(self.barcode_template)
        preview_layout.addLayout(template_box)

        preview_layout.addWidget(QLabel("🖨️ اختر الطابعة:"))
        self.barcode_printer = QComboBox()
        self.barcode_printer.setStyleSheet(INPUT_STYLE)
        self._load_printers()
        preview_layout.addWidget(self.barcode_printer)

        print_btn = QPushButton("🖨️ طباعة الآن")
        print_btn.setStyleSheet(get_button_style("success"))
        print_btn.clicked.connect(self._print_barcode)
        preview_layout.addWidget(print_btn)

        save_btn = QPushButton("حفظ صورة")
        save_btn.setStyleSheet(get_button_style("outline"))
        save_btn.clicked.connect(self._save_barcode_image)
        preview_layout.addWidget(save_btn)
        preview_layout.addStretch()
        left_layout.addWidget(preview_card)
        left_layout.addStretch()

        main_layout.addWidget(right_panel, 6)
        main_layout.addWidget(left_panel, 4)
        scroll.setWidget(container)

        self._load_barcode_suppliers()
        self._load_barcode_products()
        return scroll

    def _create_manual_barcode_dialog(self):
        self.barcode_manual_dialog = QDialog(self)
        self.barcode_manual_dialog.setWindowTitle("صنف جديد / مخصص")
        style_dialog(self.barcode_manual_dialog, min_width=480)
        dialog_layout = QVBoxLayout(self.barcode_manual_dialog)
        form = QFormLayout()
        configure_form_layout(form)
        self.barcode_code = QLineEdit()
        self.barcode_code.setPlaceholderText("أدخل كود الصنف...")
        self.barcode_name = QLineEdit()
        self.barcode_name.setPlaceholderText("أدخل اسم الصنف...")
        self.barcode_price = QLineEdit()
        self.barcode_price.setPlaceholderText("أدخل السعر...")
        for widget in (self.barcode_code, self.barcode_name, self.barcode_price):
            widget.setStyleSheet(INPUT_STYLE)
            widget.textChanged.connect(self._preview_barcode)
        form.addRow("الكود:", self.barcode_code)
        form.addRow("الاسم:", self.barcode_name)
        form.addRow("السعر:", self.barcode_price)
        dialog_layout.addLayout(form)

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet(get_button_style("secondary"))
        close_btn.clicked.connect(self.barcode_manual_dialog.close)
        dialog_layout.addWidget(close_btn)

    def _open_manual_barcode_dialog(self):
        self.barcode_manual_dialog.show()
        self.barcode_manual_dialog.raise_()
        self.barcode_manual_dialog.activateWindow()

    def _barcode_card(self, title):
        card = QFrame()
        card.setObjectName("ProductCard")
        card.setStyleSheet(
            f"QFrame#ProductCard {{ background-color: {COLORS['bg_panel']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 12px; padding: 8px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 14px; font-weight: 700;"
        )
        layout.addWidget(title_label)
        return card

    def _load_printers(self):
        self.barcode_printer.clear()
        printers = [
            printer.printerName() for printer in QPrinterInfo.availablePrinters()
        ]
        self.barcode_printer.addItems(printers)
        default_printer = QPrinterInfo.defaultPrinter().printerName()
        index = self.barcode_printer.findText(default_printer)
        if index >= 0:
            self.barcode_printer.setCurrentIndex(index)

    def _load_barcode_suppliers(self):
        self.barcode_supplier_filter.blockSignals(True)
        self.barcode_supplier_filter.clear()
        self.barcode_supplier_filter.addItem("كل الموردين", None)
        for supplier in self.ctrl.get_suppliers():
            self.barcode_supplier_filter.addItem(supplier["name"], supplier["id"])
        self.barcode_supplier_filter.blockSignals(False)

    def _prev_barcode_page(self):
        if hasattr(self, "barcode_page") and self.barcode_page > 1:
            self.barcode_page -= 1
            self._load_barcode_products()

    def _next_barcode_page(self):
        if hasattr(self, "barcode_page"):
            self.barcode_page += 1
            self._load_barcode_products()

    def _load_barcode_products(self, *_args):
        if not hasattr(self, "barcode_table"):
            return
        search = (
            self.barcode_search_input.text().strip()
            if hasattr(self, "barcode_search_input")
            else ""
        )
        supplier_id = (
            self.barcode_supplier_filter.currentData()
            if hasattr(self, "barcode_supplier_filter")
            else None
        )

        page = getattr(self, "barcode_page", 1)
        per_page = getattr(self, "barcode_per_page", 100)

        products, total = self.ctrl.get_products(
            search=search,
            supplier_id=supplier_id,
            page=page,
            per_page=per_page,
        )

        total_pages = max(1, (total + per_page - 1) // per_page)
        if page > total_pages:
            self.barcode_page = total_pages
            products, total = self.ctrl.get_products(
                search=search,
                supplier_id=supplier_id,
                page=self.barcode_page,
                per_page=per_page,
            )

        if hasattr(self, "barcode_page_label"):
            self.barcode_page_label.setText(
                f"صفحة {self.barcode_page} من {total_pages}"
            )
            self.prev_barcode_btn.setEnabled(self.barcode_page > 1)
            self.next_barcode_btn.setEnabled(self.barcode_page < total_pages)

        self.barcode_table.setRowCount(len(products))
        self.barcode_table.blockSignals(True)
        for row, product in enumerate(products):
            code = str(product.barcode or product.product_code)
            name = str(product.product_name)
            price = f"{float(product.sell_price or 0):.2f}"
            set_center_item(self.barcode_table, row, 0, code)
            set_center_item(self.barcode_table, row, 1, name)
            set_center_item(self.barcode_table, row, 3, price)
            choose_btn = table_action_button(
                "اختيار",
                "info",
                lambda checked=False, r=row: self._select_barcode_row(r),
            )
            self.barcode_table.setCellWidget(row, 2, actions_cell([choose_btn]))
        self.barcode_table.blockSignals(False)

    def _select_barcode_row(self, row):
        self.barcode_table.selectRow(row)
        self._fill_barcode_from_selected_row()

    def _fill_barcode_from_selected_row(self):
        if not hasattr(self, "barcode_table"):
            return
        selected = self.barcode_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        code_item = self.barcode_table.item(row, 0)
        name_item = self.barcode_table.item(row, 1)
        price_item = self.barcode_table.item(row, 3)
        if not code_item or not name_item:
            return
        self.barcode_code.blockSignals(True)
        self.barcode_name.blockSignals(True)
        self.barcode_price.blockSignals(True)
        self.barcode_code.setText(code_item.text())
        self.barcode_name.setText(name_item.text())
        self.barcode_price.setText(price_item.text() if price_item else "")
        self.barcode_code.blockSignals(False)
        self.barcode_name.blockSignals(False)
        self.barcode_price.blockSignals(False)
        self._preview_barcode()

    def _preview_barcode(self, *_args):
        code = self.barcode_code.text().strip()
        name = self.barcode_name.text().strip()
        price = self.barcode_price.text().strip() or None
        if not code:
            self.barcode_preview.setText("أدخل بيانات للمعاينة")
            self.barcode_info_label.setText("")
            return
        path = BarcodeService.generate_barcode(
            code,
            name,
            price=price,
            label_size=self.barcode_size.currentText(),
            write_text=False,
        )
        self._last_barcode_path = path
        if not path:
            self.barcode_preview.setText("تعذر إنشاء الباركود")
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.barcode_preview.setText(path or "تعذر إنشاء الباركود")
            return
        self.barcode_preview.setPixmap(
            pixmap.scaled(
                self.barcode_preview.width(),
                self.barcode_preview.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        info = f"{name}\n({code})"
        if price:
            info += f"\nالسعر: {price} ج.م"
        self.barcode_info_label.setText(info)

    def _print_barcode(self):
        code = self.barcode_code.text().strip()
        name = self.barcode_name.text().strip()
        if not code:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار صنف أو إدخال بيانات أولاً")
            return
        printer_name = self.barcode_printer.currentText().strip()
        if not printer_name:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار طابعة أولاً")
            return
        store_name = (
            self.user_info.get("store_name", "")
            if isinstance(self.user_info, dict)
            else getattr(self.user_info, "store_name", "")
        )
        job = BarcodePrintJob(
            name=name,
            code=code,
            printer_name=printer_name,
            label_size=self.barcode_size.currentText(),
            price=self.barcode_price.text().strip(),
            store_name=store_name,
            copies=self.barcode_copies.value(),
        )
        success_count = PrinterService.print_barcode_labels(job)
        if success_count:
            QMessageBox.information(
                self, "تم", f"تم إرسال {success_count} نسخة للطباعة"
            )
        else:
            QMessageBox.warning(self, "خطأ", "تعذرت طباعة الباركود")

    def _save_barcode_image(self):
        self._preview_barcode()
        path = getattr(self, "_last_barcode_path", None)
        if not path:
            return
        target, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ صورة الباركود",
            f"{self.barcode_code.text().strip()}.png",
            "PNG Images (*.png)",
        )
        if not target:
            return
        pixmap = QPixmap(path)
        if pixmap.save(target, "PNG"):
            QMessageBox.information(self, "تم", "تم حفظ صورة الباركود")
        else:
            QMessageBox.warning(self, "خطأ", "تعذر حفظ صورة الباركود")

    def load_data(self):
        search_term = self.search_input.text().strip()
        category_id = (
            self.product_category_filter.currentData()
            if hasattr(self, "product_category_filter")
            else None
        )
        supplier_id = (
            self.product_supplier_filter.currentData()
            if hasattr(self, "product_supplier_filter")
            else None
        )
        products, total = self.ctrl.get_products(
            search=search_term,
            category_id=category_id,
            supplier_id=supplier_id,
            page=self.current_page,
            per_page=self.per_page,
            column_filters=self._product_column_filters(),
        )

        self.table.setRowCount(len(products))

        # Permissions
        policy = PermissionPolicy(self.user_info)
        can_view_buy = policy.can_view_buy_price()
        can_edit = policy.can_edit_products()
        can_delete = policy.can_delete_products()

        for row, p in enumerate(products):
            self.table.setRowHeight(row, 52)

            # Code
            set_center_item(self.table, row, 0, p.product_code)
            # Name
            set_center_item(self.table, row, 1, p.product_name)

            # Buy Price
            buy_price = f"{p.buy_price:,.2f}" if can_view_buy else "***"
            set_center_item(self.table, row, 2, buy_price)

            # Sell Price
            set_center_item(self.table, row, 3, f"{p.sell_price:,.2f}")

            # Unit
            set_center_item(self.table, row, 4, p.unit)

            status_text = {
                "ready": "جاهز",
                "needs_pricing": "ناقص سعر",
                "needs_cost": "ناقص تكلفة",
            }.get(
                getattr(p, "import_status", "ready"),
                getattr(p, "import_status", "ready"),
            )
            set_center_item(self.table, row, 5, status_text)

            # Actions
            action_buttons = []
            history_btn = table_action_button(
                "📈 السجل",
                "info",
                lambda checked=False, p_obj=p: self._show_price_history(p_obj),
            )
            action_buttons.append(history_btn)
            if can_edit:
                edit_btn = table_action_button(
                    "تعديل",
                    "warning",
                    lambda checked=False, pid=p.id: self._edit_product(pid),
                )
                action_buttons.append(edit_btn)
            if can_delete:
                del_btn = table_action_button(
                    "حذف",
                    "danger",
                    lambda checked=False, pid=p.id: self._delete_product(pid),
                )
                action_buttons.append(del_btn)

            self.table.setCellWidget(row, 6, actions_cell(action_buttons))

        # Update pagination state
        total_pages = max(1, (total + self.per_page - 1) // self.per_page)
        self.page_label.setText(f"صفحة {self.current_page} من {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)

    def _on_search_changed(self, text):
        self.current_page = 1
        self.load_data()

    def _on_product_filter_changed(self, *_args):
        self.current_page = 1
        self.load_data()

    def _reset_product_filters(self):
        self.search_input.clear()
        self.product_category_filter.setCurrentIndex(0)
        self.product_supplier_filter.setCurrentIndex(0)
        if hasattr(self, "product_code_filter"):
            self.product_code_filter.clear()
            self.product_name_filter.clear()
            self.product_unit_filter.clear()
            self.product_min_buy_filter.setValue(0)
            self.product_max_buy_filter.setValue(0)
            self.product_min_sell_filter.setValue(0)
            self.product_max_sell_filter.setValue(0)
            self.product_status_filter.setCurrentIndex(0)
        self.product_sort_column = None
        self.product_sort_direction = None
        if hasattr(self, "table") and isinstance(
            self.table.horizontalHeader(), FilterSortHeader
        ):
            self.table.horizontalHeader().set_sort_state(None, None)
        self.current_page = 1
        self.load_data()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()

    def _next_page(self):
        self.current_page += 1
        self.load_data()

    def _on_add_product(self):
        if not PermissionPolicy(self.user_info).can_edit_products():
            QMessageBox.warning(self, "صلاحية مرفوضة", "لا تملك صلاحية إضافة المنتجات")
            return
        dialog = ProductDialog(self.ctrl, self)
        if dialog.exec():
            data = dialog.get_data()
            if not data["product_code"]:
                QMessageBox.warning(self, "تنبيه", "كود المنتج مطلوب")
                return

            try:
                self.ctrl.create_product(data, store_id=self._get_store_id())
                self.load_data()
                self._load_inventory()
                self._load_barcode_products()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الإضافة:\n{str(e)}")

    def _import_from_excel(self):
        if not PermissionPolicy(self.user_info).can_edit_products():
            QMessageBox.warning(
                self, "صلاحية مرفوضة", "لا تملك صلاحية استيراد المنتجات"
            )
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "استيراد المنتجات من Excel",
            "",
            "Product Files (*.xlsx *.xlsm *.csv);;Excel Files (*.xlsx *.xlsm);;CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            preview = self.ctrl.preview_import_file(file_path)
            dialog = ProductImportPreviewDialog(preview, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            result = self.ctrl.commit_import_preview(
                dialog.get_rows(),
                self._get_store_id(),
                include_incomplete=dialog.should_include_incomplete(),
            )
            self.load_data()
            self._load_inventory()
            self._load_barcode_products()
            QMessageBox.information(
                self,
                "تم الاستيراد",
                (
                    f"تمت معالجة {result.get('processed', 0)} صف.\n"
                    f"ناجح: {result.get('valid', 0)}\n"
                    f"متخطى: {result.get('skipped', 0)}\n"
                    f"أخطاء: {result.get('errors', 0)}\n"
                    f"بدون سعر: {preview.get('needs_pricing', 0)}\n"
                    f"بدون تكلفة: {preview.get('needs_cost', 0)}"
                ),
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر استيراد ملف Excel:\n{str(e)}")

    def _fix_zero_costs(self):
        if not PermissionPolicy(self.user_info).can_view_buy_price():
            QMessageBox.warning(self, "صلاحية مرفوضة", "لا تملك صلاحية تصحيح التكاليف")
            return
        margin, ok = QInputDialog.getDouble(
            self,
            "تصحيح التكاليف",
            "هامش الربح الافتراضي %:",
            25.0,
            0.0,
            99.0,
            2,
        )
        if not ok:
            return

        reply = QMessageBox.question(
            self,
            "تأكيد التصحيح",
            "سيتم تعديل سعر الشراء للمنتجات التي لا تحتوي على تكلفة فقط. هل تريد المتابعة؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            count = self.ctrl.fix_zero_costs(margin)
            self.load_data()
            QMessageBox.information(self, "تم", f"تم تصحيح تكلفة {count} منتج")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر تصحيح التكاليف:\n{str(e)}")

    def _edit_product(self, product_id):
        if not PermissionPolicy(self.user_info).can_edit_products():
            QMessageBox.warning(self, "صلاحية مرفوضة", "لا تملك صلاحية تعديل المنتجات")
            return
        product = self.ctrl.get_product(product_id)
        if not product:
            return

        dialog = ProductDialog(self.ctrl, self, product)
        if dialog.exec():
            data = dialog.get_data()
            try:
                self.ctrl.update_product(product_id, data)
                self.load_data()
                self._load_inventory()
                self._load_barcode_products()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء التحديث:\n{str(e)}")

    def _delete_product(self, product_id):
        if not PermissionPolicy(self.user_info).can_delete_products():
            QMessageBox.warning(self, "صلاحية مرفوضة", "لا تملك صلاحية حذف المنتجات")
            return
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            "هل أنت متأكد من حذف هذا المنتج؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.ctrl.delete_product(product_id, self._get_user_id()):
                self.load_data()
                self._load_inventory()
                self._load_barcode_products()
            else:
                QMessageBox.warning(self, "خطأ", "لم يتم حذف المنتج")

    def _show_price_history(self, product):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"سجل أسعار الصنف: {product.product_name}")
        style_dialog(dialog, min_width=450, min_height=300)
        _, content_layout, footer_layout = scrollable_dialog_layout(dialog)
        
        info = QLabel(
            f"<b>كود الصنف:</b> {product.product_code}<br>"
            f"<b>اسم الصنف:</b> {product.product_name}<br>"
            f"<b>سعر الشراء الحالي:</b> {float(product.buy_price or 0):,.2f} ج.م<br>"
            f"<b>سعر البيع الحالي:</b> {float(product.sell_price or 0):,.2f} ج.م"
        )
        info.setStyleSheet("font-size: 13px; line-height: 1.6; padding: 5px;")
        content_layout.addWidget(info)
        
        history_table = QTableWidget(0, 3)
        history_table.setHorizontalHeaderLabels(["التاريخ", "سعر الشراء", "سعر البيع"])
        history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(history_table, TABLE_STYLE)
        
        history_table.setRowCount(1)
        set_center_item(history_table, 0, 0, str(getattr(product, 'updated_at', 'الحالي')))
        set_center_item(history_table, 0, 1, f"{float(product.buy_price or 0):,.2f}")
        set_center_item(history_table, 0, 2, f"{float(product.sell_price or 0):,.2f}")
        content_layout.addWidget(history_table)
        
        btn_layout, ok_btn, _ = action_row("إغلاق")
        ok_btn.clicked.connect(dialog.accept)
        footer_layout.addLayout(btn_layout)
        dialog.exec()
