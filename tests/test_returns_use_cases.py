from application.use_cases.returns import (
    ProcessReturnUseCase,
    ReturnInvoiceQueryUseCase,
    ReturnsDrawerQueryUseCase,
    ReturnsHistoryUseCase,
)


class FakeReturnsRepository:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.invoice = {
            "id": 1,
            "invoice_number": "INV-1",
            "status": "Completed",
            "payment_method": "Cash",
            "cash_amount": 100.0,
            "remaining_amount": 0.0,
            "customer_id": None,
            "store_id": 3,
        }
        self.invoice_items = [
            {
                "product_id": 10,
                "product_name": "منتج",
                "quantity": 3,
                "returned_quantity": 0,
                "unit_price": 25.0,
                "buy_price": 10.0,
            }
        ]
        self.return_id = 99

    def get_invoice_by_number(self, invoice_number):
        self.calls.append(("get_invoice_by_number", invoice_number))
        return (
            self.invoice if invoice_number == self.invoice["invoice_number"] else None
        )

    def get_invoice_items(self, invoice_id):
        self.calls.append(("get_invoice_items", invoice_id))
        return self.invoice_items

    def get_invoice_for_return(self, invoice_id):
        self.calls.append(("get_invoice_for_return", invoice_id))
        return self.invoice if invoice_id == self.invoice["id"] else None

    def create_return_header(
        self,
        return_number,
        invoice_id,
        store_id,
        user_id,
        total_return,
        reason,
        drawer_id=None,
    ):
        self.calls.append(
            (
                "create_return_header",
                return_number,
                invoice_id,
                store_id,
                user_id,
                total_return,
                reason,
                drawer_id,
            )
        )
        return self.return_id

    def insert_return_item(self, return_id, item):
        self.calls.append(("insert_return_item", return_id, item))

    def add_inventory_quantity(self, product_id, store_id, quantity):
        self.calls.append(("add_inventory_quantity", product_id, store_id, quantity))

    def record_cash_refund(
        self, store_id, amount, return_id, invoice_number, return_number, user_id
    ):
        self.calls.append(
            (
                "record_cash_refund",
                store_id,
                amount,
                return_id,
                invoice_number,
                return_number,
                user_id,
            )
        )

    def reduce_customer_balance(self, customer_id, amount):
        self.calls.append(("reduce_customer_balance", customer_id, amount))

    def record_customer_return_ledger(
        self, customer_id, amount, return_id, invoice_number, user_id
    ):
        self.calls.append(
            (
                "record_customer_return_ledger",
                customer_id,
                amount,
                return_id,
                invoice_number,
                user_id,
            )
        )

    def get_returns_history(self, **kwargs):
        self.calls.append(("get_returns_history", kwargs))
        return [{"return_number": "RET-1"}]

    def get_drawer_status(self, user_id):
        self.calls.append(("get_drawer_status", user_id))
        return {"cashier_id": user_id}

    def get_store_open_drawer(self, store_id):
        self.calls.append(("get_store_open_drawer", store_id))
        return {"store_id": store_id}

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def call_names(repo):
    return [call[0] for call in repo.calls]


def test_cash_return_restores_inventory_records_refund_and_commits():
    repo = FakeReturnsRepository()
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        invoice_id=1,
        items=[{"product_id": 10, "quantity": 2}],
        reason="خطأ بيع",
        user_id=7,
        store_id=3,
        drawer_id=4,
    )

    assert result is not None
    assert result["return_id"] == 99
    assert result["invoice_number"] == "INV-1"
    assert result["total_amount"] == 50.0
    assert result["cash_refund"] == 50.0
    assert result["credit_adjustment"] == 0.0
    assert repo.committed is True
    assert repo.rolled_back is False
    assert "insert_return_item" in call_names(repo)
    assert ("add_inventory_quantity", 10, 3, 2) in repo.calls

    cash_refund = next(call for call in repo.calls if call[0] == "record_cash_refund")
    assert cash_refund[2] == 50.0
    assert "reduce_customer_balance" not in call_names(repo)


