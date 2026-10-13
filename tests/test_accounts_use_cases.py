import pytest

from application.errors import AccountsValidationError, PromotionCatalogError
from application.use_cases.accounts import (
    ADD_EXPENSE_ACTION,
    RECORD_PAYMENT_ACTION,
    RECORD_SETTLEMENT_ACTION,
    RECORD_TREASURY_ACTION,
    UPDATE_CREDIT_LIMIT_ACTION,
    VOID_EXPENSE_ACTION,
    AccountsQueryUseCase,
    CreatePromotionsCatalogUseCase,
    ExpenseUseCase,
    PromotionsUseCase,
    RecordAccountPaymentUseCase,
    RecordSettlementUseCase,
    TreasuryTransactionUseCase,
    UpdateCreditLimitUseCase,
)


class FakeAudit:
    def __init__(self):
        self.entries = []

    def log(self, user_id, action, entity_type="", entity_id=None, store_id=None, success=True, details=None):
        self.entries.append(
            {
                "user_id": user_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "store_id": store_id,
                "success": success,
                "details": details or {},
            }
        )


class FakeAccountsRepository:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.account = {"id": 1, "name": "حساب", "phone": "010"}
        self.user_store_id = 3
        self.ledger_id = 77
        self.treasury_id = 88
        self.expense = {"id": 11, "store_id": 3, "amount": 50.0, "is_voided": 0}
        self.raise_on_update_balance = None
        self.raise_on_expense = None
        self.raise_on_promotion = None
        self.promotion_margin_products = []
        self.current_promotion = {}

    def get_customer_accounts(self):
        self.calls.append(("get_customer_accounts",))
        return [{"id": 1}]

    def get_all_suppliers(self):
        self.calls.append(("get_all_suppliers",))
        return [{"id": 2}]

    def get_account_history(self, account_type, account_id):
        self.calls.append(("get_account_history", account_type, account_id))
        return [{"account_id": account_id}]

    def get_financial_ledger(self, search="", acc_type=""):
        self.calls.append(("get_financial_ledger", search, acc_type))
        return [{"id": 1}]

    def get_debt_totals(self):
        self.calls.append(("get_debt_totals",))
        return {"customers": 10, "suppliers": 20}

    def get_debt_aging_report(self):
        self.calls.append(("get_debt_aging_report",))
        return [{"age": "30"}]

    def get_treasury_transactions(self):
        self.calls.append(("get_treasury_transactions",))
        return [{"id": 1}]

    def get_treasury_balance(self):
        self.calls.append(("get_treasury_balance",))
        return 100.0

    def get_expenses(self, store_id):
        self.calls.append(("get_expenses", store_id))
        return [self.expense]

    def get_financial_report(self, store_id, start_date, end_date):
        self.calls.append(("get_financial_report", store_id, start_date, end_date))
        return {"store_id": store_id}

    def get_all_stores(self):
        self.calls.append(("get_all_stores",))
        return [{"id": 3}]

    def get_account_snapshot(self, account_type, account_id):
        self.calls.append(("get_account_snapshot", account_type, account_id))
        return self.account if account_id == 1 else None

    def update_account_balance(self, account_type, account_id, delta):
        self.calls.append(("update_account_balance", account_type, account_id, delta))
        if self.raise_on_update_balance:
            raise self.raise_on_update_balance

    def update_customer_credit_limit(self, customer_id, limit):
        self.calls.append(("update_customer_credit_limit", customer_id, limit))

    def get_user_store_id(self, user_id):
        self.calls.append(("get_user_store_id", user_id))
        return self.user_store_id

    def insert_treasury_entry(self, store_id, transaction_type, amount, source_type, reference_id, description, user_id):
        self.calls.append(("insert_treasury_entry", store_id, transaction_type, amount, source_type, reference_id, description, user_id))
        return self.treasury_id

    def insert_ledger_entry(
        self,
        account_type,
        account_id,
        transaction_type,
        amount,
        reference_type,
        description,
        user_id,
        reference_id=None,
        attachment_path="",
        is_settlement=False,
    ):
        self.calls.append(
            (
                "insert_ledger_entry",
                account_type,
                account_id,
                transaction_type,
                amount,
                reference_type,
                description,
                user_id,
                reference_id,
                attachment_path,
                is_settlement,
            )
        )
        return self.ledger_id

    def allocate_supplier_payment(self, supplier_id, amount):
        self.calls.append(("allocate_supplier_payment", supplier_id, amount))

    def insert_expense(self, store_id, user_id, expense_type, amount, description, is_personal):
        self.calls.append(("insert_expense", store_id, user_id, expense_type, amount, description, is_personal))
        if self.raise_on_expense:
            raise self.raise_on_expense
        return 11

    def get_expense(self, expense_id):
        self.calls.append(("get_expense", expense_id))
        return self.expense if expense_id == self.expense["id"] else None

    def mark_expense_voided(self, expense_id, user_id, reason):
        self.calls.append(("mark_expense_voided", expense_id, user_id, reason))

    def get_promotion_categories(self):
        self.calls.append(("get_promotion_categories",))
        return [{"id": 1}]

    def search_promotion_products(self, term=""):
        self.calls.append(("search_promotion_products", term))
        return [{"id": 10}]

    def get_all_promotions(self):
        self.calls.append(("get_all_promotions",))
        return [{"id": 5}]

    def get_promotion_by_id(self, promo_id):
        self.calls.append(("get_promotion_by_id", promo_id))
        return self.current_promotion

    def get_promotion_margin_products(self, apply_to, apply_to_id=None):
        self.calls.append(("get_promotion_margin_products", apply_to, apply_to_id))
        return self.promotion_margin_products

    def insert_promotion(self, **kwargs):
        self.calls.append(("insert_promotion", kwargs))
        if self.raise_on_promotion:
            raise self.raise_on_promotion
        return 5

    def update_promotion_record(self, promo_id, fields):
        self.calls.append(("update_promotion_record", promo_id, fields))

    def toggle_promotion_active(self, promo_id):
        self.calls.append(("toggle_promotion_active", promo_id))

    def delete_promotion_record(self, promo_id):
        self.calls.append(("delete_promotion_record", promo_id))

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


