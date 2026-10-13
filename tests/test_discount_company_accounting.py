import pytest
from application.use_cases.cashier_cart import (
    CashierCartUseCase,
    is_product_eligible_for_discount_company,
    distribute_discount_to_lines,
)
from application.use_cases.checkout_sale import CheckoutSaleUseCase
from application.use_cases.returns import ProcessReturnUseCase
from application.use_cases.receipt_data import ReceiptDataUseCase
from models.invoice import InvoiceItem
from models.product import Product


class FakeInventoryRepo:
    def __init__(self):
        self.stock = 999.0

    def get_stock(self, product_id, store_id=None):
        return self.stock


class FakeInvoiceRepo:
    def __init__(self):
        self.promos = []
        self.promo_discount = 0.0
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.buy_prices = {}
        self.next_num = "1001"
        self.fail_on_insert_item = False

    def calculate_promotions(self, items):
        return self.promos, self.promo_discount

    def get_next_number(self):
        return self.next_num

    def get_or_create_customer(self, name, phone, address):
        return 1

    def get_customer_by_phone(self, phone):
        return None

    def check_credit_limit(self, customer_id, amount):
        return True, ""

    def validate_sale_stock(self, items, store_id):
        pass

    def insert_invoice_header(self, **kwargs):
        self.calls.append(("insert_invoice_header", kwargs))
        return 1

    def insert_sale_item(self, **kwargs):
        if self.fail_on_insert_item:
            raise RuntimeError("Database error on inserting sale item")
        self.calls.append(("insert_sale_item", kwargs))

    def decrease_product_inventory(self, product_id, store_id, quantity):
        self.calls.append(("decrease_product_inventory", product_id, store_id, quantity))

    def apply_sale_financial_effects(self, **kwargs):
        self.calls.append(("apply_sale_financial_effects", kwargs))

    def record_supplier_promotion_claims(self, **kwargs):
        pass

    def save_sale_tax_details(self, invoice_id, tax_data):
        pass

    def get_product_buy_price(self, product_id):
        return self.buy_prices.get(product_id, 10.0)

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


class FakeReturnsRepo:
    def __init__(self, invoice_items=None):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.invoice = {
            "id": 1,
            "invoice_number": "INV-1001",
            "status": "Completed",
            "payment_method": "Cash",
            "cash_amount": 180.0,
            "remaining_amount": 0.0,
            "customer_id": None,
            "store_id": 1,
        }
        self.invoice_items = invoice_items or []
        self.return_id = 501

    def get_invoice_by_number(self, invoice_number):
        return self.invoice if invoice_number == self.invoice["invoice_number"] else None

    def get_invoice_items(self, invoice_id):
        return self.invoice_items

    def get_invoice_for_return(self, invoice_id):
        return self.invoice if invoice_id == self.invoice["id"] else None

    def create_return_header(self, **kwargs):
        self.calls.append(("create_return_header", kwargs))
        return self.return_id

    def insert_return_item(self, return_id, item):
        self.calls.append(("insert_return_item", return_id, item))
        line_id = item.get("invoice_item_id")
        for line in self.invoice_items:
            if line.get("id") == line_id or line.get("invoice_item_id") == line_id:
                line["returned_quantity"] = float(line.get("returned_quantity") or 0) + float(item.get("quantity") or 0)
                line["line_returned_amount"] = float(line.get("line_returned_amount") or 0) + float(item.get("total_price") or 0)

    def add_inventory_quantity(self, product_id, store_id, quantity):
        self.calls.append(("add_inventory_quantity", product_id, store_id, quantity))

    def record_cash_refund(self, store_id, amount, return_id, invoice_number, return_number, user_id):
        self.calls.append(("record_cash_refund", store_id, amount, return_id, invoice_number, return_number, user_id))

    def reduce_customer_balance(self, customer_id, amount):
        self.calls.append(("reduce_customer_balance", customer_id, amount))

    def record_customer_return_ledger(self, customer_id, amount, return_id, invoice_number, user_id):
        self.calls.append(("record_customer_return_ledger", customer_id, amount, return_id, invoice_number, user_id))

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def make_product(product_id=1, name="منتج", price=100.0, tax=14.0):
    return Product(
        id=product_id,
        product_code=f"P{product_id}",
        product_name=name,
        sell_price=price,
        tax_percent=tax,
    )


# ==============================================================================
# 1. اختبارات سياسة الأهلية (Eligibility Policy Tests)
# ==============================================================================


def test_empty_list_legacy_company_applies_to_all_products():
    """
    الشركات القديمة (مثل xclusive) المسجلة بدون أصناف محددة وبدون نمط صريح:
    تطبق على جميع الأصناف للحفاظ على التوافق مع البيانات التاريخية.
    """
    legacy_company = {"id": 1, "name": "Xclusive", "discount_percent": 5.0, "product_ids": []}
    assert is_product_eligible_for_discount_company(legacy_company, 101) is True
    assert is_product_eligible_for_discount_company(legacy_company, 999) is True


