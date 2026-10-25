from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QWidget, QGridLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from ui.styles import COLORS, GLOBAL_STYLE, get_button_style

class ProfitLossDialog(QDialog):
    """
    نافذة تفصيلية لتقرير الأرباح والخسائر (Profit & Loss Statement)
    تعرض الإيرادات، التكاليف (COGS)، والمصروفات التشغيلية بشكل محاسبي منظم.
    """
    
    def __init__(self, start_date, end_date, store_id, stats_controller, user_info, parent=None):
        super().__init__(parent)
        self.start_date = start_date
        self.end_date = end_date
        self.store_id = store_id
        self.controller = stats_controller
        self.user_info = user_info
        self.pdf_data = None
        
        self.setWindowTitle("تقرير الأرباح والخسائر (Profit & Loss)")
        self.setMinimumSize(800, 700)
        self.setStyleSheet(GLOBAL_STYLE)
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border-bottom: 1px solid {COLORS['border']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        title_box = QVBoxLayout()
        title = QLabel("📄 قائمة الدخل (الأرباح والخسائر)")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_on_brand']};")
        
        period_lbl = QLabel(f"الفترة: من {self.start_date} إلى {self.end_date}")
        period_lbl.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        
        title_box.addWidget(title)
        title_box.addWidget(period_lbl)
        
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        # Actions
        btn_print = QPushButton("🖨️ تصدير PDF")
        btn_print.setStyleSheet(get_button_style('primary'))
        btn_print.clicked.connect(self.export_pdf)
        
        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet(get_button_style('danger'))
        btn_close.clicked.connect(self.close)
        
        header_layout.addWidget(btn_print)
        header_layout.addWidget(btn_close)
        
        main_layout.addWidget(header)
        
        # Body (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        container = QWidget()
        container.setStyleSheet(f"background-color: {COLORS['bg_main']};")
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(30, 30, 30, 30)
        self.content_layout.setSpacing(15)
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def load_data(self):
        try:
            report = self.controller.get_profit_loss_data(
                self.start_date, self.end_date, self.store_id, self.user_info
            )
            # The application use case returns these values pre-calculated with
            # Decimal.  This dialog only renders them.
            total_sales = report.total_sales
            total_returns = report.total_returns
            net_sales = report.net_sales
            adjusted_net_sales = report.adjusted_net_sales
            total_cogs = report.total_cogs
            total_returned_cost = report.total_returned_cost
            net_cogs = report.net_cogs
            gross_profit = report.gross_profit
            total_expenses = report.total_expenses
            net_profit = report.net_profit
            
            # --- Render UI Sections ---
            
            # SECTION 1: REVENUES
            self.add_section_header("الإيرادات (Revenues)", "#3B82F6")
            self.add_line_item("إجمالي المبيعات", total_sales)
            self.add_line_item("يُخصم: المرتجعات", -total_returns, is_deduction=True)
            self.add_subtotal("صافي المبيعات (Net Sales)", net_sales, "#10B981")
            self.add_line_item("مطالبات عروض الموردين", report.supplier_promotion_claims)
            self.add_subtotal("صافي المبيعات المعدلة", adjusted_net_sales, "#10B981")
            
            self.add_separator()
            
            # SECTION 2: COGS
            self.add_section_header("تكلفة المبيعات (COGS)", "#F59E0B")
            self.add_line_item("تكلفة البضاعة المباعة", total_cogs)
            self.add_line_item("يُخصم: تكلفة البضاعة المرتجعة", -total_returned_cost, is_deduction=True)
            self.add_subtotal("صافي تكلفة المبيعات", net_cogs, "#F59E0B")
            
            self.add_separator()
            
            # GROSS PROFIT
            self.add_subtotal("مُجمل الربح (Gross Profit)", gross_profit, "#8B5CF6", font_size=18)
            
            self.add_separator()
            
            # SECTION 3: OPERATING EXPENSES
            self.add_section_header("المصروفات التشغيلية (Op. Expenses)", "#EF4444")
            
            if report.expenses:
                for exp in report.expenses:
                    self.add_line_item(exp.expense_type, exp.total)
            else:
                lbl = QLabel("لا توجد مصروفات مسجلة لهذه الفترة")
                lbl.setStyleSheet("color: #6B7280; font-style: italic;")
                self.content_layout.addWidget(lbl)
                
            self.add_subtotal("إجمالي المصروفات التشغيلية", total_expenses, "#EF4444")
            
            self.add_separator(height=3)
            
            # FINAL NET PROFIT
            net_profit_color = "#10B981" if net_profit >= 0 else "#EF4444"
            self.add_subtotal("صافي الربح الفعلي (Net Profit)", net_profit, net_profit_color, font_size=22)
            
            
            self.pdf_data = report

        except Exception as e:
            # Technical details remain in the application log, not in a financial UI.
            import logging
            logging.getLogger(__name__).error("Unable to load P&L report: %s", e, exc_info=True)
            QMessageBox.critical(self, "خطأ", "تعذر تحميل قائمة الدخل. لم يتم إنشاء تقرير بديل.")

    def add_section_header(self, text, indicator_color):
        lbl = QLabel(text)
        lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_on_brand']}; border-left: 4px solid {indicator_color}; padding-left: 10px; margin-top: 10px;")
        self.content_layout.addWidget(lbl)

    def add_line_item(self, text, value, is_deduction=False):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(20, 5, 20, 5)
        
        lbl_text = QLabel(text)
        lbl_text.setStyleSheet("color: #D1D5DB; font-size: 14px;")
        
        color = "#EF4444" if is_deduction else "#F3F4F6"
        operator = "− " if is_deduction else ""
        if value < 0:
            value = abs(value) # Handle negative display cleanly
        
        lbl_val = QLabel(f"{operator}{value:,.2f} ج.م")
        lbl_val.setStyleSheet(f"color: {color}; font-size: 14px;")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(lbl_text)
        layout.addWidget(lbl_val)
        
        self.content_layout.addWidget(row)

    def add_subtotal(self, text, value, text_color, font_size=16):
        row = QWidget()
        row.setStyleSheet(f"background-color: rgba(255, 255, 255, 0.03); border-radius: 6px;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(15, 10, 15, 10)
        
        lbl_text = QLabel(text)
        lbl_text.setFont(QFont("Arial", font_size - 2, QFont.Weight.Bold))
        lbl_text.setStyleSheet(f"color: {COLORS['text_on_brand']};")
        
        lbl_val = QLabel(f"{value:,.2f} ج.م")
        lbl_val.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {text_color};")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(lbl_text)
        layout.addWidget(lbl_val)
        
        self.content_layout.addWidget(row)
        
    def add_separator(self, height=1):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {COLORS['border']}; border: none; height: {height}px; margin: 5px 0px;")
        self.content_layout.addWidget(line)

    def export_pdf(self):
        try:
            if not self.pdf_data:
                QMessageBox.warning(self, "تنبيه", "لا توجد قائمة دخل صالحة للتصدير.")
                return
            store_name = getattr(self.parent(), "store_combo", None)
            store_name = store_name.currentText() if store_name else "الفرع المحدد"
            user_name = self.user_info.get("name") or self.user_info.get("username") or "مستخدم"
            result = self.controller.export_profit_loss(
                self.start_date, self.end_date, self.store_id, self.user_info, store_name, user_name
            )
            if result.get("saved"):
                QMessageBox.information(self, "نجاح", "تم حفظ تقرير الأرباح والخسائر كـ PDF بنجاح")
            else:
                QMessageBox.warning(self, "خطأ", "فشل أثناء حفظ الملف")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Unable to export P&L PDF: %s", e, exc_info=True)
            QMessageBox.critical(self, "خطأ", "تعذر تصدير قائمة الدخل.")
