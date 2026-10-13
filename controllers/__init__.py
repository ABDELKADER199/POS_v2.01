"""Thin UI adapters for POS V2 controllers.

Controllers are exposed lazily to avoid importing UI-dependent services during
package import.
"""
from importlib import import_module


_CONTROLLER_MODULES = {
    "AccountsController": "controllers.accounts_controller",
    "AdminController": "controllers.admin_controller",
    "AuthController": "controllers.auth_controller",
    "BackupController": "controllers.backup_controller",
    "CallCenterController": "controllers.callcenter_controller",
    "CashierController": "controllers.cashier_controller",
    "DrawerController": "controllers.drawer_controller",
    "PrintController": "controllers.print_controller",
    "ProductController": "controllers.product_controller",
    "PurchasesController": "controllers.purchases_controller",
    "ReturnsController": "controllers.returns_controller",
    "StatsController": "controllers.stats_controller",
    "SyncController": "controllers.sync_controller",
    "TransfersController": "controllers.transfers_controller",
}

__all__ = list(_CONTROLLER_MODULES)


def __getattr__(name):
    if name not in _CONTROLLER_MODULES:
        raise AttributeError(f"module 'controllers' has no attribute {name!r}")
    module = import_module(_CONTROLLER_MODULES[name])
    controller = getattr(module, name)
    globals()[name] = controller
    return controller
