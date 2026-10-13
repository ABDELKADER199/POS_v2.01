-- =====================================================================
-- POS V2 - Complete Database Schema (Database Engineer Output)
-- Rebuilt & consolidated from legacy database_manager.py + V2 schema
-- Safe to run on fresh OR existing databases (uses CREATE/DROP IF EXISTS)
-- =====================================================================

-- إنشاء قاعدة البيانات إن لم تكن موجودة
CREATE DATABASE IF NOT EXISTS stocks CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE stocks;

-- ─────────────────────────────────────────────────────────────────────
-- 1. Core System Tables (Roles, Stores, Users)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stores (
    id INT PRIMARY KEY AUTO_INCREMENT,
    store_name VARCHAR(100) NOT NULL UNIQUE,
    store_type ENUM('Main','Branch','GM','Warehouse') DEFAULT 'Branch',
    city VARCHAR(50),
    address VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(100),
    manager_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    ip_range_start VARCHAR(15),
    ip_range_end VARCHAR(15),
    require_ip_check TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stores_active (is_active),
    INDEX idx_stores_type (store_type)
);

CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    role_id INT NOT NULL,
    store_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_users_role_store (role_id, store_id)
);

-- Default Roles
INSERT IGNORE INTO roles (id, role_name, description) VALUES
(99, 'developer', 'Developer - full system permissions for testing'),
(1,  'admin',     'مدير النظام - يمتلك جميع الصلاحيات'),
(2,  'manager',   'مدير المخزن'),
(3,  'cashier',   'كاشير'),
(4,  'call_center','موظف Call Center'),
(5,  'warehouse_staff','موظف المخزن'),
(6,  'accountant','Accountant - finance, purchases, and financial reports'),
(7,  'owner',     'Owner - full system permissions');

-- Default Store
INSERT IGNORE INTO stores (id, store_name, store_type, city, address, phone, manager_name, require_ip_check) VALUES
(0, 'مدير عام', 'GM', 'القاهرة', 'المقر الرئيسي', '01070276578', 'عبدالقادر طارق', 0),
(1, 'المخزن الرئيسي', 'Main', 'القاهرية', 'شارع النيل', '0201234567', 'أحمد محمد', 0),
(2, 'فرع الإسكندرية', 'Branch', 'الإسكندرية', 'شارع البحر', '0203456789','محمد علي', 0),
(3, 'فرع الجيزة', 'Branch', 'الجيزة', 'شارع الهرم', '0202345678','فاطمة محمود', 0);

-- ─────────────────────────────────────────────────────────────────────
-- 2. Product Management Tables (COMPLETE)
-- ─────────────────────────────────────────────────────────────────────

-- 2.1. Categories
CREATE TABLE IF NOT EXISTS categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_categories_active (is_active)
);

INSERT IGNORE INTO categories (category_name, description) VALUES
('إلكترونيات', 'أجهزة إلكترونية'),
('ملابس', 'ملابس وأحذية'),
('غذائيات', 'منتجات غذائية'),
('مستحضرات عناية', 'مستحضرات العناية الشخصية'),
('أدوات منزلية', 'أدوات وأجهزة منزلية');

-- 2.2. Suppliers (موردين)
CREATE TABLE IF NOT EXISTS suppliers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    tax_number VARCHAR(50),
    opening_balance DECIMAL(10,2) DEFAULT 0,
    current_balance DECIMAL(10,2) DEFAULT 0,
    notes TEXT,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_suppliers_active (is_active),
    INDEX idx_suppliers_name (name)
);

-- 2.3. Products (المنتجات) - Enhanced
CREATE TABLE IF NOT EXISTS products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_code VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(150) NOT NULL,
    category_id INT NOT NULL,
    supplier_id INT,
    buy_price DECIMAL(10,2) NOT NULL DEFAULT 0,
    sell_price DECIMAL(10,2) NOT NULL DEFAULT 0,
    profit_margin DECIMAL(5,2),
    cost_price DECIMAL(10,2) DEFAULT 0,
    wholesale_price DECIMAL(10,2) DEFAULT 0,
    unit VARCHAR(20) DEFAULT 'قطعة',
    barcode VARCHAR(50) UNIQUE,
    description TEXT,
    image_path VARCHAR(255),
    tax_percent DECIMAL(5,2) DEFAULT 14.00,
    min_quantity INT DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    import_status VARCHAR(30) DEFAULT 'ready',
    import_notes VARCHAR(255),
    last_purchase_date DATE,
    last_supplier_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    INDEX idx_products_code (product_code),
    INDEX idx_products_barcode (barcode),
    INDEX idx_products_category (category_id),
    INDEX idx_products_active (is_active)
);

