"""
Returns View - واجهة المرتجعات (Clean Architecture)
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
    QHeaderView,
    QGroupBox,
    QFormLayout,
    QSpinBox,
    QDialog,
    QDateEdit,
    QFrame,
    QGridLayout,
    QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QColor
from ui.styles import (
    GLOBAL_STYLE,
    COLORS,
    TABLE_STYLE,
    INPUT_STYLE,
    get_button_style,
    GROUP_BOX_STYLE,
    CARD_STYLE,
)
from ui.table_helpers import center_item, configure_table
from controllers.returns_controller import ReturnsController
from utils.printer_service import PrinterService
from utils.permissions import PermissionPolicy
from services.whatsapp_share_service import WhatsAppShareService

logger = logging.getLogger(__name__)


class ReturnsView(QWidget):
    return_processed = pyqtSignal()

    def __init__(self, ctrl: ReturnsController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user = user_info
        self.current_invoice = None
        self.selected_total = 0.0
        self.setStyleSheet(GLOBAL_STYLE)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Check permissions
        if not PermissionPolicy(self.user).can_access_returns():
            lbl = QLabel("⛔ ليس لديك صلاحية الوصول لهذه الصفحة")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            lbl.setStyleSheet("color: red; margin-top: 50px;")
            layout.addWidget(lbl)
            return

        # Search
        search_group = QGroupBox("البحث عن فاتورة")
        search_group.setStyleSheet(GROUP_BOX_STYLE)
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("أدخل رقم الفاتورة أو آخر 4 أرقام...")
        self.search_input.setStyleSheet(INPUT_STYLE)
        self.search_input.returnPressed.connect(self._search_invoice)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("🔍 بحث")
        search_btn.setStyleSheet(get_button_style("primary"))
        search_btn.clicked.connect(self._search_invoice)
        search_layout.addWidget(search_btn)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # Invoice Info
        self.info_group = QGroupBox("بيانات الفاتورة")
        self.info_group.setStyleSheet(GROUP_BOX_STYLE)
        self.info_group.hide()
        info_layout = QGridLayout()
        self.lbl_date = QLabel("-")
        self.lbl_customer = QLabel("-")
        self.lbl_total = QLabel("-")
        self.lbl_payment = QLabel("-")
        self.lbl_status = QLabel("-")
        for label in (
            self.lbl_date,
            self.lbl_customer,
            self.lbl_total,
            self.lbl_payment,
            self.lbl_status,
        ):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 700;")
        info_layout.addWidget(QLabel("تاريخ الفاتورة"), 0, 0)
        info_layout.addWidget(self.lbl_date, 1, 0)
        info_layout.addWidget(QLabel("اسم العميل"), 0, 1)
        info_layout.addWidget(self.lbl_customer, 1, 1)
        info_layout.addWidget(QLabel("إجمالي الفاتورة"), 0, 2)
        info_layout.addWidget(self.lbl_total, 1, 2)
        info_layout.addWidget(QLabel("طريقة الدفع"), 0, 3)
        info_layout.addWidget(self.lbl_payment, 1, 3)
        info_layout.addWidget(QLabel("الحالة"), 0, 4)
        info_layout.addWidget(self.lbl_status, 1, 4)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        summary_layout = QHBoxLayout()
        self.available_items_card, self.available_items_lbl = self._create_summary_card(
            "أصناف قابلة للإرجاع", "0"
        )
        self.selected_items_card, self.selected_items_lbl = self._create_summary_card(
            "أصناف مختارة", "0"
        )
        self.return_total_card, self.return_total_lbl = self._create_summary_card(
            "إجمالي المرتجع", "0.00 ج.م"
        )
        self.cash_refund_card, self.cash_refund_lbl = self._create_summary_card(
            "استرداد نقدي متوقع", "0.00 ج.م"
        )
        for card in (
            self.available_items_card,
            self.selected_items_card,
            self.return_total_card,
            self.cash_refund_card,
        ):
            summary_layout.addWidget(card)
        layout.addLayout(summary_layout)

        # Items Table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(
            ["المنتج", "السعر", "الكمية المباعة", "الكمية المرتجعة", "الإجمالي"]
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        configure_table(self.items_table, TABLE_STYLE, row_height=46)
        layout.addWidget(self.items_table)

        # Actions
        actions = QHBoxLayout()
        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText("سبب المرتجع...")
        self.reason_input.setStyleSheet(INPUT_STYLE)
        actions.addWidget(self.reason_input)

        self.print_pdf_chk = QCheckBox("حفظ إيصال PDF")
        self.print_pdf_chk.setChecked(True)
        self.print_pdf_chk.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: 700;"
        )
        actions.addWidget(self.print_pdf_chk)

        self.process_btn = QPushButton("🔄 إتمام المرتجع")
        self.process_btn.setStyleSheet(get_button_style("success"))
        self.process_btn.clicked.connect(self._process_return)
        self.process_btn.setEnabled(False)
        actions.addWidget(self.process_btn)

        history_btn = QPushButton("📜 سجل المرتجعات")
        history_btn.setStyleSheet(get_button_style("info"))
        history_btn.clicked.connect(self._show_history)
        actions.addWidget(history_btn)

        clear_btn = QPushButton("🗑️ مسح")
        clear_btn.setStyleSheet(get_button_style("secondary"))
        clear_btn.clicked.connect(self._clear_page)
        actions.addWidget(clear_btn)

        layout.addLayout(actions)
        layout.addStretch()

    def _create_summary_card(self, title: str, value: str):
        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
        card_layout = QVBoxLayout(card)
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        value_lbl = QLabel(value)
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_lbl.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: 800;"
        )
        card_layout.addWidget(title_lbl)
        card_layout.addWidget(value_lbl)
        return card, value_lbl

    def _search_invoice(self):
        num = self.search_input.text().strip()
        if not num:
            return
        self._clear_invoice_result()
        try:
            invoice = self.ctrl.search_invoice(num)
        except Exception as exc:
            logger.error("Error searching invoice: %s", exc, exc_info=True)
            QMessageBox.critical(self, "خطأ", "تعذر البحث عن الفاتورة")
            return
        if not invoice:
            QMessageBox.warning(self, "خطأ", "الفاتورة غير موجودة")
            return
        if invoice.get("status") != "Completed":
            QMessageBox.warning(self, "تنبيه", "لا يمكن عمل مرتجع لفاتورة غير مكتملة")
            return

        self.current_invoice = invoice
        self.lbl_date.setText(str(invoice.get("invoice_date", "")))
        self.lbl_customer.setText(invoice.get("customer_name", "") or "عميل نقدي")
        self.lbl_total.setText(self._format_money(invoice.get("total_amount", 0)))
        self.lbl_payment.setText(
            self._payment_label(invoice.get("payment_method", "Cash"))
        )
        self.lbl_status.setText("مكتملة")
        self.info_group.show()

        try:
            items = self.ctrl.get_invoice_items(invoice["id"])
        except Exception as exc:
            logger.error("Error loading invoice items: %s", exc, exc_info=True)
            self._clear_invoice_result()
            QMessageBox.critical(self, "خطأ", "تعذر تحميل أصناف الفاتورة")
            return
        self._display_items(items)
        self.process_btn.setEnabled(self._has_returnable_items())

    def _display_items(self, items):
        self.items_table.setRowCount(0)
        for item in items:
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)

            sold_qty = item.get("quantity", 1)
            returned = item.get("returned_quantity", 0)
            available = max(0, sold_qty - returned)

            try:
                total_price = float(
                    item.get("total_price", item.get("unit_price", 0) * sold_qty)
                )
                effective_price = (
                    total_price / sold_qty
                    if sold_qty > 0
                    else float(item.get("unit_price", 0))
                )
            except:
                effective_price = float(item.get("unit_price", 0))

            prod_item = self._table_item(item["product_name"])
            prod_item.setData(Qt.ItemDataRole.UserRole, item["product_id"])
            prod_item.setData(
                Qt.ItemDataRole.UserRole + 1, float(item.get("buy_price") or 0)
            )
            prod_item.setData(
                Qt.ItemDataRole.UserRole + 2, item.get("invoice_item_id") or item.get("id")
            )
            self.items_table.setItem(row, 0, prod_item)
            self.items_table.setItem(row, 1, self._table_item(f"{effective_price:.2f}"))

            qty_text = (
                f"{sold_qty}" if returned == 0 else f"{available} (من أصل {sold_qty})"
            )
            qty_item = self._table_item(qty_text)
            self.items_table.setItem(row, 2, qty_item)

            spin = QSpinBox()
            spin.setRange(0, int(available))
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.setFixedSize(130, 34)
            spin.setStyleSheet(f"""
                QSpinBox {{
                    background: {COLORS['bg_input']};
                    color: {COLORS['text_primary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 10px;
                    padding: 0 8px;
                    font-size: 13px;
                    font-weight: 700;
                }}
                QSpinBox:focus {{
                    border: 1px solid {COLORS['primary']};
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    width: 0;
                    border: none;
                }}
            """)
            if available <= 0:
                spin.setEnabled(False)
                qty_item.setText(f"تم الإرجاع ({sold_qty})")
                qty_item.setForeground(QColor(COLORS.get("danger", "#FF0000")))

            spin_cell = QWidget()
            spin_layout = QHBoxLayout(spin_cell)
            spin_layout.setContentsMargins(0, 0, 0, 0)
            spin_layout.setSpacing(0)
            spin_layout.addWidget(spin, 0, Qt.AlignmentFlag.AlignCenter)
            self.items_table.setCellWidget(row, 3, spin_cell)
            self.items_table.setItem(row, 4, self._table_item("0.00"))

            spin.valueChanged.connect(
                lambda v, r=row, p=effective_price: self._update_row_total(r, v, p)
            )
        self._update_summary()

    def _table_item(self, value):
        return center_item(value)

    def _update_row_total(self, row: int, quantity: int, price: float):
        self.items_table.setItem(row, 4, self._table_item(f"{quantity * price:.2f}"))
        self._update_summary()

    def _format_money(self, value) -> str:
        return f"{float(value or 0):,.2f} ج.م"

    def _payment_label(self, method: str) -> str:
        labels = {
            "Cash": "نقدي",
            "Card": "بطاقة",
            "Mixed": "مختلط",
            "Credit": "آجل",
        }
        return labels.get(method, method or "-")

    def _build_items_to_return(self):
        items_to_return = []
        for row in range(self.items_table.rowCount()):
            widget = self.items_table.cellWidget(row, 3)
            spin = (
                widget
                if isinstance(widget, QSpinBox)
                else widget.findChild(QSpinBox) if widget else None
            )
            if not spin:
                continue
            qty = spin.value()
            if qty > 0:
                name_item = self.items_table.item(row, 0)
                items_to_return.append(
                    {
                        "product_id": name_item.data(Qt.ItemDataRole.UserRole),
                        "invoice_item_id": name_item.data(Qt.ItemDataRole.UserRole + 2),
                        "product_name": name_item.text(),
                        "quantity": qty,
                        "unit_price": float(self.items_table.item(row, 1).text()),
                        "buy_price": float(
                            name_item.data(Qt.ItemDataRole.UserRole + 1) or 0
                        ),
                        "total_price": qty
                        * float(self.items_table.item(row, 1).text()),
                    }
                )
        return items_to_return

    def _update_summary(self):
        items = self._build_items_to_return()
        self.selected_total = sum(item["total_price"] for item in items)
        available_count = 0
        for row in range(self.items_table.rowCount()):
            widget = self.items_table.cellWidget(row, 3)
            spin = (
                widget
                if isinstance(widget, QSpinBox)
                else widget.findChild(QSpinBox) if widget else None
            )
            if spin and spin.maximum() > 0:
                available_count += 1
        self.available_items_lbl.setText(str(available_count))
        self.selected_items_lbl.setText(str(len(items)))
        self.return_total_lbl.setText(self._format_money(self.selected_total))
        self.cash_refund_lbl.setText(
            self._format_money(self._estimate_cash_refund(self.selected_total))
        )

    def _has_returnable_items(self):
        for row in range(self.items_table.rowCount()):
            widget = self.items_table.cellWidget(row, 3)
            spin = widget.findChild(QSpinBox) if widget else None
            if spin and spin.maximum() > 0:
                return True
        return False

    def _estimate_cash_refund(self, total_return: float) -> float:
        if not self.current_invoice:
            return 0.0
        payment_method = (self.current_invoice.get("payment_method") or "").lower()
        cash_amount = float(self.current_invoice.get("cash_amount") or 0)
        remaining_amount = float(self.current_invoice.get("remaining_amount") or 0)
        credit_adjustment = (
            min(total_return, remaining_amount) if remaining_amount > 0 else 0.0
        )
        refundable = max(0.0, total_return - credit_adjustment)
        if payment_method == "card":
            return 0.0
        if cash_amount > 0:
            return min(refundable, cash_amount)
        if payment_method in ("cash", "mixed"):
            return refundable
        return 0.0

    def _process_return(self):
        if not self.current_invoice:
            return

        items_to_return = self._build_items_to_return()
        if not items_to_return:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد كميات للمرتجع")
            return

        reason = self.reason_input.text().strip()
        user_id = self.user.get("id", 1)
        store_id = self.current_invoice.get("store_id", self.user.get("store_id", 1))

        # Check drawer
        drawer_id = None
        try:
            status = self.ctrl.get_drawer_status(user_id)
        except Exception as exc:
            logger.error("Error checking cashier drawer: %s", exc, exc_info=True)
            QMessageBox.critical(self, "خطأ", "تعذر التحقق من حالة درج الكاشير")
            return
        if status and status.get("is_open"):
            drawer_id = status["id"]
        else:
            if not PermissionPolicy(self.user).can_use_shared_drawer():
                QMessageBox.warning(
                    self, "تنبيه", "يجب فتح درجك الخاص قبل تنفيذ المرتجع"
                )
                return
            try:
                store_drawer = self.ctrl.get_store_open_drawer(store_id)
            except Exception as exc:
                logger.error("Error checking shared drawer: %s", exc, exc_info=True)
                QMessageBox.critical(self, "خطأ", "تعذر التحقق من درج الفرع")
                return
            if store_drawer:
                drawer_id = store_drawer["id"]
            else:
                QMessageBox.warning(self, "تنبيه", "لا يوجد درج كاشير مفتوح!")
                return

        try:
            result = self.ctrl.process_return(
                self.current_invoice["id"],
                items_to_return,
                reason,
                user_id,
                store_id,
                drawer_id,
            )
        except Exception as exc:
            logger.error("Error processing return: %s", exc, exc_info=True)
            result = None

        if result:
            if isinstance(result, dict):
                ret_num = result.get("return_number")
                total_amount = result.get("total_amount", self.selected_total)
                result_items = result.get("items", items_to_return)
            else:
                ret_num = result
                total_amount = self.selected_total
                result_items = items_to_return

            if self.print_pdf_chk.isChecked():
                self._save_return_pdf(ret_num, total_amount, reason, result_items)
            else:
                return_data = {
                    "return_number": ret_num,
                    "invoice_number": self.current_invoice.get("invoice_number", ""),
                    "total_amount": float(total_amount or 0),
                    "reason": reason or "-",
                }
                self.last_return_items = result_items
                self._offer_whatsapp_return_share(return_data, None)

            QMessageBox.information(
                self,
                "نجاح",
                f"تمت عملية المرتجع بنجاح\nرقم المرتجع: {ret_num}\nالإجمالي: {self._format_money(total_amount)}",
            )
            self.return_processed.emit()
            self._clear_page()
        else:
            reason = (
                self.ctrl.get_last_return_error()
                if hasattr(self.ctrl, "get_last_return_error")
                else ""
            )
            QMessageBox.critical(self, "خطأ", reason or "فشلت عملية المرتجع")

    def _save_return_pdf(
        self, return_number: str, total_amount: float, reason: str, items: list
    ):
        return_data = {
            "return_number": return_number,
            "invoice_number": self.current_invoice.get("invoice_number", ""),
            "total_amount": float(total_amount or 0),
            "reason": reason or "-",
        }
        user_name = self.user.get("name") or self.user.get("username") or "مستخدم"
        result = None
        self.last_return_items = items
        try:
            result = PrinterService.save_return_as_pdf(return_data, items, user_name)
        except Exception as exc:
            logger.error(f"Error saving return PDF: {exc}", exc_info=True)
            QMessageBox.warning(
                self, "تنبيه", f"تم حفظ المرتجع، لكن فشل حفظ إيصال PDF:\n{exc}"
            )
        self._offer_whatsapp_return_share(return_data, result)

    def _offer_whatsapp_return_share(self, return_data: dict, pdf_result):
        phone = str((self.current_invoice or {}).get("customer_phone") or "").strip()
        if not phone:
            return
        reply = QMessageBox.question(
            self,
            "إرسال واتساب",
            "هل تريد تجهيز إيصال المرتجع للإرسال عبر واتساب؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        result = WhatsAppShareService().prepare_text_share(
            phone,
            self._format_return_whatsapp_message(
                return_data, getattr(self, "last_return_items", [])
            ),
        )
        if result.error:
            QMessageBox.warning(self, "واتساب", result.error)
            return
        QMessageBox.information(
            self,
            "واتساب",
            "تم فتح واتساب وتجهيز بيانات المرتجع كنص منسق.\n"
            "راجع الرسالة ثم اضغط إرسال.",
        )

    def _format_return_whatsapp_message(self, return_data: dict, items: list) -> str:
        def money(value):
            try:
                return f"{float(value or 0):,.2f}"
            except (TypeError, ValueError):
                return "0.00"

        invoice = self.current_invoice or {}
        lines = [
            "↩️ *إيصال مرتجع بيع*",
            "━━━━━━━━━━━━",
            f"رقم المرتجع: {return_data.get('return_number', '-')}",
            f"فاتورة الأصل: {return_data.get('invoice_number') or invoice.get('invoice_number') or '-'}",
            f"العميل: {invoice.get('customer_name') or 'عميل نقدي'}",
            f"سبب المرتجع: {return_data.get('reason', '-')}",
            "",
            "📦 *الأصناف المرتجعة*",
            "━━━━━━━━━━━━",
        ]
        for index, item in enumerate(items or [], 1):
            name = item.get("product_name") or item.get("name") or "صنف"
            qty = item.get("quantity", 0)
            price = item.get("unit_price", item.get("price", 0))
            total = item.get(
                "total_price", item.get("total", float(qty or 0) * float(price or 0))
            )
            lines.extend(
                [
                    f"*{index}) {name}*",
                    f"الكمية المرتجعة: {qty}",
                    f"السعر: {money(price)} ج.م",
                    f"الإجمالي: {money(total)} ج.م",
                    "────────────",
                ]
            )
        lines.extend(
            [
                "",
                "💰 *ملخص المرتجع*",
                "━━━━━━━━━━━━",
                f"*إجمالي المرتجع: {money(return_data.get('total_amount', 0))} ج.م*",
            ]
        )
        return "\n".join(lines)

    def _clear_page(self):
        self.search_input.clear()
        self.reason_input.clear()
        self._clear_invoice_result()

    def _clear_invoice_result(self):
        self.lbl_date.setText("-")
        self.lbl_customer.setText("-")
        self.lbl_total.setText("-")
        self.lbl_payment.setText("-")
        self.lbl_status.setText("-")
        self.items_table.setRowCount(0)
        self.info_group.hide()
        self.process_btn.setEnabled(False)
        self.current_invoice = None
        self._update_summary()

    def _show_history(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("سجل المرتجعات")
        dialog.resize(800, 500)
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)

        # Filters
        f_layout = QHBoxLayout()
        f_layout.addWidget(QLabel("من:"))
        start = QDateEdit(QDate.currentDate().addMonths(-1))
        start.setCalendarPopup(True)
        start.setStyleSheet(INPUT_STYLE)
        f_layout.addWidget(start)
        f_layout.addWidget(QLabel("إلى:"))
        end = QDateEdit(QDate.currentDate())
        end.setCalendarPopup(True)
        end.setStyleSheet(INPUT_STYLE)
        f_layout.addWidget(end)

        search_btn = QPushButton("🔎 بحث")
        search_btn.setStyleSheet(get_button_style("info"))
        f_layout.addWidget(search_btn)
        layout.addLayout(f_layout)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(
            ["رقم المرتجع", "التاريخ", "الكاشير", "المبلغ", "السبب"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(table, TABLE_STYLE, row_height=44)
        layout.addWidget(table)

        def load():
            s = start.date().toString("yyyy-MM-dd")
            e = end.date().toString("yyyy-MM-dd")
            if s > e:
                QMessageBox.warning(
                    dialog, "تنبيه", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية"
                )
                return
            store_id = self.user.get("store_id")
            try:
                history = self.ctrl.get_returns_history(
                    store_id=store_id, start_date=s, end_date=e
                )
            except Exception as exc:
                logger.error("Error loading returns history: %s", exc, exc_info=True)
                table.setRowCount(0)
                QMessageBox.critical(dialog, "خطأ", "تعذر تحميل سجل المرتجعات")
                return
            table.setRowCount(len(history))
            for i, r in enumerate(history):
                table.setItem(i, 0, self._table_item(str(r.get("return_number", ""))))
                table.setItem(i, 1, self._table_item(str(r.get("return_date", ""))))
                table.setItem(i, 2, self._table_item(r.get("cashier_name", "")))
                table.setItem(
                    i,
                    3,
                    self._table_item(f"{abs(float(r.get('total_amount', 0))):.2f}"),
                )
                table.setItem(i, 4, self._table_item(r.get("reason", "") or ""))

        search_btn.clicked.connect(load)
        load()

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet(get_button_style("secondary"))
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()
