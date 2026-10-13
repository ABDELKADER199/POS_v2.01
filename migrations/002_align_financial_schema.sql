-- Align legacy local databases with the financial fields required by POS V2.
-- Additions are defaulted or nullable and preserve existing records.

ALTER TABLE purchase_invoices ADD COLUMN subtotal DECIMAL(12,2) NOT NULL DEFAULT 0;
ALTER TABLE purchase_invoices ADD COLUMN discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0;
ALTER TABLE purchase_invoices ADD COLUMN tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0;
ALTER TABLE purchase_invoices ADD COLUMN paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0;
ALTER TABLE purchase_invoices ADD COLUMN remaining_amount DECIMAL(12,2) NOT NULL DEFAULT 0;
ALTER TABLE purchase_invoices ADD COLUMN payment_method VARCHAR(50) NULL;

ALTER TABLE expenses ADD COLUMN expense_date DATETIME NULL;
ALTER TABLE expenses ADD COLUMN user_id INT NULL;

UPDATE expenses
SET expense_date = COALESCE(expense_date, created_at),
    user_id = COALESCE(user_id, created_by)
WHERE expense_date IS NULL OR user_id IS NULL;

ALTER TABLE sales_returns ADD COLUMN drawer_id INT NULL;

ALTER TABLE invoice_items ADD COLUMN buy_price DECIMAL(10,2) NULL;

ALTER TABLE return_items ADD COLUMN buy_price DECIMAL(10,2) NULL;
