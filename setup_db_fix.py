#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إعداد قاعدة البيانات وإنشاء مستخدم تجريبي بدور مطور (Developer)
"""
import mysql.connector
import bcrypt

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123',
    'database': 'stocks',
    'port': 3306,
}

def main():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        print("تم الاتصال بقاعدة البيانات بنجاح")

        # التحقق من وجود المستخدم التجريبي
        cursor.execute("SELECT * FROM users WHERE email = 'dev@test.com'")
        user = cursor.fetchone()
        if user:
            print(f"المستخدم موجود: {user['name']} - الدور: {user['role_id']}")
        else:
            print("إنشاء مستخدم تجريبي بدور مطور (Developer)...")
            pw = bcrypt.hashpw('DevPass2026!'.encode(), bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO users (name, email, password, phone, role_id, store_id, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                ('Test Developer', 'dev@test.com', pw.decode(), '01012345678', 99, 1, True)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE email = 'dev@test.com'")
            new_user = cursor.fetchone()
            print(f"تم إنشاء المستخدم: {new_user['name']} - الدور: {new_user['role_id']} - المتجر: {new_user['store_id']}")

        # التحقق من جدول الإعدادات
        cursor.execute("SHOW TABLES LIKE 'system_settings'")
        settings_table = cursor.fetchone()
        if settings_table:
            print("جدول الإعدادات موجود")
        else:
            print("جدول الإعدادات غير موجود - يتم إنشاؤه")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    setting_key VARCHAR(100) PRIMARY KEY,
                    setting_value VARCHAR(500) DEFAULT ''
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            print("تم إنشاء جدول الإعدادات بنجاح")

        # إضافة إعدادات النسخ الاحتياطي
        cursor.execute("SELECT * FROM system_settings WHERE setting_key LIKE 'backup_%'")
        backup_settings = cursor.fetchall()
        print(f"إعدادات النسخ الاحتياطي: {len(backup_settings)} سجل")

        # التحقق من جدول المزامنة
        cursor.execute("SHOW TABLES LIKE 'sync_queue'")
        sync_queue = cursor.fetchone()
        print(f"جدول طابور المزامنة: {'موجود' if sync_queue else 'غير موجود'}")

        conn.close()
        print("\nتم إصلاح الاتصال وإنشاء المستخدم التجريبي بنجاح!")
        print("بيانات تسجيل الدخول التجريبية:")
        print("البريد: dev@test.com")
        print("كلمة المرور: DevPass2026!")
        print("الدور: مطور (Developer - ID: 99)")

    except mysql.connector.Error as e:
        print(f"خطأ في الاتصال بقاعدة البيانات: {str(e)[:200]}")
    except Exception as e:
        print(f"خطأ غير متوقع: {str(e)[:200]}")

if __name__ == '__main__':
    main()
