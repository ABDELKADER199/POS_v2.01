import pytest

from utils.permissions import (
    Permission,
    PermissionDenied,
    PermissionPolicy,
    require_store_id,
    ROLE_ACCOUNTANT,
    ROLE_ADMIN,
    ROLE_CALL_CENTER,
    ROLE_CASHIER,
    ROLE_DEVELOPER,
    ROLE_MANAGER,
    ROLE_OWNER,
    ROLE_WAREHOUSE,
    Scope,
)


def user(role_id, role_name="", store_id=10):
    return {"id": 1, "role_id": role_id, "role_name": role_name, "store_id": store_id}


def test_cashier_sees_only_cashier_page_and_limited_drawer_permissions():
    policy = PermissionPolicy(user(ROLE_CASHIER, "cashier"))

    assert policy.main_pages() == ["cashier"]
    assert policy.can(Permission.OPEN_DRAWER)
    assert policy.can(Permission.CLOSE_OWN_DRAWER)
    assert policy.can(Permission.USE_SHARED_DRAWER)
    assert not policy.can(Permission.CLOSE_SHARED_DRAWER)
    assert not policy.can_access_returns()
    assert not policy.can_access_full_accounts()
    assert not policy.can_manage_users()
    assert policy.scope_for(Permission.OPEN_DRAWER) == Scope.OWN


def test_manager_is_branch_scoped_without_promotions_or_full_stats():
    policy = PermissionPolicy(user(ROLE_MANAGER, "manager", store_id=3))

    assert "stats" in policy.main_pages()
    assert "promotions" not in policy.main_pages()
    assert "admin" not in policy.main_pages()
    assert "settings" not in policy.main_pages()
    assert policy.can(Permission.VIEW_BRANCH_STATS)
    assert not policy.can_view_all_stats()
    assert policy.can_access_branch_expenses()
    assert not policy.can_access_full_accounts()
    assert policy.can(Permission.OPEN_DRAWER)
    assert policy.can(Permission.CLOSE_SHARED_DRAWER)
    assert policy.scoped_store_id(requested_store_id=99) == 3
    assert policy.scope_for(Permission.ACCESS_BRANCH_EXPENSES) == Scope.BRANCH


def test_role_name_does_not_escalate_to_developer_permissions():
    policy = PermissionPolicy(user(ROLE_CASHIER, "Developer"))

    assert not policy.is_developer
    assert not policy.is_admin
    assert not policy.can_manage_users()
    assert policy.main_pages() == ["cashier"]


def test_owner_role_id_gets_admin_level_permissions():
    policy = PermissionPolicy(user(ROLE_OWNER, "owner"))

    assert policy.is_owner
    assert policy.is_admin
    assert policy.can_manage_users()
    assert policy.can_access_full_accounts()
    assert policy.can_view_all_stats()
    assert policy.can_delete_products()
    assert policy.can_close_shared_drawer()
    assert policy.scoped_store_id(requested_store_id=99) == 99


def test_admin_role_id_has_full_permissions_and_pages():
    policy = PermissionPolicy(user(ROLE_ADMIN, "admin"))

    assert policy.can_manage_users()
    assert policy.can_access_full_accounts()
    assert policy.can_view_all_stats()
    assert policy.can_manage_cloud()
    assert policy.main_pages() == [
        "stats",
        "admin",
        "products",
        "inventory_count",
        "purchases",
        "accounts",
        "promotions",
        "returns",
        "cashier",
        "call_center",
        "drawer",
        "settings",
    ]


def test_accountant_has_finance_and_purchases_without_drawer_or_admin():
    policy = PermissionPolicy(user(ROLE_ACCOUNTANT, "accountant"))

    assert policy.main_pages() == ["stats", "purchases", "accounts"]
    assert policy.can_access_full_accounts()
    assert policy.can_view_all_stats()
    assert policy.can_view_buy_price()
    assert policy.can(Permission.RECORD_PAYMENT)
    assert not policy.can(Permission.OPEN_DRAWER)
    assert not policy.can_manage_users()
    assert not policy.can_access_returns()
    assert policy.scope_for(Permission.ACCESS_FULL_ACCOUNTS) == Scope.ALL


def test_warehouse_can_only_access_products_inventory_scope():
    policy = PermissionPolicy(user(ROLE_WAREHOUSE, "warehouse", store_id=4))

    assert policy.main_pages() == ["products", "inventory_count"]
    assert policy.can_adjust_inventory()
    assert policy.can_transfer_inventory()
    assert policy.can_count_inventory()
    assert not policy.can_approve_inventory_count()
    assert policy.can_view_all_inventory()
    assert not policy.can_view_buy_price()
    assert not policy.can_access_full_accounts()
    assert policy.scoped_store_id(requested_store_id=99) == 4
    assert policy.scope_for(Permission.ADJUST_INVENTORY) == Scope.BRANCH


def test_call_center_only_sees_call_center_page():
    policy = PermissionPolicy(user(ROLE_CALL_CENTER, "call center"))

    assert policy.main_pages() == ["call_center"]
    assert not policy.can(Permission.OPEN_DRAWER)
    assert not policy.can_access_returns()
    assert not policy.can_access_full_accounts()


def test_require_raises_permission_denied_for_missing_permission():
    policy = PermissionPolicy(user(ROLE_CASHIER, "cashier"))

    policy.require(Permission.OPEN_DRAWER)
    with pytest.raises(PermissionDenied, match="لا تملك"):
        policy.require(Permission.MANAGE_USERS)


def test_invalid_role_id_defaults_to_cashier():
    policy = PermissionPolicy({"id": 1, "role_id": "bad", "role_name": "", "store_id": 7})

    assert policy.role_id == ROLE_CASHIER
    assert policy.main_pages() == ["cashier"]
    assert policy.scoped_store_id(requested_store_id=99) == 7


def test_explicit_developer_role_id_has_all_permissions():
    policy = PermissionPolicy(user(ROLE_DEVELOPER, "developer"))

    assert policy.can_manage_users()
    assert policy.can_manage_cloud()
    assert policy.can_delete_products()
    assert policy.can_access_returns()
    assert policy.scope_for(Permission.MANAGE_USERS) == Scope.ALL


def test_branch_user_cannot_operate_without_a_store_or_on_another_store():
    with pytest.raises(PermissionDenied, match="لا يوجد فرع"):
        require_store_id({"role_id": ROLE_MANAGER, "store_id": None})
    with pytest.raises(PermissionDenied, match="فرع آخر"):
        require_store_id({"role_id": ROLE_MANAGER, "store_id": 3}, requested_store_id=9)
    assert require_store_id({"role_id": ROLE_MANAGER, "store_id": 3}, requested_store_id=3) == 3


def test_privileged_user_must_explicitly_choose_a_store():
    with pytest.raises(PermissionDenied, match="اختيار الفرع"):
        require_store_id({"role_id": ROLE_DEVELOPER, "store_id": None})
    assert require_store_id({"role_id": ROLE_DEVELOPER}, requested_store_id=4) == 4
