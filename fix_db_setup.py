#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix database: add developer role and create test user"""
import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123',
    'database': 'stocks',
    'port': 3306,
}

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    # Check roles
    cursor.execute("SELECT * FROM roles WHERE id = 99")
    role = cursor.fetchone()
    if not role:
        print("Adding developer role (ID: 99)...")
        cursor.execute("INSERT IGNORE INTO roles (id, role_name, description) VALUES (99, 'developer', 'Developer - full permissions for testing')")
        conn.commit()
        print("Developer role added.")
    else:
        print(f"Developer role exists: {role}")

    # Check user
    cursor.execute("SELECT * FROM users WHERE email = 'dev@test.com'")
    user = cursor.fetchone()
    if not user:
        import bcrypt
        pw = bcrypt.hashpw('DevPass2026!'.encode(), bcrypt.gensalt())
        cursor.execute("""
            INSERT INTO users (name, email, password, phone, role_id, store_id, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
        """, ('Test Developer', 'dev@test.com', pw.decode(), '01012345678', 99, 1, True))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE email = 'dev@test.com'")
        new_user = cursor.fetchone()
        print(f"Test user created: ID={new_user['id']}, Name={new_user['name']}, Role={new_user['role_id']}")
    else:
        print(f"Test user exists: ID={user['id']}, Name={user['name']}, Role={user['role_id']}")

    # Create backup settings table if missing
    cursor.execute("SHOW TABLES LIKE 'system_settings'")
    if not cursor.fetchone():
        print("Creating system_settings table...")
        cursor.execute("""
            CREATE TABLE system_settings (
                setting_key VARCHAR(100) PRIMARY KEY,
                setting_value VARCHAR(500) DEFAULT ''
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        print("system_settings created.")

    # Insert default backup settings
    cursor.execute("INSERT IGNORE INTO system_settings (setting_key, setting_value) VALUES ('backup_path', 'backups')")
    cursor.execute("INSERT IGNORE INTO system_settings (setting_key, setting_value) VALUES ('auto_backup_enabled', 'true')")
    cursor.execute("INSERT IGNORE INTO system_settings (setting_key, setting_value) VALUES ('mysqldump_path', 'C:\\\\Program Files\\\\MySQL\\\\MySQL Server 8.0\\\\bin\\\\mysqldump.exe')")
    conn.commit()
    print("Default backup settings inserted.")

    cursor.execute("SELECT setting_key, setting_value FROM system_settings WHERE setting_key LIKE 'backup_%'")
    settings = cursor.fetchall()
    for s in settings:
        print(f"  {s['setting_key']}: {s['setting_value']}")

    conn.close()
    print("\nDatabase setup complete!")
    print("Login credentials:")
    print("  Email: dev@test.com")
    print("  Password: DevPass2026!")
    print("  Role: Developer (ID: 99) - full permissions")

if __name__ == '__main__':
    main()
