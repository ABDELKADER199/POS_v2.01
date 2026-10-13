from typing import Protocol


class CashierCartRepositoryPort(Protocol):
    def get_stock(self, product_id: int, store_id: int) -> int:
        ...

    def calculate_promotions(self, items: list[dict]) -> tuple[list[dict], float]:
        ...
