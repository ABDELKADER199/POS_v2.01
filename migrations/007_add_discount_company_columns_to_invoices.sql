-- Migration 007: Add discount company columns to invoices
-- Align invoice table with POS V2 discount company recording.

ALTER TABLE invoices ADD COLUMN discount_company_id INT NULL;
ALTER TABLE invoices ADD COLUMN discount_company_name VARCHAR(150) NULL;
ALTER TABLE invoices ADD COLUMN company_discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0;
