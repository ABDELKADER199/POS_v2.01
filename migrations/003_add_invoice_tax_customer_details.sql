CREATE TABLE IF NOT EXISTS invoice_tax_customer_details (
    id INT NOT NULL AUTO_INCREMENT,
    invoice_id INT NOT NULL,

    company_name VARCHAR(255) NOT NULL,
    tax_id_number VARCHAR(100) NULL,
    commercial_registry VARCHAR(100) NULL,
    company_address VARCHAR(500) NULL,
    company_phone VARCHAR(100) NULL,
    notes TEXT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_invoice_tax_customer_details_invoice (invoice_id),
    CONSTRAINT fk_invoice_tax_customer_details_invoice
        FOREIGN KEY (invoice_id)
        REFERENCES invoices(id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;