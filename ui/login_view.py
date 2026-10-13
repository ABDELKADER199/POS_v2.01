"""
Login View - old app visual design, modern controller wiring.
Arabic strings are stored as unicode escapes to avoid Windows encoding damage.
"""
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton,
    QFrame, QCheckBox, QGraphicsDropShadowEffect, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from controllers.auth_controller import AuthController


class LoginView(QWidget):
    login_success = pyqtSignal(dict)

    def __init__(self, controller: AuthController, parent=None):
        super().__init__(parent)
        self.ctrl = controller
        self._init_ui()

    def _arabic_date_parts(self):
        now = datetime.now()
        days = [
            "\u0627\u0644\u0625\u062b\u0646\u064a\u0646",
            "\u0627\u0644\u062b\u0644\u0627\u062b\u0627\u0621",
            "\u0627\u0644\u0623\u0631\u0628\u0639\u0627\u0621",
            "\u0627\u0644\u062e\u0645\u064a\u0633",
            "\u0627\u0644\u062c\u0645\u0639\u0629",
            "\u0627\u0644\u0633\u0628\u062a",
            "\u0627\u0644\u0623\u062d\u062f",
        ]
        months = [
            "\u064a\u0646\u0627\u064a\u0631",
            "\u0641\u0628\u0631\u0627\u064a\u0631",
            "\u0645\u0627\u0631\u0633",
            "\u0623\u0628\u0631\u064a\u0644",
            "\u0645\u0627\u064a\u0648",
            "\u064a\u0648\u0646\u064a\u0648",
            "\u064a\u0648\u0644\u064a\u0648",
            "\u0623\u063a\u0633\u0637\u0633",
            "\u0633\u0628\u062a\u0645\u0628\u0631",
            "\u0623\u0643\u062a\u0648\u0628\u0631",
            "\u0646\u0648\u0641\u0645\u0628\u0631",
            "\u062f\u064a\u0633\u0645\u0628\u0631",
        ]
        return days[now.weekday()], f"{now.day:02d} {months[now.month - 1]} {now.year}"

    def _init_ui(self):
        self.setObjectName("loginPage")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("""
            QWidget#loginPage {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #0B1220,
                    stop: 0.45 #10203F,
                    stop: 1 #091326
                );
            }
            QFrame#authShell {
                background-color: rgba(7, 13, 26, 0.82);
                border: 1px solid rgba(125, 167, 255, 0.25);
                border-radius: 26px;
            }
            QFrame#heroPanel {
                border-radius: 22px;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #1D4ED8,
                    stop: 0.55 #0E3A89,
                    stop: 1 #08224F
                );
            }
            QLabel#heroBadge {
                background: rgba(255, 255, 255, 0.16);
                border: 1px solid rgba(255, 255, 255, 0.25);
                color: #F8FAFC;
                font-size: 26px;
                font-weight: 900;
                border-radius: 18px;
                padding: 10px 16px;
            }
            QFrame#dateCard {
                background: rgba(3, 7, 18, 0.30);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 22px;
            }
            QLabel#dayName {
                color: {COLORS['text_on_brand']};
                font-family: "Cairo", "Tajawal", "Tahoma";
                font-size: 42px;
                font-weight: 900;
                background: transparent;
            }
            QLabel#dateLine {
                color: #BFDBFE;
                font-family: "Cairo", "Tajawal", "Tahoma";
                font-size: 18px;
                font-weight: 800;
                background: transparent;
            }
            QLabel#heroTitle {
                color: {COLORS['text_on_brand']};
                font-family: "Cairo", "Tajawal", "Tahoma";
                font-size: 24px;
                font-weight: 900;
                background: transparent;
            }
            QLabel#heroSubtitle {
                color: #DBEAFE;
                font-size: 13px;
                background: transparent;
            }
            QLabel#heroFeature {
                background: rgba(255, 255, 255, 0.12);
                color: #EFF6FF;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 12px;
                padding: 9px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QFrame#formPanel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #F8FAFC,
                    stop: 0.48 #EEF6FF,
                    stop: 1 #E0ECFF
                );
                border: 1px solid rgba(255, 255, 255, 0.85);
                border-radius: 22px;
            }
            QLabel#helloWatermark {
                color: rgba(37, 99, 235, 0.18);
                font-size: 86px;
                font-weight: 900;
                letter-spacing: 2px;
                background: transparent;
            }
            QFrame#formContent {
                background: rgba(255, 255, 255, 0.54);
                border: 1px solid rgba(255, 255, 255, 0.42);
                border-radius: 18px;
            }
            QLabel#formTitle {
                color: #0F172A;
                font-family: "Cairo", "Tajawal", "Tahoma";
                font-size: 25px;
                font-weight: 900;
                background: transparent;
            }
            QLabel#formSubtitle {
                color: #475569;
                font-size: 12px;
                background: transparent;
            }
            QLabel#fieldLabel {
                color: #334155;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
            QLabel#statusHint {
                color: #64748B;
                font-size: 12px;
                background: transparent;
                border: none;
            }
            QLineEdit {
                border: 1px solid rgba(37, 99, 235, 0.20);
                border-radius: 14px;
                padding: 12px 14px;
                background-color: rgba(248, 250, 252, 0.92);
                color: #0F172A;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #2563EB;
                background-color: {COLORS['bg_input']};
            }
            QCheckBox {
                color: #334155;
                font-size: 12px;
                spacing: 8px;
                padding-right: 2px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #94A3B8;
                background: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background: #2563EB;
                border-color: #2563EB;
            }
            QPushButton#loginButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #2563EB,
                    stop: 0.52 #1D4ED8,
                    stop: 1 #0F766E
                );
                color: {COLORS['text_on_brand']};
                border: none;
                border-radius: 14px;
                font-size: 13px;
                font-weight: 900;
                min-height: 50px;
            }
            QPushButton#loginButton:hover { background-color: #1D4ED8; }
            QPushButton#loginButton:pressed { background-color: #1E40AF; }
            QPushButton#loginButton:disabled {
                background-color: #9CA3AF;
                color: #E5E7EB;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)

        shell = QFrame()
        shell.setObjectName("authShell")
        shell.setFixedSize(980, 610)
        shell.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(55)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 190))
        shell.setGraphicsEffect(shadow)

        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(12, 12, 12, 12)
        shell_layout.setSpacing(12)

        hero_panel = QFrame()
        hero_panel.setObjectName("heroPanel")
        hero_panel.setFixedWidth(300)
        hero_layout = QVBoxLayout(hero_panel)
        hero_layout.setContentsMargins(24, 24, 24, 22)
        hero_layout.setSpacing(10)

        hero_badge = QLabel("HELLO POS")
        hero_badge.setObjectName("heroBadge")
        hero_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_badge.setFixedWidth(250)
        hero_layout.addWidget(hero_badge, alignment=Qt.AlignmentFlag.AlignRight)

        day_name, date_line = self._arabic_date_parts()
        date_card = QFrame()
        date_card.setObjectName("dateCard")
        date_layout = QVBoxLayout(date_card)
        date_layout.setContentsMargins(16, 16, 16, 14)
        date_layout.setSpacing(2)

        day_label = QLabel(day_name)
        day_label.setObjectName("dayName")
        day_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        day_label.setFont(QFont("Cairo", 34, QFont.Weight.Black))
        date_layout.addWidget(day_label)

        date_label = QLabel(date_line)
        date_label.setObjectName("dateLine")
        date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        date_label.setFont(QFont("Cairo", 16, QFont.Weight.Bold))
        date_layout.addWidget(date_label)
        hero_layout.addWidget(date_card)

        hero_title = QLabel("\u0646\u0638\u0627\u0645 \u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0645\u0628\u064a\u0639\u0627\u062a")
        hero_title.setObjectName("heroTitle")
        hero_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        hero_layout.addWidget(hero_title)

        hero_subtitle = QLabel(
            "\u0648\u0635\u0648\u0644 \u0622\u0645\u0646 \u0648\u0633\u0631\u064a\u0639 \u0625\u0644\u0649 "
            "\u0644\u0648\u062d\u0629 \u0627\u0644\u062a\u062d\u0643\u0645\u060c "
            "\u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a\u060c "
            "\u0627\u0644\u0641\u0648\u0627\u062a\u064a\u0631\u060c "
            "\u0648\u0627\u0644\u0625\u062d\u0635\u0627\u0626\u064a\u0627\u062a "
            "\u0627\u0644\u064a\u0648\u0645\u064a\u0629."
        )
        hero_subtitle.setObjectName("heroSubtitle")
        hero_subtitle.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        hero_subtitle.setWordWrap(True)
        hero_layout.addWidget(hero_subtitle)

        for text in [
            "\u062d\u0645\u0627\u064a\u0629 \u0627\u0644\u062f\u062e\u0648\u0644 "
            "\u0628\u0627\u0644\u0628\u0635\u0645\u0629 \u0627\u0644\u0631\u0642\u0645\u064a\u0629 "
            "\u0644\u0644\u062c\u0647\u0627\u0632",
            "\u062a\u062f\u0642\u064a\u0642 \u0645\u062d\u0627\u0648\u0644\u0627\u062a "
            "\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644 "
            "\u0644\u062d\u0638\u064a\u0627\u064b",
            "\u0625\u062f\u0627\u0631\u0629 \u0645\u062a\u0639\u062f\u062f\u0629 "
            "\u0627\u0644\u0641\u0631\u0648\u0639 \u0636\u0645\u0646 "
            "\u0648\u0627\u062c\u0647\u0629 \u0648\u0627\u062d\u062f\u0629",
        ]:
            feature = QLabel(f"\u2022 {text}")
            feature.setObjectName("heroFeature")
            feature.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            hero_layout.addWidget(feature)
        hero_layout.addStretch()

        form_panel = QFrame()
        form_panel.setObjectName("formPanel")
        form_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_outer_layout = QGridLayout(form_panel)
        form_outer_layout.setContentsMargins(16, 16, 16, 16)
        form_outer_layout.setSpacing(0)

        hello_watermark = QLabel("HELLO\nPOS")
        hello_watermark.setObjectName("helloWatermark")
        hello_watermark.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form_outer_layout.addWidget(hello_watermark, 0, 0)

        form_content = QFrame()
        form_content.setObjectName("formContent")
        form_content.setMinimumWidth(420)
        form_content.setMaximumWidth(480)
        form_content.setMaximumHeight(510)
        form_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        form_layout = QVBoxLayout(form_content)
        form_layout.setContentsMargins(30, 24, 30, 22)
        form_layout.setSpacing(8)

        form_title = QLabel("\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644")
        form_title.setObjectName("formTitle")
        form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(form_title)

        form_subtitle = QLabel(
            "\u0623\u062f\u062e\u0644 \u0628\u0631\u064a\u062f\u0643 "
            "\u0648\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631 "
            "\u0644\u0644\u0645\u062a\u0627\u0628\u0639\u0629"
        )
        form_subtitle.setObjectName("formSubtitle")
        form_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(form_subtitle)
        form_layout.addSpacing(4)

        email_label = QLabel("\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a")
        email_label.setObjectName("fieldLabel")
        email_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(email_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("name@example.com")
        self.username_input.setFont(QFont("Tahoma", 11))
        self.username_input.setMinimumHeight(48)
        self.username_input.setMaximumWidth(420)
        self.username_input.returnPressed.connect(self._on_login)
        form_layout.addWidget(self.username_input)

        password_label = QLabel("\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631")
        password_label.setObjectName("fieldLabel")
        password_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("\u0623\u062f\u062e\u0644 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFont(QFont("Tahoma", 11))
        self.password_input.setMinimumHeight(48)
        self.password_input.setMaximumWidth(420)
        self.password_input.returnPressed.connect(self._on_login)
        form_layout.addWidget(self.password_input)

        self.show_password_check = QCheckBox("\u0625\u0638\u0647\u0627\u0631 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631")
        self.show_password_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_password_check.stateChanged.connect(self._toggle_password_visibility)
        form_layout.addWidget(self.show_password_check)

        self.error_label = QLabel("\u0623\u062f\u062e\u0644 \u0628\u064a\u0627\u0646\u0627\u062a\u0643 \u0644\u0644\u0645\u062a\u0627\u0628\u0639\u0629 \u0628\u0634\u0643\u0644 \u0622\u0645\u0646")
        self.error_label.setObjectName("statusHint")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.error_label)

        self.login_btn = QPushButton("\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644")
        self.login_btn.setObjectName("loginButton")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setFont(QFont("Tahoma", 12, QFont.Weight.Bold))
        self.login_btn.setMaximumWidth(420)
        self.login_btn.clicked.connect(self._on_login)
        form_layout.addWidget(self.login_btn)

        helper = QLabel(
            "\u064a\u062a\u0645 \u0627\u0644\u062a\u062d\u0642\u0642 \u0645\u0646 "
            "\u0627\u0644\u062d\u0633\u0627\u0628 \u0648\u0627\u0644\u0635\u0644\u0627\u062d\u064a\u0627\u062a "
            "\u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b \u0644\u062d\u0645\u0627\u064a\u0629 "
            "\u0627\u0644\u0646\u0638\u0627\u0645"
        )
        helper.setAlignment(Qt.AlignmentFlag.AlignCenter)
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 2px;")
        form_layout.addWidget(helper)

        form_outer_layout.addWidget(form_content, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)

        shell_layout.addWidget(hero_panel)
        shell_layout.addWidget(form_panel, 1)
        main_layout.addWidget(shell)

    def _toggle_password_visibility(self):
        if self.show_password_check.isChecked():
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

    def _set_login_busy(self, busy: bool):
        self.login_btn.setEnabled(not busy)
        self.login_btn.setText(
            "\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u062d\u0642\u0642..."
            if busy else
            "\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644"
        )

    def _show_status(self, message: str, is_error: bool = False):
        self.error_label.setText(message)
        color = "#DC2626" if is_error else "#64748B"
        self.error_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self._show_status(
                "\u064a\u0631\u062c\u0649 \u0625\u062f\u062e\u0627\u0644 "
                "\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a "
                "\u0648\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631",
                True,
            )
            return

        self._set_login_busy(True)
        try:
            user = self.ctrl.login(username, password)
        finally:
            self._set_login_busy(False)

        if user:
            self._show_status(
                "\u062a\u0645 \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644 \u0628\u0646\u062c\u0627\u062d",
                False,
            )
            self.login_success.emit(user.to_dict())
        else:
            self._show_status(
                "\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u062f\u062e\u0648\u0644 \u063a\u064a\u0631 \u0635\u062d\u064a\u062d\u0629",
                True,
            )
            self.password_input.clear()
            self.password_input.setFocus()
