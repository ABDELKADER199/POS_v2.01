#!/usr/bin/env python3
"""
إضافة مستخدم إداري جديد
"""
import sys
import os
sys.path.insert(0, '.')

from repositories.db_connection import DatabaseConnection
import bcrypt
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def create_admin_user(name, email, password, store_id=1):
    """
    إنشاء مستخدم إداري
    """
    db = DatabaseConnection()
    
    print("\n" + "="*70)
    print("➕ إضافة مستخدم إداري جديد")
    print("="*70 + "\n")
    
    # التحقق من وجود الدور (admin)
    role = db.fetch_one("SELECT id FROM roles WHERE role_name = 'admin'")
    if not role:
        print("❌ الدور 'admin' غير موجود في قاعدة البيانات")
        print("تأكد من تطبيق هجرات قاعدة البيانات")
        return False
    
    role_id = role['id']
    
    # التحقق من وجود الفرع (store)
    store = db.fetch_one("SELECT id FROM stores WHERE id = %s", (store_id,))
    if not store:
        print(f"❌ الفرع برقم {store_id} غير موجود")
        # اجلب أول فرع
        store = db.fetch_one("SELECT id FROM stores LIMIT 1")
        if store:
            store_id = store['id']
            print(f"✅ استخدام الفرع الافتراضي: {store_id}")
        else:
            print("❌ لا توجد فروع في قاعدة البيانات")
            return False
    
    # التحقق من عدم وجود المستخدم مسبقاً
    existing = db.fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        print(f"⚠️  المستخدم {email} موجود بالفعل")
        return False
    
    # تشفير كلمة المرور
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
    
    try:
        db.execute("""
            INSERT INTO users (name, email, password, role_id, store_id, is_active)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (name, email, password_hash, role_id, store_id))
        db.commit()
        
        print("✅ تم إنشاء المستخدم بنجاح!")
        print("\n" + "="*70)
        print("📋 بيانات المستخدم:")
        print("="*70)
        print(f"الاسم: {name}")
        print(f"البريد: {email}")
        print(f"كلمة المرور: {password}")
        print(f"الدور: Admin (مدير نظام)")
        print(f"الفرع: {store_id}")
        print("="*70 + "\n")
        print("💡 الآن يمكنك تسجيل الدخول بهذه البيانات!")
        print("="*70 + "\n")
        return True
        
    except Exception as e:
        print(f"❌ خطأ أثناء الإنشاء: {e}")
        return False

def main():
    # بيانات افتراضية
    print("\n" + "="*70)
    print("👤 إنشاء مستخدم إداري - Create Admin User")
    print("="*70 + "\n")
    
    # الحصول على البيانات من المستخدم
    name = input("أدخل اسم المستخدم (مثال: مدير النظام): ").strip()
    if not name:
        name = "مدير النظام"
    
    email = input("أدخل بريد المستخدم (مثال: admin@hyperpos.com): ").strip()
    if not email:
        email = "admin@hyperpos.com"
    
    password = input("أدخل كلمة المرور (مثال: Admin@123): ").strip()
    if not password:
        password = "Admin@123"
    
    # إنشاء المستخدم
    success = create_admin_user(name, email, password)
    
    if success:
        print("🎉 يمكنك الآن تشغيل البرنامج وتسجيل الدخول!")
        print("   python main.py\n")
    else:
        print("⚠️  فشل إنشاء المستخدم. تأكد من قاعدة البيانات.\n")
        return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ تم الإلغاء من قبل المستخدم\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ: {e}\n")
        sys.exit(1)
