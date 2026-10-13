"""Accounts PDF Report Service - خدمة تقارير الحسابات بصيغة PDF"""
import html
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.stats_pdf_report_service import StatsPdfReportService
from utils.printer_service import PrinterService


class AccountsPdfReportService:
    """توليد تقارير PDF موحدة للحسابات والمالية"""

    def create_customer_account_pdf(
        self,
        customer_data: Dict,
        account_history: List[Dict],
        user_name: str,
        store_name: str,
    ) -> Dict[str, Any]:
        """إنشاء تقرير حساب عميل بصيغة PDF"""
        html_content = self._build_customer_account_html(customer_data, account_history, user_name, store_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"customer_account_{customer_data.get('name', 'Unknown')}_{timestamp}"
        saved, pdf_path = PrinterService._save_as_pdf(
            html_content,
            width_pts=595,
            filename_prefix=filename,
            category="تقارير الحسابات",
            auto_open=False,
        )
        return {"saved": saved, "pdf_path": pdf_path}

    def create_debt_aging_pdf(
        self,
        aging_data: List[Dict],
        store_name: str,
        user_name: str,
    ) -> Dict[str, Any]:
        """إنشاء تقرير تقادم الديون بصيغة PDF"""
        html_content = self._build_aging_html(aging_data, store_name, user_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"debt_aging_report_{timestamp}"
        saved, pdf_path = PrinterService._save_as_pdf(
            html_content,
            width_pts=595,
            filename_prefix=filename,
            category="تقارير الديون",
            auto_open=False,
        )
        return {"saved": saved, "pdf_path": pdf_path}

    def create_financial_ledger_pdf(
        self,
        ledger_data: List[Dict],
        store_name: str,
        user_name: str,
    ) -> Dict[str, Any]:
        """إنشاء تقرير السجل المالي بصيغة PDF"""
        html_content = self._build_ledger_html(ledger_data, store_name, user_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"financial_ledger_{timestamp}"
        saved, pdf_path = PrinterService._save_as_pdf(
            html_content,
            width_pts=595,
            filename_prefix=filename,
            category="تقارير مالية",
            auto_open=False,
        )
        return {"saved": saved, "pdf_path": pdf_path}

    def create_ledger_pdf(
        self,
        ledger_data: List[Dict],
        store_name: str,
        user_name: str,
    ) -> Dict[str, Any]:
        """اسم متوافق لإنشاء تقرير السجل المالي."""
        return self.create_financial_ledger_pdf(ledger_data, store_name, user_name)

    def create_treasury_pdf(
        self,
        transactions: List[Dict],
        balance: float,
        store_name: str,
        user_name: str,
    ) -> Dict[str, Any]:
        """إنشاء تقرير حركة الخزينة بصيغة PDF"""
        html_content = self._build_treasury_html(transactions, balance, store_name, user_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"treasury_report_{timestamp}"
        saved, pdf_path = PrinterService._save_as_pdf(
            html_content,
            width_pts=595,
            filename_prefix=filename,
            category="تقارير الخزينة",
            auto_open=False,
        )
        return {"saved": saved, "pdf_path": pdf_path}

    def create_expense_pdf(
        self,
        expenses: List[Dict],
        store_name: str,
        user_name: str,
    ) -> Dict[str, Any]:
        """إنشاء تقرير المصروفات بصيغة PDF"""
        html_content = self._build_expense_html(expenses, store_name, user_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"expense_report_{timestamp}"
        saved, pdf_path = PrinterService._save_as_pdf(
            html_content,
            width_pts=595,
            filename_prefix=filename,
            category="تقارير المصروفات",
            auto_open=False,
        )
        return {"saved": saved, "pdf_path": pdf_path}

    # ── HTML Builders ────────────────────────────────────

    def _build_customer_account_html(
        self,
        customer_data: Dict,
        account_history: List[Dict],
        user_name: str,
        store_name: str,
    ) -> str:
        rows = ""
        for item in account_history:
            rows += f"""
            <tr>
                <td style="text-align:center; padding:4px;">{item.get('date', '-')}</td>
                <td style="text-align:center; padding:4px;">{item.get('description', '-')}</td>
                <td style="text-align:center; padding:4px;">{float(item.get('amount', 0) or 0):,.2f}</td>
                <td style="text-align:center; padding:4px;">{float(item.get('balance', 0) or 0):,.2f}</td>
            </tr>
            """
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""
        <!doctype html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="utf-8">
            <title>كشف حساب عميل</title>
            <style>
                body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; background: #eef3fb; color: #0f172a; margin: 0; padding: 0; }}
                .page {{ width: 100%; background: #fff; padding: 18px; }}
                .cover {{ background: #10224a; color: #fff; padding: 18px; border-bottom: 5px solid #2563eb; }}
                .brand {{ color: #bfdbfe; font-size: 12px; font-weight: 900; }}
                .title {{ color: #fff; font-size: 24px; font-weight: 900; margin-top: 5px; }}
                .meta {{ color: #dbeafe; font-size: 11px; line-height: 1.8; margin-top: 8px; }}
                table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 10px; }}
                th {{ background: #2563eb; color: #fff; padding: 8px; text-align: center; font-size: 11px; }}
                td {{ padding: 7px 6px; font-size: 10px; text-align: center; border-bottom: 1px solid #dbe3ef; }}
                .total-box {{ background: #f8fafc; border: 2px solid #2563eb; padding: 10px; margin-top: 10px; font-size: 12px; font-weight: 800; }}
            </style>
        </head>
        <body>
            <div class="page">
                <div class="cover">
                    <div class="brand">نظام POS - تقرير كشف حساب عميل</div>
                    <div class="title">كشف حساب العميل</div>
                    <div class="meta">
                        <div>المتجر: {store_name}</div>
                        <div>المستخدم: {user_name}</div>
                        <div>العميل: {customer_data.get('name', '-')}</div>
                        <div>الهاتف: {customer_data.get('phone', '-')}</div>
                        <div>التاريخ: {generated_at}</div>
                    </div>
                </div>
                <div style="padding: 14px;">
                    <table>
                        <thead>
                            <tr>
                                <th>التاريخ</th>
                                <th>الوصف</th>
                                <th>المبلغ</th>
                                <th>الرصيد</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else '<tr><td colspan="4">لا توجد حركات</td></tr>'}
                        </tbody>
                    </table>
                    <div class="total-box">
                        الرصيد الحالي: <span style="float:left;">{float(customer_data.get('current_balance', 0) or 0):,.2f} ج.م</span>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def _build_aging_html(self, aging_data: List[Dict], store_name: str, user_name: str) -> str:
        rows = ""
        for item in aging_data:
            rows += f"""
            <tr>
                <td style="text-align:center; padding:4px;">{item.get('customer_name', '-')}</td>
                <td style="text-align:center; padding:4px;">{item.get('current', 0):.2f}</td>
                <td style="text-align:center; padding:4px;">{item.get('over_30', 0):.2f}</td>
                <td style="text-align:center; padding:4px;">{item.get('over_60', 0):.2f}</td>
                <td style="text-align:center; padding:4px;">{item.get('over_90', 0):.2f}</td>
                <td style="text-align:center; padding:4px; font-weight:900;">{item.get('total_due', 0):.2f}</td>
            </tr>
            """
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""
        <!doctype html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="utf-8">
            <title>تقرير تقادم الديون</title>
            <style>
                body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; background: #eef3fb; color: #0f172a; margin: 0; padding: 0; }}
                .page {{ width: 100%; background: #fff; padding: 18px; }}
                .cover {{ background: #10224a; color: #fff; padding: 18px; border-bottom: 5px solid #2563eb; }}
                .brand {{ color: #bfdbfe; font-size: 12px; font-weight: 900; }}
                .title {{ color: #fff; font-size: 24px; font-weight: 900; margin-top: 5px; }}
                .meta {{ color: #dbeafe; font-size: 11px; line-height: 1.8; margin-top: 8px; }}
                table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 10px; }}
                th {{ background: #2563eb; color: #fff; padding: 8px; text-align: center; font-size: 11px; }}
                td {{ padding: 7px 6px; font-size: 10px; text-align: center; border-bottom: 1px solid #dbe3ef; }}
            </style>
        </head>
        <body>
            <div class="page">
                <div class="cover">
                    <div class="brand">نظام POS - تقرير تقادم الديون</div>
                    <div class="title">تقرير تقادم الديون</div>
                    <div class="meta">
                        <div>المتجر: {store_name}</div>
                        <div>المستخدم: {user_name}</div>
                        <div>التاريخ: {generated_at}</div>
                    </div>
                </div>
                <div style="padding: 14px;">
                    <table>
                        <thead>
                            <tr>
                                <th>العميل</th>
                                <th>الحالي</th>
                                <th>30+ يوم</th>
                                <th>60+ يوم</th>
                                <th>90+ يوم</th>
                                <th>الإجمالي</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else '<tr><td colspan="6">لا توجد ديون مسجلة</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """

    def _build_ledger_html(self, ledger_data: List[Dict], store_name: str, user_name: str) -> str:
        rows = ""
        for item in ledger_data:
            amount_str = f"{float(item.get('amount', 0) or 0):,.2f}"
            amount_color = "#2563eb" if float(item.get('amount', 0) or 0) >= 0 else "#dc2626"
            rows += f"""
            <tr>
                <td style="text-align:center; padding:4px;">{item.get('date', '-')}</td>
                <td style="text-align:center; padding:4px;">{item.get('description', '-')}</td>
                <td style="text-align:center; padding:4px; color:{amount_color}; font-weight:900;">{amount_str}</td>
                <td style="text-align:center; padding:4px;">{float(item.get('balance', 0) or 0):,.2f}</td>
            </tr>
            """
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""
        <!doctype html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="utf-8">
            <title>السجل المالي</title>
            <style>
                body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; background: #eef3fb; color: #0f172a; margin: 0; padding: 0; }}
                .page {{ width: 100%; background: #fff; padding: 18px; }}
                .cover {{ background: #10224a; color: #fff; padding: 18px; border-bottom: 5px solid #2563eb; }}
                .brand {{ color: #bfdbfe; font-size: 12px; font-weight: 900; }}
                .title {{ color: #fff; font-size: 24px; font-weight: 900; margin-top: 5px; }}
                .meta {{ color: #dbeafe; font-size: 11px; line-height: 1.8; margin-top: 8px; }}
                table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 10px; }}
                th {{ background: #2563eb; color: #fff; padding: 8px; text-align: center; font-size: 11px; }}
                td {{ padding: 7px 6px; font-size: 10px; text-align: center; border-bottom: 1px solid #dbe3ef; }}
            </style>
        </head>
        <body>
            <div class="page">
                <div class="cover">
                    <div class="brand">نظام POS - السجل المالي</div>
                    <div class="title">السجل المالي العام</div>
                    <div class="meta">
                        <div>المتجر: {store_name}</div>
                        <div>المستخدم: {user_name}</div>
                        <div>التاريخ: {generated_at}</div>
                    </div>
                </div>
                <div style="padding: 14px;">
                    <table>
                        <thead>
                            <tr>
                                <th>التاريخ</th>
                                <th>الوصف</th>
                                <th>المبلغ</th>
                                <th>الرصيد</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else '<tr><td colspan="4">لا توجد حركات</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """

    def _build_treasury_html(self, transactions: List[Dict], balance: float, store_name: str, user_name: str) -> str:
        rows = ""
        for item in transactions:
            amount_str = f"{float(item.get('amount', 0) or 0):,.2f}"
            amount_color = "#2563eb" if float(item.get('amount', 0) or 0) >= 0 else "#dc2626"
            rows += f"""
            <tr>
                <td style="text-align:center; padding:4px;">{item.get('date', '-')}</td>
                <td style="text-align:center; padding:4px;">{item.get('description', '-')}</td>
                <td style="text-align:center; padding:4px; color:{amount_color}; font-weight:900;">{amount_str}</td>
                <td style="text-align:center; padding:4px;">{float(item.get('balance_after', 0) or 0):,.2f}</td>
            </tr>
            """
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""
        <!doctype html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="utf-8">
            <title>تقرير حركة الخزينة</title>
            <style>
                body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; background: #eef3fb; color: #0f172a; margin: 0; padding: 0; }}
                .page {{ width: 100%; background: #fff; padding: 18px; }}
                .cover {{ background: #10224a; color: #fff; padding: 18px; border-bottom: 5px solid #2563eb; }}
                .brand {{ color: #bfdbfe; font-size: 12px; font-weight: 900; }}
                .title {{ color: #fff; font-size: 24px; font-weight: 900; margin-top: 5px; }}
                .meta {{ color: #dbeafe; font-size: 11px; line-height: 1.8; margin-top: 8px; }}
                table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 10px; }}
                th {{ background: #2563eb; color: #fff; padding: 8px; text-align: center; font-size: 11px; }}
                td {{ padding: 7px 6px; font-size: 10px; text-align: center; border-bottom: 1px solid #dbe3ef; }}
            </style>
        </head>
        <body>
            <div class="page">
                <div class="cover">
                    <div class="brand">نظام POS - حركة الخزينة</div>
                    <div class="title">تقرير حركة الخزينة</div>
                    <div class="meta">
                        <div>المتجر: {store_name}</div>
                        <div>المستخدم: {user_name}</div>
                        <div>التاريخ: {generated_at}</div>
                        <div>الرصيد الحالي: {balance:,.2f} ج.م</div>
                    </div>
                </div>
                <div style="padding: 14px;">
                    <table>
                        <thead>
                            <tr>
                                <th>التاريخ</th>
                                <th>الوصف</th>
                                <th>المبلغ</th>
                                <th>الرصيد</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else '<tr><td colspan="4">لا توجد حركات</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """

    def _build_expense_html(self, expenses: List[Dict], store_name: str, user_name: str) -> str:
        rows = ""
        for item in expenses:
            rows += f"""
            <tr>
                <td style="text-align:center; padding:4px;">{item.get('date', '-')}</td>
                <td style="text-align:center; padding:4px;">{item.get('expense_type', '-')}</td>
                <td style="text-align:center; padding:4px;">{float(item.get('amount', 0) or 0):,.2f}</td>
                <td style="text-align:center; padding:4px;">{item.get('description', '-')}</td>
            </tr>
            """
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""
        <!doctype html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="utf-8">
            <title>تقرير المصروفات</title>
            <style>
                body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; background: #eef3fb; color: #0f172a; margin: 0; padding: 0; }}
                .page {{ width: 100%; background: #fff; padding: 18px; }}
                .cover {{ background: #10224a; color: #fff; padding: 18px; border-bottom: 5px solid #2563eb; }}
                .brand {{ color: #bfdbfe; font-size: 12px; font-weight: 900; }}
                .title {{ color: #fff; font-size: 24px; font-weight: 900; margin-top: 5px; }}
                .meta {{ color: #dbeafe; font-size: 11px; line-height: 1.8; margin-top: 8px; }}
                table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 10px; }}
                th {{ background: #2563eb; color: #fff; padding: 8px; text-align: center; font-size: 11px; }}
                td {{ padding: 7px 6px; font-size: 10px; text-align: center; border-bottom: 1px solid #dbe3ef; }}
            </style>
        </head>
        <body>
            <div class="page">
                <div class="cover">
                    <div class="brand">نظام POS - تقرير المصروفات</div>
                    <div class="title">تقرير المصروفات</div>
                    <div class="meta">
                        <div>المتجر: {store_name}</div>
                        <div>المستخدم: {user_name}</div>
                        <div>التاريخ: {generated_at}</div>
                    </div>
                </div>
                <div style="padding: 14px;">
                    <table>
                        <thead>
                            <tr>
                                <th>التاريخ</th>
                                <th>النوع</th>
                                <th>المبلغ</th>
                                <th>الوصف</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else '<tr><td colspan="4">لا توجد مصروفات مسجلة</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
