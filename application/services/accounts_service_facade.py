from application.use_cases.accounts import (
    AccountsQueryUseCase,
    CreatePromotionsCatalogUseCase,
    DiscountCompaniesUseCase,
    ExpenseUseCase,
    PromotionsUseCase,
    RecordAccountPaymentUseCase,
    RecordSettlementUseCase,
    TreasuryTransactionUseCase,
    UpdateCreditLimitUseCase,
)
from services.promotion_catalog_service import PromotionCatalogService
from services.accounts_pdf_service import AccountsPdfReportService


class AccountsServiceFacade:
    def __init__(self, repo, audit):
        self.queries = AccountsQueryUseCase(repo)
        self.update_credit_limit_use_case = UpdateCreditLimitUseCase(repo, audit)
        self.record_payment_use_case = RecordAccountPaymentUseCase(repo, audit)
        self.record_settlement_use_case = RecordSettlementUseCase(repo, audit)
        self.treasury_transaction_use_case = TreasuryTransactionUseCase(repo, audit)
        self.expense_use_case = ExpenseUseCase(repo, audit)
        self.promotions_use_case = PromotionsUseCase(repo)
        self.discount_companies_use_case = DiscountCompaniesUseCase(repo)
        self.promotions_catalog_use_case = CreatePromotionsCatalogUseCase(
            PromotionCatalogService(repo)
        )

    def get_customer_accounts(self):
        return self.queries.get_customer_accounts()

    def update_credit_limit(self, cid, limit):
        return self.update_credit_limit_use_case.execute(cid, limit)

    def get_all_suppliers(self):
        return self.queries.get_all_suppliers()

    def record_payment(
        self, account_type, account_id, amount, user_id, desc, attachment_path=""
    ):
        return self.record_payment_use_case.execute(
            account_type,
            account_id,
            amount,
            user_id,
            desc,
            attachment_path,
        )

    def record_settlement(
        self, account_type, account_id, amount, desc, user_id, attachment_path=""
    ):
        return self.record_settlement_use_case.execute(
            account_type,
            account_id,
            amount,
            desc,
            user_id,
            attachment_path,
        )

    def get_account_history(self, account_type, account_id):
        return self.queries.get_account_history(account_type, account_id)

    def get_financial_ledger(self, search="", acc_type=""):
        return self.queries.get_financial_ledger(search, acc_type)

    def get_debt_totals(self):
        return self.queries.get_debt_totals()

    def get_debt_aging_report(self):
        return self.queries.get_debt_aging_report()

    def get_treasury_transactions(self):
        return self.queries.get_treasury_transactions()

    def get_treasury_balance(self):
        return self.queries.get_treasury_balance()

    def record_treasury_transaction(
        self, store_id, trans_type, amount, source_type, source_id, desc, user_id
    ):
        return self.treasury_transaction_use_case.execute(
            store_id,
            trans_type,
            amount,
            source_type,
            source_id,
            desc,
            user_id,
        )

    def get_expenses(self, store_id):
        return self.queries.get_expenses(store_id)

    def add_expense(self, store_id, user_id, expense_type, amount, desc, is_personal):
        return self.expense_use_case.add(
            store_id, user_id, expense_type, amount, desc, is_personal
        )

    def delete_expense(self, expense_id, user_id=None, reason=""):
        return self.expense_use_case.void(expense_id, user_id, reason)

    def get_financial_report(self, store_id, start_date, end_date):
        return self.queries.get_financial_report(store_id, start_date, end_date)

    def get_promotion_categories(self):
        return self.promotions_use_case.get_categories()

    def search_promotion_products(self, term=""):
        return self.promotions_use_case.search_products(term)

    def get_all_promotions(self):
        return self.promotions_use_case.list()

    def add_promotion(self, **kwargs):
        return self.promotions_use_case.add(**kwargs)

    def update_promotion(self, promo_id, **kwargs):
        return self.promotions_use_case.update(promo_id, **kwargs)

    def get_last_promotion_error(self):
        return getattr(self.promotions_use_case, "last_error", "")

    def toggle_promotion(self, promo_id):
        return self.promotions_use_case.toggle(promo_id)

    def delete_promotion(self, promo_id):
        return self.promotions_use_case.delete(promo_id)

    def create_promotions_catalog_pdf(
        self, download_missing_images=True, refresh_images=True
    ):
        return self.promotions_catalog_use_case.execute(
            download_missing_images, refresh_images
        )

    def get_all_stores(self):
        return self.queries.get_all_stores()

    def get_discount_companies(self, active_only=False):
        return self.discount_companies_use_case.list(active_only)

    def add_discount_company(self, name, discount_percent, product_ids=None):
        return self.discount_companies_use_case.add(name, discount_percent, product_ids)

    def update_discount_company(
        self, company_id, name, discount_percent, is_active=True, product_ids=None
    ):
        return self.discount_companies_use_case.update(
            company_id, name, discount_percent, is_active, product_ids
        )

    def delete_discount_company(self, company_id):
        return self.discount_companies_use_case.delete(company_id)

    def get_last_discount_company_error(self):
        return self.discount_companies_use_case.last_error

    def search_discount_eligible_products(self, term="", min_margin_percent=0.0):
        return self.discount_companies_use_case.search_eligible_products(term, min_margin_percent)

    def check_product_has_offer_or_discount(
        self, product_ids, exclude_promo_id=None, exclude_company_id=None
    ):
        if hasattr(self.repo, "check_product_has_offer_or_discount"):
            return self.repo.check_product_has_offer_or_discount(
                product_ids, exclude_promo_id, exclude_company_id
            )
        return []

    # ── PDF Reports ────────────────────────────────────

    def create_customer_account_pdf(
        self, customer_data, account_history, user_name, store_name
    ):
        """إنشاء تقرير حساب عميل بصيغة PDF"""
        pdf_service = AccountsPdfReportService()
        return pdf_service.create_customer_account_pdf(
            customer_data, account_history, user_name, store_name
        )

    def create_debt_aging_pdf(self, aging_data, store_name, user_name):
        """إنشاء تقرير تقادم الديون بصيغة PDF"""
        pdf_service = AccountsPdfReportService()
        return pdf_service.create_debt_aging_pdf(aging_data, store_name, user_name)

    def create_ledger_pdf(self, ledger_data, store_name, user_name):
        """إنشاء تقرير السجل المالي بصيغة PDF"""
        pdf_service = AccountsPdfReportService()
        return pdf_service.create_financial_ledger_pdf(
            ledger_data, store_name, user_name
        )

    def create_treasury_pdf(self, transactions, balance, store_name, user_name):
        """إنشاء تقرير حركة الخزينة بصيغة PDF"""
        pdf_service = AccountsPdfReportService()
        return pdf_service.create_treasury_pdf(
            transactions, balance, store_name, user_name
        )

    def create_expense_pdf(self, expenses, store_name, user_name):
        """إنشاء تقرير المصروفات بصيغة PDF"""
        pdf_service = AccountsPdfReportService()
        return pdf_service.create_expense_pdf(expenses, store_name, user_name)
