import pytest

from application.services.product_service_facade import ProductServiceFacade
from application.use_cases.product_management import (
    ADJUST_INVENTORY_ACTION,
    CreateProductUseCase,
    FixZeroCostsUseCase,
    ListProductsUseCase,
    ProductCategoriesUseCase,
    ProductInventoryUseCase,
    ProductSuppliersUseCase,
    save_image_if_needed,
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
        self.product = Product(id=10, product_code="P10", product_name="منتج", buy_price=5, sell_price=10)
        self.committed = False
        self.rolled_back = False
        self.raise_on_insert = None
        self.raise_on_update = None

    def search(self, term, store_id=None, category_id=None, supplier_id=None, limit=50, offset=0, column_filters=None):
        self.calls.append(("search", term, store_id, category_id, supplier_id, limit, offset, column_filters))
        return [self.product]

    def count(self, term=None, category_id=None, supplier_id=None, column_filters=None):
        self.calls.append(("count", term, category_id, supplier_id, column_filters))
        return 1

    def get_by_id(self, product_id):
        self.calls.append(("get_by_id", product_id))
        return self.product if product_id == 10 else None

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
        if self.raise_on_update:
            raise self.raise_on_update
        return 4

    def get_suppliers(self, active_only=True):
        self.calls.append(("get_suppliers", active_only))
        return [{"id": 1, "name": "مورد"}]

    def get_categories(self):
        self.calls.append(("get_categories",))
        return [{"id": 1, "category_name": "غير مصنف"}]

    def insert_category(self, category_name):
        self.calls.append(("insert_category", category_name))
        if self.raise_on_insert:
            raise self.raise_on_insert
        return 5

    def update_category_record(self, category_id, category_name):
        self.calls.append(("update_category_record", category_id, category_name))
        if self.raise_on_update:
            raise self.raise_on_update

    def soft_delete_category(self, category_id):
        self.calls.append(("soft_delete_category", category_id))
        if self.raise_on_update:
            raise self.raise_on_update

    def get_all_stock(self, store_id=None, low_stock_only=False, limit=100, offset=0, search="", filters=None):
        self.calls.append(("get_all_stock", store_id, low_stock_only, limit, offset, search, filters))
        return [{"product_id": 10, "quantity": 3}]

    def count_all_stock(self, store_id=None, low_stock_only=False, search="", filters=None):
        self.calls.append(("count_all_stock", store_id, low_stock_only, search, filters))
        return 1

    def set_stock(self, product_id, store_id, quantity):
        self.calls.append(("set_stock", product_id, store_id, quantity))
        if self.raise_on_update:
            raise self.raise_on_update

    def get_existing_codes_and_names(self):
        self.calls.append(("get_existing_codes_and_names",))
        return set(), set()

    def next_numeric_internal_code(self):
        self.calls.append(("next_numeric_internal_code",))
        return "900000000001"

    def get_or_create_categories(self, category_names):
        self.calls.append(("get_or_create_categories", category_names))
        return {name: index + 1 for index, name in enumerate(category_names)}

    def bulk_create(self, products, stock_by_code, store_id=1, chunk_size=1000):
        self.calls.append(("bulk_create", products, stock_by_code, store_id, chunk_size))
        return len(products)

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


def test_list_products_normalizes_invalid_paging_values():
    repo = FakeProductRepository()

    products, total = ListProductsUseCase(repo).execute(page=0, per_page=0)

    assert products == [repo.product]
    assert total == 1
    assert ("search", "", None, None, None, 50, 0, None) in repo.calls


def test_save_image_if_needed_uses_barcode_when_product_code_missing():
    repo = FakeProductRepository()

    path = save_image_if_needed(repo, {"image_source": "image.png", "barcode": "B100"})

    assert path == "assets/products/B100.png"
    assert ("save_product_image", "image.png", "B100") in repo.calls


def test_create_product_rolls_back_and_reraises_on_failure():
    repo = FakeProductRepository()
    repo.raise_on_insert = RuntimeError("insert failed")

    with pytest.raises(RuntimeError, match="insert failed"):
        CreateProductUseCase(repo).execute({"product_code": "P1", "product_name": "منتج"}, store_id=2)

    assert repo.committed is False
    assert repo.rolled_back is True


def test_create_product_accepts_explicit_import_status_over_calculated_state():
    repo = FakeProductRepository()

    product_id = CreateProductUseCase(repo).execute(
        {
            "product_code": "P1",
            "product_name": "منتج",
            "sell_price": 0,
            "buy_price": 0,
            "import_status": "ready",
            "initial_stock": -5,
        },
        store_id=2,
    )

    inserted = next(call[1] for call in repo.calls if call[0] == "insert_product")
    assert product_id == 99
    assert inserted.import_status == "ready"
    assert inserted.import_notes
    assert not any(call[0] == "set_initial_stock" for call in repo.calls)


def test_fix_zero_costs_rolls_back_and_reraises_on_failure():
    repo = FakeProductRepository()
    repo.raise_on_update = RuntimeError("margin failed")

    with pytest.raises(RuntimeError, match="margin failed"):
        FixZeroCostsUseCase(repo).execute(20)

    assert repo.committed is False
    assert repo.rolled_back is True


def test_categories_update_delete_failures_return_false_and_rollback():
    repo = FakeProductRepository()
    repo.raise_on_update = RuntimeError("category failed")
    categories = ProductCategoriesUseCase(repo)

    assert categories.update(1, "أغذية") is False
    assert categories.delete(1) is False

    assert repo.rolled_back is True


def test_category_add_failure_rolls_back_and_reraises():
    repo = FakeProductRepository()
    repo.raise_on_insert = RuntimeError("category insert failed")

    with pytest.raises(RuntimeError, match="category insert failed"):
        ProductCategoriesUseCase(repo).add("أغذية")

    assert repo.rolled_back is True


def test_category_update_rejects_empty_name():
    repo = FakeProductRepository()

    with pytest.raises(ValueError, match="اسم الفئة"):
        ProductCategoriesUseCase(repo).update(1, " ")


def test_inventory_update_failure_rolls_back_and_audits_failure():
    repo = FakeProductRepository()
    audit = FakeAudit()
    repo.raise_on_update = RuntimeError("stock failed")

    result = ProductInventoryUseCase(repo, audit).update(10, 2, 5, user_id=7)

    assert result is False
    assert repo.rolled_back is True
    assert audit.entries[-1]["action"] == ADJUST_INVENTORY_ACTION
    assert audit.entries[-1]["success"] is False
    assert audit.entries[-1]["details"] == {"quantity": 5}


def test_inventory_update_requires_product_and_store():
    repo = FakeProductRepository()
    audit = FakeAudit()

    with pytest.raises(ValueError, match="تحديد المنتج والفرع"):
        ProductInventoryUseCase(repo, audit).update(0, 2, 5)
    with pytest.raises(ValueError, match="تحديد المنتج والفرع"):
        ProductInventoryUseCase(repo, audit).update(10, 0, 5)


def test_product_service_facade_delegates_core_operations():
    product_repo = FakeProductRepository()
    inventory_repo = FakeProductRepository()
    audit = FakeAudit()
    service = ProductServiceFacade(product_repo, inventory_repo, audit)

    assert service.get_products()[1] == 1
    assert service.get_product(10) == product_repo.product
    assert service.create_product({"product_code": "P1", "product_name": "منتج"}, store_id=3) == 99
    assert service.update_product(10, {"sell_price": 11}) is True
    assert service.fix_zero_costs(30) == 4
    assert service.get_categories() == [{"id": 1, "category_name": "غير مصنف"}]
    assert service.add_category("أغذية") == 5
    assert service.get_suppliers() == [{"id": 1, "name": "مورد"}]
    assert service.get_inventory(store_id=2) == [{"product_id": 10, "quantity": 3}]
    assert service.update_stock(10, 2, 8, user_id=7) is True
