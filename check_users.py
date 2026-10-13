#!/usr/bin/env python3
"""
فحص قاعدة البيانات - المستخدمون وحالتهم
"""
import sys
sys.path.insert(0, '.')

from repositories.db_connection import DatabaseConnection

db = DatabaseConnection()

print("\n" + "="*70)
print("📋 المستخدمون في قاعدة البيانات:")
print("="*70 + "\n")

try:
    users = db.fetch_all('SELECT id, name, email, is_active FROM users')
    
    if not users:
        print("❌ لا توجد مستخدمون في قاعدة البيانات!")
        print("\nيجب إضافة مستخدم واحد على الأقل قبل تسجيل الدخول.")
    else:
        for user in users:
            status = "✅ مفعّل" if user['is_active'] else "❌ معطّل"
            print(f"ID: {user['id']}")
            print(f"   الاسم: {user['name']}")
            print(f"   البريد: {user['email']}")
            print(f"   الحالة: {status}")
            print()
            
except Exception as e:
    print(f"❌ خطأ: {e}")
    print("قد تكون جداول قاعدة البيانات غير موجودة")

print("="*70 + "\n")
