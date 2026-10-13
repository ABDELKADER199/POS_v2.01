import pytest

from application.use_cases.product_lookup import ProductLookupUseCase
from application.use_cases.scan_product import ScanProductUseCase
from models.invoice import InvoiceItem
from models.product import Product


def make_product(
    product_id=10,
    code="P10",
    barcode="B10",
    name="منتج",
    sell_price=25,
    import_status="ready",
):
    return Product(
        id=product_id,
        product_code=code,
        barcode=barcode,
        product_name=name,
        sell_price=sell_price,
        tax_percent=14,
        import_status=import_status,
    )


class FakeProductLookupRepository:
    def __init__(self):
        self.calls = []
        self.by_code = {}
        self.by_barcode = {}
        self.search_results = []

    def get_by_code(self, product_code):
        self.calls.append(("get_by_code", product_code))
        return self.by_code.get(product_code)

    def get_by_barcode(self, barcode):
        self.calls.append(("get_by_barcode", barcode))
        return self.by_barcode.get(barcode)

    def search(self, term, limit=50, offset=0):
        self.calls.append(("search", term, limit, offset))
        return self.search_results


class FakeCart:
    def __init__(self):
        self.calls = []
        self.items = []
        self.raise_on_add = None

    def add_item(self, product, quantity=1):
        self.calls.append(("add_item", product.id, quantity))
        if self.raise_on_add:
            raise self.raise_on_add
        self.items.append(
            InvoiceItem(
                product_id=product.id,
                product_code=product.product_code,
                product_name=product.product_name,
                quantity=quantity,
                unit_price=product.sell_price,
            )
        )
        return self.items


def test_product_lookup_returns_none_for_empty_search_without_repository_call():
    repo = FakeProductLookupRepository()

    assert ProductLookupUseCase(repo).find_sellable_product("   ") is None

    assert repo.calls == []


def test_product_lookup_prefers_product_code_before_barcode():
    repo = FakeProductLookupRepository()
    code_product = make_product(product_id=1, code="123")
    barcode_product = make_product(product_id=2, barcode="123")
    repo.by_code["123"] = code_product
    repo.by_barcode["123"] = barcode_product

    result = ProductLookupUseCase(repo).find_sellable_product(" 123 ")

    assert result is code_product
    assert repo.calls == [("get_by_code", "123")]


def test_product_lookup_falls_back_to_barcode_when_code_not_found():
    repo = FakeProductLookupRepository()
    barcode_product = make_product(product_id=2, barcode="622")
    repo.by_barcode["622"] = barcode_product

    result = ProductLookupUseCase(repo).find_sellable_product(" 622 ")

    assert result is barcode_product
    assert repo.calls == [("get_by_code", "622"), ("get_by_barcode", "622")]


def test_product_lookup_search_trims_term_and_passes_limit():
    repo = FakeProductLookupRepository()
    repo.search_results = [make_product(product_id=1)]

    result = ProductLookupUseCase(repo).search_sellable_products(" منتج ", limit=7)

    assert result == repo.search_results
    assert repo.calls == [("search", "منتج", 7, 0)]


def test_product_lookup_search_returns_empty_for_blank_term():
    repo = FakeProductLookupRepository()

    assert ProductLookupUseCase(repo).search_sellable_products("  ") == []

    assert repo.calls == []


def test_scan_product_adds_direct_code_match_to_cart():
    repo = FakeProductLookupRepository()
    product = make_product(product_id=10, code="P10")
    repo.by_code["P10"] = product
    cart = FakeCart()

    result = ScanProductUseCase(ProductLookupUseCase(repo), cart).execute(" P10 ", quantity=3)

    assert result.added is True
    assert result.product is product
    assert result.items == cart.items
    assert result.search_results == []
    assert cart.calls == [("add_item", 10, 3)]


def test_scan_product_adds_direct_barcode_match_to_cart():
    repo = FakeProductLookupRepository()
    product = make_product(product_id=11, barcode="622")
    repo.by_barcode["622"] = product
    cart = FakeCart()

    result = ScanProductUseCase(ProductLookupUseCase(repo), cart).execute("622")

    assert result.added is True
    assert result.product is product
    assert cart.calls == [("add_item", 11, 1)]


def test_scan_product_returns_search_results_when_no_direct_match():
    repo = FakeProductLookupRepository()
    search_product = make_product(product_id=12, name="نتيجة")
    repo.search_results = [search_product]
    cart = FakeCart()

    result = ScanProductUseCase(ProductLookupUseCase(repo), cart).execute("نتيجة")

    assert result.added is False
    assert result.product is None
    assert result.items == []
    assert result.search_results == [search_product]
    assert cart.calls == []
    assert repo.calls == [
        ("get_by_code", "نتيجة"),
        ("get_by_barcode", "نتيجة"),
        ("search", "نتيجة", 20, 0),
    ]


def test_scan_product_propagates_cart_validation_errors():
    repo = FakeProductLookupRepository()
    product = make_product(product_id=13, code="P13", sell_price=0)
    repo.by_code["P13"] = product
    cart = FakeCart()
    cart.raise_on_add = ValueError("لا يمكن بيع المنتج قبل تحديد السعر")

    with pytest.raises(ValueError, match="تحديد السعر"):
        ScanProductUseCase(ProductLookupUseCase(repo), cart).execute("P13")

    assert cart.calls == [("add_item", 13, 1)]


def test_scan_product_blank_term_returns_empty_result_without_cart_changes():
    repo = FakeProductLookupRepository()
    cart = FakeCart()

    result = ScanProductUseCase(ProductLookupUseCase(repo), cart).execute(" ")

    assert result.added is False
    assert result.product is None
    assert result.items == []
    assert result.search_results == []
    assert repo.calls == []
    assert cart.calls == []
