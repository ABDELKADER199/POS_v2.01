"""
Returns Repository - مستودع المرتجعات
عمليات البحث عن الفواتير ومعالجة المرتجعات
"""

import logging
from typing import Dict, List, Optional
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class ReturnsRepository(BaseRepository):

    def get_invoice_by_number(self, invoice_number: str) -> Optional[Dict]:
        """البحث عن فاتورة برقمها أو بآخر أرقام"""
        row = self._fetch_one(
            """
            SELECT id, invoice_number, invoice_date, total_amount,
                   paid_amount, remaining_amount, payment_method,
                   cash_amount, card_amount, customer_id, customer_name,
                   customer_phone, store_id, status
            FROM invoices
            WHERE invoice_number = %s OR invoice_number LIKE %s
            ORDER BY id DESC LIMIT 1
        """,
            (invoice_number, f"%{invoice_number}"),
        )
        return row

    def get_invoice_items(self, invoice_id: int) -> List[Dict]:
        """جلب أصناف الفاتورة مع تتبع دقيق على مستوى السطر (invoice_item_id) ومعالجة المرتجعات التاريخية"""
        query = """
            SELECT ii.*, ii.id as invoice_item_id, p.product_name,
                   COALESCE(p.product_code, '') as product_code,
                   COALESCE(p.buy_price, 0) as fallback_buy_price,
                   COALESCE((
                       SELECT SUM(ri.quantity)
                       FROM return_items ri JOIN sales_returns sr ON ri.return_id = sr.id
                       WHERE ri.invoice_item_id = ii.id AND LOWER(sr.status) = 'completed'
                   ), 0) as line_returned_quantity,
                   COALESCE((
                       SELECT SUM(ri.total_price)
                       FROM return_items ri JOIN sales_returns sr ON ri.return_id = sr.id
                       WHERE ri.invoice_item_id = ii.id AND LOWER(sr.status) = 'completed'
                   ), 0) as line_returned_amount,
                   COALESCE((
                       SELECT SUM(ri.quantity)
                       FROM return_items ri JOIN sales_returns sr ON ri.return_id = sr.id
                       WHERE ri.product_id = ii.product_id AND ri.invoice_item_id IS NULL
                         AND sr.original_invoice_id = ii.invoice_id AND LOWER(sr.status) = 'completed'
                   ), 0) as legacy_unassigned_returned_quantity
            FROM invoice_items ii
            JOIN products p ON ii.product_id = p.id
            WHERE ii.invoice_id = %s
            ORDER BY ii.id
        """
        try:
            rows = self._fetch_all(query, (invoice_id,))
        except Exception as exc:
            if "invoice_item_id" in str(exc).lower():
                fallback_query = """
                SELECT ii.*, ii.id as invoice_item_id, p.product_name,
                       COALESCE(p.product_code, '') as product_code,
                       COALESCE(p.buy_price, 0) as fallback_buy_price,
                       0 as line_returned_quantity,
                       0 as line_returned_amount,
                       COALESCE((
                           SELECT SUM(ri.quantity)
                           FROM return_items ri
                           JOIN sales_returns sr ON ri.return_id = sr.id
                           WHERE ri.product_id = ii.product_id
                             AND sr.original_invoice_id = ii.invoice_id AND LOWER(sr.status) = 'completed'
                       ), 0) as legacy_unassigned_returned_quantity
                FROM invoice_items ii
                JOIN products p ON ii.product_id = p.id
                WHERE ii.invoice_id = %s
                ORDER BY ii.id
                """
                rows = self._fetch_all(fallback_query, (invoice_id,))
            else:
                raise

        from collections import Counter
        prod_counts = Counter(int(r["product_id"]) for r in rows)
        for r in rows:
            pid = int(r["product_id"])
            r["quantity"] = float(r.get("quantity") or 0)
            r["unit_price"] = float(r.get("unit_price") or 0)
            r["total_price"] = float(r.get("total_price") or 0)
            r["discount"] = float(r.get("discount") or 0)
            if not r.get("buy_price"):
                r["buy_price"] = float(r.get("fallback_buy_price") or 0)
            else:
                r["buy_price"] = float(r["buy_price"])
            if "item_subtotal" not in r or r["item_subtotal"] is None:
                r["item_subtotal"] = float(r.get("total_price") or 0)
            else:
                r["item_subtotal"] = float(r["item_subtotal"])
            if "item_tax" not in r or r["item_tax"] is None:
                r["item_tax"] = 0.0
            else:
                r["item_tax"] = float(r["item_tax"])
            line_ret = float(r.get("line_returned_quantity") or 0)
            legacy_ret = float(r.get("legacy_unassigned_returned_quantity") or 0)
            r["line_returned_amount"] = float(r.get("line_returned_amount") or 0)
            if legacy_ret > 0:
                if prod_counts[pid] == 1:
                    r["returned_quantity"] = line_ret + legacy_ret
                    r["is_ambiguous_return"] = False
                else:
                    r["returned_quantity"] = line_ret
                    r["is_ambiguous_return"] = True
                    r["ambiguous_unassigned_quantity"] = legacy_ret
            else:
                r["returned_quantity"] = line_ret
                r["is_ambiguous_return"] = False
        return rows

    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def get_invoice_for_return(self, invoice_id: int, for_update: bool = False) -> Optional[Dict]:
        query = """
            SELECT id, invoice_number, customer_id, customer_name, store_id,
                   status, payment_method, total_amount, paid_amount,
                   remaining_amount, cash_amount, card_amount
            FROM invoices
            WHERE id = %s
        """
        if for_update:
            query += " FOR UPDATE"
        return self._fetch_one(query, (invoice_id,))

    def create_return_header(
        self,
        return_number: str,
        invoice_id: int,
        store_id: int,
        user_id: int,
        total_return: float,
        reason: str,
        drawer_id: int = None,
    ) -> int:
        self._execute(
            """
            INSERT INTO sales_returns (return_number, original_invoice_id, store_id, created_by,
                total_amount, reason, drawer_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
            (
                return_number,
                invoice_id,
                store_id,
                user_id,
                total_return,
                reason,
                drawer_id,
            ),
        )
        return self._last_id

    def insert_return_item(self, return_id: int, item: Dict):
        if item.get("invoice_item_id"):
            try:
                self._execute(
                    """
                    INSERT INTO return_items
                        (return_id, product_id, invoice_item_id, quantity, unit_price, total_price, buy_price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        return_id,
                        item["product_id"],
                        item["invoice_item_id"],
                        item["quantity"],
                        item["unit_price"],
                        item["total_price"],
                        item["buy_price"],
                    ),
                )
                return
            except Exception as exc:
                if "invoice_item_id" in str(exc).lower():
                    pass
                else:
                    raise

        self._execute(
            """
            INSERT INTO return_items
                (return_id, product_id, quantity, unit_price, total_price, buy_price)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (
                return_id,
                item["product_id"],
                item["quantity"],
                item["unit_price"],
                item["total_price"],
                item["buy_price"],
            ),
        )

    def add_inventory_quantity(self, product_id: int, store_id: int, quantity: int):
        self._execute(
            """
            INSERT INTO product_inventory (product_id, store_id, quantity_in_stock)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity_in_stock = quantity_in_stock + VALUES(quantity_in_stock)
        """,
            (product_id, store_id, quantity),
        )

    def record_cash_refund(
        self,
        store_id: int,
        amount: float,
        return_id: int,
        invoice_number: str,
        return_number: str,
        user_id: int,
    ):
        self._execute(
            """
            INSERT INTO treasury
                (store_id, user_id, transaction_type, amount, source_type,
                 source_id, description)
            VALUES (%s, %s, 'Out', %s, 'Return', %s, %s)
        """,
            (
                store_id,
                user_id,
                amount,
                return_id,
                f"مرتجع فاتورة {invoice_number} - {return_number}",
            ),
        )

    def reduce_customer_balance(self, customer_id: int, amount: float):
        self._execute(
            """
            UPDATE customers
            SET current_balance = GREATEST(0, current_balance - %s)
            WHERE id = %s
        """,
            (amount, customer_id),
        )

    def record_customer_return_ledger(
        self,
        customer_id: int,
        amount: float,
        return_id: int,
        invoice_number: str,
        user_id: int,
    ):
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
            balance_before = current_balance + float(amount or 0)
            balance_after = current_balance

            self._execute(
                """
                INSERT INTO financial_ledger
                    (store_id, account_type, account_id, transaction_type, amount,
                     reference_type, reference_id, description, balance_before, balance_after, created_by)
                VALUES (%s, 'Customer', %s, 'Debit', %s, 'Return', %s, %s, %s, %s, %s)
            """,
                (
                    store_id,
                    customer_id,
                    amount,
                    return_id,
                    f"تخفيض مديونية العميل بسبب مرتجع فاتورة {invoice_number}",
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
            VALUES ('Customer', %s, 'Debit', %s, 'Return', %s, %s, %s)
        """,
            (
                customer_id,
                amount,
                return_id,
                f"تخفيض مديونية العميل بسبب مرتجع فاتورة {invoice_number}",
                user_id,
            ),
        )

    def get_returns_history(
        self,
        store_id: int = None,
        start_date: str = None,
        end_date: str = None,
        return_number: str = None,
    ) -> List[Dict]:
        """جلب سجل المرتجعات"""
        query = """
            SELECT sr.return_number, sr.return_date,
                   sr.total_amount, sr.reason,
                     u.name as cashier_name, s.store_name
            FROM sales_returns sr
                 JOIN users u ON sr.created_by = u.id
            JOIN stores s ON sr.store_id = s.id
            WHERE 1=1
        """
        params = []

        if store_id:
            query += " AND sr.store_id = %s"
            params.append(store_id)
        if start_date and end_date:
            query += " AND DATE(sr.return_date) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        if return_number:
            query += " AND sr.return_number LIKE %s"
            params.append(f"%{return_number}%")

        query += " ORDER BY sr.return_date DESC LIMIT 100"
        return self._fetch_all(query, tuple(params))

    def get_drawer_status(self, user_id: int) -> Optional[Dict]:
        row = self._fetch_one(
            """
            SELECT id, (status = 'Open') as is_open
            FROM drawer_logs WHERE cashier_id = %s AND status = 'Open'
            ORDER BY opening_date DESC LIMIT 1
        """,
            (user_id,),
        )
        return row

    def get_store_open_drawer(self, store_id: int) -> Optional[Dict]:
        return self._fetch_one(
            """
            SELECT dl.id, u.name as cashier_name
            FROM drawer_logs dl JOIN users u ON dl.cashier_id = u.id
            WHERE dl.store_id = %s AND dl.status = 'Open'
            ORDER BY dl.opening_date DESC LIMIT 1
        """,
            (store_id,),
        )
