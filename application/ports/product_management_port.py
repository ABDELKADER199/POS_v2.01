from typing import Dict, List, Optional, Protocol

from models.product import Product


class ProductManagementPort(Protocol):
    def search(
        self,
        term: str,
        store_id: int = None,
        category_id: int = None,
        supplier_id: int = None,
        limit: int = 50,
        offset: int = 0,
        column_filters: Dict = None,
    ) -> List[Product]:
        ...

    def count(
        self,
        term: str = None,
        category_id: int = None,
        supplier_id: int = None,
        column_filters: Dict = None,
    ) -> int:
        ...

    def get_by_id(self, product_id: int) -> Optional[Product]:
        ...

    def insert_product(self, product: Product, store_id: int = None) -> int:
        ...

    def set_initial_stock(self, product_id: int, store_id: int, initial_stock: int):
        ...

    def update_product_record(self, product: Product):
        ...

    def soft_delete_product(self, product_id: int):
        ...

    def commit(self):
        ...

    def rollback(self):
        ...

    def save_product_image(self, source_path: str, product_code: str) -> str:
        ...

    def update_zero_costs_from_margin(self, margin_percent: float = 25.0) -> int:
        ...

    def get_suppliers(self, active_only: bool = True) -> List[Dict]:
        ...


class ProductCategoryPort(Protocol):
    def get_categories(self) -> List[Dict]:
        ...

    def insert_category(self, category_name: str) -> int:
        ...

    def update_category_record(self, category_id: int, category_name: str) -> None:
        ...

    def soft_delete_category(self, category_id: int) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


class ProductInventoryPort(Protocol):
    def get_all_stock(
        self,
        store_id: int = None,
        low_stock_only: bool = False,
        limit: int = 100,
        offset: int = 0,
        search: str = "",
        filters: dict = None,
    ) -> List[Dict]:
        ...

    def count_all_stock(
        self,
        store_id: int = None,
        low_stock_only: bool = False,
        search: str = "",
        filters: dict = None,
    ) -> int:
        ...

    def set_stock(self, product_id: int, store_id: int, quantity: int) -> None:
        ...

    def commit(self):
        ...

    def rollback(self):
        ...
