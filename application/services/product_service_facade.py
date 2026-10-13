from typing import Dict, List, Optional

from application.use_cases.import_products import ProductImportUseCase
from application.use_cases.product_management import (
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


class ProductServiceFacade:
    def __init__(self, product_repo, inventory_repo, audit):
        self.product_import_use_case = ProductImportUseCase(product_repo)
        self.list_products_use_case = ListProductsUseCase(product_repo)
        self.get_product_use_case = GetProductUseCase(product_repo)
        self.create_product_use_case = CreateProductUseCase(product_repo)
        self.update_product_use_case = UpdateProductUseCase(product_repo)
        self.delete_product_use_case = DeleteProductUseCase(product_repo, audit)
        self.fix_zero_costs_use_case = FixZeroCostsUseCase(product_repo)
        self.product_categories_use_case = ProductCategoriesUseCase(product_repo)
        self.product_suppliers_use_case = ProductSuppliersUseCase(product_repo)
        self.product_inventory_use_case = ProductInventoryUseCase(inventory_repo, audit)

    def get_products(
        self,
        search: str = "",
        category_id: int = None,
        supplier_id: int = None,
        page: int = 1,
        per_page: int = 50,
        column_filters: Dict = None,
    ) -> tuple[List[Product], int]:
        return self.list_products_use_case.execute(
            search,
            category_id,
            supplier_id,
            page,
            per_page,
            column_filters,
        )

    def get_product(self, product_id: int) -> Optional[Product]:
        return self.get_product_use_case.execute(product_id)

    def create_product(self, data: dict, store_id: int = None) -> int:
        return self.create_product_use_case.execute(data, store_id)

    def update_product(self, product_id: int, data: dict) -> bool:
        return self.update_product_use_case.execute(product_id, data)

    def delete_product(self, product_id: int, user_id: int = None) -> bool:
        return self.delete_product_use_case.execute(product_id, user_id)

    def fix_zero_costs(self, margin_percent: float = 25.0) -> int:
        return self.fix_zero_costs_use_case.execute(margin_percent)

    def get_categories(self) -> List[Dict]:
        return self.product_categories_use_case.list()

    def add_category(self, category_name: str) -> int:
        return self.product_categories_use_case.add(category_name)

    def update_category(self, category_id: int, category_name: str) -> bool:
        return self.product_categories_use_case.update(category_id, category_name)

    def delete_category(self, category_id: int) -> bool:
        return self.product_categories_use_case.delete(category_id)

    def get_suppliers(self) -> List[Dict]:
        return self.product_suppliers_use_case.execute()

    def get_inventory(
        self,
        store_id: int = None,
        low_stock_only: bool = False,
        page: int = 1,
        per_page: int = 100,
        search: str = "",
        filters: dict = None,
    ) -> List[Dict]:
        return self.product_inventory_use_case.list(store_id, low_stock_only, page, per_page, search, filters)

    def get_inventory_count(
        self,
        store_id: int = None,
        low_stock_only: bool = False,
        search: str = "",
        filters: dict = None,
    ) -> int:
        return self.product_inventory_use_case.count(store_id, low_stock_only, search, filters)

    def update_stock(
        self,
        product_id: int,
        store_id: int,
        quantity: int,
        user_id: int = None,
    ) -> bool:
        return self.product_inventory_use_case.update(product_id, store_id, quantity, user_id)

    def preview_import_file(self, file_path: str) -> Dict:
        return self.product_import_use_case.preview_import_file(file_path)

    def commit_import_preview(
        self,
        rows: List[Dict],
        store_id: int,
        include_incomplete: bool = True,
    ) -> Dict:
        return self.product_import_use_case.commit_import_preview(
            rows,
            store_id,
            include_incomplete,
        )

    def import_from_excel(self, file_path: str, store_id: int, progress_callback=None) -> Dict:
        return self.product_import_use_case.import_from_excel(file_path, store_id)

    def product_import_state(self, sell_price, buy_price, notes: str = None) -> tuple[str, str]:
        return product_import_state(sell_price, buy_price, notes)
