"""
Pure-data configuration for the Developer Builder.

This module contains **no** Qt or UI imports – it can be tested and imported
anywhere without pulling in a graphical toolkit.
"""

from __future__ import annotations

from utils.permissions import (
    ROLE_ACCOUNTANT,
    ROLE_ADMIN,
    ROLE_CALL_CENTER,
    ROLE_CASHIER,
    ROLE_DEVELOPER,
    ROLE_MANAGER,
    ROLE_OWNER,
    ROLE_WAREHOUSE,
)

# ---------------------------------------------------------------------------
# Human-readable labels
# ---------------------------------------------------------------------------

ROLE_LABELS: dict[int, str] = {
    ROLE_DEVELOPER: "المطور",
    ROLE_OWNER: "المالك",
    ROLE_ADMIN: "مدير عام",
    ROLE_MANAGER: "مدير فرع",
    ROLE_ACCOUNTANT: "محاسب",
    ROLE_CASHIER: "كاشير",
    ROLE_CALL_CENTER: "كول سنتر",
    ROLE_WAREHOUSE: "مخزن",
}

PERMISSION_LABELS: dict[str, str] = {
    "stats.view_all": "عرض إحصائيات كل الفروع",
    "stats.view_branch": "عرض إحصائيات الفرع",
    "financial.view_costs": "عرض التكلفة والأرباح",
    "admin.manage_users": "إدارة المستخدمين",
    "admin.manage_devices": "إدارة الأجهزة والتفعيل",
    "admin.manage_cloud": "إدارة السحابة والمزامنة",
    "accounts.full_access": "وصول كامل للحسابات",
    "expenses.branch_access": "مصروفات الفرع",
    "expenses.add": "إضافة مصروف",
    "expenses.void": "إلغاء مصروف",
    "accounts.record_payment": "تسجيل السداد والتحصيل",
    "accounts.record_settlement": "تسجيل التسويات",
    "products.edit": "إضافة وتعديل المنتجات",
    "products.delete": "حذف المنتجات",
    "inventory.adjust": "تعديل المخزون",
    "inventory.transfer": "تحويل المخزون بين الفروع",
    "inventory.count": "تنفيذ الجرد",
    "inventory.count.approve": "اعتماد الجرد",
    "drawer.open": "فتح درج الكاشير",
    "drawer.close_own": "غلق درج المستخدم",
    "drawer.close_shared": "غلق درج مشترك",
    "drawer.use_shared": "استخدام درج مفتوح في الفرع",
    "drawer.view_history": "عرض سجل الدرج",
    "invoice.delete_held": "حذف الفواتير المعلقة",
    "invoice.reprint": "إعادة طباعة الفواتير",
    "returns.access": "الوصول إلى المرتجعات",
}

FEATURE_GROUP_LABELS: dict[str, str] = {
    "stats": "الإحصائيات والتقارير",
    "admin": "الإدارة والأمان",
    "products": "المنتجات والمخزون",
    "inventory_count": "الجرد",
    "purchases": "المشتريات والموردين",
    "accounts": "الحسابات والمالية",
    "promotions": "العروض",
    "returns": "المرتجعات",
    "cashier": "الكاشير",
    "call_center": "الكول سنتر",
    "drawer": "درج الكاشير",
    "settings": "الإعدادات",
    "security": "الأمان",
    "documents": "المستندات والمشاركة",
}

# ---------------------------------------------------------------------------
# Edition presets  (NOTE: "stats" duplicate in 'management' has been fixed)
# ---------------------------------------------------------------------------

