from typing import Dict, List, Optional, Protocol


class DrawerPort(Protocol):
    def get_store_open_drawer(self, store_id: int) -> Optional[Dict]:
        ...

    def get_any_open_drawer(self) -> Optional[Dict]:
        ...

    def get_operational_stores(self) -> List[Dict]:
        ...

    def get_drawer_status(self, user_id: int) -> Optional[Dict]:
        ...

    def insert_open_drawer(self, store_id: int, user_id: int, opening_balance: float) -> int:
        ...

    def mark_drawer_closed(self, drawer_id: int, closing_balance: float) -> None:
        ...

    def replace_closing_details(self, drawer_id: int, denomination_details: dict) -> None:
        ...

    def commit(self):
        ...

    def rollback(self):
        ...

    def get_drawer_summary(self, drawer_id: int) -> Optional[Dict]:
        ...

    def get_open_drawer_summary(self, drawer_id: int) -> Optional[Dict]:
        ...

    def get_closed_drawers_history(
        self,
        store_id: int,
        date_from: str = None,
        date_to: str = None,
    ) -> List[Dict]:
        ...

    def get_last_closed_drawer_id(self, store_id: int, user_id: int) -> Optional[int]:
        ...
