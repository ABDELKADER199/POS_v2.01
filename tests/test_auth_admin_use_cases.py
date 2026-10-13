import json
from pathlib import Path
from uuid import uuid4

import bcrypt
import pytest

from application.use_cases.admin import (
    AdminDevicesUseCase,
    AdminDrawersUseCase,
    AdminStoresUseCase,
    AdminSyncStatsUseCase,
    AdminUsersUseCase,
    InitializeAdminUseCase,
)
from application.use_cases.auth import CurrentUserInfoUseCase, LoginUseCase, LogoutUseCase
from application.services.auth_service_facade import AuthServiceFacade
from models.user import User
from utils.feature_flags import clear_feature_config_cache


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test_tmp" / "auth"


def _feature_config(name: str) -> Path:
    root = TEST_TMP_ROOT / f"{name}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root / "customer_features.json"


@pytest.fixture(autouse=True)
def reset_feature_config(monkeypatch):
    monkeypatch.setenv("POS_FEATURES_CONFIG", str(_feature_config("missing_default")))
    clear_feature_config_cache()
    yield
    clear_feature_config_cache()


class FakeAuthRepository:
    def __init__(self):
        self.calls = []
        self.user = User(id=1, email="dev@example.com", name="Dev", role="developer", role_id=99)

    def authenticate(self, email, password):
        self.calls.append(("authenticate", email, password))
        return self.user if email == "dev@example.com" and password == "secret" else None

    def get_by_id(self, user_id):
        self.calls.append(("get_by_id", user_id))
        return self.user if user_id == 1 else None

    def get_all(self, active_only=True):
        self.calls.append(("get_all", active_only))
        return [self.user]


class FakeDeviceRepository:
    def __init__(self, active_devices=0, authorized_record=None):
        self.active_devices = active_devices
        self.authorized_record = authorized_record
        self.calls = []
        self.committed = False

    def count_active_authorized_devices(self):
        self.calls.append(("count_active_authorized_devices",))
        return self.active_devices

    def get_authorized_device_for_login(self, device_id, mac_address, user_id, store_id=None):
        self.calls.append(("get_authorized_device_for_login", device_id, mac_address, user_id, store_id))
        return self.authorized_record

    def mark_authorized_device_used(self, device_record_id):
        self.calls.append(("mark_authorized_device_used", device_record_id))

    def commit(self):
        self.committed = True