def test_eligibility_mode_include_only():
    """
    نمط الشمول المحدد (include_only): يطبق فقط على الأصناف المذكورة.
    """
    company = {
        "id": 2,
        "name": "Partner",
        "discount_percent": 10.0,
        "eligibility_mode": "include_only",
        "product_ids": [10, 20],
    }
    assert is_product_eligible_for_discount_company(company, 10) is True
    assert is_product_eligible_for_discount_company(company, 20) is True
    assert is_product_eligible_for_discount_company(company, 30) is False


def test_eligibility_mode_exclude_mode():
    """
    نمط الاستثناء (exclude / all_except): يطبق على جميع الأصناف عدا المستثناة.
    """
    company = {
        "id": 3,
        "name": "Synergy",
        "discount_percent": 15.0,
        "eligibility_mode": "exclude",
        "product_ids": [55, 66],  # سلع مستثناة كالسجائر
    }
    assert is_product_eligible_for_discount_company(company, 10) is True
    assert is_product_eligible_for_discount_company(company, 55) is False
    assert is_product_eligible_for_discount_company(company, 66) is False


def test_eligibility_mode_all():
    """
    نمط الشمول التام (all): يطبق صراحة على كل المنتجات.
    """
    company = {"id": 4, "name": "GlobalPromo", "discount_percent": 5.0, "eligibility_mode": "all", "product_ids": []}
    assert is_product_eligible_for_discount_company(company, 1) is True
    assert is_product_eligible_for_discount_company(company, 9999) is True


# ==============================================================================
# 2. اختبارات التقريب وتوزيع الخصم على السطور (Penny Allocation & Rounding)
# ==============================================================================


def test_penny_accurate_allocation_uneven_amounts():
    """
    اختبار دقة التوزيع بالقرش:
    3 أصناف بسعر 33.33 ج.م (الإجمالي 99.99).
    خصم 10% = 10.00 ج.م.
    يجب أن يتوزع الخصم بحيث يكون مجموع الخصومات الموزعة = 10.00 ج.م تماماً دون فقدان أو زيادة أي قرش.
    """
    inv_repo = FakeInvoiceRepo()
    cart = CashierCartUseCase(FakeInventoryRepo(), inv_repo)
    cart.set_store(1)

    cart.items.append(InvoiceItem(product_id=1, product_name="صنف 1", quantity=1, unit_price=33.33))
    cart.items.append(InvoiceItem(product_id=2, product_name="صنف 2", quantity=1, unit_price=33.33))
    cart.items.append(InvoiceItem(product_id=3, product_name="صنف 3", quantity=1, unit_price=33.33))

    company = {"id": 1, "name": "Xclusive", "discount_percent": 10.0001, "product_ids": []}
    cart.set_discount_company(company)

    totals = cart.calculate_totals()
    allocations = totals["line_allocations"]

    sum_allocated = round(sum(a["company_discount"] for a in allocations), 2)
    assert sum_allocated == totals["company_discount"]
    assert totals["total"] == round(totals["gross_total"] - totals["company_discount"], 2)


def test_repeated_product_in_multiple_lines():
    """
    اختبار تكرار الصنف نفسه في عدة سطور في السلة:
    التوزيع يجب أن يتم على مستوى السطر (Line Item) وليس على معرف المنتج (Product ID).
    """
    inv_repo = FakeInvoiceRepo()
    cart = CashierCartUseCase(FakeInventoryRepo(), inv_repo)
    cart.set_store(1)

    # إضافة الصنف نفسه في سطرين مختلفين (مثلاً بأسعار أو كميات مختلفة)
    cart.items.append(InvoiceItem(product_id=10, product_name="منتج مكرر 1", quantity=2, unit_price=50.0))
    cart.items.append(InvoiceItem(product_id=10, product_name="منتج مكرر 2", quantity=1, unit_price=50.0))

    company = {"id": 1, "name": "Xclusive", "discount_percent": 10.0, "product_ids": [10]}
    cart.set_discount_company(company)

    totals = cart.calculate_totals()
    allocations = totals["line_allocations"]

    assert len(allocations) == 2
    # السطر الأول إجماليه 100 -> خصمه 10.00
    assert allocations[0]["gross_total"] == 100.0
    assert allocations[0]["company_discount"] == 10.0
    # السطر الثاني إجماليه 50 -> خصمه 5.00
    assert allocations[1]["gross_total"] == 50.0
    assert allocations[1]["company_discount"] == 5.0

    assert totals["company_discount"] == 15.0


# ==============================================================================
# 3. اختبارات تداخل الخصومات ومنع صافي السطر السالب (Discount Stacking)
# ==============================================================================


