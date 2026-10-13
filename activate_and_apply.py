#!/usr/bin/env python3
"""
سكريبت تطبيق التفعيل
يأخذ مفتاح التفعيل وينطبقه على قاعدة البيانات
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
from application.services.license_service import LicenseService


def main():
    """Apply activation key to the system"""
    
    print("\n" + "="*70)
    print("✨ تطبيق التفعيل - HyperPOS V2 License Activation")
    print("="*70 + "\n")
    
    # Get activation key from command line or user input
    if len(sys.argv) > 1:
        activation_key = sys.argv[1].strip().upper()
    else:
        activation_key = input("أدخل مفتاح التفعيل (Activation Key): ").strip().upper()
    
    if not activation_key:
        print("❌ لم يتم إدخال مفتاح التفعيل\n")
        return False
    
    # Get current hardware ID
    try:
        hardware_id = LicenseManager.get_hardware_id()
        print(f"✅ سريال الجهاز الحالي: {hardware_id}")
        print(f"🔑 مفتاح التفعيل المدخل: {activation_key}\n")
    except Exception as e:
        print(f"❌ خطأ في الحصول على سريال الجهاز: {e}\n")
        return False
    
    # Verify key with hardware ID
    is_valid = LicenseManager.verify_key(hardware_id, activation_key)
    if not is_valid:
        print(f"❌ مفتاح التفعيل غير صحيح لهذا الجهاز!")
        print(f"\n💡 المفتاح الصحيح للجهاز الحالي:")
        correct_key = LicenseManager.generate_activation_key(hardware_id)
        print(f"   {correct_key}\n")
        return False
    
    print("✅ مفتاح التفعيل صحيح! جاري التطبيق...\n")
    
    # Apply the license
    try:
        service = LicenseService()
        success = service.activate(activation_key)
        
        if success:
            print("="*70)
            print("\n✨ تم تفعيل التطبيق بنجاح! ✨\n")
            print("🎉 يمكنك الآن تشغيل البرنامج بدون مشاكل.")
            print("\n   python main.py\n")
            print("="*70 + "\n")
            return True
        else:
            print("❌ فشل التفعيل في قاعدة البيانات\n")
            return False
            
    except Exception as e:
        print(f"❌ خطأ أثناء التفعيل: {e}\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
