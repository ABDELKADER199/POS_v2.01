from typing import List, Optional, Protocol

from models.product import Product


class ProductLookupPort(Protocol):
    def get_by_code(self, product_code: str) -> Optional[Product]:
        ...

    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        ...

    def search(self, term: str, limit: int = 50, offset: int = 0) -> List[Product]:
        ...
