from application.use_cases.transfers import (
    CancelTransferUseCase,
    CreateTransferUseCase,
    ListTransfersUseCase,
    ReceiveTransferUseCase,
    TransferProductSearchUseCase,
    TransferStoresUseCase,
)
from utils.permissions import ROLE_ADMIN, ROLE_MANAGER


class FakeTransfersRepository:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.stock = 10
        self.transfer_id = 55
        self.transfer = {
            "id": 55,
            "status": "Pending",
            "product_id": 10,
            "from_store_id": 1,
            "to_store_id": 2,
            "quantity_sent": 4,
        }
        self.raise_on_create_header = None
        self.raise_on_receive = None
        self.raise_on_cancel = None

    def get_stores(self):
        self.calls.append(("get_stores",))
        return [{"id": 1}, {"id": 2}]

    def search_products(self, term, store_id=None, limit=25):
        self.calls.append(("search_products", term, store_id, limit))
        return [{"id": 10, "name": "منتج"}]

    def get_transfers(self, store_id=None, status=None):
        self.calls.append(("get_transfers", store_id, status))
        return [self.transfer]

    def get_stock(self, product_id, store_id):
        self.calls.append(("get_stock", product_id, store_id))
        return self.stock

    def create_transfer_header(self, transfer_number, from_store_id, to_store_id, user_id, notes=""):
        self.calls.append(("create_transfer_header", transfer_number, from_store_id, to_store_id, user_id, notes))
        if self.raise_on_create_header:
            raise self.raise_on_create_header
        return self.transfer_id

    def insert_transfer_item(self, transfer_id, product_id, quantity, notes=""):
        self.calls.append(("insert_transfer_item", transfer_id, product_id, quantity, notes))

    def decrease_inventory(self, product_id, store_id, quantity):
        self.calls.append(("decrease_inventory", product_id, store_id, quantity))

    def increase_inventory(self, product_id, store_id, quantity):
        self.calls.append(("increase_inventory", product_id, store_id, quantity))
        if self.raise_on_receive:
            raise self.raise_on_receive
        if self.raise_on_cancel:
            raise self.raise_on_cancel

    def get_transfer_for_receiving(self, transfer_id):
        self.calls.append(("get_transfer_for_receiving", transfer_id))
        return self.transfer if transfer_id == self.transfer["id"] else None

    def get_transfer_for_cancellation(self, transfer_id):
        self.calls.append(("get_transfer_for_cancellation", transfer_id))
        return self.transfer if transfer_id == self.transfer["id"] else None

    def mark_transfer_received(self, transfer_id, user_id):
        self.calls.append(("mark_transfer_received", transfer_id, user_id))

    def mark_transfer_cancelled(self, transfer_id):
        self.calls.append(("mark_transfer_cancelled", transfer_id))

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def call_names(repo):
    return [call[0] for call in repo.calls]


def test_simple_transfer_queries_delegate_and_validate_search_term():
    repo = FakeTransfersRepository()

    assert TransferStoresUseCase(repo).execute() == [{"id": 1}, {"id": 2}]
    assert TransferProductSearchUseCase(repo).execute("a") == []
    assert TransferProductSearchUseCase(repo).execute("منتج", store_id=1) == [{"id": 10, "name": "منتج"}]
    assert ("search_products", "منتج", 1, 25) in repo.calls


def test_list_transfers_scopes_manager_to_branch_and_admin_to_all():
    repo = FakeTransfersRepository()
    manager = {"role_id": ROLE_MANAGER, "store_id": 3}
    admin = {"role_id": ROLE_ADMIN, "store_id": 3}

    assert ListTransfersUseCase(repo).execute(manager, status="Pending") == [repo.transfer]
    assert ("get_transfers", 3, "Pending") in repo.calls

    ListTransfersUseCase(repo).execute(admin, status="Pending")
    assert ("get_transfers", None, "Pending") in repo.calls


def test_create_transfer_success_decreases_source_inventory_and_commits():
    repo = FakeTransfersRepository()
    use_case = CreateTransferUseCase(repo)

    ok, message = use_case.execute(
        product_id=10,
        from_store_id=1,
        to_store_id=2,
        quantity=4,
        user_id=7,
        notes="طلب فرع",
    )

    assert ok is True
    assert "تم إنشاء التحويل رقم TRF-" in message
    assert repo.committed is True
    assert repo.rolled_back is False
    assert ("get_stock", 10, 1) in repo.calls
    assert ("insert_transfer_item", 55, 10, 4, "طلب فرع") in repo.calls
    assert ("decrease_inventory", 10, 1, 4) in repo.calls
    assert call_names(repo)[-1] == "commit"


