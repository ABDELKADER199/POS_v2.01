"""
Drawer View - واجهة إدارة الدرج النقدي (Clean Architecture)
مطابقة للنظام القديم لكن تعتمد فقط على DrawerController
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QFrame, QInputDialog, QDialog, QFormLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QDateEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QColor, QShortcut, QKeySequence

from ui.styles import GLOBAL_STYLE, COLORS
from ui.form_helpers import action_row, configure_form_layout, numeric_text, style_dialog, style_form_controls
from controllers.drawer_controller import DrawerController
from utils.printer_service import PrinterService
from utils.permissions import PermissionPolicy

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
#  Closed Drawers History Dialog
# ═══════════════════════════════════════════════════════
class ClosedDrawersDialog(QDialog):
    """حوار سجل الأدراج المغلقة"""

    def __init__(self, ctrl: DrawerController, store_id: int, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.store_id = store_id
        self.setWindowTitle("سجل الأدراج المغلقة")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(GLOBAL_STYLE + f"""
            QDialog {{ background-color: {COLORS['bg_panel']}; }}
            QLabel {{ color: {COLORS['text_on_brand']}; }}
        """)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QHBoxLayout()
        icon = QLabel("🗄️")
        icon.setFont(QFont("Segoe UI Emoji", 24))
        header.addWidget(icon)
        title = QLabel("سجل إغلاق الأدراج")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_on_brand']};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("📅 من:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("📅 إلى:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.date_to)

        filter_layout.addSpacing(20)
        filter_layout.addWidget(QLabel("🔍 بحث:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("اسم الكاشير...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._filter_table)
        filter_layout.addWidget(self.search_input)

        reload_btn = QPushButton("🔄 تحديث البيانات")
        reload_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['success']}; color: {COLORS['text_on_brand']}; padding: 5px 15px; border-radius: 4px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
        """)
        reload_btn.clicked.connect(self._load_data)
        filter_layout.addWidget(reload_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["#", "الكاشير", "وقت الإغلاق", "الرصيد الفعلي", "الرصيد المتوقع", "العجز/الزيادة", "إجراءات"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 120)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {COLORS['bg_elevated']}; border: 1px solid {COLORS['border']}; border-radius: 12px; color: {COLORS['text_on_brand']}; selection-background-color: {COLORS['primary']}; }}
            QHeaderView::section {{ background-color: {COLORS['text_dark']}; color: {COLORS['border_soft']}; padding: 12px; border: none; font-weight: bold; }}
            QTableWidget::item {{ padding: 10px; border-bottom: 1px solid {COLORS['border']}; }}
        """)
        layout.addWidget(self.table)

        # Close
        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet(f"QPushButton {{ background-color: {COLORS['danger']}; color: {COLORS['text_on_brand']}; padding: 10px 24px; border-radius: 8px; font-weight: bold; }}")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignLeft)

    def _load_data(self):
        start = self.date_from.date().toString("yyyy-MM-dd")
        end = self.date_to.date().toString("yyyy-MM-dd")
        drawers = self.ctrl.get_closed_drawers_history(self.store_id, start, end)

        self.table.setRowCount(len(drawers))
        for row, d in enumerate(drawers):
            opening = float(d.get('opening_balance', 0))
            closing = float(d.get('closing_balance', 0))
            cash_sales = float(d.get('cash_sales', 0) or 0)
            cash_returns = float(d.get('cash_returns', 0) or 0)
            expected = opening + cash_sales - cash_returns
            diff = closing - expected

            items = [
                str(d.get('id', '')),
                d.get('cashier_name', ''),
                str(d.get('closing_date', '')),
                f"{closing:,.2f}",
                f"{expected:,.2f}",
                f"{'+' if diff > 0 else ''}{diff:,.2f}",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 3:
                    item.setForeground(QColor(COLORS['success']))
                elif col == 5:
                    item.setForeground(QColor(COLORS['danger']) if diff < -0.01 else QColor(COLORS['success']) if diff > 0.01 else QColor(COLORS['text_muted']))
                self.table.setItem(row, col, item)

            print_btn = QPushButton("🖨️ طباعة")
            print_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: {COLORS['text_on_brand']};
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 6px;
                }}
                QPushButton:hover {{ background-color: {COLORS['primary_hover']}; }}
            """)
            print_btn.clicked.connect(lambda _, drawer_id=d.get('id'): self._print_drawer(drawer_id))
            self.table.setCellWidget(row, 6, print_btn)

    def _print_drawer(self, drawer_id: int):
        try:
            summary = self.ctrl.get_drawer_summary(drawer_id)
            if not summary:
                QMessageBox.warning(self, "خطأ", "تعذر جلب بيانات الدرج")
                return
            result = PrinterService.print_drawer_report(summary)
            if isinstance(result, dict) and result.get("saved") and not result.get("printed"):
                QMessageBox.information(self, "تم", "لا توجد طابعة متاحة، تم حفظ تقرير الدرج PDF")
            else:
                QMessageBox.information(self, "نجاح", "تم إرسال تقرير الدرج للطباعة")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الطباعة: {e}")

    def _filter_table(self):
        text = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            self.table.setRowHidden(row, text not in item.text().lower() if item else True)


