from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from application.services.license_service import LicenseService
from ui.styles import COLORS, INPUT_STYLE, get_button_style


class ActivationView(QWidget):
    activation_success = pyqtSignal()

    def __init__(self, service: LicenseService, parent=None):
        super().__init__(parent)
        self.service = service
        self.hw_id = service.hardware_id
        self._init_ui()

    def _init_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {COLORS['bg_app']};
                color: {COLORS['text_primary']};
            }}
            """
        )

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(20, 20, 20, 20)

        panel = QFrame()
        panel.setFixedWidth(560)
        panel.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['border']};
                border-radius: 22px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 10)
        panel.setGraphicsEffect(shadow)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(14)

        title = QLabel("تفعيل نسخة البرنامج")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Tahoma", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_on_brand']};")
        layout.addWidget(title)

        subtitle = QLabel("هذه النسخة مرتبطة بجهاز واحد. أرسل كود الجهاز للمطور ثم أدخل مفتاح التفعيل.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        layout.addWidget(subtitle)

        layout.addWidget(self._label("كود الجهاز"))
        self.hw_id_display = QLineEdit(self.hw_id)
        self.hw_id_display.setReadOnly(True)
        self.hw_id_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hw_id_display.setStyleSheet(INPUT_STYLE)
        layout.addWidget(self.hw_id_display)

        copy_btn = QPushButton("نسخ كود الجهاز")
        copy_btn.setStyleSheet(get_button_style("outline"))
        copy_btn.clicked.connect(self._copy_hardware_id)
        layout.addWidget(copy_btn)

        layout.addWidget(self._label("مفتاح التفعيل"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_input.setStyleSheet(INPUT_STYLE)
        self.key_input.returnPressed.connect(self._activate)
        layout.addWidget(self.key_input)

        activate_btn = QPushButton("تفعيل الآن")
        activate_btn.setStyleSheet(get_button_style("primary"))
        activate_btn.clicked.connect(self._activate)
        layout.addWidget(activate_btn)

        note = QLabel("لن يعمل البرنامج على جهاز آخر إلا بمفتاح تفعيل خاص بهذا الجهاز.")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(note)

        root.addWidget(panel)

    def _label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignRight)
        label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 900;")
        return label

    def _copy_hardware_id(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.hw_id)
        QMessageBox.information(self, "تم", "تم نسخ كود الجهاز.")

    def _activate(self):
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "تنبيه", "أدخل مفتاح التفعيل أولًا.")
            return
        if self.service.activate(key):
            QMessageBox.information(self, "تم", "تم تفعيل النسخة بنجاح.")
            self.activation_success.emit()
            return
        QMessageBox.critical(self, "فشل", "مفتاح التفعيل غير صحيح لهذا الجهاز.")
