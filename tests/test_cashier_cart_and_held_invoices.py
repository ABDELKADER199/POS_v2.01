import pytest

from application.use_cases.cashier_cart import CashierCartUseCase
from application.use_cases.cashier_queries import (
    FindCustomerByPhoneUseCase,
    GetCrossBranchStockUseCase,
    GetSettingsUseCase,
    GetStockUseCase,
)
from application.use_cases.held_invoices import (
    DeleteHeldInvoiceUseCase,
    ListHeldInvoicesUseCase,
    ResumeHeldInvoiceUseCase,
    SaveHeldInvoiceUseCase,
)
from application.use_cases.product_lookup import ProductLookupUseCase
from application.use_cases.scan_product import ScanProductUseCase
from models.invoice import InvoiceItem
from models.product import Product


class FakeCashierRepository:
    def __init__(self):
        self.calls = []
        self.stock = 10
        self.promos = []
        self.promo_discount = 0.0
        self.products_by_code = {}
        self.products_by_barcode = {}
        self.search_results = []
        self.customer = {"id": 1, "name": "عميل"}
        self.settings = {"store_name": "HyperPOS"}
        self.cross_branch_stock = {"product": {"id": 1}, "stocks": []}

    def get_stock(self, product_id, store_id):
        self.calls.append(("get_stock", product_id, store_id))
        return self.stock

    def calculate_promotions(self, items):
        self.calls.append(("calculate_promotions", items))
        return self.promos, self.promo_discount

    def get_by_code(self, code):
        self.calls.append(("get_by_code", code))
        return self.products_by_code.get(code)

    def get_by_barcode(self, barcode):
        self.calls.append(("get_by_barcode", barcode))
        return self.products_by_barcode.get(barcode)

    def search(self, term, limit=20):
        self.calls.append(("search", term, limit))
        return self.search_results

    def get_customer_by_phone(self, phone):
        self.calls.append(("get_customer_by_phone", phone))
        return self.customer

    def get_all(self):
        self.calls.append(("get_all",))
        return self.settings

    def get_product_cross_branch_stock(self, search_term):
        self.calls.append(("get_product_cross_branch_stock", search_term))
        return self.cross_branch_stock


class FakeHeldInvoiceRepository:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.temp_id = 88
        self.raise_on_insert = None
        self.held_rows = [{"id": 88, "temp_invoice_code": "HOLD-1"}]
        self.held_items = [
            {
                "product_id": 10,
                "product_code": "P10",
                "product_name": "منتج محفوظ",
                "quantity": 2,
                "unit_price": 30,
                "discount": 5,
                "tax_percent": 14,
            }
        ]

    def insert_held_invoice_header(
        self,
        temp_invoice_code,
        store_id,
        cashier_id,
        customer_name,
        customer_phone,
        customer_address,
        total_amount,
    ):
        self.calls.append(
            (
                "insert_held_invoice_header",
                temp_invoice_code,
                store_id,
                cashier_id,
                customer_name,
                customer_phone,
                customer_address,
                total_amount,
            )
        )
        if self.raise_on_insert:
            raise self.raise_on_insert
        return self.temp_id

    def insert_held_invoice_item(
        self, temp_invoice_id, product_id, quantity, unit_price, discount, total_price
    ):
        self.calls.append(
            (
                "insert_held_invoice_item",
                temp_invoice_id,
                product_id,
                quantity,
                unit_price,
                discount,
                total_price,
            )
        )

    def get_held_invoices(self, store_id, search_term=None):
        self.calls.append(("get_held_invoices", store_id, search_term))
        return self.held_rows

    def get_held_invoice_items(self, temp_invoice_id):
        self.calls.append(("get_held_invoice_items", temp_invoice_id))
        return self.held_items if temp_invoice_id == self.temp_id else []

    def delete_held_invoice_record(self, temp_invoice_id):
        self.calls.append(("delete_held_invoice_record", temp_invoice_id))

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


class FakeCart:
    def __init__(self):
        self.items = []
        self.cleared = False

    def clear(self):
        self.cleared = True
        self.items.clear()


