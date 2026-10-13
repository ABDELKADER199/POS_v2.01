with open(r'd:\Python Desktop\POS_V2\repositories\purchases_repo.py', 'a', encoding='utf-8') as f:
    f.write('''
    def get_product_snapshot(self, product_id: int) -> dict:
        return self._fetch_one("SELECT * FROM products WHERE id = %s", (product_id,)) or {}

    def get_product_total_stock(self, product_id: int) -> int:
        res = self._fetch_one("SELECT COALESCE(SUM(quantity), 0) as total FROM product_inventory WHERE product_id = %s", (product_id,))
        return int(res["total"]) if res else 0

    def create_purchase_invoice_header(self, supplier_id, user_id, ref_number, subtotal, discount, tax, total, paid, remaining, payment_method, payment_status, store_id=None) -> dict:
        import uuid
        inv_num = f"PUR-{uuid.uuid4().hex[:8].upper()}"
        
        # Check columns dynamically
        cols = self.columns("purchase_invoices")
        
        c = ["invoice_number", "supplier_id", "created_by", "total_amount", "status"]
        v = [inv_num, supplier_id, user_id, total, "Completed"]
        
        if "ref_number" in cols: c.append("ref_number"); v.append(ref_number)
        if "paid_amount" in cols: c.append("paid_amount"); v.append(paid)
        if "remaining_amount" in cols: c.append("remaining_amount"); v.append(remaining)
        if "payment_method" in cols: c.append("payment_method"); v.append(payment_method)
        if "payment_status" in cols: c.append("payment_status"); v.append(payment_status)
        if "store_id" in cols and store_id: c.append("store_id"); v.append(store_id)
        
        ph = ", ".join(["%s"] * len(v))
        self._execute(f"INSERT INTO purchase_invoices ({', '.join(c)}) VALUES ({ph})", tuple(v))
        
        inv_id = self._last_id
        return {"id": inv_id, "invoice_number": inv_num}

    def add_inventory_quantity(self, product_id: int, store_id: int, quantity: int):
        existing = self._fetch_one("SELECT id, quantity FROM product_inventory WHERE product_id = %s AND store_id = %s", (product_id, store_id))
        if existing:
            self._execute("UPDATE product_inventory SET quantity = quantity + %s WHERE id = %s", (quantity, existing["id"]))
        else:
            self._execute("INSERT INTO product_inventory (product_id, store_id, quantity) VALUES (%s, %s, %s)", (product_id, store_id, quantity))

    def update_product_after_purchase(self, product_id: int, new_cost: float, new_price: float, supplier_id: int = None):
        self._execute("UPDATE products SET cost_price = %s, buy_price = %s, last_purchase_date = CURRENT_TIMESTAMP WHERE id = %s", (new_cost, new_price, product_id))
        if supplier_id:
            cols = self.columns("products")
            if "supplier_id" in cols:
                self._execute("UPDATE products SET supplier_id = %s WHERE id = %s", (supplier_id, product_id))

    def increase_supplier_balance(self, supplier_id: int, amount: float):
        self._execute("UPDATE suppliers SET opening_balance = COALESCE(opening_balance, 0) + %s WHERE id = %s", (amount, supplier_id))

    def record_supplier_payment(self, supplier_id, amount, payment_method, user_id, description, invoice_id=None, store_id=None):
        if amount <= 0 or "financial_ledger" not in self.existing_tables(): return
        
        cols = self.columns("financial_ledger")
        c = ["account_type", "account_id", "transaction_type", "amount", "description", "created_by"]
        v = ["Supplier", supplier_id, "Debit", amount, description, user_id]
        
        if "reference_type" in cols: c.append("reference_type"); v.append("Purchase")
        if "reference_id" in cols and invoice_id: c.append("reference_id"); v.append(invoice_id)
        if "store_id" in cols and store_id: c.append("store_id"); v.append(store_id)
        
        ph = ", ".join(["%s"] * len(v))
        self._execute(f"INSERT INTO financial_ledger ({', '.join(c)}) VALUES ({ph})", tuple(v))

''')