class FakeCatalogService:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = result or {"path": "catalog.pdf"}
        self.error = error

    def create_pdf(self, download_missing_images=True, refresh_images=True):
        self.calls.append(("create_pdf", download_missing_images, refresh_images))
        if self.error:
            raise self.error
        return self.result


def call_names(repo):
    return [call[0] for call in repo.calls]


def test_accounts_query_use_case_delegates_all_read_operations():
    repo = FakeAccountsRepository()
    query = AccountsQueryUseCase(repo)

    assert query.get_customer_accounts() == [{"id": 1}]
    assert query.get_all_suppliers() == [{"id": 2}]
    assert query.get_account_history("Customer", 1) == [{"account_id": 1}]
    assert query.get_financial_ledger("x", "Customer") == [{"id": 1}]
    assert query.get_debt_totals() == {"customers": 10, "suppliers": 20}
    assert query.get_debt_aging_report() == [{"age": "30"}]
    assert query.get_treasury_transactions() == [{"id": 1}]
    assert query.get_treasury_balance() == 100.0
    assert query.get_expenses(3) == [repo.expense]
    assert query.get_financial_report(3, "2026-01-01", "2026-12-31") == {"store_id": 3}
    assert query.get_all_stores() == [{"id": 3}]


def test_record_customer_payment_updates_balance_ledger_treasury_and_audit():
    repo = FakeAccountsRepository()
    audit = FakeAudit()
    use_case = RecordAccountPaymentUseCase(repo, audit)

    assert use_case.execute("Customer", 1, 25, 7, "", "file.pdf") is True
    assert ("update_account_balance", "Customer", 1, -25.0) in repo.calls
    assert ("insert_treasury_entry", 3, "In", 25.0, "Settlement", 77, "تحصيل من العميل حساب", 7) in repo.calls
    ledger_call = next(call for call in repo.calls if call[0] == "insert_ledger_entry")
    assert ledger_call[3] == "Debit"
    assert ledger_call[5] == "Payment"
    assert ledger_call[9] == "file.pdf"
    assert repo.committed is True
    assert audit.entries[0]["action"] == RECORD_PAYMENT_ACTION


