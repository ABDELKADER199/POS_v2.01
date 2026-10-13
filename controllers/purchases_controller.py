"""
Purchases Controller
"""
from application.services.purchases_service_facade import PurchasesServiceFacade
from repositories.purchases_repo import PurchasesRepository


class PurchasesController:
    def __init__(self):
        self.service = PurchasesServiceFacade(
            repo=PurchasesRepository(),
        )

    def get_all_suppliers(self):
        return self.service.get_all_suppliers()

    def get_all_stores(self, user_info=None):
        return self.service.get_all_stores(user_info)

    def add_supplier(self, *args, **kwargs):
        return self.service.add_supplier(*args, **kwargs)

    def update_supplier(self, *args, **kwargs):
        return self.service.update_supplier(*args, **kwargs)

    def soft_delete_supplier(self, *args, **kwargs):
        return self.service.soft_delete_supplier(*args, **kwargs)

    def search_product(self, *args, **kwargs):
        return self.service.search_product(*args, **kwargs)

    def save_purchase_invoice(self, *args, **kwargs):
        return self.service.save_purchase_invoice(*args, **kwargs)

    def get_purchase_history(self, *args, **kwargs):
        return self.service.get_purchase_history(*args, **kwargs)

    def get_purchase_invoice_details(self, *args, **kwargs):
        return self.service.get_purchase_invoice_details(*args, **kwargs)

    def create_purchase_return(self, *args, **kwargs):
        return self.service.create_purchase_return(*args, **kwargs)

    def make_supplier_payment(self, *args, **kwargs):
        return self.service.make_supplier_payment(*args, **kwargs)

    def update_purchase_invoice_payment(self, *args, **kwargs):
        return self.service.update_purchase_invoice_payment(*args, **kwargs)