class FakeAdminRepository:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.existing_user = None
        self.raise_on_insert_user = None
        self.store_invoice_count = 0
        self.store_stock_count = 0

    def ensure_accountant_role(self):
        self.calls.append(("ensure_accountant_role",))

    def ensure_store_admin_columns(self):
        self.calls.append(("ensure_store_admin_columns",))

    def ensure_authorized_devices_table(self):
        self.calls.append(("ensure_authorized_devices_table",))

    def get_all_users(self):
        self.calls.append(("get_all_users",))
        return [{"id": 1, "email": "dev@example.com"}]

    def get_user_by_email(self, email):
        self.calls.append(("get_user_by_email", email))
        return {"email": email} if email == "dev@example.com" else None

    def get_all_roles(self):
        self.calls.append(("get_all_roles",))
        return [{"id": 1, "role_name": "admin"}]

    def get_all_stores(self, include_inactive=False):
        self.calls.append(("get_all_stores", include_inactive))
        return [{"id": 1, "store_name": "الرئيسي"}]

    def get_user_activation_status_by_email(self, email):
        self.calls.append(("get_user_activation_status_by_email", email))
        return self.existing_user

    def insert_user(self, name, email, password_hash, role_id, store_id, phone=""):
        self.calls.append(("insert_user", name, email, password_hash, role_id, store_id, phone))
        if self.raise_on_insert_user:
            raise self.raise_on_insert_user
        return 10

    def reactivate_user(self, user_id, name, password_hash, role_id, store_id, phone=""):
        self.calls.append(("reactivate_user", user_id, name, password_hash, role_id, store_id, phone))

    def update_user_record(self, user_id, name, email, role_id, store_id, phone="", password_hash=None):
        self.calls.append(("update_user_record", user_id, name, email, role_id, store_id, phone, password_hash))

    def soft_delete_user(self, user_id):
        self.calls.append(("soft_delete_user", user_id))

    def get_drawers_report(self):
        self.calls.append(("get_drawers_report",))
        return [{"id": 1}]

    def get_drawer_summary(self, drawer_id):
        self.calls.append(("get_drawer_summary", drawer_id))
        return {"drawer_id": drawer_id}

    def insert_store(
        self,
        name,
        store_type,
        city="",
        address="",
        phone="",
        manager="",
        ip_start=None,
        ip_end=None,
        require_ip_check=True,
        is_active=True,
    ):
        self.calls.append(
            (
                "insert_store",
                name,
                store_type,
                city,
                address,
                phone,
                manager,
                ip_start,
                ip_end,
                require_ip_check,
                is_active,
            )
        )
        return 20

    def update_store_record(
        self,
        store_id,
        name,
        store_type,
        city="",
        address="",
        phone="",
        manager="",
        ip_start=None,
        ip_end=None,
        require_ip_check=True,
        is_active=True,
    ):
        self.calls.append(("update_store_record", store_id, name, store_type, city, address, phone, manager, ip_start, ip_end, require_ip_check, is_active))

    def count_store_invoices(self, store_id):
        self.calls.append(("count_store_invoices", store_id))
        return self.store_invoice_count

    def count_store_stock_items(self, store_id):
        self.calls.append(("count_store_stock_items", store_id))
        return self.store_stock_count

    def delete_store_record(self, store_id):
        self.calls.append(("delete_store_record", store_id))

    def get_authorized_devices(self):
        self.calls.append(("get_authorized_devices",))
        return [{"device_id": "D1"}]

    def upsert_authorized_device(self, device_id, device_name, mac, store_id, user_id, reg_by, notes=""):
        self.calls.append(("upsert_authorized_device", device_id, device_name, mac, store_id, user_id, reg_by, notes))

    def update_device_status_record(self, device_id, is_active):
        self.calls.append(("update_device_status_record", device_id, is_active))

    def delete_device_record(self, device_id):
        self.calls.append(("delete_device_record", device_id))

    def get_sync_stats(self):
        self.calls.append(("get_sync_stats",))
        return {"pending": 0}

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def call_names(repo):
    return [call[0] for call in repo.calls]


def test_login_returns_user_and_current_user_info_maps_to_dict():
    repo = FakeAuthRepository()
    user = LoginUseCase(repo).execute("dev@example.com", "secret")

    assert user is repo.user
    assert ("authenticate", "dev@example.com", "secret") in repo.calls

    info = CurrentUserInfoUseCase().execute(user)
    assert info["email"] == "dev@example.com"
    assert info["role_id"] == 99
    assert info["is_admin"] is True
    LogoutUseCase().execute(user)


def test_auth_service_allows_login_when_no_device_policy_is_configured():
    repo = FakeAuthRepository()
    device_repo = FakeDeviceRepository(active_devices=0)

    service = AuthServiceFacade(repo, device_repo)
    user = service.login("dev@example.com", "secret")

    assert user is repo.user
    assert service.current_user is repo.user
    assert ("count_active_authorized_devices",) in device_repo.calls


