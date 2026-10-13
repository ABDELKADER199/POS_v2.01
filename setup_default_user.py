#!/usr/bin/env python3
"""
إضافة مستخدم إداري جديد - نسخة بسيطة
"""
import sys
import os
sys.path.insert(0, '.')

from repositories.db_connection import DatabaseConnection
import bcrypt

def create_default_admin():
    """إنشاء مستخدم إداري افتراضي"""
    db = DatabaseConnection()
    
    print("\n" + "="*70)
    print("➕ إضافة مستخدم إداري افتراضي")
    print("="*70 + "\n")
    
    # البيانات الافتراضية
    name = "مدير النظام"
    email = "admin@hyperpos.com"
    password = "Admin@123"
    store_id = 1
    
    # التحقق من وجود الدور
    role = db.fetch_one("SELECT id FROM roles WHERE role_name = 'admin'")
    if not role:
        print("❌ الدور 'admin' غير موجود")
        return False
    
    role_id = role['id']
    
    # التحقق من وجود الفرع
    store = db.fetch_one("SELECT id FROM stores WHERE id = %s", (store_id,))
    if not store:
        store = db.fetch_one("SELECT id FROM stores LIMIT 1")
        if not store:
            print("❌ لا توجد فروع في قاعدة البيانات")
            return False
        store_id = store['id']
    
    # التحقق من عدم وجود المستخدم
    existing = db.fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        print(f"⚠️  المستخدم {email} موجود بالفعل!")
        return False
    
    # تشفير كلمة المرور
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
    
    try:
        db.execute("""
            INSERT INTO users (name, email, password, role_id, store_id, is_active)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (name, email, password_hash, role_id, store_id))
        db.commit()
        
        print("✅ تم إنشاء المستخدم بنجاح!\n")
        print("="*70)
        print("📋 بيانات الدخول:")
        print("="*70)
        print(f"البريد الإلكتروني: {email}")
        print(f"كلمة المرور: {password}")
        print("="*70 + "\n")
        print("🎉 الآن يمكنك تسجيل الدخول!")
        print("="*70 + "\n")
        return True
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False

if __name__ == "__main__":
    try:
        success = create_default_admin()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ خطأ: {e}\n")
        sys.exit(1)