# ═══════════════════════════════════════════════════════
#  Main Drawer View
# ═══════════════════════════════════════════════════════
class DrawerView(QWidget):
    """واجهة إدارة الدرج النقدي"""

    drawer_opened = pyqtSignal()
    drawer_closed = pyqtSignal()

    def __init__(self, ctrl: DrawerController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user_info = user_info
        self.setStyleSheet(GLOBAL_STYLE)
        self._init_ui()
        self.check_drawer_status()

        # Shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_F2), self).activated.connect(self._open_drawer)
        QShortcut(QKeySequence(Qt.Key.Key_F12), self).activated.connect(self._close_drawer)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Title
        title = QLabel("💰 إدارة الدرج النقدي")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Status Card
        self.status_card = QFrame()
        self.status_card.setStyleSheet(f"""
            QFrame {{ background-color: {COLORS['secondary']}; border-radius: 12px; padding: 15px; }}
        """)
        card_layout = QVBoxLayout(self.status_card)

        lbl = QLabel("حالة الدرج الحالي")
        lbl.setStyleSheet(f"color: {COLORS['text_on_brand']}; font-size: 14px;")
        card_layout.addWidget(lbl)

        self.status_label = QLabel("---")
        self.status_label.setStyleSheet(f"color: {COLORS['text_on_brand']}; font-size: 24px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)
        layout.addWidget(self.status_card)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_open = QPushButton("🔓 فتح الدرج (F2)")
        self.btn_open.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['success']}; color: {COLORS['text_on_brand']}; border: none; padding: 15px; border-radius: 8px; font-size: 16px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
        """)
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_drawer)
        btn_layout.addWidget(self.btn_open)

        self.btn_close = QPushButton("🔒 إغلاق الدرج (F12)")
        self.btn_close.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['danger']}; color: {COLORS['text_on_brand']}; border: none; padding: 15px; border-radius: 8px; font-size: 16px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {COLORS['danger_hover']}; }}
        """)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self._close_drawer)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        # History
        self.btn_history = QPushButton("🗄️ سجل الأدراج المغلقة")
        self.btn_history.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['primary']}; color: {COLORS['text_on_brand']}; border: none; padding: 15px; border-radius: 8px; font-size: 16px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {COLORS['hover']}; }}
        """)
        self.btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_history.clicked.connect(self._show_history)
        layout.addWidget(self.btn_history)

        layout.addStretch()
        self.btn_open.hide()
        self.btn_close.hide()
        self.btn_history.hide()

    def check_drawer_status(self):
        """فحص حالة الدرج وتحديث الواجهة"""
        try:
            store_id = self.user_info.get('store_id')
            user_id = self.user_info.get('id')
            policy = PermissionPolicy(self.user_info)

            # Show history for managers
            if policy.can_view_drawer_history():
                self.btn_history.show()
            else:
                self.btn_history.hide()

            store_status = self._get_shared_open_drawer(store_id)

            if store_status:
                opener = store_status.get('cashier_name', 'Unknown')
                opened_at = store_status.get('opened_at', '')
                store_name = store_status.get('store_name') or f"فرع {store_status.get('store_id', '')}"

                if store_status.get('cashier_id') == user_id:
                    self.status_label.setText(f"مفتوح لديك منذ {opened_at} - {store_name}")
                    self.status_card.setStyleSheet("QFrame { background-color: #10B981; border-radius: 12px; padding: 15px; }")
                    self.btn_open.hide()
                    self.btn_close.show()
                else:
                    self.status_label.setText(f"مفتوح بواسطة: {opener} - {store_name}")
                    self.status_card.setStyleSheet("QFrame { background-color: #F59E0B; border-radius: 12px; padding: 15px; }")
                    self.btn_open.hide()
                    self.btn_close.setVisible(policy.can_close_shared_drawer())
            else:
                self.status_label.setText("مغلق")
                self.status_card.setStyleSheet(f"QFrame {{ background-color: {COLORS['secondary']}; border-radius: 12px; padding: 15px; }}")
                self.btn_open.show()
                self.btn_close.hide()
        except Exception as e:
            logger.error(f"Error checking drawer status: {e}")

    def _can_use_any_branch_drawer(self) -> bool:
        policy = PermissionPolicy(self.user_info)
        return policy.is_admin or policy.is_developer

    def _get_shared_open_drawer(self, store_id: int = None):
        store_id = store_id or self.user_info.get('store_id')
        store_status = self.ctrl.get_store_open_drawer(store_id)
        if store_status:
            return store_status
        if self._can_use_any_branch_drawer() and hasattr(self.ctrl, 'get_any_open_drawer'):
            return self.ctrl.get_any_open_drawer()
        return None

    def _open_drawer(self):
        store_id = self.user_info.get('store_id')
        user_id = self.user_info.get('id')

        if not store_id:
            QMessageBox.warning(self, "تنبيه", "لا يوجد فرع مرتبط بهذا المستخدم")
            return

        existing = self._get_shared_open_drawer(store_id)
        if existing:
            store_name = existing.get('store_name') or f"فرع {existing.get('store_id', '')}"
            QMessageBox.warning(self, "تنبيه", f"يوجد درج مفتوح بالفعل بواسطة {existing.get('cashier_name')} في {store_name}. سيتم استخدامه كنقطة مشاركة.")
            self.check_drawer_status()
            return

        balance, ok = QInputDialog.getDouble(self, "فتح الدرج", "أدخل رصيد البداية (اختياري):", 0, 0, 1000000, 2)
        if ok:
            if self.ctrl.open_drawer(store_id, user_id, balance):
                QMessageBox.information(self, "نجاح", "تم فتح الدرج بنجاح")
                self.check_drawer_status()
                self.drawer_opened.emit()
            else:
                QMessageBox.critical(self, "خطأ", "فشل في فتح الدرج")

    def _close_drawer(self):
        status = self.ctrl.get_drawer_status(self.user_info.get('id'))
        if not status or not status.get('is_open'):
            store_status = self._get_shared_open_drawer(self.user_info.get('store_id'))
            if store_status and PermissionPolicy(self.user_info).can_close_shared_drawer():
                status = {
                    'id': store_status.get('id'),
                    'is_open': True,
                    'cashier_id': store_status.get('cashier_id'),
                    'store_id': store_status.get('store_id'),
                }
        if not status or not status.get('is_open'):
            return

        from ui.denomination_dialog import DenominationDialog
        dialog = DenominationDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        cash, card, details = dialog.get_results()

        if self.ctrl.close_drawer(
            status['id'],
            cash,
            details,
            self.user_info.get('id'),
            status.get('store_id') or self.user_info.get('store_id'),
        ):
            # Show summary after closure (blind comparison)
            summary = self.ctrl.get_drawer_summary(status['id'])
            if summary:
                opening = float(summary.get('opening_balance', 0))
                cash_sales = float(summary.get('cash_sales', 0) or 0)
                cash_returns = float(summary.get('cash_returns', 0) or 0)
                expected = opening + cash_sales - cash_returns
                diff = cash - expected
                diff_text = f"+{diff:,.2f}" if diff > 0 else f"{diff:,.2f}"
                diff_color = "green" if abs(diff) < 0.01 else ("red" if diff < 0 else "orange")
                QMessageBox.information(
                    self, "تم إغلاق الدرج بنجاح",
                    f"<b>ملخص الجرد:</b><br>"
                    f"الرصيد الافتتاحي: {opening:,.2f} ج.م<br>"
                    f"مبيعات كاش: {cash_sales:,.2f} ج.م<br>"
                    f"مرتجعات كاش: {cash_returns:,.2f} ج.م<br>"
                    f"<b>المتوقع: {expected:,.2f} ج.م</b><br>"
                    f"<b>الفعلي: {cash:,.2f} ج.م</b><br>"
                    f"<b style=\'color:{diff_color}\'>الفرق: {diff_text} ج.م</b>"
                )
            else:
                QMessageBox.information(self, "نجاح", "تم إغلاق الدرج بنجاح")
            self._print_closed_drawer(status['id'])
            self.check_drawer_status()
            self.drawer_closed.emit()
        else:
            QMessageBox.critical(self, "خطأ", "فشل في إغلاق الدرج")

    def _show_history(self):
        store_id = self.user_info.get('store_id')
        if store_id:
            dialog = ClosedDrawersDialog(self.ctrl, store_id, self)
            dialog.exec()

    def _print_closed_drawer(self, drawer_id: int):
        try:
            summary = self.ctrl.get_drawer_summary(drawer_id)
            if summary:
                PrinterService.print_drawer_report(summary)
        except Exception as e:
            logger.warning(f"Could not print drawer report: {e}")
