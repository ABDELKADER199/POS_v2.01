from typing import Dict, List, Optional, Protocol


class CallCenterRepositoryPort(Protocol):
    def get_all_stores(self) -> List[Dict]:
        ...

    def search_products(self, term: str) -> List[Dict]:
        ...

    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        ...

    def update_customer(self, customer_id: int, name: str = "", address: str = ""):
        ...

    def create_customer(self, name: str, phone: str = "", address: str = "") -> int:
        ...

    def create_order_header(
        self,
        order_number: str,
        customer_name: str,
        phone: str,
        address: str,
        customer_city: Optional[str],
        customer_id: Optional[int],
        source_store_id: int,
        destination_store_id: int,
        user_id: int,
        total: float,
    ) -> int:
        ...

    def insert_order_item(self, order_id: int, product_id: int, quantity: float, price: float):
        ...

    def get_orders(
        self,
        statuses: list[str] = None,
        store_id: int = None,
        search: str = None,
    ) -> List[Dict]:
        ...

    def update_order_status(self, order_id: int, status: str):
        ...

    def get_delivery_agents(self, store_id: int) -> List[Dict]:
        ...

    def assign_delivery_agent(self, order_id: int, agent_id: int):
        ...

    def update_delivery_status(self, order_id: int, status: str, notes: str = None):
        ...

    def commit(self):
        ...

    def rollback(self):
        ...

    def get_order_details(self, order_id: int) -> List[Dict]:
        ...

    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        ...
