import pytest

from application.use_cases.checkout_sale import CheckoutSaleUseCase
from models.invoice import InvoiceItem, TaxInvoiceDetails


class FakeCheckoutRepository:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.customer = None
        self.credit_limit_result = (True, "")
        self.raise_on_stock_validation = None
        self.buy_price = 12.5

    def get_customer_by_phone(self, phone):
        self.calls.append(("get_customer_by_phone", phone))
        return self.customer

    def check_credit_limit(self, customer_id, amount):
        self.calls.append(("check_credit_limit", customer_id, amount))
        return self.credit_limit_result

    def get_next_number(self):
        self.calls.append(("get_next_number",))
        return "1001"

    def get_or_create_customer(self, name="", phone="", address=""):
        self.calls.append(("get_or_create_customer", name, phone, address))
        return 10 if name or phone else None

    def validate_sale_stock(self, items, store_id):
        self.calls.append(("validate_sale_stock", items, store_id))
        if self.raise_on_stock_validation:
            raise self.raise_on_stock_validation

    def insert_invoice_header(self, **kwargs):
        self.calls.append(("insert_invoice_header", kwargs))
        return 77

    def get_product_buy_price(self, product_id):
        self.calls.append(("get_product_buy_price", product_id))
        return self.buy_price

    def insert_sale_item(self, **kwargs):
        self.calls.append(("insert_sale_item", kwargs))

    def decrease_product_inventory(self, product_id, store_id, quantity):
        self.calls.append(("decrease_product_inventory", product_id, store_id, quantity))

    def apply_sale_financial_effects(self, **kwargs):
        self.calls.append(("apply_sale_financial_effects", kwargs))

    def record_supplier_promotion_claims(self, **kwargs):
        self.calls.append(("record_supplier_promotion_claims", kwargs))

    def save_sale_tax_details(self, invoice_id, tax_invoice_data):
        self.calls.append(("save_sale_tax_details", invoice_id, tax_invoice_data))

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def make_sale_use_case(
    repo,
    items=None,
    totals=None,
    tax_details=None,
    promo_discount=0,
    company_promo_discount=None,
    supplier_claims=None,
):
    return CheckoutSaleUseCase(
        invoice_repo=repo,
        totals_calculator=lambda: totals or {"total": 95.0, "subtotal": 83.33, "tax_total": 11.67},
        promo_discount_for_product=lambda product_id: promo_discount,
        current_items_provider=lambda: items if items is not None else [
            InvoiceItem(
                product_id=1,
                product_code="P1",
                product_name="منتج اختبار",
                quantity=2,
                unit_price=50,
                discount=5,
                tax_percent=14,
            )
        ],
        tax_invoice_provider=lambda: tax_details,
        company_promo_discount_for_product=(
            (lambda product_id: company_promo_discount)
            if company_promo_discount is not None
            else None
        ),
        supplier_promotion_claims_provider=lambda: supplier_claims or [],
    )


def call_names(repo):
    return [call[0] for call in repo.calls]


def test_cash_sale_creates_invoice_items_financial_effects_and_commits():
    repo = FakeCheckoutRepository()
    use_case = make_sale_use_case(repo)

    invoice_number = use_case.execute(
        store_id=1,
        cashier_id=2,
        drawer_id=3,
        payment_method="Cash",
        cash_amount=95,
        card_amount=0,
        customer_name="عميل",
        customer_phone="010",
        customer_address="عنوان",
    )

    assert invoice_number == "1001"
    assert repo.committed is True
    assert repo.rolled_back is False
    assert call_names(repo)[-1] == "commit"

    header = next(call[1] for call in repo.calls if call[0] == "insert_invoice_header")
    assert header["paid_amount"] == 95
    assert header["remaining_amount"] == 0
    assert header["customer_name"] == "عميل"

    item = next(call[1] for call in repo.calls if call[0] == "insert_sale_item")
    assert item["quantity"] == 2
    assert item["unit_price"] == 50
    assert item["discount"] == 5
    assert item["total_price"] == 95
    assert item["item_tax"] == 11.67
    assert item["item_subtotal"] == 83.33


def test_cash_sale_keeps_decimal_quantity_for_scale_items():
    repo = FakeCheckoutRepository()
    repo.buy_price = 20
    item = InvoiceItem(
        product_id=1,
        product_code="W1",
        product_name="Weighted Product",
        quantity=0.001,
        unit_price=100,
        discount=0,
        tax_percent=0,
    )
    use_case = make_sale_use_case(
        repo,
        items=[item],
        totals={
            "total": 0.10,
            "subtotal": 0.10,
            "tax_total": 0.0,
            "manual_discount": 0.0,
            "promo_discount": 0.0,
        },
    )

    use_case.execute(1, 2, 3, "Cash", 0.10, 0)

    sale_item = next(call[1] for call in repo.calls if call[0] == "insert_sale_item")
    assert sale_item["quantity"] == 0.001
    assert sale_item["total_price"] == 0.10
    assert ("decrease_product_inventory", 1, 1, 0.001) in repo.calls


def test_rejects_empty_cart_before_transaction():
    repo = FakeCheckoutRepository()
    use_case = make_sale_use_case(repo, items=[])

    with pytest.raises(ValueError, match="لا توجد أصناف"):
        use_case.execute(1, 2, 3, "Cash", 0, 0)

    assert repo.calls == []
    assert repo.committed is False
    assert repo.rolled_back is False