def test_stacking_promo_and_company_discount_prevent_negative_net():
    """
    اختبار تداخل خصم ترويجي كبير مع خصم شركة:
    يجب ألا يتجاوز إجمالي الخصومات على السطر إجمالي سعر السطر (لا صافي سالب).
    """
    inv_repo = FakeInvoiceRepo()
    inv_repo.promos = [
        {"product_id": 1, "discount_amount": 95.0, "promo_name": "عرض ضخم"}
    ]
    inv_repo.promo_discount = 95.0

    cart = CashierCartUseCase(FakeInventoryRepo(), inv_repo)
    cart.set_store(1)
    cart.add_item(make_product(1, "صنف 1", 100.0, 0.0), 1)

    # خصم شركة 10% (كان سيحسب 10 ج.م إضافية مما يرفع الخصم إلى 105 والصافي إلى -5)
    company = {"id": 1, "name": "Xclusive", "discount_percent": 10.0, "product_ids": []}
    cart.set_discount_company(company)

    totals = cart.calculate_totals()
    allocations = totals["line_allocations"]

    # يجب ألا يتجاوز إجمالي خصم السطر 100 ج.م وصافي السطر يجب ألا يقل عن 0
    assert allocations[0]["net_total"] >= 0.0
    assert allocations[0]["total_discount"] <= 100.0


# ==============================================================================
# 4. اختبار المطابقة المحاسبية وحفظ رأس وبنود الفاتورة (Checkout Reconciliation)
# ==============================================================================


def test_checkout_accounting_reconciliation_items_match_header_and_audit():
    """
    التحقق الصارم من المطابقة المحاسبية الكاملة:
    1. sum(invoice_items.total_price) == invoices.total_amount
    2. sum(invoice_items.item_subtotal) == invoices.subtotal_amount
    3. sum(invoice_items.item_tax) == invoices.tax_amount
    4. حفظ discount_company_id و discount_company_name و company_discount_amount
    """
    inv_repo = FakeInvoiceRepo()
    cart = CashierCartUseCase(FakeInventoryRepo(), inv_repo)
    cart.set_store(1)

    cart.add_item(make_product(1, "منتج أ", 150.0, 14.0), 1)
    cart.add_item(make_product(2, "منتج ب", 75.0, 14.0), 2)  # gross = 150.0

    company = {"id": 9, "name": "Xclusive Club", "discount_percent": 10.0, "product_ids": []}
    cart.set_discount_company(company)

    totals = cart.calculate_totals()
    assert totals["gross_total"] == 300.0
    assert totals["company_discount"] == 30.0
    assert totals["total"] == 270.0

    checkout = CheckoutSaleUseCase(
        invoice_repo=inv_repo,
        totals_calculator=cart.calculate_totals,
        promo_discount_for_product=cart.promo_discount_for_product,
        current_items_provider=lambda: cart.items,
        tax_invoice_provider=lambda: None,
        company_promo_discount_for_product=cart.company_promo_discount_for_product,
    )

    invoice_number = checkout.execute(
        store_id=1,
        cashier_id=2,
        drawer_id=3,
        payment_method="Cash",
        cash_amount=270.0,
        card_amount=0.0,
    )

    assert invoice_number == "1001"
    assert inv_repo.committed is True

    # 1. مطابقة رأس الفاتورة
    header = next(c[1] for c in inv_repo.calls if c[0] == "insert_invoice_header")
    assert header["total_amount"] == 270.0
    assert header["subtotal_amount"] == totals["subtotal"]
    assert header["tax_amount"] == totals["tax_total"]
    assert header["discount_company_id"] == 9
    assert header["discount_company_name"] == "Xclusive Club"
    assert header["company_discount_amount"] == 30.0

    # 2. مطابقة بنود الفاتورة
    items = [c[1] for c in inv_repo.calls if c[0] == "insert_sale_item"]
    assert len(items) == 2

    sum_items_total = round(sum(i["total_price"] for i in items), 2)
    sum_items_subtotal = round(sum(i["item_subtotal"] for i in items), 2)
    sum_items_tax = round(sum(i["item_tax"] for i in items), 2)
    sum_items_discount = round(sum(i["discount"] for i in items), 2)

    assert sum_items_total == header["total_amount"], "مجموع إجماليات السطور لا يطابق رأس الفاتورة!"
    assert sum_items_subtotal == header["subtotal_amount"], "مجموع قبل الضريبة للسطور لا يطابق رأس الفاتورة!"
    assert sum_items_tax == header["tax_amount"], "مجموع ضرائب السطور لا يطابق رأس الفاتورة!"
    assert sum_items_discount == 30.0, "مجموع خصومات السطور لا يطابق خصم الشركة!"


# ==============================================================================
# 5. اختبار الإيصال وتطابقه مع بنود الفاتورة (Receipt Data Synchronization)
# ==============================================================================


