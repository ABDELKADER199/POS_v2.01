import pytest

from application.errors import AccountsValidationError
from application.services.accounts_service_facade import AccountsServiceFacade
from application.use_cases.accounts import (
    ADD_EXPENSE_ACTION,
    RECORD_SETTLEMENT_ACTION,
    RECORD_TREASURY_ACTION,
    UPDATE_CREDIT_LIMIT_ACTION,
    VOID_EXPENSE_ACTION,
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
        self.account = {"id": 1, "name": "حساب", "phone": "010"}
        self.user_store_id = 2
        self.ledger_id = 70
        self.treasury_id = 80
        self.expense_id = 90
        self.expense = {"id": 90, "store_id": 2, "amount": 45, "is_voided": 0}
        self.committed = False
        self.rolled_back = False
        self.raise_on_credit_limit = None
        self.raise_on_balance = None
        self.raise_on_treasury = None
        self.raise_on_expense = None
        self.raise_on_void = None
        self.raise_on_promotion = None

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
        return {"customers": 10}

    def get_debt_aging_report(self):
        self.calls.append(("get_debt_aging_report",))
        return [{"bucket": "30"}]

    def get_treasury_transactions(self):
        self.calls.append(("get_treasury_transactions",))
        return [{"id": 1}]

    def get_treasury_balance(self):
        self.calls.append(("get_treasury_balance",))
        return 100

    def get_expenses(self, store_id):
        self.calls.append(("get_expenses", store_id))
        return [self.expense]

    def get_financial_report(self, store_id, start_date, end_date):
        self.calls.append(("get_financial_report", store_id, start_date, end_date))
        return {"store_id": store_id}

    def get_all_stores(self):
        self.calls.append(("get_all_stores",))
        return [{"id": 2}]

    def get_account_snapshot(self, account_type, account_id):
        self.calls.append(("get_account_snapshot", account_type, account_id))
        return self.account if account_id == 1 else None

    def update_account_balance(self, account_type, account_id, delta):
        self.calls.append(("update_account_balance", account_type, account_id, delta))
        if self.raise_on_balance:
            raise self.raise_on_balance

    def update_customer_credit_limit(self, customer_id, limit):
        self.calls.append(("update_customer_credit_limit", customer_id, limit))
        if self.raise_on_credit_limit:
            raise self.raise_on_credit_limit

    def get_user_store_id(self, user_id):
        self.calls.append(("get_user_store_id", user_id))
        return self.user_store_id

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

    def insert_treasury_entry(self, store_id, transaction_type, amount, source_type, reference_id, description, user_id):
        self.calls.append(
            ("insert_treasury_entry", store_id, transaction_type, amount, source_type, reference_id, description, user_id)
        )
        if self.raise_on_treasury:
            raise self.raise_on_treasury
        return self.treasury_id

    def allocate_supplier_payment(self, supplier_id, amount):
        self.calls.append(("allocate_supplier_payment", supplier_id, amount))

    def update_promotion_record(self, promo_id, fields):
        self.calls.append(("update_promotion_record", promo_id, fields))
        if self.raise_on_promotion:
            raise self.raise_on_promotion

    def toggle_promotion_active(self, promo_id):
        self.calls.append(("toggle_promotion_active", promo_id))
        if self.raise_on_promotion:
            raise self.raise_on_promotion

    def delete_promotion_record(self, promo_id):
        self.calls.append(("delete_promotion_record", promo_id))
        if self.raise_on_promotion:
            raise self.raise_on_promotion

    def insert_promotion(self, **kwargs):
        self.calls.append(("insert_promotion", kwargs))
        if self.raise_on_promotion:
            raise self.raise_on_promotion
        return 5

    def get_promotion_categories(self):
        self.calls.append(("get_promotion_categories",))
        return [{"id": 1}]

    def search_promotion_products(self, term=""):
        self.calls.append(("search_promotion_products", term))
        return [{"id": 10}]

    def get_all_promotions(self):
        self.calls.append(("get_all_promotions",))
        return [{"id": 5}]

    def insert_expense(self, store_id, user_id, expense_type, amount, description, is_personal):
        self.calls.append(("insert_expense", store_id, user_id, expense_type, amount, description, is_personal))
        if self.raise_on_expense:
            raise self.raise_on_expense
        return self.expense_id

    def get_expense(self, expense_id):
        self.calls.append(("get_expense", expense_id))
        return self.expense if expense_id == self.expense_id else None

    def mark_expense_voided(self, expense_id, user_id, reason):
        self.calls.append(("mark_expense_voided", expense_id, user_id, reason))
        if self.raise_on_void:
            raise self.raise_on_void

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def promotion_payload(**overrides):
    data = {
        "name": "عرض",
        "promo_type": "fixed",
        "value": 5,
        "min_quantity": 1,
        "buy_quantity": 0,
        "apply_to": "all",
        "apply_to_id": None,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
    data.update(overrides)
    return data


def test_payment_validation_guards_missing_account_user_and_snapshot():
    repo = FakeAccountsRepository()
    use_case = RecordAccountPaymentUseCase(repo, FakeAudit())

    with pytest.raises(AccountsValidationError):
        use_case.execute("Customer", 0, 10, 7, "")
    with pytest.raises(AccountsValidationError):
        use_case.execute("Customer", 1, 10, 0, "")
    with pytest.raises(AccountsValidationError):
        use_case.execute("Customer", 999, 10, 7, "")


def test_credit_limit_validates_negative_and_rolls_back_on_failure():
    repo = FakeAccountsRepository()
    audit = FakeAudit()
    use_case = UpdateCreditLimitUseCase(repo, audit)

    with pytest.raises(AccountsValidationError):
        use_case.execute(1, -1)

    repo.raise_on_credit_limit = RuntimeError("credit failed")
    assert use_case.execute(1, 100, user_id=7) is False
    assert repo.rolled_back is True
    assert audit.entries == []


def test_credit_limit_uses_default_user_id_when_missing():
    repo = FakeAccountsRepository()
    audit = FakeAudit()

    assert UpdateCreditLimitUseCase(repo, audit).execute(1, 100) is True

    assert audit.entries[-1]["user_id"] == 1
    assert audit.entries[-1]["action"] == UPDATE_CREDIT_LIMIT_ACTION


def test_customer_settlement_does_not_allocate_supplier_payment_and_keeps_attachment():
    repo = FakeAccountsRepository()
    audit = FakeAudit()

    assert RecordSettlementUseCase(repo, audit).execute("Customer", 1, "12.345", "تسوية", 7, "settle.pdf") is True

    assert ("update_account_balance", "Customer", 1, -12.35) in repo.calls
    assert not any(call[0] == "allocate_supplier_payment" for call in repo.calls)
    ledger_call = next(call for call in repo.calls if call[0] == "insert_ledger_entry")
    assert ledger_call[9] == "settle.pdf"
    assert ledger_call[10] is True
    assert audit.entries[-1]["action"] == RECORD_SETTLEMENT_ACTION


def test_settlement_validation_and_rollback_on_failure():
    repo = FakeAccountsRepository()
    use_case = RecordSettlementUseCase(repo, FakeAudit())

    with pytest.raises(AccountsValidationError):
        use_case.execute("Bad", 1, 10, "", 7)
    with pytest.raises(AccountsValidationError):
        use_case.execute("Customer", 1, 0, "", 7)

    repo.raise_on_balance = RuntimeError("balance failed")
    assert use_case.execute("Customer", 1, 10, "", 7) is False
    assert repo.rolled_back is True


def test_treasury_transaction_validation_guards():
    use_case = TreasuryTransactionUseCase(FakeAccountsRepository(), FakeAudit())

    with pytest.raises(AccountsValidationError):
        use_case.execute(0, "In", 10, "", None, "", 7)
    with pytest.raises(AccountsValidationError):
        use_case.execute(1, "In", 10, "", None, "", 0)
    with pytest.raises(AccountsValidationError):
        use_case.execute(1, "Bad", 10, "", None, "", 7)
    with pytest.raises(AccountsValidationError):
        use_case.execute(1, "In", 0, "", None, "", 7)


def test_treasury_transaction_trims_values_and_rolls_back_on_failure():
    repo = FakeAccountsRepository()
    audit = FakeAudit()

    assert TreasuryTransactionUseCase(repo, audit).execute(2, " Out ", "10.239", " Manual ", 5, " سبب ", 7) is True
    assert ("insert_treasury_entry", 2, "Out", 10.24, "Manual", 5, "سبب", 7) in repo.calls
    assert audit.entries[-1]["action"] == RECORD_TREASURY_ACTION

    repo = FakeAccountsRepository()
    repo.raise_on_treasury = RuntimeError("treasury failed")
    assert TreasuryTransactionUseCase(repo, FakeAudit()).execute(2, "In", 10, "", None, "", 7) is False
    assert repo.rolled_back is True


def test_expense_add_validation_and_rollback_on_failure():
    use_case = ExpenseUseCase(FakeAccountsRepository(), FakeAudit())

    with pytest.raises(AccountsValidationError):
        use_case.add(0, 7, "مصروف", 10, "", False)
    with pytest.raises(AccountsValidationError):
        use_case.add(2, 0, "مصروف", 10, "", False)

    repo = FakeAccountsRepository()
    repo.raise_on_expense = RuntimeError("expense failed")
    assert ExpenseUseCase(repo, FakeAudit()).add(2, 7, "مصروف", 10, "", True) is False
    assert repo.rolled_back is True


def test_expense_void_defaults_user_and_reason_and_rolls_back_on_failure():
    repo = FakeAccountsRepository()
    audit = FakeAudit()

    assert ExpenseUseCase(repo, audit).void(90) is True

    assert ("mark_expense_voided", 90, 1, "إلغاء مصروف") in repo.calls
    assert audit.entries[-1]["user_id"] == 1
    assert audit.entries[-1]["action"] == VOID_EXPENSE_ACTION

    repo = FakeAccountsRepository()
    repo.raise_on_void = RuntimeError("void failed")
    assert ExpenseUseCase(repo, FakeAudit()).void(90, user_id=7, reason="خطأ") is False
    assert repo.rolled_back is True


def test_promotions_failure_paths_roll_back_and_return_false():
    repo = FakeAccountsRepository()
    repo.raise_on_promotion = RuntimeError("promotion failed")
    use_case = PromotionsUseCase(repo)

    assert use_case.add(**promotion_payload()) is False
    assert use_case.update(5, name="عرض") is False
    assert use_case.toggle(5) is False
    assert use_case.delete(5) is False
    assert repo.rolled_back is True


def test_promotions_update_with_no_allowed_fields_is_noop_without_commit():
    repo = FakeAccountsRepository()

    assert PromotionsUseCase(repo).update(5, ignored="value") is True

    assert repo.calls == []
    assert repo.committed is False
    assert repo.rolled_back is False


def test_promotions_validate_missing_required_and_negative_quantities():
    use_case = PromotionsUseCase(FakeAccountsRepository())

    assert use_case.add(name="عرض") is False
    assert use_case.add(**promotion_payload(min_quantity=-1)) is False
    assert use_case.add(**promotion_payload(buy_quantity=-1)) is False


def test_accounts_service_facade_delegates_financial_operations():
    repo = FakeAccountsRepository()
    audit = FakeAudit()
    service = AccountsServiceFacade(repo, audit)

    service.promotions_catalog_use_case = None

    assert service.get_customer_accounts() == [{"id": 1}]
    assert service.get_all_suppliers() == [{"id": 2}]
    assert service.get_account_history("Customer", 1) == [{"account_id": 1}]
    assert service.get_financial_ledger("x", "Customer") == [{"id": 1}]
    assert service.get_debt_totals() == {"customers": 10}
    assert service.get_treasury_balance() == 100
    assert service.record_payment("Customer", 1, 10, 7, "سداد") is True
    assert service.record_settlement("Customer", 1, 5, "تسوية", 7) is True
    assert service.record_treasury_transaction(2, "In", 3, "", None, "", 7) is True
    assert service.add_expense(2, 7, "مصروف", 4, "", False) is True
    assert service.delete_expense(90, 7, "خطأ") is True
    assert service.get_promotion_categories() == [{"id": 1}]
    assert service.search_promotion_products("p") == [{"id": 10}]
    assert service.get_all_promotions() == [{"id": 5}]
    assert service.add_promotion(**promotion_payload()) is True
    assert service.update_promotion(5, name="عرض جديد") is True
    assert service.toggle_promotion(5) is True
    assert service.delete_promotion(5) is True
    assert service.get_all_stores() == [{"id": 2}]
    assert any(entry["action"] == ADD_EXPENSE_ACTION for entry in audit.entries)