EDITION_PRESETS: dict[str, dict] = {
    "full": {
        "label": "نسخة كاملة لكل الشركة",
        "features": None,
        "roles": None,
    },
    "branch_manager": {
        "label": "نسخة مدير الفرع",
        "roles": {ROLE_DEVELOPER, ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER},
        "role_overrides": {
            ROLE_DEVELOPER: ROLE_MANAGER,
            ROLE_ADMIN: ROLE_MANAGER,
        },
        "features": {
            "stats",
            "products",
            "inventory_count",
            "accounts",
            "returns",
            "cashier",
            "call_center",
            "drawer",
            "products.header_filters",
            "products.stock_adjustment",
            "products.transfer_management",
            "inventory_count.sessions",
            "inventory_count.quick_search",
            "inventory_count.approval",
            "inventory_count.pdf_report",
            "accounts.expenses",
            "cashier.scan_barcode",
            "cashier.scale_decimal_quantity",
            "cashier.customer_display",
            "cashier.held_invoices",
            "cashier.orders",
            "cashier.receipt_print",
            "cashier.pdf_invoice",
            "cashier.whatsapp_message",
            "cashier.discount",
            "cashier.promotions",
            "cashier.cross_branch_lookup",
            "returns.sales_return",
            "returns.cash_refund",
            "returns.customer_debt_reduce",
            "returns.pdf_receipt",
            "returns.whatsapp_message",
            "call_center.orders",
            "call_center.convert_to_cashier",
            "call_center.customer_history",
            "drawer.open_close",
            "drawer.shared",
            "drawer.print_close",
            "drawer.history",
            "documents.pdf_export",
            "documents.whatsapp_share",
        },
    },
    "cashier": {
        "label": "نسخة الكاشير",
        "roles": {ROLE_DEVELOPER, ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_CASHIER},
        "role_overrides": {
            ROLE_DEVELOPER: ROLE_MANAGER,
            ROLE_ADMIN: ROLE_MANAGER,
        },
        "features": {
            "cashier",
            "drawer",
            "cashier.scan_barcode",
            "cashier.scale_decimal_quantity",
            "cashier.customer_display",
            "cashier.held_invoices",
            "cashier.orders",
            "cashier.receipt_print",
            "cashier.pdf_invoice",
            "cashier.whatsapp_message",
            "cashier.discount",
            "cashier.promotions",
            "cashier.cross_branch_lookup",
            "drawer.open_close",
            "drawer.shared",
            "drawer.print_close",
            "documents.pdf_export",
            "documents.whatsapp_share",
        },
    },
    "accounts": {
        "label": "نسخة الحسابات",
        "roles": {ROLE_DEVELOPER, ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_ACCOUNTANT},
        "features": {
            "stats",
            "accounts",
            "accounts.treasury",
            "accounts.expenses",
            "accounts.customer_collection",
            "accounts.supplier_payment",
            "accounts.settlements",
            "accounts.financial_log",
            "accounts.pdf_reports",
            "documents.pdf_export",
        },
    },
    "inventory": {
        "label": "نسخة المخزون",
        "roles": {ROLE_DEVELOPER, ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_WAREHOUSE},
        "features": {
            "products",
            "inventory_count",
            "products.categories",
            "products.excel_import",
            "products.bulk_import",
            "products.barcode_print",
            "products.images",
            "products.header_filters",
            "products.stock_adjustment",
            "products.transfer_management",
            "inventory_count.sessions",
            "inventory_count.quick_search",
            "inventory_count.approval",
            "inventory_count.pdf_report",
            "documents.pdf_export",
        },
    },
    "purchases": {
        "label": "نسخة المشتريات",
        "roles": {ROLE_DEVELOPER, ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_ACCOUNTANT, ROLE_WAREHOUSE},
        "features": {
            "purchases",
            "products",
            "promotions",
            "purchases.suppliers",
            "purchases.invoice",
            "purchases.payment",
            "purchases.return",
            "purchases.supplier_promotions",
            "purchases.pdf_invoice",
            "purchases.whatsapp_message",
            "promotions.supplier_funded",
            "documents.pdf_export",
            "documents.whatsapp_share",
        },
    },
    "management": {
        "label": "نسخة الإدارة",
        "roles": {ROLE_DEVELOPER, ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER},
        "features": {
            "stats",
            "admin",
            "products",
            "accounts",
            "promotions",
            "drawer",
            "settings",
            # NOTE: "stats" was duplicated here – fixed.
            "admin.users",
            "admin.roles",
            "admin.stores",
            "admin.device_lock",
            "admin.activation",
            "admin.error_log",
            "products.header_filters",
            "accounts.pdf_reports",
            "promotions.manage",
            "promotions.margin_guard",
            "settings.database",
            "settings.printing",
            "settings.backup",
            "security.local_db_only",
            "security.audit_logs",
            "documents.pdf_export",
        },
    },
}

# ---------------------------------------------------------------------------
# Validation helpers (pure functions – no side-effects)
# ---------------------------------------------------------------------------

# Characters allowed in file-system slugs (Alphanumeric + Arabic + Dash/Underscore)
_SLUG_PATTERN = r"[^A-Za-z0-9_\-\u0600-\u06FF]+"

# Minimum requirements for a valid build
MIN_FEATURES_FOR_BUILD = 1
MAX_CLIENT_NAME_LENGTH = 120


def sanitize_filename(name: str | None, fallback: str = "app") -> str:
    """
    Sanitize a string to be a safe filename, preventing path traversal
    while allowing English and Arabic characters.
    """
    if not name:
        return fallback
    raw = name.strip() or fallback
    import re
    slug = re.sub(_SLUG_PATTERN, "_", raw).strip("_")
    # Replace multiple underscores with a single underscore
    slug = re.sub(r"_+", "_", slug)
    return slug or fallback


def validate_client_name(name: str) -> tuple[bool, str]:
    """Return (ok, error_message)."""
    stripped = name.strip()
    if not stripped:
        return False, "يرجى إدخال اسم العميل."
    if len(stripped) > MAX_CLIENT_NAME_LENGTH:
        return False, f"اسم العميل طويل جداً (الحد الأقصى {MAX_CLIENT_NAME_LENGTH} حرف)."
    return True, ""


def validate_app_name(name: str) -> tuple[bool, str]:
    stripped = name.strip()
    if not stripped:
        return False, "يرجى إدخال اسم التطبيق."
    return True, ""


def validate_features(enabled: list[str]) -> tuple[bool, str]:
    if len(enabled) < MIN_FEATURES_FOR_BUILD:
        return False, "يرجى اختيار ميزة واحدة على الأقل."
    return True, ""


def validate_roles(allowed: list[int]) -> tuple[bool, str]:
    if not allowed:
        return False, "يرجى تفعيل دور واحد على الأقل."
    return True, ""


def validate_all(
    client_name: str,
    app_name: str,
    enabled_features: list[str],
    allowed_roles: list[int],
) -> tuple[bool, list[str]]:
    """Run every validator and collect error messages."""
    errors: list[str] = []
    for ok, msg in (
        validate_client_name(client_name),
        validate_app_name(app_name),
        validate_features(enabled_features),
        validate_roles(allowed_roles),
    ):
        if not ok:
            errors.append(msg)
    return len(errors) == 0, errors