def test_receipt_data_reflects_allocated_company_discount():
    """
    التحقق من أن بيانات الإيصال تعكس بدقة الخصم الموزع على كل سطر ومجموعه يطابق الإجمالي.
    """
    inv_repo = FakeInvoiceRepo()
    cart = CashierCartUseCase(FakeInventoryRepo(), inv_repo)
    cart.set_store(1)
    cart.add_item(make_product(1, "منتج 1", 100.0, 14.0), 1)

    company = {"id": 1, "name": "Xclusive", "discount_percent": 10.0, "product_ids": []}
    cart.set_discount_company(company)

    receipt_use_case = ReceiptDataUseCase(
        current_items_provider=lambda: cart.items,
        totals_provider=cart.calculate_totals,
        applied_promos_provider=lambda: cart.applied_promos,
        tax_invoice_provider=lambda: None,
    )

    receipt_header, receipt_items = receipt_use_case.execute(
        invoice_number="INV-1001",
        drawer_id=1,
        payment_method="Cash",
        cash_amount=90.0,
        card_amount=0.0,
        paid_amount=90.0,
    )

    assert receipt_header["total_amount"] == 90.0
    assert receipt_header["company_discount"] == 10.0

    # سطر الإيصال يعكس الخصم الموزع
    assert len(receipt_items) == 1
    assert receipt_items[0]["line_discount"] == 10.0
    assert receipt_items[0]["company_discount"] == 10.0
    assert receipt_items[0]["total"] == 90.0


# ==============================================================================
# 6. اختبارات المرتجعات بالقيمة الصافية التاريخية (Returns with Historical Net)
# ==============================================================================


def test_full_return_refunds_exact_historical_net_paid():
    """
    مرتجع كامل لصنف بيع بخصم شركة:
    إذا بيع الصنف (100 ج.م مع خصم 10% = 90 ج.م صافي):
    يجب أن يسترد العميل 90.0 ج.م فقط وليس 100.0 ج.م!
    """
    # صنف بيع في الفاتورة التاريخية بـ total_price = 90.0 بعد الخصم
    invoice_items = [
        {
            "product_id": 10,
            "product_name": "منتج مخصوم",
            "quantity": 1,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 70.0,
            "total_price": 90.0,  # الصافي الفعلي المدفوع
        }
    ]
    returns_repo = FakeReturnsRepo(invoice_items)
    returns_use_case = ProcessReturnUseCase(returns_repo)

    result = returns_use_case.execute(
        invoice_id=1,
        items=[{"product_id": 10, "quantity": 1}],
        reason="استرجاع منتج",
        user_id=1,
        store_id=1,
    )

    assert result is not None
    # يجب أن يكون الاسترداد 90.0 ج.م تماماً
    assert result["total_amount"] == 90.0
    assert result["cash_refund"] == 90.0


def test_partial_return_refunds_proportional_historical_net():
    """
    مرتجع جزئي: شراء قطعتين بإجمالي صافي 180 ج.م (90 ج.م للقطعة).
    إرجاع قطعة واحدة يجب أن يسترد 90.0 ج.م.
    """
    invoice_items = [
        {
            "product_id": 20,
            "product_name": "منتج كمية",
            "quantity": 2,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 60.0,
            "total_price": 180.0,  # 90 ج.م للقطعة الواحدة
        }
    ]
    returns_repo = FakeReturnsRepo(invoice_items)
    returns_use_case = ProcessReturnUseCase(returns_repo)

    result = returns_use_case.execute(
        invoice_id=1,
        items=[{"product_id": 20, "quantity": 1}],
        reason="استرجاع قطعة واحدة",
        user_id=1,
        store_id=1,
    )

    assert result is not None
    assert result["total_amount"] == 90.0
    assert result["cash_refund"] == 90.0


# ==============================================================================
# 7. اختبار الفشل والتراجع التام عن المعاملة (Transaction Rollback)
# ==============================================================================


def test_checkout_rollback_on_failure_leaves_no_partial_state():
    """
    التحقق من تنفيذ rollback بالكامل عند حدوث أي خطأ أثناء إدخال السطور،
    وعدم حفظ أي بيانات منقوصة.
    """
    inv_repo = FakeInvoiceRepo()
    inv_repo.fail_on_insert_item = True  # محاكاة خطأ أثناء حفظ أحد بنود الفاتورة

    cart = CashierCartUseCase(FakeInventoryRepo(), inv_repo)
    cart.set_store(1)
    cart.add_item(make_product(1, "منتج", 100.0, 14.0), 1)

    checkout = CheckoutSaleUseCase(
        invoice_repo=inv_repo,
        totals_calculator=cart.calculate_totals,
        promo_discount_for_product=cart.promo_discount_for_product,
        current_items_provider=lambda: cart.items,
        tax_invoice_provider=lambda: None,
        company_promo_discount_for_product=cart.company_promo_discount_for_product,
    )

    with pytest.raises(RuntimeError, match="Database error on inserting sale item"):
        checkout.execute(
            store_id=1,
            cashier_id=1,
            drawer_id=1,
            payment_method="Cash",
            cash_amount=100.0,
            card_amount=0.0,
        )

    # التحقق من استدعاء rollback وعدم استدعاء commit
    assert inv_repo.rolled_back is True
    assert inv_repo.committed is False


# ==============================================================================
# 8. اختبارات تدقيق إضافية مستقلة (Independent Audit Verification Tests)
# ==============================================================================


