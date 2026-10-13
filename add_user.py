#!/usr/bin/env python3
"""
إضافة مستخدم جديد
"""
import sys
import os
sys.path.insert(0, '.')

from repositories.db_connection import DatabaseConnection
import bcrypt

def add_user(name, email, password, role_name='cashier', store_id=1):
    """إضافة مستخدم جديد"""
    db = DatabaseConnection()
    
    print("\n" + "="*70)
    print("➕ إضافة مستخدم جديد")
    print("="*70 + "\n")
    
    # البحث عن الدور
    role = db.fetch_one("SELECT id FROM roles WHERE role_name = %s", (role_name,))
    if not role:
        print(f"❌ الدور '{role_name}' غير موجود")
        print("الأدوار المتاحة:")
        roles = db.fetch_all("SELECT role_name FROM roles")
        for r in roles:
            print(f"  - {r['role_name']}")
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
        print(f"❌ المستخدم {email} موجود بالفعل")
        return False
    
    # تشفير كلمة المرور
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
    
    try:
        db.execute("""
            INSERT INTO users (name, email, password, role_id, store_id, is_active)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (name, email, password_hash, role_id, store_id))
        db.commit()
        
        print("✅ تم إضافة المستخدم بنجاح!\n")
        print("="*70)
        print("📋 بيانات المستخدم:")
        print("="*70)
        print(f"الاسم: {name}")
        print(f"البريد: {email}")
        print(f"كلمة المرور: {password}")
        print(f"الدور: {role_name}")
        print("="*70 + "\n")
        return True
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False

def show_roles():
    """عرض الأدوار المتاحة"""
    db = DatabaseConnection()
    print("\n" + "="*70)
    print("📋 الأدوار المتاحة:")
    print("="*70 + "\n")
    roles = db.fetch_all("SELECT role_name, description FROM roles")
    for role in roles:
        print(f"  • {role['role_name']}")
        if role['description']:
            print(f"    {role['description']}")
    print("\n" + "="*70 + "\n")

def main():
    if len(sys.argv) < 2:
        show_roles()
        print("الاستخدام:")
        print("  python add_user.py <الاسم> <البريد> <كلمة_المرور> [الدور] [الفرع]\n")
        print("مثال:")
        print("  python add_user.py 'أحمد محمد' 'ahmed@hyperpos.com' 'Pass@123' cashier 1\n")
        return False
    
    name = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    role_name = sys.argv[4] if len(sys.argv) > 4 else 'cashier'
    store_id = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    
    return add_user(name, email, password, role_name, store_id)

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ خطأ: {e}\n")
        sys.exit(1)
