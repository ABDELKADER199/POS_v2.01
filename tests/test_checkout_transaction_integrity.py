import pytest
from application.use_cases.cashier_cart import (
    CashierCartUseCase,
    is_product_eligible_for_discount_company,
    distribute_discount_to_lines,
)
from application.use_cases.checkout_sale import CheckoutSaleUseCase
from models.invoice import InvoiceItem
from models.product import Product


class TransactionalDBMock:
    """
    محاكاة دقيقة لسلوك جلسة MySQL مع دعم التراجع (Rollback) الذري:
    تحتفظ بسجل العمليات المؤقت، وتلغي جميع التعديلات عند rollback.
    """

    def __init__(self):
        self.invoices = {}
        self.invoice_items = []
        self.treasury = []
        self.inventory = {101: 50.0, 102: 30.0}
        self.customer_balances = {1: 0.0}
        self.tax_details = {}
        self.committed = False
        self.rolled_back = False
        self.calls = []
        self.in_transaction = False
        self.fail_at_stage = None

    def begin(self):
        self.in_transaction = True
        self.calls.append("BEGIN")

    def commit(self):
        self.committed = True
        self.in_transaction = False
        self.calls.append("COMMIT")

    def rollback(self):
        self.rolled_back = True
        self.in_transaction = False
        self.calls.append("ROLLBACK")
        # تنظيف كل البيانات غير المثبتة
        self.invoices.clear()
        self.invoice_items.clear()
        self.treasury.clear()
        self.tax_details.clear()


class RealTransactionalRepo:
    """
    مستودع يطبق تدفق MySQL الحقيقي لاختبار حدود المعاملات وحقن الأعطال.
    """

    def __init__(self, db: TransactionalDBMock):
        self.db = db
        self.columns = {
            "invoices": {
                "id", "invoice_number", "store_id", "cashier_id", "customer_id",
                "customer_name", "customer_phone", "customer_address", "drawer_id",
                "payment_method", "cash_amount", "card_amount", "total_amount",
                "paid_amount", "remaining_amount", "subtotal_amount", "tax_amount",
                "discount_company_id", "discount_company_name", "company_discount_amount",
            },
            "invoice_items": {
                "id", "invoice_id", "product_id", "quantity", "unit_price",
                "discount", "total_price", "buy_price", "item_subtotal", "item_tax",
            },
        }

    def _columns(self, table_name):
        return self.columns.get(table_name, set())

    def get_stock(self, product_id, store_id=None):
        return 999.0

    def calculate_promotions(self, items):
        return [], 0.0

    def get_next_number(self):
        return "INV-9001"

    def get_or_create_customer(self, name, phone, address):
        return 1

    def get_customer_by_phone(self, phone):
        return None

    def check_credit_limit(self, customer_id, amount):
        return True, ""

    def validate_sale_stock(self, items, store_id):
        if self.db.fail_at_stage == "validate_stock":
            raise ValueError("رصيد المخزون لا يكفي")

    def insert_invoice_header(self, **kwargs):
        if self.db.fail_at_stage == "insert_header":
            raise RuntimeError("Database connection error on insert_invoice_header")
        has_company_discount = bool(
            kwargs.get("discount_company_id")
            or (kwargs.get("company_discount_amount") and kwargs.get("company_discount_amount") > 0)
        )
        invoice_cols = self._columns("invoices")
        required_company_cols = [
            "discount_company_id",
            "discount_company_name",
            "company_discount_amount",
        ]
        if has_company_discount and not all(c in invoice_cols for c in required_company_cols):
            missing = [c for c in required_company_cols if c not in invoice_cols]
            raise RuntimeError(
                f"تعذر تسجيل الفاتورة: أعمدة شركة الخصم غير متوفرة في قاعدة البيانات: {missing}. يجب تشغيل تهيئة مخطط الفواتير عند بدء التشغيل خارج المعاملة المالية."
            )
        inv_id = 1
        self.db.invoices[inv_id] = kwargs
        return inv_id

    def insert_sale_item(self, **kwargs):
        if self.db.fail_at_stage == "insert_item":
            raise RuntimeError("Database dead-lock on inserting sale item")
        self.db.invoice_items.append(kwargs)

    def decrease_product_inventory(self, product_id, store_id, quantity):
        if self.db.fail_at_stage == "decrease_inventory":
            raise RuntimeError("Inventory lock timeout")
        self.db.inventory[product_id] = self.db.inventory.get(product_id, 0.0) - quantity

    def apply_sale_financial_effects(self, **kwargs):
        if self.db.fail_at_stage == "financial_effects":
            raise RuntimeError("Treasury ledger constraint failure")
        self.db.treasury.append({
            "amount": kwargs.get("cash_amount"),
            "invoice_id": kwargs.get("invoice_id"),
        })

    def record_supplier_promotion_claims(self, **kwargs):
        pass

    def save_sale_tax_details(self, invoice_id, tax_data):
        if self.db.fail_at_stage == "tax_details":
            raise RuntimeError("Tax registry external service timeout")
        self.db.tax_details[invoice_id] = tax_data

    def get_product_buy_price(self, product_id):
        return 10.0

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()


