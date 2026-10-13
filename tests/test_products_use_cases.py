import pytest

from application.use_cases.import_products import ProductImportUseCase
from application.use_cases.product_management import (
    ADJUST_INVENTORY_ACTION,
    DELETE_PRODUCTS_ACTION,
    CreateProductUseCase,
    DeleteProductUseCase,
    FixZeroCostsUseCase,
    GetProductUseCase,
    ListProductsUseCase,
    ProductCategoriesUseCase,
    ProductInventoryUseCase,
    ProductSuppliersUseCase,
    UpdateProductUseCase,
    product_import_state,
)
from models.product import Product


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


class FakeProductRepository:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.product = Product(
            id=10,
            product_code="P10",
            product_name="منتج",
            buy_price=20,
            sell_price=30,
            barcode="P10",
        )
        self.products = [self.product]
        self.total = 1
        self.next_code = "900000000001"
        self.existing_codes = set()
        self.existing_names = set()
        self.category_map = {"غير مصنف": 1, "أغذية": 2}
        self.raise_on_insert = None
        self.raise_on_update = None
        self.raise_on_bulk = None

    def search(self, term, store_id=None, category_id=None, supplier_id=None, limit=50, offset=0, column_filters=None):
        self.calls.append(("search", term, store_id, category_id, supplier_id, limit, offset, column_filters))
        return self.products

    def count(self, term=None, category_id=None, supplier_id=None, column_filters=None):
        self.calls.append(("count", term, category_id, supplier_id, column_filters))
        return self.total

    def get_by_id(self, product_id):
        self.calls.append(("get_by_id", product_id))
        return self.product if product_id == self.product.id else None

    def insert_product(self, product, store_id=1):
        self.calls.append(("insert_product", product, store_id))
        if self.raise_on_insert:
            raise self.raise_on_insert
        return 99

    def set_initial_stock(self, product_id, store_id, initial_stock):
        self.calls.append(("set_initial_stock", product_id, store_id, initial_stock))

    def update_product_record(self, product):
        self.calls.append(("update_product_record", product))
        if self.raise_on_update:
            raise self.raise_on_update

    def soft_delete_product(self, product_id):
        self.calls.append(("soft_delete_product", product_id))
        if self.raise_on_update:
            raise self.raise_on_update

    def save_product_image(self, source_path, product_code):
        self.calls.append(("save_product_image", source_path, product_code))
        return f"assets/products/{product_code}.png"

    def update_zero_costs_from_margin(self, margin_percent=25.0):
        self.calls.append(("update_zero_costs_from_margin", margin_percent))
        return 7

    def get_suppliers(self, active_only=True):
        self.calls.append(("get_suppliers", active_only))
        return [{"id": 1, "name": "مورد"}]

    def get_categories(self):
        self.calls.append(("get_categories",))
        return [{"id": 1, "category_name": "غير مصنف"}]

    def insert_category(self, category_name):
        self.calls.append(("insert_category", category_name))
        return 5

    def update_category_record(self, category_id, category_name):
        self.calls.append(("update_category_record", category_id, category_name))

    def soft_delete_category(self, category_id):
        self.calls.append(("soft_delete_category", category_id))

    def get_all_stock(self, store_id=None, low_stock_only=False, limit=100, offset=0, search="", filters=None):
        self.calls.append(("get_all_stock", store_id, low_stock_only, limit, offset, search, filters))
        return [{"product_id": 10}]

    def count_all_stock(self, store_id=None, low_stock_only=False, search="", filters=None):
        self.calls.append(("count_all_stock", store_id, low_stock_only, search, filters))
        return 1

    def set_stock(self, product_id, store_id, quantity):
        self.calls.append(("set_stock", product_id, store_id, quantity))
        if self.raise_on_update:
            raise self.raise_on_update

    def next_numeric_internal_code(self):
        self.calls.append(("next_numeric_internal_code",))
        return self.next_code

    def get_existing_codes_and_names(self):
        self.calls.append(("get_existing_codes_and_names",))
        return set(self.existing_codes), set(self.existing_names)

    def get_or_create_categories(self, category_names):
        self.calls.append(("get_or_create_categories", category_names))
        result = dict(self.category_map)
        for name in category_names:
            result.setdefault(name, len(result) + 1)
        return result

    def bulk_create(self, products, stock_by_code, store_id=1, chunk_size=1000):
        self.calls.append(("bulk_create", products, stock_by_code, store_id, chunk_size))
        if self.raise_on_bulk:
            raise self.raise_on_bulk
        return len(products)

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def call_names(repo):
    return [call[0] for call in repo.calls]