def product(**kwargs):
    data = {
        "id": 10,
        "product_code": "P10",
        "product_name": "منتج",
        "sell_price": 50.0,
        "tax_percent": 14.0,
        "import_status": "ready",
    }
    data.update(kwargs)
    return Product(**data)


def call_names(obj):
    return [call[0] for call in obj.calls]


def test_cart_adds_new_item_merges_quantity_and_checks_stock():
    repo = FakeCashierRepository()
    cart = CashierCartUseCase(repo, repo)
    cart.set_store(3)

    cart.add_item(product(), quantity=2)
    cart.add_item(product(), quantity=3)

    assert len(cart.items) == 1
    assert cart.items[0].quantity == 5
    assert ("get_stock", 10, 3) in repo.calls


def test_cart_rejects_unpriced_or_needs_pricing_or_insufficient_stock():
    repo = FakeCashierRepository()
    cart = CashierCartUseCase(repo, repo)

    with pytest.raises(ValueError, match="تحديد سعر البيع"):
        cart.add_item(product(sell_price=0), 1)

    with pytest.raises(ValueError, match="تحديد سعر البيع"):
        cart.add_item(product(import_status="needs_pricing"), 1)

    repo.stock = 1
    with pytest.raises(ValueError, match="الكمية غير متاحة"):
        cart.add_item(product(), 2)


def test_cart_updates_removes_clears_and_calculates_totals_with_promotions():
    repo = FakeCashierRepository()
    repo.promos = [{"product_id": 10, "discount_amount": 10}]
    repo.promo_discount = 10
    cart = CashierCartUseCase(repo, repo)
    cart.add_item(product(), 2)
    cart.manual_discount = 5

    totals = cart.calculate_totals()

    assert totals["gross_total"] == 100
    assert totals["manual_discount"] == 5
    assert totals["promo_discount"] == 10
    assert totals["total"] == 85
    assert totals["tax_total"] == 10.44
    assert totals["subtotal"] == 74.56
    assert cart.promo_discount_for_product(10) == 10

    cart.update_item_quantity(0, 1)
    assert cart.items[0].quantity == 1
    cart.update_item_quantity(0, 0)
    assert cart.items == []

    cart.add_item(product(), 1)
    cart.clear()
    assert cart.items == []
    assert cart.manual_discount == 0
    assert cart.promo_discount == 0
    assert cart.applied_promos == []


def test_cart_separates_supplier_funded_promotion_from_company_discount():
    repo = FakeCashierRepository()
    repo.promos = [
        {
            "product_id": 10,
            "discount_amount": 11,
            "company_discount_amount": 0,
            "funding_source": "supplier",
            "supplier_id": 7,
            "promo_id": 5,
            "quantity": 1,
            "promo_name": "عرض مورد",
        }
    ]
    repo.promo_discount = 11
    cart = CashierCartUseCase(repo, repo)
    cart.add_item(product(), 1)
    cart.calculate_totals()

    assert cart.promo_discount_for_product(10) == 11
    assert cart.company_promo_discount_for_product(10) == 0
    assert cart.supplier_promotion_claims() == [
        {
            "promotion_id": 5,
            "supplier_id": 7,
            "product_id": 10,
            "quantity": 1,
            "amount": 11,
            "description": "عرض مورد",
        }
    ]


def test_company_discount_selection_reduces_total_and_tax_base():
    repo = FakeCashierRepository()
    cart = CashierCartUseCase(repo, repo)
    cart.set_store(1)
    cart.add_item(
        Product(
            id=10,
            product_code="P",
            product_name="منتج",
            sell_price=100,
            tax_percent=14,
        )
    )
    cart.set_discount_company({"id": 1, "name": "إكسكلوسف", "discount_percent": 10})

    totals = cart.calculate_totals()

    assert totals["company_discount"] == 10.0
    assert totals["total"] == 90.0
    assert totals["tax_total"] == round(90 - (90 / 1.14), 2)


