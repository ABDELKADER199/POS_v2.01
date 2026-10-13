from application.use_cases.purchases import (
    AddSupplierUseCase,
    CreatePurchaseInvoiceUseCase,
    CreatePurchaseReturnUseCase,
    PurchaseInvoiceDetailsUseCase,
    ListSuppliersUseCase,
    PayPurchaseInvoiceUseCase,
    PurchaseHistoryUseCase,
    SearchPurchaseProductUseCase,
    SoftDeleteSupplierUseCase,
    SupplierPaymentUseCase,
    UpdateSupplierUseCase,
)


class PurchasesServiceFacade:
    def __init__(self, repo):
        self.repo = repo
        self.repo.ensure_purchase_columns()
        self.list_suppliers_use_case = ListSuppliersUseCase(self.repo)
        self.add_supplier_use_case = AddSupplierUseCase(self.repo)
        self.update_supplier_use_case = UpdateSupplierUseCase(self.repo)
        self.soft_delete_supplier_use_case = SoftDeleteSupplierUseCase(self.repo)
        self.search_product_use_case = SearchPurchaseProductUseCase(self.repo)
        self.create_invoice_use_case = CreatePurchaseInvoiceUseCase(self.repo)
        self.purchase_invoice_details_use_case = PurchaseInvoiceDetailsUseCase(self.repo)
        self.create_purchase_return_use_case = CreatePurchaseReturnUseCase(self.repo)
        self.purchase_history_use_case = PurchaseHistoryUseCase(self.repo)
        self.supplier_payment_use_case = SupplierPaymentUseCase(self.repo)
        self.pay_invoice_use_case = PayPurchaseInvoiceUseCase(self.repo)

    def get_all_suppliers(self):
        return self.list_suppliers_use_case.execute()

    def get_all_stores(self, user_info=None):
        return self.repo.get_all_stores()

    def add_supplier(self, name, phone, address, tax_number, opening_balance):
        return self.add_supplier_use_case.execute(name, phone, address, tax_number, opening_balance)

    def update_supplier(self, supplier_id, name, phone, address, tax_number):
        return self.update_supplier_use_case.execute(supplier_id, name, phone, address, tax_number)

    def soft_delete_supplier(self, supplier_id):
        return self.soft_delete_supplier_use_case.execute(supplier_id)

    def search_product(self, term):
        return self.search_product_use_case.execute(term)

    def save_purchase_invoice(
        self,
        supplier_id,
        store_id,
        user_id,
        ref_number,
        items,
        subtotal,
        discount,
        tax,
        total,
        paid,
        payment_method,
    ):
        return self.create_invoice_use_case.execute(
            supplier_id,
            store_id,
            user_id,
            ref_number,
            items,
            subtotal,
            discount,
            tax,
            total,
            paid,
            payment_method,
        )

    def get_purchase_history(self, page=1, per_page=100):
        return self.purchase_history_use_case.execute(page, per_page)

    def get_purchase_invoice_details(self, search_term):
        return self.purchase_invoice_details_use_case.execute(search_term)

    def create_purchase_return(self, invoice_id, supplier_id, store_id, user_id, items, settlement_method, reason=""):
        return self.create_purchase_return_use_case.execute(
            invoice_id,
            supplier_id,
            store_id,
            user_id,
            items,
            settlement_method,
            reason,
        )

    def make_supplier_payment(self, supplier_id, amount, user_id, store_id):
        return self.supplier_payment_use_case.execute(supplier_id, amount, store_id, user_id)

    def update_purchase_invoice_payment(self, invoice_id, amount, payment_method, user_id, store_id):
        return self.pay_invoice_use_case.execute(invoice_id, amount, payment_method, user_id, store_id)
