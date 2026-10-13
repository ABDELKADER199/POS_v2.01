"""
Settings View - واجهة الإعدادات (Clean Architecture)
إعدادات النظام الأساسية.
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QFrame, QMessageBox, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ui.styles import (
    GLOBAL_STYLE,
    COLORS,
    THEME_MODES,
    apply_theme_mode,
    get_button_style,
    load_theme_preference,
)
from application.services.settings_service_facade import SettingsServiceFacade

logger = logging.getLogger(__name__)


class SettingsView(QWidget):
    """واجهة الإعدادات."""

    theme_changed = pyqtSignal(str)

    def __init__(self, user_info: dict, parent=None):
        super().__init__(parent)
        self.user_info = user_info
        self.settings_service = SettingsServiceFacade()
        self.setStyleSheet(GLOBAL_STYLE)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("⚙️ إعدادات النظام")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        # Store Info Card
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background-color: {COLORS['bg_panel']}; border-radius: 12px; padding: 20px; border: 1px solid {COLORS['border']}; }}
        """)
        card_layout = QVBoxLayout(card)

        card_title = QLabel("📋 معلومات المتجر")
        card_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        card_title.setStyleSheet(f"color: {COLORS['accent']};")
        card_layout.addWidget(card_title)

        form = QFormLayout()
        form.setSpacing(15)

        self.store_name = QLineEdit()
        self.store_phone = QLineEdit()
        self.store_address = QLineEdit()
        self.tax_number = QLineEdit()
        self.receipt_footer = QLineEdit()
        self.theme_mode = QComboBox()
        self.theme_mode.addItem(THEME_MODES["dark"], "dark")
        self.theme_mode.addItem(THEME_MODES["light"], "light")

        for inp in [self.store_name, self.store_phone, self.store_address, self.tax_number, self.receipt_footer, self.theme_mode]:
            inp.setStyleSheet(f"min-height: 40px; font-size: 14px; background-color: {COLORS['bg_input']}; color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 5px 10px;")

        form.addRow("اسم المتجر:", self.store_name)
        form.addRow("الهاتف:", self.store_phone)
        form.addRow("العنوان:", self.store_address)
        form.addRow("الرقم الضريبي:", self.tax_number)
        form.addRow("تذييل الإيصال:", self.receipt_footer)
        form.addRow("مظهر التطبيق:", self.theme_mode)
        card_layout.addLayout(form)

        save_btn = QPushButton("💾 حفظ الإعدادات")
        save_btn.setStyleSheet(get_button_style('success') + " min-height: 45px; font-size: 15px;")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_settings)
        card_layout.addWidget(save_btn)

        layout.addWidget(card)
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _load_settings(self):
        try:
            s = self.settings_service.get_all()
            self.store_name.setText(s.get('store_name', ''))
            self.store_phone.setText(s.get('store_phone', ''))
            self.store_address.setText(s.get('store_address', ''))
            self.tax_number.setText(s.get('tax_number', ''))
            self.receipt_footer.setText(s.get('receipt_footer', ''))
            theme_mode = s.get("ui_theme_mode") or load_theme_preference()
            index = self.theme_mode.findData(theme_mode)
            self.theme_mode.setCurrentIndex(index if index >= 0 else 0)
        except Exception as e:
            logger.warning(f"Could not load settings: {e}")

    def _save_settings(self):
        try:
            pairs = {
                'store_name': self.store_name.text(),
                'store_phone': self.store_phone.text(),
                'store_address': self.store_address.text(),
                'tax_number': self.tax_number.text(),
                'receipt_footer': self.receipt_footer.text(),
                'ui_theme_mode': self.theme_mode.currentData() or 'dark',
            }
            self.settings_service.update_many(pairs)
            selected_theme = apply_theme_mode(pairs["ui_theme_mode"])
            self.theme_changed.emit(selected_theme)
            QMessageBox.information(
                self,
                "نجاح",
                "تم حفظ الإعدادات بنجاح.\n"
                "سيتم تطبيق المظهر المختار بالكامل بعد إعادة فتح التطبيق.",
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل حفظ الإعدادات: {e}")
