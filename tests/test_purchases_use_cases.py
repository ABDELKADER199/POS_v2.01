import pytest

from application.errors import PurchaseValidationError
from application.use_cases.purchases import (
    AddSupplierUseCase,
    CreatePurchaseInvoiceUseCase,
    CreatePurchaseReturnUseCase,
    ListSuppliersUseCase,
    PayPurchaseInvoiceUseCase,
    PurchaseHistoryUseCase,
    PurchaseInvoiceDetailsUseCase,
    SearchPurchaseProductUseCase,
    SoftDeleteSupplierUseCase,
    SupplierPaymentUseCase,
    UpdateSupplierUseCase,
)


class FakePurchaseRepository:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.supplier = {"id": 1, "name": "مورد", "is_active": 1}
        self.product = {"id": 10, "product_name": "منتج", "buy_price": 20.0}
        self.product_stock = 10.0
        self.invoice = {"id": 99, "invoice_number": "PUR-99"}
        self.invoice_details = {
            "id": 99,
            "invoice_number": "PUR-99",
            "supplier_id": 1,
            "supplier_name": "مورد",
            "items": [
                {
                    "product_id": 10,
                    "product_name": "منتج",
                    "quantity": 5,
                    "unit_cost": 30.0,
                    "returned_quantity": 1,
                }
            ],
        }
        self.invoice_for_payment = {
            "id": 99,
            "supplier_id": 1,
            "invoice_number": "PUR-99",
            "paid_amount": 20.0,
            "remaining_amount": 80.0,
            "payment_method": "Credit",
        }
        self.inventory_quantity = 10
        self.remaining_purchase_quantity = 4
        self.purchase_return = {"id": 77, "return_number": "PR-000077"}
        self.raise_on_insert_item = None

    def ensure_purchase_columns(self):
        self.calls.append(("ensure_purchase_columns",))

    def get_all_suppliers(self):
        self.calls.append(("get_all_suppliers",))
        return [self.supplier]

    def add_supplier(self, name, phone, address, tax_number, opening_balance):
        self.calls.append(("add_supplier", name, phone, address, tax_number, opening_balance))
        return True

    def update_supplier(self, supplier_id, name, phone, address, tax_number):
        self.calls.append(("update_supplier", supplier_id, name, phone, address, tax_number))
        return True

    def soft_delete_supplier(self, supplier_id):
        self.calls.append(("soft_delete_supplier", supplier_id))
        return True

    def search_product(self, term):
        self.calls.append(("search_product", term))
        return self.product if term else None

    def get_purchase_history(self, page=1, per_page=100):
        self.calls.append(("get_purchase_history", page, per_page))
        return [self.invoice]

    def get_purchase_invoice_details(self, search_term):
        self.calls.append(("get_purchase_invoice_details", search_term))
        return self.invoice_details if search_term == "PUR-99" else None

    def get_supplier(self, supplier_id):
        self.calls.append(("get_supplier", supplier_id))
        return self.supplier if supplier_id == self.supplier["id"] else None

    def get_product_snapshot(self, product_id):
        self.calls.append(("get_product_snapshot", product_id))
        return self.product if product_id == self.product["id"] else None

    def get_product_total_stock(self, product_id):
        self.calls.append(("get_product_total_stock", product_id))
        return self.product_stock

    def create_purchase_invoice_header(self, **kwargs):
        self.calls.append(("create_purchase_invoice_header", kwargs))
        return self.invoice

    def insert_purchase_item(self, invoice_id, product_id, quantity, unit_cost, expiry_date=None):
        self.calls.append(("insert_purchase_item", invoice_id, product_id, quantity, unit_cost, expiry_date))
        if self.raise_on_insert_item:
            raise self.raise_on_insert_item

    def add_inventory_quantity(self, product_id, store_id, quantity):
        self.calls.append(("add_inventory_quantity", product_id, store_id, quantity))

    def decrease_inventory_quantity(self, product_id, store_id, quantity):
        self.calls.append(("decrease_inventory_quantity", product_id, store_id, quantity))

    def get_inventory_quantity(self, product_id, store_id):
        self.calls.append(("get_inventory_quantity", product_id, store_id))
        return self.inventory_quantity

    def get_purchase_item_remaining_quantity(self, invoice_id, product_id):
        self.calls.append(("get_purchase_item_remaining_quantity", invoice_id, product_id))
        return self.remaining_purchase_quantity

    def create_purchase_return_header(self, purchase_invoice_id, supplier_id, store_id, user_id, total_amount, settlement_method, reason):
        self.calls.append(
            (
                "create_purchase_return_header",
                purchase_invoice_id,
                supplier_id,
                store_id,
                user_id,
                total_amount,
                settlement_method,
                reason,
            )
        )
        return self.purchase_return

    def insert_purchase_return_item(self, return_id, product_id, quantity, unit_cost):
        self.calls.append(("insert_purchase_return_item", return_id, product_id, quantity, unit_cost))

    def record_supplier_purchase_return_credit(self, supplier_id, user_id=None, return_id=None, amount=0, description="", store_id=None, **kwargs):
        self.calls.append(("record_supplier_purchase_return_credit", supplier_id, user_id, return_id, amount, description))

    def record_purchase_return_cash_refund(self, supplier_id, store_id, user_id, return_id, amount, description):
        self.calls.append(("record_purchase_return_cash_refund", supplier_id, store_id, user_id, return_id, amount, description))

    def update_product_after_purchase(self, product_id, new_cost=None, buy_price=None, sell_price=None, supplier_id=None, supplier_name=""):
        self.calls.append(("update_product_after_purchase", product_id, new_cost, buy_price, sell_price, supplier_id, supplier_name))

    def create_supplier_funded_promotion(self, supplier_id, product_id, product_name, discount_value, invoice_id):
        self.calls.append((
            "create_supplier_funded_promotion",
            supplier_id,
            product_id,
            product_name,
            discount_value,
            invoice_id,
        ))
        return 5

    def increase_supplier_balance(self, supplier_id, amount):
        self.calls.append(("increase_supplier_balance", supplier_id, amount))

    def record_supplier_purchase_debt(self, supplier_id, store_id, user_id, invoice_id, amount, description):
        self.calls.append(("record_supplier_purchase_debt", supplier_id, store_id, user_id, invoice_id, amount, description))

    def decrease_supplier_balance(self, supplier_id, amount):
        self.calls.append(("decrease_supplier_balance", supplier_id, amount))

    def allocate_supplier_payment(self, supplier_id, amount):
        self.calls.append(("allocate_supplier_payment", supplier_id, amount))

    def record_supplier_payment(
        self,
        supplier_id,
        store_id,
        user_id,
        invoice_id,
        amount,
        payment_method,
        description,
        record_ledger,
    ):
        self.calls.append(
            (
                "record_supplier_payment",
                supplier_id,
                store_id,
                user_id,
                invoice_id,
                amount,
                payment_method,
                description,
                record_ledger,
            )
        )

    def get_purchase_invoice_for_payment(self, invoice_id):
        self.calls.append(("get_purchase_invoice_for_payment", invoice_id))
        return self.invoice_for_payment if invoice_id == self.invoice_for_payment["id"] else None

    def update_purchase_invoice_payment_state(self, invoice_id, paid_amount, remaining_amount, payment_status, payment_method):
        self.calls.append(
            (
                "update_purchase_invoice_payment_state",
                invoice_id,
                paid_amount,
                remaining_amount,
                payment_status,
                payment_method,
            )
        )

    def reconcile_purchase_return_credits(self, invoice_id=None):
        self.calls.append(("reconcile_purchase_return_credits", invoice_id))

    def sync_supplier_balance_from_open_invoices(self, supplier_id=None):
        self.calls.append(("sync_supplier_balance_from_open_invoices", supplier_id))

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def call_names(repo):
    return [call[0] for call in repo.calls]


