"""
POS V2 - Main Application Entry Point
نقطة إقلاع التطبيق الرئيسية - تقوم بتكوين الـ Controllers وربط الـ Views
"""
import sys
import os
import logging

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from utils.app_logging import (
    install_exception_hooks,
    install_qt_message_handler,
    setup_application_logging,
)

ERROR_LOG_PATH = setup_application_logging(PROJECT_ROOT)
logger = logging.getLogger(__name__)
install_exception_hooks(logger)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QMessageBox, QFrame, QBoxLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFont, QShortcut, QKeySequence

install_qt_message_handler(logging.getLogger("qt"))

from ui.styles import COLORS, GLOBAL_STYLE, THEME_MODES

# Controllers
from controllers.auth_controller import AuthController
from controllers.backup_controller import BackupController
from controllers.cashier_controller import CashierController
from controllers.product_controller import ProductController
from controllers.stats_controller import StatsController
from controllers.drawer_controller import DrawerController
from controllers.admin_controller import AdminController
from controllers.returns_controller import ReturnsController
from controllers.purchases_controller import PurchasesController
from controllers.accounts_controller import AccountsController
from controllers.callcenter_controller import CallCenterController
from controllers.transfers_controller import TransfersController
from controllers.inventory_count_controller import InventoryCountController
from controllers.sync_controller import SyncController

# Views
from ui.login_view import LoginView
from ui.cashier_view import CashierView
from ui.product_view import ProductView
from ui.stats_view import StatsView
from ui.drawer_view import DrawerView
from ui.admin_view import AdminView
from ui.settings_view import SettingsView
from ui.returns_view import ReturnsView
from ui.purchases_view import PurchasesView
from ui.accounts_view import AccountsView
from ui.promotions_view import PromotionsView
from ui.callcenter_view import CallCenterView
from ui.inventory_count_view import InventoryCountView
from ui.activation_view import ActivationView
from application.services.license_service import LicenseService
from application.migration_runner import run_migrations_on_startup
from utils.permissions import PermissionPolicy


