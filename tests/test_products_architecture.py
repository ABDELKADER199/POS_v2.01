"""اختبار المعمارية النظيفة لصفحة إدارة المنتجات"""
import sys
sys.path.insert(0, '.')

def test_all_layers():
    # 1. Model
    from models.product import Product
    p = Product.from_dict({
        'id': 1, 'product_code': 'P001', 'product_name': 'منتج تجريبي',
        'buy_price': 50, 'sell_price': 75, 'unit': 'قطعة', 'is_active': True
    })
    assert p.product_code == 'P001'
    assert p.sell_price == 75.0
    print("✓ Layer 5 (Model): OK")

    # 2. Repository
    from repositories.product_repo import ProductRepository
    from repositories.inventory_repo import InventoryRepository
    repo = ProductRepository()
    inv_repo = InventoryRepository()
    print("✓ Layer 4 (Repository): OK")

    # 3. Service Facade
    from application.services.product_service_facade import ProductServiceFacade
    from repositories.product_repo import ProductRepository
    from repositories.inventory_repo import InventoryRepository
    from services.audit_service import AuditService
    facade = ProductServiceFacade(
        ProductRepository(), InventoryRepository(), AuditService()
    )
    print("✓ Layer 3 (Service Facade): OK")

    # 4. Controller
    from controllers.product_controller import ProductController
    ctrl = ProductController()
    print("✓ Layer 2 (Controller): OK")

    # 5. View
    from ui.product_view import ProductView, FilterSortHeader, ProductDialog
    print("✓ Layer 1 (UI / View): OK")

    print("=== جميع طبقات المعمارية النظيفة لصفحة إدارة المنتجات مكتملة ===")

if __name__ == '__main__':
    test_all_layers()
