"""
Accounts Controller - صفحة الحسابات
    PyQt   .
"""
from application.services.accounts_service_facade import AccountsServiceFacade
from repositories.accounts_repo import AccountsRepository
from services.audit_service import AuditService


class AccountsController:
    def __init__(self):
        self.service = AccountsServiceFacade(
            repo=AccountsRepository(),
            audit=AuditService(),
        )

    def get_customer_accounts(self, *args, **kwargs): return self.service.get_customer_accounts(*args, **kwargs)
    def update_credit_limit(self, *args, **kwargs): return self.service.update_credit_limit(*args, **kwargs)
    def get_all_suppliers(self, *args, **kwargs): return self.service.get_all_suppliers(*args, **kwargs)
    def record_payment(self, *args, **kwargs): return self.service.record_payment(*args, **kwargs)
    def record_settlement(self, *args, **kwargs): return self.service.record_settlement(*args, **kwargs)
    def get_account_history(self, *args, **kwargs): return self.service.get_account_history(*args, **kwargs)
    def get_financial_ledger(self, *args, **kwargs): return self.service.get_financial_ledger(*args, **kwargs)
    def get_debt_totals(self, *args, **kwargs): return self.service.get_debt_totals(*args, **kwargs)
    def get_debt_aging_report(self, *args, **kwargs): return self.service.get_debt_aging_report(*args, **kwargs)
    def get_treasury_transactions(self, *args, **kwargs): return self.service.get_treasury_transactions(*args, **kwargs)
    def get_treasury_balance(self, *args, **kwargs): return self.service.get_treasury_balance(*args, **kwargs)
    def record_treasury_transaction(self, *args, **kwargs): return self.service.record_treasury_transaction(*args, **kwargs)
    def get_expenses(self, *args, **kwargs): return self.service.get_expenses(*args, **kwargs)
    def add_expense(self, *args, **kwargs): return self.service.add_expense(*args, **kwargs)
    def delete_expense(self, *args, **kwargs): return self.service.delete_expense(*args, **kwargs)
    def get_financial_report(self, *args, **kwargs): return self.service.get_financial_report(*args, **kwargs)
    def get_promotion_categories(self, *args, **kwargs): return self.service.get_promotion_categories(*args, **kwargs)
    def search_promotion_products(self, *args, **kwargs): return self.service.search_promotion_products(*args, **kwargs)
    def get_all_promotions(self, *args, **kwargs): return self.service.get_all_promotions(*args, **kwargs)
    def add_promotion(self, *args, **kwargs): return self.service.add_promotion(*args, **kwargs)
    def update_promotion(self, *args, **kwargs): return self.service.update_promotion(*args, **kwargs)
    def get_last_promotion_error(self, *args, **kwargs): return self.service.get_last_promotion_error(*args, **kwargs)
    def toggle_promotion(self, *args, **kwargs): return self.service.toggle_promotion(*args, **kwargs)
    def delete_promotion(self, *args, **kwargs): return self.service.delete_promotion(*args, **kwargs)
    def create_promotions_catalog_pdf(self, *args, **kwargs): return self.service.create_promotions_catalog_pdf(*args, **kwargs)
    def get_all_stores(self, *args, **kwargs): return self.service.get_all_stores(*args, **kwargs)
    def get_discount_companies(self, *args, **kwargs): return self.service.get_discount_companies(*args, **kwargs)
    def add_discount_company(self, *args, **kwargs): return self.service.add_discount_company(*args, **kwargs)
    def update_discount_company(self, *args, **kwargs): return self.service.update_discount_company(*args, **kwargs)
    def delete_discount_company(self, *args, **kwargs): return self.service.delete_discount_company(*args, **kwargs)
    def get_last_discount_company_error(self, *args, **kwargs): return self.service.get_last_discount_company_error(*args, **kwargs)
    def search_discount_eligible_products(self, *args, **kwargs): return self.service.search_discount_eligible_products(*args, **kwargs)
    def create_customer_account_pdf(self, *args, **kwargs): return self.service.create_customer_account_pdf(*args, **kwargs)
    def create_debt_aging_pdf(self, *args, **kwargs): return self.service.create_debt_aging_pdf(*args, **kwargs)
    def create_ledger_pdf(self, *args, **kwargs): return self.service.create_ledger_pdf(*args, **kwargs)
    def create_treasury_pdf(self, *args, **kwargs): return self.service.create_treasury_pdf(*args, **kwargs)
    def create_expense_pdf(self, *args, **kwargs): return self.service.create_expense_pdf(*args, **kwargs)