def test_product_import_state_classifies_missing_price_or_cost():
    assert product_import_state(10, 5) == ("ready", "")
    assert product_import_state(0, 5) == ("needs_pricing", "ناقص سعر بيع")
    assert product_import_state(10, 0) == ("needs_cost", "ناقص تكلفة")
    assert product_import_state(0, 0, "ملاحظة") == ("needs_pricing", "ملاحظة - ناقص سعر بيع")


def test_list_get_create_update_delete_product_flows():
    repo = FakeProductRepository()
    audit = FakeAudit()

    products, total = ListProductsUseCase(repo).execute("p", category_id=1, supplier_id=2, page=2, per_page=10, column_filters={"status": "ready"})
    assert products == [repo.product]
    assert total == 1
    assert ("search", "p", None, 1, 2, 10, 10, {"status": "ready"}) in repo.calls
    assert ("count", "p", 1, 2, {"status": "ready"}) in repo.calls

    assert GetProductUseCase(repo).execute(10) == repo.product

    product_id = CreateProductUseCase(repo).execute(
        {
            "product_code": "P11",
            "product_name": "منتج جديد",
            "buy_price": 10,
            "sell_price": 15,
            "initial_stock": 4,
            "image_source": "image.png",
        },
        store_id=3,
    )
    assert product_id == 99
    inserted = next(call[1] for call in repo.calls if call[0] == "insert_product")
    assert inserted.product_code == "P11"
    assert inserted.image_path == "assets/products/P11.png"
    assert inserted.import_status == "ready"
    assert ("set_initial_stock", 99, 3, 4) in repo.calls
    assert repo.committed is True

    assert UpdateProductUseCase(repo).execute(10, {"sell_price": 0, "buy_price": 20, "import_notes": "من ملف"}) is True
    updated = [call[1] for call in repo.calls if call[0] == "update_product_record"][-1]
    assert updated.import_status == "needs_pricing"
    assert "ناقص سعر بيع" in updated.import_notes

    assert DeleteProductUseCase(repo, audit).execute(10, user_id=7) is True
    assert ("soft_delete_product", 10) in repo.calls
    assert audit.entries[-1]["action"] == DELETE_PRODUCTS_ACTION
    assert audit.entries[-1]["success"] is True


def test_product_update_delete_and_fix_zero_cost_failure_paths():
    repo = FakeProductRepository()
    audit = FakeAudit()

    with pytest.raises(ValueError, match="المنتج غير موجود"):
        UpdateProductUseCase(repo).execute(999, {})

    repo.raise_on_update = RuntimeError("db error")
    assert UpdateProductUseCase(repo).execute(10, {"sell_price": 35}) is False
    assert repo.rolled_back is True

    repo.rolled_back = False
    assert DeleteProductUseCase(repo, audit).execute(10, user_id=7) is False
    assert repo.rolled_back is True
    assert audit.entries[-1]["success"] is False

    with pytest.raises(ValueError, match="هامش الربح"):
        FixZeroCostsUseCase(repo).execute(100)

    repo.raise_on_update = None
    assert FixZeroCostsUseCase(repo).execute(25) == 7
    assert ("update_zero_costs_from_margin", 25) in repo.calls


