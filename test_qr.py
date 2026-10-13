import sys
sys.path.append(r'd:\Python Desktop\POS_V2')
from utils.zatca_qr import ZatcaQRCoder
import base64

try:
    payload = ZatcaQRCoder.generate_base64(
        seller_name="Test Store متجر الاختبار",
        tax_number="300123456700003",
        timestamp_iso="2023-10-25T15:30:00Z",
        total_with_vat=115.00,
        vat_amount=15.00
    )
    print("Generated Payload:", payload)
    
    # Let's decode it to verify
    decoded_bytes = base64.b64decode(payload)
    print("\nDecoded bytes:", decoded_bytes)
    
    # Simple TLV parser
    idx = 0
    while idx < len(decoded_bytes):
        tag = decoded_bytes[idx]
        length = decoded_bytes[idx+1]
        value = decoded_bytes[idx+2:idx+2+length].decode('utf-8')
        print(f"Tag: {tag}, Length: {length}, Value: {value}")
        idx += 2 + length
        
    print("\nSUCCESS: TLV base64 encoded and decoded successfully!")
except Exception as e:
    print(f"ERROR: {e}")
