import re

with open("repositories/purchases_repo.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix increase_supplier_balance
content = content.replace(
    'self._execute("UPDATE suppliers SET opening_balance = COALESCE(opening_balance, 0) + %s WHERE id = %s", (amount, supplier_id))',
    'self._execute("UPDATE suppliers SET current_balance = COALESCE(current_balance, 0) + %s WHERE id = %s", (amount, supplier_id))'
)

# Replace record_supplier_purchase_debt entirely
import_debt = """    def record_supplier_purchase_debt(self, supplier_id: int, user_id: int,
                                       invoice_id: int, amount: float,
                                       description: str, store_id: int = None):
        if amount <= 0 or "financial_ledger" not in self.existing_tables():
            return
        
        # Calculate balance after
        balance = self._fetch_one("SELECT current_balance FROM suppliers WHERE id=%s", (supplier_id,))
        balance_after = balance["current_balance"] if balance else 0

        columns = ["account_type", "account_id", "transaction_type", "amount", "reference_type", "reference_id", "description", "created_by", "balance_after"]
        values = ["Supplier", supplier_id, "Credit", amount, "Purchase", invoice_id, description, user_id, balance_after]
        
        if store_id is not None:
            cols = self.columns("financial_ledger")
            if "store_id" in cols:
                columns.insert(1, "store_id")
                values.insert(1, store_id)
        
        placeholders = ", ".join(["%s"] * len(values))
        query = f"INSERT INTO financial_ledger ({', '.join(columns)}) VALUES ({placeholders})"
        self._execute(query, tuple(values))
"""
content = re.sub(
    r'    def record_supplier_purchase_debt\(.*?self\._execute\(query, tuple\(values\)\)',
    import_debt.strip('\n'),
    content,
    flags=re.DOTALL
)

# Add missing methods at the end
missing = """

    def decrease_supplier_balance(self, supplier_id: int, amount: float):
        self._execute("UPDATE suppliers SET current_balance = COALESCE(current_balance, 0) - %s WHERE id = %s", (amount, supplier_id))

    def update_supplier(self, supplier_id: int, name: str, phone: str, address: str, tax_number: str):
        self._execute("UPDATE suppliers SET name=%s, phone=%s, address=%s, tax_number=%s WHERE id=%s", (name, phone, address, tax_number, supplier_id))
        return True

    def create_purchase_return_header(self, purchase_invoice_id, supplier_id, store_id, user_id, total_amount, settlement_method, reason):
        import uuid
        ret_num = f"PRT-{uuid.uuid4().hex[:8].upper()}"
        self._execute('''
            INSERT INTO purchase_returns (return_number, purchase_invoice_id, supplier_id, store_id, created_by, total_amount, settlement_method, reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (ret_num, purchase_invoice_id, supplier_id, store_id, user_id, total_amount, settlement_method, reason))
        return {"id": self._last_id, "return_number": ret_num}

    def get_purchase_invoice_details(self, search_term: str):
        invoice = self._fetch_one("SELECT * FROM purchase_invoices WHERE invoice_number = %s", (search_term,))
        if not invoice: return None
        items = self._fetch_all("SELECT * FROM purchase_items WHERE purchase_invoice_id = %s", (invoice["id"],))
        return {"invoice": invoice, "items": items}

    def get_purchase_item_remaining_quantity(self, invoice_id: int, product_id: int):
        item = self._fetch_one("SELECT quantity FROM purchase_items WHERE purchase_invoice_id=%s AND product_id=%s", (invoice_id, product_id))
        return item["quantity"] if item else 0

    def decrease_inventory_quantity(self, product_id: int, store_id: int, quantity):
        self._execute("UPDATE product_inventory SET quantity_in_stock = quantity_in_stock - %s WHERE product_id=%s AND store_id=%s", (quantity, product_id, store_id))

    def record_supplier_purchase_return_credit(self, supplier_id, user_id, return_id, amount, description):
        if "financial_ledger" not in self.existing_tables(): return
        balance = self._fetch_one("SELECT current_balance FROM suppliers WHERE id=%s", (supplier_id,))
        balance_after = balance["current_balance"] if balance else 0
        cols = ["account_type", "account_id", "transaction_type", "amount", "reference_type", "reference_id", "description", "created_by", "balance_after"]
        vals = ["Supplier", supplier_id, "Credit", amount, "Return", return_id, description, user_id, balance_after]
        pl = ", ".join(["%s"] * len(vals))
        self._execute(f"INSERT INTO financial_ledger ({', '.join(cols)}) VALUES ({pl})", tuple(vals))

    def update_purchase_invoice_payment_state(self, invoice_id, payment_status, paid_amount, remaining_amount):
        self._execute("UPDATE purchase_invoices SET payment_status=%s, paid_amount=%s, remaining_amount=%s WHERE id=%s", (payment_status, paid_amount, remaining_amount, invoice_id))

    def get_purchase_invoice_for_payment(self, invoice_id: int):
        return self._fetch_one("SELECT id, payment_method, payment_status, total_amount, paid_amount, remaining_amount FROM purchase_invoices WHERE id=%s", (invoice_id,))

    def allocate_supplier_payment(self, supplier_id: int, amount: float, store_id: int, user_id: int):
        pass

    def reconcile_supplier_open_invoices(self, supplier_id: int, amount: float):
        pass
"""

with open("repositories/purchases_repo.py", "w", encoding="utf-8") as f:
    f.write(content + missing)

