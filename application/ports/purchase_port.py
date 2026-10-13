from typing import Dict, List, Optional, Protocol


class PurchaseRepositoryPort(Protocol):
    def ensure_purchase_columns(self):
        ...

    def get_all_suppliers(self) -> List[Dict]:
        ...

    def get_all_stores(self) -> List[Dict]:
        ...

    def add_supplier(
        self,
        name: str,
        phone: str,
        address: str,
        tax_number: str,
        opening_balance: float,
    ) -> bool:
        ...

    def update_supplier(
        self,
        supplier_id: int,
        name: str,
        phone: str,
        address: str,
        tax_number: str,
    ) -> bool:
        ...

    def soft_delete_supplier(self, supplier_id: int) -> bool:
        ...

    def search_product(self, term: str) -> Optional[Dict]:
        ...

    def get_purchase_history(self, page: int = 1, per_page: int = 100) -> List[Dict]:
        ...

    def get_purchase_invoice_details(self, search_term: str) -> Optional[Dict]:
        ...

    def get_supplier(self, supplier_id: int) -> Optional[Dict]:
        ...

    def get_product_snapshot(self, product_id: int) -> Optional[Dict]:
        ...

    def get_product_total_stock(self, product_id: int) -> float:
        ...

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
    ) -> Dict:
        ...

    def insert_purchase_item(
        self,
        invoice_id: int,
        product_id: int,
        quantity: int,
        unit_cost: float,
        expiry_date: Optional[str] = None,
    ):
        ...

    def add_inventory_quantity(self, product_id: int, store_id: int, quantity: int):
        ...

    def decrease_inventory_quantity(self, product_id: int, store_id: int, quantity: int):
        ...

    def get_inventory_quantity(self, product_id: int, store_id: int) -> int:
        ...

    def get_purchase_item_remaining_quantity(self, invoice_id: int, product_id: int) -> int:
        ...

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
        ...

    def insert_purchase_return_item(
        self,
        return_id: int,
        product_id: int,
        quantity: int,
        unit_cost: float,
    ):
        ...

    def record_supplier_purchase_return_credit(
        self,
        supplier_id: int,
        user_id: int,
        return_id: int,
        amount: float,
        description: str,
    ):
        ...

    def record_purchase_return_cash_refund(
        self,
        supplier_id: int,
        store_id: int,
        user_id: int,
        return_id: int,
        amount: float,
        description: str,
    ):
        ...

    def update_product_after_purchase(
        self,
        product_id: int,
        new_cost: float,
        buy_price: Optional[float] = None,
        sell_price: Optional[float] = None,
        supplier_id: Optional[int] = None,
        supplier_name: str = "",
    ):
        ...

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
        ...

    def increase_supplier_balance(self, supplier_id: int, amount: float):
        ...

    def record_supplier_purchase_debt(
        self,
        supplier_id: int,
        store_id: int,
        user_id: int,
        invoice_id: int,
        amount: float,
        description: str,
    ):
        ...

    def decrease_supplier_balance(self, supplier_id: int, amount: float):
        ...

    def allocate_supplier_payment(self, supplier_id: int, amount: float):
        ...

    def record_supplier_payment(
        self,
        supplier_id: int,
        store_id: int,
        user_id: int,
        invoice_id: Optional[int],
        amount: float,
        payment_method: str,
        description: str,
        record_ledger: bool,
    ):
        ...

    def get_purchase_invoice_for_payment(self, invoice_id: int) -> Optional[Dict]:
        ...

    def update_purchase_invoice_payment_state(
        self,
        invoice_id: int,
        paid_amount: float,
        remaining_amount: float,
        payment_status: str,
        payment_method: str,
    ):
        ...

    def reconcile_purchase_return_credits(self, invoice_id: Optional[int] = None):
        ...

    def sync_supplier_balance_from_open_invoices(self, supplier_id: Optional[int] = None):
        ...

    def commit(self):
        ...

    def rollback(self):
        ...
