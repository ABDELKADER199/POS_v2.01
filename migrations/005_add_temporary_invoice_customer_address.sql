SET @has_customer_address = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'temporary_invoices'
      AND column_name = 'customer_address'
);
SET @sql = IF(
    @has_customer_address = 0,
    'ALTER TABLE temporary_invoices ADD COLUMN customer_address VARCHAR(255) NULL AFTER customer_phone',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;