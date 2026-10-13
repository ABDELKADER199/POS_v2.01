from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from ui.styles import COLORS


class CustomerDisplayWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("شاشة عرض العميل")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(f"background-color: {COLORS['bg_app']}; color: {COLORS['text_primary']};")
        self._last_totals = None
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.setInterval(5000)
        self.idle_timer.timeout.connect(self.show_totals)
        self._init_ui()
        self.show_welcome()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        header = QLabel("HyperPOS")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 30, QFont.Weight.Black))
        header.setStyleSheet(f"color: {COLORS['text_on_brand']}; padding: 10px;")
        layout.addWidget(header)

        self.card = QFrame()
        self.card.setStyleSheet(
            f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border']}; "
            "border-radius: 24px;"
        )
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(18)

        self.mode_label = QLabel()
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.mode_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        card_layout.addWidget(self.mode_label)

        self.primary_label = QLabel()
        self.primary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.primary_label.setWordWrap(True)
        self.primary_label.setFont(QFont("Arial", 34, QFont.Weight.Black))
        self.primary_label.setStyleSheet(f"color: {COLORS['text_on_brand']};")
        card_layout.addWidget(self.primary_label, 2)

        self.secondary_label = QLabel()
        self.secondary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.secondary_label.setWordWrap(True)
        self.secondary_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.secondary_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        card_layout.addWidget(self.secondary_label)

        self.totals_frame = QFrame()
        self.totals_frame.setStyleSheet("background-color: transparent; border: none;")
        self.totals_grid = QGridLayout(self.totals_frame)
        self.totals_grid.setContentsMargins(0, 10, 0, 0)
        self.totals_grid.setHorizontalSpacing(16)
        self.totals_grid.setVerticalSpacing(12)
        card_layout.addWidget(self.totals_frame)

        layout.addWidget(self.card, 1)

        footer = QLabel("شكرًا لتسوقكم معنا")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        footer.setStyleSheet(f"color: {COLORS['success']};")
        layout.addWidget(footer)

    def open_on_customer_screen(self):
        screens = QApplication.screens()
        if len(screens) > 1:
            geometry = screens[-1].availableGeometry()
            self.setGeometry(geometry)
            self.showFullScreen()
        else:
            self.resize(900, 620)
            self.show()
        self.raise_()

    def show_welcome(self):
        self.idle_timer.stop()
        self._clear_totals()
        self.mode_label.setText("مرحبًا بك")
        self.primary_label.setText("جاهز لاستقبال الفاتورة")
        self.secondary_label.setText("ستظهر الأصناف والأسعار هنا أثناء البيع")

    def show_item(self, product_name: str, unit_price: float, quantity: int, line_total: float):
        self._clear_totals()
        self.mode_label.setText("تمت إضافة صنف")
        self.primary_label.setText(product_name or "صنف بدون اسم")
        self.secondary_label.setText(
            f"السعر: {self._money(unit_price)}   |   الكمية: {quantity}   |   الإجمالي: {self._money(line_total)}"
        )

    def schedule_totals(self, totals: dict):
        self._last_totals = totals or {}
        self.idle_timer.start()

    def show_totals(self):
        totals = self._last_totals or {}
        self._clear_totals()
        gross_total = float(totals.get("gross_total") or 0)
        manual_discount = float(totals.get("manual_discount") or 0)
        promo_discount = float(totals.get("promo_discount") or 0)
        discount_total = manual_discount + promo_discount
        final_total = float(totals.get("total") or 0)

        self.mode_label.setText("إجمالي الفاتورة")
        self.primary_label.setText(self._money(final_total))
        self.secondary_label.setText("يرجى مراجعة الإجمالي قبل الدفع")

        row = 0
        if discount_total > 0:
            self._add_total_row(row, "الإجمالي قبل الخصم", gross_total, COLORS["text_secondary"])
            row += 1
            self._add_total_row(row, "قيمة الخصم", discount_total, COLORS["warning"])
            row += 1
        self._add_total_row(row, "الإجمالي بعد الخصم", final_total, COLORS["success"])

    def reset(self):
        self._last_totals = None
        self.show_welcome()

    def _add_total_row(self, row: int, label: str, value: float, color: str):
        name = QLabel(label)
        name.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        name.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        name.setStyleSheet(f"color: {COLORS['text_primary']};")

        amount = QLabel(self._money(value))
        amount.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        amount.setFont(QFont("Arial", 24, QFont.Weight.Black))
        amount.setStyleSheet(f"color: {color};")

        self.totals_grid.addWidget(name, row, 0)
        self.totals_grid.addWidget(amount, row, 1)

    def _clear_totals(self):
        while self.totals_grid.count():
            item = self.totals_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _money(self, value: float) -> str:
        return f"{float(value or 0):,.2f} ج.م"
