#!/usr/bin/env python3
"""
مولد مفاتيح التفعيل
يأخذ سريال الجهاز (Hardware ID) ويعطيك مفتاح التفعيل المناسب
"""

import sys
import os
import logging

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

from utils.license_manager import LicenseManager


def main():
    """Generate activation key for a given hardware ID"""
    
    print("\n" + "="*70)
    print("🔐 مولد مفاتيح التفعيل - HyperPOS V2 License Key Generator")
    print("="*70 + "\n")
    
    # Get hardware ID from command line or user input
    if len(sys.argv) > 1:
        hardware_id = sys.argv[1].strip().upper()
    else:
        hardware_id = input("أدخل سريال الجهاز (Hardware ID): ").strip().upper()
    
    if not hardware_id:
        print("❌ لم يتم إدخال سريال الجهاز")
        return False
    
    # Validate hardware ID format
    if not _validate_hardware_id(hardware_id):
        print(f"❌ صيغة سريال الجهاز غير صحيحة. يجب أن يكون بهذا الشكل: XXXX-XXXX-XXXX-XXXX")
        return False
    
    print(f"\n✅ سريال الجهاز: {hardware_id}\n")
    
    # Generate activation key
    try:
        activation_key = LicenseManager.generate_activation_key(hardware_id)
        print("="*70)
        print(f"\n🔑 مفتاح التفعيل:\n")
        print(f"   {activation_key}\n")
        print("="*70)
        print("\n💡 تعليمات الاستخدام:")
        print("   1. انسخ مفتاح التفعيل أعلاه")
        print("   2. افتح البرنامج وادخل المفتاح في شاشة التفعيل")
        print("   3. أو استخدم السكريبت التالي للتفعيل المباشر:")
        print(f"\n   python activate_and_apply.py {activation_key}\n")
        print("="*70 + "\n")
        return True
        
    except Exception as e:
        print(f"❌ خطأ أثناء توليد المفتاح: {e}\n")
        return False


def _validate_hardware_id(hw_id: str) -> bool:
    """Validate hardware ID format (XXXX-XXXX-XXXX-XXXX)"""
    parts = hw_id.split('-')
    if len(parts) != 4:
        return False
    for part in parts:
        if len(part) != 4 or not all(c in '0123456789ABCDEF' for c in part):
            return False
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
