-- Migration 008: Add invoice_item_id to return_items for exact line-level return accounting
-- Preserves backward compatibility: existing historical return rows retain invoice_item_id = NULL.

ALTER TABLE return_items ADD COLUMN invoice_item_id INT NULL;
ALTER TABLE return_items ADD INDEX idx_return_items_invoice_item (invoice_item_id);
