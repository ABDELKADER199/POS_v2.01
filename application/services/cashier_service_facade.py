import logging
from typing import Dict, List, Optional

from application.use_cases.cashier_cart import CashierCartUseCase
from application.use_cases.cashier_queries import (
    FindCustomerByPhoneUseCase,
    GetCrossBranchStockUseCase,
    GetSettingsUseCase,
    GetStockUseCase,
)
from application.use_cases.checkout_sale import CheckoutSaleUseCase
from application.use_cases.held_invoices import (
    DeleteHeldInvoiceUseCase,
    ListHeldInvoicesUseCase,
    ResumeHeldInvoiceUseCase,
    SaveHeldInvoiceUseCase,
)
from application.use_cases.invoice_history import InvoiceHistoryUseCase
from application.use_cases.manage_drawer import (
    CloseDrawerUseCase,
    DrawerQueryUseCase,
    OpenDrawerUseCase,
)
from application.use_cases.open_orders import (
    ListOpenOrdersUseCase,
    LoadOrderItemsUseCase,
    MarkOrderDeliveredUseCase,
)
from application.use_cases.print_receipt import PrintReceiptUseCase
from application.use_cases.product_lookup import ProductLookupUseCase
from application.use_cases.receipt_data import ReceiptDataUseCase
from application.use_cases.scan_product import ScanProductUseCase
from application.use_cases.tax_invoice import TaxInvoiceUseCase
from models.invoice import InvoiceItem, TaxInvoiceDetails
from models.product import Product

logger = logging.getLogger(__name__)