def test_company_discount_applies_only_to_selected_products():
    repo = FakeCashierRepository()
    cart = CashierCartUseCase(repo, repo)
    cart.set_store(1)
    cart.add_item(product(id=10, sell_price=100), 1)
    cart.add_item(product(id=11, sell_price=50), 1)
    cart.set_discount_company(
        {"id": 1, "name": "إكسكلوسف", "discount_percent": 10, "product_ids": [10]}
    )

    totals = cart.calculate_totals()

    assert totals["company_discount"] == 10.0
    assert totals["total"] == 140.0


def test_scan_product_adds_direct_match_or_returns_search_results():
    repo = FakeCashierRepository()
    repo.products_by_code["P10"] = product()
    lookup = ProductLookupUseCase(repo)
    cart = CashierCartUseCase(repo, repo)
    scanner = ScanProductUseCase(lookup, cart)

    result = scanner.execute("P10", quantity=2)
    assert result.added is True
    assert result.product.id == 10
    assert result.items[0].quantity == 2

    repo.products_by_code.clear()
    repo.search_results = [product(id=11, product_code="P11")]
    result = scanner.execute("منتج")
    assert result.added is False
    assert len(result.search_results) == 1


def test_cashier_query_use_cases_delegate_and_normalize_empty_values():
    repo = FakeCashierRepository()

    assert GetSettingsUseCase(repo).execute() == {"store_name": "HyperPOS"}
    assert FindCustomerByPhoneUseCase(repo).execute("") is None
    assert FindCustomerByPhoneUseCase(repo).execute(" 010 ") == {
        "id": 1,
        "name": "عميل",
    }
    assert GetStockUseCase(repo, active_store_provider=lambda: 5).execute(10) == 10
    assert ("get_stock", 10, 5) in repo.calls
    assert GetCrossBranchStockUseCase(repo).execute("") == {}
    assert GetCrossBranchStockUseCase(repo).execute(" P10 ") == repo.cross_branch_stock


def test_save_held_invoice_persists_header_items_and_commits():
    repo = FakeHeldInvoiceRepository()
    cart = FakeCart()
    cart.items = [
        InvoiceItem(
            product_id=10,
            product_code="P10",
            product_name="منتج",
            quantity=2,
            unit_price=30,
            discount=5,
        )
    ]
    use_case = SaveHeldInvoiceUseCase(repo, cart)

    assert use_case.execute(1, 2, "عميل", "010", "عنوان") is True
    header = next(
        call for call in repo.calls if call[0] == "insert_held_invoice_header"
    )
    assert header[2] == 1
    assert header[3] == 2
    assert header[4] == "عميل"
    assert header[7] == 60
    assert ("insert_held_invoice_item", 88, 10, 2, 30.0, 5.0, 55.0) in repo.calls
    assert repo.committed is True
    assert repo.rolled_back is False


def test_save_held_invoice_empty_cart_or_repository_failure():
    repo = FakeHeldInvoiceRepository()
    cart = FakeCart()
    use_case = SaveHeldInvoiceUseCase(repo, cart)

    assert use_case.execute(1, 2) is False
    assert repo.calls == []

    cart.items = [InvoiceItem(product_id=10, quantity=1, unit_price=30)]
    repo.raise_on_insert = RuntimeError("insert failed")
    assert use_case.execute(1, 2) is False
    assert repo.committed is False
    assert repo.rolled_back is True


def test_list_delete_and_resume_held_invoices():
    repo = FakeHeldInvoiceRepository()
    cart = FakeCart()

    assert ListHeldInvoicesUseCase(repo).execute(1, "عميل") == repo.held_rows
    assert ("get_held_invoices", 1, "عميل") in repo.calls

    assert DeleteHeldInvoiceUseCase(repo).execute(88) is True
    assert ("delete_held_invoice_record", 88) in repo.calls

    repo.committed = False
    assert ResumeHeldInvoiceUseCase(repo, cart).execute(88) is True
    assert cart.cleared is True
    assert len(cart.items) == 1
    assert cart.items[0].product_id == 10
    assert cart.items[0].quantity == 2
    assert repo.committed is False

    assert ResumeHeldInvoiceUseCase(repo, cart).execute(999) is False
