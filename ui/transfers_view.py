"""
Transfers View - warehouse transfers between stores.
"""
import logging

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from controllers.transfers_controller import TransfersController
from ui.styles import GLOBAL_STYLE, TABLE_STYLE, get_button_style, COLORS
from ui.form_helpers import action_row, configure_form_layout, style_dialog, style_form_controls
from ui.table_helpers import actions_cell, center_item, configure_table, table_action_button

logger = logging.getLogger(__name__)


class NewTransferDialog(QDialog):
    def __init__(self, ctrl: TransfersController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user_info = user_info
        self.products = []
        self.stores = []
        self.setWindowTitle("تحويل مخزني جديد")
        style_dialog(self, min_width=560)
        self._init_ui()
        self._load_stores()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        configure_form_layout(form)

        self.from_store = QComboBox()
        self.to_store = QComboBox()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("اكتب كود أو اسم المنتج ثم اضغط بحث")
        self.product_combo = QComboBox()
        self.qty = QDoubleSpinBox()
        self.qty.setRange(0.001, 100000)
        self.qty.setDecimals(3)
        self.qty.setValue(1.0)
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("ملاحظات اختيارية")
        style_form_controls(
            self.from_store, self.to_store, self.search_input,
            self.product_combo, self.qty, self.notes
        )

        search_row = QHBoxLayout()
        search_row.addWidget(self.search_input)
        search_btn = QPushButton("بحث")
        search_btn.setStyleSheet(get_button_style("info"))
        search_btn.clicked.connect(self._search_products)
        search_row.addWidget(search_btn)

        form.addRow("من فرع:", self.from_store)
        form.addRow("إلى فرع:", self.to_store)
        form.addRow("بحث المنتج:", search_row)
        form.addRow("المنتج:", self.product_combo)
        form.addRow("الكمية:", self.qty)
        form.addRow("ملاحظات:", self.notes)
        layout.addLayout(form)

        actions, save_btn, cancel_btn = action_row("حفظ التحويل")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addLayout(actions)

        self.search_input.returnPressed.connect(self._search_products)
        self.from_store.currentIndexChanged.connect(self._clear_products)

    def _load_stores(self):
        self.stores = self.ctrl.get_stores()
        self.from_store.clear()
        self.to_store.clear()
        for store in self.stores:
            label = f"{store['store_name']} ({store['store_type']})"
            self.from_store.addItem(label, store["id"])
            self.to_store.addItem(label, store["id"])

        user_store_id = self.user_info.get("store_id")
        for combo in (self.from_store, self.to_store):
            index = combo.findData(user_store_id)
            if index >= 0:
                combo.setCurrentIndex(index)

    def _clear_products(self):
        self.product_combo.clear()
        self.products = []

    def _search_products(self):
        term = self.search_input.text().strip()
        store_id = self.from_store.currentData()
        self.products = self.ctrl.search_products(term, store_id=store_id)
        self.product_combo.clear()
        for product in self.products:
            label = (
                f"{product['product_code']} - {product['product_name']} "
                f"(المتاح: {product.get('quantity_in_stock', 0)})"
            )
            self.product_combo.addItem(label, product["id"])
        if not self.products:
            QMessageBox.information(self, "بحث المنتجات", "لا توجد نتائج في الفرع المصدر.")

    def get_data(self) -> dict:
        return {
            "product_id": self.product_combo.currentData(),
            "from_store_id": self.from_store.currentData(),
            "to_store_id": self.to_store.currentData(),
            "quantity": self.qty.value(),
            "notes": self.notes.text().strip(),
        }

    def accept(self):
        if not self.product_combo.currentData():
            QMessageBox.warning(self, "تنبيه", "يجب اختيار منتج قبل حفظ التحويل.")
            self.search_input.setFocus()
            return
        if self.from_store.currentData() == self.to_store.currentData():
            QMessageBox.warning(self, "تنبيه", "لا يمكن التحويل إلى نفس الفرع.")
            self.to_store.setFocus()
            return
        super().accept()


class TransfersView(QWidget):
    def __init__(self, ctrl: TransfersController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user = user_info
        self.setStyleSheet(GLOBAL_STYLE)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("📦 التحويلات المخزنية")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['text_on_brand']};")
        header.addWidget(title)

        header.addStretch()
        header.addWidget(QLabel("الحالة:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Pending", "Received", "Cancelled"])
        self.status_filter.currentIndexChanged.connect(self.load_data)
        header.addWidget(self.status_filter)

        add_transfer_btn = QPushButton("➕ تحويل جديد")
        add_transfer_btn.setStyleSheet(get_button_style("primary"))
        add_transfer_btn.clicked.connect(self._new_transfer)
        header.addWidget(add_transfer_btn)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "رقم التحويل",
            "المنتج",
            "الكمية",
            "من",
            "إلى",
            "الحالة",
            "التاريخ",
            "ملاحظات",
            "إجراءات",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(self.table, TABLE_STYLE)
        layout.addWidget(self.table)

        self.refresh_btn = QPushButton("🔄 تحديث البيانات")
        self.refresh_btn.setStyleSheet(get_button_style("info"))
        self.refresh_btn.clicked.connect(self.load_data)
        layout.addWidget(self.refresh_btn)

        self.load_data()

    def load_data(self):
        try:
            status = self.status_filter.currentText() if hasattr(self, "status_filter") else "All"
            transfers = self.ctrl.get_transfers(self.user, status=status)
            self.table.setRowCount(len(transfers))

            for row, transfer in enumerate(transfers):
                values = [
                    transfer.get("transfer_number", ""),
                    f"{transfer.get('product_code', '')} - {transfer.get('product_name', '')}",
                    str(transfer.get("quantity_sent", "")),
                    transfer.get("from_store_name", ""),
                    transfer.get("to_store_name", ""),
                    transfer.get("status", ""),
                    str(transfer.get("transfer_date", "")),
                    transfer.get("notes", "") or "",
                ]
                for col, value in enumerate(values):
                    self.table.setItem(row, col, center_item(value))

                self.table.setCellWidget(row, 8, self._actions_widget(transfer))
        except Exception as exc:
            logger.error(f"Error loading transfers: {exc}", exc_info=True)
            QMessageBox.critical(self, "خطأ", f"فشل تحميل التحويلات: {exc}")

    def _actions_widget(self, transfer: dict) -> QWidget:
        status = transfer.get("status")
        transfer_id = transfer.get("id")

        receive_btn = table_action_button("استلام", "success", lambda: self._receive_transfer(transfer_id))
        receive_btn.setEnabled(status == "Pending")

        cancel_btn = table_action_button("إلغاء", "danger", lambda: self._cancel_transfer(transfer_id))
        cancel_btn.setEnabled(status == "Pending")

        return actions_cell([receive_btn, cancel_btn])

    def _new_transfer(self):
        dialog = NewTransferDialog(self.ctrl, self.user, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()

        ok, message = self.ctrl.create_transfer(
            product_id=data["product_id"],
            from_store_id=data["from_store_id"],
            to_store_id=data["to_store_id"],
            quantity=data["quantity"],
            user_id=self.user.get("id", 1),
            notes=data["notes"],
        )
        if ok:
            QMessageBox.information(self, "نجاح", message)
            self.load_data()
        else:
            QMessageBox.warning(self, "تعذر الحفظ", message)

    def _receive_transfer(self, transfer_id: int):
        reply = QMessageBox.question(
            self,
            "استلام التحويل",
            "هل تريد استلام هذا التحويل وتحديث المخزون؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, message = self.ctrl.receive_transfer(transfer_id, self.user)
        if ok:
            QMessageBox.information(self, "نجاح", message)
            self.load_data()
        else:
            QMessageBox.warning(self, "تعذر الاستلام", message)

    def _cancel_transfer(self, transfer_id: int):
        reply = QMessageBox.question(
            self,
            "إلغاء التحويل",
            "هل تريد إلغاء هذا التحويل وإرجاع الكمية للمصدر؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, message = self.ctrl.cancel_transfer(transfer_id)
        if ok:
            QMessageBox.information(self, "نجاح", message)
            self.load_data()
        else:
            QMessageBox.warning(self, "تعذر الإلغاء", message)

    def refresh_data(self):
        self.load_data()
