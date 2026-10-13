from application.use_cases.inventory_count import (
    AddInventoryCountItemUseCase,
    ApproveInventoryCountUseCase,
    CancelInventoryCountUseCase,
    InventoryCountSessionsUseCase,
    InventoryCountStoresUseCase,
    StartInventoryCountUseCase,
    UpdateInventoryCountItemUseCase,
)
from utils.permissions import ROLE_MANAGER, ROLE_WAREHOUSE


class FakeInventoryCountRepository:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.sessions = {
            7: {
                "id": 7,
                "count_number": "CNT-1",
                "store_id": 3,
                "status": "open",
            }
        }
        self.counted_items = [
            {
                "id": 11,
                "product_id": 50,
                "book_quantity": 10,
                "actual_quantity": 12,
                "variance": 2,
                "unit_cost": 5,
            },
            {
                "id": 12,
                "product_id": 51,
                "book_quantity": 4,
                "actual_quantity": 1,
                "variance": -3,
                "unit_cost": 8,
            },
        ]

    def get_stores(self):
        return [
            {"id": 1, "store_name": "المخزن الرئيسي", "store_type": "Main"},
            {"id": 3, "store_name": "فرع", "store_type": "Branch"},
        ]

    def create_session(self, count_number, store_id, count_type, user_id, notes=""):
        self.calls.append(("create_session", count_number, store_id, count_type, user_id, notes))
        self.sessions[99] = {
            "id": 99,
            "count_number": count_number,
            "store_id": store_id,
            "status": "open",
        }
        return 99

    def populate_full_session(self, session_id, store_id):
        self.calls.append(("populate_full_session", session_id, store_id))
        return 2

    def get_sessions(self, store_id=None, status=None):
        self.calls.append(("get_sessions", store_id, status))
        return list(self.sessions.values())

    def get_session(self, session_id):
        self.calls.append(("get_session", session_id))
        return self.sessions.get(session_id)

    def get_session_items(self, session_id, search="", limit=300):
        self.calls.append(("get_session_items", session_id, search, limit))
        return []

    def search_products(self, term, store_id, limit=50):
        self.calls.append(("search_products", term, store_id, limit))
        return []

    def add_product_to_session(self, session_id, product_id, store_id):
        self.calls.append(("add_product_to_session", session_id, product_id, store_id))

    def update_count_item(self, session_id, product_id, actual_quantity, notes, user_id):
        self.calls.append(("update_count_item", session_id, product_id, actual_quantity, notes, user_id))

    def get_counted_items(self, session_id):
        self.calls.append(("get_counted_items", session_id))
        return self.counted_items

    def set_inventory_quantity(self, product_id, store_id, quantity, user_id, notes):
        self.calls.append(("set_inventory_quantity", product_id, store_id, quantity, user_id, notes))

    def insert_adjustment(self, session_id, item_id, item, store_id, user_id):
        self.calls.append(("insert_adjustment", session_id, item_id, item["product_id"], store_id, user_id))

    def mark_session_approved(self, session_id, user_id):
        self.calls.append(("mark_session_approved", session_id, user_id))
        self.sessions[session_id]["status"] = "approved"

    def mark_session_cancelled(self, session_id):
        self.calls.append(("mark_session_cancelled", session_id))

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def manager_user(store_id=3):
    return {"id": 10, "role_id": ROLE_MANAGER, "role_name": "manager", "store_id": store_id}


def warehouse_user(store_id=3):
    return {"id": 20, "role_id": ROLE_WAREHOUSE, "role_name": "warehouse", "store_id": store_id}


def call_names(repo):
    return [call[0] for call in repo.calls]


def test_store_and_session_lists_are_branch_scoped_for_manager():
    repo = FakeInventoryCountRepository()

    stores = InventoryCountStoresUseCase(repo).execute(manager_user(store_id=3))
    assert stores == [{"id": 3, "store_name": "فرع", "store_type": "Branch"}]

    InventoryCountSessionsUseCase(repo).execute(manager_user(store_id=3), store_id=1, status="open")
    assert ("get_sessions", 3, "open") in repo.calls


def test_start_full_inventory_count_populates_items_and_commits():
    repo = FakeInventoryCountRepository()

    ok, message, session_id = StartInventoryCountUseCase(repo).execute(
        manager_user(store_id=3),
        store_id=3,
        count_type="full",
        notes="جرد شهري",
    )

    assert ok is True
    assert session_id == 99
    assert "تم فتح جلسة الجرد" in message
    assert ("populate_full_session", 99, 3) in repo.calls
    assert repo.committed is True


def test_add_and_update_inventory_count_item_require_open_branch_session():
    repo = FakeInventoryCountRepository()

    ok, message = AddInventoryCountItemUseCase(repo).execute(manager_user(store_id=3), 7, 50)
    assert ok is True
    assert "تمت إضافة الصنف" in message
    assert ("add_product_to_session", 7, 50, 3) in repo.calls

    ok, message = UpdateInventoryCountItemUseCase(repo).execute(manager_user(store_id=3), 7, 50, 12, "مراجعة")
    assert ok is True
    assert "تم حفظ كمية الجرد" in message
    assert ("update_count_item", 7, 50, 12, "مراجعة", 10) in repo.calls


def test_approve_inventory_count_updates_stock_and_records_adjustments():
    repo = FakeInventoryCountRepository()

    ok, message = ApproveInventoryCountUseCase(repo).execute(manager_user(store_id=3), 7)

    assert ok is True
    assert "تم اعتماد الجرد" in message
    assert ("set_inventory_quantity", 50, 3, 12, 10, "تسوية جرد CNT-1") in repo.calls
    assert ("set_inventory_quantity", 51, 3, 1, 10, "تسوية جرد CNT-1") in repo.calls
    assert ("insert_adjustment", 7, 11, 50, 3, 10) in repo.calls
    assert ("insert_adjustment", 7, 12, 51, 3, 10) in repo.calls
    assert ("mark_session_approved", 7, 10) in repo.calls
    assert repo.committed is True


def test_warehouse_can_count_but_cannot_approve():
    repo = FakeInventoryCountRepository()

    ok, _message, _session_id = StartInventoryCountUseCase(repo).execute(
        warehouse_user(store_id=3),
        store_id=3,
        count_type="partial",
    )
    assert ok is True

    ok, message = ApproveInventoryCountUseCase(repo).execute(warehouse_user(store_id=3), 7)
    assert ok is False
    assert "لا تملك صلاحية اعتماد الجرد" in message
    assert "mark_session_approved" not in call_names(repo)


def test_inventory_count_cancellation_is_branch_scoped():
    repo = FakeInventoryCountRepository()

    ok, message = CancelInventoryCountUseCase(repo).execute(warehouse_user(store_id=9), 7)

    assert ok is False
    assert "لا تملك صلاحية إلغاء جرد هذا الفرع" in message
    assert "mark_session_cancelled" not in call_names(repo)
