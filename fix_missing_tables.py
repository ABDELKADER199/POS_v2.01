#!/usr/bin/env python3
"""إصلاح قاعدة البيانات: إنشاء الجداول المفقودة حسب متطلبات المستودعات والخدمات"""

import mysql.connector
import sys

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123",
    "database": "stocks",
    "port": 3306,
}


def main():
    # First connect without database to create it
    conn_init = mysql.connector.connect(
        host="localhost", user="root", password="123", port=3306
    )
    cursor_init = conn_init.cursor()
    cursor_init.execute(
        "CREATE DATABASE IF NOT EXISTS stocks CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    conn_init.commit()
    print("DB stocks: created (or existed)")
    conn_init.close()

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("تم الاتصال بقاعدة البيانات stocks")

    # 1. suppliers
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS suppliers (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            address VARCHAR(255),
            tax_number VARCHAR(50),
            current_balance DECIMAL(12,2) DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        conn.commit()
        print("✅ جدول suppliers: تم إنشاؤه")
    except Exception as e:
        print(f"ℹ️ suppliers: {e}")

    # 2. customers
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS customers (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            address VARCHAR(255),
            tax_number VARCHAR(50),
            current_balance DECIMAL(12,2) DEFAULT 0,
            credit_limit DECIMAL(12,2) DEFAULT 0,
            notes TEXT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        conn.commit()
        print("✅ جدول customers: تم إنشاؤه")
    except Exception as e:
        print(f"ℹ️ customers: {e}")

    # 3. purchase_invoices
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS purchase_invoices (
            id INT PRIMARY KEY AUTO_INCREMENT,
            invoice_number VARCHAR(50) DEFAULT NULL,
            supplier_id INT NOT NULL,
            store_id INT NOT NULL,
            invoice_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
            payment_status VARCHAR(50) DEFAULT 'unpaid',
            status VARCHAR(50) DEFAULT 'completed',
            ref_number VARCHAR(50) DEFAULT NULL,
            created_by INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY (store_id) REFERENCES stores(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        conn.commit()
        print("✅ جدول purchase_invoices: تم إنشاؤه")
    except Exception as e:
        print(f"ℹ️ purchase_invoices: {e}")

    # 4. purchase_items
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS purchase_items (
            id INT PRIMARY KEY AUTO_INCREMENT,
            purchase_invoice_id INT NOT NULL,
            product_id INT NOT NULL,
            quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
            unit_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
            total_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
            supplier_support_type VARCHAR(30) NOT NULL DEFAULT 'none',
            supplier_support_value DECIMAL(12,2) DEFAULT 0,
            free_quantity INT DEFAULT 0,
            expiry_date DATE NULL,
            FOREIGN KEY (purchase_invoice_id) REFERENCES purchase_invoices(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        conn.commit()
        print("✅ جدول purchase_items: تم إنشاؤه")
    except Exception as e:
        print(f"ℹ️ purchase_items: {e}")

    # 5. sales_returns
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS sales_returns (
            id INT PRIMARY KEY AUTO_INCREMENT,
            return_number VARCHAR(50) DEFAULT NULL,
            original_invoice_id INT NOT NULL,
            customer_id INT,
            store_id INT NOT NULL,
            return_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
            settlement_method VARCHAR(30) NOT NULL DEFAULT 'cash',
            reason TEXT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'completed',
            created_by INT,
            drawer_id INT NULL,
            FOREIGN KEY (original_invoice_id) REFERENCES invoices(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (store_id) REFERENCES stores(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        conn.commit()
        print("✅ جدول sales_returns: تم إنشاؤه")
    except Exception as e:
        print(f"ℹ️ sales_returns: {e}")

    # 6. system_settings
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS system_settings (
            setting_key VARCHAR(100) PRIMARY KEY,
            setting_value VARCHAR(500) DEFAULT ''
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        conn.commit()
        cursor.execute(
            "INSERT IGNORE INTO system_settings (setting_key, setting_value) VALUES ('backup_path', 'backups'), ('auto_backup_enabled', 'true')"
        )
        conn.commit()
        print("✅ جدول system_settings: تم إنشاؤه")
    except Exception as e:
        print(f"ℹ️ system_settings: {e}")

    # 7. expenses
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS expenses (
            id INT PRIMARY KEY AUTO_INCREMENT,
            store_id INT NOT NULL,
            expense_type VARCHAR(50) NOT NULL,
            amount DECIMAL(12,2) NOT NULL DEFAULT 0,
            description VARCHAR(255),
            is_voided TINYINT(1) DEFAULT 0,
            voided_at DATETIME NULL,
            voided_by INT NULL,
            void_reason VARCHAR(255) NULL,
            is_personal TINYINT(1) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INT,
            FOREIGN KEY (store_id) REFERENCES stores(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        conn.commit()
        print("✅ جدول expenses: تم إنشاؤه")
    except Exception as e:
        print(f"ℹ️ expenses: {e}")

    # 8. promotions (if missing)
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS promotions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            promotion_name VARCHAR(150) NOT NULL,
            promotion_subtype VARCHAR(40) NULL,
            promotion_type VARCHAR(30) NOT NULL DEFAULT 'discount',
            apply_to VARCHAR(20) DEFAULT 'all',
            apply_to_id INT NULL,
            discount_percent DECIMAL(5,2) DEFAULT 0,
            discount_amount DECIMAL(10,2) DEFAULT 0,
            minimum_purchase_amount DECIMAL(10,2) DEFAULT 0,
            start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_date DATETIME NULL,
            is_active TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bundle_product_id INT NULL,
            bundle_price DECIMAL(10,2) DEFAULT 0,
            second_item_discount_percent DECIMAL(5,2) DEFAULT 0,
            funding_source VARCHAR(20) NOT NULL DEFAULT 'company',
            supplier_id INT NULL,
            supplier_support_type VARCHAR(30) NOT NULL DEFAULT 'claim_per_unit',
            supplier_support_value DECIMAL(12,2) DEFAULT 0,
            minimum_margin_percent DECIMAL(5,2) DEFAULT 5
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        conn.commit()
        print("✅ جدول promotions: تم إنشاؤه")
    except Exception as e:
        print(f"ℹ️ promotions: {e}")

    conn.close()
    print("\n✅ تم إصلاح قاعدة البيانات وإضافة الجداول المفقودة!")


if __name__ == "__main__":
    main()