def test_accounting_reconciliation_separates_company_manual_and_promo_discounts():
    """
    التحقق الصارم من فصل الخصومات:
    وجود خصم يدوي + خصم ترويجي + خصم شركة في نفس الفاتورة.
    يجب أن تثبت المطابقة أن:
    1. sum(alloc['company_discount']) == header['company_discount_amount']
    2. sum(alloc['promo_discount']) == totals['promo_discount']
    3. sum(alloc['manual_discount']) == totals['manual_discount']
    4. sum(items['discount']) == totals['manual_discount'] + totals['promo_discount'] + totals['company_discount']
    5. sum(items['total_price']) == header['total_amount']
    6. sum(items['item_subtotal']) == header['subtotal_amount']
    7. sum(items['item_tax']) == header['tax_amount']
    """
    inv_repo = FakeInvoiceRepo()
    # عرض ترويجي على صنف 1 بقيمة 15.0 ج.م
    inv_repo.promos = [{"product_id": 1, "discount_amount": 15.0, "promo_name": "عرض صنف 1"}]
    inv_repo.promo_discount = 15.0

    cart = CashierCartUseCase(FakeInventoryRepo(), inv_repo)
    cart.set_store(1)

    cart.add_item(make_product(1, "صنف 1", 100.0, 14.0), 1)
    cart.add_item(make_product(2, "صنف 2", 100.0, 14.0), 1)
    cart.add_item(make_product(3, "صنف 3", 50.0, 0.0), 1)

    # خصم شركة 10% على كل الأصناف (إجمالي 250 -> 25 ج.م)
    company = {"id": 5, "name": "Corporate Partner", "discount_percent": 10.0, "product_ids": []}
    cart.set_discount_company(company)

    # إضافة خصم يدوي إضافي بقيمة 10.0 ج.م
    cart.manual_discount = 10.0

    totals = cart.calculate_totals()
    allocations = totals["line_allocations"]

    assert totals["gross_total"] == 250.0
    assert totals["company_discount"] == 25.0
    assert totals["manual_discount"] == 10.0
    assert totals["promo_discount"] == 15.0
    assert totals["total"] == 200.0  # 250 - 25 - 10 - 15 = 200.0

    # التحقق من أن الخصومات مفصولة في توزيع السطور وتطابق الرأس
    sum_line_company = round(sum(a["company_discount"] for a in allocations), 2)
    sum_line_promo = round(sum(a["promo_discount"] for a in allocations), 2)
    sum_line_manual = round(sum(a["manual_discount"] for a in allocations), 2)
    sum_line_total_disc = round(sum(a["total_discount"] for a in allocations), 2)

    assert sum_line_company == totals["company_discount"]
    assert sum_line_promo == totals["promo_discount"]
    assert sum_line_manual == totals["manual_discount"]
    assert sum_line_total_disc == 50.0  # 25 + 10 + 15

    checkout = CheckoutSaleUseCase(
        invoice_repo=inv_repo,
        totals_calculator=cart.calculate_totals,
        promo_discount_for_product=cart.promo_discount_for_product,
        current_items_provider=lambda: cart.items,
        tax_invoice_provider=lambda: None,
        company_promo_discount_for_product=cart.company_promo_discount_for_product,
    )

    checkout.execute(
        store_id=1,
        cashier_id=1,
        drawer_id=1,
        payment_method="Cash",
        cash_amount=200.0,
        card_amount=0.0,
    )

    header = next(c[1] for c in inv_repo.calls if c[0] == "insert_invoice_header")
    items = [c[1] for c in inv_repo.calls if c[0] == "insert_sale_item"]

    assert header["total_amount"] == 200.0
    assert header["company_discount_amount"] == 25.0
    assert sum_line_company == header["company_discount_amount"]

    sum_items_total = round(sum(i["total_price"] for i in items), 2)
    sum_items_subtotal = round(sum(i["item_subtotal"] for i in items), 2)
    sum_items_tax = round(sum(i["item_tax"] for i in items), 2)
    sum_items_discount = round(sum(i["discount"] for i in items), 2)

    assert sum_items_total == header["total_amount"]
    assert sum_items_subtotal == header["subtotal_amount"]
    assert sum_items_tax == header["tax_amount"]
    assert sum_items_discount == totals["company_discount"] + totals["manual_discount"] + totals["promo_discount"]


def test_receipt_total_discount_includes_company_and_other_discounts():
    """
    التحقق من أن إجمالي الخصم في رأس الإيصال يجمع خصم الشركة مع الخصومات الأخرى
    ولا يتجاهل خصم الشركة.
    """
    inv_repo = FakeInvoiceRepo()
    cart = CashierCartUseCase(FakeInventoryRepo(), inv_repo)
    cart.set_store(1)
    cart.add_item(make_product(1, "منتج 1", 100.0, 14.0), 1)

    company = {"id": 1, "name": "Xclusive", "discount_percent": 10.0, "product_ids": []}
    cart.set_discount_company(company)
    cart.manual_discount = 5.0

    receipt_use_case = ReceiptDataUseCase(
        current_items_provider=lambda: cart.items,
        totals_provider=cart.calculate_totals,
        applied_promos_provider=lambda: cart.applied_promos,
        tax_invoice_provider=lambda: None,
    )

    receipt_header, receipt_items = receipt_use_case.execute(
        invoice_number="INV-1002",
        drawer_id=1,
        payment_method="Cash",
        cash_amount=85.0,
        card_amount=0.0,
        paid_amount=85.0,
    )

    # إجمالي الخصم في الإيصال: 10 خصم شركة + 5 يدوي = 15
    assert receipt_header["company_discount"] == 10.0
    assert receipt_header["discount"] == 5.0
    assert receipt_header["total_discount"] == 15.0
    assert receipt_header["total_amount"] == 85.0