def test_credit_return_reduces_customer_balance_without_cash_refund():
    repo = FakeReturnsRepository()
    repo.invoice.update(
        {
            "payment_method": "Credit",
            "cash_amount": 0.0,
            "remaining_amount": 75.0,
            "customer_id": 22,
        }
    )
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(1, [{"product_id": 10, "quantity": 2}], "مرتجع آجل", 7, 3)

    assert result["total_amount"] == 50.0
    assert result["cash_refund"] == 0.0
    assert result["credit_adjustment"] == 50.0
    assert ("reduce_customer_balance", 22, 50.0) in repo.calls
    ledger_call = next(
        call for call in repo.calls if call[0] == "record_customer_return_ledger"
    )
    assert ledger_call[1] == 22
    assert ledger_call[2] == 50.0
    assert "record_cash_refund" not in call_names(repo)


def test_credit_return_only_adjusts_outstanding_balance():
    repo = FakeReturnsRepository()
    repo.invoice.update(
        {
            "payment_method": "Credit",
            "cash_amount": 0.0,
            "remaining_amount": 25.0,
            "customer_id": 22,
        }
    )
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        1, [{"product_id": 10, "quantity": 2}], "مديونية جزئية", 7, 3
    )

    assert result["total_amount"] == 50.0
    assert result["credit_adjustment"] == 25.0
    assert result["cash_refund"] == 0.0
    assert ("reduce_customer_balance", 22, 25.0) in repo.calls


def test_card_return_does_not_create_cash_refund():
    repo = FakeReturnsRepository()
    repo.invoice.update({"payment_method": "Card", "cash_amount": 0.0})
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        1, [{"product_id": 10, "quantity": 2}], "مرتجع كارت", 7, 3
    )

    assert result["cash_refund"] == 0.0
    assert "record_cash_refund" not in call_names(repo)
    assert repo.committed is True


def test_invalid_return_quantity_rolls_back_and_returns_none():
    repo = FakeReturnsRepository()
    repo.invoice_items[0]["returned_quantity"] = 2
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(1, [{"product_id": 10, "quantity": 2}], "كمية خطأ", 7, 3)

    assert result is None
    assert repo.committed is False
    assert repo.rolled_back is True
    assert "create_return_header" not in call_names(repo)


def test_non_completed_invoice_is_rejected():
    repo = FakeReturnsRepository()
    repo.invoice["status"] = "Cancelled"
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        1, [{"product_id": 10, "quantity": 1}], "فاتورة ملغاة", 7, 3
    )

    assert result is None
    assert repo.rolled_back is True
    assert "create_return_header" not in call_names(repo)


def test_return_rejects_different_store():
    repo = FakeReturnsRepository()
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(1, [{"product_id": 10, "quantity": 1}], "فرع خاطئ", 7, 9)

    assert result is None
    assert "فرع مختلف" in use_case.last_error
    assert repo.rolled_back is True
    assert "create_return_header" not in call_names(repo)


def test_duplicate_product_quantities_are_aggregated_and_authoritative_price_is_used():
    repo = FakeReturnsRepository()
    use_case = ProcessReturnUseCase(repo)

    result = use_case.execute(
        1,
        [
            {"product_id": 10, "quantity": 1, "unit_price": 999},
            {"product_id": 10, "quantity": 1, "unit_price": 999},
        ],
        "تجميع",
        7,
        3,
    )

    assert result["total_amount"] == 50.0
    assert len(result["items"]) == 1
    assert result["items"][0]["quantity"] == 2
    assert result["items"][0]["unit_price"] == 25.0


def test_return_invoice_query_validates_empty_invoice_number():
    repo = FakeReturnsRepository()
    query = ReturnInvoiceQueryUseCase(repo)

    assert query.search_invoice("") is None
    assert repo.calls == []

    assert query.search_invoice("INV-1") == repo.invoice
    assert ("get_invoice_by_number", "INV-1") in repo.calls


def test_history_and_drawer_queries_delegate_safely():
    repo = FakeReturnsRepository()

    assert ReturnsHistoryUseCase(repo).execute(store_id=3) == [
        {"return_number": "RET-1"}
    ]
    drawer_query = ReturnsDrawerQueryUseCase(repo)
    assert drawer_query.get_drawer_status(None) is None
    assert drawer_query.get_store_open_drawer(None) is None
    assert drawer_query.get_drawer_status(7) == {"cashier_id": 7}
    assert drawer_query.get_store_open_drawer(3) == {"store_id": 3}