def test_rejects_incomplete_non_credit_payment_before_transaction():
    repo = FakeCheckoutRepository()
    use_case = make_sale_use_case(repo)

    with pytest.raises(ValueError, match="الدفع غير مكتمل"):
        use_case.execute(1, 2, 3, "Cash", 20, 0)

    assert "insert_invoice_header" not in call_names(repo)
    assert repo.committed is False
    assert repo.rolled_back is False


def test_rejects_manual_discount_that_drops_item_profit_below_five_percent():
    repo = FakeCheckoutRepository()
    repo.buy_price = 90
    item = InvoiceItem(
        product_id=1,
        product_code="P1",
        product_name="Test Product",
        quantity=1,
        unit_price=100,
        discount=0,
        tax_percent=0,
    )
    totals = {
        "total": 89.0,
        "subtotal": 89.0,
        "tax_total": 0.0,
        "manual_discount": 11.0,
        "promo_discount": 0.0,
    }
    use_case = make_sale_use_case(repo, items=[item], totals=totals)

    with pytest.raises(ValueError, match="5%"):
        use_case.execute(1, 2, 3, "Cash", 89, 0)

    assert "insert_invoice_header" not in call_names(repo)
    assert repo.committed is False
    assert repo.rolled_back is False


def test_rejects_promotion_discount_that_drops_item_profit_below_five_percent():
    repo = FakeCheckoutRepository()
    repo.buy_price = 90
    item = InvoiceItem(
        product_id=1,
        product_code="P1",
        product_name="Test Product",
        quantity=1,
        unit_price=100,
        discount=0,
        tax_percent=0,
    )
    totals = {
        "total": 89.0,
        "subtotal": 89.0,
        "tax_total": 0.0,
        "manual_discount": 0.0,
        "promo_discount": 11.0,
    }
    use_case = make_sale_use_case(repo, items=[item], totals=totals, promo_discount=11)

    with pytest.raises(ValueError, match="5%"):
        use_case.execute(1, 2, 3, "Cash", 89, 0)

    assert "insert_invoice_header" not in call_names(repo)
    assert repo.committed is False
    assert repo.rolled_back is False


def test_supplier_funded_promotion_discount_does_not_reduce_company_profit_margin():
    repo = FakeCheckoutRepository()
    repo.buy_price = 90
    item = InvoiceItem(
        product_id=1,
        product_code="P1",
        product_name="Supplier Funded Product",
        quantity=1,
        unit_price=100,
        discount=0,
        tax_percent=0,
    )
    totals = {
        "total": 89.0,
        "subtotal": 89.0,
        "tax_total": 0.0,
        "manual_discount": 0.0,
        "promo_discount": 11.0,
    }
    use_case = make_sale_use_case(
        repo,
        items=[item],
        totals=totals,
        promo_discount=11,
        company_promo_discount=0,
        supplier_claims=[
            {
                "promotion_id": 5,
                "supplier_id": 7,
                "product_id": 1,
                "quantity": 1,
                "amount": 11,
            }
        ],
    )

    invoice_number = use_case.execute(1, 2, 3, "Cash", 89, 0)

    assert invoice_number == "1001"
    assert repo.committed is True
    sale_item = next(call[1] for call in repo.calls if call[0] == "insert_sale_item")
    assert sale_item["discount"] == 11
    assert sale_item["total_price"] == 89
    claim_call = next(call[1] for call in repo.calls if call[0] == "record_supplier_promotion_claims")
    assert claim_call["sale_invoice_id"] == 77
    assert claim_call["invoice_number"] == "1001"
    assert claim_call["claims"][0]["supplier_id"] == 7
    assert claim_call["claims"][0]["amount"] == 11


def test_credit_sale_requires_customer_identity():
    repo = FakeCheckoutRepository()
    use_case = make_sale_use_case(repo)

    with pytest.raises(ValueError, match="البيع الآجل"):
        use_case.execute(1, 2, 3, "Credit", 0, 0)

    assert repo.calls == []
    assert repo.committed is False
    assert repo.rolled_back is False


def test_rolls_back_when_stock_validation_fails():
    repo = FakeCheckoutRepository()
    repo.raise_on_stock_validation = ValueError("المخزون غير كاف")
    use_case = make_sale_use_case(repo)

    with pytest.raises(ValueError, match="المخزون غير كاف"):
        use_case.execute(1, 2, 3, "Cash", 95, 0)

    assert repo.committed is False
    assert repo.rolled_back is True
    assert "rollback" in call_names(repo)


def test_credit_limit_is_checked_for_existing_customer_with_remaining_amount():
    repo = FakeCheckoutRepository()
    repo.customer = {"id": 10}
    repo.credit_limit_result = (False, "تجاوز الحد الائتماني")
    use_case = make_sale_use_case(repo)

    with pytest.raises(ValueError, match="تجاوز الحد الائتماني"):
        use_case.execute(1, 2, 3, "Credit", 20, 0, customer_phone="010")

    assert ("check_credit_limit", 10, 75.0) in repo.calls
    assert "insert_invoice_header" not in call_names(repo)


def test_tax_invoice_payload_is_saved_with_invoice():
    repo = FakeCheckoutRepository()
    tax_details = TaxInvoiceDetails(
        company_name="شركة اختبار",
        tax_id_number="123",
        commercial_registry="456",
        company_address="القاهرة",
        company_phone="010",
        notes="ملاحظة",
    )
    use_case = make_sale_use_case(repo, tax_details=tax_details)

    use_case.execute(1, 2, 3, "Cash", 95, 0)

    tax_call = next(call for call in repo.calls if call[0] == "save_sale_tax_details")
    assert tax_call[1] == 77
    assert tax_call[2]["company_name"] == "شركة اختبار"
    assert tax_call[2]["tax_id_number"] == "123"