-- 2.4. Product Units (وحدات متعددة للمنتج)
CREATE TABLE IF NOT EXISTS product_units (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    unit_name VARCHAR(50) NOT NULL,
    conversion_rate DECIMAL(12,4) NOT NULL DEFAULT 1,
    is_default TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY unique_product_unit (product_id, unit_name),
    INDEX idx_units_product (product_id)
);

-- 2.5. Product Images (صور متعددة للمنتج)
CREATE TABLE IF NOT EXISTS product_images (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    image_path VARCHAR(500) NOT NULL,
    is_primary TINYINT(1) DEFAULT 0,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_images_product (product_id),
    INDEX idx_images_primary (is_primary)
);

-- 2.6. Product Variants/Attributes (متغيرات وخصائص المنتجات)
CREATE TABLE IF NOT EXISTS product_attributes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    attribute_name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_attribute_values (
    id INT PRIMARY KEY AUTO_INCREMENT,
    attribute_id INT NOT NULL,
    value VARCHAR(100) NOT NULL,
    FOREIGN KEY (attribute_id) REFERENCES product_attributes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_variants (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    variant_name VARCHAR(150) NOT NULL,
    sku VARCHAR(50) UNIQUE,
    buy_price DECIMAL(10,2) DEFAULT 0,
    sell_price DECIMAL(10,2) DEFAULT 0,
    additional_price DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_variants_product (product_id)
);

CREATE TABLE IF NOT EXISTS variant_attribute_values (
    variant_id INT NOT NULL,
    value_id INT NOT NULL,
    PRIMARY KEY (variant_id, value_id),
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE,
    FOREIGN KEY (value_id) REFERENCES product_attribute_values(id) ON DELETE CASCADE
);

-- 2.7. Product Serial Numbers & Batches (أرقام مسلسلة ودفعات)
CREATE TABLE IF NOT EXISTS product_batches (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    batch_number VARCHAR(100) NOT NULL,
    expiry_date DATE,
    manufacturing_date DATE,
    purchase_price DECIMAL(10,2) DEFAULT 0,
    quantity DECIMAL(12,3) DEFAULT 0,
    remaining_quantity DECIMAL(12,3) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    INDEX idx_batches_product (product_id),
    INDEX idx_batches_expiry (expiry_date),
    UNIQUE KEY unique_batch_product (product_id, batch_number)
);

CREATE TABLE IF NOT EXISTS product_serials (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    serial_number VARCHAR(100) NOT NULL UNIQUE,
    batch_id INT,
    status ENUM('available','sold','warranty','returned') DEFAULT 'available',
    warranty_end_date DATE,
    sold_invoice_id INT,
    sold_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (batch_id) REFERENCES product_batches(id),
    FOREIGN KEY (sold_invoice_id) REFERENCES invoices(id),
    INDEX idx_serials_product (product_id),
    INDEX idx_serials_status (status)
);

-- 2.8. Product Cost History (تاريخ التكاليف)
CREATE TABLE IF NOT EXISTS product_cost_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    buy_price DECIMAL(10,2) NOT NULL,
    sell_price DECIMAL(10,2) NOT NULL,
    changed_by INT,
    change_reason VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (changed_by) REFERENCES users(id),
    INDEX idx_cost_history_product (product_id),
    INDEX idx_cost_history_date (changed_at)
);

-- 2.9. Product Movements Log (سجل حركات المنتج)
CREATE TABLE IF NOT EXISTS product_movements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    source_type VARCHAR(50),
    source_id INT,
    destination_type VARCHAR(50),
    destination_id INT,
    quantity DECIMAL(12,3) NOT NULL,
    unit_price DECIMAL(10,2) DEFAULT 0,
    movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_by INT,
    FOREIGN KEY (product_id) REFERENCES products(id),
    INDEX idx_movements_product (product_id),
    INDEX idx_movements_date (movement_date)
);

-- ─────────────────────────────────────────────────────────────────────
-- 3. Inventory Management Tables
-- ─────────────────────────────────────────────────────────────────────

