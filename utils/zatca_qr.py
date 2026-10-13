import base64
from datetime import datetime

class ZatcaQRCoder:
    """
    أداة متخصصة لتوليد رمز QR متوافق مع هيئة الزكاة والدخل (ZATCA)
    ومصلحة الضرائب المصرية (ETA) باستخدام معيار TLV Base64.
    """

    @staticmethod
    def _to_tlv(tag: int, value: str) -> bytes:
        """
        تحويل قيمة نصية إلى صيغة Tag-Length-Value
        """
        value_bytes = str(value).encode('utf-8')
        # Tag (1 byte) + Length (1 byte) + Value (N bytes)
        return bytes([tag, len(value_bytes)]) + value_bytes

    @classmethod
    def generate_base64(cls, seller_name: str, tax_number: str, timestamp_iso: str, total_with_vat: float, vat_amount: float) -> str:
        """
        تجميع الحقول الخمسة المطلوبة وتشفيرها بصيغة Base64
        """
        tlv_data = b""
        
        # 1. اسم المورد / البائع
        tlv_data += cls._to_tlv(1, seller_name)
        
        # 2. رقم التسجيل الضريبي للمورد
        tlv_data += cls._to_tlv(2, tax_number)
        
        # 3. الطابع الزمني (التاريخ والوقت) بصيغة ISO8601
        tlv_data += cls._to_tlv(3, timestamp_iso)
        
        # 4. إجمالي الفاتورة (مع الضريبة)
        tlv_data += cls._to_tlv(4, f"{float(total_with_vat):.2f}")
        
        # 5. إجمالي ضريبة القيمة المضافة
        tlv_data += cls._to_tlv(5, f"{float(vat_amount):.2f}")
        
        # التشفير النهائي بصيغة Base64
        return base64.b64encode(tlv_data).decode('utf-8')
