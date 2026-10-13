"""
Cashier Controller - متحكم الكاشير
طبقة رقيقة بين واجهة PyQt وخدمات تطبيق الكاشير.
"""

from application.services.cashier_service_facade import CashierServiceFacade
from infrastructure.printer_adapter import ReceiptPrinterAdapter
from repositories.drawer_repo import DrawerRepository
from repositories.inventory_repo import InventoryRepository
from repositories.invoice_repo import InvoiceRepository
from repositories.product_repo import ProductRepository
from repositories.settings_repo import SettingsRepository
from services.audit_service import AuditService


class CashierController:
    """Cashier Controller"""

    def __init__(self):
        from application.services.cashier_service_facade import CashierServiceFacade
        from infrastructure.printer_adapter import ReceiptPrinterAdapter
        from repositories.drawer_repo import DrawerRepository
        from repositories.inventory_repo import InventoryRepository
        from repositories.invoice_repo import InvoiceRepository
        from repositories.product_repo import ProductRepository
        from repositories.settings_repo import SettingsRepository
        from services.audit_service import AuditService

        self.service = CashierServiceFacade(
            product_repo=ProductRepository(),
            invoice_repo=InvoiceRepository(),
            inventory_repo=InventoryRepository(),
            settings_repo=SettingsRepository(),
            drawer_repo=DrawerRepository(),
            audit=AuditService(),
            receipt_printer=ReceiptPrinterAdapter(),
        )

    # Properties
    @property
    def current_items(self): return self.service.current_items
    
    @current_items.setter
    def current_items(self, value): self.service.current_items = value

    @property
    def manual_discount(self): return self.service.manual_discount
    
    @manual_discount.setter
    def manual_discount(self, value): self.service.manual_discount = value

    @property
    def discount_company(self): return self.service.discount_company
    
    @discount_company.setter
    def discount_company(self, value): self.service.discount_company = value

    @property
    def promo_discount(self): return self.service.promo_discount
    
    @promo_discount.setter
    def promo_discount(self, value): self.service.promo_discount = value

    @property
    def applied_promos(self): return self.service.applied_promos
    
    @applied_promos.setter
    def applied_promos(self, value): self.service.applied_promos = value

    @property
    def tax_invoice_data(self): return self.service.tax_invoice_data
    
    @tax_invoice_data.setter
    def tax_invoice_data(self, value): self.service.tax_invoice_data = value

    @property
    def is_tax_invoice(self): return self.service.is_tax_invoice

    # Methods
    def set_discount_company(self, *args, **kwargs): return self.service.set_discount_company(*args, **kwargs)
    def clear_discount_company(self, *args, **kwargs): return self.service.clear_discount_company(*args, **kwargs)
    def get_discount_companies(self, *args, **kwargs): return self.service.get_discount_companies(*args, **kwargs)
    def set_store(self, *args, **kwargs): return self.service.set_store(*args, **kwargs)
    def find_product(self, *args, **kwargs): return self.service.find_product(*args, **kwargs)
    def search_products(self, *args, **kwargs): return self.service.search_products(*args, **kwargs)
    def scan_item(self, *args, **kwargs): return self.service.scan_item(*args, **kwargs)
    def add_item(self, *args, **kwargs): return self.service.add_item(*args, **kwargs)
    def update_item_quantity(self, *args, **kwargs): return self.service.update_item_quantity(*args, **kwargs)
    def remove_item(self, *args, **kwargs): return self.service.remove_item(*args, **kwargs)
    def clear_cart(self, *args, **kwargs): return self.service.clear_cart(*args, **kwargs)
    def set_tax_invoice(self, *args, **kwargs): return self.service.set_tax_invoice(*args, **kwargs)
    def clear_tax_invoice(self, *args, **kwargs): return self.service.clear_tax_invoice(*args, **kwargs)
    def calculate_totals(self, *args, **kwargs): return self.service.calculate_totals(*args, **kwargs)
    def checkout(self, *args, **kwargs): return self.service.checkout(*args, **kwargs)
    def get_print_data(self, *args, **kwargs): return self.service.get_print_data(*args, **kwargs)
    def print_receipt(self, *args, **kwargs): return self.service.print_receipt(*args, **kwargs)
    def get_settings(self, *args, **kwargs): return self.service.get_settings(*args, **kwargs)
    def get_customer_by_phone(self, *args, **kwargs): return self.service.get_customer_by_phone(*args, **kwargs)
    def get_stock(self, *args, **kwargs): return self.service.get_stock(*args, **kwargs)
    def get_drawer_status(self, *args, **kwargs): return self.service.get_drawer_status(*args, **kwargs)
    def get_store_open_drawer(self, *args, **kwargs): return self.service.get_store_open_drawer(*args, **kwargs)
    def get_any_open_drawer(self, *args, **kwargs): return self.service.get_any_open_drawer(*args, **kwargs)
    def get_operational_stores(self, *args, **kwargs): return self.service.get_operational_stores(*args, **kwargs)
    def open_drawer(self, *args, **kwargs): return self.service.open_drawer(*args, **kwargs)
    def close_drawer(self, *args, **kwargs): return self.service.close_drawer(*args, **kwargs)
    def save_held_invoice(self, *args, **kwargs): return self.service.save_held_invoice(*args, **kwargs)
    def get_held_invoices(self, *args, **kwargs): return self.service.get_held_invoices(*args, **kwargs)
    def delete_held_invoice(self, *args, **kwargs): return self.service.delete_held_invoice(*args, **kwargs)
    def resume_held_invoice(self, *args, **kwargs): return self.service.resume_held_invoice(*args, **kwargs)
    def delete_resumed_held_invoice(self, *args, **kwargs): return self.service.delete_resumed_held_invoice(*args, **kwargs)
    def get_recent_invoices(self, *args, **kwargs): return self.service.get_recent_invoices(*args, **kwargs)
    def get_completed_invoices(self, *args, **kwargs): return self.service.get_completed_invoices(*args, **kwargs)
    def get_invoice_by_id(self, *args, **kwargs): return self.service.get_invoice_by_id(*args, **kwargs)
    def get_invoice_items_by_id(self, *args, **kwargs): return self.service.get_invoice_items_by_id(*args, **kwargs)
    def get_invoice_items(self, *args, **kwargs): return self.service.get_invoice_items(*args, **kwargs)
    def get_open_orders(self, *args, **kwargs): return self.service.get_open_orders(*args, **kwargs)
    def load_order_items(self, *args, **kwargs): return self.service.load_order_items(*args, **kwargs)
    def mark_order_delivered(self, *args, **kwargs): return self.service.mark_order_delivered(*args, **kwargs)
    def get_product_cross_branch_stock(self, *args, **kwargs): return self.service.get_product_cross_branch_stock(*args, **kwargs)