def test_record_supplier_payment_allocates_supplier_and_uses_out_treasury():
    repo = FakeAccountsRepository()
    audit = FakeAudit()

    assert RecordAccountPaymentUseCase(repo, audit).execute("Supplier", 1, 30, 7, "سداد") is True
    assert ("allocate_supplier_payment", 1, 30.0) in repo.calls
    treasury_call = next(call for call in repo.calls if call[0] == "insert_treasury_entry")
    assert treasury_call[2] == "Out"


def test_record_payment_validation_and_rollback_on_failure():
    repo = FakeAccountsRepository()
    audit = FakeAudit()
    use_case = RecordAccountPaymentUseCase(repo, audit)

    with pytest.raises(AccountsValidationError, match="نوع الحساب"):
        use_case.execute("Bad", 1, 10, 7, "")
    with pytest.raises(AccountsValidationError, match="أكبر من صفر"):
        use_case.execute("Customer", 1, 0, 7, "")

    repo.raise_on_update_balance = RuntimeError("db error")
    assert use_case.execute("Customer", 1, 10, 7, "") is False
    assert repo.rolled_back is True


def test_credit_limit_settlement_and_treasury_transactions():
    repo = FakeAccountsRepository()
    audit = FakeAudit()

    assert UpdateCreditLimitUseCase(repo, audit).execute(1, 500, user_id=7) is True
    assert ("update_customer_credit_limit", 1, 500.0) in repo.calls
    assert audit.entries[-1]["action"] == UPDATE_CREDIT_LIMIT_ACTION

    assert RecordSettlementUseCase(repo, audit).execute("Supplier", 1, 15, "", 7) is True
    assert ("allocate_supplier_payment", 1, 15.0) in repo.calls
    treasury_call = [call for call in repo.calls if call[0] == "insert_treasury_entry"][-1]
    assert treasury_call[2] == "Out"
    assert treasury_call[3] == 15.0
    assert treasury_call[4] == "Settlement"
    settlement_ledger = [call for call in repo.calls if call[0] == "insert_ledger_entry"][-1]
    assert settlement_ledger[10] is True
    assert audit.entries[-1]["action"] == RECORD_SETTLEMENT_ACTION

    assert TreasuryTransactionUseCase(repo, audit).execute(3, "In", 20, "", None, "", 7) is True
    treasury_call = [call for call in repo.calls if call[0] == "insert_treasury_entry"][-1]
    assert treasury_call[4] == "Adjustment"
    assert treasury_call[6] == "حركة خزينة يدوية"
    assert audit.entries[-1]["action"] == RECORD_TREASURY_ACTION


def test_expense_add_and_void_create_reverse_entries():
    repo = FakeAccountsRepository()
    audit = FakeAudit()
    use_case = ExpenseUseCase(repo, audit)

    assert use_case.add(3, 7, "نثريات", 50, "شراء أدوات", False) is True
    assert ("insert_expense", 3, 7, "نثريات", 50.0, "شراء أدوات", False) in repo.calls
    assert ("insert_treasury_entry", 3, "Out", 50.0, "Expense", 11, "مصروف: نثريات - شراء أدوات", 7) in repo.calls
    assert audit.entries[-1]["action"] == ADD_EXPENSE_ACTION

    assert use_case.void(11, user_id=7, reason="خطأ") is True
    assert ("mark_expense_voided", 11, 7, "خطأ") in repo.calls
    reverse_treasury = [call for call in repo.calls if call[0] == "insert_treasury_entry"][-1]
    assert reverse_treasury[2] == "In"
    assert reverse_treasury[4] == "Adjustment"
    assert audit.entries[-1]["action"] == VOID_EXPENSE_ACTION


def test_expense_validation_and_void_guards():
    repo = FakeAccountsRepository()
    audit = FakeAudit()
    use_case = ExpenseUseCase(repo, audit)

    with pytest.raises(AccountsValidationError, match="نوع المصروف"):
        use_case.add(3, 7, "", 10, "", False)
    with pytest.raises(AccountsValidationError, match="المبلغ"):
        use_case.add(3, 7, "نثريات", 0, "", False)
    with pytest.raises(AccountsValidationError, match="غير موجود"):
        use_case.void(999, 7)

    repo.expense["is_voided"] = 1
    with pytest.raises(AccountsValidationError, match="ملغى بالفعل"):
        use_case.void(11, 7)


