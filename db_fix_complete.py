#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Fix Script - Database Engineer
Fixes: missing users, authorized devices, and schema columns
"""
import mysql.connector
import bcrypt
import uuid
import socket

DB_CONFIG = {'host': 'localhost', 'user': 'root', 'password': '123', 'database': 'stocks', 'port': 3306}

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("Database fix started")

    # 1. Ensure authorized_devices has required columns
    try:
        cursor.execute("ALTER TABLE authorized_devices ADD COLUMN IF NOT EXISTS device_name VARCHAR(255)")
        cursor.execute("ALTER TABLE authorized_devices ADD COLUMN IF NOT EXISTS mac_address VARCHAR(255)")
        cursor.execute("ALTER TABLE authorized_devices ADD COLUMN IF NOT EXISTS is_active TINYINT(1) DEFAULT 1")
        cursor.execute("ALTER TABLE authorized_devices ADD COLUMN IF NOT EXISTS last_used TIMESTAMP NULL")
        cursor.execute("ALTER TABLE authorized_devices ADD COLUMN IF NOT EXISTS registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        conn.commit()
        print("authorized_devices: columns verified")
    except Exception as e:
        print("authorized_devices column check:", str(e)[:80])

    # 2. Get or create developer role
    cursor.execute("SELECT id FROM roles WHERE id = 99 OR role_name = 'developer'")
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT IGNORE INTO roles (id, role_name, description) VALUES (99, 'developer', 'Developer - full permissions')")
        conn.commit()
        print("Developer role created (ID: 99)")
    else:
        print("Developer role exists (ID: {})".format(row[0]))

    # 3. Create/Update admin@hyperpos.com user
    cursor.execute("SELECT id FROM users WHERE email = 'admin@hyperpos.com'")
    admin_user = cursor.fetchone()
    if not admin_user:
        # Create the admin user
        pw_hash = bcrypt.hashpw('DevPass2026!'.encode(), bcrypt.gensalt()).decode()
        cursor.execute("""
            INSERT INTO users (name, email, password, phone, role_id, store_id, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
        """, ('Test Developer', 'admin@hyperpos.com', pw_hash, '01012345678', 99, 1, True))
        admin_user_id = cursor.lastrowid
        conn.commit()
        print("admin@hyperpos.com created (ID: {})".format(admin_user_id))
    else:
        admin_user_id = admin_user[0]
        # Ensure user is active and has developer role
        cursor.execute("UPDATE users SET is_active=1, role_id=99 WHERE email='admin@hyperpos.com'")
        conn.commit()
        print("admin@hyperpos.com verified (ID: {})".format(admin_user_id))

    # 4. Create/Update dev@test.com user
    cursor.execute("SELECT id FROM users WHERE email = 'dev@test.com'")
    test_user = cursor.fetchone()
    if not test_user:
        pw_hash = bcrypt.hashpw('DevPass2026!'.encode(), bcrypt.gensalt()).decode()
        cursor.execute("""
            INSERT INTO users (name, email, password, phone, role_id, store_id, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
        """, ('Test Developer', 'dev@test.com', pw_hash, '01012345678', 99, 1, True))
        test_user_id = cursor.lastrowid
        conn.commit()
        print("dev@test.com created (ID: {})".format(test_user_id))
    else:
        test_user_id = test_user[0]
        cursor.execute("UPDATE users SET is_active=1, role_id=99 WHERE email='dev@test.com'")
        conn.commit()
        print("dev@test.com verified (ID: {})".format(test_user_id))

    # 5. Add an authorized device to prevent login blocking
    try:
        hostname = socket.gethostname()
        mac = hex(uuid.getnode())
        cursor.execute("SELECT id FROM authorized_devices WHERE is_active = 1 LIMIT 1")
        device = cursor.fetchone()
        if not device:
            cursor.execute("""
                INSERT INTO authorized_devices (device_name, mac_address, store_id, user_id, registered_by, notes, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, 1)
            """, (hostname, mac, 1, 1, 1, 'Auto-registered device for development',))
            conn.commit()
            print("Authorized device added (hostname: {})".format(hostname))
        else:
            print("Authorized device exists (ID: {})".format(device[0]))
    except Exception as e:
        print("Device registration error:", str(e)[:80])

    # 6. Verify final state
    cursor.execute("SELECT id, name, email, role_id, store_id FROM users")
    print("\n=== Final Users ===")
    for u in cursor.fetchall():
        print("  ID={}, Email={}, Role={}, Store={}".format(u[0], u[2], u[3], u[4]))

    conn.close()
    print("\nDatabase fix complete!")

if __name__ == '__main__':
    main()