def purchase_items():
    return [
        {
            "product_id": 10,
            "name": "منتج",
            "quantity": 5,
            "cost": 30.0,
            "sell_price": 45.0,
            "expiry_date": "2027-01-31",
        }
    ]


def test_create_cash_purchase_updates_stock_cost_and_records_payment():
    repo = FakePurchaseRepository()
    use_case = CreatePurchaseInvoiceUseCase(repo)

    invoice = use_case.execute(
        supplier_id=1,
        store_id=2,
        user_id=3,
        ref_number="REF-1",
        items=purchase_items(),
        subtotal=0,
        discount=10,
        tax=5,
        total=0,
        paid=145,
        payment_method="نقدي",
    )

    assert invoice == repo.invoice
    assert repo.committed is True
    assert repo.rolled_back is False

    header = next(call[1] for call in repo.calls if call[0] == "create_purchase_invoice_header")
    assert header["subtotal"] == 150.0
    assert header["discount"] == 10.0
    assert header["tax"] == 5.0
    assert header["total"] == 145.0
    assert header["paid"] == 145.0
    assert header["remaining"] == 0.0
    assert header["payment_method"] == "Cash"
    assert header["payment_status"] == "paid"

    assert ("insert_purchase_item", 99, 10, 5, 30.0, "2027-01-31") in repo.calls
    assert ("add_inventory_quantity", 10, 2, 5) in repo.calls

    update_call = next(call for call in repo.calls if call[0] == "update_product_after_purchase")
    assert float(update_call[2]) == pytest.approx(23.3333333333)
    assert update_call[4] == 45.0

    payment_call = next(call for call in repo.calls if call[0] == "record_supplier_payment")
    assert payment_call[5] == 145.0
    assert payment_call[6] == "Cash"
    assert payment_call[8] is False
    assert "increase_supplier_balance" not in call_names(repo)