-- 3.1. Product Inventory (المخزون حسب الفرع)
CREATE TABLE IF NOT EXISTS product_inventory (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    store_id INT NOT NULL,
    quantity_in_stock DECIMAL(12,3) NOT NULL DEFAULT 0,
    reserved_quantity DECIMAL(12,3) DEFAULT 0,
    minimum_quantity INT DEFAULT 10,
    last_count_date DATETIME,
    last_counted_by INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (last_counted_by) REFERENCES users(id),
    UNIQUE KEY unique_product_store (product_id, store_id),
    INDEX idx_inv_store_qty (store_id, quantity_in_stock),
    INDEX idx_inv_product (product_id)
);

-- 3.2. Inventory Count Sessions (جلسات جرد المخزون)
CREATE TABLE IF NOT EXISTS inventory_count_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    count_number VARCHAR(50) NOT NULL UNIQUE,
    store_id INT NOT NULL,
    count_type ENUM('full','partial','cycle','spot') NOT NULL DEFAULT 'partial',
    status ENUM('open','review','approved','cancelled') NOT NULL DEFAULT 'open',
    notes TEXT,
    created_by INT NOT NULL,
    approved_by INT,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (approved_by) REFERENCES users(id),
    INDEX idx_count_store_status (store_id, status)
);

CREATE TABLE IF NOT EXISTS inventory_count_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    product_id INT NOT NULL,
    book_quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
    actual_quantity DECIMAL(12,3),
    variance DECIMAL(12,3),
    unit_cost DECIMAL(12,2) DEFAULT 0,
    notes VARCHAR(255),
    counted_by INT,
    counted_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES inventory_count_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (counted_by) REFERENCES users(id),
    UNIQUE KEY unique_session_product (session_id, product_id),
    INDEX idx_items_session (session_id)
);

CREATE TABLE IF NOT EXISTS inventory_count_adjustments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    item_id INT NOT NULL,
    product_id INT NOT NULL,
    store_id INT NOT NULL,
    old_quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
    new_quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
    variance DECIMAL(12,3) NOT NULL DEFAULT 0,
    unit_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
    adjustment_value DECIMAL(12,2) NOT NULL DEFAULT 0,
    adjustment_type ENUM('increase','decrease','no_change') NOT NULL DEFAULT 'no_change',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES inventory_count_sessions(id),
    FOREIGN KEY (item_id) REFERENCES inventory_count_items(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_adj_session (session_id),
    INDEX idx_adj_store (store_id)
);

-- ─────────────────────────────────────────────────────────────────────
-- 4. Sales Tables
-- ─────────────────────────────────────────────────────────────────────

-- 4.1. Price History
CREATE TABLE IF NOT EXISTS price_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    old_buy_price DECIMAL(10,2),
    new_buy_price DECIMAL(10,2),
    old_sell_price DECIMAL(10,2),
    new_sell_price DECIMAL(10,2),
    changed_by INT NOT NULL,
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes VARCHAR(255),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (changed_by) REFERENCES users(id)
);

-- 4.2. Invoices (الفواتير)
CREATE TABLE IF NOT EXISTS invoices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    store_id INT NOT NULL,
    cashier_id INT NOT NULL,
    customer_id INT,
    customer_name VARCHAR(100),
    customer_phone VARCHAR(20),
    customer_address TEXT,
    drawer_id INT,
    invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12,2) NOT NULL,
    paid_amount DECIMAL(12,2),
    remaining_amount DECIMAL(12,2),
    cash_amount DECIMAL(12,2) DEFAULT 0,
    card_amount DECIMAL(12,2) DEFAULT 0,
    subtotal_amount DECIMAL(12,2) DEFAULT 0,
    tax_amount DECIMAL(12,2) DEFAULT 0,
    payment_method ENUM('Cash','Card','Credit','Mixed','Check','Other') DEFAULT 'Cash',
    status ENUM('Completed','Cancelled','Draft') DEFAULT 'Completed',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (cashier_id) REFERENCES users(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_invoice_number (invoice_number),
    INDEX idx_invoice_date (invoice_date),
    INDEX idx_invoice_status (status)
);

-- 4.3. Invoice Items (بنود الفواتور)
CREATE TABLE IF NOT EXISTS invoice_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_id INT NOT NULL,
    product_id INT,
    product_code VARCHAR(50),
    product_name VARCHAR(150),
    quantity DECIMAL(12,3) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount DECIMAL(10,2) DEFAULT 0,
    total_price DECIMAL(12,2),
    buy_price DECIMAL(10,2),
    tax_percent DECIMAL(5,2) DEFAULT 0,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    item_subtotal DECIMAL(12,2) DEFAULT 0,
    notes VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    INDEX idx_items_invoice (invoice_id)
);

