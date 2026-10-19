
import os
from datetime import datetime
from dataclasses import dataclass
from html import escape
from typing import Optional
try:
    import qrcode
    import io
    import base64
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    import base64 # Still needed for barcode Base64
    import io

@dataclass(frozen=True)
class BarcodePrintJob:
    """Immutable barcode label print request."""
    name: str
    code: str
    printer_name: str = ""
    label_size: str = "40x25"
    price: Optional[str] = None
    store_name: Optional[str] = None
    copies: int = 1


class PrinterService:
    """Service to handle printing receipts and labels using HTML-safe layouts."""

    BARCODE_LABEL_SPECS = {
        "50x30": {
            "width": 141.7,
            "height": 85.0,
            "image_height": 40,
            "name_font": 10,
            "meta_font": 9,
            "name_row": 20,
            "meta_row": 18,
            "padding": 4,
        },
        "40x25": {
            "width": 110.0,
            "height": 70.0,
            "image_height": 30,
            "name_font": 7,
            "meta_font": 5,
            "name_row": 15,
            "meta_row": 12,
            "padding": 4,
        },
        "30x20": {
            "width": 85.0,
            "height": 56.7,
            "image_height": 28,
            "name_font": 7,
            "meta_font": 6,
            "name_row": 12,
            "meta_row": 10,
            "padding": 2,
        },
    }

    @staticmethod
    def _load_settings():
        """Load settings from the new repository layer without depending on legacy modules."""
        try:
            from repositories.settings_repo import SettingsRepository
            return SettingsRepository().get_all()
        except Exception:
            return {}
    
    @staticmethod
    def _get_common_styles():
        """Returns CSS styles common to all receipt types."""
        return """
            * {
                box-sizing: border-box;
            }
            body {
                direction: rtl;
                font-family: 'Tahoma', 'Arial', sans-serif;
                font-size: 11px;
                margin: 0;
                padding: 0;
                width: 100%;
                color: #111827;
                background-color: #fff;
            }
            .receipt {
                width: 100%;
                max-width: 72mm;
                margin: 0 auto;
                padding: 2px 2px;
            }
            .header {
                text-align: center;
                padding-bottom: 6px;
                border-bottom: 1px dashed #111827;
            }
            .store-name {
                font-size: 17px;
                font-weight: 900;
                color: #000;
                line-height: 1.25;
                margin: 0 0 2px;
            }
            .branch-info {
                font-size: 9px;
                font-weight: 700;
                color: #374151;
                line-height: 1.4;
            }
            .receipt-title {
                display: inline-block;
                font-size: 12px;
                font-weight: 900;
                border: 1px solid #111827;
                border-radius: 10px;
                padding: 3px 14px;
                margin-top: 6px;
                background-color: #f3f4f6;
            }
            .meta-card {
                margin: 7px 0;
                padding: 5px 7px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                background-color: #f9fafb;
            }
            .meta-info {
                width: 100%;
                font-size: 10px;
                font-weight: bold;
                border-collapse: collapse;
            }
            .meta-info td {
                padding: 2px 0;
                border: none;
            }
            .meta-info .label {
                text-align: right;
                width: 40%;
                color: #374151;
            }
            .meta-info .value {
                text-align: left;
                width: 60%;
                color: #000;
            }
            .customer-section {
                margin: 7px 0;
                padding: 5px 7px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                text-align: center;
                background-color: #f9fafb;
            }
            .customer-title {
                display: inline-block;
                font-weight: 900;
                font-size: 10px;
                margin-bottom: 4px;
                padding: 1px 8px;
                border-radius: 8px;
                background-color: #111827;
                color: #fff;
            }
            .customer-info {
                font-size: 10px;
                line-height: 1.45;
            }
            table.items-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 7px;
            }
            table.items-table th {
                border-top: 1px solid #111827;
                border-bottom: 1px solid #111827;
                padding: 5px 3px;
                font-size: 10px;
                font-weight: 900;
                text-align: right;
                background-color: #f3f4f6;
            }
            table.items-table td {
                padding: 6px 3px;
                font-size: 10px;
                vertical-align: top;
                border-bottom: 1px dotted #cbd5e1;
            }
            .item-name {
                font-weight: 900;
                font-size: 11px;
                margin-bottom: 2px;
                display: block;
                color: #111827;
                line-height: 1.35;
            }
            .item-details {
                font-size: 9px;
                color: #4b5563;
            }
            .item-total {
                text-align: left;
                font-weight: 900;
                font-size: 11px;
                vertical-align: middle;
            }
            .totals-section {
                margin-top: 8px;
                padding: 7px;
                border: 1px solid #111827;
                border-radius: 8px;
                background-color: #fff;
            }
            .total-table {
                width: 100%;
                border-collapse: collapse;
            }
            .total-table td {
                padding: 3px 0;
                border: none;
            }
            .total-label {
                text-align: right;
                font-weight: 800;
                font-size: 10px;
                color: #374151;
            }
            .total-value {
                text-align: left;
                font-weight: 900;
                font-size: 11px;
                color: #000;
            }
            .grand-total td {
                padding: 7px 0 5px;
                border-top: 1px solid #111827;
                font-size: 14px;
            }
            .grand-total .total-label,
            .grand-total .total-value {
                font-size: 14px;
                color: #000;
            }
            .footer {
                text-align: center;
                margin-top: 9px;
                font-size: 9px;
                font-weight: 700;
                border-top: 1px dashed #111827;
                padding-top: 7px;
                line-height: 1.5;
            }
            .divider {
                border-top: 1px dashed #111827;
                margin: 7px 0;
                height: 0;
            }
            .barcode-container {
                text-align: center;
                margin-top: 8px;
                padding-top: 6px;
                border-top: 1px dotted #cbd5e1;
                width: 100%;
            }
            .barcode-img {
                max-width: 130px;
                height: auto;
            }
        """

    @staticmethod
    def _get_qr_code_html(invoice_data, store_name, tax_number):
        """Generates an E-Invoice QR code based on ZATCA/Egyptian standard (Base64 TLV)."""
        if not QR_AVAILABLE:
            return "<!-- QR Library not installed -->"
        try:
            
            from utils.zatca_qr import ZatcaQRCoder
            now = datetime.now()
            timestamp_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
            qr_payload = ZatcaQRCoder.generate_base64(
                seller_name=store_name or 'المتجر',
                tax_number=tax_number or '000000000000000',
                timestamp_iso=timestamp_iso,
                total_with_vat=float(invoice_data.get('total_amount', 0)),
                vat_amount=float(invoice_data.get('tax_amount', 0))
            )
            qr = qrcode.QRCode(version=1, box_size=3, border=1)
            qr.add_data(qr_payload)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return f"""
            <div style="text-align: center; margin-top: 10px;">
                <img src="data:image/png;base64,{qr_base64}" style="width: 100px; height: 100px;">
                <div style="font-size: 8px; color: #666; margin-top: 2px;">فاتورة ضريبية إلكترونية</div>
            </div>
            """
        except Exception as e:
            print(f"QR Error: {e}")
            return ""

    @staticmethod
    def _get_barcode_html(code):
        """Generates a small barcode HTML fragment."""
        if not code:
            return ""
        try:
            from utils.barcode_service import BarcodeService
            import base64
            barcode_path = BarcodeService.generate_barcode(str(code), "", label_size="40x25")
            if barcode_path and os.path.exists(barcode_path):
                with open(barcode_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                return f"""
                <div class="barcode-container">
                    <img src="data:image/png;base64,{b64_string}" class="barcode-img">
                    <div style="font-size: 8px; margin-top: 2px;">{code}</div>
                </div>
                """
        except Exception:
            pass
        safe_code = escape(str(code))
        return f"""
        <div class="barcode-container">
            <div style="font-size: 8px; font-weight: 800;">رقم الفاتورة: {safe_code}</div>
        </div>
        """

    @staticmethod
    def _money(value):
        try:
            return f"{float(value or 0):,.2f}"
        except (TypeError, ValueError):
            return "0.00"

    @staticmethod
    def _payment_method_label(method):
        labels = {
            "Cash": "كاش",
            "Card": "فيزا",
            "Credit": "آجل",
            "Mixed": "مختلط",
        }
        return labels.get(str(method or "Cash"), str(method or "Cash"))

    @staticmethod
    def _generate_receipt_html(invoice_data, items, user_name, settings, is_order=False):
        """Generates modern HTML for sales receipts and orders."""
        rows = ""
        for index, item in enumerate(items, start=1):
            raw_name = str(item.get('product_name', 'Unknown') or 'Unknown')
            if len(raw_name) > 30:
                raw_name = raw_name[:28] + ".."
            name = escape(raw_name)
            qty = float(item.get('quantity', 0) or 0)
            price = float(item.get('price', item.get('unit_price', 0)) or 0)
            total = float(item.get('total', qty * price) or 0)
            line_disc = float(item.get('line_discount', item.get('discount', 0)) or 0)
            disc_str = f" - خصم: {PrinterService._money(line_disc)}" if line_disc > 0 else ""
            rows += f"""
            <tr>
                <td style="width: 78%; padding: 3px 1px; font-size: 9px; vertical-align: middle; border-bottom: 1px dotted #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 195px;">
                    <span style="font-weight: 600; color: #111827; font-size: 9.5px;">{index}. {name}</span>
                    <span style="font-size: 8px; color: #4b5563; margin-right: 3px;">({PrinterService._money(qty)} × {PrinterService._money(price)}{disc_str})</span>
                </td>
                <td class="item-total" style="width: 22%; padding: 3px 1px; font-size: 9.5px; font-weight: 600; text-align: left; vertical-align: middle; border-bottom: 1px dotted #cbd5e1; white-space: nowrap;">{PrinterService._money(total)}</td>
            </tr>
            """

        customer_html = ""
        if invoice_data.get('customer_name'):
            customer_name = escape(str(invoice_data.get('customer_name') or ''))
            customer_phone = escape(str(invoice_data.get('customer_phone') or ''))
            customer_address = escape(str(invoice_data.get('customer_address') or ''))
            customer_html = f"""
            <div class="customer-section">
                <div class="customer-title">بيانات العميل{"/ توصيل" if is_order else ""}</div>
                <div class="customer-info">
                    <strong>{customer_name}</strong>
                    {f'<br>{customer_phone}' if customer_phone else ''}
                    {f'<br>{customer_address}' if customer_address else ''}
                </div>
            </div>
            """

        # --- Corporate Tax Invoice Section (B2B) ---
        tax_invoice_info = invoice_data.get('tax_invoice_data')
        is_tax_invoice = bool(tax_invoice_info)
        
        corporate_html = ""
        if is_tax_invoice:
            company_name = escape(str(tax_invoice_info.get('company_name', '') or ''))
            tax_id_number = escape(str(tax_invoice_info.get('tax_id_number', '') or ''))
            commercial_registry = escape(str(tax_invoice_info.get('commercial_registry', '') or ''))
            company_address = escape(str(tax_invoice_info.get('company_address', '') or ''))
            company_phone = escape(str(tax_invoice_info.get('company_phone', '') or ''))
            corporate_html = f"""
            <div class="customer-section">
                <div class="customer-title">بيانات المشتري الضريبي</div>
                <table style="width: 100%; font-size: 11px; font-weight: bold; border-collapse: collapse;">
                    <tr><td style="text-align:right; width:38%; padding:2px 0;">الشركة:</td><td style="text-align:left;">{company_name}</td></tr>
                    {f'<tr><td style="text-align:right; padding:2px 0;">الرقم الضريبي:</td><td style="text-align:left;">{tax_id_number}</td></tr>' if tax_id_number else ''}
                    {f'<tr><td style="text-align:right; padding:2px 0;">السجل التجاري:</td><td style="text-align:left;">{commercial_registry}</td></tr>' if commercial_registry else ''}
                    {f'<tr><td style="text-align:right; padding:2px 0;">العنوان:</td><td style="text-align:left;">{company_address}</td></tr>' if company_address else ''}
                    {f'<tr><td style="text-align:right; padding:2px 0;">الهاتف:</td><td style="text-align:left;">{company_phone}</td></tr>' if company_phone else ''}
                </table>
            </div>
            """

        receipt_title = "فاتورة ضريبية" if is_tax_invoice else ("طلب توصيل" if is_order else "فاتورة مبيعات")

        payment_details = ""
        method = invoice_data.get('payment_method', 'Cash')
        if method == 'Mixed':
            payment_details = f"""
            <tr><td class="total-label">نقداً:</td><td class="total-value">{PrinterService._money(invoice_data.get('cash_amount', 0))}</td></tr>
            <tr><td class="total-label">فيزا:</td><td class="total-value">{PrinterService._money(invoice_data.get('card_amount', 0))}</td></tr>
            """
        else:
            payment_details = f"""<tr><td class="total-label">طريقة الدفع:</td><td class="total-value">{PrinterService._payment_method_label(method)}</td></tr>"""

        store_name = escape(str(settings.get('store_name', 'نظام POS') or 'نظام POS'))
        legal_name = escape(str(settings.get('business_legal_name', store_name) or store_name))
        tax_number = escape(str(settings.get('tax_number', '') or ''))
        store_address = escape(str(settings.get('store_address', '') or ''))
        store_phone = escape(str(settings.get('store_phone', '') or ''))
        receipt_footer = escape(str(settings.get('receipt_footer', 'شكراً لزيارتكم') or 'شكراً لزيارتكم'))
        invoice_number = escape(str(invoice_data.get('invoice_number', '-') or '-'))
        cashier = escape(str(user_name or '-'))
        drawer_id = escape(str(invoice_data.get('drawer_id', '-') or '-'))
        tax_html = ""
        if float(invoice_data.get("tax_amount", 0) or 0) > 0:
            tax_html = f"""
            <tr><td class="total-label">ضريبة القيمة المضافة:</td><td class="total-value">{PrinterService._money(invoice_data.get("tax_amount", 0))}</td></tr>
            """
        manual_discount_html = ""
        if float(invoice_data.get("discount", 0) or 0) > 0:
            manual_discount_html = f"""
            <tr><td class="total-label">الخصم اليدوي:</td><td class="total-value">-{PrinterService._money(invoice_data.get("discount", 0))}</td></tr>
            """
        promo_discount_html = ""
        if float(invoice_data.get("promo_discount", 0) or 0) > 0:
            promo_discount_html = f"""
            <tr><td class="total-label">خصم العروض:</td><td class="total-value">-{PrinterService._money(invoice_data.get("promo_discount", 0))}</td></tr>
            """
        tendered_html = ""
        if float(invoice_data.get("tendered", 0) or 0) > 0:
            tendered_html = f"""
            <tr><td class="total-label">المدفوع:</td><td class="total-value">{PrinterService._money(invoice_data.get("tendered", 0))}</td></tr>
            <tr><td class="total-label">الباقي:</td><td class="total-value">{PrinterService._money(invoice_data.get("change", 0))}</td></tr>
            """

        credit_statement_html = ""
        if method in ('Credit', 'آجل') or invoice_data.get('is_credit') or invoice_data.get('customer_balance_due') is not None:
            prev_balance = float(invoice_data.get('previous_customer_balance', 0) or 0)
            current_invoice_total = float(invoice_data.get('total_amount', invoice_data.get('total', 0)) or 0)
            total_balance_due = prev_balance + current_invoice_total
            credit_statement_html = f"""
            <div style="margin-top: 10px; padding: 8px; border: 1px dashed #1e293b; border-radius: 6px; background-color: #f8fafc; font-size: 10px;">
                <div style="font-weight: 900; margin-bottom: 4px; text-align: center; color: #0f172a;">📋 كشف حساب العميل الآجل</div>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td>الرصيد السابق:</td><td style="text-align: left; font-weight: bold;">{PrinterService._money(prev_balance)}</td></tr>
                    <tr><td>قيمة الفاتورة الحالية:</td><td style="text-align: left; font-weight: bold;">{PrinterService._money(current_invoice_total)}</td></tr>
                    <tr style="border-top: 1px solid #cbd5e1; font-weight: 900;"><td>إجمالي الرصيد المستحق:</td><td style="text-align: left; color: #dc2626;">{PrinterService._money(total_balance_due)}</td></tr>
                </table>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <style>{PrinterService._get_common_styles()}</style>
        </head>
        <body>
            <div class="receipt">
                <div class="header">
                    <div class="store-name">{legal_name}</div>
                    <div class="branch-info">
                        {f'الرقم الضريبي: {tax_number}<br>' if tax_number else ''}
                        {store_address}{'<br>' if store_address and store_phone else ''}{store_phone}
                    </div>
                    <div class="receipt-title">{receipt_title}</div>
                </div>
                <div class="meta-card">
                    <table class="meta-info">
                        <tr>
                            <td class="label">رقم الفاتورة:</td>
                            <td class="value">#{invoice_number}</td>
                        </tr>
                        <tr>
                            <td class="label">التاريخ:</td>
                            <td class="value">{datetime.now().strftime('%Y-%m-%d %H:%M')}</td>
                        </tr>
                        <tr>
                            <td class="label">الكاشير:</td>
                            <td class="value">{cashier} (د-{drawer_id})</td>
                        </tr>
                    </table>
                </div>

                {corporate_html}
                {customer_html}

                <table class="items-table">
                    <thead>
                        <tr>
                            <th style="width: 78%; text-align: right; padding: 4px 1px; font-size: 9.5px;">الصنف</th>
                            <th style="width: 22%; text-align: left; padding: 4px 1px; font-size: 9.5px;">الإجمالي</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>

                <div class="totals-section">
                    <table class="total-table">
                        <tr><td class="total-label">المجموع قبل الخصم:</td><td class="total-value">{PrinterService._money(invoice_data.get('subtotal', 0))}</td></tr>
                        {tax_html}
                        {manual_discount_html}
                        {promo_discount_html}
                        {payment_details}
                        <tr class="grand-total">
                            <td class="total-label">الصافي:</td>
                            <td class="total-value">{PrinterService._money(invoice_data.get('total_amount', 0))} ج.م</td>
                        </tr>
                        {tendered_html}
                    </table>
                    {credit_statement_html}
                </div>

                <div class="footer">
                    {receipt_footer}<br>
                    يرجى الاحتفاظ بالفاتورة في حال الاستبدال أو الاسترجاع (14 يوماً)
                </div>

                {PrinterService._get_qr_code_html(invoice_data, legal_name, tax_number) if (settings.get('tax_enabled') == '1' or is_tax_invoice) else ''}
                {PrinterService._get_barcode_html(invoice_number)}
            </div>
        </body>
        </html>
        """
        return html

    @staticmethod
    def _generate_return_receipt_html(return_data, items, user_name, settings):
        """Generates modern HTML for return receipts."""
        rows = ""
        for item in items:
            name = item.get('product_name', 'Unknown')
            qty = item.get('quantity', 0)
            price = item.get('unit_price', 0)
            total = item.get('total_price', qty * price)
            rows += f"""
            <tr>
                <td>
                    <span class="item-name">{name}</span>
                    <span class="item-details">{qty} x {price:.2f}</span>
                </td>
                <td class="item-total">{total:.2f}</td>
            </tr>
            """

        store_name = settings.get('store_name', 'نظام POS')
        store_address = settings.get('store_address', '')
        store_phone = settings.get('store_phone', '')
        receipt_footer = settings.get('receipt_footer', 'شكراً لزيارتكم')

        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <style>{PrinterService._get_common_styles()}</style>
        </head>
        <body>
            <div class="receipt">
                <div class="header">
                    <div class="store-name">{store_name}</div>
                    <div class="branch-info">{store_address}<br>{store_phone}</div>
                    <div class="return-badge">*** إيصال مرتجع ***</div>
                    <table class="meta-info">
                        <tr>
                            <td class="label">رقم المرتجع: {return_data.get('return_number')}</td>
                            <td class="value" style="text-align:left">{datetime.now().strftime('%Y-%m-%d %H:%M')}</td>
                        </tr>
                        <tr>
                            <td class="label">فاتورة الأصل: #{return_data.get('invoice_number')}</td>
                            <td class="value" style="text-align:left">الموظف: {user_name}</td>
                        </tr>
                    </table>
                </div>

                <table class="items-table">
                    <thead>
                         <tr>
                            <th style="width: 65%; text-align: right; padding-right: 5px;">الصنف</th>
                            <th style="width: 35%; text-align: left; padding-left: 5px;">السعر</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>

                <div class="totals-section">
                    <table class="total-table">
                        <tr class="grand-total" style="color: #c53030;">
                            <td class="total-label">إجمالي المرتجع:</td> 
                            <td class="total-value">{return_data.get('total_amount', 0):.2f} ج.م</td>
                        </tr>
                    </table>
                </div>

                <div style="margin-top: 10px; font-size: 11px; color: #4a5568;">
                    <strong>السبب:</strong> {return_data.get('reason', '-')}
                </div>

                <div class="footer">
                    {receipt_footer}<br>
                    تم استرداد المبلغ نقداً
                </div>

                {PrinterService._get_barcode_html(return_data.get('return_number', '000'))}
            </div>
        </body>
        </html>
        """
        return html

    @staticmethod
    def _save_as_pdf(html_content, width_pts, filename_prefix="Document", category="الفواتير", auto_open=True):
        """Saves HTML content to a PDF file and opens it. Category can be 'invoices', 'returns', etc."""
        try:
            from PyQt6.QtCore import QCoreApplication
            if QCoreApplication.instance() is None:
                return False, None

            from PyQt6.QtGui import QTextDocument, QPageLayout, QPageSize
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtCore import QSizeF, QMarginsF
            import os
            import subprocess
            import sys

            # 1. Arabic Month Names
            arabic_months = {
                1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
                5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
                9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
            }
            
            now = datetime.now()
            month_name = arabic_months.get(now.month, str(now.month))
            year_name = str(now.year)

            # 2. Create nested directory structure.
            category_parts = [part for part in str(category).replace("\\", "/").split("/") if part]
            if category_parts and category_parts[0] == "الخزينة":
                base_category_dir = os.path.join(os.getcwd(), *category_parts)
            else:
                root_pdf_dir = os.path.join(os.getcwd(), "الفواتير")
                base_category_dir = os.path.join(root_pdf_dir, *category_parts)
            final_month_dir = os.path.join(base_category_dir, year_name, month_name)
            
            if not os.path.exists(final_month_dir):
                os.makedirs(final_month_dir)

            # 3. Generate filename
            filename = f"{filename_prefix}.pdf"
            pdf_path = os.path.join(final_month_dir, filename)

            # 4. Setup Printer for PDF
            printer = QPrinter() 
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(pdf_path)

            # 5. Content setup
            doc = QTextDocument()
            doc.setMetaInformation(QTextDocument.MetaInformation.DocumentTitle, filename_prefix)
            doc.setDocumentMargin(0)
            doc.setHtml(html_content)
            doc.setTextWidth(width_pts)
            
            is_small_label = width_pts < 150 
            real_height = doc.size().height() + (0 if is_small_label else 20)

            custom_size = QPageSize(QSizeF(width_pts, real_height), QPageSize.Unit.Point)
            layout = QPageLayout(custom_size, QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0))
            printer.setPageLayout(layout)
            printer.setFullPage(True)
            
            doc.setPageSize(QSizeF(width_pts, real_height))
            doc.print(printer)

            # 6. Open PDF if requested
            if os.path.exists(pdf_path):
                if auto_open:
                    if os.name == 'nt':  # Windows
                        os.startfile(pdf_path)
                    elif os.name == 'posix':  # macOS/Linux
                        subprocess.run(['open', pdf_path] if sys.platform == 'darwin' else ['xdg-open', pdf_path])
                return True, pdf_path
            return False, None

        except Exception as e:
            print(f"PDF Save Error: {e}")
            return False, None

    @staticmethod
    def _is_virtual_printer(printer_info):
        """Helper to detect virtual printers (Fax, XPS, etc.)"""
        if not printer_info or printer_info.isNull():
            return True
        
        name = printer_info.printerName().lower()
        # Common virtual/system-only printers on Windows
        virtual_names = [
            'fax', 'xps', 'one note', 'onenote', 'print to pdf', 
            'microsoft pdf', 'send to', 'virtual', 'writer', 'redirected',
            'pdf', 'fax', 'cute-pdf', 'do-pdf'
        ]
        return any(vn in name for vn in virtual_names)

    @staticmethod
    def _print_html_document(html_content, receipt_height_est=600, width_pts=None, printer_name=None, filename_prefix="Document", category="الفواتير"):
        """Unified method to print HTML content, fallback to PDF if no physical printer."""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QTextDocument, QPageLayout, QPageSize
            from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo
            from PyQt6.QtCore import QSizeF, QMarginsF
            import os

            # Determine width
            thermal_width_pts = 226 # ~80mm
            p_width = width_pts or thermal_width_pts

            # 1. Setup Printer
            printer_info = None
            if printer_name:
                available_printers = QPrinterInfo.availablePrinters()
                for p in available_printers:
                    if p.printerName() == printer_name:
                        printer_info = p
                        break
            
            if not printer_info:
                printer_info = QPrinterInfo.defaultPrinter()

            # 2. Always save a silent copy in the organized folders (Silent Archive)
            success_save, pdf_path = PrinterService._save_as_pdf(html_content, p_width, filename_prefix, category=category, auto_open=False)

            # 3. Robust Fallback Logic for actual printing
            if not printer_info or printer_info.isNull() or PrinterService._is_virtual_printer(printer_info):
                # We already saved the PDF in step 2.
                # If we don't have a real printer, we just return the success of the save.
                return {"printed": False, "saved": success_save, "pdf_path": pdf_path}

            # 4. Physical Printing Attempt
            try:
                printer = QPrinter(printer_info)
                printer.setPrinterName(printer_info.printerName())
                
                doc = QTextDocument()
                doc.setMetaInformation(QTextDocument.MetaInformation.DocumentTitle, filename_prefix)
                doc.setDocumentMargin(0) 
                doc.setHtml(html_content)
                doc.setTextWidth(p_width)
                
                is_small_label = p_width < 150
                real_height = doc.size().height() + (0 if is_small_label else 20)
                
                custom_size = QPageSize(QSizeF(p_width, real_height), QPageSize.Unit.Point)
                layout = QPageLayout(custom_size, QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0))
                
                printer.setPageLayout(layout)
                doc.setPageSize(QSizeF(p_width, real_height))
                doc.print(printer)
                return {"printed": True, "saved": success_save, "pdf_path": pdf_path}
            except Exception as e:
                print(f"❌ Physical printing failed: {e}")
                return {"printed": False, "saved": success_save, "pdf_path": pdf_path}

        except Exception as e:
            print(f"Printing Service Error: {e}")
            return {"printed": False, "saved": False, "pdf_path": None}

    @staticmethod
    def _format_barcode_price(price) -> str:
        if price in (None, ""):
            return ""
        try:
            return f"{float(price):.2f} ج.م"
        except (TypeError, ValueError):
            return escape(str(price))

    @staticmethod
    def print_barcode_labels(job: BarcodePrintJob) -> int:
        """Print a barcode job and return the number of successfully printed labels."""
        copies = max(1, int(job.copies or 1))
        success_count = 0
        for _ in range(copies):
            if PrinterService.print_barcode_direct(
                job.name,
                job.code,
                job.printer_name,
                label_size=job.label_size,
                price=job.price,
                store_name=job.store_name,
            ):
                success_count += 1
        return success_count

    @staticmethod
    def print_barcode_direct(name, code, printer_name, label_size="40x25", price=None, store_name=None):
        """Prints a single barcode label directly to a specified printer."""
        try:
            from utils.barcode_service import BarcodeService
            import base64
            
            # Use write_text=False to allow manual HTML layout control
            path = BarcodeService.generate_barcode(code, name, label_size=label_size, write_text=False)
            if not path or not os.path.exists(path):
                return False
            
            with open(path, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode()
            
            price_str = PrinterService._format_barcode_price(price)
            
            # === QTextDocument-compatible layouts (table-based, NO flex) ===
            common_style = "margin:0; padding:0; font-family:'Arial', sans-serif; background-color:white; color:black;"
            if label_size == "50x30":
                w_pts = 141.7  # 50mm
                h_pts = 85.0   # 30mm
                img_w_pts = w_pts - 20
                
                html = f"""
                <html>
                <body style="{common_style}">
                    <table width="{w_pts}pt" height="{h_pts}pt" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; table-layout:fixed;">
                        <tr height="20pt">
                            <td align="center" valign="middle" style="padding:2pt 4pt 0 4pt;">
                                <div style="font-size:10pt; font-weight:bold; line-height:1.1; white-space:nowrap; overflow:hidden;">{name}</div>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" valign="middle" style="padding:2pt 4pt;">
                                <img src="data:image/png;base64,{b64_img}" style="width:{img_w_pts}pt; height:40pt; object-fit:contain;">
                            </td>
                        </tr>
                        <tr height="18pt">
                            <td align="center" valign="top" style="padding:0 4pt 2pt 4pt;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td align="right" style="font-size:9pt; font-weight:bold; width:50%;">{code}</td>
                                        <td align="left" style="font-size:9pt; font-weight:bold; width:50%; direction:rtl;">{price_str}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """
            elif label_size == "30x20":
                w_pts = 85.0   # 30mm
                h_pts = 56.7   # 20mm
                img_w_pts = w_pts - 10

                html = f"""
                <html>
                <body style="{common_style}">
                    <table width="{w_pts}pt" height="{h_pts}pt" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; table-layout:fixed;">
                        <tr height="12pt">
                            <td align="center" valign="middle" style="padding:1pt 2pt 0 2pt;">
                                <div style="font-size:7pt; font-weight:bold; line-height:1; white-space:nowrap; overflow:hidden;">{name}</div>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" valign="middle" style="padding:1pt 2pt;">
                                <img src="data:image/png;base64,{b64_img}" style="width:{img_w_pts}pt; height:28pt; object-fit:contain;">
                            </td>
                        </tr>
                        <tr height="10pt">
                            <td align="center" valign="top" style="padding:0 2pt;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td align="right" style="font-size:6pt; width:50%;">{code}</td>
                                        <td align="left" style="font-size:6pt; font-weight:bold; width:50%;">{price_str}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """
            else:  # 40x25 (Classic compact layout)
                w_pts = 110  # 40mm
                h_pts = 70   # 25mm
                img_w_pts = w_pts - 14

                html = f"""
                <html>
                <body style="{common_style}">
                    <table width="{w_pts}pt" height="{h_pts}pt" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; table-layout:fixed;">
                        <tr height="15pt">
                            <td align="center" valign="middle" style="padding:2pt 4pt 0 4pt;">
                                <div style="font-size:7pt; font-weight:bold; line-height:1.1; overflow:hidden; white-space:nowrap;">{name}</div>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" valign="middle" style="padding:2pt 4pt;">
                                <img src="data:image/png;base64,{b64_img}" style="width:{img_w_pts}pt; height:30pt; object-fit:contain;">
                            </td>
                        </tr>
                        <tr height="12pt">
                            <td align="center" valign="top" style="padding:0 4pt 2pt 4pt;">
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td align="right" style="font-size:5pt; width:50%;">{code}</td>
                                        <td align="left" style="font-size:5pt; font-weight:bold; width:50%;">{price_str}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """
            
            # === Check for real physical printer ===
            from PyQt6.QtPrintSupport import QPrinterInfo
            
            has_real_printer = False
            if printer_name:
                for p in QPrinterInfo.availablePrinters():
                    if p.printerName() == printer_name and not PrinterService._is_virtual_printer(p):
                        has_real_printer = True
                        break
            
            if not has_real_printer:
                # Check default printer
                default = QPrinterInfo.defaultPrinter()
                if default and not default.isNull() and not PrinterService._is_virtual_printer(default):
                    has_real_printer = True
            
            if has_real_printer:
                # Physical printer found → print normally
                return PrinterService._print_html_document(html, receipt_height_est=h_pts, width_pts=w_pts, printer_name=printer_name, filename_prefix="Barcode")
            else:
                # No physical printer → save as high-DPI PNG image
                return PrinterService._save_barcode_as_image(html, w_pts, h_pts, code, name=name, price_str=price_str, label_size=label_size)
                
        except Exception as e:
            print(f"Barcode Print Error: {e}")
            return False
    
    @staticmethod
    def _save_barcode_as_image(html_content, w_pts, h_pts, code, name="", price_str="", label_size="40x25"):
        """Saves barcode label as a high-DPI PNG image using direct QPainter drawing."""
        try:
            from PyQt6.QtGui import QImage, QPainter, QFont, QColor, QPixmap
            from PyQt6.QtCore import Qt, QRect
            import subprocess

            from utils.barcode_service import BarcodeService
            barcode_path = BarcodeService.generate_barcode(code, name, label_size=label_size, write_text=False)
            if not barcode_path or not os.path.exists(barcode_path):
                print("❌ Barcode file not found")
                return False

            # 300 DPI — professional print quality
            dpi = 300
            scale = dpi / 72.0  # 1 pt = 1/72 inch

            # Convert pt to pixels
            img_w = int(w_pts * scale)
            img_h = int(h_pts * scale)

            # Create white canvas at target pixel size
            image = QImage(img_w, img_h, QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)
            image.setDotsPerMeterX(int(dpi / 0.0254))
            image.setDotsPerMeterY(int(dpi / 0.0254))

            # Load barcode raw image
            barcode_pix = QPixmap(barcode_path)

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            # === Layout zones in pixels (proportional to image size) ===
            margin    = int(img_w * 0.04)      # ~4% margin
            name_h    = int(img_h * 0.17)      # 17% for name
            code_h    = int(img_h * 0.16)      # 16% for code+price
            barcode_h = img_h - margin * 2 - name_h - code_h - int(img_h * 0.04)
            barcode_y = margin + name_h + int(img_h * 0.02)
            bottom_y  = barcode_y + barcode_h + int(img_h * 0.02)

            name_px  = max(int(img_h * 0.10), 18)   # ~10% of label height
            text_px  = max(int(img_h * 0.09), 14)   # ~9% of label height

            # --- Product name (top center, bold) ---
            name_font = QFont("Arial")
            name_font.setPixelSize(name_px)
            name_font.setBold(True)
            painter.setFont(name_font)
            painter.setPen(QColor(0, 0, 0))
            name_rect = QRect(margin, margin, img_w - margin * 2, name_h)
            painter.drawText(name_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, str(name))

            # --- Barcode image (center) ---
            if not barcode_pix.isNull():
                barcode_target = QRect(margin, barcode_y, img_w - margin * 2, barcode_h)
                painter.drawPixmap(barcode_target, barcode_pix.scaled(
                    barcode_target.width(), barcode_target.height(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))

            # --- Code (left) and price (right) at bottom ---
            half_w   = (img_w - margin * 2) // 2
            code_rect  = QRect(margin,             bottom_y, half_w, code_h)
            price_rect = QRect(margin + half_w,    bottom_y, half_w, code_h)

            code_font = QFont("Arial")
            code_font.setPixelSize(text_px)

            price_font = QFont("Arial")
            price_font.setPixelSize(text_px)
            price_font.setBold(True)

            painter.setFont(code_font)
            painter.drawText(code_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(code))

            painter.setFont(price_font)
            painter.drawText(price_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, price_str)

            painter.end()

            # Save
            save_dir = os.path.join(os.getcwd(), "الباركود")
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            safe_code = str(code).replace('/', '_').replace('\\', '_')
            img_path = os.path.join(save_dir, f"barcode_{safe_code}.png")
            image.save(img_path, "PNG")

            if os.path.exists(img_path):
                if os.name == 'nt':
                    os.startfile(img_path)
                print(f"✅ Barcode saved as image: {img_path}")
                return True
            return False
        except Exception as e:
            print(f"❌ Image save error: {e}")
            import traceback; traceback.print_exc()
            return False

    @staticmethod
    def print_receipt(invoice_data, items, user_name, store_name_unused=None, is_order=False):
        """Prints a modern sales receipt or order."""
        settings = PrinterService._load_settings()
        
        est_height = 400 + (len(items) * 45) + (100 if invoice_data.get('customer_name') else 0)
        html = PrinterService._generate_receipt_html(invoice_data, items, user_name, settings, is_order)
        prefix = invoice_data.get('invoice_number', 'Invoice')
        return PrinterService._print_html_document(html, est_height, filename_prefix=prefix, category="فواتير البيع")

    @staticmethod
    def print_return_receipt(return_data, items, user_name, store_name_unused=None):
        """Prints a modern return receipt."""
        settings = PrinterService._load_settings()
        
        est_height = 350 + (len(items) * 45)
        html = PrinterService._generate_return_receipt_html(return_data, items, user_name, settings)
        prefix = return_data.get('return_number', 'Return')
        return PrinterService._print_html_document(html, est_height, filename_prefix=prefix, category="فواتير المرتجعات")

    @staticmethod
    def print_drawer_report(summary_data):
        """Prints a modern drawer report."""
        settings = PrinterService._load_settings()

        html = PrinterService._generate_drawer_report_html(summary_data, settings)
        closed_at = summary_data.get("closed_at") or datetime.now()
        if isinstance(closed_at, datetime):
            stamp = closed_at.strftime("%Y%m%d_%H%M")
        else:
            stamp = datetime.now().strftime("%Y%m%d_%H%M")
        drawer_id = summary_data.get("drawer_id", "drawer")
        prefix = f"غلق_الخزينة_{drawer_id}_{stamp}"
        return PrinterService._print_html_document(
            html,
            800,
            filename_prefix=prefix,
            category=os.path.join("الخزينة", "غلق الخزينة"),
        )

    @staticmethod
    def save_receipt_as_pdf(invoice_data, items, user_name, store_name_unused=None, is_order=False):
        """Explicitly saves a receipt as PDF without trying to print."""
        settings = PrinterService._load_settings()
        
        html = PrinterService._generate_receipt_html(invoice_data, items, user_name, settings, is_order)
        prefix = invoice_data.get('invoice_number', 'Invoice')
        thermal_width_pts = 226
        success, pdf_path = PrinterService._save_as_pdf(html, thermal_width_pts, filename_prefix=prefix, category="فواتير البيع", auto_open=True)
        return {"printed": False, "saved": success, "pdf_path": pdf_path}

    @staticmethod
    def _generate_purchase_invoice_html(invoice_data, items, user_name, settings):
        """Generates modern HTML for purchase invoices."""
        rows = ""
        for item in items:
            raw_name = item.get('product_name') or item.get('name') or item.get('product') or "صنف غير مسمى"
            name = escape(str(raw_name))
            qty = int(item.get('quantity', 0) or 0)
            free_qty = int(item.get('free_quantity', 0) or 0)
            received_qty = int(item.get('received_quantity', qty + free_qty) or 0)
            cost = float(item.get('cost', item.get('unit_cost', item.get('price', 0))) or 0)
            total = float(item.get('total', item.get('total_cost', qty * cost)) or 0)
            qty_details = f"{qty} x {cost:.2f}"
            if free_qty > 0:
                qty_details += f"<br>+ {free_qty} مجاني<br>المستلم: {received_qty}"
            rows += f"""
            <tr>
                <td>
                    <span class="item-name">{name}</span>
                    <span class="item-details">{qty_details}</span>
                </td>
                <td class="item-total">{total:.2f}</td>
            </tr>
            """

        supplier_html = ""
        if invoice_data.get('supplier_name'):
            supplier_html = f"""
            <div class="customer-section">
                <div class="customer-title">المورد</div>
                <div class="customer-info">
                    <strong>{invoice_data.get('supplier_name')}</strong>
                </div>
            </div>
            """

        store_name = settings.get('store_name', 'نظام POS')
        store_address = settings.get('store_address', '')
        store_phone = settings.get('store_phone', '')

        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <style>{PrinterService._get_common_styles()}</style>
        </head>
        <body>
            <div class="receipt">
                <div class="header">
                    <div class="store-name">{store_name}</div>
                    <div class="branch-info">{store_address}<br>{store_phone}</div>
                    <div class="return-badge" style="border: 2px solid #000; padding: 2px; margin: 5px 0;">*** فاتورة مشتريات ***</div>
                    <table class="meta-info">
                        <tr>
                            <td class="label">رقم الفاتورة:</td>
                            <td class="value">#{invoice_data.get('invoice_number', '-')}</td>
                        </tr>
                        <tr>
                            <td class="label">مرجع المورد:</td>
                            <td class="value">{invoice_data.get('ref_number', '-')}</td>
                        </tr>
                        <tr>
                            <td class="label">التاريخ:</td>
                            <td class="value">{datetime.now().strftime('%Y-%m-%d %H:%M')}</td>
                        </tr>
                        <tr>
                            <td class="label">المستخدم:</td>
                            <td class="value">{user_name}</td>
                        </tr>
                    </table>
                </div>

                {supplier_html}

                <table class="items-table">
                    <thead>
                        <tr>
                            <th style="width: 65%; text-align: right; padding-right: 5px;">الصنف</th>
                            <th style="width: 35%; text-align: left; padding-left: 5px;">التكلفة</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>

                <div class="totals-section">
                    <table class="total-table">
                        <tr><td class="total-label">المجموع:</td><td class="total-value">{invoice_data.get('subtotal', 0):.2f}</td></tr>
                        <tr><td class="total-label">الخصم:</td><td class="total-value">-{invoice_data.get('discount', 0):.2f}</td></tr>
                        <tr><td class="total-label">الضريبة:</td><td class="total-value">+{invoice_data.get('tax', 0):.2f}</td></tr>
                        <tr class="grand-total">
                            <td class="total-label">الإجمالي:</td>
                            <td class="total-value">{invoice_data.get('total_amount', 0):.2f} ج.م</td>
                        </tr>
                        <tr><td class="total-label">طريقة الدفع:</td><td class="total-value">{invoice_data.get('payment_method', '-')}</td></tr>
                        <tr><td class="total-label">المدفوع:</td><td class="total-value">{invoice_data.get('paid_amount', 0):.2f}</td></tr>
                        <tr><td class="total-label">المتبقي:</td><td class="total-value">{invoice_data.get('remaining_amount', 0):.2f}</td></tr>
                    </table>
                </div>

                <div class="footer">
                    تم حفظ الفاتورة بنجاح
                </div>
            </div>
        </body>
        </html>
        """
        return html

    @staticmethod
    def save_purchase_invoice_as_pdf(invoice_data, items, user_name):
        """Saves a purchase invoice as PDF."""
        settings = PrinterService._load_settings()
        
        html = PrinterService._generate_purchase_invoice_html(invoice_data, items, user_name, settings)
        prefix = f"Purchase_{invoice_data.get('invoice_number', 'New')}"
        thermal_width_pts = 226
        # Save to specific folder for purchases if needed, for now sticking to category='مشتريات'
        success, pdf_path = PrinterService._save_as_pdf(html, thermal_width_pts, filename_prefix=prefix, category="المشتريات", auto_open=True)
        return {"saved": success, "pdf_path": pdf_path}

    @staticmethod
    def _generate_purchase_return_html(return_data, items, user_name, settings):
        """Generates modern HTML for supplier purchase returns."""
        rows = ""
        for item in items:
            raw_name = item.get("product_name") or item.get("name") or "صنف غير مسمى"
            name = escape(str(raw_name))
            qty = int(item.get("quantity", item.get("return_quantity", 0)) or 0)
            unit_cost = float(item.get("unit_cost", item.get("cost", 0)) or 0)
            total = float(item.get("total", qty * unit_cost) or 0)
            rows += f"""
            <tr>
                <td>
                    <span class="item-name">{name}</span>
                    <span class="item-details">{qty} x {unit_cost:.2f}</span>
                </td>
                <td class="item-total">{total:.2f}</td>
            </tr>
            """

        supplier_name = escape(str(return_data.get("supplier_name") or "-"))
        invoice_number = escape(str(return_data.get("invoice_number") or "-"))
        return_number = escape(str(return_data.get("return_number") or "-"))
        settlement_method = return_data.get("settlement_method")
        settlement_label = "تخفيض مديونية المورد" if settlement_method == "credit" else "استرداد نقدي للخزينة"
        reason = escape(str(return_data.get("reason") or "-"))
        store_name = escape(str(settings.get("store_name", "نظام POS") or "نظام POS"))
        store_address = escape(str(settings.get("store_address", "") or ""))
        store_phone = escape(str(settings.get("store_phone", "") or ""))

        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <style>{PrinterService._get_common_styles()}</style>
        </head>
        <body>
            <div class="receipt">
                <div class="header">
                    <div class="store-name">{store_name}</div>
                    <div class="branch-info">{store_address}<br>{store_phone}</div>
                    <div class="receipt-title">إيصال مرتجع شراء</div>
                </div>

                <div class="meta-card">
                    <table class="meta-info">
                        <tr><td class="label">رقم المرتجع:</td><td class="value">#{return_number}</td></tr>
                        <tr><td class="label">فاتورة الشراء:</td><td class="value">#{invoice_number}</td></tr>
                        <tr><td class="label">التاريخ:</td><td class="value">{datetime.now().strftime('%Y-%m-%d %H:%M')}</td></tr>
                        <tr><td class="label">المستخدم:</td><td class="value">{escape(str(user_name or '-'))}</td></tr>
                    </table>
                </div>

                <div class="customer-section">
                    <div class="customer-title">المورد</div>
                    <div class="customer-info"><strong>{supplier_name}</strong></div>
                </div>

                <table class="items-table">
                    <thead>
                        <tr>
                            <th style="width: 65%; text-align: right;">الصنف</th>
                            <th style="width: 35%; text-align: left;">التكلفة</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>

                <div class="totals-section">
                    <table class="total-table">
                        <tr><td class="total-label">طريقة التسوية:</td><td class="total-value">{settlement_label}</td></tr>
                        <tr><td class="total-label">السبب:</td><td class="total-value">{reason}</td></tr>
                        <tr class="grand-total">
                            <td class="total-label">إجمالي المرتجع:</td>
                            <td class="total-value">{PrinterService._money(return_data.get('total_amount', 0))} ج.م</td>
                        </tr>
                    </table>
                </div>

                <div class="footer">
                    تم خصم الكمية من المخزون وتسجيل أثر المرتجع ماليًا.
                </div>
                {PrinterService._get_barcode_html(return_number)}
            </div>
        </body>
        </html>
        """
        return html

    @staticmethod
    def save_purchase_return_as_pdf(return_data, items, user_name):
        """Saves a supplier purchase return receipt as PDF."""
        settings = PrinterService._load_settings()
        html = PrinterService._generate_purchase_return_html(return_data, items, user_name, settings)
        prefix = f"Purchase_Return_{return_data.get('return_number', 'New')}"
        thermal_width_pts = 226
        success, pdf_path = PrinterService._save_as_pdf(
            html,
            thermal_width_pts,
            filename_prefix=prefix,
            category="المشتريات/مرتجعات المشتريات",
            auto_open=True,
        )
        return {"saved": success, "pdf_path": pdf_path}

    @staticmethod
    def save_return_as_pdf(return_data, items, user_name, store_name_unused=None):
        """Explicitly saves a return receipt as PDF without trying to print."""
        settings = PrinterService._load_settings()
        
        html = PrinterService._generate_return_receipt_html(return_data, items, user_name, settings)
        prefix = return_data.get('return_number', 'Return')
        thermal_width_pts = 226
        success, pdf_path = PrinterService._save_as_pdf(html, thermal_width_pts, filename_prefix=prefix, category="فواتير المرتجعات", auto_open=True)
        return {"saved": success, "pdf_path": pdf_path}

    @staticmethod
    def _generate_drawer_report_html(summary, settings):
        """Format the drawer report with premium HTML."""
        den_html = ""
        if summary.get('denominations'):
            den_html = "<div class='divider'></div><div class='customer-title'>تفاصيل الفئات</div><table>"
            for den in summary['denominations']:
                den_html += f"<tr><td>{den['denomination']} x {den['quantity']}</td><td style='text-align:left'>{den['total_amount']:.2f}</td></tr>"
            den_html += "</table>"

        store_name = settings.get('store_name', 'نظمة POS')
        store_address = settings.get('store_address', '')
        store_phone = settings.get('store_phone', '')

        diff = summary['difference']
        diff_style = "color: #38a169;" if diff >= 0 else "color: #e53e3e;"
        
        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <style>{PrinterService._get_common_styles()}</style>
        </head>
        <body>
            <div class="receipt">
                <div class="header">
                    <div class="store-name">{store_name}</div>
                    <div class="branch-info">{store_address}<br>{store_phone}</div>
                    <div class="customer-title" style="font-size: 14px; margin-top:5px;">*** تقرير إغلاق الدرج ***</div>
                    <div class="divider"></div>
                    <table class="meta-info">
                        <tr>
                            <td class="label">رقم الدرج: {summary['drawer_id']}</td>
                            <td class="value" style="text-align:left">{datetime.now().strftime('%Y-%m-%d %H:%M')}</td>
                        </tr>
                        <tr>
                            <td class="label" colspan="2" style="text-align:center">الكاشير: {summary['cashier_name']}</td>
                        </tr>
                    </table>
                </div>

                <table class="items-table">
                    <tr><td>الرصيد الافتتاحي:</td><td style="text-align:left">{summary['opening_balance']:.2f}</td></tr>
                    <tr><td>إجمالي المبيعات ({summary['sales_count']}):</td><td style="text-align:left">{summary['total_sales']:.2f}</td></tr>
                    <tr style="font-size: 10px; color: #555"><td>&nbsp;&nbsp; - نقداً:</td><td style="text-align:left">{summary['total_cash_sales']:.2f}</td></tr>
                    <tr style="font-size: 10px; color: #555"><td>&nbsp;&nbsp; - فيزا (نظام):</td><td style="text-align:left">{summary['total_card_sales']:.2f}</td></tr>
                    <tr style="font-size: 10px; color: #555"><td>&nbsp;&nbsp; - آجل:</td><td style="text-align:left">{summary.get('total_deferred', 0):.2f}</td></tr>
                    <tr><td>المرتجعات ({summary['returns_count']}):</td><td style="text-align:left">-{summary['total_returns']:.2f}</td></tr>
                    <tr style="font-size: 10px; color: #555"><td>&nbsp;&nbsp; - مرتجعات نقدية:</td><td style="text-align:left">-{summary.get('total_cash_returns', summary['total_returns']):.2f}</td></tr>
                </table>

                <div class="divider"></div>
                <div class="customer-title" style="font-size: 13px;">مطابقة الفيزا (الماكينة)</div>
                <table class="items-table">
                    <tr><td>المتوقع (النظام):</td><td style="text-align:left">{summary['total_card_sales']:.2f}</td></tr>
                    <tr><td>الفعلي (الماكينة):</td><td style="text-align:left">{summary['actual_visa']:.2f}</td></tr>
                    <tr style="font-weight: bold; color: {'#38a169' if summary['visa_difference'] >= 0 else '#e53e3e'};">
                        <td>فرق الفيزا:</td>
                        <td style="text-align:left">{summary['visa_difference']:+.2f}</td>
                    </tr>
                </table>

                <div class="totals-section">
                    <table class="total-table">
                        <tr><td class="total-label">المتوقع نقداً:</td> <td class="total-value">{summary['expected_cash']:.2f}</td></tr>
                        <tr><td class="total-label">الفعلي نقداً:</td> <td class="total-value">{summary['actual_cash']:.2f}</td></tr>
                        <tr class="grand-total" style="{diff_style}">
                            <td class="total-label">العجز / الزيادة:</td> 
                            <td class="total-value">{diff:+.2f} ج.م</td>
                        </tr>
                    </table>
                </div>

                {den_html}

                <table style="margin-top: 30px; font-size: 10px;">
                    <tr>
                        <td style="text-align: center; width: 50%;">توقيع الكاشير<br><br>__________</td>
                        <td style="text-align: center; width: 50%;">توقيع المدير<br><br>__________</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        """
        return html

