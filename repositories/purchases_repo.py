"""
Purchases Repository - مستودع بيانات المشتريات والموردين.
يبقى هذا الملف مسؤولاً عن SQL فقط، بينما قواعد العمل في services.purchase_service.
"""

import logging
import uuid
from typing import Dict, List, Optional

from repositories.base_repo import BaseRepository
from decimal import Decimal

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
                row["Field"]
                for row in self._fetch_all(f"SHOW COLUMNS FROM {table_name}")
            }
        return self._metadata_cache[key]

    def existing_tables(self) -> set:
        if "tables" not in self._metadata_cache:
            self._metadata_cache["tables"] = {
                next(iter(row.values())) for row in self._fetch_all("SHOW TABLES")
            }
        return self._metadata_cache["tables"]

    # ───────────────────── stores / suppliers ──────────────────────

    def get_all_stores(self) -> List[Dict]:
        return self._fetch_all(
            "SELECT id, store_name FROM stores "
            "WHERE COALESCE(is_active, TRUE) = TRUE "
            "AND COALESCE(store_type, 'Branch') != 'GM' "
            "ORDER BY id"
        )

    def get_all_suppliers(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT
                id, name, phone, address, tax_number,
                opening_balance, current_balance, is_active
            FROM suppliers
            WHERE is_active = 1
            ORDER BY name
        """)

    def add_supplier(
        self,
        name: str,
        phone: str,
        address: str,
        tax_number: str,
        opening_balance: float,
    ) -> bool:
        self._execute(
            "INSERT INTO suppliers (name, phone, address, tax_number, "
            "opening_balance, current_balance) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, phone, address, tax_number, opening_balance, opening_balance),
        )
        self._commit()
        return True

    def update_supplier(
        self, supplier_id: int, name: str, phone: str, address: str, tax_number: str
    ) -> bool:
        self._execute(
            "UPDATE suppliers SET name=%s, phone=%s, address=%s, tax_number=%s "
            "WHERE id=%s",
            (name, phone, address, tax_number, supplier_id),
        )
        self._commit()
        return True

    def soft_delete_supplier(self, supplier_id: int) -> bool:
        self._execute(
            "UPDATE suppliers SET is_active = FALSE WHERE id = %s",
            (supplier_id,),
        )
        self._commit()
        return True

    def get_supplier(self, supplier_id: int):
        query = """
            SELECT id, name, phone, address, tax_number,
                   opening_balance, current_balance, notes,
                   is_active, created_at
            FROM suppliers
            WHERE id = %s
            LIMIT 1
        """
        rows = self._fetch_all(query, (supplier_id,))
        return rows[0] if rows else None

    def increase_supplier_balance(self, supplier_id: int, amount: float):
        self._execute(
            "UPDATE suppliers SET current_balance = COALESCE(current_balance, 0) + %s "
            "WHERE id = %s",
            (amount, supplier_id),
        )

    def decrease_supplier_balance(self, supplier_id: int, amount: float):
        self._execute(
            "UPDATE suppliers SET current_balance = COALESCE(current_balance, 0) - %s "
            "WHERE id = %s",
            (amount, supplier_id),
        )

    def _insert_treasury_entry(
        self,
        store_id: int,
        transaction_type: str,
        amount: float,
        source_type: str,
        source_id: Optional[int],
        description: str,
        user_id: int,
    ):
        treasury_columns = self.columns("treasury")
        columns = ["store_id", "amount", "description"]
        values = [store_id, amount, description]

        if "user_id" in treasury_columns:
            columns.insert(1, "user_id")
            values.insert(1, user_id)
        elif "created_by" in treasury_columns:
            columns.append("created_by")
            values.append(user_id)

        if "transaction_type" in treasury_columns:
            columns.insert(2 if "user_id" in columns else 1, "transaction_type")
            values.insert(2 if "user_id" in columns else 1, transaction_type)

        if "source_type" in treasury_columns:
            columns.append("source_type")
            values.append(source_type)
        elif "reference_type" in treasury_columns:
            columns.append("reference_type")
            values.append(source_type)

        if "source_id" in treasury_columns:
            columns.append("source_id")
            values.append(source_id)
        elif "reference_id" in treasury_columns:
            columns.append("reference_id")
            values.append(source_id)

        placeholders = ", ".join(["%s"] * len(columns))
        self._execute(
            f"INSERT INTO treasury ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )

    def _purchase_return_item_return_column(self) -> str:
        item_columns = self.columns("purchase_return_items")
        if "return_id" in item_columns:
            return "return_id"
        return "purchase_return_id"

    # ───────────────────── schema migration ──────────────────────

    def ensure_purchase_columns(self):
        """إضافة أعمدة المشتريات المطلوبة عند العمل على قاعدة قديمة."""
        try:
            item_columns = self.columns("purchase_items")
            if "expiry_date" not in item_columns:
                self._execute(
                    "ALTER TABLE purchase_items ADD COLUMN expiry_date DATE NULL"
                )
            extra_item_columns = {
                "supplier_support_type": "VARCHAR(30) NOT NULL DEFAULT 'none'",
                "supplier_support_value": "DECIMAL(12,2) DEFAULT 0",
                "free_quantity": "INT DEFAULT 0",
            }
            for column, definition in extra_item_columns.items():
                if column not in item_columns:
                    self._execute(
                        f"ALTER TABLE purchase_items ADD COLUMN {column} {definition}"
                    )

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
                    self._execute(
                        f"ALTER TABLE purchase_invoices ADD COLUMN {column} {definition}"
                    )

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
                    self._execute(
                        "ALTER TABLE promotions ADD COLUMN supplier_id INT NULL"
                    )
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
                        self._execute(
                            f"ALTER TABLE promotions ADD COLUMN {column} {definition}"
                        )

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
        except Exception as e:
            logger.exception("Failed to ensure purchase columns: %s", e)
            raise

    # ───────────────────── products / search ──────────────────────

    def search_product(self, term: str):
        term = (term or "").strip()
        if not term:
            return None

        like_term = f"%{term}%"

        query = """
            SELECT
                p.id, p.product_code, p.product_name, p.barcode,
                p.buy_price, p.cost_price AS cost, p.sell_price, p.supplier_id
            FROM products p
            WHERE p.product_name LIKE %s
                OR p.barcode = %s
                OR p.product_code = %s
            ORDER BY
                CASE
                    WHEN p.product_code = %s THEN 1
                    WHEN p.barcode = %s THEN 2
                    WHEN p.product_name = %s THEN 3
                    ELSE 4
                END,
                p.id ASC
            LIMIT 1
        """
        rows = self._fetch_all(query, (like_term, term, term, term, term, term))
        return rows[0] if rows else None

    def get_product_snapshot(self, product_id: int) -> dict:
        return (
            self._fetch_one("SELECT * FROM products WHERE id = %s", (product_id,)) or {}
        )

    def get_product_total_stock(self, product_id: int):
        res = self._fetch_one(
            "SELECT COALESCE(SUM(quantity_in_stock), 0) AS total "
            "FROM product_inventory WHERE product_id = %s",
            (product_id,),
        )
        return res["total"] if res else 0

    # ───────────────────── purchase invoices ──────────────────────

    def create_purchase_invoice_header(
        self,
        supplier_id: int,
        user_id: int,
        ref_number: str,
        subtotal: float,
        discount: float,
        tax: float,
        total: float,
        paid: float,
        remaining: float,
        payment_method: str,
        payment_status: str,
        store_id: int = None,
    ) -> Dict:
        tmp_num = f"TMP-{uuid.uuid4().hex[:8].upper()}"

        cols = [
            "invoice_number",
            "supplier_id",
            "created_by",
            "ref_number",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "paid_amount",
            "remaining_amount",
            "payment_method",
            "payment_status",
        ]
        vals = [
            tmp_num,
            supplier_id,
            user_id,
            ref_number,
            subtotal,
            discount,
            tax,
            total,
            paid,
            remaining,
            payment_method,
            payment_status,
        ]

        if store_id is not None:
            cols.append("store_id")
            vals.append(store_id)

        placeholders = ", ".join(["%s"] * len(vals))
        self._execute(
            f"INSERT INTO purchase_invoices ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(vals),
        )

        inv_id = self._last_id
        inv_num = f"PUR-{inv_id:06d}"
        self._execute(
            "UPDATE purchase_invoices SET invoice_number = %s WHERE id = %s",
            (inv_num, inv_id),
        )
        return {"id": inv_id, "invoice_number": inv_num}

    def insert_purchase_item(
        self,
        invoice_id: int,
        product_id: int,
        quantity: float,
        unit_cost: float,
        expiry_date: Optional[str] = None,
        supplier_support_type: str = "none",
        supplier_support_value: float = 0,
        free_quantity: float = 0,
    ):
        total_cost = quantity * unit_cost
        exp = expiry_date if expiry_date else None

        self._execute(
            "INSERT INTO purchase_items "
            "(purchase_invoice_id, product_id, quantity, unit_cost, total_cost, expiry_date) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (invoice_id, product_id, quantity, unit_cost, total_cost, exp),
        )

    def get_purchase_history(self, page: int = 1, per_page: int = 100):
        offset = (page - 1) * per_page

        query = """
            SELECT pi.id, pi.invoice_number, s.name as supplier_name,
                   pi.invoice_date as created_at, pi.total_amount, pi.paid_amount,
                   pi.remaining_amount, pi.payment_status, pi.status,
                   u.name as user_name, pi.supplier_id
            FROM purchase_invoices pi
            JOIN suppliers s ON pi.supplier_id = s.id
            LEFT JOIN users u ON pi.created_by = u.id
            ORDER BY pi.invoice_date DESC
            LIMIT %s OFFSET %s
        """
        rows = self._fetch_all(query, (per_page, offset))
        return rows

    def get_purchase_invoice_details(self, search_term: str) -> Optional[Dict]:
        invoice = self._fetch_one(
            """
            SELECT *
            FROM purchase_invoices pi
            WHERE pi.invoice_number = %s
            OR pi.id = %s
            OR pi.ref_number LIKE %s
            LIMIT 1
            """,
            (search_term, search_term, f"%{search_term}%"),
        )

        if not invoice:
            return None

        # Determine the actual FK column used by purchase_return_items.
        return_column = self._purchase_return_item_return_column()

        items = self._fetch_all(
            f"""
            SELECT
                pitems.*,
                products.product_name AS product_name,
                products.product_code AS product_code,

                COALESCE(
                    (
                        SELECT SUM(pri.quantity)
                        FROM purchase_return_items pri
                        INNER JOIN purchase_returns pr
                            ON pr.id = pri.{return_column}
                        WHERE pr.purchase_invoice_id = pitems.purchase_invoice_id
                        AND pri.product_id = pitems.product_id
                    ),
                    0
                ) AS returned_quantity,

                (
                    pitems.quantity - COALESCE(
                        (
                            SELECT SUM(pri.quantity)
                            FROM purchase_return_items pri
                            INNER JOIN purchase_returns pr
                                ON pr.id = pri.{return_column}
                            WHERE pr.purchase_invoice_id = pitems.purchase_invoice_id
                            AND pri.product_id = pitems.product_id
                        ),
                        0
                    )
                ) AS remaining_quantity

            FROM purchase_items pitems
            LEFT JOIN products
                ON products.id = pitems.product_id
            WHERE pitems.purchase_invoice_id = %s
            """,
            (invoice["id"],),
        )

        # Normalize numeric values for the UI.
        for item in items:
            item["returned_quantity"] = float(item.get("returned_quantity") or 0)
            item["remaining_quantity"] = max(
                0,
                float(item.get("remaining_quantity") or 0),
            )

            # Optional compatibility key if the UI uses this name.
            item["returnable_quantity"] = item["remaining_quantity"]

        invoice["items"] = items
        return invoice

    def get_purchase_invoice_for_payment(self, invoice_id: int) -> Optional[Dict]:
        return self._fetch_one(
            "SELECT id, supplier_id, invoice_number, paid_amount, "
            "remaining_amount, payment_method "
            "FROM purchase_invoices WHERE id = %s",
            (invoice_id,),
        )

    def update_purchase_invoice_payment_state(
        self,
        invoice_id: int,
        paid_amount: float,
        remaining_amount: float,
        payment_status: str,
        payment_method: str,
    ):
        self._execute(
            "UPDATE purchase_invoices "
            "SET paid_amount = %s, remaining_amount = %s, "
            "payment_status = %s, payment_method = %s WHERE id = %s",
            (paid_amount, remaining_amount, payment_status, payment_method, invoice_id),
        )

    # ───────────────────── inventory ──────────────────────

    def add_inventory_quantity(self, product_id: int, store_id: int, quantity):
        existing = self._fetch_one(
            "SELECT id, quantity_in_stock FROM product_inventory "
            "WHERE product_id = %s AND store_id = %s LIMIT 1",
            (product_id, store_id),
        )

        if existing:
            self._execute(
                "UPDATE product_inventory "
                "SET quantity_in_stock = quantity_in_stock + %s "
                "WHERE product_id = %s AND store_id = %s",
                (quantity, product_id, store_id),
            )
        else:
            self._execute(
                "INSERT INTO product_inventory "
                "(product_id, store_id, quantity_in_stock) "
                "VALUES (%s, %s, %s)",
                (product_id, store_id, quantity),
            )

    def get_inventory_quantity(self, product_id: int, store_id: int) -> int:
        res = self._fetch_one(
            "SELECT quantity_in_stock as qty "
            "FROM product_inventory WHERE product_id = %s AND store_id = %s",
            (product_id, store_id),
        )
        return res["qty"] if res else 0

    def decrease_inventory_quantity(
        self, product_id: int, store_id: int, quantity: int
    ):
        self._execute(
            "UPDATE product_inventory "
            "SET quantity_in_stock = quantity_in_stock - %s "
            "WHERE product_id = %s AND store_id = %s",
            (quantity, product_id, store_id),
        )

    # ───────────────────── product update ──────────────────────

    def update_product_after_purchase(
        self,
        product_id: int,
        new_cost=None,
        buy_price=None,
        sell_price=None,
        supplier_id=None,
        supplier_name="",
    ):
        cols = self.columns("products")

        set_parts = []
        params = []

        if new_cost is not None:
            set_parts.append("cost_price = %s")
            params.append(new_cost)

        if buy_price is not None:
            set_parts.append("buy_price = %s")
            params.append(buy_price)

        if sell_price is not None and sell_price > 0:
            set_parts.append("sell_price = %s")
            params.append(sell_price)

        if supplier_id is not None and "supplier_id" in cols:
            set_parts.append("supplier_id = %s")
            params.append(supplier_id)

        if supplier_name:
            # Try each possible column name for supplier name
            for col_name in ("last_supplier", "last_supplier_name"):
                if col_name in cols:
                    set_parts.append(f"{col_name} = %s")
                    params.append(supplier_name)
                    break

        if "last_purchase_date" in cols:
            set_parts.append("last_purchase_date = CURDATE()")

        if not set_parts:
            return

        params.append(product_id)
        query = f"UPDATE products SET {', '.join(set_parts)} WHERE id = %s"
        self._execute(query, tuple(params))

    # ───────────────────── supplier balance / debt ──────────────────────
    def record_supplier_purchase_debt(
        self,
        supplier_id: int,
        store_id: int,
        user_id: int,
        invoice_id: int,
        amount: float,
        description: str,
    ):
        if amount <= 0:
            return

        if "financial_ledger" not in self.existing_tables():
            return

        if store_id is None:
            raise ValueError(
                "store_id is required when recording supplier purchase debt"
            )

        # Get supplier balance BEFORE recording this transaction.
        supplier = self._fetch_one(
            "SELECT current_balance " "FROM suppliers " "WHERE id = %s " "FOR UPDATE",
            (supplier_id,),
        )

        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")

        balance_before = float(supplier.get("current_balance") or 0)
        balance_after = balance_before + float(amount)

        self._execute(
            "INSERT INTO financial_ledger "
            "(store_id, account_type, account_id, transaction_type, "
            "description, amount, reference_type, reference_id, "
            "balance_before, balance_after, created_by) "
            "VALUES (%s, 'Supplier', %s, 'Credit', %s, %s, "
            "'Purchase', %s, %s, %s, %s)",
            (
                store_id,
                supplier_id,
                description,
                amount,
                invoice_id,
                balance_before,
                balance_after,
                user_id,
            ),
        )

    def record_supplier_payment(
        self,
        supplier_id: int,
        store_id: int,
        user_id: int,
        invoice_id: Optional[int],
        amount: float,
        payment_method: str,
        description: str,
        record_ledger: bool = True,
    ):
        if amount <= 0:
            return

        if record_ledger and "financial_ledger" in self.existing_tables():
            self._execute(
                "INSERT INTO financial_ledger "
                "(account_type, account_id, transaction_type, amount, "
                "reference_type, reference_id, description, created_by) "
                "VALUES ('Supplier', %s, 'Debit', %s, 'Payment', %s, %s, %s)",
                (supplier_id, amount, invoice_id, description, user_id),
            )

        if "treasury" in self.existing_tables():
            self._insert_treasury_entry(
                store_id=store_id,
                transaction_type="Out",
                amount=amount,
                source_type="PurchasePayment",
                source_id=invoice_id,
                description=f"{description} - {payment_method}",
                user_id=user_id,
            )

    def sync_supplier_balance_from_open_invoices(
        self, supplier_id: Optional[int] = None
    ):
        if not supplier_id:
            return
        self._execute(
            "UPDATE suppliers s "
            "LEFT JOIN ("
            "  SELECT supplier_id, SUM(remaining_amount) AS open_balance "
            "  FROM purchase_invoices "
            "  WHERE payment_status != 'paid' "
            "  GROUP BY supplier_id"
            ") pi ON pi.supplier_id = s.id "
            "SET s.current_balance = COALESCE(pi.open_balance, 0) "
            "WHERE s.id = %s",
            (supplier_id,),
        )

    def reconcile_purchase_return_credits(self, invoice_id: Optional[int] = None):
        query = (
            "UPDATE purchase_invoices pi "
            "SET pi.remaining_amount = GREATEST(0, pi.total_amount - pi.paid_amount "
            "- COALESCE(("
            "SELECT SUM(pr.total_amount) FROM purchase_returns pr "
            "WHERE pr.purchase_invoice_id = pi.id "
            "AND COALESCE(settlement_method, 'credit') = 'credit'"
            "), 0))"
        )
        if invoice_id:
            query += " WHERE pi.id = %s"
            self._execute(query, (invoice_id,))
        else:
            self._execute(query)

    def allocate_supplier_payment(self, supplier_id: int, amount: float):
        invoices = self._fetch_all(
            "SELECT id, remaining_amount, paid_amount "
            "FROM purchase_invoices "
            "WHERE supplier_id = %s AND remaining_amount > 0 "
            "ORDER BY invoice_date ASC",
            (supplier_id,),
        )
        remaining_payment = amount
        for inv in invoices:
            if remaining_payment <= 0:
                break
            pay = min(inv["remaining_amount"], remaining_payment)
            new_paid = inv["paid_amount"] + pay
            new_remaining = inv["remaining_amount"] - pay
            status = "paid" if new_remaining <= 0 else "partial"
            self._execute(
                "UPDATE purchase_invoices "
                "SET paid_amount = %s, remaining_amount = %s, "
                "payment_status = %s WHERE id = %s",
                (new_paid, new_remaining, status, inv["id"]),
            )
            remaining_payment -= pay

    def reconcile_supplier_open_invoices(self, supplier_id: int) -> float:
        supplier = self._fetch_one(
            "SELECT id, current_balance FROM suppliers WHERE id = %s",
            (supplier_id,),
        )
        if not supplier:
            return 0.0
        curr = supplier["current_balance"]

        inv_row = self._fetch_one(
            "SELECT COALESCE(SUM(remaining_amount), 0) AS invoice_balance "
            "FROM purchase_invoices "
            "WHERE supplier_id = %s AND remaining_amount > 0",
            (supplier_id,),
        )
        inv_balance = inv_row["invoice_balance"] if inv_row else 0

        diff = inv_balance - curr
        if diff <= 0:
            return 0.0

        invoices = self._fetch_all(
            "SELECT id, remaining_amount, paid_amount "
            "FROM purchase_invoices "
            "WHERE supplier_id = %s AND remaining_amount > 0 "
            "ORDER BY invoice_date ASC",
            (supplier_id,),
        )
        remaining_diff = diff
        for inv in invoices:
            if remaining_diff <= 0:
                break
            deduct = min(inv["remaining_amount"], remaining_diff)
            self._execute(
                "UPDATE purchase_invoices "
                "SET remaining_amount = remaining_amount - %s, "
                "paid_amount = paid_amount + %s WHERE id = %s",
                (deduct, deduct, inv["id"]),
            )
            remaining_diff -= deduct
        self._commit()
        return float(diff)

    # ───────────────────── purchase returns ──────────────────────

    def create_purchase_return_header(
        self,
        purchase_invoice_id: int,
        supplier_id: int,
        store_id: int,
        user_id: int,
        total_amount: float,
        settlement_method: str,
        reason: str,
    ) -> Dict:
        tmp_num = f"TMP-{uuid.uuid4().hex[:8].upper()}"
        self._execute(
            "INSERT INTO purchase_returns "
            "(return_number, purchase_invoice_id, supplier_id, store_id, "
            "created_by, total_amount, settlement_method, reason) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                tmp_num,
                purchase_invoice_id,
                supplier_id,
                store_id,
                user_id,
                total_amount,
                settlement_method,
                reason,
            ),
        )
        ret_id = self._last_id
        ret_num = f"PR-{ret_id:06d}"
        self._execute(
            "UPDATE purchase_returns SET return_number = %s WHERE id = %s",
            (ret_num, ret_id),
        )
        return {"id": ret_id, "return_number": ret_num}

    def insert_purchase_return_item(
        self,
        return_id: int,
        product_id: int,
        quantity: float,
        unit_cost: float,
    ):
        return_column = self._purchase_return_item_return_column()
        self._execute(
            "INSERT INTO purchase_return_items "
            f"({return_column}, product_id, quantity, unit_cost, total_cost) "
            "VALUES (%s, %s, %s, %s, %s)",
            (return_id, product_id, quantity, unit_cost, quantity * unit_cost),
        )

    def get_purchase_item_remaining_quantity(
        self, invoice_id: int, product_id: int
    ) -> int:
        return_column = self._purchase_return_item_return_column()
        res = self._fetch_one(
            "SELECT (pi.quantity - COALESCE("
            "(SELECT SUM(pri.quantity) FROM purchase_return_items pri "
            f"JOIN purchase_returns pr ON pr.id = pri.{return_column} "
            "WHERE pr.purchase_invoice_id = pi.purchase_invoice_id "
            "AND pri.product_id = pi.product_id), 0)) AS remaining_qty "
            "FROM purchase_items pi "
            "WHERE pi.purchase_invoice_id = %s AND pi.product_id = %s",
            (invoice_id, product_id),
        )
        return res["remaining_qty"] if res else 0

    def record_supplier_purchase_return_credit(
        self,
        supplier_id: int,
        store_id: int,
        user_id: int,
        return_id: int,
        amount: float,
        description: str,
    ):
        if amount <= 0 or "financial_ledger" not in self.existing_tables():
            return

        # Lock/read the latest supplier balance for this store.
        row = self._fetch_one(
            """
            SELECT balance_after
            FROM financial_ledger
            WHERE account_type = 'Supplier'
            AND account_id = %s
            AND store_id = %s
            ORDER BY id DESC
            LIMIT 1
            FOR UPDATE
            """,
            (supplier_id, store_id),
        )

        balance_before = float(row["balance_after"]) if row else 0.0
        balance_after = round(balance_before + float(amount), 2)

        self._execute(
            """
            INSERT INTO financial_ledger
            (
                account_type,
                account_id,
                store_id,
                transaction_type,
                amount,
                balance_before,
                balance_after,
                reference_type,
                reference_id,
                description,
                created_by
            )
            VALUES
            (
                'Supplier',
                %s,
                %s,
                'Debit',
                %s,
                %s,
                %s,
                'Return',
                %s,
                %s,
                %s
            )
            """,
            (
                supplier_id,
                store_id,
                amount,
                balance_before,
                balance_after,
                return_id,
                description,
                user_id,
            ),
        )

    def record_purchase_return_cash_refund(
        self,
        supplier_id: int,
        store_id: int,
        user_id: int,
        return_id: int,
        amount: float,
        description: str,
    ):
        if amount <= 0:
            return

        if "financial_ledger" in self.existing_tables():
            self._execute(
                "INSERT INTO financial_ledger "
                "(account_type, account_id, transaction_type, amount, "
                "reference_type, reference_id, description, created_by) "
                "VALUES ('Supplier', %s, 'Debit', %s, 'Return', %s, %s, %s)",
                (supplier_id, amount, return_id, description, user_id),
            )

        if "treasury" in self.existing_tables():
            self._insert_treasury_entry(
                store_id=store_id,
                transaction_type="In",
                amount=amount,
                source_type="PurchaseReturn",
                source_id=return_id,
                description=description,
                user_id=user_id,
            )

    # ───────────────────── promotions (stub) ──────────────────────

    def create_supplier_funded_promotion(
        self,
        supplier_id: int,
        product_id: int,
        product_name: str,
        discount_value: float,
        invoice_id: int,
        support_type: str = "claim_per_unit",
        support_value: float = None,
        min_quantity: int = 1,
        buy_quantity: int = 1,
        promo_type: str = "fixed_per_unit",
        promotion_subtype: str = "supplier_claim",
    ):
        # TODO: implement supplier-funded promotion persistence
        pass
