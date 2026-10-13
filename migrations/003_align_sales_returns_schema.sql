-- Align legacy sales_returns columns with the canonical schema.
-- This migration preserves existing rows created with invoice_id/cashier_id.

SET @has_original_invoice_id = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'sales_returns'
      AND column_name = 'original_invoice_id'
);
SET @sql = IF(
    @has_original_invoice_id = 0,
    'ALTER TABLE sales_returns ADD COLUMN original_invoice_id INT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_invoice_id = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'sales_returns'
      AND column_name = 'invoice_id'
);
SET @sql = IF(
    @has_invoice_id = 1,
    'UPDATE sales_returns SET original_invoice_id = invoice_id WHERE original_invoice_id IS NULL',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_created_by = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'sales_returns'
      AND column_name = 'created_by'
);
SET @sql = IF(
    @has_created_by = 0,
    'ALTER TABLE sales_returns ADD COLUMN created_by INT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_cashier_id = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'sales_returns'
      AND column_name = 'cashier_id'
);
SET @sql = IF(
    @has_cashier_id = 1,
    'UPDATE sales_returns SET created_by = cashier_id WHERE created_by IS NULL',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_drawer_id = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'sales_returns'
      AND column_name = 'drawer_id'
);
SET @sql = IF(
    @has_drawer_id = 0,
    'ALTER TABLE sales_returns ADD COLUMN drawer_id INT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE sales_returns MODIFY COLUMN original_invoice_id INT NOT NULL;