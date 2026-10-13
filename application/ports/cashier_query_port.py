from typing import Dict, Optional, Protocol


class SettingsQueryPort(Protocol):
    def get_all(self) -> Dict:
        ...


class CustomerQueryPort(Protocol):
    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        ...


class StockQueryPort(Protocol):
    def get_stock(self, product_id: int, store_id: int) -> int:
        ...


class CrossBranchStockQueryPort(Protocol):
    def get_product_cross_branch_stock(self, search_term: str) -> Dict:
        ...
