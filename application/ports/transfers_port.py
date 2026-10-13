from typing import Dict, List, Optional, Protocol


class TransfersRepositoryPort(Protocol):
    def get_stores(self) -> List[Dict]:
        ...

    def search_products(
        self,
        term: str,
        store_id: Optional[int] = None,
        limit: int = 25,
    ) -> List[Dict]:
        ...

    def get_transfers(
        self,
        store_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Dict]:
        ...

    def get_stock(self, product_id: int, store_id: int) -> int:
        ...

    def create_transfer_header(
        self,
        transfer_number: str,
        from_store_id: int,
        to_store_id: int,
        user_id: int,
        notes: str = "",
    ) -> int:
        ...

    def insert_transfer_item(self, transfer_id: int, product_id: int, quantity: int, notes: str = ""):
        ...

    def decrease_inventory(self, product_id: int, store_id: int, quantity: int):
        ...

    def increase_inventory(self, product_id: int, store_id: int, quantity: int):
        ...

    def get_transfer_for_receiving(self, transfer_id: int) -> Optional[Dict]:
        ...

    def get_transfer_for_cancellation(self, transfer_id: int) -> Optional[Dict]:
        ...

    def mark_transfer_received(self, transfer_id: int, user_id: int):
        ...

    def mark_transfer_cancelled(self, transfer_id: int):
        ...

    def commit(self):
        ...

    def rollback(self):
        ...
