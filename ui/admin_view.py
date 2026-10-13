"""
Admin View - واجهة لوحة الإدارة (Clean Architecture)
إدارة المستخدمين + مراقبة الأدراج + إدارة الفروع
"""
import logging
from PyQt6.QtWidgets import (
    QTableWidgetItem,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTableWidget, QMessageBox, QComboBox, QDialog,
    QFormLayout, QTabWidget, QHeaderView, QScrollArea,
    QFrame, QCheckBox, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from ui.styles import GLOBAL_STYLE, COLORS, TABLE_STYLE, get_button_style
from datetime import datetime
from controllers.admin_controller import AdminController
from ui.form_helpers import (
    action_row,
    configure_form_layout,
    scrollable_dialog_layout,
    style_dialog,
    style_form_controls,
)
from ui.table_helpers import center_item, configure_table, set_center_item
from ui.subtab_dropdown import create_stack_dropdown
from utils.device_identity import get_current_device_info
from utils.permissions import PermissionPolicy

logger = logging.getLogger(__name__)


class AdminView(QWidget):
    """واجهة لوحة الإدارة"""

    def __init__(self, ctrl: AdminController, user_info: dict, parent=None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.user_info = user_info
        self.setStyleSheet(GLOBAL_STYLE)
        self._init_ui()
        self._load_all()

        # Real-time refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._load_all)
        self.refresh_timer.start(10000) # Every 10 seconds

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        policy = PermissionPolicy(self.user_info)
        sub_tabs = [
            ("👤 إدارة المستخدمين", self._create_users_tab()),
            ("💰 مراقبة الأدراج", self._create_drawers_tab()),
            ("🏥 إدارة الفروع", self._create_branches_tab()),
            ("📝 سجل التدقيق", self._create_audit_logs_tab()),
        ]
        if policy.can_manage_devices():
            sub_tabs.append(("💻 إدارة الأجهزة", self._create_devices_tab()))
        if policy.can_manage_cloud():
            sub_tabs.append(("☁️ إدارة السحابة", self._create_cloud_tab()))

        from PyQt6.QtWidgets import QStackedWidget
        self.stack = QStackedWidget()

        for _, widget in sub_tabs:
            self.stack.addWidget(widget)

        layout.addWidget(
            create_stack_dropdown(
                self.stack,
                [text for text, _ in sub_tabs],
                "اختر قسم الإدارة",
                self._switch_tab,
            )
        )
        layout.addWidget(self.stack)

        # Set initial tab
        self._switch_tab(0)

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)

    def _make_table_button(self, text: str, style: str) -> QPushButton:
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        color_map = {
            "info": (COLORS["info"], COLORS["info_hover"]),
            "danger": (COLORS["danger"], COLORS["danger_hover"]),
            "warning": (COLORS["warning"], COLORS["warning_hover"]),
            "success": (COLORS["success"], COLORS["success_hover"]),
            "primary": (COLORS["primary"], COLORS["primary_hover"]),
        }
        bg, hover = color_map.get(style, color_map["primary"])
        button.setFixedHeight(30)
        button.setMinimumWidth(64)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {COLORS['text_on_brand']};
                border: none;
                border-radius: 8px;
                padding: 2px 10px;
                min-height: 30px;
                max-height: 30px;
                font-size: 12px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['bg_elevated']};
                color: {COLORS['text_muted']};
            }}
        """)
        return button

    def _current_device_info(self) -> dict:
        return get_current_device_info()

    # ═══════════════════════════════════════════════════
    #  Users Tab
    # ═══════════════════════════════════════════════════
    def _create_users_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        title = QLabel("إدارة المستخدمين")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ إضافة مستخدم جديد")
        add_btn.setStyleSheet(get_button_style('success'))
        add_btn.clicked.connect(self._add_user)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(7)
        self.users_table.setHorizontalHeaderLabels(["#", "الاسم", "البريد", "الدور", "الفرع", "الهاتف", "الإجراءات"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(self.users_table, TABLE_STYLE, row_height=60)
        layout.addWidget(self.users_table)

        scroll.setWidget(container)
        return scroll

    def _load_users(self):
        users = self.ctrl.get_all_users()
        self.users_table.setRowCount(len(users))

        for row, user in enumerate(users):
            set_center_item(self.users_table, row, 0, row + 1)
            set_center_item(self.users_table, row, 1, user.get('name', ''))
            set_center_item(self.users_table, row, 2, user.get('email', ''))
            set_center_item(self.users_table, row, 3, user.get('role_name', ''))
            set_center_item(self.users_table, row, 4, user.get('store_name', '') or '---')
            set_center_item(self.users_table, row, 5, user.get('phone', '') or '')

            actions = QWidget()
            a_layout = QHBoxLayout(actions)
            a_layout.setContentsMargins(4, 3, 4, 3)
            a_layout.setSpacing(8)
            a_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = self._make_table_button("✏️", "info")
            edit_btn.clicked.connect(lambda _, u=user: self._edit_user(u))
            a_layout.addWidget(edit_btn)

            del_btn = self._make_table_button("🗑️", "danger")
            del_btn.clicked.connect(lambda _, uid=user['id']: self._delete_user(uid))
            if user['id'] == 1:
                del_btn.setEnabled(False)
            a_layout.addWidget(del_btn)

            self.users_table.setCellWidget(row, 6, actions)

    def _add_user(self):
        self._show_user_dialog()

    def _edit_user(self, user: dict):
        self._show_user_dialog(user)

    def _show_user_dialog(self, user: dict = None):
        dialog = QDialog(self)
        dialog.setWindowTitle("تعديل مستخدم" if user else "إضافة مستخدم")
        style_dialog(dialog, min_width=500)

        _, content_layout, footer_layout = scrollable_dialog_layout(dialog)
        form = QFormLayout()
        configure_form_layout(form)

        name_input = QLineEdit(user.get('name', '') if user else '')
        email_input = QLineEdit(user.get('email', '') if user else '')
        phone_input = QLineEdit(user.get('phone', '') if user else '')
        pass_input = QLineEdit()
        pass_input.setPlaceholderText("كلمة المرور الجديدة" if user else "كلمة المرور")
        pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        role_combo = QComboBox()
        roles = self.ctrl.get_all_roles()
        for r in roles:
            role_combo.addItem(r['role_name'], r['id'])
        if user:
            idx = role_combo.findData(user.get('role_id'))
            if idx >= 0:
                role_combo.setCurrentIndex(idx)

        store_combo = QComboBox()
        stores = self.ctrl.get_all_stores()

        for s in stores:
            store_combo.addItem(s['store_name'], s['id'])

        if user:
            user_store_id = user.get('store_id')
            idx = store_combo.findData(user_store_id)
            if idx >= 0:
                store_combo.setCurrentIndex(idx)
            elif store_combo.count() > 0:
                store_combo.setCurrentIndex(0)
        else:
            # اختيار أول فرع نشط كفرع افتراضي بدلاً من إرسال None
            if store_combo.count() > 0:
                store_combo.setCurrentIndex(0)
        style_form_controls(name_input, email_input, phone_input, pass_input, role_combo, store_combo)

        form.addRow("الاسم:", name_input)
        form.addRow("البريد:", email_input)
        form.addRow("الهاتف:", phone_input)
        form.addRow("كلمة المرور:", pass_input)
        form.addRow("الدور:", role_combo)
        form.addRow("الفرع:", store_combo)
        content_layout.addLayout(form)

        btn_layout, save_btn, cancel_btn = action_row("حفظ")
        cancel_btn.clicked.connect(dialog.reject)
        footer_layout.addLayout(btn_layout)

        def save():
            name = name_input.text().strip()
            email = email_input.text().strip()
            phone = phone_input.text().strip()
            password = pass_input.text()
            role_id = role_combo.currentData()
            store_id = store_combo.currentData()

            if not name or not email:
                QMessageBox.warning(dialog, "تنبيه", "الاسم والبريد مطلوبان")
                return

            # Check for existing inactive user
            if not user:
                existing = self.ctrl.get_user_by_email(email)
                if existing:
                    if existing['is_active']:
                        QMessageBox.warning(dialog, "تنبيه", f"البريد {email} مستخدم بالفعل وبحساب نشط")
                        return
                    else:
                        # User exists but inactive - Show confirmation flow
                        dialog.accept() # Close current add dialog
                        self._show_reactivate_confirmation(existing)
                        return

            if user:
                ok = self.ctrl.update_user(user['id'], name, email, role_id, store_id, phone,
                                           password if password else None)
            else:
                if not password:
                    QMessageBox.warning(dialog, "تنبيه", "كلمة المرور مطلوبة")
                    return
                ok = self.ctrl.add_user(name, email, password, role_id, store_id, phone)

            if ok:
                QMessageBox.information(dialog, "نجاح", "تمت العملية بنجاح")
                dialog.accept()
                self._load_users()
            else:
                QMessageBox.critical(dialog, "خطأ", "فشلت العملية")

        save_btn.clicked.connect(save)
        dialog.exec()
    def _show_reactivate_confirmation(self, user_data: dict):
        dialog = QDialog(self)
        dialog.setWindowTitle("استعادة مستخدم مسجل")
        dialog.setFixedWidth(450)
        dialog.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(dialog)

        msg = QLabel("<b>هذا المستخدم مسجل من قبل ولكنه غير نشط.</b><br>إليك البيانات المسجلة له:")
        msg.setStyleSheet("font-size: 14px;")
        layout.addWidget(msg)

        info_box = QFrame()
        info_box.setStyleSheet(f"background: {COLORS['bg_panel']}; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 15px;")
        info_lay = QFormLayout(info_box)
        info_lay.addRow("الاسم:", QLabel(user_data['name']))
        info_lay.addRow("البريد:", QLabel(user_data['email']))
        info_lay.addRow("الدور السابق:", QLabel(user_data['role_name']))
        info_lay.addRow("الفرع السابق:", QLabel(user_data['store_name'] or "الإدارة العليا"))
        layout.addWidget(info_box)

        btn_layout = QHBoxLayout()
        reactivate_btn = QPushButton("✅ إعادة تفعيل المستخدم")
        reactivate_btn.setStyleSheet(get_button_style('success'))
        
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet(get_button_style('danger'))
        cancel_btn.clicked.connect(dialog.reject)

        btn_layout.addWidget(reactivate_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def do_reactivate():
            # Simply update them without changing password unless requested? 
            # Or just reactivate with existing data. 
            # The user just wants to reactivate.
            if self.ctrl.update_user(user_data['id'], user_data['name'], user_data['email'], 
                                   user_data['role_id'], user_data['store_id'], user_data['phone']):
                QMessageBox.information(self, "نجاح", "تمت إعادة تفعيل المستخدم بنجاح")
                dialog.accept()
                self._load_users()

        reactivate_btn.clicked.connect(do_reactivate)
        dialog.exec()

    def _delete_user(self, user_id: int):
        reply = QMessageBox.question(self, "تأكيد", "هل تريد حذف هذا المستخدم؟")
        if reply == QMessageBox.StandardButton.Yes:
            if self.ctrl.delete_user(user_id):
                self._load_users()

    # ═══════════════════════════════════════════════════
    #  Drawers Monitoring Tab
    # ═══════════════════════════════════════════════════
    def _create_drawers_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        header = QHBoxLayout()
        title = QLabel("تقرير الأدراج المفتوحة والمغلقة")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()

        refresh_btn = QPushButton("🔄 تحديث البيانات")
        refresh_btn.setStyleSheet(get_button_style('info'))
        refresh_btn.clicked.connect(self._load_drawers)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        self.drawers_table = QTableWidget()
        self.drawers_table.setColumnCount(10)
        self.drawers_table.setHorizontalHeaderLabels([
            "الكاشير", "الفرع", "وقت الفتح", "الحالة",
            "الرصيد الافتتاحي", "المبيعات", "المبلغ المتوقع",
            "الرصيد الفعلي", "الفرق", "طباعة"
        ])
        self.drawers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.drawers_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.drawers_table.setColumnWidth(9, 120)
        configure_table(self.drawers_table, TABLE_STYLE, row_height=60)
        layout.addWidget(self.drawers_table)

        scroll.setWidget(container)
        return scroll

    def _load_drawers(self):
        report = self.ctrl.get_drawers_report()
        self.drawers_table.setRowCount(len(report))

        for row, data in enumerate(report):
            set_center_item(self.drawers_table, row, 0, data.get('cashier_name', ''))
            set_center_item(self.drawers_table, row, 1, data.get('store_name', ''))

            opening_date = data.get('opening_date')
            open_time = opening_date.strftime("%Y-%m-%d %H:%M") if isinstance(opening_date, datetime) else str(opening_date or "")
            set_center_item(self.drawers_table, row, 2, open_time)

            status_text = "🟢 مفتوح" if data.get('status') == 'Open' else "🔴 مغلق"
            status_item = center_item(status_text)
            if data.get('status') == 'Open':
                status_item.setForeground(QColor("#27ae60"))
            self.drawers_table.setItem(row, 3, status_item)

            opening = float(data.get('opening_balance', 0) or 0)
            cash_sales = float(data.get('cash_sales', 0) or 0)
            total_sales = float(data.get('total_sales', 0) or 0)
            cash_returns = float(data.get('cash_returns', 0) or 0)
            expected = opening + cash_sales - cash_returns
            actual = float(data.get('closing_balance', 0) or 0) if data.get('status') == 'Closed' else 0
            diff = actual - expected if data.get('status') == 'Closed' else 0

            set_center_item(self.drawers_table, row, 4, f"{opening:,.2f}")
            set_center_item(self.drawers_table, row, 5, f"{total_sales:,.2f}")
            set_center_item(self.drawers_table, row, 6, f"{expected:,.2f}")
            set_center_item(self.drawers_table, row, 7, f"{actual:,.2f}" if data.get('status') == 'Closed' else "---")

            diff_item = center_item(f"{diff:,.2f}" if data.get('status') == 'Closed' else "---")
            if diff < 0:
                diff_item.setForeground(QColor("#e74c3c"))
            elif diff > 0:
                diff_item.setForeground(QColor("#27ae60"))
            self.drawers_table.setItem(row, 8, diff_item)

            print_btn = self._make_table_button("🖨️ طباعة", "info")
            print_btn.clicked.connect(lambda _, drawer_id=data['id']: self._print_drawer_receipt(drawer_id))
            self.drawers_table.setCellWidget(row, 9, print_btn)

    def _print_drawer_receipt(self, drawer_id: int):
        try:
            from utils.printer_service import PrinterService
            summary = self.ctrl.get_drawer_summary(drawer_id)
            if not summary:
                QMessageBox.warning(self, "خطأ", "تعذر العثور على بيانات الدرج")
                return
            result = PrinterService.print_drawer_report(summary)
            if isinstance(result, dict) and not result.get("printed") and result.get("saved"):
                QMessageBox.information(
                    self,
                    "حفظ PDF",
                    f"لا توجد طابعة فعلية. تم حفظ التقرير تلقائياً في:\n{result.get('pdf_path')}",
                )
            elif isinstance(result, dict) and result.get("printed"):
                QMessageBox.information(self, "طباعة", "تم إرسال أمر الطباعة بنجاح")
            elif result:
                QMessageBox.information(self, "طباعة", "تم تنفيذ أمر الطباعة/الحفظ بنجاح")
            else:
                QMessageBox.warning(self, "تنبيه", "تعذر الطباعة أو حفظ ملف PDF")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الطباعة: {e}")

    # ═══════════════════════════════════════════════════
    #  Branches Tab
    # ═══════════════════════════════════════════════════

    def _create_branches_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        title = QLabel("إدارة الفروع والمخازن")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setStyleSheet(get_button_style('info'))
        refresh_btn.clicked.connect(self._load_branches)
        btn_layout.addWidget(refresh_btn)

        add_btn = QPushButton("➕ إضافة فرع جديد")
        add_btn.setStyleSheet(get_button_style('success'))
        add_btn.clicked.connect(lambda: self._show_branch_dialog())
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.branches_table = QTableWidget()
        self.branches_table.setColumnCount(7)
        self.branches_table.setHorizontalHeaderLabels([
            "اسم الفرع", "النوع", "نطاق IP (من)", "نطاق IP (إلى)",
            "فحص IP", "الحالة", "الإجراءات"
        ])
        self.branches_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(self.branches_table, TABLE_STYLE, row_height=46)
        layout.addWidget(self.branches_table)

        scroll.setWidget(container)
        return scroll

    def _load_branches(self):
        stores = self.ctrl.get_all_stores(include_inactive=True)
        self.branches_table.setRowCount(len(stores))
        for row, s in enumerate(stores):
            type_text = {
                'GM': 'مدير عام',
                'Main': 'مخزن رئيسي',
                'Warehouse': 'مخزن',
                'Branch': 'فرع',
            }.get(s.get('store_type'), s.get('store_type', ''))

            set_center_item(self.branches_table, row, 0, s.get('store_name', ''))
            set_center_item(self.branches_table, row, 1, type_text)
            set_center_item(self.branches_table, row, 2, s.get('ip_range_start') or '-')
            set_center_item(self.branches_table, row, 3, s.get('ip_range_end') or '-')

            require_check = bool(s.get('require_ip_check', True))
            ip_item = center_item("✅ نعم" if require_check else "❌ لا")
            ip_item.setForeground(QColor("#27ae60" if require_check else "#e74c3c"))
            self.branches_table.setItem(row, 4, ip_item)

            is_active = bool(s.get('is_active', True))
            status_item = center_item("✅ نشط" if is_active else "🚫 معطّل")
            status_item.setForeground(QColor("#27ae60" if is_active else "#e74c3c"))
            self.branches_table.setItem(row, 5, status_item)

            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            edit_btn = self._make_table_button("✏️ تعديل", "info")
            edit_btn.clicked.connect(lambda _, store=s: self._show_branch_dialog(store))
            delete_btn = self._make_table_button("🗑️ حذف", "danger")
            delete_btn.clicked.connect(lambda _, store=s: self._delete_branch(store))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            self.branches_table.setCellWidget(row, 6, actions)

    def _create_devices_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Info
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        
        info_layout = QVBoxLayout()
        title = QLabel("🔐 إدارة الأجهزة المصرح بها")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        info_layout.addWidget(title)
        
        desc = QLabel("تحكم في الأجهزة المسموح لها بالولوج للنظام وربطها بفروع أو مستخدمين محددين.")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info_layout.addWidget(desc)
        h_layout.addLayout(info_layout)
        
        # Current Device Info
        curr_box = QWidget()
        curr_box.setStyleSheet(f"background: {COLORS['bg_input']}; border-radius: 8px; padding: 10px;")
        curr_lay = QVBoxLayout(curr_box)
        try:
            device = self._current_device_info()
            curr_info = QLabel(f"<b>هذا الجهاز:</b> {device['device_name']}<br><small>{device['mac_address']}</small>")
        except Exception:
            curr_info = QLabel("<b>هذا الجهاز:</b> غير معروف")
        curr_info.setStyleSheet(f"color: {COLORS['text_on_brand']};")
        curr_lay.addWidget(curr_info)
        h_layout.addWidget(curr_box)
        
        layout.addWidget(header)

        # Actions
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ إضافة جهاز")
        add_btn.setStyleSheet(get_button_style('success'))
        add_btn.clicked.connect(lambda: self._show_device_dialog())
        btn_layout.addWidget(add_btn)

        assign_btn = QPushButton("👤 إضافة مستخدم لجهاز")
        assign_btn.setStyleSheet(get_button_style('info'))
        assign_btn.clicked.connect(self._assign_user_to_device)
        btn_layout.addWidget(assign_btn)

        activate_btn = QPushButton("✅ تفعيل")
        activate_btn.setStyleSheet(get_button_style('success'))
        activate_btn.clicked.connect(lambda: self._set_selected_device_status(True))
        btn_layout.addWidget(activate_btn)

        deactivate_btn = QPushButton("🚫 تعطيل")
        deactivate_btn.setStyleSheet(get_button_style('warning'))
        deactivate_btn.clicked.connect(lambda: self._set_selected_device_status(False))
        btn_layout.addWidget(deactivate_btn)

        delete_btn = QPushButton("🗑️ حذف")
        delete_btn.setStyleSheet(get_button_style('danger'))
        delete_btn.clicked.connect(self._delete_selected_device)
        btn_layout.addWidget(delete_btn)

        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setStyleSheet(get_button_style('info'))
        refresh_btn.clicked.connect(self._load_devices)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Devices Table
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(9)
        self.devices_table.setHorizontalHeaderLabels([
            "ID", "معرّف الجهاز", "اسم الجهاز", "MAC Address",
            "الفرع", "المستخدم", "الحالة", "آخر استخدام", "ملاحظات"
        ])
        self.devices_table.setColumnHidden(0, True)
        self.devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        configure_table(self.devices_table, TABLE_STYLE)
        layout.addWidget(self.devices_table)

        scroll.setWidget(container)
        return scroll

    def _create_cloud_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        title = QLabel("☁️ إدارة السحابة والمزامنة")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Stats Cards
        card_layout = QHBoxLayout()
        
        self.pending_card = QWidget()
        self.pending_card.setStyleSheet(f"background: {COLORS['bg_input']}; border-radius: 12px; border-left: 5px solid {COLORS['warning']};")
        p_lay = QVBoxLayout(self.pending_card)
        p_lay.addWidget(QLabel("بيانات بانتظار الرفع"))
        self.pending_count_lbl = QLabel("0")
        self.pending_count_lbl.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        p_lay.addWidget(self.pending_count_lbl)
        card_layout.addWidget(self.pending_card)

        self.last_sync_card = QWidget()
        self.last_sync_card.setStyleSheet(f"background: {COLORS['bg_input']}; border-radius: 12px; border-left: 5px solid {COLORS['success']};")
        l_lay = QVBoxLayout(self.last_sync_card)
        l_lay.addWidget(QLabel("آخر مزامنة ناجحة"))
        self.last_sync_lbl = QLabel("---")
        self.last_sync_lbl.setFont(QFont("Arial", 12))
        l_lay.addWidget(self.last_sync_lbl)
        card_layout.addWidget(self.last_sync_card)

        layout.addLayout(card_layout)

        # Sync Button Section
        sync_panel = QWidget()
        sync_panel.setStyleSheet(f"background: {COLORS['bg_panel']}; border-radius: 15px; padding: 30px;")
        sync_lay = QVBoxLayout(sync_panel)
        sync_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sync_desc = QLabel("يمكنك إجراء مزامنة يدوية شاملة لرفع كافة البيانات المحلية للسحابة في حال وجود بيانات متراكمة.")
        sync_desc.setWordWrap(True)
        sync_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sync_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; margin-bottom: 20px;")
        sync_lay.addWidget(sync_desc)

        self.sync_btn = QPushButton("🚀 بدء المزامنة الشاملة الآن")
        self.sync_btn.setFixedSize(300, 60)
        self.sync_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['text_on_brand']};
                font-size: 16px;
                font-weight: bold;
                border-radius: 30px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        self.sync_btn.clicked.connect(self._start_cloud_sync)
        sync_lay.addWidget(self.sync_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(sync_panel)
        layout.addStretch()
        
        scroll.setWidget(container)
        return scroll

    def _show_branch_dialog(self, store: dict = None):
        dialog = QDialog(self)
        dialog.setWindowTitle("تعديل فرع" if store else "إضافة فرع جديد")
        style_dialog(dialog, min_width=580)

        _, content_layout, footer_layout = scrollable_dialog_layout(dialog)
        basic_group = QGroupBox("المعلومات الأساسية")
        basic_form = QFormLayout(basic_group)
        configure_form_layout(basic_form)

        name_input = QLineEdit(store.get('store_name', '') if store else '')
        type_combo = QComboBox()
        type_combo.addItem("فرع عادي", "Branch")
        type_combo.addItem("مدير عام", "GM")
        type_combo.addItem("مخزن رئيسي", "Main")
        type_combo.addItem("مخزن", "Warehouse")

        city_input = QLineEdit(store.get('city', '') if store else '')
        address_input = QLineEdit(store.get('address', '') if store else '')
        phone_input = QLineEdit(store.get('phone', '') if store else '')
        manager_input = QLineEdit(store.get('manager_name', '') if store else '')
        active_check = QCheckBox("نشط")
        active_check.setChecked(bool(store.get('is_active', True)) if store else True)

        if store:
            type_index = type_combo.findData(store.get('store_type', 'Branch'))
            if type_index >= 0:
                type_combo.setCurrentIndex(type_index)
        style_form_controls(name_input, type_combo, city_input, address_input, phone_input, manager_input)

        basic_form.addRow("اسم الفرع:", name_input)
        basic_form.addRow("النوع:", type_combo)
        basic_form.addRow("المدينة:", city_input)
        basic_form.addRow("العنوان:", address_input)
        basic_form.addRow("الهاتف:", phone_input)
        basic_form.addRow("المدير:", manager_input)
        basic_form.addRow("الحالة:", active_check)
        content_layout.addWidget(basic_group)

        ip_group = QGroupBox("إعدادات نطاق IP وربط الجهاز")
        ip_form = QFormLayout(ip_group)
        configure_form_layout(ip_form)
        ip_start_input = QLineEdit(store.get('ip_range_start', '') if store else '')
        ip_end_input = QLineEdit(store.get('ip_range_end', '') if store else '')
        require_ip_check = QCheckBox("تفعيل فحص نطاق IP")
        require_ip_check.setChecked(bool(store.get('require_ip_check', True)) if store else True)
        link_device_check = QCheckBox("ربط هذا الجهاز بالفرع الحالي" if not store else "نقل هذا الجهاز إلى هذا الفرع")
        user_combo = QComboBox()
        user_combo.addItem("سماح لجميع المستخدمين", None)
        for user in self.ctrl.get_all_users():
            user_combo.addItem(user.get('name', ''), user.get('id'))
        user_combo.setEnabled(False)
        link_device_check.toggled.connect(user_combo.setEnabled)
        style_form_controls(ip_start_input, ip_end_input, user_combo)

        ip_form.addRow("بداية النطاق:", ip_start_input)
        ip_form.addRow("نهاية النطاق:", ip_end_input)
        ip_form.addRow("", require_ip_check)
        ip_form.addRow("", link_device_check)
        ip_form.addRow("المستخدم المسموح له:", user_combo)
        content_layout.addWidget(ip_group)

        buttons_layout, save_btn, cancel_btn = action_row("حفظ")
        cancel_btn.clicked.connect(dialog.reject)
        footer_layout.addLayout(buttons_layout)

        def save():
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(dialog, "خطأ", "يرجى إدخال اسم الفرع")
                return

            payload = (
                name,
                type_combo.currentData(),
                city_input.text().strip(),
                address_input.text().strip(),
                phone_input.text().strip(),
                manager_input.text().strip(),
                ip_start_input.text().strip() or None,
                ip_end_input.text().strip() or None,
                require_ip_check.isChecked(),
                active_check.isChecked(),
            )

            if store:
                ok = self.ctrl.update_store(store['id'], *payload)
                store_id = store['id'] if ok else None
            else:
                store_id = self.ctrl.add_store(*payload)
                ok = bool(store_id)

            if not ok:
                QMessageBox.critical(dialog, "خطأ", "فشل حفظ الفرع")
                return

            if link_device_check.isChecked() and store_id:
                device = self._current_device_info()
                linked = self.ctrl.add_authorized_device(
                    device["device_id"],
                    device["device_name"],
                    device["mac_address"],
                    store_id,
                    user_combo.currentData(),
                    self.user_info.get('id', 1),
                    f"تم الربط تلقائياً من إدارة الفروع: {name}",
                )
                if not linked:
                    QMessageBox.warning(dialog, "تنبيه", "تم حفظ الفرع لكن فشل ربط الجهاز")
                else:
                    QMessageBox.information(dialog, "نجاح", "تم حفظ الفرع وربط الجهاز")
                    dialog.accept()
                    self._load_branches()
                    if hasattr(self, 'devices_table'):
                        self._load_devices()
                    return

            QMessageBox.information(dialog, "نجاح", "تم حفظ الفرع بنجاح")
            dialog.accept()
            self._load_branches()

        save_btn.clicked.connect(save)
        dialog.exec()

    def _delete_branch(self, store: dict):
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            f"هل أنت متأكد من حذف فرع '{store.get('store_name', '')}'؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok, message = self.ctrl.delete_store(store['id'])
            if ok:
                QMessageBox.information(self, "نجاح", message)
                self._load_branches()
            else:
                QMessageBox.critical(self, "خطأ", message)

    # ═══════════════════════════════════════════════════
    #  Load All
    # ═══════════════════════════════════════════════════
    def _load_all(self):
        try:
            current_widget = self.stack.currentWidget()
            if current_widget == self.stack.widget(0):
                self._load_users()
            elif current_widget == self.stack.widget(1):
                self._load_drawers()
            elif current_widget == self.stack.widget(2):
                self._load_branches()
            elif current_widget == self.stack.widget(3):
                if hasattr(self, 'audit_table'):
                    self._load_audit_logs()
            else:
                if hasattr(self, 'devices_table') and self.devices_table.isVisible():
                    self._load_devices()
                if hasattr(self, 'pending_count_lbl') and self.pending_count_lbl.isVisible():
                    self._load_sync_stats()
        except Exception as e:
            logger.error(f"Error loading admin data: {e}")

    # ── Devices Logic ──────────────────────────────────
    def _load_devices(self):
        devices = self.ctrl.get_authorized_devices()
        self.devices_table.setRowCount(len(devices))
        for row, d in enumerate(devices):
            id_item = center_item(d.get('id', ''))
            id_item.setData(Qt.ItemDataRole.UserRole, d.get('id'))
            self.devices_table.setItem(row, 0, id_item)
            set_center_item(self.devices_table, row, 1, d.get('device_id', ''))
            set_center_item(self.devices_table, row, 2, d.get('device_name', ''))
            set_center_item(self.devices_table, row, 3, d.get('mac_address', ''))
            set_center_item(self.devices_table, row, 4, d.get('store_name') or 'جميع الفروع')
            set_center_item(self.devices_table, row, 5, d.get('user_name') or 'جميع المستخدمين')

            is_active = d.get('is_active', False)
            status_item = center_item("✅ مفعّل" if is_active else "🚫 معطّل")
            status_item.setForeground(QColor("#27ae60" if is_active else "#e74c3c"))
            self.devices_table.setItem(row, 6, status_item)

            last_used = d.get('last_used')
            last_str = last_used.strftime('%Y-%m-%d %H:%M') if isinstance(last_used, datetime) else str(last_used or 'لم يُستخدم بعد')
            set_center_item(self.devices_table, row, 7, last_str)
            set_center_item(self.devices_table, row, 8, d.get('notes', '') or '')

    def _selected_device_record_id(self):
        selected_rows = self.devices_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار جهاز من الجدول أولاً")
            return None
        row = selected_rows[0].row()
        item = self.devices_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _assign_user_to_device(self):
        selected_rows = self.devices_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار جهاز من الجدول أولاً")
            return
        row = selected_rows[0].row()
        self._show_device_dialog({
            "device_id": self.devices_table.item(row, 1).text(),
            "device_name": self.devices_table.item(row, 2).text(),
            "mac_address": self.devices_table.item(row, 3).text(),
        })

    def _show_device_dialog(self, device_data: dict = None):
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة مستخدم لجهاز" if device_data else "إضافة جهاز مصرح به")
        style_dialog(dialog, min_width=560)
        _, content_layout, footer_layout = scrollable_dialog_layout(dialog)
        group = QGroupBox("معلومات الجهاز")
        form = QFormLayout(group)
        configure_form_layout(form)

        current = device_data or self._current_device_info()
        name_in = QLineEdit(current.get("device_name", ""))
        id_in = QLineEdit(current.get("device_id", ""))
        mac_in = QLineEdit(current.get("mac_address", ""))
        if device_data:
            id_in.setReadOnly(True)
            mac_in.setReadOnly(True)

        store_combo = QComboBox()
        store_combo.addItem("جميع الفروع", None)
        for s in self.ctrl.get_all_stores():
            store_combo.addItem(s['store_name'], s['id'])
            
        user_combo = QComboBox()
        user_combo.addItem("جميع المستخدمين", None)
        for u in self.ctrl.get_all_users():
            user_combo.addItem(u['name'], u['id'])

        form.addRow("اسم الجهاز:", name_in)
        form.addRow("معرف الجهاز:", id_in)
        form.addRow("عنوان MAC:", mac_in)
        form.addRow("الفرع المرتبط:", store_combo)
        form.addRow("المستخدم المرتبط:", user_combo)
        notes_input = QTextEdit()
        notes_input.setMaximumHeight(80)
        notes_input.setPlaceholderText("ملاحظات إضافية...")
        form.addRow("ملاحظات:", notes_input)
        style_form_controls(name_in, id_in, mac_in, store_combo, user_combo, notes_input)
        content_layout.addWidget(group)

        buttons_layout, save_btn, cancel_btn = action_row("حفظ")
        cancel_btn.clicked.connect(dialog.reject)
        footer_layout.addLayout(buttons_layout)

        def save():
            if not id_in.text().strip() or not name_in.text().strip() or not mac_in.text().strip():
                QMessageBox.warning(dialog, "خطأ", "معرّف الجهاز واسم الجهاز و MAC مطلوبة")
                return
            if self.ctrl.add_authorized_device(
                id_in.text().strip(), name_in.text().strip(), mac_in.text().strip(),
                store_combo.currentData(), user_combo.currentData(),
                self.user_info.get('id', 1), notes_input.toPlainText().strip()
            ):
                QMessageBox.information(dialog, "نجاح", "تم تسجيل الجهاز بنجاح")
                dialog.accept()
                self._load_devices()
            else:
                QMessageBox.critical(dialog, "خطأ", "فشل تسجيل الجهاز")
        
        save_btn.clicked.connect(save)
        dialog.exec()

    def _set_selected_device_status(self, new_status: bool):
        device_id = self._selected_device_record_id()
        if not device_id:
            return
        if not new_status:
            reply = QMessageBox.question(
                self,
                "تأكيد",
                "هل أنت متأكد من تعطيل هذا التصريح؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        if self.ctrl.update_device_status(device_id, new_status):
            QMessageBox.information(self, "نجاح", "تم تحديث حالة الجهاز")
            self._load_devices()

    def _delete_selected_device(self):
        device_id = self._selected_device_record_id()
        if not device_id:
            return
        if QMessageBox.question(self, "تأكيد", "هل أنت متأكد من حذف هذا التصريح نهائياً؟") == QMessageBox.StandardButton.Yes:
            if self.ctrl.delete_device(device_id):
                QMessageBox.information(self, "نجاح", "تم حذف الجهاز")
                self._load_devices()

    # ── Cloud Logic ────────────────────────────────────
    def _load_sync_stats(self):
        stats = self.ctrl.get_sync_stats()
        self.pending_count_lbl.setText(str(stats['pending_count']))
        last_sync = stats['last_sync_time']
        self.last_sync_lbl.setText(last_sync.strftime('%Y-%m-%d %H:%M') if isinstance(last_sync, datetime) else str(last_sync or 'لا توجد بيانات'))

    def _start_cloud_sync(self):
        QMessageBox.information(self, "مزامنة", "هذه الخاصية قيد التطوير وسيتم تفعيلها قريباً.")
        self._load_sync_stats()


    # ============================================================
    #  Audit Logs Tab
    # ============================================================
    def _create_audit_logs_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("📝 سجل المراقبة والتدقيق")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        refresh_btn = self._make_table_button("🔄 تحديث", "info")
        refresh_btn.clicked.connect(self._load_audit_logs)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)

        # Table
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(8)
        self.audit_table.setHorizontalHeaderLabels([
            "#", "المستخدم", "الفرع", "الإجراء", "نوع الكيان", "رقم الكيان", "الحالة", "التاريخ والوقت"
        ])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.audit_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.audit_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.audit_table.setColumnWidth(0, 80)
        configure_table(self.audit_table, TABLE_STYLE)
        
        # Double click to view details
        self.audit_table.cellDoubleClicked.connect(self._view_audit_details)

        layout.addWidget(self.audit_table)
        
        # Instructions
        help_lbl = QLabel("💡 نصيحة: انقر نقراً مزدوجاً على أي صف لعرض التفاصيل الكاملة.")
        help_lbl.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(help_lbl)

        return container

    def _load_audit_logs(self):
        if not hasattr(self, 'audit_table'):
            return
            
        try:
            logs = self.ctrl.get_audit_logs(limit=100)
            self.audit_table.setRowCount(0)
            
            if not logs:
                return
                
            self.audit_table.setRowCount(len(logs))
            for row, log in enumerate(logs):
                set_center_item(self.audit_table, row, 0, str(log.get('id', '')))
                set_center_item(self.audit_table, row, 1, log.get('user_name', '') or 'نظام')
                set_center_item(self.audit_table, row, 2, log.get('store_name', '') or '---')
                set_center_item(self.audit_table, row, 3, log.get('action', ''))
                set_center_item(self.audit_table, row, 4, log.get('entity_type', '') or '---')
                set_center_item(self.audit_table, row, 5, str(log.get('entity_id', '')) or '---')
                
                success = log.get('success', 1)
                status_item = QTableWidgetItem("✅ نجاح" if success else "❌ فشل")
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if not success:
                    status_item.setForeground(QColor("#e74c3c"))
                else:
                    status_item.setForeground(QColor("#2ecc71"))
                self.audit_table.setItem(row, 6, status_item)
                
                created_at = log.get('created_at')
                date_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else ""
                set_center_item(self.audit_table, row, 7, date_str)
                
                # Store details in the row for double-click retrieval
                details = log.get('details', '')
                self.audit_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, details)
                
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تحميل سجل التدقيق: {str(e)}")

    def _view_audit_details(self, row: int, col: int):
        details = self.audit_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        action = self.audit_table.item(row, 3).text()
        
        if not details:
            details = "لا توجد تفاصيل إضافية مسجلة لهذه العملية."
            
        import json
        try:
            # Try to format json if it's json string
            parsed = json.loads(details)
            formatted_details = json.dumps(parsed, ensure_ascii=False, indent=4)
        except:
            formatted_details = str(details)
            
        msg = QMessageBox(self)
        msg.setWindowTitle(f"تفاصيل العملية: {action}")
        msg.setText("التفاصيل المسجلة:")
        msg.setDetailedText(formatted_details)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
