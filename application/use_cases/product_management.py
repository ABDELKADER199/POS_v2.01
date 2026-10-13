import logging
from typing import Dict, List, Optional

from application.ports.audit_port import AuditPort
from application.ports.product_management_port import (
    ProductCategoryPort,
    ProductInventoryPort,
    ProductManagementPort,
)
from models.product import Product

logger = logging.getLogger(__name__)

DELETE_PRODUCTS_ACTION = "products.delete"
ADJUST_INVENTORY_ACTION = "inventory.adjust"


def product_import_state(sell_price, buy_price, notes: str = None) -> tuple[str, str]:
    sell_price = float(sell_price or 0)
    buy_price = float(buy_price or 0)
    note_parts = [part for part in [notes] if part]
    if sell_price <= 0:
        note_parts.append("ناقص سعر بيع")
        return "needs_pricing", " - ".join(dict.fromkeys(note_parts))
    if buy_price <= 0:
        note_parts.append("ناقص تكلفة")
        return "needs_cost", " - ".join(dict.fromkeys(note_parts))
    return "ready", notes or ""


def save_image_if_needed(product_repo: ProductManagementPort, data: dict) -> str:
    image_source = (data.get("image_source") or "").strip()
    if not image_source:
        return ""
    product_code = data.get("product_code") or data.get("barcode") or "product"
    return product_repo.save_product_image(image_source, product_code)


class ListProductsUseCase:
    def __init__(self, product_repo: ProductManagementPort):
        self.product_repo = product_repo

    def execute(
        self,
        search: str = "",
        category_id: int = None,
        supplier_id: int = None,
        page: int = 1,
        per_page: int = 50,
        column_filters: Dict = None,
    ) -> tuple[List[Product], int]:
        page = max(1, int(page or 1))
        per_page = max(1, int(per_page or 50))
        offset = (page - 1) * per_page
        products = self.product_repo.search(
            search,
            category_id=category_id,
            supplier_id=supplier_id,
            limit=per_page,
            offset=offset,
            column_filters=column_filters,
        )
        total = self.product_repo.count(
            search,
            category_id,
            supplier_id,
            column_filters=column_filters,
        )
        return products, total


class GetProductUseCase:
    def __init__(self, product_repo: ProductManagementPort):
        self.product_repo = product_repo

    def execute(self, product_id: int) -> Optional[Product]:
        return self.product_repo.get_by_id(product_id)


class CreateProductUseCase:
    def __init__(self, product_repo: ProductManagementPort):
        self.product_repo = product_repo

    def execute(self, data: dict, store_id: int = None) -> int:
        if not store_id:
            raise ValueError("يجب تحديد الفرع قبل إضافة المنتج")
        import_status, import_notes = product_import_state(
            data.get("sell_price", 0),
            data.get("buy_price", 0),
            data.get("import_notes"),
        )
        product = Product(
            product_code=data["product_code"],
            product_name=data["product_name"],
            category_id=data.get("category_id", 1),
            supplier_id=data.get("supplier_id"),
            buy_price=data.get("buy_price", 0),
            sell_price=data.get("sell_price", 0),
            unit=data.get("unit", "قطعة"),
            barcode=data.get("barcode") or data["product_code"],
            image_path=save_image_if_needed(self.product_repo, data),
            tax_percent=data.get("tax_percent", 0.0),
            import_status=data.get("import_status") or import_status,
            import_notes=import_notes,
        )
        initial_stock = int(data.get("initial_stock", 0) or 0)
        try:
            product_id = self.product_repo.insert_product(product, store_id)
            if product_id and initial_stock >= 0:
                self.product_repo.set_initial_stock(product_id, int(store_id), initial_stock)
            self.product_repo.commit()
            logger.info("Product created: %s (ID: %s)", product.product_code, product_id)
            return product_id
        except Exception:
            self.product_repo.rollback()
            raise


class UpdateProductUseCase:
    def __init__(self, product_repo: ProductManagementPort):
        self.product_repo = product_repo

    def execute(self, product_id: int, data: dict) -> bool:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise ValueError("المنتج غير موجود")

        product.product_code = data.get("product_code", product.product_code)
        product.product_name = data.get("product_name", product.product_name)
        product.category_id = data.get("category_id", product.category_id)
        product.supplier_id = data.get("supplier_id", product.supplier_id)
        product.buy_price = data.get("buy_price", product.buy_price)
        product.sell_price = data.get("sell_price", product.sell_price)
        product.unit = data.get("unit", product.unit)
        product.barcode = data.get("barcode") or product.product_code
        product.image_path = (
            save_image_if_needed(self.product_repo, data)
            or data.get("image_path")
            or product.image_path
        )
        product.tax_percent = data.get("tax_percent", product.tax_percent)
        product.import_status, product.import_notes = product_import_state(
            product.sell_price,
            product.buy_price,
            data.get("import_notes") or product.import_notes,
        )
        try:
            self.product_repo.update_product_record(product)
            self.product_repo.commit()
            return True
        except Exception as exc:
            self.product_repo.rollback()
            logger.error("Error updating product %s: %s", product.id, exc, exc_info=True)
            return False


