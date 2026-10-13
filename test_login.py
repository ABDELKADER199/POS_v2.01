#!/usr/bin/env python3
"""
اختبار تسجيل الدخول
"""
import sys
sys.path.insert(0, '.')

from repositories.user_repo import UserRepository

def test_login():
    """اختبار تسجيل الدخول"""
    repo = UserRepository()
    
    print("\n" + "="*70)
    print("🧪 اختبار تسجيل الدخول")
    print("="*70 + "\n")
    
    # البيانات الافتراضية
    email = "admin@hyperpos.com"
    password = "Admin@123"
    
    print(f"📧 البريد: {email}")
    print(f"🔑 كلمة المرور: {password}")
    print("\nجاري الاختبار...\n")
    
    # محاولة تسجيل الدخول
    user = repo.authenticate(email, password)
    
    if user:
        print("✅ تسجيل الدخول نجح!\n")
        print("="*70)
        print("👤 بيانات المستخدم:")
        print("="*70)
        print(f"ID: {user.id}")
        print(f"الاسم: {user.name}")
        print(f"البريد: {user.email}")
        print(f"الدور: {user.role}")
        print(f"الفرع: {user.store_name}")
        print("="*70 + "\n")
        print("🎉 يمكنك الآن تشغيل البرنامج!")
        return True
    else:
        print("❌ فشل تسجيل الدخول!")
        print("\nالأسباب المحتملة:")
        print("  1. البريد الإلكتروني خاطئ")
        print("  2. كلمة المرور خاطئة")
        print("  3. المستخدم معطّل")
        return False

if __name__ == "__main__":
    try:
        success = test_login()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ خطأ: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
