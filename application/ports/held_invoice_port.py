from typing import Dict, List, Protocol

from models.invoice import InvoiceItem


class HeldInvoiceRepositoryPort(Protocol):
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
        ...

    def insert_held_invoice_item(
        self,
        temp_invoice_id: int,
        product_id: int,
        quantity: int,
        unit_price: float,
        discount: float,
        total_price: float,
    ) -> None:
        ...

    def get_held_invoices(self, store_id: int, search_term: str = None) -> List[Dict]:
        ...

    def get_held_invoice_items(self, temp_invoice_id: int) -> List[Dict]:
        ...

    def delete_held_invoice_record(self, temp_invoice_id: int) -> None:
        ...

    def commit(self):
        ...

    def rollback(self):
        ...


class HeldInvoiceCartPort(Protocol):
    items: List[InvoiceItem]

    def clear(self):
        ...