def test_categories_suppliers_and_inventory_use_cases():
    repo = FakeProductRepository()
    audit = FakeAudit()
    categories = ProductCategoriesUseCase(repo)

    assert categories.list() == [{"id": 1, "category_name": "غير مصنف"}]
    assert categories.add(" أغذية ") == 5
    assert ("insert_category", "أغذية") in repo.calls
    assert categories.update(5, "مشروبات") is True
    assert ("update_category_record", 5, "مشروبات") in repo.calls
    assert categories.delete(5) is True
    assert ("soft_delete_category", 5) in repo.calls
    with pytest.raises(ValueError, match="اسم الفئة"):
        categories.add("")

    assert ProductSuppliersUseCase(repo).execute() == [{"id": 1, "name": "مورد"}]

    inventory = ProductInventoryUseCase(repo, audit)
    assert inventory.list(store_id=3, low_stock_only=True, page=2, per_page=10) == [{"product_id": 10}]
    assert ("get_all_stock", 3, True, 10, 10, "", None) in repo.calls
    assert inventory.update(10, 3, 15, user_id=7) is True
    assert ("set_stock", 10, 3, 15) in repo.calls
    assert audit.entries[-1]["action"] == ADJUST_INVENTORY_ACTION
    with pytest.raises(ValueError, match="سالبة"):
        inventory.update(10, 3, -1, 7)


def test_preview_import_file_generates_numeric_codes_and_marks_duplicates(tmp_path):
    repo = FakeProductRepository()
    repo.existing_codes = {"900000000001"}
    repo.existing_names = {"موجود"}
    file_path = tmp_path / "products.csv"
    file_path.write_text(
        "الاسم,سعر البيع,سعر الشراء,الفئة,المخزون\n"
        "منتج بدون كود,12,8,أغذية,5\n"
        "موجود,20,10,أغذية,2\n"
        ",20,10,أغذية,2\n",
        encoding="utf-8-sig",
    )

    preview = ProductImportUseCase(repo).preview_import_file(str(file_path))

    assert preview["processed"] == 3
    assert preview["ready"] == 1
    assert preview["blocked"] == 2
    first = preview["rows"][0]
    assert first["product_code"] == "900000000002"
    assert first["generated_code"] is True
    assert first["import_status"] == "ready"
    duplicate = preview["rows"][1]
    assert duplicate["import_status"] == "duplicate"
    assert "اسم مكرر" in duplicate["import_notes"]
    invalid = preview["rows"][2]
    assert invalid["import_status"] == "invalid"


def test_commit_import_preview_bulk_creates_importable_rows_and_skips_blocked():
    repo = FakeProductRepository()
    rows = [
        {
            "row_number": 2,
            "product_code": "900000000010",
            "product_name": "جاهز",
            "category_name": "أغذية",
            "buy_price": 8,
            "sell_price": 12,
            "unit": "قطعة",
            "initial_stock": 5,
            "tax_percent": 14,
            "import_status": "ready",
            "import_notes": "",
            "importable": True,
        },
        {
            "row_number": 3,
            "product_code": "900000000011",
            "product_name": "ناقص سعر",
            "category_name": "غير مصنف",
            "buy_price": 8,
            "sell_price": 0,
            "initial_stock": 1,
            "import_status": "needs_pricing",
            "import_notes": "ناقص سعر بيع",
            "importable": True,
        },
        {
            "row_number": 4,
            "product_code": "900000000012",
            "product_name": "مكرر",
            "importable": False,
        },
    ]

    result = ProductImportUseCase(repo).commit_import_preview(rows, store_id=3, include_incomplete=False)

    assert result["processed"] == 3
    assert result["valid"] == 1
    assert result["skipped"] == 2
    bulk_call = next(call for call in repo.calls if call[0] == "bulk_create")
    products = bulk_call[1]
    stock_by_code = bulk_call[2]
    assert len(products) == 1
    assert products[0].product_code == "900000000010"
    assert products[0].category_id == 2
    assert stock_by_code == {"900000000010": 5}
    assert bulk_call[3] == 3


def test_commit_import_preview_can_include_incomplete_and_reports_bulk_errors():
    repo = FakeProductRepository()
    repo.raise_on_bulk = RuntimeError("bulk failed")
    rows = [
        {
            "row_number": 2,
            "product_code": "900000000011",
            "product_name": "ناقص سعر",
            "category_name": "غير مصنف",
            "buy_price": 8,
            "sell_price": 0,
            "initial_stock": 1,
            "import_status": "needs_pricing",
            "import_notes": "ناقص سعر بيع",
            "importable": True,
        }
    ]

    result = ProductImportUseCase(repo).commit_import_preview(rows, store_id=3, include_incomplete=True)

    assert result["processed"] == 1
    assert result["valid"] == 0
    assert result["errors"] == 1
    assert result["error_samples"] == ["bulk failed"]
