from typing import Dict, List, Optional, Protocol


class StatsRepositoryPort(Protocol):
    def get_sales_summary(self, date_from: str, date_to: str, store_id: Optional[int] = None) -> Dict:
        ...

    def get_returns_summary(self, date_from: str, date_to: str, store_id: Optional[int] = None) -> Dict:
        ...

    def get_inventory_valuation(self, store_id: Optional[int] = None) -> float:
        ...

    def get_customer_retention_stats(
        self,
        date_from: str,
        date_to: str,
        store_id: Optional[int] = None,
    ) -> Dict:
        ...

    def get_treasury_period_totals(
        self,
        date_from: str,
        date_to: str,
        store_id: Optional[int] = None,
    ) -> Dict:
        ...

    def get_total_treasury_balance(self, store_id: Optional[int] = None) -> float:
        ...

    def get_total_paid_to_suppliers(self, store_id: Optional[int] = None) -> float:
        ...

    def get_total_supplier_debt(self, store_id: Optional[int] = None) -> float:
        ...

    def get_daily_sales_trend(
        self,
        date_from: str,
        date_to: str,
        store_id: Optional[int] = None,
    ) -> List[Dict]:
        ...

    def get_hourly_sales(self, date_from: str, date_to: str, store_id: Optional[int] = None) -> List[Dict]:
        ...

    def get_payment_method_distribution(
        self,
        date_from: str,
        date_to: str,
        store_id: Optional[int] = None,
    ) -> List[Dict]:
        ...

    def get_sales_by_store(self, date_from: str, date_to: str) -> List[Dict]:
        ...

    def get_top_selling_products(
        self,
        limit: int,
        date_from: str,
        date_to: str,
        store_id: Optional[int] = None,
    ) -> List[Dict]:
        ...

    def get_top_customers(
        self,
        limit: int,
        date_from: str,
        date_to: str,
        store_id: Optional[int] = None,
    ) -> List[Dict]:
        ...

    def get_most_returned_products(
        self,
        limit: int,
        date_from: str,
        date_to: str,
        store_id: Optional[int] = None,
    ) -> List[Dict]:
        ...

    def get_return_reasons(self, date_from: str, date_to: str, store_id: Optional[int] = None) -> List[Dict]:
        ...

    def get_supplier_stats(self, date_from: str, date_to: str) -> List[Dict]:
        ...

    def get_product_sales_report(
        self,
        date_from: str,
        date_to: str,
        store_id: Optional[int] = None,
    ) -> List[Dict]:
        ...

    def get_all_stores(self) -> List[Dict]:
        ...

    def get_discounts_summary(self, date_from: str, date_to: str, store_id: Optional[int] = None) -> Dict:
        ...

    def get_discount_breakdown_details(self, date_from: str, date_to: str, store_id: Optional[int] = None) -> List[Dict]:
        ...

