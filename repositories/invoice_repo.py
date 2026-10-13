"""
Invoice Repository - مستودع الفواتير
عمليات CRUD للفواتير وبنودها والبيانات الضريبية
"""

import logging
from typing import Optional, List, Dict
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class InvoiceRepository(BaseRepository):
    """مستودع عمليات الفواتير"""

    def __init__(self):
        super().__init__()
        self._metadata_cache = {}
        self.ensure_invoice_columns()

    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def _columns(self, table_name: str) -> set:
        if table_name not in self._metadata_cache:
            self._metadata_cache[table_name] = {
                row["Field"]
                for row in self._fetch_all(f"SHOW COLUMNS FROM {table_name}")
            }
        return self._metadata_cache[table_name]

    def _table_exists(self, table_name: str) -> bool:
        row = self._fetch_one(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = %s
            LIMIT 1
            """,
            (table_name,),
        )
        return bool(row)

    def ensure_invoice_columns(self):
        """تهيئة أعمدة الفواتير المطلوبة عند العمل على قاعدة بيانات قديمة."""
        try:
            invoice_columns = self._columns("invoices")
            required = {
                "customer_id": "INT NULL",
                "cash_amount": "DECIMAL(12, 2) DEFAULT 0",
                "card_amount": "DECIMAL(12, 2) DEFAULT 0",
                "subtotal_amount": "DECIMAL(12, 2) DEFAULT 0",
                "tax_amount": "DECIMAL(12, 2) DEFAULT 0",
                "discount_company_id": "INT NULL",
                "discount_company_name": "VARCHAR(150) NULL",
                "company_discount_amount": "DECIMAL(12, 2) DEFAULT 0",
            }
            for column, definition in required.items():
                if column not in invoice_columns:
                    self._execute(
                        f"ALTER TABLE invoices ADD COLUMN {column} {definition}"
                    )

            decimal_quantity_columns = {
                "invoice_items": "quantity",
                "temporary_invoice_items": "quantity",
                "product_inventory": "quantity_in_stock",
            }
            for table_name, column_name in decimal_quantity_columns.items():
                if self._table_exists(table_name) and column_name in self._columns(
                    table_name
                ):
                    self._execute(
                        f"ALTER TABLE {table_name} "
                        f"MODIFY COLUMN {column_name} DECIMAL(12,3) NOT NULL DEFAULT 0"
                    )

            if "payment_method" in invoice_columns:
                self._execute("""
                    ALTER TABLE invoices
                    MODIFY payment_method ENUM('Cash', 'Card', 'Credit', 'Mixed', 'Check', 'Other')
                    DEFAULT 'Cash'
                """)

            if self._table_exists("promotions"):
                promotion_columns = self._columns("promotions")
                if "funding_source" not in promotion_columns:
                    self._execute(
                        "ALTER TABLE promotions "
                        "ADD COLUMN funding_source VARCHAR(20) NOT NULL DEFAULT 'company'"
                    )
                if "supplier_id" not in promotion_columns:
                    self._execute(
                        "ALTER TABLE promotions ADD COLUMN supplier_id INT NULL"
                    )

            self._execute("""
                CREATE TABLE IF NOT EXISTS supplier_promotion_claims (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    supplier_id INT NOT NULL,
                    promotion_id INT NULL,
                    invoice_id INT NULL,
                    sale_invoice_id INT NULL,
                    product_id INT NULL,
                    quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
                    amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                    status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    claim_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    description VARCHAR(255) NULL,
                    INDEX idx_supplier_promotion_claims_supplier (supplier_id),
                    INDEX idx_supplier_promotion_claims_promotion (promotion_id),
                    INDEX idx_supplier_promotion_claims_sale_invoice (sale_invoice_id)
                )
            """)

            self._commit()
            self._metadata_cache.clear()
        except Exception as e:
            logger.error(f"Error ensuring invoice columns: {e}", exc_info=True)
            self._rollback()

    def get_next_number(self) -> str:
        """توليد رقم فاتورة تسلسلي"""
        row = self._fetch_one(
            "SELECT MAX(CAST(invoice_number AS UNSIGNED)) as max_num FROM invoices"
        )
        next_num = (row["max_num"] or 0) + 1 if row else 1
        return str(next_num)

    def get_discount_companies(self, active_only: bool = True) -> List[dict]:
        query = """
            SELECT dc.id, dc.name, dc.discount_percent,
                   GROUP_CONCAT(dcp.product_id) AS product_ids
            FROM discount_companies dc
            LEFT JOIN discount_company_products dcp ON dcp.company_id = dc.id
        """
        if active_only:
            query += " WHERE dc.is_active = TRUE"
        query += " GROUP BY dc.id, dc.name, dc.discount_percent ORDER BY dc.name"
        companies = self._fetch_all(query)
        for company in companies:
            raw_ids = str(company.get("product_ids") or "").strip()
            company["product_ids"] = [
                int(value) for value in raw_ids.split(",") if value
            ]
        return companies

    def insert_invoice_header(
        self,
        invoice_number: str,
        store_id: int,
        cashier_id: int,
        customer_id: int = None,
        customer_name: str = "",
        customer_phone: str = "",
        customer_address: str = "",
        drawer_id: int = None,
        payment_method: str = "Cash",
        cash_amount: float = 0,
        card_amount: float = 0,
        total_amount: float = 0,
        paid_amount: float = 0,
        remaining_amount: float = 0,
        subtotal_amount: float = 0,
        tax_amount: float = 0,
        discount_company_id: int = None,
        discount_company_name: str = None,
        company_discount_amount: float = 0.0,
    ) -> int:
        columns = [
            "invoice_number",
            "store_id",
            "cashier_id",
            "customer_id",
            "customer_name",
            "customer_phone",
            "customer_address",
            "drawer_id",
            "payment_method",
            "cash_amount",
            "card_amount",
            "total_amount",
            "paid_amount",
            "remaining_amount",
            "subtotal_amount",
            "tax_amount",
        ]
        values = [
            invoice_number,
            store_id,
            cashier_id,
            customer_id,
            customer_name,
            customer_phone,
            customer_address,
            drawer_id,
            payment_method,
            cash_amount,
            card_amount,
            total_amount,
            paid_amount,
            remaining_amount,
            subtotal_amount,
            tax_amount,
        ]

        has_company_discount = bool(
            discount_company_id or (company_discount_amount and company_discount_amount > 0)
        )
        invoice_cols = self._columns("invoices")
        required_company_cols = [
            "discount_company_id",
            "discount_company_name",
            "company_discount_amount",
        ]
        if has_company_discount and not all(c in invoice_cols for c in required_company_cols):
            missing = [c for c in required_company_cols if c not in invoice_cols]
            raise RuntimeError(
                f"تعذر تسجيل الفاتورة: أعمدة شركة الخصم غير متوفرة في قاعدة البيانات: {missing}. يجب تشغيل تهيئة مخطط الفواتير عند بدء التشغيل خارج المعاملة المالية."
            )

        if "discount_company_id" in invoice_cols:
            columns.append("discount_company_id")
            values.append(discount_company_id)
        if "discount_company_name" in invoice_cols:
            columns.append("discount_company_name")
            values.append(discount_company_name)
        if "company_discount_amount" in invoice_cols:
            columns.append("company_discount_amount")
            values.append(company_discount_amount)

        placeholders = ", ".join(["%s"] * len(columns))
        col_names = ", ".join(columns)
        self._execute(
            f"INSERT INTO invoices ({col_names}) VALUES ({placeholders})",
            tuple(values),
        )
        return self._last_id

    def insert_sale_item(
        self,
        invoice_id: int,
        product_id: int,
        quantity: float,
        unit_price: float,
        discount: float,
        total_price: float,
        buy_price: float,
        item_subtotal: float,
        item_tax: float,
        invoice_item_columns: Optional[set] = None,
    ) -> None:
        invoice_item_columns = invoice_item_columns or self._columns("invoice_items")
        columns = [
            "invoice_id",
            "product_id",
            "quantity",
            "unit_price",
            "discount",
            "total_price",
        ]
        values = [invoice_id, product_id, quantity, unit_price, discount, total_price]
        if "buy_price" in invoice_item_columns:
            columns.append("buy_price")
            values.append(buy_price)
        if "item_subtotal" in invoice_item_columns:
            columns.append("item_subtotal")
            values.append(item_subtotal)
        if "item_tax" in invoice_item_columns:
            columns.append("item_tax")
            values.append(item_tax)

        self.insert_sale_invoice_item(columns, values)

    def insert_sale_invoice_item(self, columns: List[str], values: List) -> None:
        placeholders = ", ".join(["%s"] * len(columns))
        self._execute(
            f"INSERT INTO invoice_items ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )

    def decrease_product_inventory(
        self, product_id: int, store_id: int, quantity: float
    ) -> None:
        self._execute(
            """
            UPDATE product_inventory
            SET quantity_in_stock = quantity_in_stock - %s
            WHERE product_id = %s AND store_id = %s
        """,
            (quantity, product_id, store_id),
        )

    def apply_sale_financial_effects(
        self,
        invoice_id: int,
        invoice_number: str,
        store_id: int,
        cashier_id: int,
        customer_id: Optional[int],
        cash_amount: float,
        remaining_amount: float,
    ) -> None:
        if cash_amount > 0:
            description = f"مبيعات نقدية: فاتورة رقم {invoice_number}"
            self.insert_sale_treasury_entry(
                store_id, cash_amount, invoice_id, description, cashier_id
            )

        if customer_id and remaining_amount > 0:
            description = f"مديونية فاتورة رقم {invoice_number}"
            self.increase_customer_balance(customer_id, remaining_amount)
            self.insert_customer_invoice_ledger(
                customer_id, remaining_amount, invoice_id, description, cashier_id
            )

    def save_sale_tax_details(
        self, invoice_id: int, tax_invoice_data: Optional[dict]
    ) -> None:
        if not tax_invoice_data:
            return

        self.upsert_tax_customer_details(
            invoice_id,
            tax_invoice_data.get("company_name", ""),
            tax_invoice_data.get("tax_id_number", ""),
            tax_invoice_data.get("commercial_registry", ""),
            tax_invoice_data.get("company_address", ""),
            tax_invoice_data.get("company_phone", ""),
            tax_invoice_data.get("notes", ""),
        )

    def insert_sale_treasury_entry(
        self,
        store_id: int,
        amount: float,
        invoice_id: int,
        description: str,
        user_id: int,
    ) -> None:
        self._execute(
            """
            INSERT INTO treasury
                (store_id, transaction_type, amount, source_type, source_id, description, user_id)
            VALUES (%s, 'In', %s, 'Sale', %s, %s, %s)
        """,
            (
                store_id,
                amount,
                invoice_id,
                description,
                user_id,
            ),
        )

    def increase_customer_balance(self, customer_id: int, amount: float) -> None:
        self._execute(
            "UPDATE customers SET current_balance = current_balance + %s WHERE id = %s",
            (amount, customer_id),
        )

    def insert_customer_invoice_ledger(
        self,
        customer_id: int,
        amount: float,
        invoice_id: int,
        description: str,
        user_id: int,
    ) -> None:
        columns_fn = getattr(self, "_columns", None)
        ledger_columns = (
            set(columns_fn("financial_ledger")) if callable(columns_fn) else set()
        )

        if (
            "balance_after" in ledger_columns
            or "balance_before" in ledger_columns
            or "store_id" in ledger_columns
        ):
            store_row = self._fetch_one(
                "SELECT store_id FROM users WHERE id = %s", (user_id,)
            )
            store_id = (
                int(store_row["store_id"])
                if store_row and store_row.get("store_id")
                else 0
            )
            current_balance = self._fetch_one(
                "SELECT current_balance FROM customers WHERE id = %s",
                (customer_id,),
            )
            current_balance = (
                float(current_balance["current_balance"] or 0)
                if current_balance
                else 0.0
            )
            balance_before = current_balance - float(amount or 0)
            balance_after = current_balance
            self._execute(
                """
                INSERT INTO financial_ledger
                    (store_id, account_type, account_id, transaction_type, amount,
                     reference_type, reference_id, description, balance_before, balance_after, created_by)
                VALUES (%s, 'Customer', %s, 'Credit', %s, 'Invoice', %s, %s, %s, %s, %s)
            """,
                (
                    store_id,
                    customer_id,
                    amount,
                    invoice_id,
                    description,
                    balance_before,
                    balance_after,
                    user_id,
                ),
            )
            return

        self._execute(
            """
            INSERT INTO financial_ledger
                (account_type, account_id, transaction_type, amount,
                 reference_type, reference_id, description, created_by)
            VALUES ('Customer', %s, 'Credit', %s, 'Invoice', %s, %s, %s)
        """,
            (customer_id, amount, invoice_id, description, user_id),
        )

    def record_supplier_promotion_claims(
        self,
        sale_invoice_id: int,
        invoice_number: str,
        user_id: int,
        claims: List[dict],
    ) -> None:
        for claim in claims or []:
            supplier_id = claim.get("supplier_id")
            amount = round(float(claim.get("amount") or 0), 2)
            if not supplier_id or amount <= 0:
                continue

            promotion_id = claim.get("promotion_id")
            product_id = claim.get("product_id")
            quantity = float(claim.get("quantity") or 0)
            description = (
                claim.get("description")
                or f"مطالبة عرض مورد لفاتورة بيع {invoice_number}"
            )
            self._execute(
                """
                INSERT INTO supplier_promotion_claims
                    (supplier_id, promotion_id, sale_invoice_id, product_id,
                     quantity, amount, status, description)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s)
            """,
                (
                    supplier_id,
                    promotion_id,
                    sale_invoice_id,
                    product_id,
                    quantity,
                    amount,
                    description,
                ),
            )

            if self._table_exists("financial_ledger"):
                columns_fn = getattr(self, "_columns", None)
                ledger_columns = (
                    set(columns_fn("financial_ledger"))
                    if callable(columns_fn)
                    else set()
                )

                if (
                    "balance_after" in ledger_columns
                    or "balance_before" in ledger_columns
                    or "store_id" in ledger_columns
                ):
                    store_row = self._fetch_one(
                        "SELECT store_id FROM users WHERE id = %s", (user_id,)
                    )
                    store_id = (
                        int(store_row["store_id"])
                        if store_row and store_row.get("store_id")
                        else 0
                    )
                    current_balance = self._fetch_one(
                        "SELECT current_balance FROM suppliers WHERE id = %s",
                        (supplier_id,),
                    )
                    current_balance = (
                        float(current_balance["current_balance"] or 0)
                        if current_balance
                        else 0.0
                    )
                    balance_before = current_balance
                    balance_after = current_balance - float(amount or 0)
                    self._execute(
                        """
                        INSERT INTO financial_ledger
                            (store_id, account_type, account_id, transaction_type, amount,
                             reference_type, reference_id, description, balance_before, balance_after, created_by)
                        VALUES (%s, 'Supplier', %s, 'Debit', %s, 'Adjustment', %s, %s, %s, %s, %s)
                    """,
                        (
                            store_id,
                            supplier_id,
                            amount,
                            sale_invoice_id,
                            description,
                            balance_before,
                            balance_after,
                            user_id,
                        ),
                    )
                else:
                    self._execute(
                        """
                        INSERT INTO financial_ledger
                            (account_type, account_id, transaction_type, amount,
                             reference_type, reference_id, description, created_by)
                        VALUES ('Supplier', %s, 'Debit', %s, 'Adjustment', %s, %s, %s)
                    """,
                        (supplier_id, amount, sale_invoice_id, description, user_id),
                    )

    def get_or_create_customer(
        self, name: str = "", phone: str = "", address: str = ""
    ) -> Optional[int]:
        name = (name or "").strip()
        phone = (phone or "").strip()
        address = (address or "").strip()
        if not name and not phone:
            return None
        if phone:
            row = self._fetch_one(
                "SELECT id FROM customers WHERE phone = %s LIMIT 1", (phone,)
            )
            if row:
                updates = []
                params = []
                if name:
                    updates.append("name = %s")
                    params.append(name)
                if address:
                    updates.append("address = %s")
                    params.append(address)
                if updates:
                    params.append(row["id"])
                    self._execute(
                        f"UPDATE customers SET {', '.join(updates)} WHERE id = %s",
                        tuple(params),
                    )
                return row["id"]
        self._execute(
            "INSERT INTO customers (name, phone, address) VALUES (%s, %s, %s)",
            (name or "عميل نقدي", phone or None, address or None),
        )
        return self._last_id

    def get_customer_by_phone(self, phone: str) -> Optional[dict]:
        if not phone:
            return None
        return self._fetch_one(
            """
            SELECT id, name as customer_name, phone as customer_phone,
                   address as customer_address, current_balance, credit_limit
            FROM customers
            WHERE phone = %s
            LIMIT 1
        """,
            (phone,),
        )

    def check_credit_limit(
        self, customer_id: int, additional_amount: float
    ) -> tuple[bool, str]:
        row = self._fetch_one(
            "SELECT name, current_balance, credit_limit FROM customers WHERE id = %s",
            (customer_id,),
        )
        if not row or float(row.get("credit_limit") or 0) <= 0:
            return True, ""
        new_balance = float(row.get("current_balance") or 0) + float(
            additional_amount or 0
        )
        limit = float(row.get("credit_limit") or 0)
        if new_balance > limit:
            return False, (
                f"العميل {row.get('name')} سيتجاوز الحد الائتماني "
                f"({limit:,.2f} ج.م). الرصيد بعد الفاتورة: {new_balance:,.2f} ج.م"
            )
        return True, ""

    def insert_held_invoice_header(
        self,
        temp_invoice_code: str,
        store_id: int,
        cashier_id: int,
        customer_name: str,
        customer_phone: str,
        customer_address: str,
        total_amount: float,
    ) -> int:
        self._execute(
            """
            INSERT INTO temporary_invoices
                (temp_invoice_code, store_id, cashier_id, customer_name,
                 customer_phone, customer_address, total_amount, saved_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                temp_invoice_code,
                store_id,
                cashier_id,
                customer_name,
                customer_phone,
                customer_address,
                total_amount,
                cashier_id,
            ),
        )
        return self._last_id

    def insert_held_invoice_item(
        self,
        temp_invoice_id: int,
        product_id: int,
        quantity: float,
        unit_price: float,
        discount: float,
        total_price: float,
    ) -> None:
        self._execute(
            """
            INSERT INTO temporary_invoice_items
                (temp_invoice_id, product_id, quantity, unit_price, discount, total_price)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (temp_invoice_id, product_id, quantity, unit_price, discount, total_price),
        )

    def delete_held_invoice_record(self, temp_invoice_id: int) -> None:
        self._execute(
            "DELETE FROM temporary_invoices WHERE id = %s", (temp_invoice_id,)
        )

    def get_held_invoices(self, store_id: int, search_term: str = None) -> List[dict]:
        query = """
            SELECT ti.*, u.name as cashier_name
            FROM temporary_invoices ti
            LEFT JOIN users u ON ti.cashier_id = u.id
            WHERE ti.store_id = %s
        """
        params = [store_id]
        if search_term:
            query += """
                AND (
                    ti.temp_invoice_code LIKE %s OR ti.customer_name LIKE %s
                    OR ti.customer_phone LIKE %s
                )
            """
            like = f"%{search_term}%"
            params.extend([like, like, like])
        query += " ORDER BY ti.saved_at DESC LIMIT 100"
        return self._fetch_all(query, tuple(params))

    def get_held_invoice_items(self, temp_invoice_id: int) -> List[dict]:
        return self._fetch_all(
            """
            SELECT tii.*, p.product_code, p.product_name, p.sell_price, p.tax_percent
            FROM temporary_invoice_items tii
            JOIN products p ON tii.product_id = p.id
            WHERE tii.temp_invoice_id = %s
        """,
            (temp_invoice_id,),
        )

    def get_invoice_id_by_number(self, invoice_number: str):
        invoice = self._fetch_one(
            "SELECT id FROM invoices WHERE invoice_number = %s", (invoice_number,)
        )
        return invoice["id"] if invoice else None

    def upsert_tax_customer_details(
        self,
        invoice_id: int,
        company_name: str,
        tax_id_number: str = "",
        commercial_registry: str = "",
        company_address: str = "",
        company_phone: str = "",
        notes: str = "",
    ) -> None:
        self._execute(
            """
            INSERT INTO invoice_tax_customer_details
                (
                    invoice_id,
                    company_name,
                    tax_id_number,
                    commercial_registry,
                    company_address,
                    company_phone,
                    notes
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                company_name = VALUES(company_name),
                tax_id_number = VALUES(tax_id_number),
                commercial_registry = VALUES(commercial_registry),
                company_address = VALUES(company_address),
                company_phone = VALUES(company_phone),
                notes = VALUES(notes)
            """,
            (
                invoice_id,
                company_name,
                tax_id_number,
                commercial_registry,
                company_address,
                company_phone,
                notes,
            ),
        )

    def get_tax_customer_details(self, invoice_number: str) -> dict:
        """Get customer/company details for a tax invoice."""
        return (
            self._fetch_one(
                """
                SELECT itcd.*
                FROM invoice_tax_customer_details itcd
                JOIN invoices i ON itcd.invoice_id = i.id
                WHERE i.invoice_number = %s
                """,
                (invoice_number,),
            )
            or {}
        )
    
    def get_tax_details(self, invoice_number: str) -> dict:
        """جلب بيانات الفاتورة الضريبية"""
        return (
            self._fetch_one(
                """
            SELECT itd.* FROM invoice_tax_details itd
            JOIN invoices i ON itd.invoice_id = i.id
            WHERE i.invoice_number = %s
        """,
                (invoice_number,),
            )
            or {}
        )

    def get_by_number(self, invoice_number: str) -> Optional[dict]:
        """جلب فاتورة بالرقم"""
        return self._fetch_one(
            "SELECT * FROM invoices WHERE invoice_number = %s", (invoice_number,)
        )

    def get_recent(self, store_id: int = None, limit: int = 50) -> List[dict]:
        """جلب أحدث الفواتير"""
        query = "SELECT * FROM invoices WHERE 1=1"
        params = []
        if store_id:
            query += " AND store_id = %s"
            params.append(store_id)
        query += " ORDER BY id DESC LIMIT %s"
        params.append(limit)
        return self._fetch_all(query, tuple(params))

    def get_completed_invoices(
        self,
        store_id: int,
        search_term: str = None,
        start_date: str = None,
        end_date: str = None,
    ) -> List[dict]:
        query = """
            SELECT i.*, u.name as cashier_name
            FROM invoices i
            LEFT JOIN users u ON i.cashier_id = u.id
            WHERE i.status = 'Completed'
        """
        params = []
        if store_id:
            query += " AND i.store_id = %s"
            params.append(store_id)
        if search_term:
            query += """
                AND (
                    i.invoice_number LIKE %s OR i.customer_name LIKE %s
                    OR i.customer_phone LIKE %s
                )
            """
            like = f"%{search_term}%"
            params.extend([like, like, like])
        if start_date and end_date:
            query += " AND DATE(i.invoice_date) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        query += " ORDER BY i.invoice_date DESC LIMIT 1000"  # Increased limit for better visibility
        return self._fetch_all(query, tuple(params))

    def get_invoice_by_id(self, invoice_id: int) -> Optional[dict]:
        return self._fetch_one(
            """
            SELECT i.*, u.name as cashier_name
            FROM invoices i
            LEFT JOIN users u ON i.cashier_id = u.id
            WHERE i.id = %s
        """,
            (invoice_id,),
        )

    def get_invoice_items_by_id(self, invoice_id: int) -> List[dict]:
        return self._fetch_all(
            """
            SELECT ii.*, p.product_name, p.product_code
            FROM invoice_items ii
            JOIN products p ON ii.product_id = p.id
            WHERE ii.invoice_id = %s
        """,
            (invoice_id,),
        )

    def get_items(self, invoice_number: str) -> List[dict]:
        """جلب بنود فاتورة"""
        return self._fetch_all(
            """
            SELECT ii.*, p.product_name, p.product_code
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            JOIN products p ON ii.product_id = p.id
            WHERE i.invoice_number = %s
        """,
            (invoice_number,),
        )

    def get_active_promotions(self) -> List[dict]:
        try:
            return self._fetch_all("""
                SELECT *
                FROM promotions
                WHERE is_active = 1
                  AND CURDATE() BETWEEN start_date AND end_date
                ORDER BY promo_type
            """)
        except Exception as e:
            logger.warning(f"Could not load active promotions: {e}")
            return []

    def calculate_promotions(
        self, invoice_items: List[dict]
    ) -> tuple[List[dict], float]:
        promos = self.get_active_promotions()
        if not promos or not invoice_items:
            return [], 0.0

        product_categories = {}
        for item in invoice_items:
            product_id = item["product_id"]
            if product_id not in product_categories:
                row = self._fetch_one(
                    "SELECT category_id FROM products WHERE id = %s", (product_id,)
                )
                product_categories[product_id] = row.get("category_id") if row else None

        applied = []
        total_discount = 0.0
        for item in invoice_items:
            product_id = item["product_id"]
            quantity = round(float(item.get("quantity") or 0), 3)
            price = float(item.get("price") or item.get("unit_price") or 0)
            category_id = product_categories.get(product_id)
            best_promo = None

            for promo in promos:
                if (
                    promo.get("apply_to") == "product"
                    and int(promo.get("apply_to_id") or 0) != product_id
                ):
                    continue
                if promo.get("apply_to") == "category" and int(
                    promo.get("apply_to_id") or 0
                ) != int(category_id or 0):
                    continue

                min_quantity = float(promo.get("min_quantity") or 1)
                if quantity < min_quantity:
                    continue

                promo_type = promo.get("promo_type")
                value = float(promo.get("value") or 0)
                discount = 0.0
                if promo_type == "percentage":
                    discount = (price * quantity) * (value / 100.0)
                elif promo_type == "fixed":
                    discount = min(value, price * quantity)
                elif promo_type == "fixed_per_unit":
                    discount = min(value * quantity, price * quantity)
                elif promo_type == "buy_x_get_y":
                    buy_quantity = int(promo.get("buy_quantity") or 0)
                    free_quantity = int(value)
                    discrete_quantity = int(quantity)
                    if (
                        buy_quantity > 0
                        and free_quantity > 0
                        and discrete_quantity >= buy_quantity
                    ):
                        group_size = buy_quantity + free_quantity
                        sets = discrete_quantity // group_size
                        remainder = discrete_quantity % group_size
                        free_items = (sets * free_quantity) + max(
                            0, min(remainder - buy_quantity, free_quantity)
                        )
                        discount = free_items * price
                elif promo_type == "second_item_percentage":
                    discounted_items = int(quantity) // 2
                    discount = discounted_items * price * (value / 100.0)
                elif promo_type == "second_item_fixed":
                    discounted_items = int(quantity) // 2
                    discount = min(discounted_items * value, discounted_items * price)
                elif promo_type == "min_qty_discount":
                    discount = (price * quantity) * (value / 100.0)
                elif promo_type == "bundle_price":
                    bundle_product_id = int(promo.get("bundle_product_id") or 0)
                    bundle_price = float(promo.get("bundle_price") or value or 0)
                    if bundle_product_id and bundle_price > 0:
                        companion = next(
                            (
                                other
                                for other in invoice_items
                                if int(other.get("product_id") or 0)
                                == bundle_product_id
                            ),
                            None,
                        )
                        if companion:
                            pairs = min(
                                int(quantity),
                                int(float(companion.get("quantity") or 0)),
                            )
                            companion_price = float(
                                companion.get("price")
                                or companion.get("unit_price")
                                or 0
                            )
                            normal_pair_total = price + companion_price
                            discount = max(
                                0.0, (normal_pair_total - bundle_price) * pairs
                            )

                if discount > 0:
                    discount = round(discount, 2)
                    candidate = {
                        "promo_name": promo.get("name", "عرض"),
                        "promo_id": promo.get("id"),
                        "product_id": product_id,
                        "quantity": quantity,
                        "discount_amount": discount,
                        "company_discount_amount": (
                            0.0
                            if promo.get("funding_source") == "supplier"
                            else discount
                        ),
                        "funding_source": promo.get("funding_source") or "company",
                        "supplier_id": promo.get("supplier_id"),
                        "promo_type": promo_type,
                    }
                    if best_promo is None or discount > best_promo["discount_amount"]:
                        best_promo = candidate
            if best_promo:
                applied.append(best_promo)
                total_discount += best_promo["discount_amount"]
        return applied, round(total_discount, 2)

    def get_open_orders(self, store_id: int, search_term: str = None) -> List[dict]:
        query = """
            SELECT o.*, u.name as call_center_agent
            FROM orders o
            LEFT JOIN users u ON o.call_center_user_id = u.id
            WHERE COALESCE(o.destination_store_id, o.source_store_id) = %s
              AND o.status IN ('Pending', 'Confirmed', 'Prepared')
        """
        params = [store_id]
        if search_term:
            query += """
                AND (
                    o.order_number LIKE %s OR o.customer_name LIKE %s
                    OR o.customer_phone LIKE %s
                )
            """
            like = f"%{search_term}%"
            params.extend([like, like, like])
        query += " ORDER BY o.order_date DESC LIMIT 100"
        return self._fetch_all(query, tuple(params))

    def get_order_items(self, order_id: int) -> List[dict]:
        return self._fetch_all(
            """
            SELECT oi.*, p.product_code, p.product_name, p.sell_price, p.tax_percent
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """,
            (order_id,),
        )

    def update_order_status_record(self, order_id: int, status: str) -> None:
        self._execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))

    def get_product_cross_branch_stock(self, search_term: str) -> dict:
        product = self._fetch_one(
            """
            SELECT *
            FROM products
            WHERE (product_code = %s OR barcode = %s OR product_name LIKE %s)
              AND is_active = TRUE
            ORDER BY CASE
                WHEN product_code = %s THEN 1
                WHEN barcode = %s THEN 2
                ELSE 3
            END
            LIMIT 1
        """,
            (search_term, search_term, f"%{search_term}%", search_term, search_term),
        )
        if not product:
            return {}
        stocks = self._fetch_all(
            """
            SELECT s.id as store_id, s.store_name,
                   COALESCE(pi.quantity_in_stock, 0) as quantity,
                   COALESCE(pi.minimum_quantity, 0) as minimum_quantity
            FROM stores s
            LEFT JOIN product_inventory pi
                ON pi.store_id = s.id AND pi.product_id = %s
            WHERE COALESCE(s.is_active, TRUE) = TRUE
              AND COALESCE(s.store_type, 'Branch') != 'GM'
            ORDER BY s.store_name
        """,
            (product["id"],),
        )
        return {"product": product, "stocks": stocks}

    def _validate_sale_stock(self, items: List[dict], store_id: int):
        for item in items:
            row = self._fetch_one(
                """
                SELECT COALESCE(quantity_in_stock, 0) as qty
                FROM product_inventory
                WHERE product_id = %s AND store_id = %s
            """,
                (item["product_id"], store_id),
            )
            available = float(row.get("qty") or 0) if row else 0.0
            requested = round(float(item.get("quantity") or 0), 3)
            if requested < 0.001:
                raise ValueError("كمية الصنف يجب أن تكون أكبر من صفر")
            if available + 0.0005 < requested:
                raise ValueError(
                    f"المخزون غير كافٍ للصنف {item.get('product_name', item['product_id'])}: "
                    f"المتاح {available} والمطلوب {requested}"
                )

    def validate_sale_stock(self, items: List[dict], store_id: int):
        self._validate_sale_stock(items, store_id)

    def get_product_buy_price(self, product_id: int) -> float:
        row = self._fetch_one(
            "SELECT buy_price FROM products WHERE id = %s", (product_id,)
        )
        return float(row.get("buy_price") or 0) if row else 0.0