def test_create_purchase_with_supplier_support_creates_supplier_funded_promotion():
    repo = FakePurchaseRepository()
    use_case = CreatePurchaseInvoiceUseCase(repo)
    items = purchase_items()
    items[0]["supplier_support_amount"] = 4.5

    invoice = use_case.execute(1, 2, 3, "", items, 0, 0, 0, 0, 150, "Cash")

    assert invoice == repo.invoice
    assert (
        "create_supplier_funded_promotion",
        1,
        10,
        'منتج',
        4.5,
        99,
    ) in repo.calls


def test_create_purchase_with_direct_support_and_free_quantity_updates_effective_cost():
    repo = FakePurchaseRepository()

    def insert_purchase_item(**kwargs):
        repo.calls.append(("insert_purchase_item_v2", kwargs))

    def create_supplier_funded_promotion(**kwargs):
        repo.calls.append(("create_supplier_funded_promotion_v2", kwargs))
        return 5

    repo.insert_purchase_item = insert_purchase_item
    repo.create_supplier_funded_promotion = create_supplier_funded_promotion
    use_case = CreatePurchaseInvoiceUseCase(repo)
    items = purchase_items()
    items[0].update({
        "quantity": 10,
        "cost": 20.0,
        "sell_price": 35.0,
        "supplier_support_type": "direct_per_unit",
        "supplier_support_value": 2.0,
        "free_quantity": 2,
    })

    invoice = use_case.execute(1, 2, 3, "", items, 0, 0, 0, 0, 180, "Cash")

    assert invoice == repo.invoice
    header = next(call[1] for call in repo.calls if call[0] == "create_purchase_invoice_header")
    assert header["subtotal"] == 200.0
    assert header["discount"] == 20.0
    assert header["total"] == 180.0
    assert next(call for call in repo.calls if call[0] == "add_inventory_quantity") == (
        "add_inventory_quantity", 10, 2, 12
    )
    update_call = next(call for call in repo.calls if call[0] == "update_product_after_purchase")
    assert float(update_call[2]) == pytest.approx(17.2727272727)
    insert_call = next(call[1] for call in repo.calls if call[0] == "insert_purchase_item_v2")
    assert insert_call["supplier_support_type"] == "direct_per_unit"
    assert insert_call["supplier_support_value"] == 2.0
    assert insert_call["free_quantity"] == 2
    assert "create_supplier_funded_promotion_v2" not in call_names(repo)


def test_create_credit_purchase_forces_paid_zero_and_records_supplier_debt():
    repo = FakePurchaseRepository()
    use_case = CreatePurchaseInvoiceUseCase(repo)

    invoice = use_case.execute(1, 2, 3, "", purchase_items(), 0, 0, 0, 0, 100, "آجل")

    assert invoice == repo.invoice
    header = next(call[1] for call in repo.calls if call[0] == "create_purchase_invoice_header")
    assert header["payment_method"] == "Credit"
    assert header["paid"] == 0.0
    assert header["remaining"] == 150.0
    assert header["payment_status"] == "unpaid"
    assert ("increase_supplier_balance", 1, 150.0) in repo.calls
    debt_call = next(call for call in repo.calls if call[0] == "record_supplier_purchase_debt")
    assert debt_call[5] == 150.0
    assert "record_supplier_payment" not in call_names(repo)