class CashierServiceFacade:
    def __init__(
        self,
        product_repo,
        invoice_repo,
        inventory_repo,
        settings_repo,
        drawer_repo,
        audit,
        receipt_printer,
    ):
        self.active_store_id: int = None
        self.invoice_repo = invoice_repo
        self.cart_use_case = CashierCartUseCase(inventory_repo, invoice_repo)
        self.get_settings_use_case = GetSettingsUseCase(settings_repo)
        self.find_customer_by_phone_use_case = FindCustomerByPhoneUseCase(invoice_repo)
        self.get_stock_use_case = GetStockUseCase(
            inventory_repo, lambda: self.active_store_id
        )
        self.get_cross_branch_stock_use_case = GetCrossBranchStockUseCase(invoice_repo)
        self.product_lookup_use_case = ProductLookupUseCase(product_repo)
        self.scan_product_use_case = ScanProductUseCase(
            self.product_lookup_use_case, self.cart_use_case
        )
        self.save_held_invoice_use_case = SaveHeldInvoiceUseCase(
            invoice_repo, self.cart_use_case
        )
        self.list_held_invoices_use_case = ListHeldInvoicesUseCase(invoice_repo)
        self.delete_held_invoice_use_case = DeleteHeldInvoiceUseCase(invoice_repo)
        self.resume_held_invoice_use_case = ResumeHeldInvoiceUseCase(
            invoice_repo, self.cart_use_case
        )
        self.invoice_history_use_case = InvoiceHistoryUseCase(invoice_repo)
        self.list_open_orders_use_case = ListOpenOrdersUseCase(invoice_repo)
        self.load_order_items_use_case = LoadOrderItemsUseCase(
            invoice_repo,
            inventory_repo,
            self.cart_use_case,
        )
        self.mark_order_delivered_use_case = MarkOrderDeliveredUseCase(invoice_repo)
        self.drawer_query_use_case = DrawerQueryUseCase(drawer_repo)
        self.open_drawer_use_case = OpenDrawerUseCase(drawer_repo, audit)
        self.close_drawer_use_case = CloseDrawerUseCase(drawer_repo, audit)
        self.tax_invoice_use_case = TaxInvoiceUseCase()
        self.checkout_use_case = CheckoutSaleUseCase(
            invoice_repo,
            self.calculate_totals,
            self._promo_discount_for_product,
            lambda: self.current_items,
            lambda: self.tax_invoice_data,
            self._company_promo_discount_for_product,
            self._supplier_promotion_claims,
        )
        self.receipt_data_use_case = ReceiptDataUseCase(
            lambda: self.current_items,
            self.calculate_totals,
            lambda: self.applied_promos,
            lambda: self.tax_invoice_data,
        )
        self.print_receipt_use_case = PrintReceiptUseCase(receipt_printer)

    @property
    def current_items(self) -> List[InvoiceItem]:
        return self.cart_use_case.items

    @current_items.setter
    def current_items(self, value: List[InvoiceItem]):
        self.cart_use_case.items = value

    @property
    def manual_discount(self) -> float:
        return self.cart_use_case.manual_discount

    @manual_discount.setter
    def manual_discount(self, value: float):
        self.cart_use_case.manual_discount = float(value or 0)

    @property
    def promo_discount(self) -> float:
        return self.cart_use_case.promo_discount

    @promo_discount.setter
    def promo_discount(self, value: float):
        self.cart_use_case.promo_discount = float(value or 0)

    @property
    def applied_promos(self) -> List[Dict]:
        return self.cart_use_case.applied_promos

    @applied_promos.setter
    def applied_promos(self, value: List[Dict]):
        self.cart_use_case.applied_promos = value

    @property
    def is_tax_invoice(self) -> bool:
        return self.tax_invoice_use_case.is_enabled()

    @property
    def tax_invoice_data(self) -> Optional[TaxInvoiceDetails]:
        return self.tax_invoice_use_case.data

    @tax_invoice_data.setter
    def tax_invoice_data(self, value: Optional[TaxInvoiceDetails]):
        self.tax_invoice_use_case.data = value

    @property
    def discount_company(self):
        return self.cart_use_case.discount_company

    def set_discount_company(self, company):
        self.cart_use_case.set_discount_company(company)

    def clear_discount_company(self):
        self.cart_use_case.clear_discount_company()

    def get_discount_companies(self):
        return self.invoice_repo.get_discount_companies(active_only=True)

    def set_store(self, store_id: int):
        if not store_id:
            raise ValueError("لا يوجد فرع تشغيل محدد")
        self.active_store_id = int(store_id)
        self.cart_use_case.set_store(store_id)

    def find_product(self, search_term: str) -> Optional[Product]:
        return self.product_lookup_use_case.find_sellable_product(search_term)

    def search_products(self, term: str, limit: int = 20) -> List[Product]:
        return self.product_lookup_use_case.search_sellable_products(term, limit=limit)

    def scan_item(self, search_term: str, quantity: float = 1.0):
        return self.scan_product_use_case.execute(search_term, quantity)

    def add_item(self, product: Product, quantity: float = 1.0) -> List[InvoiceItem]:
        return self.cart_use_case.add_item(product, quantity)

    def update_item_quantity(self, index: int, quantity: float) -> List[InvoiceItem]:
        return self.cart_use_case.update_item_quantity(index, quantity)

    def remove_item(self, index: int) -> List[InvoiceItem]:
        return self.cart_use_case.remove_item(index)

    def clear_cart(self):
        self.cart_use_case.clear()
        self.tax_invoice_use_case.clear()

    def set_tax_invoice(self, data: dict):
        self.tax_invoice_use_case.set(data)

    def clear_tax_invoice(self):
        self.tax_invoice_use_case.clear()

    def calculate_totals(self) -> Dict:
        return self.cart_use_case.calculate_totals()

    def _promo_discount_for_product(self, product_id: int) -> float:
        return self.cart_use_case.promo_discount_for_product(product_id)

    def _company_promo_discount_for_product(self, product_id: int) -> float:
        return self.cart_use_case.company_promo_discount_for_product(product_id)

    def _supplier_promotion_claims(self) -> List[Dict]:
        return self.cart_use_case.supplier_promotion_claims()

    def checkout(
        self,
        store_id: int,
        cashier_id: int,
        drawer_id: int,
        payment_method: str,
        cash_amount: float,
        card_amount: float,
        customer_name: str = "",
        customer_phone: str = "",
        customer_address: str = "",
    ) -> Optional[str]:
        invoice_number = self.checkout_use_case.execute(
            store_id=store_id,
            cashier_id=cashier_id,
            drawer_id=drawer_id,
            payment_method=payment_method,
            cash_amount=cash_amount,
            card_amount=card_amount,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
        )
        logger.info("✅ Checkout complete: Invoice #%s", invoice_number)
        return invoice_number

    def get_print_data(
        self,
        invoice_number: str,
        drawer_id: int,
        payment_method: str,
        cash_amount: float,
        card_amount: float,
        paid_amount: float,
        customer_name: str = "",
        customer_phone: str = "",
        customer_address: str = "",
    ) -> tuple[Dict, List[Dict]]:
        return self.receipt_data_use_case.execute(
            invoice_number,
            drawer_id,
            payment_method,
            cash_amount,
            card_amount,
            paid_amount,
            customer_name,
            customer_phone,
            customer_address,
        )

    def print_receipt(
        self, invoice: dict, items: list[dict], cashier_name: str, as_pdf: bool = False
    ):
        return self.print_receipt_use_case.execute(invoice, items, cashier_name, as_pdf)

    def get_settings(self) -> Dict:
        return self.get_settings_use_case.execute()

    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        return self.find_customer_by_phone_use_case.execute(phone)

    def get_stock(self, product_id: int, store_id: int = None) -> int:
        return self.get_stock_use_case.execute(product_id, store_id)

    def get_drawer_status(self, user_id: int) -> Optional[Dict]:
        return self.drawer_query_use_case.get_drawer_status(user_id)

    def get_store_open_drawer(self, store_id: int) -> Optional[Dict]:
        return self.drawer_query_use_case.get_store_open_drawer(store_id)

    def get_any_open_drawer(self) -> Optional[Dict]:
        return self.drawer_query_use_case.get_any_open_drawer()

    def get_operational_stores(self) -> List[Dict]:
        return self.drawer_query_use_case.get_operational_stores()

    def open_drawer(
        self, store_id: int, user_id: int, opening_balance: float = 0
    ) -> bool:
        return self.open_drawer_use_case.execute(store_id, user_id, opening_balance)

    def close_drawer(
        self,
        drawer_id: int,
        cash_amount: float,
        card_amount: float = 0,
        user_id: int = None,
        store_id: int = None,
        details: dict = None,
    ) -> bool:
        denom_details = details or {"Cash": cash_amount, "Visa": card_amount}
        # Ensure Visa is in details for compatibility
        if details and "Visa" not in denom_details:
            denom_details["Visa"] = card_amount
            
        return self.close_drawer_use_case.execute(
            drawer_id,
            cash_amount,
            denom_details,
            user_id,
            store_id,
        )

    def save_held_invoice(
        self,
        store_id: int,
        cashier_id: int,
        customer_name: str = "",
        customer_phone: str = "",
        customer_address: str = "",
    ) -> bool:
        return self.save_held_invoice_use_case.execute(
            store_id,
            cashier_id,
            customer_name,
            customer_phone,
            customer_address,
        )

    def get_held_invoices(self, store_id: int, search_term: str = None) -> List[Dict]:
        return self.list_held_invoices_use_case.execute(store_id, search_term)

    def delete_held_invoice(self, temp_invoice_id: int) -> bool:
        return self.delete_held_invoice_use_case.execute(temp_invoice_id)

    def resume_held_invoice(self, temp_invoice_id: int) -> bool:
        return self.resume_held_invoice_use_case.execute(temp_invoice_id)

    def delete_resumed_held_invoice(self, temp_invoice_id: int) -> bool:
        return self.delete_held_invoice(temp_invoice_id)

    def get_recent_invoices(self, store_id: int = None, limit: int = 50) -> List[Dict]:
        return self.invoice_history_use_case.get_recent_invoices(store_id, limit)

    def get_completed_invoices(
        self,
        store_id: int,
        search_term: str = None,
        start_date: str = None,
        end_date: str = None,
    ) -> List[Dict]:
        return self.invoice_history_use_case.get_completed_invoices(
            store_id,
            search_term,
            start_date,
            end_date,
        )

    def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict]:
        return self.invoice_history_use_case.get_invoice_by_id(invoice_id)

    def get_invoice_items_by_id(self, invoice_id: int) -> List[Dict]:
        return self.invoice_history_use_case.get_invoice_items_by_id(invoice_id)

    def get_invoice_items(self, invoice_number: str) -> List[Dict]:
        return self.invoice_history_use_case.get_invoice_items(invoice_number)

    def get_open_orders(self, store_id: int, search_term: str = None) -> List[Dict]:
        return self.list_open_orders_use_case.execute(store_id, search_term)

    def load_order_items(self, order_id: int) -> bool:
        return self.load_order_items_use_case.execute(order_id)

    def mark_order_delivered(self, order_id: int) -> bool:
        return self.mark_order_delivered_use_case.execute(order_id)

    def get_product_cross_branch_stock(self, search_term: str) -> Dict:
        return self.get_cross_branch_stock_use_case.execute(search_term)