-- 4.4. Sales Returns (المرتجعات)
CREATE TABLE IF NOT EXISTS sales_returns (
    id INT PRIMARY KEY AUTO_INCREMENT,
    return_number VARCHAR(50) NOT NULL UNIQUE,
    original_invoice_id INT NOT NULL,
    customer_id INT,
    store_id INT NOT NULL,
    return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    reason TEXT,
    status ENUM('pending','approved','rejected','completed') NOT NULL DEFAULT 'pending',
    created_by INT,
    approved_by INT,
    approved_at DATETIME,
    FOREIGN KEY (original_invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    INDEX idx_returns_invoice (original_invoice_id),
    INDEX idx_returns_status (status)
);

CREATE TABLE IF NOT EXISTS return_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    return_id INT NOT NULL,
    product_id INT,
    product_code VARCHAR(50),
    product_name VARCHAR(150),
    quantity DECIMAL(12,3) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(12,2),
    buy_price DECIMAL(10,2),
    reason VARCHAR(255),
    FOREIGN KEY (return_id) REFERENCES sales_returns(id) ON DELETE CASCADE,
    INDEX idx_return_items_return (return_id)
);

-- ─────────────────────────────────────────────────────────────────────
-- 5. Purchases Tables (المشتريات)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS purchase_invoices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    supplier_id INT NOT NULL,
    store_id INT NOT NULL,
    invoice_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    payment_status VARCHAR(50) DEFAULT 'unpaid',
    status VARCHAR(50) DEFAULT 'completed',
    ref_number VARCHAR(50),
    created_by INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    INDEX idx_purchases_supplier (supplier_id),
    INDEX idx_purchases_date (invoice_date)
);

CREATE TABLE IF NOT EXISTS purchase_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    purchase_invoice_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity DECIMAL(12,3) DEFAULT 0,
    unit_cost DECIMAL(12,2) DEFAULT 0,
    total_cost DECIMAL(12,2) DEFAULT 0,
    supplier_support_type VARCHAR(30) DEFAULT 'none',
    supplier_support_value DECIMAL(12,2) DEFAULT 0,
    free_quantity INT DEFAULT 0,
    expiry_date DATE,
    FOREIGN KEY (purchase_invoice_id) REFERENCES purchase_invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    INDEX idx_purchase_items_invoice (purchase_invoice_id)
);

CREATE TABLE IF NOT EXISTS purchase_returns (
    id INT PRIMARY KEY AUTO_INCREMENT,
    return_number VARCHAR(50) DEFAULT NULL,
    purchase_invoice_id INT NOT NULL,
    supplier_id INT NOT NULL,
    store_id INT NOT NULL,
    created_by INT NOT NULL,
    return_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12,2) DEFAULT 0,
    settlement_method VARCHAR(30) DEFAULT 'credit',
    reason TEXT,
    status VARCHAR(30) DEFAULT 'completed',
    FOREIGN KEY (purchase_invoice_id) REFERENCES purchase_invoices(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE IF NOT EXISTS purchase_return_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    return_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity DECIMAL(12,3) NOT NULL,
    unit_cost DECIMAL(12,2) DEFAULT 0,
    total_cost DECIMAL(12,2) DEFAULT 0,
    FOREIGN KEY (return_id) REFERENCES purchase_returns(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- ─────────────────────────────────────────────────────────────────────
-- 6. Transfers (تحويلات المخزون)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS warehouse_transfers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    transfer_number VARCHAR(50) NOT NULL UNIQUE,
    from_store_id INT NOT NULL,
    to_store_id INT NOT NULL,
    transfer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_date DATETIME,
    created_by INT NOT NULL,
    received_by INT,
    status ENUM('Pending','In Transit','Received','Cancelled') DEFAULT 'Pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (from_store_id) REFERENCES stores(id),
    FOREIGN KEY (to_store_id) REFERENCES stores(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (received_by) REFERENCES users(id),
    INDEX idx_transfer_status (status),
    INDEX idx_transfer_from (from_store_id),
    INDEX idx_transfer_to (to_store_id)
);

CREATE TABLE IF NOT EXISTS transfer_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    transfer_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity_sent INT NOT NULL,
    quantity_received INT,
    notes VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transfer_id) REFERENCES warehouse_transfers(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    INDEX idx_transfer_items_transfer (transfer_id)
);

-- ─────────────────────────────────────────────────────────────────────
-- 7. Financial & Accounting Tables
-- ─────────────────────────────────────────────────────────────────────

-- 7.1. Customers (العملاء)
CREATE TABLE IF NOT EXISTS customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) UNIQUE,
    address TEXT,
    email VARCHAR(100),
    current_balance DECIMAL(12,2) DEFAULT 0,
    credit_limit DECIMAL(12,2) DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customers_phone (phone),
    INDEX idx_customers_active (is_active)
);