def test_return_product_repeated_across_multiple_lines_with_company_discount():
    """
    اختبار إرجاع صنف كان مكرراً في أكثر من سطر في الفاتورة وبخصومات موزعة:
    السطر 1: قطعتان بسعر 100 (صافي 180 بعد الخصم)
    السطر 2: قطعة بسعر 100 (صافي 90 بعد الخصم)
    إجمالي 3 قطع بصافي 270 ج.م (90 ج.م للقطعة).
    إرجاع قطعتين من السطر 1 عبر invoice_item_id=1 يجب أن يسترد 180.0 ج.م بدقة.
    """
    invoice_items = [
        {
            "id": 1,
            "product_id": 101,
            "product_name": "منتج مكرر سطر 1",
            "quantity": 2,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 60.0,
            "total_price": 180.0,
        },
        {
            "id": 2,
            "product_id": 101,
            "product_name": "منتج مكرر سطر 2",
            "quantity": 1,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 60.0,
            "total_price": 90.0,
        },
    ]
    returns_repo = FakeReturnsRepo(invoice_items)
    returns_use_case = ProcessReturnUseCase(returns_repo)

    result = returns_use_case.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 1, "quantity": 2}],
        reason="استرجاع قطعتين من أصل 3",
        user_id=1,
        store_id=1,
    )

    assert result is not None
    assert result["total_amount"] == 180.0
    assert result["cash_refund"] == 180.0


def test_checkout_fails_explicitly_if_repo_cannot_save_company_discount():
    """
    التحقق من عدم السماح بحفظ الفاتورة بصمت دون بيانات شركة الخصم:
    إذا كان المستودع قديماً ولا يدعم حفظ أعمدة شركة الخصم، يجب أن تفشل المعاملة وتتراجع.
    """
    class FakeLegacyRepoWithoutCompanyColumns(FakeInvoiceRepo):
        def insert_invoice_header(self, invoice_number, store_id, cashier_id, customer_id=None,
                                  customer_name="", customer_phone="", customer_address="",
                                  drawer_id=None, payment_method="Cash", cash_amount=0,
                                  card_amount=0, total_amount=0, paid_amount=0,
                                  remaining_amount=0, subtotal_amount=0, tax_amount=0):
            # لا يقبل وسائط discount_company_id وغيره (يطرح TypeError)
            raise TypeError("unexpected keyword argument 'discount_company_id'")

    legacy_repo = FakeLegacyRepoWithoutCompanyColumns()
    cart = CashierCartUseCase(FakeInventoryRepo(), legacy_repo)
    cart.set_store(1)
    cart.add_item(make_product(1, "منتج", 100.0, 14.0), 1)
    cart.set_discount_company({"id": 1, "name": "Xclusive", "discount_percent": 10.0, "product_ids": []})

    checkout = CheckoutSaleUseCase(
        invoice_repo=legacy_repo,
        totals_calculator=cart.calculate_totals,
        promo_discount_for_product=cart.promo_discount_for_product,
        current_items_provider=lambda: cart.items,
        tax_invoice_provider=lambda: None,
        company_promo_discount_for_product=cart.company_promo_discount_for_product,
    )

    with pytest.raises(RuntimeError, match="مستودع الفواتير لا يدعم تسجيل بيانات شركة الخصم"):
        checkout.execute(
            store_id=1,
            cashier_id=1,
            drawer_id=1,
            payment_method="Cash",
            cash_amount=90.0,
            card_amount=0.0,
        )

    assert legacy_repo.rolled_back is True
    assert legacy_repo.committed is False


# ==============================================================================
# 9. اختبارات تدقيق دقة المرتجعات التاريخية (Historical Return Accuracy Tests)
# ==============================================================================


def test_returns_record_invoice_item_id_and_product_id():
    """
    التحقق الهندسي من أن المرتجعات ترتبط بـ invoice_item_id و product_id:
    كل من بنية قاعدة البيانات ودالة ProcessReturnUseCase تسجل معرف سطر الفاتورة invoice_item_id بدقة.
    """
    invoice_items = [
        {
            "id": 1001,
            "product_id": 101,
            "product_name": "منتج تجريبي",
            "quantity": 1,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 60.0,
            "total_price": 100.0,
        }
    ]
    repo = FakeReturnsRepo(invoice_items)
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        invoice_id=1,
        items=[{"product_id": 101, "quantity": 1}],
        reason="استرجاع",
        user_id=1,
        store_id=1,
    )

    assert result is not None
    # التحقق من أن السجلات المُدخلة في return_items تعتمد على invoice_item_id و product_id
    item_call = next(c for c in repo.calls if c[0] == "insert_return_item")
    return_item_payload = item_call[2]
    assert return_item_payload["product_id"] == 101
    assert return_item_payload["invoice_item_id"] == 1001