def test_create_partial_purchase_records_debt_and_direct_payment():
    repo = FakePurchaseRepository()
    use_case = CreatePurchaseInvoiceUseCase(repo)

    use_case.execute(1, 2, 3, "", purchase_items(), 0, 0, 0, 0, 50, "Cash")

    header = next(call[1] for call in repo.calls if call[0] == "create_purchase_invoice_header")
    assert header["payment_status"] == "partial"
    assert header["paid"] == 50.0
    assert header["remaining"] == 100.0
    assert ("increase_supplier_balance", 1, 100.0) in repo.calls
    assert "record_supplier_payment" in call_names(repo)


def test_create_purchase_rejects_invalid_header_or_items_without_transaction():
    repo = FakePurchaseRepository()
    use_case = CreatePurchaseInvoiceUseCase(repo)

    with pytest.raises(PurchaseValidationError, match="يجب اختيار المورد"):
        use_case.execute(None, 2, 3, "", purchase_items(), 0, 0, 0, 0, 0, "Cash")

    with pytest.raises(PurchaseValidationError, match="الفاتورة فارغة"):
        use_case.execute(1, 2, 3, "", [], 0, 0, 0, 0, 0, "Cash")

    assert repo.committed is False
    assert repo.rolled_back is False
    assert "create_purchase_invoice_header" not in call_names(repo)


def test_create_purchase_rolls_back_on_repository_failure():
    repo = FakePurchaseRepository()
    repo.raise_on_insert_item = RuntimeError("insert failed")
    use_case = CreatePurchaseInvoiceUseCase(repo)

    invoice = use_case.execute(1, 2, 3, "", purchase_items(), 0, 0, 0, 0, 0, "Cash")

    assert invoice is None
    assert repo.committed is False
    assert repo.rolled_back is True
    assert "rollback" in call_names(repo)


def test_pay_purchase_invoice_updates_status_and_records_payment():
    repo = FakePurchaseRepository()
    use_case = PayPurchaseInvoiceUseCase(repo)

    result = use_case.execute(99, 30, "تحويل", user_id=3, store_id=2)

    assert result is True
    assert repo.committed is True
    assert ("update_purchase_invoice_payment_state", 99, 50.0, 50.0, "partial", "Bank Transfer") in repo.calls
    assert ("decrease_supplier_balance", 1, 30.0) in repo.calls
    payment_call = next(call for call in repo.calls if call[0] == "record_supplier_payment")
    assert payment_call[5] == 30.0
    assert payment_call[6] == "Bank Transfer"
    assert payment_call[8] is False


def test_pay_purchase_invoice_rejects_invalid_amounts():
    repo = FakePurchaseRepository()
    use_case = PayPurchaseInvoiceUseCase(repo)

    with pytest.raises(PurchaseValidationError, match="قيمة السداد"):
        use_case.execute(99, 0, "Cash", 3, 2)

    with pytest.raises(PurchaseValidationError, match="أكبر من المتبقي"):
        use_case.execute(99, 100, "Cash", 3, 2)

    assert repo.committed is False
    assert repo.rolled_back is False


def test_supplier_payment_use_case_records_general_payment():
    repo = FakePurchaseRepository()
    use_case = SupplierPaymentUseCase(repo)

    assert use_case.execute(1, 25, store_id=2, user_id=7) is True
    assert ("decrease_supplier_balance", 1, 25.0) in repo.calls
    assert ("allocate_supplier_payment", 1, 25.0) in repo.calls
    payment_call = next(call for call in repo.calls if call[0] == "record_supplier_payment")
    assert payment_call[8] is True
    assert repo.committed is True


def test_simple_purchase_queries_delegate_to_repository():
    repo = FakePurchaseRepository()

    assert ListSuppliersUseCase(repo).execute() == [repo.supplier]
    assert AddSupplierUseCase(repo).execute(" مورد جديد ", "010", "عنوان", "TX", 0) is True
    assert SearchPurchaseProductUseCase(repo).execute("منتج") == repo.product
    assert SearchPurchaseProductUseCase(repo).execute("") is None
    assert PurchaseHistoryUseCase(repo).execute() == [repo.invoice]


