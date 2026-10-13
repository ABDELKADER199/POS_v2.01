import os

file_path = r'd:\Python Desktop\POS_V2\ui\admin_view.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

audit_methods = """
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
        
        refresh_btn = self._make_table_button("🔄 تحديث", "secondary")
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
            logs = self.ctrl.get_audit_logs(limit=1000)
            self.audit_table.setRowCount(0)
            
            if not logs:
                return
                
            self.audit_table.setRowCount(len(logs))
            from PyQt6.QtGui import QColor
            from PyQt6.QtWidgets import QTableWidgetItem
            from PyQt6.QtCore import Qt
            for row, log in enumerate(logs):
                self._set_center_item(self.audit_table, row, 0, str(log.get('id', '')))
                self._set_center_item(self.audit_table, row, 1, log.get('user_name', '') or 'نظام')
                self._set_center_item(self.audit_table, row, 2, log.get('store_name', '') or '---')
                self._set_center_item(self.audit_table, row, 3, log.get('action', ''))
                self._set_center_item(self.audit_table, row, 4, log.get('entity_type', '') or '---')
                self._set_center_item(self.audit_table, row, 5, str(log.get('entity_id', '')) or '---')
                
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
                self._set_center_item(self.audit_table, row, 7, date_str)
                
                # Store details in the row for double-click retrieval
                details = log.get('details', '')
                self.audit_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, details)
                
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تحميل سجل التدقيق: {str(e)}")

    def _view_audit_details(self, row: int, col: int):
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtCore import Qt
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
"""

if "def _create_audit_logs_tab" not in content:
    content += "\n" + audit_methods
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added audit methods.")
else:
    print("Already added.")
