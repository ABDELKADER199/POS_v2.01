#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
POS V2 - Database Rebuilder
As a Database Engineer - rebuilds the complete schema
"""
import mysql.connector
import sys

SCHEMA_FILE = r'D:\Python Desktop\POS_V2\database_schema_complete.sql'
DB_CONFIG = {'host':'localhost', 'user':'root', 'password':'123', 'port':3306}

def split_sql(sql_text):
    """Split SQL into statements, handling DELIMITER commands and // markers"""
    statements = []
    current = []
    current_delimiter = ';'
    lines = sql_text.split('\n')
    for line in lines:
        stripped = line.strip()
        # Handle DELIMITER changes
        if stripped.upper().startswith('DELIMITER '):
            delim = stripped.split(None, 1)[1].strip()
            current_delimiter = delim
            continue
        # Collect lines
        if current_delimiter == '//':
            current.append(line)
            if stripped == '//':
                stmt = '\n'.join(current)
                statements.append(stmt)
                current = []
                current_delimiter = ';'
        else:
            current.append(line)
            if stripped.endswith(';'):
                stmt = '\n'.join(current).strip()
                if stmt:
                    # Remove trailing semicolon
                    stmt = stmt[:-1] if stmt.endswith(';') else stmt
                    statements.append(stmt)
                current = []
    return statements

print("Starting database rebuild...")

# Step 1: Connect and recreate
conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()
print("Connected to MySQL server")

cursor.execute("DROP DATABASE IF EXISTS stocks")
cursor.execute("CREATE DATABASE stocks CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
print("Database stocks recreated")
conn.commit()
conn.close()

# Step 2: Apply schema
conn = mysql.connector.connect(database='stocks', **DB_CONFIG)
cursor = conn.cursor()
print("Connected to fresh stocks database")

# Disable FK checks to handle forward references
cursor.execute("SET FOREIGN_KEY_CHECKS=0")

with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
    sql_text = f.read()

statements = split_sql(sql_text)
print(f"Parsed {len(statements)} SQL statements")

errors = 0
success = 0
for i, stmt in enumerate(statements):
    try:
        cursor.execute(stmt)
        conn.commit()
        success += 1
    except Exception as e:
        err_str = str(e)[:100]
        if 'already exists' in err_str or 'Duplicate' in err_str or '1051' in err_str or '1061' in err_str or '1091' in err_str:
            pass  # Ignore already-exists errors (safe to rerun)
        else:
            errors += 1
            print(f"  Stmt {i}: ERROR - {err_str}")

print(f"\nStatements executed: {success} OK, {errors} errors")

# Step 3: Verification
verification_tables = [
    'roles', 'stores', 'users', 'categories', 'suppliers', 'customers',
    'products', 'product_units', 'product_images', 'product_variants',
    'product_batches', 'product_serials', 'product_inventory',
    'product_cost_history', 'product_movements', 'price_history',
    'invoices', 'invoice_items', 'invoice_tax_details', 'sales_returns',
    'return_items', 'purchase_invoices', 'purchase_items', 'purchase_returns',
    'purchase_return_items', 'warehouse_transfers', 'transfer_items',
    'expenses', 'treasury', 'payments', 'settlements', 'financial_ledger',
    'drawer_logs', 'drawer_closing_details', 'orders', 'order_items',
    'temporary_invoices', 'temporary_invoice_items', 'promotions',
    'audit_logs', 'login_attempts', 'authorized_devices',
    'system_settings', 'system_license', 'backup_history',
    'schema_migrations', 'sync_queue', 'supplier_promotion_claims'
]

cursor.execute("SHOW TABLES")
existing = set(r[0] for r in cursor.fetchall())
missing = [t for t in verification_tables if t not in existing]

print("\n=== Database Rebuild Verification ===")
print(f"Total tables expected: {len(verification_tables)}")
print(f"Total tables in DB: {len(existing)}")

if missing:
    print("MISSING tables:")
    for t in missing:
        print("  -", t)
else:
    print("All required tables present!")

# Check roles
cursor.execute("SELECT COUNT(*) FROM roles")
print(f"Roles: {cursor.fetchone()[0]} records")
cursor.execute("SELECT * FROM roles WHERE id = 99")
dev = cursor.fetchone()
if dev:
    print(f"Developer role: OK (ID={dev[0]}, name={dev[1]})")
else:
    print("Developer role: MISSING - will be added by fix_db_setup.py")

# Check settings
cursor.execute("SELECT COUNT(*) FROM system_settings")
print(f"System settings: {cursor.fetchone()[0]} records")

# Check users
cursor.execute("SELECT COUNT(*) FROM users")
print(f"Users: {cursor.fetchone()[0]} records")

conn.close()
print("\nDatabase rebuild complete!")
