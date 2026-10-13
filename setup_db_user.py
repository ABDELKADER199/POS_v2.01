#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to setup database connection and create test user with developer role
"""
import mysql.connector
import sys

# Database configuration from .env
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123',
    'database': 'stocks',
    'port': 3306
}

try:
    # Connect to database
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    print("DB connection: SUCCESS")

    # Check if users table exists and has records
    cursor.execute("SELECT COUNT(*) as count FROM users")
    result = cursor.fetchone()
    print(f"Current users count: {result['count']}")

    # Check roles
    cursor.execute("SELECT * FROM roles")
    roles = cursor.fetchall()
    print(f"Available roles: {len(roles)}")
    for role in roles:
        print(f"  - {role['id']}: {role['role_name']} ({role['description']})")

    # Check if developer/test user exists
    cursor.execute("SELECT * FROM users WHERE email = 'dev@test.com'")
    dev_user = cursor.fetchone()
    if dev_user:
        print(f"Developer user exists: {dev_user['name']} (role: {dev_user['role_id']})")
    else:
        print("Creating test developer user...")
        # Insert developer user (using role_id 99 from the new schema)
        # We need to insert with a hashed password
        import bcrypt
        password_hash = bcrypt.hashpw('TestPass123!'.encode(), bcrypt.gensalt())
        try:
            cursor.execute("""
                INSERT IGNORE INTO users (name, email, password, phone, role_id, store_id, is_active)
                VALUES ('Test Developer', 'dev@test.com', %s, '01012345678', 99, 1, TRUE)
            """, (password_hash.decode(),))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE email = 'dev@test.com'")
            new_user = cursor.fetchone()
            if new_user:
                print(f"Developer user created: ID={new_user['id']}, Name={new_user['name']}, Role={new_user['role_id']}")
            else:
                print("User may already exist or insertion failed")
        except mysql.connector.errors.IntegrityError:
            print("Developer user already exists (unique constraint)")
            conn.rollback()

    # Verify system_settings table exists
    cursor.execute("SHOW TABLES LIKE 'system_settings'")
    settings_table = cursor.fetchone()
    if settings_table:
        print("system_settings table: EXISTS")
    else:
        print("system_settings table: NOT FOUND - creating...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_key VARCHAR(100) PRIMARY KEY,
                setting_value VARCHAR(500) DEFAULT ''
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        print("system_settings table created successfully")

    # Verify sync_queue table exists
    cursor.execute("SHOW TABLES LIKE 'sync_queue'")
    sync_table = cursor.fetchone()
    if sync_table:
        print("sync_queue table: EXISTS")
    else:
        print("sync_queue table: NOT FOUND")

    conn.close()
    print("\n=== Setup Complete ===")

except mysql.connector.Error as e:
    print(f"DB connection: FAILED - {str(e)[:200]}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {str(e)[:200]}")
    sys.exit(1)