def test_purchase_invoice_details_validates_and_delegates_to_repository():
    repo = FakePurchaseRepository()
    use_case = PurchaseInvoiceDetailsUseCase(repo)

    assert use_case.execute(" PUR-99 ") == repo.invoice_details
    assert ("get_purchase_invoice_details", "PUR-99") in repo.calls

    with pytest.raises(PurchaseValidationError):
        use_case.execute("")
    with pytest.raises(PurchaseValidationError):
        use_case.execute("missing")


def test_update_supplier_and_soft_delete_supplier_use_cases():
    repo = FakePurchaseRepository()

    assert UpdateSupplierUseCase(repo).execute(1, " مورد معدل ", "010", "عنوان", "TX") is True
    assert ("update_supplier", 1, "مورد معدل", "010", "عنوان", "TX") in repo.calls

    assert SoftDeleteSupplierUseCase(repo).execute(1) is True
    assert ("soft_delete_supplier", 1) in repo.calls

    repo.supplier["current_balance"] = 10
    with pytest.raises(ValueError, match="رصيد"):
        SoftDeleteSupplierUseCase(repo).execute(1)


def test_create_purchase_return_credit_decreases_stock_and_supplier_balance():
    repo = FakePurchaseRepository()
    use_case = CreatePurchaseReturnUseCase(repo)

    result = use_case.execute(
        invoice_id=99,
        supplier_id=1,
        store_id=2,
        user_id=3,
        items=[{"product_id": 10, "product_name": "منتج", "quantity": 2, "unit_cost": 30}],
        settlement_method="credit",
        reason="تالف",
    )

    assert result["id"] == 77
    assert result["return_number"] == "PR-000077"
    assert result["total_amount"] == 60.0
    assert ("create_purchase_return_header", 99, 1, 2, 3, 60.0, "credit", "تالف") in repo.calls
    assert ("insert_purchase_return_item", 77, 10, 2, 30.0) in repo.calls
    assert ("decrease_inventory_quantity", 10, 2, 2) in repo.calls
    assert ("reconcile_purchase_return_credits", 99) in repo.calls
    assert ("sync_supplier_balance_from_open_invoices", 1) in repo.calls
    assert "record_supplier_purchase_return_credit" in call_names(repo)
    assert "record_purchase_return_cash_refund" not in call_names(repo)
    assert repo.committed is True


def test_create_purchase_return_cash_refund_records_treasury_without_supplier_balance():
    repo = FakePurchaseRepository()
    use_case = CreatePurchaseReturnUseCase(repo)

    result = use_case.execute(
        99,
        1,
        2,
        3,
        [{"product_id": 10, "product_name": "منتج", "return_quantity": 1, "unit_cost": 30}],
        "cash_refund",
    )

    assert result["total_amount"] == 30.0
    assert "record_purchase_return_cash_refund" in call_names(repo)
    assert "decrease_supplier_balance" not in call_names(repo)
    assert "reconcile_purchase_return_credits" not in call_names(repo)
    assert repo.committed is True


def test_purchase_history_reconciles_stale_purchase_return_credits_before_loading():
    repo = FakePurchaseRepository()

    assert PurchaseHistoryUseCase(repo).execute(page=2, per_page=25) == [repo.invoice]

    assert ("reconcile_purchase_return_credits", None) in repo.calls
    assert ("get_purchase_history", 2, 25) in repo.calls
    assert ("commit",) in repo.calls


def test_create_purchase_return_rejects_quantity_over_invoice_remaining():
    repo = FakePurchaseRepository()
    repo.remaining_purchase_quantity = 1
    use_case = CreatePurchaseReturnUseCase(repo)

    with pytest.raises(PurchaseValidationError):
        use_case.execute(99, 1, 2, 3, [{"product_id": 10, "quantity": 2, "unit_cost": 30}], "credit")

    assert repo.rolled_back is True
    assert repo.committed is False
    assert "create_purchase_return_header" not in call_names(repo)


def test_create_purchase_return_rejects_quantity_over_branch_stock():
    repo = FakePurchaseRepository()
    repo.inventory_quantity = 1
    use_case = CreatePurchaseReturnUseCase(repo)

    with pytest.raises(PurchaseValidationError):
        use_case.execute(99, 1, 2, 3, [{"product_id": 10, "quantity": 2, "unit_cost": 30}], "credit")

    assert repo.rolled_back is True
    assert repo.committed is False
    assert "create_purchase_return_header" not in call_names(repo)

