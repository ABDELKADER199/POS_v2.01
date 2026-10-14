"""
Accounts Repository - مستودع الحسابات والمالية
"""

import logging
from typing import Dict, List, Optional
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class AccountsRepository(BaseRepository):
    def __init__(self):
        super().__init__()
        self._metadata_cache = {}
        self.ensure_accounts_columns()

    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def existing_tables(self) -> set:
        if "tables" not in self._metadata_cache:
            self._metadata_cache["tables"] = {
                next(iter(row.values())) for row in self._fetch_all("SHOW TABLES")
            }
        return self._metadata_cache["tables"]

    def _columns(self, table_name: str) -> set:
        key = f"columns:{table_name}"
        if key not in self._metadata_cache:
            self._metadata_cache[key] = {
                row["Field"]
                for row in self._fetch_all(f"SHOW COLUMNS FROM {table_name}")
            }
        return self._metadata_cache[key]

    def ensure_accounts_columns(self):
        """تهيئة أعمدة الحسابات المتقدمة من التطبيق القديم."""
        try:
            customer_columns = self._columns("customers")
            if "credit_limit" not in customer_columns:
                self._execute(
                    "ALTER TABLE customers ADD COLUMN credit_limit DECIMAL(12, 2) DEFAULT 0"
                )
            if "notes" not in customer_columns:
                self._execute("ALTER TABLE customers ADD COLUMN notes TEXT NULL")

            expense_columns = self._columns("expenses")
            if "is_voided" not in expense_columns:
                self._execute(
                    "ALTER TABLE expenses ADD COLUMN is_voided TINYINT(1) DEFAULT 0"
                )
            if "voided_at" not in expense_columns:
                self._execute("ALTER TABLE expenses ADD COLUMN voided_at DATETIME NULL")
            if "voided_by" not in expense_columns:
                self._execute("ALTER TABLE expenses ADD COLUMN voided_by INT NULL")
            if "void_reason" not in expense_columns:
                self._execute(
                    "ALTER TABLE expenses ADD COLUMN void_reason VARCHAR(255) NULL"
                )

            treasury_columns = self._columns("treasury")
            if (
                "user_id" not in treasury_columns
                and "created_by" not in treasury_columns
            ):
                self._execute("ALTER TABLE treasury ADD COLUMN user_id INT NULL")
            if (
                "source_id" not in treasury_columns
                and "reference_id" not in treasury_columns
            ):
                self._execute("ALTER TABLE treasury ADD COLUMN source_id INT NULL")

            product_columns = self._columns("products")
            if "image_path" not in product_columns:
                self._execute(
                    "ALTER TABLE products ADD COLUMN image_path VARCHAR(255) NULL"
                )

            if "promotions" in self.existing_tables():
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

            ledger_columns = self._columns("financial_ledger")
            if "store_id" not in ledger_columns:
                self._execute(
                    "ALTER TABLE financial_ledger ADD COLUMN store_id INT NULL DEFAULT 0"
                )
            if "balance_before" not in ledger_columns:
                self._execute(
                    "ALTER TABLE financial_ledger ADD COLUMN balance_before DECIMAL(12,2) DEFAULT 0"
                )
            if "balance_after" not in ledger_columns:
                self._execute(
                    "ALTER TABLE financial_ledger ADD COLUMN balance_after DECIMAL(12,2) NOT NULL DEFAULT 0"
                )
            elif "balance_after" in ledger_columns:
                try:
                    self._execute(
                        "ALTER TABLE financial_ledger MODIFY COLUMN balance_after DECIMAL(12,2) NOT NULL DEFAULT 0"
                    )
                except Exception:
                    pass
            if "attachment_path" not in ledger_columns:
                self._execute(
                    "ALTER TABLE financial_ledger ADD COLUMN attachment_path VARCHAR(255) NULL"
                )
            if "is_settlement" not in ledger_columns:
                self._execute(
                    "ALTER TABLE financial_ledger ADD COLUMN is_settlement TINYINT(1) DEFAULT 0"
                )

            try:
                self._execute(
                    "ALTER TABLE financial_ledger MODIFY COLUMN account_type "
                    "ENUM('Customer','Supplier','Expense','System') NOT NULL"
                )
                self._execute(
                    "ALTER TABLE financial_ledger MODIFY COLUMN reference_type "
                    "ENUM('Invoice','Purchase','Payment','Return','Expense','Adjustment') NOT NULL"
                )
            except Exception as enum_error:
                logger.warning(f"Could not update ledger enums: {enum_error}")

            self._commit()
            self._metadata_cache.clear()
        except Exception as e:
            logger.error(f"Error ensuring accounts columns: {e}")
            self._rollback()

    def _insert_treasury_compatible(
        self,
        store_id: int,
        transaction_type: str,
        amount: float,
        source_type: str,
        source_id: int,
        description: str,
        user_id: int,
    ) -> int:
        treasury_columns = self._columns("treasury")
        columns = ["store_id", "amount", "description"]
        values = [store_id, amount, description]

        if "user_id" in treasury_columns:
            columns.insert(1, "user_id")
            values.insert(1, user_id)
        elif "created_by" in treasury_columns:
            columns.append("created_by")
            values.append(user_id)

        if "transaction_type" in treasury_columns:
            transaction_index = 2 if "user_id" in columns else 1
            columns.insert(transaction_index, "transaction_type")
            values.insert(transaction_index, transaction_type)

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
        return self._last_id

    def _get_ledger_balance_values(
        self, account_type: str, account_id: int, transaction_type: str, amount: float
    ):
        if account_type not in ("Customer", "Supplier"):
            return 0.0, 0.0

        table = "customers" if account_type == "Customer" else "suppliers"
        row = self._fetch_one(
            f"SELECT current_balance FROM {table} WHERE id = %s", (account_id,)
        )
        current_balance = float(row["current_balance"] or 0) if row else 0.0
        amount = float(amount or 0)

        if str(transaction_type).lower() == "debit":
            balance_before = current_balance + amount
            balance_after = current_balance
        elif str(transaction_type).lower() == "credit":
            balance_before = current_balance - amount
            balance_after = current_balance
        else:
            balance_before = current_balance
            balance_after = current_balance
        return balance_before, balance_after

    # ── Customers ──────────────────────────────────────
    def get_customer_accounts(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT id, name, phone, current_balance, credit_limit
            FROM customers ORDER BY name
        """)

    def get_account_snapshot(
        self, account_type: str, account_id: int
    ) -> Optional[Dict]:
        table = (
            "customers"
            if account_type == "Customer"
            else "suppliers" if account_type == "Supplier" else None
        )
        if not table:
            return None
        return self._fetch_one(f"SELECT * FROM {table} WHERE id = %s", (account_id,))

    def update_account_balance(self, account_type: str, account_id: int, delta: float):
        table = "customers" if account_type == "Customer" else "suppliers"
        self._execute(
            f"UPDATE {table} SET current_balance = current_balance + %s WHERE id = %s",
            (delta, account_id),
        )

    def update_customer_credit_limit(self, customer_id: int, limit: float) -> None:
        self._execute(
            "UPDATE customers SET credit_limit = %s WHERE id = %s", (limit, customer_id)
        )

    # ── Suppliers ──────────────────────────────────────
    def get_all_suppliers(self) -> List[Dict]:
        return self._fetch_all(
            "SELECT id, name, phone, current_balance FROM suppliers ORDER BY name"
        )

    # ── Payments ───────────────────────────────────────
    def _legacy_record_payment(
        self,
        account_type: str,
        account_id: int,
        amount: float,
        user_id: int,
        description: str,
        attachment_path: str = "",
    ) -> bool:
        try:
            table = "customers" if account_type == "Customer" else "suppliers"
            self._execute(
                f"UPDATE {table} SET current_balance = current_balance - %s WHERE id = %s",
                (amount, account_id),
            )

            transaction_type = "Debit" if account_type == "Customer" else "Debit"
            treasury_type = "In" if account_type == "Customer" else "Out"

            self._execute(
                """
                INSERT INTO financial_ledger
                (account_type, account_id, transaction_type, amount, reference_type,
                 description, created_by, attachment_path)
                VALUES (%s, %s, %s, %s, 'Payment', %s, %s, %s)
            """,
                (
                    account_type,
                    account_id,
                    transaction_type,
                    amount,
                    description,
                    user_id,
                    attachment_path or None,
                ),
            )
            ledger_id = self._last_id

            if account_type == "Supplier":
                self.allocate_supplier_payment(account_id, amount)

            self._execute(
                """
                INSERT INTO treasury (store_id, transaction_type, amount, source_type,
                    reference_id, description, created_by)
                VALUES (
                    (SELECT COALESCE(store_id, 1) FROM users WHERE id = %s),
                    %s, %s, 'Settlement', %s, %s, %s
                )
            """,
                (user_id, treasury_type, amount, ledger_id, description, user_id),
            )

            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error recording payment: {e}")
            self._rollback()
            return False

    def _legacy_record_settlement(
        self,
        account_type: str,
        account_id: int,
        amount: float,
        description: str,
        user_id: int,
        attachment_path: str = "",
    ) -> bool:
        try:
            table = "customers" if account_type == "Customer" else "suppliers"
            self._execute(
                f"UPDATE {table} SET current_balance = current_balance - %s WHERE id = %s",
                (amount, account_id),
            )

            ledger_columns = self._columns("financial_ledger")
            columns = [
                "account_type",
                "account_id",
                "transaction_type",
                "amount",
                "reference_type",
                "description",
                "created_by",
            ]
            values = [
                account_type,
                account_id,
                "Debit",
                amount,
                "Adjustment",
                description,
                user_id,
            ]

            if "store_id" in ledger_columns:
                try:
                    store_id = self.get_user_store_id(user_id)
                except Exception:
                    store_id = 0
                columns.insert(0, "store_id")
                values.insert(0, store_id)
            if "attachment_path" in ledger_columns:
                columns.append("attachment_path")
                values.append(attachment_path or None)
            if "is_settlement" in ledger_columns:
                columns.append("is_settlement")
                values.append(1)

            placeholders = ", ".join(["%s"] * len(columns))
            self._execute(
                f"INSERT INTO financial_ledger ({', '.join(columns)}) VALUES ({placeholders})",
                tuple(values),
            )

            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error recording settlement: {e}")
            self._rollback()
            return False

    # ── Account History ────────────────────────────────
    def get_account_history(self, account_type: str, account_id: int) -> List[Dict]:
        return self._fetch_all(
            """
            SELECT transaction_date, transaction_type, amount, reference_type,
                   reference_id, description, attachment_path, is_settlement
            FROM financial_ledger
            WHERE account_type = %s AND account_id = %s
            ORDER BY transaction_date DESC LIMIT 500
        """,
            (account_type, account_id),
        )

    # ── Ledger ─────────────────────────────────────────
    def get_financial_ledger(self, search: str = "", acc_type: str = "") -> List[Dict]:
        query = """
            SELECT l.*, 
                CASE WHEN l.account_type = 'Customer' THEN c.name 
                     WHEN l.account_type = 'Supplier' THEN s.name
                     WHEN l.account_type = 'Expense' THEN 'مصروف'
                     ELSE 'System' END as name
            FROM financial_ledger l
            LEFT JOIN customers c ON l.account_type = 'Customer' AND l.account_id = c.id
            LEFT JOIN suppliers s ON l.account_type = 'Supplier' AND l.account_id = s.id
        """
        params = []
        conditions = []

        if search:
            conditions.append(
                "(l.description LIKE %s OR l.reference_type LIKE %s OR c.name LIKE %s OR s.name LIKE %s)"
            )
            params.extend([f"%{search}%"] * 4)
        if acc_type and acc_type not in ("الكل", "ط§ظ„ظƒظ„"):
            conditions.append("l.account_type = %s")
            params.append(acc_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY l.transaction_date DESC LIMIT 500"
        return self._fetch_all(query, tuple(params))

    def get_debt_totals(self) -> Dict:
        try:
            c = self._fetch_one(
                "SELECT COALESCE(SUM(current_balance), 0) as total FROM customers"
            )
            s = self._fetch_one(
                "SELECT COALESCE(SUM(current_balance), 0) as total FROM suppliers"
            )
            return {
                "customer_debt": float(c["total"]) if c else 0,
                "supplier_debt": float(s["total"]) if s else 0,
            }
        except:
            return {"customer_debt": 0, "supplier_debt": 0}

    # ── Treasury ───────────────────────────────────────
    def get_treasury_transactions(self) -> List[Dict]:
        try:
            return self._fetch_all("""
                SELECT t.*, u.name as user_name
                FROM treasury t
                LEFT JOIN users u ON u.id = COALESCE(t.user_id, t.created_by)
                ORDER BY t.created_at DESC LIMIT 500
            """)
        except:
            return []

    def get_treasury_balance(self) -> float:
        try:
            row = self._fetch_one("""
                SELECT COALESCE(SUM(CASE WHEN transaction_type='In' THEN amount ELSE -amount END), 0) as balance
                FROM treasury
            """)
            return float(row["balance"]) if row else 0
        except:
            return 0

    def _legacy_record_treasury_transaction(
        self,
        store_id: int,
        trans_type: str,
        amount: float,
        source_type: str,
        source_id: int,
        description: str,
        user_id: int,
    ) -> bool:
        try:
            self._insert_treasury_compatible(
                store_id=store_id,
                transaction_type=trans_type,
                amount=amount,
                source_type=source_type,
                source_id=source_id,
                description=description,
                user_id=user_id,
            )
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error recording treasury: {e}")
            self._rollback()
            return False

    def get_user_store_id(self, user_id: int) -> int:
        row = self._fetch_one("SELECT store_id FROM users WHERE id = %s", (user_id,))
        if not row or not row.get("store_id"):
            raise ValueError("لا يوجد فرع مرتبط بهذا المستخدم")
        return int(row["store_id"])

    def insert_treasury_entry(
        self,
        store_id: int,
        transaction_type: str,
        amount: float,
        source_type: str,
        reference_id: int,
        description: str,
        user_id: int,
    ) -> int:
        return self._insert_treasury_compatible(
            store_id=store_id,
            transaction_type=transaction_type,
            amount=amount,
            source_type=source_type,
            source_id=reference_id,
            description=description,
            user_id=user_id,
        )

    def insert_ledger_entry(
        self,
        account_type: str,
        account_id: int,
        transaction_type: str,
        amount: float,
        reference_type: str,
        description: str,
        user_id: int,
        reference_id: int = None,
        attachment_path: str = "",
        is_settlement: bool = False,
        store_id: int = None,
    ) -> int:
        ledger_columns = self._columns("financial_ledger")
        if store_id is None:
            try:
                store_id = self.get_user_store_id(user_id)
            except Exception:
                store_id = 0

        balance_before, balance_after = self._get_ledger_balance_values(
            account_type=account_type,
            account_id=account_id,
            transaction_type=transaction_type,
            amount=amount,
        )

        columns = []
        values = []

        if "store_id" in ledger_columns:
            columns.append("store_id")
            values.append(store_id)

        if "account_type" in ledger_columns:
            columns.append("account_type")
            values.append(account_type)
        if "account_id" in ledger_columns:
            columns.append("account_id")
            values.append(account_id)
        if "transaction_type" in ledger_columns:
            columns.append("transaction_type")
            values.append(transaction_type)
        if "amount" in ledger_columns:
            columns.append("amount")
            values.append(amount)
        if "reference_type" in ledger_columns:
            columns.append("reference_type")
            values.append(reference_type)
        if "reference_id" in ledger_columns:
            columns.append("reference_id")
            values.append(reference_id)
        elif "source_id" in ledger_columns:
            columns.append("source_id")
            values.append(reference_id)

        if "balance_before" in ledger_columns:
            columns.append("balance_before")
            values.append(balance_before)
        if "balance_after" in ledger_columns:
            columns.append("balance_after")
            values.append(balance_after)

        if "description" in ledger_columns:
            columns.append("description")
            values.append(description)

        if "created_by" in ledger_columns:
            columns.append("created_by")
            values.append(user_id)
        elif "user_id" in ledger_columns:
            columns.append("user_id")
            values.append(user_id)

        if "attachment_path" in ledger_columns:
            columns.append("attachment_path")
            values.append(attachment_path or None)
        if "is_settlement" in ledger_columns:
            columns.append("is_settlement")
            values.append(1 if is_settlement else 0)

        if not columns:
            raise ValueError("No compatible columns found in financial_ledger")

        placeholders = ", ".join(["%s"] * len(columns))
        self._execute(
            f"INSERT INTO financial_ledger ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )
        return self._last_id

    # ── Expenses ───────────────────────────────────────
    def get_expenses(self, store_id: int) -> List[Dict]:
        return self._fetch_all(
            """
            SELECT e.id, e.expense_date, e.expense_type, e.amount,
                   e.description, e.is_personal, u.name as user_name
            FROM expenses e
            JOIN users u ON e.user_id = u.id
            WHERE e.store_id = %s
              AND COALESCE(e.is_voided, 0) = 0
            ORDER BY e.expense_date DESC LIMIT 500
        """,
            (store_id,),
        )

    def insert_expense(
        self,
        store_id: int,
        user_id: int,
        expense_type: str,
        amount: float,
        description: str,
        is_personal: bool,
    ) -> int:
        self._execute(
            """
            INSERT INTO expenses (store_id, user_id, expense_type, amount, description, is_personal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (store_id, user_id, expense_type, amount, description, is_personal),
        )
        return self._last_id

    def get_expense(self, expense_id: int) -> Optional[Dict]:
        return self._fetch_one("SELECT * FROM expenses WHERE id = %s", (expense_id,))

    def mark_expense_voided(self, expense_id: int, user_id: int, reason: str):
        self._execute(
            """
            UPDATE expenses
            SET is_voided = 1, voided_at = NOW(), voided_by = %s, void_reason = %s
            WHERE id = %s AND COALESCE(is_voided, 0) = 0
        """,
            (user_id, reason, expense_id),
        )

    def _legacy_add_expense(
        self,
        store_id: int,
        user_id: int,
        expense_type: str,
        amount: float,
        description: str,
        is_personal: bool,
    ) -> bool:
        try:
            self._execute(
                """
                INSERT INTO expenses (store_id, user_id, expense_type, amount, description, is_personal)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (store_id, user_id, expense_type, amount, description, is_personal),
            )
            expense_id = self._last_id
            self._execute(
                """
                INSERT INTO treasury (store_id, transaction_type, amount, source_type,
                    reference_id, description, created_by)
                VALUES (%s, 'Out', %s, 'Expense', %s, %s, %s)
            """,
                (
                    store_id,
                    amount,
                    expense_id,
                    f"مصروف: {expense_type} - {description or ''}",
                    user_id,
                ),
            )
            self._execute(
                """
                INSERT INTO financial_ledger
                    (account_type, account_id, transaction_type, amount, reference_type,
                     reference_id, description, created_by)
                VALUES ('Expense', %s, 'Debit', %s, 'Expense', %s, %s, %s)
            """,
                (
                    user_id,
                    amount,
                    expense_id,
                    f"مصروف: {expense_type} - {description or ''}",
                    user_id,
                ),
            )
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error adding expense: {e}")
            self._rollback()
            return False

    def _legacy_delete_expense(self, expense_id: int) -> bool:
        try:
            expense = self.get_expense(expense_id)
            if not expense or bool(expense.get("is_voided")):
                return False
            amount = float(expense.get("amount") or 0)
            if not expense.get("store_id"):
                logger.error("Cannot reverse expense %s without a store", expense_id)
                return False
            store_id = int(expense["store_id"])
            actor_id = expense.get("voided_by") or expense.get("user_id")
            if not actor_id:
                logger.error(
                    "Cannot reverse expense %s without an accountable user", expense_id
                )
                return False
            description = f"قيد عكسي لإلغاء مصروف #{expense_id}"
            self.mark_expense_voided(expense_id, actor_id, "إلغاء")
            self.insert_treasury_entry(
                store_id, "In", amount, "Adjustment", expense_id, description, actor_id
            )
            self.insert_ledger_entry(
                "Expense",
                actor_id,
                "Credit",
                amount,
                "Expense",
                description,
                actor_id,
                expense_id,
            )
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting expense: {e}")
            self._rollback()
            return False

    def get_financial_report(
        self, store_id: int, start_date: str, end_date: str
    ) -> Dict:
        try:
            sales = self._fetch_one(
                """
                SELECT COALESCE(SUM(total_amount), 0) as total
                FROM invoices WHERE store_id = %s AND status = 'Completed'
                AND DATE(invoice_date) BETWEEN %s AND %s
            """,
                (store_id, start_date, end_date),
            )

            returns = self._fetch_one(
                """
                SELECT COALESCE(SUM(total_amount), 0) as total
                FROM sales_returns WHERE store_id = %s 
                AND DATE(return_date) BETWEEN %s AND %s
            """,
                (store_id, start_date, end_date),
            )

            expenses = self._fetch_one(
                """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM expenses WHERE store_id = %s AND is_personal = FALSE
                AND COALESCE(is_voided, 0) = 0
                AND DATE(expense_date) BETWEEN %s AND %s
            """,
                (store_id, start_date, end_date),
            )

            personal = self._fetch_one(
                """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM expenses WHERE store_id = %s AND is_personal = TRUE
                AND COALESCE(is_voided, 0) = 0
                AND DATE(expense_date) BETWEEN %s AND %s
            """,
                (store_id, start_date, end_date),
            )

            total_sales = float(sales["total"]) if sales else 0
            total_returns = float(returns["total"]) if returns else 0
            total_expenses = float(expenses["total"]) if expenses else 0
            total_personal = float(personal["total"]) if personal else 0

            net_profit = total_sales - total_returns - total_expenses
            net_cash = net_profit - total_personal

            return {
                "total_sales": total_sales,
                "total_returns": total_returns,
                "total_cogs": 0,
                "cost_of_returns": 0,
                "total_expenses": total_expenses,
                "personal_expenses": total_personal,
                "net_profit": net_profit,
                "net_cash": net_cash,
            }
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return None

    def get_debt_aging_report(self) -> List[Dict]:
        try:
            return self._fetch_all("""
                SELECT c.name, c.current_balance,
                       COALESCE(DATEDIFF(NOW(), MAX(i.invoice_date)), 0) as days_since_last_sale
                FROM customers c
                LEFT JOIN invoices i ON c.id = i.customer_id
                WHERE c.current_balance > 0
                GROUP BY c.id, c.name, c.current_balance
                ORDER BY days_since_last_sale DESC
            """)
        except Exception as e:
            logger.error(f"Error fetching debt aging report: {e}")
            return []

    def allocate_supplier_payment(self, supplier_id: int, amount: float):
        remaining = float(amount or 0)
        if remaining <= 0:
            return
        invoices = self._fetch_all(
            """
            SELECT id, remaining_amount, paid_amount
            FROM purchase_invoices
            WHERE supplier_id = %s AND COALESCE(payment_status, 'unpaid') != 'paid'
            ORDER BY invoice_date ASC, id ASC
        """,
            (supplier_id,),
        )
        for invoice in invoices:
            if remaining <= 0:
                break
            invoice_remaining = float(invoice.get("remaining_amount") or 0)
            invoice_paid = float(invoice.get("paid_amount") or 0)
            if invoice_remaining <= 0:
                continue
            allocated = min(remaining, invoice_remaining)
            new_paid = invoice_paid + allocated
            new_remaining = max(invoice_remaining - allocated, 0)
            status = "paid" if new_remaining <= 0 else "partial"
            self._execute(
                """
                UPDATE purchase_invoices
                SET paid_amount = %s, remaining_amount = %s, payment_status = %s
                WHERE id = %s
            """,
                (new_paid, new_remaining, status, invoice["id"]),
            )
            remaining -= allocated

    # ── Promotions ─────────────────────────────────────
    def get_promotion_categories(self) -> List[Dict]:
        try:
            return self._fetch_all("""
                SELECT id, category_name
                FROM categories
                WHERE is_active = TRUE
                ORDER BY category_name
            """)
        except Exception as e:
            logger.error(f"Error fetching promotion categories: {e}")
            return []

    def search_promotion_products(self, term: str = "") -> List[Dict]:
        try:
            like = f"%{term or ''}%"
            return self._fetch_all(
                """
                SELECT id, product_code, product_name, barcode, sell_price,
                       COALESCE(buy_price, 0) as buy_price
                FROM products
                WHERE is_active = TRUE
                  AND (%s = '%%' OR product_name LIKE %s OR product_code LIKE %s OR barcode LIKE %s)
                ORDER BY product_name
                LIMIT 500
            """,
                (like, like, like, like),
            )
        except Exception as e:
            logger.error(f"Error fetching promotion products: {e}")
            return []

    def search_discount_eligible_products(self, term: str = "", min_margin_percent: float = 0.0) -> List[Dict]:
        """جلب المنتجات التي سعر بيعها أعلى من سعر شرائها فقط (يوجد هامش ربح).
        يُستخدم في حوار خصومات الشركات لمنع اختيار منتجات بدون هامش ربح.
        min_margin_percent: الحد الأدنى لنسبة هامش الربح المطلوبة (مثلاً 5.0 = 5%)
        """
        try:
            like = f"%{term or ''}%"
            min_margin = max(0.0, float(min_margin_percent or 0)) / 100.0
            return self._fetch_all(
                """
                SELECT id, product_code, product_name, barcode,
                       sell_price, COALESCE(buy_price, 0) as buy_price,
                       ROUND(sell_price - COALESCE(buy_price, 0), 2) as profit_amount,
                       CASE WHEN sell_price > 0
                            THEN ROUND(((sell_price - COALESCE(buy_price, 0)) / sell_price) * 100, 1)
                            ELSE 0
                       END as profit_percent
                FROM products
                WHERE is_active = TRUE
                  AND sell_price > 0
                  AND COALESCE(buy_price, 0) > 0
                  AND sell_price > COALESCE(buy_price, 0)
                  AND ((sell_price - COALESCE(buy_price, 0)) / sell_price) > %s
                  AND (%s = '%%' OR product_name LIKE %s OR product_code LIKE %s OR barcode LIKE %s)
                ORDER BY product_name
                LIMIT 500
            """,
                (min_margin, like, like, like, like),
            )
        except Exception as e:
            logger.error(f"Error fetching discount eligible products: {e}")
            return []

    def get_all_promotions(self) -> List[Dict]:
        try:
            return self._fetch_all("""
                SELECT p.*, s.name AS supplier_name,
                    pr.product_code AS apply_product_code,
                    pr.barcode AS apply_product_barcode,
                    pr.product_name AS apply_product_name,
                    c.category_name AS apply_category_name,
                    CASE WHEN p.apply_to = 'product' THEN pr.product_name
                         WHEN p.apply_to = 'category' THEN c.category_name
                         ELSE 'الكل' END as apply_to_name
                FROM promotions p
                LEFT JOIN products pr ON p.apply_to = 'product' AND p.apply_to_id = pr.id
                LEFT JOIN categories c ON p.apply_to = 'category' AND p.apply_to_id = c.id
                LEFT JOIN suppliers s ON p.supplier_id = s.id
                ORDER BY p.created_at DESC
            """)
        except:
            return []

    def get_promotion_by_id(self, promo_id: int) -> Dict:
        return (
            self._fetch_one("SELECT * FROM promotions WHERE id = %s", (promo_id,)) or {}
        )

    def get_promotion_margin_products(
        self, apply_to: str, apply_to_id=None
    ) -> List[Dict]:
        params = []
        query = """
            SELECT id, product_name, buy_price, sell_price
            FROM products
            WHERE is_active = TRUE
        """
        if apply_to == "product":
            query += " AND id = %s"
            params.append(apply_to_id)
        elif apply_to == "category":
            query += " AND category_id = %s"
            params.append(apply_to_id)
        query += " ORDER BY product_name LIMIT 5000"
        return self._fetch_all(query, tuple(params))

    def get_active_promotion_catalog_products(self) -> List[Dict]:
        try:
            return self._fetch_all("""
                SELECT
                    p.id as product_id,
                    p.product_code,
                    p.barcode,
                    p.product_name,
                    p.sell_price,
                    p.image_path,
                    c.category_name,
                    promo.id as promotion_id,
                    promo.name as promotion_name,
                    promo.promo_type,
                    promo.value,
                    promo.min_quantity,
                    promo.buy_quantity,
                    promo.bundle_product_id,
                    promo.bundle_price,
                    bundle_product.product_name AS bundle_product_name
                FROM promotions promo
                JOIN products p ON (
                    promo.apply_to = 'all'
                    OR (promo.apply_to = 'category' AND p.category_id = promo.apply_to_id)
                    OR (promo.apply_to = 'product' AND p.id = promo.apply_to_id)
                )
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN products bundle_product ON bundle_product.id = promo.bundle_product_id
                WHERE promo.is_active = TRUE
                  AND CURDATE() BETWEEN DATE(promo.start_date) AND DATE(promo.end_date)
                  AND p.is_active = TRUE
                ORDER BY promo.name, c.category_name, p.product_name
            """)
        except Exception as e:
            logger.error(f"Error fetching catalog products: {e}")
            return []

    def update_product_image_path(self, product_id: int, image_path: str) -> bool:
        try:
            self._execute(
                "UPDATE products SET image_path = %s WHERE id = %s",
                (image_path, product_id),
            )
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error updating product image path: {e}")
            self._rollback()
            return False

    def insert_promotion(
        self,
        name,
        promo_type,
        value,
        min_quantity,
        buy_quantity,
        apply_to,
        apply_to_id,
        start_date,
        end_date,
        funding_source="company",
        supplier_id=None,
        promotion_subtype=None,
        second_item_discount_percent=0,
        bundle_product_id=None,
        bundle_price=0,
        supplier_support_type="claim_per_unit",
        supplier_support_value=0,
        minimum_margin_percent=5,
    ) -> int:
        self._execute(
            """
            INSERT INTO promotions (name, promo_type, value, min_quantity, buy_quantity,
                apply_to, apply_to_id, start_date, end_date, funding_source, supplier_id, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        """,
            (
                name,
                promo_type,
                value,
                min_quantity,
                buy_quantity,
                apply_to,
                apply_to_id,
                start_date,
                end_date,
                funding_source,
                supplier_id,
            ),
        )
        promo_id = self._last_id
        fields = {}
        optional_values = {
            "promotion_subtype": promotion_subtype,
            "second_item_discount_percent": second_item_discount_percent,
            "bundle_product_id": bundle_product_id,
            "bundle_price": bundle_price,
            "supplier_support_type": supplier_support_type,
            "supplier_support_value": supplier_support_value,
            "minimum_margin_percent": minimum_margin_percent,
        }
        promotion_columns = self._columns("promotions")
        for key, value in optional_values.items():
            if key in promotion_columns:
                fields[key] = value
        if fields:
            self.update_promotion_record(promo_id, fields)
        return promo_id

    def update_promotion_record(self, promo_id, fields: Dict) -> None:
        sets = ", ".join([f"{key} = %s" for key in fields.keys()])
        vals = list(fields.values()) + [promo_id]
        self._execute(f"UPDATE promotions SET {sets} WHERE id = %s", tuple(vals))

    def toggle_promotion_active(self, promo_id: int) -> None:
        self._execute(
            "UPDATE promotions SET is_active = NOT is_active WHERE id = %s", (promo_id,)
        )

    def delete_promotion_record(self, promo_id: int) -> None:
        self._execute("DELETE FROM promotions WHERE id = %s", (promo_id,))

    def get_all_stores(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT id, store_name
            FROM stores
            WHERE COALESCE(is_active, TRUE) = TRUE
              AND COALESCE(store_type, 'Branch') != 'GM'
            ORDER BY id
        """)

    def get_discount_companies(self, active_only: bool = False) -> List[Dict]:
        query = "SELECT id, name, discount_percent, is_active FROM discount_companies"
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name"
        return self._fetch_all(query)

    def get_discount_company_products(self, company_id: int) -> List[int]:
        rows = self._fetch_all(
            "SELECT product_id FROM discount_company_products WHERE company_id = %s",
            (company_id,),
        )
        return [int(row["product_id"]) for row in rows]

    def insert_discount_company(
        self, name: str, discount_percent: float, product_ids=None
    ) -> int:
        self._execute(
            "INSERT INTO discount_companies (name, discount_percent, is_active) VALUES (%s, %s, TRUE)",
            (name, discount_percent),
        )
        company_id = self._last_id
        self._replace_discount_company_products(company_id, product_ids or [])
        return company_id

    def update_discount_company(
        self, company_id: int, fields: Dict, product_ids=None
    ) -> None:
        self._execute(
            "UPDATE discount_companies SET name = %s, discount_percent = %s, is_active = %s WHERE id = %s",
            (
                fields["name"],
                fields["discount_percent"],
                fields["is_active"],
                company_id,
            ),
        )

        self._replace_discount_company_products(company_id, product_ids or [])

    def _replace_discount_company_products(self, company_id: int, product_ids):
        self._execute(
            "DELETE FROM discount_company_products WHERE company_id = %s",
            (company_id,),
        )
        for product_id in sorted({int(value) for value in product_ids if value}):
            self._execute(
                "INSERT INTO discount_company_products (company_id, product_id) VALUES (%s, %s)",
                (company_id, product_id),
            )

    def delete_discount_company(self, company_id: int) -> None:
        self._execute("DELETE FROM discount_companies WHERE id = %s", (company_id,))