def test_full_return_for_repeated_product_with_differing_discounts():
    """
    التحقق من المرتجع الكامل لصنف مكرر بسطور متفاوتة الأسعار والخصومات:
    السطر 1: قطعة واحدة بسعر 100 وخصم 50% -> صافي 50.0 ج.م
    السطر 2: قطعة واحدة بسعر 100 وخصم 0%  -> صافي 100.0 ج.م
    إجمالي الفاتورة للصنف: 150.0 ج.م
    استرجاع القطعتين بالكامل عبر تحديد السطور يسترد 150.0 ج.م مطابقة تماماً للقيمة المدفوعة.
    """
    invoice_items = [
        {
            "id": 101,
            "product_id": 201,
            "product_name": "قميص",
            "quantity": 1,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 50.0,
            "total_price": 50.0,
        },
        {
            "id": 102,
            "product_id": 201,
            "product_name": "قميص",
            "quantity": 1,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 50.0,
            "total_price": 100.0,
        },
    ]
    repo = FakeReturnsRepo(invoice_items)
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        invoice_id=1,
        items=[
            {"invoice_item_id": 101, "quantity": 1},
            {"invoice_item_id": 102, "quantity": 1},
        ],
        reason="مرتجع كامل",
        user_id=1,
        store_id=1,
    )

    assert result is not None
    assert result["total_amount"] == 150.0
    assert result["cash_refund"] == 150.0


def test_partial_return_line_level_exact_amount_and_ambiguity_rejection():
    """
    التحقق من أن المرتجع الجزئي لصنف مكرر في عدة سطور:
    1. عند تمرير product_id فقط دون invoice_item_id، يتم رفض المعاملة صراحة لمنع الانحراف المالي أو التخمين.
    2. عند تحديد السطر 1 (صافي 50 ج.م)، يتم استرداد 50.0 ج.م بدقة دون الاعتماد على متوسط مرجح غير دقيق.
    3. عند تحديد السطر 2 (صافي 100 ج.م)، يتم استرداد 100.0 ج.م بدقة.
    """
    invoice_items = [
        {
            "id": 101,
            "product_id": 201,
            "product_name": "قميص",
            "quantity": 1,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 50.0,
            "total_price": 50.0,
        },
        {
            "id": 102,
            "product_id": 201,
            "product_name": "قميص",
            "quantity": 1,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 50.0,
            "total_price": 100.0,
        },
    ]
    repo = FakeReturnsRepo(invoice_items)
    use_case = ProcessReturnUseCase(repo)

    # 1. رفض محاولة المرتجع الغامض لسلعة مكررة بدون تحديد السطر
    result_ambiguous = use_case.execute(
        invoice_id=1,
        items=[{"product_id": 201, "quantity": 1}],
        reason="مرتجع غامض",
        user_id=1,
        store_id=1,
    )
    assert result_ambiguous is None
    assert "مسجل في أكثر من سطر بالفاتورة" in use_case.last_error

    # 2. استرداد السطر الأول بدقة (50 ج.م)
    result_line1 = use_case.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 101, "quantity": 1}],
        reason="استرجاع السطر 1",
        user_id=1,
        store_id=1,
    )
    assert result_line1 is not None
    assert result_line1["total_amount"] == 50.0

    # 3. استرداد السطر الثاني بدقة (100 ج.م)
    repo2 = FakeReturnsRepo(invoice_items)
    use_case2 = ProcessReturnUseCase(repo2)
    result_line2 = use_case2.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 102, "quantity": 1}],
        reason="استرجاع السطر 2",
        user_id=1,
        store_id=1,
    )
    assert result_line2 is not None
    assert result_line2["total_amount"] == 100.0


def test_sequential_partial_returns_of_repeated_product_lines():
    """
    التحقق من تتبع الكمية المسترجعة لكل سطر بشكل مستقل عند التكرار:
    السطر 1: قطعتان، تم إرجاع 1 سابقاً -> المتبقي 1 (صافي 90)
    السطر 2: قطعة واحدة، تم إرجاع 0 -> المتبقي 1 (صافي 90)
    استرجاع المتبقي من السطر 1 يرجع 90.0 ج.م بدقة.
    """
    invoice_items = [
        {
            "id": 101,
            "product_id": 201,
            "product_name": "صنف مكرر",
            "quantity": 2,
            "returned_quantity": 1,
            "unit_price": 100.0,
            "buy_price": 50.0,
            "total_price": 180.0,
        },
        {
            "id": 102,
            "product_id": 201,
            "product_name": "صنف مكرر",
            "quantity": 1,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 50.0,
            "total_price": 90.0,
        },
    ]
    repo = FakeReturnsRepo(invoice_items)
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 101, "quantity": 1}],
        reason="استرجاع المتبقي من السطر 1",
        user_id=1,
        store_id=1,
    )

    assert result is not None
    assert result["total_amount"] == 90.0


