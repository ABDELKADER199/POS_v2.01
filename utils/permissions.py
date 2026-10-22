"""
Central permission policy for POS V2.

The rules mirror the legacy dashboard/page permissions while keeping the new
    application split into controllers and views.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from utils.feature_flags import (
    effective_edition_role_id,
    effective_role_permissions,
    filter_pages_for_enabled_features,
)


ROLE_ADMIN = 1
ROLE_MANAGER = 2
ROLE_CASHIER = 3
ROLE_CALL_CENTER = 4
ROLE_WAREHOUSE = 5
ROLE_ACCOUNTANT = 6
ROLE_OWNER = 7
ROLE_DEVELOPER = 99


class PermissionDenied(Exception):
    """Raised when a user attempts an action outside their role/scope."""


class Permission:
    VIEW_ALL_STATS = "stats.view_all"
    VIEW_BRANCH_STATS = "stats.view_branch"
    VIEW_COSTS = "financial.view_costs"
    MANAGE_USERS = "admin.manage_users"
    MANAGE_DEVICES = "admin.manage_devices"
    MANAGE_CLOUD = "admin.manage_cloud"
    ACCESS_FULL_ACCOUNTS = "accounts.full_access"
    ACCESS_BRANCH_EXPENSES = "expenses.branch_access"
    ADD_EXPENSE = "expenses.add"
    VOID_EXPENSE = "expenses.void"
    RECORD_PAYMENT = "accounts.record_payment"
    RECORD_SETTLEMENT = "accounts.record_settlement"
    EDIT_PRODUCTS = "products.edit"
    DELETE_PRODUCTS = "products.delete"
    ADJUST_INVENTORY = "inventory.adjust"
    TRANSFER_INVENTORY = "inventory.transfer"
    COUNT_INVENTORY = "inventory.count"
    APPROVE_INVENTORY_COUNT = "inventory.count.approve"
    OPEN_DRAWER = "drawer.open"
    CLOSE_OWN_DRAWER = "drawer.close_own"
    CLOSE_SHARED_DRAWER = "drawer.close_shared"
    USE_SHARED_DRAWER = "drawer.use_shared"
    VIEW_DRAWER_HISTORY = "drawer.view_history"
    DELETE_HELD_INVOICE = "invoice.delete_held"
    REPRINT_INVOICE = "invoice.reprint"
    ACCESS_RETURNS = "returns.access"


class Scope:
    NONE = "none"
    OWN = "own"
    BRANCH = "branch"
    ALL = "all"


ROLE_PERMISSIONS = {
    ROLE_DEVELOPER: {
        Permission.VIEW_ALL_STATS,
        Permission.VIEW_BRANCH_STATS,
        Permission.VIEW_COSTS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_DEVICES,
        Permission.MANAGE_CLOUD,
        Permission.ACCESS_FULL_ACCOUNTS,
        Permission.ACCESS_BRANCH_EXPENSES,
        Permission.ADD_EXPENSE,
        Permission.VOID_EXPENSE,
        Permission.RECORD_PAYMENT,
        Permission.RECORD_SETTLEMENT,
        Permission.EDIT_PRODUCTS,
        Permission.DELETE_PRODUCTS,
        Permission.ADJUST_INVENTORY,
        Permission.TRANSFER_INVENTORY,
        Permission.COUNT_INVENTORY,
        Permission.APPROVE_INVENTORY_COUNT,
        Permission.OPEN_DRAWER,
        Permission.CLOSE_OWN_DRAWER,
        Permission.CLOSE_SHARED_DRAWER,
        Permission.USE_SHARED_DRAWER,
        Permission.VIEW_DRAWER_HISTORY,
        Permission.DELETE_HELD_INVOICE,
        Permission.REPRINT_INVOICE,
        Permission.ACCESS_RETURNS,
    },
    ROLE_ADMIN: {
        Permission.VIEW_ALL_STATS,
        Permission.VIEW_BRANCH_STATS,
        Permission.VIEW_COSTS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_DEVICES,
        Permission.MANAGE_CLOUD,
        Permission.ACCESS_FULL_ACCOUNTS,
        Permission.ACCESS_BRANCH_EXPENSES,
        Permission.ADD_EXPENSE,
        Permission.VOID_EXPENSE,
        Permission.RECORD_PAYMENT,
        Permission.RECORD_SETTLEMENT,
        Permission.EDIT_PRODUCTS,
        Permission.DELETE_PRODUCTS,
        Permission.ADJUST_INVENTORY,
        Permission.TRANSFER_INVENTORY,
        Permission.COUNT_INVENTORY,
        Permission.APPROVE_INVENTORY_COUNT,
        Permission.OPEN_DRAWER,
        Permission.CLOSE_OWN_DRAWER,
        Permission.CLOSE_SHARED_DRAWER,
        Permission.USE_SHARED_DRAWER,
        Permission.VIEW_DRAWER_HISTORY,
        Permission.DELETE_HELD_INVOICE,
        Permission.REPRINT_INVOICE,
        Permission.ACCESS_RETURNS,
    },
    ROLE_MANAGER: {
        Permission.VIEW_BRANCH_STATS,
        Permission.ACCESS_BRANCH_EXPENSES,
        Permission.ADD_EXPENSE,
        Permission.VOID_EXPENSE,
        Permission.TRANSFER_INVENTORY,
        Permission.COUNT_INVENTORY,
        Permission.APPROVE_INVENTORY_COUNT,
        Permission.OPEN_DRAWER,
        Permission.CLOSE_OWN_DRAWER,
        Permission.CLOSE_SHARED_DRAWER,
        Permission.USE_SHARED_DRAWER,
        Permission.VIEW_DRAWER_HISTORY,
        Permission.DELETE_HELD_INVOICE,
        Permission.REPRINT_INVOICE,
        Permission.ACCESS_RETURNS,
    },
    ROLE_CASHIER: {
        Permission.OPEN_DRAWER,
        Permission.CLOSE_OWN_DRAWER,
        Permission.USE_SHARED_DRAWER,
    },
    ROLE_CALL_CENTER: set(),
    ROLE_WAREHOUSE: {
        Permission.ADJUST_INVENTORY,
        Permission.TRANSFER_INVENTORY,
        Permission.COUNT_INVENTORY,
    },
    ROLE_ACCOUNTANT: {
        Permission.VIEW_ALL_STATS,
        Permission.VIEW_BRANCH_STATS,
        Permission.VIEW_COSTS,
        Permission.ACCESS_FULL_ACCOUNTS,
        Permission.ADD_EXPENSE,
        Permission.VOID_EXPENSE,
        Permission.RECORD_PAYMENT,
        Permission.RECORD_SETTLEMENT,
    },
    ROLE_OWNER: set(),
}

ROLE_PERMISSIONS[ROLE_OWNER] = set(ROLE_PERMISSIONS[ROLE_ADMIN])


def _get_value(user: Any, key: str, default=None):
    if isinstance(user, dict):
        return user.get(key, default)
    return getattr(user, key, default)


def get_role_id(user: Any) -> int:
    try:
        return int(_get_value(user, "role_id", ROLE_CASHIER) or ROLE_CASHIER)
    except (TypeError, ValueError):
        return ROLE_CASHIER


def get_role_name(user: Any) -> str:
    return str(_get_value(user, "role_name", _get_value(user, "role", "")) or "").strip().lower()


def get_user_id(user: Any):
    return _get_value(user, "id")


def get_store_id(user: Any):
    return _get_value(user, "store_id")


def require_store_id(user: Any, requested_store_id=None) -> int:
    """Resolve a store without silently falling back to a hard-coded store."""
    policy = PermissionPolicy(user)
    requested = requested_store_id if requested_store_id is not None else get_store_id(user)
    try:
        requested = int(requested)
    except (TypeError, ValueError):
        requested = None

    if policy.is_developer or policy.is_owner or policy.role_id in (ROLE_ADMIN, ROLE_ACCOUNTANT):
        if requested is None:
            raise PermissionDenied("يجب اختيار الفرع قبل تنفيذ العملية")
        return requested

    user_store_id = get_store_id(user)
    try:
        user_store_id = int(user_store_id)
    except (TypeError, ValueError):
        raise PermissionDenied("لا يوجد فرع مرتبط بهذا المستخدم")
    if requested is not None and requested != user_store_id:
        raise PermissionDenied("لا تملك صلاحية تنفيذ العملية على فرع آخر")
    return user_store_id


@dataclass(frozen=True)
class PermissionPolicy:
    user: Any

    @property
    def role_id(self) -> int:
        return effective_edition_role_id(get_role_id(self.user))

    @property
    def original_role_id(self) -> int:
        return get_role_id(self.user)

    @property
    def role_name(self) -> str:
        return get_role_name(self.user)

    @property
    def is_developer(self) -> bool:
        return self.role_id == ROLE_DEVELOPER

    @property
    def is_owner(self) -> bool:
        return self.role_id == ROLE_OWNER

    @property
    def is_admin(self) -> bool:
        return self.role_id == ROLE_ADMIN or self.is_developer or self.is_owner

    @property
    def is_manager(self) -> bool:
        return self.is_admin or self.role_id == ROLE_MANAGER

    @property
    def is_cashier(self) -> bool:
        return self.role_id == ROLE_CASHIER

    @property
    def is_call_center(self) -> bool:
        return self.role_id == ROLE_CALL_CENTER

    @property
    def is_warehouse(self) -> bool:
        return self.role_id == ROLE_WAREHOUSE

    @property
    def is_accountant(self) -> bool:
        return self.role_id == ROLE_ACCOUNTANT

    @property
    def permissions(self) -> set[str]:
        if self.is_developer:
            return effective_role_permissions(ROLE_DEVELOPER, ROLE_PERMISSIONS[ROLE_DEVELOPER])
        if self.is_owner or self.is_admin:
            role_key = ROLE_OWNER if self.is_owner else ROLE_ADMIN
            return effective_role_permissions(role_key, ROLE_PERMISSIONS[ROLE_ADMIN])
        if self.is_accountant:
            return effective_role_permissions(ROLE_ACCOUNTANT, ROLE_PERMISSIONS[ROLE_ACCOUNTANT])
        if self.role_id == ROLE_MANAGER:
            return effective_role_permissions(ROLE_MANAGER, ROLE_PERMISSIONS[ROLE_MANAGER])
        if self.is_warehouse:
            return effective_role_permissions(ROLE_WAREHOUSE, ROLE_PERMISSIONS[ROLE_WAREHOUSE])
        if self.is_call_center:
            return effective_role_permissions(ROLE_CALL_CENTER, ROLE_PERMISSIONS[ROLE_CALL_CENTER])
        if self.is_cashier:
            return effective_role_permissions(ROLE_CASHIER, ROLE_PERMISSIONS[ROLE_CASHIER])
        return effective_role_permissions(self.role_id, ROLE_PERMISSIONS.get(self.role_id, set()))

    def can(self, permission: str) -> bool:
        return permission in self.permissions

    def has_verified_identity(self) -> bool:
        """Return True only for the login payload shape used by the desktop app."""
        user_id = get_user_id(self.user)
        try:
            return isinstance(self.user, dict) and int(user_id) > 0
        except (TypeError, ValueError):
            return False

    def require_stats_access(self) -> None:
        if not self.has_verified_identity():
            raise PermissionDenied("تعذر التحقق من هوية المستخدم")
        if not (self.can(Permission.VIEW_ALL_STATS) or self.can(Permission.VIEW_BRANCH_STATS)):
            raise PermissionDenied("لا تملك صلاحية عرض الإحصائيات")

    def authorized_stats_store_id(self, requested_store_id=None):
        """Resolve the only dashboard scope a verified user may query.

        ``None`` means all stores only for roles that explicitly have that scope.
        Branch users are always bound to their assigned store.
        """
        self.require_stats_access()
        if self.can(Permission.VIEW_ALL_STATS):
            if requested_store_id is None:
                return None
            try:
                return int(requested_store_id)
            except (TypeError, ValueError):
                raise PermissionDenied("معرّف الفرع غير صالح")
        return require_store_id(self.user, requested_store_id)

    def require(self, permission: str, message: str = "لا تملك صلاحية تنفيذ هذه العملية") -> None:
        if not self.can(permission):
            raise PermissionDenied(message)

    def scope_for(self, permission: str) -> str:
        if not self.can(permission):
            return Scope.NONE
        if self.is_developer or self.is_owner or self.role_id in (ROLE_ADMIN, ROLE_ACCOUNTANT):
            return Scope.ALL
        if self.is_manager or self.is_warehouse:
            return Scope.BRANCH
        if self.is_cashier:
            return Scope.OWN
        return Scope.NONE

    def scoped_store_id(self, requested_store_id=None):
        if self.is_developer or self.is_owner or self.role_id in (ROLE_ADMIN, ROLE_ACCOUNTANT):
            return requested_store_id
        return get_store_id(self.user)

    def main_pages(self) -> list[str]:
        """Legacy dashboard page order."""
        if self.is_developer or self.is_owner or self.role_id == ROLE_ADMIN:
            return filter_pages_for_enabled_features([
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
            ])
        if self.role_id == ROLE_CASHIER:
            return filter_pages_for_enabled_features(["cashier"])
        if self.role_id == ROLE_MANAGER:
            return filter_pages_for_enabled_features([
                "stats",
                "products",
                "inventory_count",
                "accounts",
                "returns",
                "cashier",
                "call_center",
                "drawer",
            ])
        if self.is_call_center:
            return filter_pages_for_enabled_features(["call_center"])
        if self.is_warehouse:
            return filter_pages_for_enabled_features(["products", "inventory_count"])
        if self.is_accountant:
            return filter_pages_for_enabled_features(["stats", "purchases", "accounts"])
        return []

    def can_access_returns(self) -> bool:
        return self.can(Permission.ACCESS_RETURNS)

    def can_view_drawer_history(self) -> bool:
        return self.can(Permission.VIEW_DRAWER_HISTORY)

    def can_use_shared_drawer(self) -> bool:
        return self.can(Permission.USE_SHARED_DRAWER)

    def can_close_shared_drawer(self) -> bool:
        return self.can(Permission.CLOSE_SHARED_DRAWER)

    def can_delete_held_invoice(self) -> bool:
        return self.can(Permission.DELETE_HELD_INVOICE)

    def can_reprint_invoices(self) -> bool:
        return self.can(Permission.REPRINT_INVOICE)

    def can_view_detailed_stats(self) -> bool:
        return self.can(Permission.VIEW_COSTS)

    def can_manage_devices(self) -> bool:
        return self.can(Permission.MANAGE_DEVICES)

    def can_manage_cloud(self) -> bool:
        return self.can(Permission.MANAGE_CLOUD)

    def can_view_all_inventory(self) -> bool:
        return self.is_admin or self.is_warehouse or self.is_developer

    def can_view_buy_price(self) -> bool:
        return self.can(Permission.VIEW_COSTS)

    def can_edit_products(self) -> bool:
        return self.can(Permission.EDIT_PRODUCTS)

    def can_delete_products(self) -> bool:
        return self.can(Permission.DELETE_PRODUCTS)

    def can_adjust_inventory(self) -> bool:
        return self.can(Permission.ADJUST_INVENTORY)

    def can_transfer_inventory(self) -> bool:
        return self.can(Permission.TRANSFER_INVENTORY)

    def can_count_inventory(self) -> bool:
        return self.can(Permission.COUNT_INVENTORY)

    def can_approve_inventory_count(self) -> bool:
        return self.can(Permission.APPROVE_INVENTORY_COUNT)

    def can_manage_users(self) -> bool:
        return self.can(Permission.MANAGE_USERS)

    def can_view_all_stats(self) -> bool:
        return self.can(Permission.VIEW_ALL_STATS)

    def can_access_full_accounts(self) -> bool:
        return self.can(Permission.ACCESS_FULL_ACCOUNTS)

    def can_access_branch_expenses(self) -> bool:
        return self.can(Permission.ACCESS_BRANCH_EXPENSES)
