from typing import Optional, Protocol


class CheckoutRepositoryPort(Protocol):
    def get_customer_by_phone(self, phone: str):
        ...

    def check_credit_limit(self, customer_id: int, amount: float) -> tuple[bool, str]:
        ...

    def get_next_number(self) -> str:
        ...

    def get_or_create_customer(self, name: str = "", phone: str = "", address: str = "") -> Optional[int]:
        ...

    def validate_sale_stock(self, items: list[dict], store_id: int):
        ...

    def insert_invoice_header(
        self,
        invoice_number: str,
        store_id: int,
        cashier_id: int,
        customer_id: Optional[int] = None,
        customer_name: str = "",
        customer_phone: str = "",
        customer_address: str = "",
        drawer_id: Optional[int] = None,
        payment_method: str = "Cash",
        cash_amount: float = 0,
        card_amount: float = 0,
        total_amount: float = 0,
        paid_amount: float = 0,
        remaining_amount: float = 0,
        subtotal_amount: float = 0,
        tax_amount: float = 0,
        discount_company_id: Optional[int] = None,
        discount_company_name: Optional[str] = None,
        company_discount_amount: float = 0,
    ) -> int:
        ...

    def get_product_buy_price(self, product_id: int) -> float:
        ...

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
    ) -> None:
        ...

    def decrease_product_inventory(self, product_id: int, store_id: int, quantity: float) -> None:
        ...

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
        ...

    def save_sale_tax_details(self, invoice_id: int, tax_invoice_data: Optional[dict]) -> None:
        ...

    def record_supplier_promotion_claims(
        self,
        sale_invoice_id: int,
        invoice_number: str,
        user_id: int,
        claims: list[dict],
    ) -> None:
        ...

    def commit(self):
        ...

    def rollback(self):
        ...