def make_product(product_id, name="صنف", price=100.0, tax=14.0):
    return Product(
        id=product_id,
        product_code=f"P{product_id}",
        product_name=name,
        sell_price=price,
        tax_percent=tax,
    )


# ==============================================================================
# Priority 1: اختبارات حقن الأعطال والتكامل لمعاملات MySQL
# ==============================================================================


@pytest.mark.parametrize("fail_stage", [
    "insert_header",
    "insert_item",
    "decrease_inventory",
    "financial_effects",
    "tax_details",
])
def test_checkout_failure_injection_at_any_stage_rolls_back_completely(fail_stage):
    """
    حقن فشل في مراحل متعددة أثناء إتمام البيع:
    يجب أن يتراجع النظام بالكامل (Rollback) دون ترك أي بيانات جزئية في:
    - الفواتير (invoices)
    - بنود الفواتير (invoice_items)
    - الخزينة (treasury)
    - الضرائب (tax_details)
    """
    db = TransactionalDBMock()
    db.fail_at_stage = fail_stage
    repo = RealTransactionalRepo(db)

    # تجهيز السلة بصنفين وخصم شركة
    cart = CashierCartUseCase(repo, repo)
    cart.set_store(1)
    cart.add_item(make_product(101, "منتج 1", 100.0, 14.0), 1)
    cart.add_item(make_product(102, "منتج 2", 50.0, 14.0), 1)
    cart.set_discount_company({"id": 1, "name": "Xclusive", "discount_percent": 10.0, "product_ids": []})

    checkout = CheckoutSaleUseCase(
        invoice_repo=repo,
        totals_calculator=cart.calculate_totals,
        promo_discount_for_product=cart.promo_discount_for_product,
        current_items_provider=lambda: cart.items,
        tax_invoice_provider=lambda: None,
        company_promo_discount_for_product=cart.company_promo_discount_for_product,
    )

    with pytest.raises(RuntimeError):
        checkout.execute(
            store_id=1,
            cashier_id=1,
            drawer_id=1,
            payment_method="Cash",
            cash_amount=135.0,
            card_amount=0.0,
        )

    # التحقق من استدعاء rollback وعدم استدعاء commit
    assert db.rolled_back is True
    assert db.committed is False

    # التحقق من عدم وجود أي سجلات جزئية أو أثر مالي معلق
    assert len(db.invoices) == 0
    assert len(db.invoice_items) == 0
    assert len(db.treasury) == 0
    assert len(db.tax_details) == 0


