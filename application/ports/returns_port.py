from typing import Dict, List, Optional, Protocol


class ReturnsRepositoryPort(Protocol):
    def get_invoice_by_number(self, invoice_number: str) -> Optional[Dict]:
        ...

    def get_invoice_items(self, invoice_id: int) -> List[Dict]:
        ...

    def commit(self):
        ...

    def rollback(self):
        ...

    def get_invoice_for_return(self, invoice_id: int) -> Optional[Dict]:
        ...

    def create_return_header(self, return_number: str, invoice_id: int, store_id: int,
                             user_id: int, total_return: float, reason: str,
                             drawer_id: int = None) -> int:
        ...

    def insert_return_item(self, return_id: int, item: Dict):
        ...

    def add_inventory_quantity(self, product_id: int, store_id: int, quantity: int):
        ...

    def record_cash_refund(self, store_id: int, amount: float, return_id: int,
                           invoice_number: str, return_number: str, user_id: int):
        ...

    def reduce_customer_balance(self, customer_id: int, amount: float):
        ...

    def record_customer_return_ledger(self, customer_id: int, amount: float,
                                      return_id: int, invoice_number: str,
                                      user_id: int):
        ...

    def get_returns_history(
        self,
        store_id: int = None,
        start_date: str = None,
        end_date: str = None,
        return_number: str = None,
    ) -> List[Dict]:
        ...

    def get_drawer_status(self, user_id: int) -> Optional[Dict]:
        ...

    def get_store_open_drawer(self, store_id: int) -> Optional[Dict]:
        ...
