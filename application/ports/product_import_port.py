from typing import Protocol

from models.product import Product


class ProductImportRepositoryPort(Protocol):
    def next_numeric_internal_code(self) -> str:
        ...

    def get_existing_codes_and_names(self) -> tuple[set, set]:
        ...

    def get_or_create_categories(self, category_names: list[str]) -> dict[str, int]:
        ...

    def bulk_create(
        self,
        products: list[Product],
        stock_by_code: dict[str, int],
        store_id: int = None,
        chunk_size: int = 1000,
    ) -> int:
        ...