-- 7.2. Expenses (المصروفات)
CREATE TABLE IF NOT EXISTS expenses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    store_id INT NOT NULL,
    expense_type VARCHAR(50) NOT NULL,
    amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    description VARCHAR(255),
    is_personal TINYINT(1) DEFAULT 0,
    is_voided TINYINT(1) DEFAULT 0,
    voided_at DATETIME,
    voided_by INT,
    void_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (voided_by) REFERENCES users(id),
    INDEX idx_expenses_store (store_id),
    INDEX idx_expenses_date (created_at)
);

-- 7.3. Treasury (الخزينة)
CREATE TABLE IF NOT EXISTS treasury (
    id INT PRIMARY KEY AUTO_INCREMENT,
    store_id INT NOT NULL,
    user_id INT NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    description VARCHAR(255),
    source_type VARCHAR(30),
    source_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_treasury_store (store_id),
    INDEX idx_treasury_date (created_at)
);

-- 7.4. Payments (المدفوعات)
CREATE TABLE IF NOT EXISTS discount_companies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL UNIQUE,
    discount_percent DECIMAL(5,2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_discount_company_percent CHECK (discount_percent > 0 AND discount_percent <= 100)
);

-- 7.5. Payments (المدفوعات)
CREATE TABLE IF NOT EXISTS payments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_id INT NOT NULL,
    store_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_by INT,
    notes VARCHAR(255),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (processed_by) REFERENCES users(id),
    INDEX idx_payments_invoice (invoice_id),
    INDEX idx_payments_date (transaction_date)
);

-- 7.5. Settlements (تسويات)
CREATE TABLE IF NOT EXISTS settlements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    account_type VARCHAR(20) NOT NULL,
    account_id INT NOT NULL,
    store_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    settlement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settled_by INT,
    notes VARCHAR(255),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (settled_by) REFERENCES users(id),
    INDEX idx_settlements_account (account_type, account_id),
    INDEX idx_settlements_date (settlement_date)
);

-- 7.6. Financial Ledger (السجل المالي العام)
CREATE TABLE IF NOT EXISTS financial_ledger (
    id INT PRIMARY KEY AUTO_INCREMENT,
    store_id INT NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_type VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    amount DECIMAL(12,2) NOT NULL,
    reference_type VARCHAR(20),
    reference_id INT,
    balance_before DECIMAL(12,2) DEFAULT 0,
    balance_after DECIMAL(12,2) NOT NULL,
    created_by INT,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_ledger_store_date (store_id, transaction_date),
    INDEX idx_ledger_type (transaction_type)
);

-- ─────────────────────────────────────────────────────────────────────
-- 8. Drawer Management (إدارة الدرج)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drawer_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    store_id INT NOT NULL,
    cashier_id INT NOT NULL,
    opening_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    opening_balance DECIMAL(12,2) DEFAULT 0,
    closing_date DATETIME,
    closing_balance DECIMAL(12,2),
    status ENUM('Open','Closed') DEFAULT 'Open',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (cashier_id) REFERENCES users(id),
    INDEX idx_drawer_store (store_id),
    INDEX idx_drawer_status (status)
);

