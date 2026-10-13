CREATE TABLE IF NOT EXISTS discount_company_products (
    company_id INT NOT NULL,
    product_id INT NOT NULL,
    PRIMARY KEY (company_id, product_id),
    FOREIGN KEY (company_id) REFERENCES discount_companies(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);