def test_ddl_never_executes_inside_checkout_transaction():
    """
    التحقق من عدم تنفيذ أي أمر DDL أو ALTER TABLE داخل المعاملة المالية:
    إذا كانت أعمدة شركة الخصم مفقودة من الجدول، يجب أن يفشل الإجراء فوراً
    ويرفض المعاملة بدلاً من تشغيل ALTER TABLE داخل المعاملة المفتوحة (الذي يسبب Implicit Commit في MySQL).
    """
    db = TransactionalDBMock()
    repo = RealTransactionalRepo(db)
    # إزالة أعمدة شركة الخصم لمحاكاة قاعدة بيانات قديمة لم يتم ترحيلها عند الإقلاع
    repo.columns["invoices"] = {
        "id", "invoice_number", "store_id", "cashier_id", "customer_id",
        "total_amount", "cash_amount", "card_amount", "payment_method",
    }

    cart = CashierCartUseCase(repo, repo)
    cart.set_store(1)
    cart.add_item(make_product(101, "منتج", 100.0, 14.0), 1)
    cart.set_discount_company({"id": 1, "name": "Xclusive", "discount_percent": 10.0, "product_ids": []})

    checkout = CheckoutSaleUseCase(
        invoice_repo=repo,
        totals_calculator=cart.calculate_totals,
        promo_discount_for_product=cart.promo_discount_for_product,
        current_items_provider=lambda: cart.items,
        tax_invoice_provider=lambda: None,
        company_promo_discount_for_product=cart.company_promo_discount_for_product,
    )

    with pytest.raises(RuntimeError, match="خارج المعاملة المالية"):
        checkout.execute(
            store_id=1,
            cashier_id=1,
            drawer_id=1,
            payment_method="Cash",
            cash_amount=90.0,
            card_amount=0.0,
        )

    assert db.rolled_back is True
    assert db.committed is False
    assert len(db.invoices) == 0


# ==============================================================================
# Priority 3: اختبار الحالات الخمس للأهلية والتوافقية الرجعية
# ==============================================================================


def test_case_1_historical_xclusive_company_with_no_linked_products():
    """
    الحالة 1: شركة Xclusive التاريخية بقائمة أصناف فارغة:
    تطبق على جميع الأصناف للحفاظ على السلوك التجاري التاريخي المعتمد.
    """
    company = {"id": 1, "name": "xclusive", "discount_percent": 5.0, "is_active": True, "product_ids": []}
    assert is_product_eligible_for_discount_company(company, 101) is True
    assert is_product_eligible_for_discount_company(company, 999) is True


def test_case_2_company_explicitly_linked_to_selected_products():
    """
    الحالة 2: شركة مرتبطة صراحة بأصناف محددة:
    تطبق فقط على الأصناف المحددة، وأي صنف آخر غير مشمول.
    """
    company = {
        "id": 2,
        "name": "Partner",
        "discount_percent": 10.0,
        "is_active": True,
        "product_ids": [101, 102],
    }
    assert is_product_eligible_for_discount_company(company, 101) is True
    assert is_product_eligible_for_discount_company(company, 102) is True
    assert is_product_eligible_for_discount_company(company, 103) is False


def test_case_3_newly_created_company_with_no_product_links():
    """
    الحالة 3: شركة جديدة أُنشئت دون تحديد أصناف:
    وفق البنية الحالية، إذا كانت product_ids فارغة، تطبق على جميع الأصناف.
    يتم توثيق هذا السلوك ليقرر العمل التجاري ما إذا كان يجب اشتراط ربط صنف.
    """
    new_company = {"id": 10, "name": "NewCompany", "discount_percent": 7.0, "is_active": True, "product_ids": []}
    assert is_product_eligible_for_discount_company(new_company, 501) is True


def test_case_4_missing_or_inconsistent_product_link_records():
    """
    الحالة 4: بيانات أصناف فاسدة أو غير متسقة (None, نصوص غير رقمية، قيم فارغة):
    يجب أن يتجاهل النظام القيم الفاسدة بأمان دون أن يتوقف أو يطرح استثناء غير معالج.
    """
    corrupt_company = {
        "id": 11,
        "name": "CorruptCo",
        "discount_percent": 10.0,
        "is_active": True,
        "product_ids": [None, "", "invalid_id", 101, "102"],
    }
    # يجب أن يتم استخراج [101, 102] بنجاح
    assert is_product_eligible_for_discount_company(corrupt_company, 101) is True
    assert is_product_eligible_for_discount_company(corrupt_company, 102) is True
    assert is_product_eligible_for_discount_company(corrupt_company, 999) is False


def test_case_5_inactive_company_and_ineligible_products():
    """
    الحالة 5: شركة معطلة (is_active = False):
    يجب ألا يتم تطبيق الخصم على أي صنف نهائياً.
    """
    inactive_company = {
        "id": 12,
        "name": "InactiveCo",
        "discount_percent": 15.0,
        "is_active": False,
        "product_ids": [101, 102],
    }
    assert is_product_eligible_for_discount_company(inactive_company, 101) is False
    assert is_product_eligible_for_discount_company(inactive_company, 102) is False
    assert is_product_eligible_for_discount_company(inactive_company, 999) is False