CREATE TABLE IF NOT EXISTS drawer_closing_details (
    id INT PRIMARY KEY AUTO_INCREMENT,
    drawer_log_id INT NOT NULL,
    denomination VARCHAR(50) NOT NULL,
    quantity DECIMAL(12,3) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (drawer_log_id) REFERENCES drawer_logs(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────
-- 9. Orders & Call Center (الطلبات ومركز الاتصالات)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    customer_address TEXT,
    customer_city VARCHAR(50),
    source_store_id INT NOT NULL,
    destination_store_id INT,
    call_center_user_id INT NOT NULL,
    delivery_agent_id INT,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expected_delivery_date DATETIME,
    total_amount DECIMAL(12,2),
    status ENUM('Pending','Confirmed','Prepared','Delivered','Cancelled') DEFAULT 'Pending',
    delivery_status ENUM('Unassigned','Assigned','PickedUp','OutForDelivery','Delivered','Failed') DEFAULT 'Unassigned',
    delivery_assigned_at DATETIME,
    delivery_notes TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (source_store_id) REFERENCES stores(id),
    FOREIGN KEY (destination_store_id) REFERENCES stores(id),
    FOREIGN KEY (call_center_user_id) REFERENCES users(id),
    FOREIGN KEY (delivery_agent_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_order_number (order_number),
    INDEX idx_order_status (status)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT,
    product_code VARCHAR(50),
    product_name VARCHAR(150),
    quantity DECIMAL(12,3) NOT NULL,
    unit_price DECIMAL(10,2),
    total_price DECIMAL(12,2),
    notes VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────
-- 10. Temporary Invoices (فواتير مؤقتة لدرج الكاشير)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS temporary_invoices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    temp_invoice_code VARCHAR(50) NOT NULL UNIQUE,
    store_id INT NOT NULL,
    cashier_id INT NOT NULL,
    customer_name VARCHAR(100),
    customer_phone VARCHAR(20),
    customer_address VARCHAR(255),
    total_amount DECIMAL(12,2),
    saved_by INT NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (cashier_id) REFERENCES users(id),
    FOREIGN KEY (saved_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS temporary_invoice_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    temp_invoice_id INT NOT NULL,
    product_id INT,
    product_code VARCHAR(50),
    product_name VARCHAR(150),
    quantity DECIMAL(12,3) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount DECIMAL(10,2) DEFAULT 0,
    total_price DECIMAL(12,2),
    FOREIGN KEY (temp_invoice_id) REFERENCES temporary_invoices(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────
-- 11. Promotions (العروض الترويجية)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS promotions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    promotion_name VARCHAR(150) NOT NULL,
    promotion_type VARCHAR(30) NOT NULL DEFAULT 'discount',
    promotion_subtype VARCHAR(40),
    apply_to VARCHAR(20) DEFAULT 'all',
    apply_to_id INT,
    discount_percent DECIMAL(5,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    minimum_purchase_amount DECIMAL(10,2) DEFAULT 0,
    buy_quantity INT DEFAULT 0,
    get_quantity INT DEFAULT 0,
    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_date DATETIME,
    is_active TINYINT(1) DEFAULT 1,
    funding_source VARCHAR(20) DEFAULT 'company',
    supplier_id INT,
    supplier_support_type VARCHAR(30) DEFAULT 'claim_per_unit',
    supplier_support_value DECIMAL(12,2) DEFAULT 0,
    minimum_margin_percent DECIMAL(5,2) DEFAULT 5,
    bundle_product_id INT,
    bundle_price DECIMAL(10,2) DEFAULT 0,
    second_item_discount_percent DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    INDEX idx_promotions_active (is_active),
    INDEX idx_promotions_dates (start_date, end_date)
);

-- ─────────────────────────────────────────────────────────────────────
-- 12. Audit & Security
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(100),
    record_id INT,
    old_values JSON,
    new_values JSON,
    action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_audit_date (action_date),
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action)
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    status ENUM('success','failed','locked') NOT NULL,
    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_login_email (email),
    INDEX idx_login_ip (ip_address)
);

CREATE TABLE IF NOT EXISTS authorized_devices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_name VARCHAR(100),
    hardware_id VARCHAR(100) NOT NULL UNIQUE,
    user_id INT,
    is_trusted TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ─────────────────────────────────────────────────────────────────────
-- 13. System Management
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value VARCHAR(500) DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS system_license (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hardware_id VARCHAR(100) NOT NULL UNIQUE,
    activation_key VARCHAR(100) NOT NULL,
    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS backup_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    backup_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(500),
    file_size INT,
    status ENUM('success','failed','in_progress') NOT NULL,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    backup_size_bytes BIGINT,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_backup_date (created_at),
    INDEX idx_backup_status (status)
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sync_queue (
    id INT PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(100) NOT NULL,
    record_id INT NOT NULL,
    operation ENUM('insert','update','delete') NOT NULL,
    payload JSON,
    status ENUM('pending','processing','completed','failed') NOT NULL DEFAULT 'pending',
    retry_count TINYINT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sync_status (status),
    INDEX idx_sync_table (table_name),
    INDEX idx_sync_created (created_at)
);

-- ─────────────────────────────────────────────────────────────────────
-- 14. Invoice Tax Details
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invoice_tax_details (
    id INT PRIMARY KEY AUTO_INCREMENT,
    invoice_id INT NOT NULL,
    tax_rate DECIMAL(5,2) NOT NULL,
    tax_amount DECIMAL(10,2) NOT NULL,
    taxable_amount DECIMAL(10,2) NOT NULL,
    tax_type VARCHAR(50) DEFAULT 'vat',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    INDEX idx_tax_invoice (invoice_id)
);

-- ─────────────────────────────────────────────────────────────────────
-- 15. Supplier Promotion Claims
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS supplier_promotion_claims (
    id INT PRIMARY KEY AUTO_INCREMENT,
    supplier_id INT NOT NULL,
    promotion_id INT,
    invoice_id INT,
    sale_invoice_id INT,
    product_id INT,
    quantity DECIMAL(12,3) DEFAULT 0,
    amount DECIMAL(12,2) DEFAULT 0,
    status VARCHAR(30) DEFAULT 'pending',
    claim_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR(255),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    INDEX idx_claims_supplier (supplier_id),
    INDEX idx_claims_status (status)
);

-- ─────────────────────────────────────────────────────────────────────
-- 16. Indexes for Performance
-- ─────────────────────────────────────────────────────────────────────
CREATE INDEX idx_product_inventory_store ON product_inventory(store_id);
CREATE INDEX idx_product_inventory_product ON product_inventory(product_id);
CREATE INDEX idx_invoice_items_invoice ON invoice_items(invoice_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_transfer_items_transfer ON transfer_items(transfer_id);

-- ─────────────────────────────────────────────────────────────────────
-- 17. Trigger: Update profit margin automatically
-- ─────────────────────────────────────────────────────────────────────
DELIMITER //

DROP TRIGGER IF EXISTS trg_update_product_profit_margin//
CREATE TRIGGER trg_update_product_profit_margin
BEFORE UPDATE ON products
FOR EACH ROW
BEGIN
    IF NEW.buy_price > 0 THEN
        SET NEW.profit_margin = ((NEW.sell_price - NEW.buy_price) / NEW.buy_price) * 100;
    ELSE
        SET NEW.profit_margin = 0;
    END IF;
END//

DROP TRIGGER IF EXISTS trg_calculate_invoice_item_total//
CREATE TRIGGER trg_calculate_invoice_item_total
BEFORE INSERT ON invoice_items
FOR EACH ROW
BEGIN
    SET NEW.total_price = (NEW.quantity * NEW.unit_price) - COALESCE(NEW.discount, 0);
    IF NEW.item_subtotal IS NULL OR NEW.item_subtotal = 0 THEN
        SET NEW.item_subtotal = NEW.quantity * NEW.unit_price;
    END IF;
    IF NEW.tax_amount IS NULL OR NEW.tax_amount = 0 THEN
        SET NEW.tax_amount = NEW.item_subtotal * (COALESCE(NEW.tax_percent, 0) / 100);
    END IF;
END//

DROP TRIGGER IF EXISTS trg_update_invoice_totals//
CREATE TRIGGER trg_update_invoice_totals
AFTER INSERT ON invoice_items
FOR EACH ROW
BEGIN
    UPDATE invoices
    SET total_amount = (
        SELECT COALESCE(SUM(total_price), 0) + COALESCE(SUM(tax_amount), 0)
        FROM invoice_items
        WHERE invoice_id = NEW.invoice_id
    )
    WHERE id = NEW.invoice_id;
END//

DELIMITER ;

-- ─────────────────────────────────────────────────────────────────────
-- 18. Default System Settings
-- ─────────────────────────────────────────────────────────────────────
INSERT IGNORE INTO system_settings (setting_key, setting_value) VALUES
('backup_path', 'backups'),
('auto_backup_enabled', 'true'),
('mysqldump_path', 'C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe'),
('cloud_sync_enabled', 'false'),
('cloud_sync_interval', '600'),
('tax_percent_default', '14.00'),
('currency_symbol', 'ج.م'),
('store_id', '1'),
('printer_name', 'PDF'),
('language', 'ar');

INSERT IGNORE INTO system_settings (setting_key, setting_value) VALUES
('developer_mode', 'true');
