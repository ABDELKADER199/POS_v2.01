"""
Purchases Repository - مستودع بيانات المشتريات والموردين.
يبقى هذا الملف مسؤولاً عن SQL فقط، بينما قواعد العمل في services.purchase_service.
"""
import logging
import uuid
from typing import Dict, List, Optional

from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class PurchasesRepository(BaseRepository):
    def __init__(self):
        super().__init__()
        self._metadata_cache = {}

    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def columns(self, table_name: str) -> set:
        key = f"columns:{table_name}"
        if key not in self._metadata_cache:
            self._metadata_cache[key] = {
                row["Field"] for row in self._fetch_all(f"SHOW COLUMNS FROM {table_name}")
            }
        return self._metadata_cache[key]

    def existing_tables(self) -> set:
        if "tables" not in self._metadata_cache:
            self._metadata_cache["tables"] = {
                next(iter(row.values())) for row in self._fetch_all("SHOW TABLES")
            }
        return self._metadata_cache["tables"]

    def ensure_purchase_columns(self):
        """إضافة أعمدة المشتريات المطلوبة عند العمل على قاعدة قديمة."""
        try:
            item_columns = self.columns("purchase_items")
            if "expiry_date" not in item_columns:
                self._execute("ALTER TABLE purchase_items ADD COLUMN expiry_date DATE NULL")
            extra_item_columns = {
                "supplier_support_type": "VARCHAR(30) NOT NULL DEFAULT 'none'",
                "supplier_support_value": "DECIMAL(12,2) DEFAULT 0",
                "free_quantity": "INT DEFAULT 0",
            }
            for column, definition in extra_item_columns.items():
                if column not in item_columns:
                    self._execute(f"ALTER TABLE purchase_items ADD COLUMN {column} {definition}")

            invoice_columns = self.columns("purchase_invoices")
            required = {
                "invoice_number": "VARCHAR(50) DEFAULT NULL",
                "invoice_date": "DATETIME DEFAULT CURRENT_TIMESTAMP",
                "ref_number": "VARCHAR(50) DEFAULT NULL",
                "payment_status": "VARCHAR(50) DEFAULT 'unpaid'",
                "status": "VARCHAR(50) DEFAULT 'completed'",
            }
            for column, definition in required.items():
                if column not in invoice_columns:
                    self._execute(f"ALTER TABLE purchase_invoices ADD COLUMN {column} {definition}")

            product_columns = self.columns("products")
            if "supplier_id" not in product_columns:
                self._execute("ALTER TABLE products ADD COLUMN supplier_id INT NULL")

            if "promotions" in self.existing_tables():
                promotion_columns = self.columns("promotions")
                if "funding_source" not in promotion_columns:
                    self._execute(
                        "ALTER TABLE promotions "
                        "ADD COLUMN funding_source VARCHAR(20) NOT NULL DEFAULT 'company'"
                    )
                if "supplier_id" not in promotion_columns:
                    self._execute("ALTER TABLE promotions ADD COLUMN supplier_id INT NULL")
                extra_promotion_columns = {
                    "promotion_subtype": "VARCHAR(40) NULL",
                    "second_item_discount_percent": "DECIMAL(5,2) DEFAULT 0",
                    "bundle_product_id": "INT NULL",
                    "bundle_price": "DECIMAL(12,2) DEFAULT 0",
                    "supplier_support_type": "VARCHAR(30) NOT NULL DEFAULT 'claim_per_unit'",
                    "supplier_support_value": "DECIMAL(12,2) DEFAULT 0",
                    "minimum_margin_percent": "DECIMAL(5,2) DEFAULT 5",
                }
                for column, definition in extra_promotion_columns.items():
                    if column not in promotion_columns:
                        self._execute(f"ALTER TABLE promotions ADD COLUMN {column} {definition}")

            self._execute("""
                CREATE TABLE IF NOT EXISTS purchase_returns (
                    id INT AUTO_INCREMENT PRIMARY KEY,
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
                    FOREIGN KEY (store_id) REFERENCES stores(id),
                    FOREIGN KEY (created_by) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

    def insert_purchase_item(self, invoice_id: int, product_id: int,
                             quantity: int, unit_cost: float,
                             expiry_date: Optional[str],
                             supplier_support_type: str = "none",
                             supplier_support_value: float = 0,
                             free_quantity: int = 0):
        # Use dynamic INSERT to handle missing columns gracefully
        columns = []
        values = []

        # Core columns - include purchase_invoice_id and product_id which are always required
        columns.extend(["purchase_invoice_id", "product_id", "quantity", "unit_cost"])
        values.extend([invoice_id, product_id, quantity, unit_cost])

        # Always include total_cost
        columns.append("total_cost")
        values.append(quantity * unit_cost)

        # expiry_date is optional but always include it (may be NULL)
        columns.append("expiry_date")
        values.append(expiry_date or None)

        # Add optional columns only if they exist in the table
        item_columns = self.columns("purchase_items")
        if "supplier_support_type" in item_columns:
            columns.append("supplier_support_type")
            values.append(supplier_support_type)
        if "supplier_support_value" in item_columns:
            columns.append("supplier_support_value")
            values.append(supplier_support_value)
        if "free_quantity" in item_columns:
            columns.append("free_quantity")
            values.append(free_quantity)

        # Build the INSERT statement dynamically
        placeholders = ", ".join(["%s"] * len(values))
        self._execute(
            f"INSERT INTO purchase_items ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )

    def record_supplier_purchase_debt(self, supplier_id: int, user_id: int,
                                       invoice_id: int, amount: float,
                                       description: str, store_id: int = None):
        if amount <= 0 or "financial_ledger" not in self.existing_tables():
            return
        # Build INSERT statement dynamically based on table structure
        columns = ["account_type", "account_id", "transaction_type", "amount", "reference_type", "reference_id", "description", "created_by"]
        values = ["'Supplier'", supplier_id, "'Credit'", amount, "'Purchase'", invoice_id, f"'{description}'", user_id]
        
        # Add store_id if it exists in the table
        if store_id is not None:
            cursor = self.db.cursor()
            cursor.execute("DESCRIBE financial_ledger")
            cols = [row[0] for row in cursor.fetchall()]
            if "store_id" in cols:
                columns.insert(1, "store_id")  # Add after account_type
                values.insert(1, store_id)
        
        placeholders = ", ".join(["%s"] * len(values))
        query = f"INSERT INTO financial_ledger ({', '.join(columns)}) VALUES ({placeholders})"
        self._execute(query, tuple(values))