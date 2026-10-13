from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


CONFIG_ENV_VAR = "POS_FEATURES_CONFIG"
CONFIG_FILE_NAME = "customer_features.json"


@dataclass(frozen=True)
class AppFeature:
    key: str
    label: str
    description: str
    permissions: tuple[str, ...] = ()


FEATURE_CATALOG: tuple[AppFeature, ...] = (
    AppFeature(
        "stats",
        "الإحصائيات",
        "لوحات الإحصائيات، الأرباح، حركة المبيعات، وتقارير الأداء.",
        ("stats.view_all", "stats.view_branch", "financial.view_costs"),
    ),
    AppFeature(
        "admin",
        "لوحة الإدارة",
        "إدارة المستخدمين، الأدوار، الفروع، الأجهزة، وسياسات التشغيل.",
        ("admin.manage_users", "admin.manage_devices", "admin.manage_cloud"),
    ),
    AppFeature(
        "products",
        "إدارة المنتجات",
        "المنتجات، الفئات، المخزون، الباركود، والتحويلات بين الفروع.",
        (
            "products.edit",
            "products.delete",
            "inventory.adjust",
            "inventory.transfer",
        ),
    ),
    AppFeature(
        "inventory_count",
        "جرد المخزون",
        "جلسات الجرد، اعتماد الفروق، وتقرير الجرد.",
        ("inventory.count", "inventory.count.approve"),
    ),
    AppFeature(
        "purchases",
        "المشتريات والموردين",
        "فواتير الشراء، الموردين، السداد، ومرتجعات المشتريات.",
    ),
    AppFeature(
        "accounts",
        "الحسابات والمالية",
        "الخزينة، المصروفات، التحصيل، التسويات، والسجل المالي.",
        (
            "accounts.full_access",
            "expenses.branch_access",
            "expenses.add",
            "expenses.void",
            "accounts.record_payment",
            "accounts.record_settlement",
        ),
    ),
    AppFeature(
        "promotions",
        "العروض",
        "إدارة عروض الشركة وعروض الموردين ومجلة العروض.",
    ),
    AppFeature(
        "returns",
        "مرتجع الفواتير",
        "مرتجعات البيع، رد النقدية، وتحديث المخزون والمديونية.",
        ("returns.access",),
    ),
    AppFeature(
        "cashier",
        "الكاشير",
        "شاشة البيع، الفواتير المعلقة، الطباعة، وشاشة العميل.",
        ("drawer.open", "drawer.use_shared", "invoice.delete_held", "invoice.reprint"),
    ),
    AppFeature(
        "call_center",
        "الكول سنتر",
        "طلبات الهاتف، متابعة الطلبات، وربطها بالكاشير.",
    ),
    AppFeature(
        "drawer",
        "درج الكاشير",
        "فتح وغلق الدرج، السجل، ومشاركة الدرج داخل الفرع.",
        ("drawer.close_own", "drawer.close_shared", "drawer.view_history"),
    ),
    AppFeature(
        "settings",
        "الإعدادات",
        "إعدادات التشغيل العامة وربط بيئة العمل.",
    ),
    AppFeature("cashier.scan_barcode", "قراءة الباركود", "إضافة الصنف بالكود أو الباركود داخل الكاشير."),
    AppFeature("cashier.scale_decimal_quantity", "دعم الموازين", "كميات عشرية بثلاث خانات حتى 0.001."),
    AppFeature("cashier.customer_display", "شاشة العميل", "عرض اسم الصنف والسعر والإجمالي على شاشة العميل."),
    AppFeature("cashier.held_invoices", "الفواتير المعلقة", "حفظ واسترجاع الفواتير المعلقة."),
    AppFeature("cashier.orders", "طلبات الكول سنتر", "استقبال الطلبات المفتوحة من الكول سنتر."),
    AppFeature("cashier.receipt_print", "طباعة إيصال البيع", "طباعة إيصال البيع من شاشة الكاشير."),
    AppFeature("cashier.pdf_invoice", "حفظ فاتورة البيع PDF", "حفظ فاتورة البيع كملف PDF."),
    AppFeature("cashier.whatsapp_message", "إرسال بيانات البيع واتساب", "تجهيز رسالة واتساب منسقة ببيانات الفاتورة."),
    AppFeature("cashier.discount", "خصم الفاتورة", "تطبيق الخصم اليدوي على الفاتورة مع حماية هامش الربح."),
    AppFeature("cashier.promotions", "تطبيق العروض وقت البيع", "احتساب العروض النشطة أثناء البيع."),
    AppFeature("cashier.cross_branch_lookup", "استعلام المخزون بالفروع", "عرض توفر الصنف في كل الفروع من الكاشير."),
    AppFeature("products.categories", "إدارة الفئات", "إضافة وتعديل وحذف فئات المنتجات."),
    AppFeature("products.excel_import", "استيراد Excel", "استيراد المنتجات والمخزون الافتتاحي من ملفات Excel."),
    AppFeature("products.bulk_import", "استيراد ضخم", "رفع آلاف الأصناف بسرعة عالية."),
    AppFeature("products.barcode_print", "طباعة الباركود", "طباعة باركود المنتجات."),
    AppFeature("products.images", "صور المنتجات", "حفظ وربط صور المنتجات."),
    AppFeature("products.header_filters", "فلاتر رؤوس الجداول", "فلاتر وفرز داخل رؤوس جداول المنتجات والمخزون."),
    AppFeature("products.stock_adjustment", "تعديل المخزون", "تعديل كميات المنتجات داخل الفروع."),
    AppFeature("products.transfer_management", "إدارة التحويلات", "إرسال واستلام التحويلات بين الفروع."),
    AppFeature("inventory_count.sessions", "جلسات الجرد", "فتح جلسة جرد للفرع أو المخزن."),
    AppFeature("inventory_count.quick_search", "بحث الجرد الذكي", "اقتراح الأصناف بعد التوقف عن الكتابة."),
    AppFeature("inventory_count.approval", "اعتماد الجرد", "تحديث المخزون بعد مراجعة فروق الجرد."),
    AppFeature("inventory_count.pdf_report", "تقرير جرد PDF", "استخراج تقرير جرد احترافي بعد الاعتماد."),
    AppFeature("purchases.suppliers", "إدارة الموردين", "إضافة وتعديل وحذف الموردين ومتابعة أرصدتهم."),
    AppFeature("purchases.invoice", "فاتورة شراء", "إضافة فاتورة شراء وتحديث تكلفة المنتج والمخزون."),
    AppFeature("purchases.payment", "سداد مورد", "تسجيل سداد فواتير الموردين."),
    AppFeature("purchases.return", "مرتجع مشتريات", "تنفيذ مرتجع شراء وتحديث المخزون ومديونية المورد."),
    AppFeature("purchases.supplier_promotions", "عروض المورد", "تسجيل دعم المورد للعروض والكميات المجانية."),
    AppFeature("purchases.pdf_invoice", "حفظ فاتورة الشراء PDF", "حفظ فاتورة الشراء كملف PDF."),
    AppFeature("purchases.whatsapp_message", "إرسال بيانات الشراء واتساب", "تجهيز رسالة واتساب منسقة للمورد."),
    AppFeature("accounts.treasury", "الخزينة", "تسجيل الداخل والخارج وأرصدة الخزينة."),
    AppFeature("accounts.expenses", "المصروفات", "إضافة ومراجعة مصروفات الفرع."),
    AppFeature("accounts.customer_collection", "تحصيل عميل", "تحصيل مديونيات العملاء."),
    AppFeature("accounts.supplier_payment", "دفع مورد", "دفع مديونيات الموردين."),
    AppFeature("accounts.settlements", "التسويات", "تسوية أرصدة العملاء والموردين."),
    AppFeature("accounts.financial_log", "السجل المالي", "عرض حركة الخزينة والقيود المالية."),
    AppFeature("accounts.pdf_reports", "تقارير مالية PDF", "استخراج تقارير مالية احترافية PDF."),
    AppFeature("promotions.manage", "إدارة العروض", "إضافة وتعديل وإيقاف العروض."),
    AppFeature("promotions.margin_guard", "حماية هامش الربح", "منع أي عرض يخفض الربح عن الحد الأدنى."),
    AppFeature("promotions.catalog_pdf", "مجلة العروض PDF", "إنشاء مجلة عروض احترافية بالصور والأسعار."),
    AppFeature("promotions.supplier_funded", "عروض ممولة من المورد", "تحديد دعم المورد وتأثيره على ربح الشركة."),
    AppFeature("returns.sales_return", "مرتجع بيع", "تنفيذ مرتجع فاتورة بيع."),
    AppFeature("returns.cash_refund", "رد نقدية", "حساب قيمة النقدية المتوقع ردها."),
    AppFeature("returns.customer_debt_reduce", "تقليل مديونية العميل", "خفض مديونية العميل عند مرتجع البيع الآجل."),
    AppFeature("returns.pdf_receipt", "إيصال مرتجع PDF", "حفظ إيصال المرتجع PDF."),
    AppFeature("returns.whatsapp_message", "إرسال المرتجع واتساب", "تجهيز رسالة واتساب ببيانات المرتجع."),
    AppFeature("call_center.orders", "إدارة الطلبات", "إنشاء ومتابعة طلبات العملاء."),
    AppFeature("call_center.convert_to_cashier", "تحويل للكاشير", "إرسال الطلب للكاشير لإتمام البيع."),
    AppFeature("call_center.customer_history", "سجل العميل", "عرض بيانات وسجل العميل من الكول سنتر."),
    AppFeature("drawer.open_close", "فتح وغلق الدرج", "فتح وغلق درج الكاشير."),
    AppFeature("drawer.shared", "الدرج المشترك", "استخدام درج مفتوح داخل نفس الفرع."),
    AppFeature("drawer.print_close", "طباعة غلق الدرج", "طباعة أو حفظ تقرير غلق الدرج PDF."),
    AppFeature("drawer.history", "سجل درج الكاشير", "عرض سجل فتح وغلق الدرج."),
    AppFeature("admin.users", "المستخدمون", "إدارة المستخدمين وربطهم بالأدوار والفروع."),
    AppFeature("admin.roles", "الأدوار والصلاحيات", "إدارة أدوار المستخدمين وصلاحياتهم."),
    AppFeature("admin.stores", "الفروع والمخازن", "إدارة الفروع والمخازن واستبعاد الإداري منها."),
    AppFeature("admin.device_lock", "قفل الجهاز", "ربط التشغيل بجهاز محدد لمنع النسخ."),
    AppFeature("admin.activation", "التفعيل", "إدارة أكواد التفعيل والترخيص."),
    AppFeature("admin.error_log", "سجل الأخطاء", "حفظ ومراجعة سجل أخطاء البرنامج."),
    AppFeature("settings.database", "إعدادات قاعدة البيانات", "إعداد الاتصال بقاعدة البيانات المحلية."),
    AppFeature("settings.printing", "إعدادات الطباعة", "إعداد الطابعات وحفظ PDF عند عدم وجود طابعة."),
    AppFeature("settings.backup", "النسخ الاحتياطي", "إنشاء واستعادة النسخ الاحتياطية."),
    AppFeature("security.local_db_only", "قاعدة محلية فقط", "منع الاتصال بقواعد خارجية للنسخ المحلية."),
    AppFeature("security.audit_logs", "تدقيق العمليات", "تسجيل العمليات الحساسة للمراجعة."),
    AppFeature("documents.pdf_export", "تصدير PDF عام", "إتاحة حفظ التقارير والفواتير PDF."),
    AppFeature("documents.whatsapp_share", "مشاركة واتساب عامة", "تجهيز رسائل واتساب منسقة من الفواتير والمرتجعات."),
)

