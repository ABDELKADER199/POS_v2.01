from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QWidget, QGridLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from ui.styles import COLORS, GLOBAL_STYLE, get_button_style
from datetime import datetime

class ProfitLossDialog(QDialog):
    """
    نافذة تفصيلية لتقرير الأرباح والخسائر (Profit & Loss Statement)
    تعرض الإيرادات، التكاليف (COGS)، والمصروفات التشغيلية بشكل محاسبي منظم.
    """
    
    def __init__(self, start_date, end_date, store_id, db_manager, parent=None):
        super().__init__(parent)
        self.start_date = start_date
        self.end_date = end_date
        self.store_id = store_id
        self.db = db_manager
        
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
            # 1. Fetch Profit Stats
            stats = self.db.get_net_profit_stats(self.start_date, self.end_date, self.store_id)
            
            total_sales = stats.get('total_sales', 0)
            total_returns = stats.get('total_returns', 0)
            net_sales = total_sales - total_returns
            
            total_cogs = stats.get('total_cogs', 0)
            total_returned_cost = stats.get('total_returned_cost', 0)
            net_cogs = total_cogs - total_returned_cost
            
            gross_profit = net_sales - net_cogs
            
            # 2. Expenses Breakdown
            expenses_breakdown = self.db.get_expenses_breakdown(self.start_date, self.end_date, self.store_id)
            total_expenses = sum(float(x['total']) for x in expenses_breakdown)
            
            net_profit = gross_profit - total_expenses
            
            # --- Render UI Sections ---
            
            # SECTION 1: REVENUES
            self.add_section_header("الإيرادات (Revenues)", "#3B82F6")
            self.add_line_item("إجمالي المبيعات", total_sales)
            self.add_line_item("يُخصم: المرتجعات", -total_returns, is_deduction=True)
            self.add_subtotal("صافي المبيعات (Net Sales)", net_sales, "#10B981")
            
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
            
            if expenses_breakdown:
                for exp in expenses_breakdown:
                    self.add_line_item(exp['expense_type'] or "أخرى", float(exp['total']))
            else:
                lbl = QLabel("لا توجد مصروفات مسجلة لهذه الفترة")
                lbl.setStyleSheet("color: #6B7280; font-style: italic;")
                self.content_layout.addWidget(lbl)
                
            self.add_subtotal("إجمالي المصروفات التشغيلية", total_expenses, "#EF4444")
            
            self.add_separator(height=3)
            
            # FINAL NET PROFIT
            net_profit_color = "#10B981" if net_profit >= 0 else "#EF4444"
            self.add_subtotal("صافي الربح الفعلي (Net Profit)", net_profit, net_profit_color, font_size=22)
            
            
            # Store values for PDF export
            self.pdf_data = {
                'sales': total_sales,
                'returns': total_returns,
                'net_sales': net_sales,
                'cogs': total_cogs,
                'ret_cogs': total_returned_cost,
                'net_cogs': net_cogs,
                'gross': gross_profit,
                'expenses': expenses_breakdown,
                'total_exp': total_expenses,
                'net_profit': net_profit
            }

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء تحميل البيانات: {e}")

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
            from utils.printer_service import PrinterService
            
            d = self.pdf_data
            expenses_html = ""
            for exp in d['expenses']:
                expenses_html += f"""
                <tr>
                    <td style='padding: 5px; color: #555;'>{exp['expense_type']}</td>
                    <td style='padding: 5px; text-align: left;'>{float(exp['total']):,.2f}</td>
                </tr>
                """
                
            if not expenses_html:
                expenses_html = "<tr><td colspan='2' style='text-align:center;'>لا يوجد مصروفات</td></tr>"
                
            net_color = "#10B981" if d['net_profit'] >= 0 else "#EF4444"
            
            html = f"""
            <html dir="rtl">
            <body style="font-family: Arial; padding: 20px; color: #333;">
                <h2 style="text-align: center; color: #2C3E50;">تقرير الأرباح والخسائر (Statement of Profit & Loss)</h2>
                <p style="text-align: center; color: #7F8C8D;">الفترة: {self.start_date} إلى {self.end_date}</p>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px;">
                    <!-- REVENUES -->
                    f"<tr style=\"background-color: #3B82F6; color: {COLORS['text_on_brand']};\">"
                        <th colspan="2" style="padding: 8px; text-align: right;">1. الإيرادات (Revenues)</th>
                    </tr>
                    <tr><td style="padding: 5px;">إجمالي المبيعات</td><td style="text-align: left;">{d['sales']:,.2f}</td></tr>
                    <tr><td style="padding: 5px; color: red;">يُخصم: المرتجعات</td><td style="text-align: left; color: red;">− {d['returns']:,.2f}</td></tr>
                    <tr style="font-weight: bold; background-color: #f8f9fa;">
                        <td style="padding: 8px;">صافي المبيعات</td><td style="text-align: left;">{d['net_sales']:,.2f}</td>
                    </tr>
                    
                    <!-- COGS -->
                    f"<tr style=\"background-color: #F59E0B; color: {COLORS['text_on_brand']};\">"
                        <th colspan="2" style="padding: 8px; text-align: right; margin-top: 10px;">2. تكلفة المبيعات (COGS)</th>
                    </tr>
                    <tr><td style="padding: 5px;">تكلفة البضاعة المباعة</td><td style="text-align: left;">{d['cogs']:,.2f}</td></tr>
                    <tr><td style="padding: 5px; color: red;">يُخصم: تكلفة البضاعة المرتجعة</td><td style="text-align: left; color: red;">− {d['ret_cogs']:,.2f}</td></tr>
                    <tr style="font-weight: bold; background-color: #f8f9fa;">
                        <td style="padding: 8px;">صافي التكلفة</td><td style="text-align: left;">{d['net_cogs']:,.2f}</td>
                    </tr>
                    
                    <!-- GROSS PROFIT -->
                    <tr style="font-size: 16px; font-weight: bold; background-color: #E0E7FF;">
                        <td style="padding: 10px;">مُجمل الربح (Gross Profit)</td><td style="text-align: left; color: #4F46E5;">{d['gross']:,.2f}</td>
                    </tr>
                    
                    <!-- EXPENSES -->
                    f"<tr style=\"background-color: #EF4444; color: {COLORS['text_on_brand']};\">"
                        <th colspan="2" style="padding: 8px; text-align: right; margin-top: 10px;">3. المصروفات التشغيلية (Expenses)</th>
                    </tr>
                    {expenses_html}
                    <tr style="font-weight: bold; background-color: #f8f9fa;">
                        <td style="padding: 8px;">إجمالي المصروفات</td><td style="text-align: left;">{d['total_exp']:,.2f}</td>
                    </tr>
                    
                    <!-- NET PROFIT -->
                    <tr style="font-size: 18px; font-weight: bold; background-color: #F3F4F6;">
                        <td style="padding: 15px;">صافي الربح الفعلي (Net Profit)</td><td style="text-align: left; color: {net_color};">{d['net_profit']:,.2f} ج.م</td>
                    </tr>
                </table>
            </body>
            </html>
            """
            
            success = PrinterService._save_as_pdf(html, 595, filename_prefix="Profit_Loss_Statement")
            if success:
                QMessageBox.information(self, "نجاح", "تم حفظ تقرير الأرباح والخسائر كـ PDF بنجاح")
            else:
                QMessageBox.warning(self, "خطأ", "فشل أثناء حفظ الملف")
                
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء تصدير PDF: {e}")