class DeleteProductUseCase:
    def __init__(self, product_repo: ProductManagementPort, audit: AuditPort):
        self.product_repo = product_repo
        self.audit = audit

    def execute(self, product_id: int, user_id: int = None) -> bool:
        try:
            self.product_repo.soft_delete_product(product_id)
            self.product_repo.commit()
            success = True
        except Exception as exc:
            self.product_repo.rollback()
            logger.error("Error deleting product %s: %s", product_id, exc, exc_info=True)
            success = False
        self.audit.log(
            user_id,
            DELETE_PRODUCTS_ACTION,
            entity_type="product",
            entity_id=product_id,
            success=success,
        )
        return success


class FixZeroCostsUseCase:
    def __init__(self, product_repo: ProductManagementPort):
        self.product_repo = product_repo

    def execute(self, margin_percent: float = 25.0) -> int:
        if margin_percent < 0 or margin_percent >= 100:
            raise ValueError("هامش الربح يجب أن يكون بين 0 و 99")
        try:
            count = self.product_repo.update_zero_costs_from_margin(margin_percent)
            self.product_repo.commit()
            return count
        except Exception as exc:
            self.product_repo.rollback()
            logger.error("Error fixing zero costs: %s", exc)
            raise


class ProductCategoriesUseCase:
    def __init__(self, product_repo: ProductCategoryPort):
        self.product_repo = product_repo

    def list(self) -> List[Dict]:
        return self.product_repo.get_categories()

    def add(self, category_name: str) -> int:
        category_name = (category_name or "").strip()
        if not category_name:
            raise ValueError("اسم الفئة مطلوب")
        try:
            category_id = self.product_repo.insert_category(category_name)
            self.product_repo.commit()
            return category_id
        except Exception as exc:
            self.product_repo.rollback()
            logger.error("Error adding category: %s", exc)
            raise

    def update(self, category_id: int, category_name: str) -> bool:
        category_name = (category_name or "").strip()
        if not category_name:
            raise ValueError("اسم الفئة مطلوب")
        try:
            self.product_repo.update_category_record(category_id, category_name)
            self.product_repo.commit()
            return True
        except Exception as exc:
            self.product_repo.rollback()
            logger.error("Error updating category %s: %s", category_id, exc)
            return False

    def delete(self, category_id: int) -> bool:
        try:
            self.product_repo.soft_delete_category(category_id)
            self.product_repo.commit()
            return True
        except Exception as exc:
            self.product_repo.rollback()
            logger.error("Error deleting category %s: %s", category_id, exc)
            return False


class ProductSuppliersUseCase:
    def __init__(self, product_repo: ProductManagementPort):
        self.product_repo = product_repo

    def execute(self) -> List[Dict]:
        return self.product_repo.get_suppliers()


class ProductInventoryUseCase:
    def __init__(self, inventory_repo: ProductInventoryPort, audit: AuditPort):
        self.inventory_repo = inventory_repo
        self.audit = audit

    def list(
        self,
        store_id: int = None,
        low_stock_only: bool = False,
        page: int = 1,
        per_page: int = 100,
        search: str = "",
        filters: dict = None,
    ) -> List[Dict]:
        page = max(1, int(page or 1))
        per_page = max(1, int(per_page or 100))
        offset = (page - 1) * per_page
        return self.inventory_repo.get_all_stock(
            store_id=store_id,
            low_stock_only=low_stock_only,
            limit=per_page,
            offset=offset,
            search=search,
            filters=filters,
        )

    def count(
        self,
        store_id: int = None,
        low_stock_only: bool = False,
        search: str = "",
        filters: dict = None,
    ) -> int:
        return self.inventory_repo.count_all_stock(
            store_id=store_id,
            low_stock_only=low_stock_only,
            search=search,
            filters=filters,
        )

    def update(
        self,
        product_id: int,
        store_id: int,
        quantity: int,
        user_id: int = None,
    ) -> bool:
        if not product_id or not store_id:
            raise ValueError("يجب تحديد المنتج والفرع")
        if quantity < 0:
            raise ValueError("كمية المخزون لا يمكن أن تكون سالبة")
        try:
            self.inventory_repo.set_stock(product_id, store_id, quantity)
            self.inventory_repo.commit()
            success = True
        except Exception as exc:
            self.inventory_repo.rollback()
            logger.error("Error updating inventory stock: %s", exc)
            success = False
        self.audit.log(
            user_id,
            ADJUST_INVENTORY_ACTION,
            entity_type="inventory",
            entity_id=product_id,
            store_id=store_id,
            success=success,
            details={"quantity": quantity},
        )
        return success