def test_create_transfer_rejects_same_store_invalid_quantity_and_insufficient_stock():
    repo = FakeTransfersRepository()
    use_case = CreateTransferUseCase(repo)

    ok, message = use_case.execute(10, 1, 1, 4, 7)
    assert ok is False
    assert "نفس الفرع" in message

    ok, message = use_case.execute(10, 1, 2, 0, 7)
    assert ok is False
    assert "أكبر من صفر" in message

    repo.stock = 3
    ok, message = use_case.execute(10, 1, 2, 4, 7)
    assert ok is False
    assert "أقل من المطلوب" in message

    assert repo.committed is False
    assert repo.rolled_back is False
    assert "create_transfer_header" not in call_names(repo)


def test_create_transfer_rolls_back_on_repository_failure():
    repo = FakeTransfersRepository()
    repo.raise_on_create_header = RuntimeError("db error")
    use_case = CreateTransferUseCase(repo)

    ok, message = use_case.execute(10, 1, 2, 4, 7)

    assert ok is False
    assert "فشل إنشاء التحويل" in message
    assert repo.committed is False
    assert repo.rolled_back is True
    assert "rollback" in call_names(repo)


def test_receive_transfer_success_increases_destination_inventory_and_commits():
    repo = FakeTransfersRepository()
    use_case = ReceiveTransferUseCase(repo)

    ok, message = use_case.execute(55, {"id": 7})

    assert ok is True
    assert "تم استلام التحويل" in message
    assert ("increase_inventory", 10, 2, 4) in repo.calls
    assert ("mark_transfer_received", 55, 7) in repo.calls
    assert repo.committed is True
    assert repo.rolled_back is False


def test_receive_transfer_rejects_missing_received_or_cancelled_transfer_without_transaction():
    repo = FakeTransfersRepository()
    use_case = ReceiveTransferUseCase(repo)

    ok, message = use_case.execute(999, {"id": 7})
    assert ok is False
    assert "غير موجود" in message

    repo.transfer["status"] = "Received"
    ok, message = use_case.execute(55, {"id": 7})
    assert ok is False
    assert "من قبل" in message

    repo.transfer["status"] = "Cancelled"
    ok, message = use_case.execute(55, {"id": 7})
    assert ok is False
    assert "ملغي" in message

    assert repo.committed is False
    assert repo.rolled_back is False
    assert "increase_inventory" not in call_names(repo)


def test_receive_transfer_rolls_back_on_repository_failure():
    repo = FakeTransfersRepository()
    repo.raise_on_receive = RuntimeError("receive failed")
    use_case = ReceiveTransferUseCase(repo)

    ok, message = use_case.execute(55, {"id": 7})

    assert ok is False
    assert "فشل استلام التحويل" in message
    assert repo.committed is False
    assert repo.rolled_back is True


def test_cancel_transfer_success_returns_stock_to_source_and_commits():
    repo = FakeTransfersRepository()
    use_case = CancelTransferUseCase(repo)

    ok, message = use_case.execute(55)

    assert ok is True
    assert "تم إلغاء التحويل" in message
    assert ("increase_inventory", 10, 1, 4) in repo.calls
    assert ("mark_transfer_cancelled", 55) in repo.calls
    assert repo.committed is True
    assert repo.rolled_back is False


def test_cancel_transfer_rejects_missing_received_or_cancelled_transfer_without_transaction():
    repo = FakeTransfersRepository()
    use_case = CancelTransferUseCase(repo)

    ok, message = use_case.execute(999)
    assert ok is False
    assert "غير موجود" in message

    repo.transfer["status"] = "Received"
    ok, message = use_case.execute(55)
    assert ok is False
    assert "تم استلامه" in message

    repo.transfer["status"] = "Cancelled"
    ok, message = use_case.execute(55)
    assert ok is False
    assert "ملغي بالفعل" in message

    assert repo.committed is False
    assert repo.rolled_back is False


def test_cancel_transfer_rolls_back_on_repository_failure():
    repo = FakeTransfersRepository()
    repo.raise_on_cancel = RuntimeError("cancel failed")
    use_case = CancelTransferUseCase(repo)

    ok, message = use_case.execute(55)

    assert ok is False
    assert "فشل إلغاء التحويل" in message
    assert repo.committed is False
    assert repo.rolled_back is True