def test_auth_service_applies_store_scope_to_non_privileged_users(monkeypatch):
    config_path = _feature_config("store_scope")
    config_path.write_text(
        json.dumps({"store_scope": {"id": 12, "name": "فرع 12"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("POS_FEATURES_CONFIG", str(config_path))
    clear_feature_config_cache()

    try:
        repo = FakeAuthRepository()
        repo.user = User(
            id=2,
            email="dev@example.com",
            name="Cashier",
            role="cashier",
            role_id=3,
            store_id=1,
            store_name="فرع 1",
        )
        service = AuthServiceFacade(repo, FakeDeviceRepository(active_devices=0))

        user = service.login("dev@example.com", "secret")

        assert user is repo.user
        assert user.store_id == 12
        assert user.store_name == "فرع 12"
    finally:
        clear_feature_config_cache()


def test_auth_service_keeps_privileged_users_on_full_scope(monkeypatch):
    config_path = _feature_config("privileged_store_scope")
    config_path.write_text(
        json.dumps({"store_scope": {"id": 12, "name": "فرع 12"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("POS_FEATURES_CONFIG", str(config_path))
    clear_feature_config_cache()

    try:
        repo = FakeAuthRepository()
        service = AuthServiceFacade(repo, FakeDeviceRepository(active_devices=0))

        user = service.login("dev@example.com", "secret")

        assert user is repo.user
        assert user.role_id == 99
        assert user.store_id == 1
    finally:
        clear_feature_config_cache()


def test_auth_service_blocks_login_when_device_is_not_authorized():
    repo = FakeAuthRepository()
    device_repo = FakeDeviceRepository(active_devices=1, authorized_record=None)

    service = AuthServiceFacade(repo, device_repo)
    user = service.login("dev@example.com", "secret")

    assert user is None
    assert service.current_user is None
    assert "get_authorized_device_for_login" in call_names(device_repo)


def test_login_failure_and_empty_current_user_info():
    repo = FakeAuthRepository()

    assert LoginUseCase(repo).execute("bad@example.com", "wrong") is None
    assert CurrentUserInfoUseCase().execute(None) == {}


def test_initialize_admin_runs_schema_guards():
    repo = FakeAdminRepository()

    InitializeAdminUseCase(repo).execute()

    assert repo.calls == [
        ("ensure_accountant_role",),
        ("ensure_store_admin_columns",),
        ("ensure_authorized_devices_table",),
    ]


def test_admin_users_add_new_user_hashes_password_and_commits():
    repo = FakeAdminRepository()
    use_case = AdminUsersUseCase(repo)

    assert use_case.add("User", "u@example.com", "secret", 3, 1, "010") is True

    insert_call = next(call for call in repo.calls if call[0] == "insert_user")
    assert insert_call[1] == "User"
    assert insert_call[2] == "u@example.com"
    assert bcrypt.checkpw("secret".encode("utf-8"), insert_call[3].encode("utf-8"))
    assert repo.committed is True
    assert repo.rolled_back is False


def test_admin_users_reject_active_duplicate_and_reactivate_inactive_user():
    repo = FakeAdminRepository()
    repo.existing_user = {"id": 5, "is_active": True}
    use_case = AdminUsersUseCase(repo)

    assert use_case.add("User", "u@example.com", "secret", 3, 1) is False
    assert "insert_user" not in call_names(repo)
    assert repo.committed is False

    repo.existing_user = {"id": 5, "is_active": False}
    assert use_case.add("User", "u@example.com", "secret", 3, 1) is True
    assert "reactivate_user" in call_names(repo)


def test_admin_users_update_delete_and_guards():
    repo = FakeAdminRepository()
    use_case = AdminUsersUseCase(repo)

    assert use_case.update(2, "User", "u@example.com", 3, 1, "010", password="new") is True
    update_call = next(call for call in repo.calls if call[0] == "update_user_record")
    assert update_call[1] == 2
    assert bcrypt.checkpw("new".encode("utf-8"), update_call[7].encode("utf-8"))

    assert use_case.delete(1) is False
    assert use_case.delete(2) is True
    assert ("soft_delete_user", 2) in repo.calls
    assert use_case.update(None, "User", "u@example.com", 3, 1) is False
    assert use_case.add("", "u@example.com", "secret", 3, 1) is False


def test_admin_users_rolls_back_on_repository_failure():
    repo = FakeAdminRepository()
    repo.raise_on_insert_user = RuntimeError("insert failed")

    assert AdminUsersUseCase(repo).add("User", "u@example.com", "secret", 3, 1) is False
    assert repo.committed is False
    assert repo.rolled_back is True


def test_admin_stores_add_update_delete_and_delete_guards():
    repo = FakeAdminRepository()
    use_case = AdminStoresUseCase(repo)

    assert use_case.get_all(include_inactive=True) == [{"id": 1, "store_name": "الرئيسي"}]
    assert use_case.add("فرع", "BR", city="C") == 20
    assert ("insert_store", "فرع", "BR", "C", "", "", "", None, None, True, True) in repo.calls
    assert use_case.update(20, "فرع جديد", "BR") is True
    assert "update_store_record" in call_names(repo)

    assert use_case.delete(None) == (False, "رقم الفرع غير صحيح")
    repo.store_invoice_count = 2
    ok, message = use_case.delete(20)
    assert ok is False
    assert "فاتورة" in message

    repo.store_invoice_count = 0
    repo.store_stock_count = 3
    ok, message = use_case.delete(20)
    assert ok is False
    assert "مخزون" in message

    repo.store_stock_count = 0
    assert use_case.delete(20) == (True, "تم حذف الفرع بنجاح")
    assert ("delete_store_record", 20) in repo.calls


def test_admin_drawers_devices_and_sync_queries():
    repo = FakeAdminRepository()

    assert AdminDrawersUseCase(repo).get_report() == [{"id": 1}]
    assert AdminDrawersUseCase(repo).get_summary(5) == {"drawer_id": 5}

    devices = AdminDevicesUseCase(repo)
    assert devices.get_all() == [{"device_id": "D1"}]
    assert devices.add("D1", "POS", "AA:BB", 1, 2, "admin", "note") is True
    assert ("upsert_authorized_device", "D1", "POS", "AA:BB", 1, 2, "admin", "note") in repo.calls
    assert devices.update_status(10, False) is True
    assert ("update_device_status_record", 10, False) in repo.calls
    assert devices.delete(10) is True
    assert ("delete_device_record", 10) in repo.calls
    assert devices.add("", "POS", "AA", 1, 2, "admin") is False
    assert devices.update_status(None, True) is False
    assert devices.delete(None) is False

    assert AdminSyncStatsUseCase(repo).execute() == {"pending": 0}


def test_admin_users_simple_queries_delegate():
    repo = FakeAdminRepository()
    use_case = AdminUsersUseCase(repo)

    assert use_case.get_all() == [{"id": 1, "email": "dev@example.com"}]
    assert use_case.get_by_email("dev@example.com") == {"email": "dev@example.com"}
    assert use_case.get_roles() == [{"id": 1, "role_name": "admin"}]


def test_admin_users_deletion_restrictions_and_invariants():
    repo = FakeAdminRepository()
    use_case = AdminUsersUseCase(repo)

    # 1. منع حذف الحساب الرئيسي صاحب المعرف 1 بشكل مطلق
    assert use_case.delete(1) is False

    # 2. منع حذف آخر مدير للنظام حتى وإن كان المعرف غير 1 (Last Administrator Invariant)
    repo.get_all_users = lambda: [
        {"id": 5, "name": "Sole Admin", "email": "admin@example.com", "role_id": 1, "role_name": "admin"},
        {"id": 6, "name": "Cashier", "email": "cashier@example.com", "role_id": 3, "role_name": "cashier"},
    ]
    assert use_case.delete(5) is False
    assert ("soft_delete_user", 5) not in repo.calls

    # 3. السماح بحذف مدير إذا وجد مدير أو مالك أو مطور آخر نشط في النظام
    repo.get_all_users = lambda: [
        {"id": 5, "name": "Admin 1", "email": "admin1@example.com", "role_id": 1, "role_name": "admin"},
        {"id": 7, "name": "Admin 2", "email": "admin2@example.com", "role_id": 7, "role_name": "owner"},
    ]
    assert use_case.delete(5) is True
    assert ("soft_delete_user", 5) in repo.calls

    # 4. السماح بحذف مستخدم عادي (كاشير / موظف مخزن)
    repo.get_all_users = lambda: [
        {"id": 1, "name": "Admin", "email": "a@example.com", "role_id": 1, "role_name": "admin"},
        {"id": 8, "name": "Cashier", "email": "c@example.com", "role_id": 3, "role_name": "cashier"},
    ]
    assert use_case.delete(8) is True
    assert ("soft_delete_user", 8) in repo.calls
