from typing import List, Optional

from application.ports.product_lookup_port import ProductLookupPort
from models.product import Product


class ProductLookupUseCase:
    def __init__(self, product_repo: ProductLookupPort):
        self.product_repo = product_repo

    def find_sellable_product(self, search_term: str) -> Optional[Product]:
        normalized_term = str(search_term or "").strip()
        if not normalized_term:
            return None

        product = self.product_repo.get_by_code(normalized_term)
        if product:
            return product
        return self.product_repo.get_by_barcode(normalized_term)

    def search_sellable_products(self, term: str, limit: int = 20) -> List[Product]:
        normalized_term = str(term or "").strip()
        if not normalized_term:
            return []
        return self.product_repo.search(normalized_term, limit=limit)
