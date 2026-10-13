from typing import Dict, List, Protocol

from models.invoice import InvoiceItem


class OpenOrderRepositoryPort(Protocol):
    def get_open_orders(self, store_id: int, search_term: str = None) -> List[Dict]:
        ...

    def get_order_items(self, order_id: int) -> List[Dict]:
        ...

    def update_order_status_record(self, order_id: int, status: str) -> None:
        ...

    def commit(self):
        ...

    def rollback(self):
        ...


class OrderInventoryPort(Protocol):
    def get_stock(self, product_id: int, store_id: int) -> int:
        ...


class OrderCartPort(Protocol):
    items: List[InvoiceItem]
    active_store_id: int

    def clear(self):
        ...
