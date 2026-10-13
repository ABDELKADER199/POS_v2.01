"""
Print Service Facade - واجهة خدمة الطباعة
طبقة الأعمال للطباعة: الإيصالات، الباركود، QR Codes، PDF
"""
import logging
import os
import base64
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from utils.printer_service import PrinterService
from utils.barcode_service import BarcodeService
from repositories.settings_repo import SettingsRepository

logger = logging.getLogger(__name__)


class PrintServiceFacade:
    """
    خدمة الطباعة الموحدة - تدير جميع عمليات الطباعة وحفظ PDF
    """

    def __init__(self, settings_repo: SettingsRepository = None):
        self.settings_repo = settings_repo or SettingsRepository()

    def _get_settings(self) -> Dict:
        return self.settings_repo.get_all()

    # ============================================================
    # Receipt Printing
    # ============================================================

    def print_sales_receipt(
        self,
        invoice: Dict,
        items: List[Dict],
        cashier_name: str
    ) -> bool:
        """طباعة إيصال مبيعات"""
        settings = self._get_settings()
        return PrinterService.print_receipt(invoice, items, cashier_name, settings)

    def save_sales_receipt_pdf(
        self,
        invoice: Dict,
        items: List[Dict],
        cashier_name: str
    ) -> Tuple[bool, Optional[str]]:
        """حفظ إيصال مبيعات كـ PDF"""
        settings = self._get_settings()
        success, pdf_path = PrinterService.save_receipt_as_pdf(invoice, items, cashier_name, settings)
        return success, pdf_path

    def print_purchase_invoice(
        self,
        invoice: Dict,
        items: List[Dict],
        user_name: str
    ) -> bool:
        """طباعة فاتورة مشتريات"""
        settings = self._get_settings()
        return PrinterService.print_purchase_invoice(invoice, items, user_name, settings)

    def save_purchase_invoice_pdf(
        self,
        invoice: Dict,
        items: List[Dict],
        user_name: str
    ) -> Tuple[bool, Optional[str]]:
        """حفظ فاتورة مشتريات كـ PDF"""
        settings = self._get_settings()
        success, pdf_path = PrinterService.save_purchase_invoice_as_pdf(invoice, items, user_name, settings)
        return success, pdf_path

    def print_return_receipt(
        self,
        return_data: Dict,
        items: List[Dict],
        user_name: str,
        store_name: str = None
    ) -> bool:
        """طباعة إيصال مرتجع"""
        settings = self._get_settings()
        return PrinterService.print_return_receipt(return_data, items, user_name, settings)

    def save_return_pdf(
        self,
        return_data: Dict,
        items: List[Dict],
        user_name: str,
        store_name: str = None
    ) -> Tuple[bool, Optional[str]]:
        """حفظ إيصال مرتجع كـ PDF"""
        settings = self._get_settings()
        success, pdf_path = PrinterService.save_return_as_pdf(return_data, items, user_name, settings)
        return success, pdf_path

    def print_drawer_report(
        self,
        summary: Dict
    ) -> bool:
        """طباعة تقرير الدرج"""
        settings = self._get_settings()
        return PrinterService.print_drawer_report(summary, settings)

    # ============================================================
    # Barcode / QR Code Generation
    # ============================================================

    def generate_product_barcode(
        self,
        code: str,
        name: str = "",
        price: float = None,
        label_size: str = "40x25"
    ) -> Optional[str]:
        """توليد صورة باركود للمنتج"""
        return BarcodeService.generate_barcode(code, name, price, label_size=label_size)

    def generate_barcode_base64(
        self,
        code: str,
        label_size: str = "40x25"
    ) -> Optional[str]:
        """توليد باركود كـ Base64 للتضمين في HTML"""
        import io
        try:
            from barcode.writer import ImageWriter
            from barcode import get as get_barcode
            
            code128 = get_barcode("code128", str(code), writer=ImageWriter())
            
            options = {
                "module_height": 12.0,
                "module_width": 0.45,
                "font_size": 8,
                "text_distance": 2.5,
                "quiet_zone": 1.5,
                "center_text": True,
                "write_text": True,
            }
            
            buffer = io.BytesIO()
            code128.write(buffer, options=options)
            buffer.seek(0)
            
            b64_string = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/png;base64,{b64_string}"
        except Exception as e:
            logger.error(f"Error generating barcode base64: {e}")
            return None

    def generate_qr_code_base64(
        self,
        data: str,
        size: int = 200
    ) -> Optional[str]:
        """توليد QR Code كـ Base64"""
        try:
            import qrcode
            import io
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=max(1, size // 25),
                border=1,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            b64_string = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/png;base64,{b64_string}"
        except ImportError:
            logger.warning("qrcode library not installed")
            return None
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return None



_print_service = None

def get_print_service():
    global _print_service
    if _print_service is None:
        _print_service = PrintServiceFacade()
    return _print_service
