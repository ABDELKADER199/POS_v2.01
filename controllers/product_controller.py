"""
Product Controller - متحكم المنتجات
طبقة رقيقة بين واجهة PyQt وخدمات تطبيق المنتجات.
"""
from application.services.product_service_facade import ProductServiceFacade
from repositories.inventory_repo import InventoryRepository
from repositories.product_repo import ProductRepository
from services.audit_service import AuditService


class ProductController:
    """متحكم عمليات إدارة المنتجات"""

    def __init__(self):
        self.service = ProductServiceFacade(
            product_repo=ProductRepository(),
            inventory_repo=InventoryRepository(),
            audit=AuditService(),
        )

    def __getattr__(self, name):
        return getattr(self.service, name)