FEATURE_BY_KEY = {feature.key: feature for feature in FEATURE_CATALOG}
ALL_FEATURE_KEYS = tuple(feature.key for feature in FEATURE_CATALOG)
ALL_FEATURE_PERMISSIONS = frozenset(
    permission
    for feature in FEATURE_CATALOG
    for permission in feature.permissions
)
PERMISSION_TO_FEATURE = {
    permission: feature.key
    for feature in FEATURE_CATALOG
    for permission in feature.permissions
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
        bundle_dir = getattr(sys, "_MEIPASS", "")
        if bundle_dir:
            roots.append(Path(bundle_dir).resolve())
    roots.extend([Path.cwd().resolve(), _project_root()])

    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root not in seen:
            seen.add(root)
            unique_roots.append(root)
    return unique_roots


def get_feature_config_path() -> Path:
    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()
    for root in _runtime_roots():
        config_path = root / CONFIG_FILE_NAME
        if config_path.exists():
            return config_path
    return _runtime_roots()[0] / CONFIG_FILE_NAME


@lru_cache(maxsize=1)
def load_feature_config() -> dict:
    path = get_feature_config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def is_feature_enabled(feature_key: str) -> bool:
    data = load_feature_config()
    enabled = data.get("enabled_features")
    if not enabled:
        return True
    return feature_key in set(enabled)


def filter_pages_for_enabled_features(page_keys: Iterable[str]) -> list[str]:
    return [key for key in page_keys if is_feature_enabled(key)]


def filter_permissions_for_enabled_features(permissions: Iterable[str]) -> set[str]:
    data = load_feature_config()
    explicit_enabled = data.get("enabled_permissions")
    enabled_permissions = set(explicit_enabled or [])
    filtered: set[str] = set()
    for permission in permissions:
        feature_key = PERMISSION_TO_FEATURE.get(permission)
        if feature_key and not is_feature_enabled(feature_key):
            continue
        if explicit_enabled and permission in ALL_FEATURE_PERMISSIONS and permission not in enabled_permissions:
            continue
        filtered.add(permission)
    return filtered


def effective_role_permissions(role_id: int, default_permissions: Iterable[str]) -> set[str]:
    data = load_feature_config()
    role_permissions = data.get("role_permissions")
    selected = None
    if isinstance(role_permissions, dict):
        selected = role_permissions.get(str(role_id))
    if isinstance(selected, list):
        permissions = set(str(permission) for permission in selected)
    else:
        permissions = set(default_permissions)
    return filter_permissions_for_enabled_features(permissions)


def is_role_allowed(role_id: int) -> bool:
    data = load_feature_config()
    allowed_roles = data.get("allowed_roles")
    if not allowed_roles:
        return True
    try:
        return int(role_id) in {int(value) for value in allowed_roles}
    except (TypeError, ValueError):
        return True


def effective_edition_role_id(role_id: int) -> int:
    data = load_feature_config()
    overrides = data.get("role_overrides")
    if not isinstance(overrides, dict):
        return role_id
    try:
        return int(overrides.get(str(int(role_id)), role_id))
    except (TypeError, ValueError):
        return role_id


def get_store_scope() -> dict | None:
    data = load_feature_config()
    scope = data.get("store_scope")
    if not isinstance(scope, dict):
        return None
    try:
        store_id = int(scope.get("id"))
    except (TypeError, ValueError):
        return None
    return {
        "id": store_id,
        "name": str(scope.get("name") or ""),
    }


def clear_feature_config_cache() -> None:
    load_feature_config.cache_clear()
