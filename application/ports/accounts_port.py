from typing import Dict, List, Protocol


class AccountsRepositoryPort(Protocol):
    def get_customer_accounts(self) -> List[Dict]: ...

    def get_account_snapshot(self, account_type: str, account_id: int) -> Dict: ...

    def update_account_balance(
        self, account_type: str, account_id: int, delta: float
    ): ...

    def update_customer_credit_limit(self, customer_id: int, limit: float) -> None: ...

    def get_all_suppliers(self) -> List[Dict]: ...

    def get_account_history(self, account_type: str, account_id: int) -> List[Dict]: ...

    def get_financial_ledger(
        self, search: str = "", acc_type: str = ""
    ) -> List[Dict]: ...

    def get_debt_totals(self) -> Dict: ...

    def get_debt_aging_report(self) -> List[Dict]: ...

    def get_treasury_transactions(self) -> List[Dict]: ...

    def get_treasury_balance(self) -> float: ...

    def get_user_store_id(self, user_id: int) -> int: ...

    def get_expenses(self, store_id: int) -> List[Dict]: ...

    def insert_expense(
        self,
        store_id: int,
        user_id: int,
        expense_type: str,
        amount: float,
        description: str,
        is_personal: bool,
    ) -> int: ...

    def get_expense(self, expense_id: int) -> Dict: ...

    def mark_expense_voided(self, expense_id: int, user_id: int, reason: str): ...

    def insert_treasury_entry(
        self,
        store_id: int,
        transaction_type: str,
        amount: float,
        source_type: str,
        reference_id: int,
        description: str,
        user_id: int,
    ) -> int: ...

    def insert_ledger_entry(
        self,
        account_type: str,
        account_id: int,
        transaction_type: str,
        amount: float,
        reference_type: str,
        description: str,
        user_id: int,
        reference_id: int = None,
        attachment_path: str = "",
        is_settlement: bool = False,
    ) -> int: ...

    def commit(self): ...

    def rollback(self): ...

    def get_financial_report(
        self, store_id: int, start_date: str, end_date: str
    ) -> Dict: ...

    def get_promotion_categories(self) -> List[Dict]: ...

    def search_promotion_products(self, term: str = "") -> List[Dict]: ...

    def get_all_promotions(self) -> List[Dict]: ...

    def get_promotion_by_id(self, promo_id: int) -> Dict: ...

    def get_promotion_margin_products(
        self, apply_to: str, apply_to_id=None
    ) -> List[Dict]: ...

    def insert_promotion(
        self,
        name,
        promo_type,
        value,
        min_quantity,
        buy_quantity,
        apply_to,
        apply_to_id,
        start_date,
        end_date,
        funding_source="company",
        supplier_id=None,
    ) -> int: ...

    def update_promotion_record(self, promo_id: int, fields: Dict) -> None: ...

    def toggle_promotion_active(self, promo_id: int) -> None: ...

    def delete_promotion_record(self, promo_id: int) -> None: ...

    def allocate_supplier_payment(self, supplier_id: int, amount: float): ...

    def get_all_stores(self) -> List[Dict]: ...

    def get_discount_companies(self, active_only: bool = False) -> List[Dict]: ...

    def get_discount_company_products(self, company_id: int) -> List[int]: ...

    def insert_discount_company(
        self, name: str, discount_percent: float, product_ids=None
    ) -> int: ...

    def update_discount_company(
        self, company_id: int, fields: Dict, product_ids=None
    ) -> None: ...

    def delete_discount_company(self, company_id: int) -> None: ...

    def search_discount_eligible_products(
        self, term: str = "", min_margin_percent: float = 0.0
    ) -> List[Dict]: ...


class PromotionCatalogPort(Protocol):
    def create_pdf(self, download_missing_images=True, refresh_images=True): ...