def promotion_payload(**overrides):
    data = {
        "name": "عرض",
        "promo_type": "percentage",
        "value": 10,
        "min_quantity": 1,
        "buy_quantity": 0,
        "apply_to": "all",
        "apply_to_id": None,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
    data.update(overrides)
    return data


def test_promotions_crud_validates_payload_and_commits():
    repo = FakeAccountsRepository()
    use_case = PromotionsUseCase(repo)

    assert use_case.get_categories() == [{"id": 1}]
    assert use_case.search_products("p") == [{"id": 10}]
    assert use_case.list() == [{"id": 5}]
    assert use_case.add(**promotion_payload(extra="ignored")) is True
    insert_call = next(call for call in repo.calls if call[0] == "insert_promotion")
    assert "extra" not in insert_call[1]
    assert insert_call[1]["value"] == 10.0

    assert use_case.update(5, name=" عرض جديد ", value=5, extra="ignored") is True
    update_call = next(call for call in repo.calls if call[0] == "update_promotion_record")
    assert update_call[2] == {"name": "عرض جديد", "value": 5.0}
    assert use_case.update(5, extra="ignored") is True
    assert use_case.toggle(5) is True
    assert use_case.delete(5) is True
    assert use_case.toggle(None) is False
    assert use_case.delete(None) is False


def test_promotions_invalid_payload_rolls_back_and_returns_false():
    repo = FakeAccountsRepository()
    use_case = PromotionsUseCase(repo)

    assert use_case.add(**promotion_payload(name="")) is False
    assert repo.rolled_back is True

    repo.rolled_back = False
    assert use_case.add(**promotion_payload(value=0)) is False
    assert repo.rolled_back is True

    repo.rolled_back = False
    assert use_case.add(**promotion_payload(apply_to="bad")) is False
    assert repo.rolled_back is True


def test_company_funded_promotion_that_breaks_minimum_margin_is_rejected():
    repo = FakeAccountsRepository()
    repo.promotion_margin_products = [
        {"id": 10, "product_name": "منتج", "buy_price": 180, "sell_price": 217.25}
    ]
    use_case = PromotionsUseCase(repo)

    result = use_case.add(
        **promotion_payload(
            promo_type="buy_x_get_y",
            value=1,
            buy_quantity=4,
            funding_source="company",
            minimum_margin_percent=5,
        )
    )

    assert result is False
    assert "السبب" in use_case.last_error
    assert "العجز" in use_case.last_error
    assert "هامش 5%" in use_case.last_error
    assert "insert_promotion" not in call_names(repo)
    assert repo.rolled_back is True


def test_supplier_funded_promotion_uses_supplier_claim_for_margin_guard():
    repo = FakeAccountsRepository()
    repo.promotion_margin_products = [
        {"id": 10, "product_name": "منتج", "buy_price": 180, "sell_price": 217.25}
    ]
    use_case = PromotionsUseCase(repo)

    result = use_case.add(
        **promotion_payload(
            promo_type="buy_x_get_y",
            value=1,
            buy_quantity=4,
            funding_source="supplier",
            supplier_id=3,
            minimum_margin_percent=5,
        )
    )

    assert result is True
    assert "insert_promotion" in call_names(repo)


def test_promotions_catalog_returns_result_none_or_reraises_business_error():
    service = FakeCatalogService(result={"path": "catalog.pdf"})
    assert CreatePromotionsCatalogUseCase(service).execute(False, False) == {"path": "catalog.pdf"}
    assert service.calls == [("create_pdf", False, False)]

    assert CreatePromotionsCatalogUseCase(FakeCatalogService(error=RuntimeError("boom"))).execute() is None

    with pytest.raises(PromotionCatalogError):
        CreatePromotionsCatalogUseCase(FakeCatalogService(error=PromotionCatalogError("لا توجد عروض"))).execute()