def test_return_rejects_exceeding_sold_quantity_on_line():
    """
    التحقق من رفض أي مرتجع يتجاوز الكمية المباعة المتبقية للسطر.
    """
    invoice_items = [
        {
            "id": 101,
            "product_id": 201,
            "product_name": "صنف 1",
            "quantity": 2,
            "returned_quantity": 1,
            "unit_price": 100.0,
            "buy_price": 50.0,
            "total_price": 180.0,
        }
    ]
    repo = FakeReturnsRepo(invoice_items)
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 101, "quantity": 2}],  # متاح 1 فقط
        reason="محاولة تجاوز المتاح",
        user_id=1,
        store_id=1,
    )
    assert result is None
    assert "كمية المرتجع غير صحيحة" in use_case.last_error


def test_return_rejects_historical_ambiguous_return_records():
    """
    التحقق من إيقاف المعالجة الآلية وطلب مراجعة الحسابات إذا كان هناك مرتجع قديم غامض للصنف.
    """
    invoice_items = [
        {
            "id": 101,
            "product_id": 201,
            "product_name": "صنف به مرتجع تاريخي قديم",
            "quantity": 2,
            "returned_quantity": 0,
            "unit_price": 100.0,
            "buy_price": 50.0,
            "total_price": 180.0,
            "is_ambiguous_return": True,
        }
    ]
    repo = FakeReturnsRepo(invoice_items)
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 101, "quantity": 1}],
        reason="محاولة استرجاع",
        user_id=1,
        store_id=1,
    )
    assert result is None
    assert "تحتوي على مرتجع تاريخي غير محدد السطر" in use_case.last_error


def test_single_line_product_return_by_product_id_compatibility():
    """
    التحقق من التوافق الخلفي: إذا كان الصنف فريداً في الفاتورة (سطر واحد)،
    فإن المرتجع عبر product_id يعمل بنجاح وبدقة.
    """
    invoice_items = [
        {
            "id": 101,
            "product_id": 201,
            "product_name": "صنف منفرد",
            "quantity": 3,
            "returned_quantity": 0,
            "unit_price": 50.0,
            "buy_price": 30.0,
            "total_price": 150.0,
        }
    ]
    repo = FakeReturnsRepo(invoice_items)
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        invoice_id=1,
        items=[{"product_id": 201, "quantity": 1}],
        reason="استرجاع بصيغة product_id للصنف المنفرد",
        user_id=1,
        store_id=1,
    )
    assert result is not None
    assert result["total_amount"] == 50.0


def test_repeated_partial_returns_reconciles_fractional_cent_rounding():
    """
    التحقق من أن المرتجعات الجزئية المتكررة لصنف ذي كسور قرش (100 ج.م مقسمة على 3 قطع):
    - المرتجع 1: 33.33 ج.م
    - المرتجع 2: 33.33 ج.م
    - المرتجع 3 (الأخير): 33.34 ج.م (مطابقة الرصيد المتبقي بدقة Decimal)
    - الإجمالي التراكمي للمرتجعات: 100.00 ج.م بالتمام والكمال
    - المرتجع 4: مرفوض لتجاوز الكمية المتاحة (0 متبقي)
    """
    invoice_items = [
        {
            "id": 501,
            "product_id": 301,
            "product_name": "صنف كسور",
            "quantity": 3,
            "returned_quantity": 0,
            "unit_price": 33.33,
            "buy_price": 20.0,
            "total_price": 100.0,
            "line_returned_amount": 0.0,
        }
    ]
    repo = FakeReturnsRepo(invoice_items)
    use_case = ProcessReturnUseCase(repo)

    # المرتجع الأول: قطعة 1
    ret1 = use_case.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 501, "quantity": 1}],
        reason="مرتجع 1",
        user_id=1,
        store_id=1,
    )
    assert ret1 is not None
    assert ret1["total_amount"] == 33.33

    # المرتجع الثاني: قطعة 1
    ret2 = use_case.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 501, "quantity": 1}],
        reason="مرتجع 2",
        user_id=1,
        store_id=1,
    )
    assert ret2 is not None
    assert ret2["total_amount"] == 33.33

    # المرتجع الثالث: القطعة الأخيرة (يجب أن يجبر كسر القرش ليكون الإجمالي 100.00)
    ret3 = use_case.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 501, "quantity": 1}],
        reason="مرتجع 3",
        user_id=1,
        store_id=1,
    )
    assert ret3 is not None
    assert ret3["total_amount"] == 33.34
    assert round(ret1["total_amount"] + ret2["total_amount"] + ret3["total_amount"], 2) == 100.00

    # محاولة مرتجع رابع: يجب أن يفشل لتجاوز الكمية المتاحة
    ret4 = use_case.execute(
        invoice_id=1,
        items=[{"invoice_item_id": 501, "quantity": 1}],
        reason="مرتجع 4 غير متاح",
        user_id=1,
        store_id=1,
    )
    assert ret4 is None
    assert "كمية المرتجع غير صحيحة" in use_case.last_error