class MainWindow(QMainWindow):
    """النافذة الرئيسية - تدير التنقل بين الشاشات"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HyperPOS V2 - Clean Architecture")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.login_window_size = (980, 610)
        self.main_window_min_size = (1200, 750)
        self.setMinimumSize(*self.login_window_size)
        self.resize(*self.login_window_size)
        self.setStyleSheet(GLOBAL_STYLE)

        # Initialize Controllers
        self.auth_ctrl = AuthController()
        self.cashier_ctrl = CashierController()
        self.product_ctrl = ProductController()
        self.stats_ctrl = StatsController()
        self.drawer_ctrl = DrawerController()
        self.admin_ctrl = AdminController()
        self.returns_ctrl = ReturnsController()
        self.purchases_ctrl = PurchasesController()
        self.accounts_ctrl = AccountsController()
        self.callcenter_ctrl = CallCenterController()
        self.transfers_ctrl = TransfersController()
        self.inventory_count_ctrl = InventoryCountController()
        self.license_service = LicenseService()
        self.sync_ctrl = SyncController()
        self.backup_ctrl = BackupController()

        # Stacked Widget for Login/Main
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.activation_view = None
        if not self.license_service.is_activated():
            self.activation_view = ActivationView(self.license_service)
            self.activation_view.activation_success.connect(self._show_login_after_activation)
            self.stack.addWidget(self.activation_view)

        # Login Page
        self.login_view = LoginView(self.auth_ctrl)
        self.login_view.login_success.connect(self._on_login_success)
        self.stack.addWidget(self.login_view)
        if self.activation_view:
            self.stack.setCurrentWidget(self.activation_view)
        else:
            self.stack.setCurrentWidget(self.login_view)

        # Main Page (created after login)
        self.main_widget = None
        self.tabs = None
        self.content_stack = None
        self.body_container = None
        self.body_layout = None
        self.sidebar = None
        self.sidebar_expanded = False
        self.sidebar_width_expanded = 245
        self.sidebar_width_collapsed = 72
        self.sidebar_toggle_btn = None
        self.sidebar_title_label = None
        self.sidebar_user_label = None
        self.drawer_sidebar_label = None
        self.nav_buttons = {}
        self.nav_titles = {}
        self._tab_factories = {}
        self._tab_widgets = {}
        self._tab_keys = {}
        self._loading_tab = False
        self.nav_buttons = {}
        self.nav_titles = {}

    def showEvent(self, event):
        super().showEvent(event)
        if self.stack.currentWidget() in (self.login_view, self.activation_view) and not self.isMaximized():
            self._center_on_screen()

    def _prepare_login_window(self):
        self.showNormal()
        self.setMinimumSize(*self.login_window_size)
        self.setMaximumSize(*self.login_window_size)
        self.resize(*self.login_window_size)
        self._center_on_screen()

    def _show_login_after_activation(self):
        self.stack.setCurrentWidget(self.login_view)
        self._prepare_login_window()

    def _prepare_main_window(self):
        self.setMaximumSize(16777215, 16777215)
        self.setMinimumSize(*self.main_window_min_size)

    def _center_on_screen(self):
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _on_login_success(self, user_info: dict):
        """بعد تسجيل الدخول بنجاح"""
        logger.info(f"✅ Login: {user_info.get('full_name')} ({user_info.get('role')})")

        if self.main_widget:
            self.stack.removeWidget(self.main_widget)

        self.main_widget = self._build_main_ui(user_info)
        self.stack.addWidget(self.main_widget)
        self.stack.setCurrentWidget(self.main_widget)
        self._prepare_main_window()
        self.showMaximized()

        # بدء المزامنة في الخلفية بعد تسجيل الدخول
        if self.sync_ctrl.is_cloud_configured():
            # ربط إشارات الحالة مع مؤشر الاتصال في الهيدر
            try:
                self.sync_ctrl.sync_started.connect(lambda: self._update_sync_indicator(True, 0, "المزامنة: جارية"))
                self.sync_ctrl.sync_finished.connect(lambda success, count, msg: self._update_sync_indicator(True, count, msg))
                self.sync_ctrl.status_changed.connect(lambda configured, pending, msg: self._update_sync_indicator(configured, pending, msg or ""))
                self.sync_ctrl.error_occurred.connect(lambda msg: self._update_sync_indicator(False, 0, f"خطأ: {msg}"))
            except Exception as e:
                logger.debug(f"Could not connect sync signals: {e}")
            
            self.sync_ctrl.start_background_sync(interval_seconds=600)  # كل 10 دقائق
            logger.info("🔄 Background sync started after login")
            # تحديث المؤشر الأولي
            self._update_sync_indicator(True, 0, "المزامنة: نشطة")

        # بدء النسخ الاحتياطي التلقائي في الخلفية
        self.backup_ctrl.start_background_auto_backup(check_interval_hours=1)
        logger.info("🔄 Background auto backup monitor started after login")

    def _build_main_ui(self, user_info: dict) -> QWidget:
        """بناء لوحة التحكم الرئيسية بجميع التبويبات"""
        self.sidebar_expanded = True
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ────────────────────────────────────
        header = QWidget()
        header.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        header.setFixedHeight(58)
        header.setStyleSheet(f"""
            background-color: {COLORS['bg_panel']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(18, 8, 18, 8)
        h_layout.setDirection(QBoxLayout.Direction.LeftToRight)

        self.sidebar_toggle_btn = QPushButton("☰")
        self.sidebar_toggle_btn.setFixedSize(36, 34)
        self.sidebar_toggle_btn.setToolTip("إظهار/إخفاء القائمة الجانبية")
        self.sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_on_brand']};
                border: 1px solid {COLORS['border']};
                border-radius: 11px;
                font-size: 18px;
                font-weight: 900;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover_surface']};
                border-color: {COLORS['focus_ring']};
            }}
        """)
        self.sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)

        title = QLabel(f"🏪 HyperPOS V2 | مرحباً {user_info.get('name', '')} ({user_info.get('role', '')})")
        title.setFont(QFont("Arial", 14, QFont.Weight.Black))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 0 6px;")
        h_layout.addWidget(title)

        h_layout.addStretch()

        # Alert container
        self.alert_label = QLabel()
        self.alert_label.setStyleSheet(
            f"color: {COLORS['danger']}; font-weight: 900; font-size: 13px; "
            f"background: rgba(226, 59, 59, 0.10); padding: 7px 12px; "
            f"border: 1px solid rgba(226, 59, 59, 0.45); border-radius: 12px;"
        )
        self.alert_label.hide()
        h_layout.addWidget(self.alert_label)

        # ── Sync Connection Indicator ───────────────────
        sync_indicator_frame = QFrame()
        sync_indicator_frame.setFixedHeight(34)
        sync_indicator_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 2px 8px;
            }}
        """)
        sync_indicator_layout = QHBoxLayout(sync_indicator_frame)
        sync_indicator_layout.setContentsMargins(6, 2, 6, 2)
        sync_indicator_layout.setSpacing(6)

        self.sync_status_dot = QLabel()
        self.sync_status_dot.setFixedSize(10, 10)
        self.sync_status_dot.setStyleSheet(f"""
            background-color: {COLORS['warning']};
            border-radius: 5px;
            border: 1px solid {COLORS['border']};
        """)
        self.sync_status_dot.setToolTip("حالة الاتصال بالسحابة: غير متصل")

        self.sync_status_text = QLabel("المزامنة: غير متصل")
        self.sync_status_text.setFont(QFont("Tahoma", 9, QFont.Weight.Bold))
        self.sync_status_text.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.sync_status_text.setToolTip("حالة المزامنة مع قاعدة البيانات السحابية")

        sync_indicator_layout.addWidget(self.sync_status_dot)
        sync_indicator_layout.addWidget(self.sync_status_text)
        sync_indicator_layout.addStretch()

        h_layout.addWidget(sync_indicator_frame)

        # Refresh button
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setStyleSheet(f"background-color: {COLORS['primary']}; color: {COLORS['text_on_brand']}; padding: 7px 14px; border-radius: 10px; font-weight: 900;")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(lambda: self._refresh_current_tab())
        h_layout.addWidget(refresh_btn)

        logout_btn = QPushButton("🚪 تسجيل الخروج")
        logout_btn.setStyleSheet(f"background-color: {COLORS['danger']}; color: {COLORS['text_on_brand']}; padding: 7px 14px; border-radius: 10px; font-weight: 900;")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.logout)
        h_layout.addWidget(logout_btn)

        h_layout.addWidget(self.sidebar_toggle_btn)
        h_layout.setAlignment(self.sidebar_toggle_btn, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(header)

        # ── Tabs ──────────────────────────────────────
        body = QWidget()
        self.body_container = body
        body.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        body.installEventFilter(self)
        body_layout = QHBoxLayout(body)
        self.body_layout = body_layout
        body_layout.setContentsMargins(0, 0, self.sidebar_width_collapsed, 0)
        body_layout.setSpacing(0)
        body_layout.setDirection(QBoxLayout.Direction.LeftToRight)

        sidebar = self._create_sidebar(user_info)
        sidebar.setParent(body)
        nav_layout = sidebar.layout()

        self.content_stack = QStackedWidget()
        self.content_stack.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.content_stack.setStyleSheet(f"background-color: {COLORS['bg_app']};")
        self.tabs = self.content_stack

        policy = PermissionPolicy(user_info)
        role_id = policy.role_id

        # Build tabs based on the legacy dashboard order.
        self.cashier_view = None
        self.drawer_view = None
        self._tab_factories = {}
        self._tab_widgets = {}
        self._tab_keys = {}
        self._loading_tab = False

        def product_view():
            return ProductView(self.product_ctrl, user_info, self.transfers_ctrl)

        def cashier_view():
            self.cashier_view = CashierView(self.cashier_ctrl, user_info)
            return self.cashier_view

        def drawer_view():
            self.drawer_view = DrawerView(self.drawer_ctrl, user_info)
            self.drawer_view.drawer_opened.connect(lambda: self._check_drawer_access(user_info))
            self.drawer_view.drawer_closed.connect(lambda: self._check_drawer_access(user_info))
            return self.drawer_view

        def settings_view():
            view = SettingsView(user_info)
            view.theme_changed.connect(self._on_theme_changed)
            return view

        factories = {
            "stats": (lambda: StatsView(self.stats_ctrl, user_info), "📊 الإحصائيات"),
            "admin": (lambda: AdminView(self.admin_ctrl, user_info), "🛡️ لوحة الإدارة"),
            "products": (product_view, "📦 المنتجات" if role_id == 5 else "📦 إدارة المنتجات"),
            "inventory_count": (lambda: InventoryCountView(self.inventory_count_ctrl, user_info), "📋 جرد المخزون"),
            "purchases": (lambda: PurchasesView(self.purchases_ctrl, user_info), "🚛 المشتريات والموردين"),
            "accounts": (lambda: AccountsView(self.accounts_ctrl, user_info), "📝 المصروفات" if role_id == 2 else ("💰 الحسابات" if role_id == 5 else "💰 الحسابات والمالية")),
            "promotions": (lambda: PromotionsView(self.accounts_ctrl, user_info), "🎫 العروض"),
            "returns": (lambda: ReturnsView(self.returns_ctrl, user_info), "🔄 مرجع فواتير"),
            "cashier": (cashier_view, "💻 الكاشير"),
            "call_center": (lambda: CallCenterView(self.callcenter_ctrl, user_info), "📞 Call Center"),
            "drawer": (drawer_view, "💵 درج الكاشير"),
            "settings": (settings_view, "⚙️ الإعدادات"),
        }

        for page_key in policy.main_pages():
            factory, title_text = factories[page_key]
            placeholder = self._create_lazy_placeholder(title_text)
            placeholder.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            index = self.content_stack.addWidget(placeholder)
            self._tab_factories[index] = factory
            self._tab_widgets[index] = placeholder
            self._tab_keys[index] = page_key
            button = self._create_nav_button(title_text, index)
            self.nav_buttons[index] = button
            self.nav_titles[index] = title_text
            nav_layout.addWidget(button)

        nav_layout.addStretch()
        self._apply_sidebar_state()

        self.content_stack.currentChanged.connect(lambda index: self._ensure_tab_loaded(index, user_info))

        # Default Tab Logic: match the legacy dashboard by opening cashier when available.
        if self.content_stack.count() > 0:
            cashier_index = self._find_tab_key("cashier")
            target_index = cashier_index if cashier_index >= 0 else 0
            self._switch_page(target_index, user_info)
            self._ensure_tab_loaded(target_index, user_info)
            self._check_drawer_access(user_info)

        body_layout.addWidget(self.content_stack, 1)
        self._position_sidebar()
        layout.addWidget(body, 1)

        # ── Keyboard Shortcuts ────────────────────────
        for i in range(min(self.content_stack.count(), 12)):
            key = getattr(Qt.Key, f"Key_F{i+1}")
            shortcut = QShortcut(QKeySequence(key), widget)
            shortcut.activated.connect(lambda idx=i: self._switch_page(idx, user_info))

        return widget

    def eventFilter(self, watched, event):
        if watched is self.body_container and event.type() == QEvent.Type.Resize:
            self._position_sidebar()
        return super().eventFilter(watched, event)

    def _position_sidebar(self):
        if not self.sidebar or not self.body_container:
            return
        width = self.sidebar_width_expanded if self.sidebar_expanded else self.sidebar_width_collapsed
        self.sidebar.setGeometry(
            max(0, self.body_container.width() - width),
            0,
            width,
            self.body_container.height(),
        )
        self.sidebar.raise_()

    def _create_sidebar(self, user_info: dict) -> QFrame:
        sidebar = QFrame()
        self.sidebar = sidebar
        sidebar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        sidebar.setFixedWidth(
            self.sidebar_width_expanded if self.sidebar_expanded else self.sidebar_width_collapsed
        )
        sidebar.setObjectName("MainSidebar")
        sidebar.setStyleSheet(f"""
            QFrame#MainSidebar {{
                background-color: {COLORS['bg_panel']};
                border-left: 1px solid {COLORS['border']};
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
            }}
        """)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(9)

        self.sidebar_title_label = QLabel("HyperPOS")
        self.sidebar_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_title_label.setStyleSheet(
            f"color: {COLORS['text_on_brand']}; background-color: {COLORS['bg_app']}; "
            "font-size: 22px; font-weight: 900; padding: 8px; border-radius: 12px;"
        )
        layout.addWidget(self.sidebar_title_label)

        self.sidebar_user_label = QLabel(f"{user_info.get('name', '')}\n{user_info.get('role', '')}")
        self.sidebar_user_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_user_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            background-color: {COLORS['bg_input']};
            border: 1px solid {COLORS['border']};
            border-radius: 14px;
            padding: 10px;
            font-weight: 800;
        """)
        layout.addWidget(self.sidebar_user_label)

        self.drawer_sidebar_label = QLabel("حالة الدرج: غير معروف")
        self.drawer_sidebar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drawer_sidebar_label.setStyleSheet(f"""
            color: {COLORS['warning']};
            background-color: {COLORS['bg_input']};
            border: 1px solid {COLORS['border']};
            border-radius: 14px;
            padding: 9px;
            font-size: 12px;
            font-weight: 900;
        """)
        layout.addWidget(self.drawer_sidebar_label)
        return sidebar

    def _create_nav_button(self, title: str, index: int) -> QPushButton:
        button = QPushButton(title)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(46)
        button.setToolTip(title)
        button.setStyleSheet(self._nav_button_style(False))
        button.clicked.connect(lambda: self._switch_page(index))
        return button

    def _nav_button_style(self, active: bool) -> str:
        bg = COLORS["primary"] if active else COLORS["bg_input"]
        fg = COLORS["text_light"] if active else COLORS["text_primary"]
        border = COLORS["primary_hover"] if active else COLORS["border"]
        text_align = "right" if self.sidebar_expanded else "center"
        padding = "9px 12px" if self.sidebar_expanded else "9px 4px"
        font_size = "13px" if self.sidebar_expanded else "18px"
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 14px;
                padding: {padding};
                text-align: {text_align};
                font-size: {font_size};
                font-weight: 900;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover_surface']};
                border-color: {COLORS['focus_ring']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['bg_elevated']};
                color: {COLORS['text_muted']};
                border-color: {COLORS['border_soft']};
            }}
        """

    def _toggle_sidebar(self):
        self.sidebar_expanded = not self.sidebar_expanded
        self._apply_sidebar_state()

    def _apply_sidebar_state(self):
        if not self.sidebar:
            return
        width = self.sidebar_width_expanded if self.sidebar_expanded else self.sidebar_width_collapsed
        self.sidebar.setFixedWidth(width)
        self._position_sidebar()
        if self.sidebar_toggle_btn:
            self.sidebar_toggle_btn.setText("☰" if self.sidebar_expanded else "☷")
        if self.sidebar_title_label:
            self.sidebar_title_label.setText("HyperPOS" if self.sidebar_expanded else "HP")
        if self.sidebar_user_label:
            self.sidebar_user_label.setVisible(self.sidebar_expanded)
        if self.drawer_sidebar_label:
            if self.sidebar_expanded:
                self.drawer_sidebar_label.setText(self.drawer_sidebar_label.toolTip() or self.drawer_sidebar_label.text())
            else:
                full_text = self.drawer_sidebar_label.text()
                self.drawer_sidebar_label.setToolTip(full_text)
                self.drawer_sidebar_label.setText("●")
        active_index = self.content_stack.currentIndex() if self.content_stack else None
        for index, button in self.nav_buttons.items():
            full_title = self.nav_titles.get(index, button.toolTip() or button.text())
            button.setText(full_title if self.sidebar_expanded else self._compact_nav_text(full_title))
            button.setToolTip(full_title)
            button.setStyleSheet(self._nav_button_style(index == active_index))

    def _compact_nav_text(self, title: str) -> str:
        return (title or "").strip().split(" ", 1)[0] or "•"

    def _switch_page(self, index: int, user_info: dict = None):
        if not self.content_stack or index < 0 or index >= self.content_stack.count():
            return
        button = self.nav_buttons.get(index)
        if button and not button.isEnabled():
            return
        self.content_stack.setCurrentIndex(index)
        self._sync_nav_state(index)
        if self.sidebar_expanded:
            self.sidebar_expanded = False
            self._apply_sidebar_state()

    def _sync_nav_state(self, active_index: int = None):
        if active_index is None and self.content_stack:
            active_index = self.content_stack.currentIndex()
        for index, button in self.nav_buttons.items():
            button.setStyleSheet(self._nav_button_style(index == active_index))

    def _create_lazy_placeholder(self, title: str) -> QWidget:
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(f"سيتم تحميل {title} عند الفتح")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px; font-weight: 700;")
        layout.addWidget(label)
        return placeholder

    def _find_tab_key(self, page_key: str) -> int:
        for index, key in self._tab_keys.items():
            if key == page_key:
                return index
        return -1

    def _ensure_tab_loaded(self, index: int, user_info: dict):
        if self._loading_tab:
            return
        if index < 0 or not self.content_stack:
            return
        if index not in self._tab_factories:
            return
        current_widget = self._tab_widgets.get(index)
        if current_widget is not None and current_widget is not self.content_stack.widget(index):
            return

        factory = self._tab_factories.pop(index)
        old_widget = self.content_stack.widget(index)
        self._loading_tab = True
        try:
            widget = factory()
            widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.content_stack.removeWidget(old_widget)
            self.content_stack.insertWidget(index, widget)
            self._tab_widgets[index] = widget
            self.content_stack.setCurrentIndex(index)
            old_widget.deleteLater()
        finally:
            self._loading_tab = False
        self._sync_nav_state(index)
        if self._tab_keys.get(index) in {"cashier", "drawer"}:
            self._check_drawer_access(user_info)

    def _find_tab_index(self, target_widget) -> int:
        if not self.content_stack or target_widget is None:
            return -1
        for index in range(self.content_stack.count()):
            if self.content_stack.widget(index) == target_widget:
                return index
        return -1

    def _check_drawer_access(self, user_info: dict):
        """تطبيق منطق الدرج القديم على تبويب الكاشير."""
        if not self.content_stack or not getattr(self, "cashier_view", None):
            return

        policy = PermissionPolicy(user_info)
        cashier_index = self._find_tab_index(self.cashier_view)
        if cashier_index < 0:
            return
        cashier_button = self.nav_buttons.get(cashier_index)
        drawer_index = self._find_tab_key("drawer")

        store_id = user_info.get("store_id")
        user_id = user_info.get("id")
        store_drawer = self.drawer_ctrl.get_store_open_drawer(store_id)
        if not store_drawer and (policy.is_admin or policy.is_developer):
            store_drawer = self.drawer_ctrl.get_any_open_drawer()

        if not store_drawer:
            if cashier_button:
                can_open_or_use = policy.is_cashier or policy.can_use_shared_drawer()
                cashier_button.setEnabled(can_open_or_use)
                cashier_button.setToolTip("افتح درجًا من شاشة الكاشير" if can_open_or_use else "يجب فتح درج أولاً")
            self._set_drawer_sidebar_status("حالة الدرج: مغلق", "warning")
            self.alert_label.setText("⚠️ لا يوجد درج كاشير مفتوح في هذا الفرع")
            self.alert_label.show()
            if policy.is_cashier and drawer_index >= 0:
                self._switch_page(drawer_index, user_info)
            return

        if store_drawer.get("cashier_id") != user_id and not policy.can_use_shared_drawer():
            opener = store_drawer.get("cashier_name", "غير معروف")
            if cashier_button:
                cashier_button.setEnabled(False)
                cashier_button.setToolTip(f"الجهاز مشغول بدرج مفتوح لـ: {opener}")
            self._set_drawer_sidebar_status(f"درج مفتوح: {opener}", "danger")
            self.alert_label.setText(f"⚠️ الدرج مفتوح بواسطة: {opener}")
            self.alert_label.show()
            if policy.is_cashier and drawer_index >= 0:
                self._switch_page(drawer_index, user_info)
            return

        if cashier_button:
            cashier_button.setEnabled(True)
        if store_drawer.get("cashier_id") != user_id:
            opener = store_drawer.get("cashier_name", "غير معروف")
            store_name = store_drawer.get("store_name", "")
            if cashier_button:
                cashier_button.setToolTip(f"استخدام درج مشترك: {opener}" + (f" - {store_name}" if store_name else ""))
            self._set_drawer_sidebar_status(f"درج مشترك: {opener}" + (f" - {store_name}" if store_name else ""), "success")
        else:
            if cashier_button:
                cashier_button.setToolTip("")
            self._set_drawer_sidebar_status("حالة الدرج: مفتوح", "success")
        self.alert_label.hide()

    def _set_drawer_sidebar_status(self, text: str, kind: str):
        if not self.drawer_sidebar_label:
            return
        self.drawer_sidebar_label.setToolTip(text)
        self.drawer_sidebar_label.setText(text if self.sidebar_expanded else "●")
        self.drawer_sidebar_label.setStyleSheet(self._drawer_status_style(kind))

    def _drawer_status_style(self, kind: str) -> str:
        color = {
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "danger": COLORS["danger"],
        }.get(kind, COLORS["info"])
        return f"""
            color: {color};
            background-color: {COLORS['bg_input']};
            border: 1px solid {color};
            border-radius: 10px;
            padding: 7px;
            font-size: 12px;
            font-weight: 800;
        """

    def _refresh_current_tab(self):
        """تحديث التبويب الحالي"""
        if not self.tabs:
            return
        current = self.tabs.currentWidget()
        if hasattr(current, 'refresh_data'):
            current.refresh_data()
        elif hasattr(current, 'check_drawer_status'):
            current.check_drawer_status()
        elif hasattr(current, '_load_all'):
            current._load_all()

    def _on_theme_changed(self, mode: str):
        label = THEME_MODES.get(mode, mode)
        self.setStyleSheet(GLOBAL_STYLE)
        QMessageBox.information(
            self,
            "تغيير المظهر",
            f"تم اختيار {label}.\n"
            "أعد فتح التطبيق لتطبيق المظهر بالكامل على كل الصفحات.",
        )

    def logout(self):
        """تسجيل الخروج والعودة لشاشة الدخول"""
        reply = QMessageBox.question(self, "تأكيد", "هل تريد تسجيل الخروج؟",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        # إيقاف المزامنة في الخلفية
        self.sync_ctrl.stop_background_sync()
        logger.info("🛑 Background sync stopped on logout")

        # إيقاف مراقبة النسخ الاحتياطي التلقائي
        self.backup_ctrl.stop_background_auto_backup()
        logger.info("🛑 Background auto backup monitor stopped on logout")

        if self.main_widget:
            self.stack.removeWidget(self.main_widget)
            self.main_widget = None
            self.tabs = None
            self.content_stack = None
            self.sidebar = None
            self.sidebar_toggle_btn = None
            self.sidebar_title_label = None
            self.sidebar_user_label = None
            self.drawer_sidebar_label = None
            self.nav_buttons = {}
            self.nav_titles = {}

        self.auth_ctrl.current_user = None
        self.login_view.username_input.clear()
        self.login_view.password_input.clear()
        self.stack.setCurrentWidget(self.login_view)
        self._prepare_login_window()

    def _update_sync_indicator(self, configured: bool, pending: int, message: str):
        """تحديث مؤشر حالة الاتصال بالسحابة في الهيدر"""
        if not hasattr(self, 'sync_status_dot') or not hasattr(self, 'sync_status_text'):
            return
        
        if configured and pending == 0:
            color = COLORS['success']
            text = message or "المزامنة: متصل - لا توجد عمليات"
            tooltip = "متصل بالسحابة - جميع البيانات متزامنة"
        elif configured:
            color = COLORS['warning']
            text = f"المزامنة: متصل - {pending} معلقة"
            tooltip = f"متصل بالسحابة - {pending} عملية معلقة"
        else:
            color = COLORS['danger']
            text = message or "المزامنة: غير متصل"
            tooltip = "غير متصل بالسحابة - تحقق من إعدادات الاتصال"
        
        self.sync_status_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 5px;
            border: 1px solid {COLORS['border']};
        """)
        self.sync_status_text.setText(text)
        self.sync_status_text.setToolTip(tooltip)
        self.sync_status_text.setStyleSheet(f"""
            color: {color};
            font-weight: 900;
        """)
        logger.debug(f"Sync indicator updated: configured={configured}, pending={pending}, msg={message}")

    def closeEvent(self, event):
        """حدث إغلاق النافذة - إيقاف المزامنة والنسخ الاحتياطي وتنظيف الموارد"""
        try:
            self.sync_ctrl.stop_background_sync()
            logger.info("🛑 Background sync stopped on application close")
        except Exception as e:
            logger.error(f"Error stopping background sync on close: {e}")
        try:
            self.backup_ctrl.stop_background_auto_backup()
            logger.info("🛑 Background auto backup monitor stopped on application close")
        except Exception as e:
            logger.error(f"Error stopping background auto backup on close: {e}")
        event.accept()


def main():
    logger.info("Starting HyperPOS V2. Error log: %s", ERROR_LOG_PATH)
    
    # تشغيل هجرات قاعدة البيانات عند البدء
    logger.info("🔄 Running database migrations...")
    try:
        run_migrations_on_startup()
        logger.info("✅ Database migrations completed")
    except Exception as e:
        logger.error(f"❌ Migration error (continuing anyway): {e}")
    
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setFont(QFont("Tahoma", 10))
    app.setStyle("Fusion")

    window = MainWindow()
    if hasattr(window, "_prepare_login_window"):
        window._prepare_login_window()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
