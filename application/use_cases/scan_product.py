from dataclasses import dataclass, field
from typing import List, Optional

from application.use_cases.cashier_cart import CashierCartUseCase
from application.use_cases.product_lookup import ProductLookupUseCase
from models.invoice import InvoiceItem
from models.product import Product


@dataclass
class ScanProductResult:
    added: bool = False
    product: Optional[Product] = None
    items: List[InvoiceItem] = field(default_factory=list)
    search_results: List[Product] = field(default_factory=list)


class ScanProductUseCase:
    def __init__(self, product_lookup: ProductLookupUseCase, cart: CashierCartUseCase):
        self.product_lookup = product_lookup
        self.cart = cart

    def execute(self, search_term: str, quantity: float = 1.0) -> ScanProductResult:
        product = self.product_lookup.find_sellable_product(search_term)
        if product:
            items = self.cart.add_item(product, quantity)
            return ScanProductResult(added=True, product=product, items=items)

        search_results = self.product_lookup.search_sellable_products(search_term)
        return ScanProductResult(search_results=search_results)
