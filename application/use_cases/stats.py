import logging
from typing import Dict, List, Optional

from application.ports.stats_port import StatsRepositoryPort

logger = logging.getLogger(__name__)


class DashboardStatsUseCase:
    def __init__(self, repo: StatsRepositoryPort):
        self.repo = repo

    def execute(self, date_from: str, date_to: str, store_id: Optional[int] = None) -> Dict:
        try:
            sales = self.repo.get_sales_summary(date_from, date_to, store_id) or {}
            returns = self.repo.get_returns_summary(date_from, date_to, store_id) or {}
            retention = self.repo.get_customer_retention_stats(date_from, date_to, store_id) or {}
            treasury = self.repo.get_treasury_period_totals(date_from, date_to, store_id) or {}

            daily_trend = self.repo.get_daily_sales_trend(date_from, date_to, store_id)
            hourly = self.repo.get_hourly_sales(date_from, date_to, store_id)
            payment_dist = self.repo.get_payment_method_distribution(date_from, date_to, store_id)

            inventory_data = self.repo.get_inventory_valuation(store_id)
            inventory_val = inventory_data.get('total_value', 0) if isinstance(inventory_data, dict) else inventory_data
            inventory_details = inventory_data.get('details', []) if isinstance(inventory_data, dict) else []

            discounts_summary = self.repo.get_discounts_summary(date_from, date_to, store_id) or {}
            discount_breakdown = self.repo.get_discount_breakdown_details(date_from, date_to, store_id) or []

            from datetime import datetime, timedelta
            try:
                d1 = datetime.strptime(date_from, "%Y-%m-%d")
                d2 = datetime.strptime(date_to, "%Y-%m-%d")
                span = (d2 - d1).days + 1
                prev_d2 = d1 - timedelta(days=1)
                prev_d1 = prev_d2 - timedelta(days=span - 1)
                prev_from = prev_d1.strftime("%Y-%m-%d")
                prev_to = prev_d2.strftime("%Y-%m-%d")
                prev_sales = self.repo.get_sales_summary(prev_from, prev_to, store_id) or {}
                prev_profit = self.repo.get_net_profit_stats(prev_from, prev_to, store_id) or {}
                prev_discounts = self.repo.get_discounts_summary(prev_from, prev_to, store_id) or {}
            except Exception:
                prev_sales = {}
                prev_profit = {}
                prev_discounts = {}

            return {
                "metrics": self._build_metrics(
                    sales,
                    returns,
                    inventory_val,
                    retention,
                    treasury,
                    self.repo.get_total_treasury_balance(store_id),
                    self.repo.get_total_paid_to_suppliers(store_id),
                    self.repo.get_total_supplier_debt(store_id),
                    discounts_summary,
                    prev_sales,
                    prev_profit,
                    prev_discounts,
                ),
                "daily_chart": self._format_daily_chart(daily_trend),
                "hourly_chart": self._format_hourly_chart(hourly),
                "payment_chart": self._format_payment_chart(payment_dist),
                "store_sales": self._get_store_sales(date_from, date_to, store_id),
                "top_products": self.repo.get_top_selling_products(10, date_from, date_to, store_id),
                "top_customers": self.repo.get_top_customers(10, date_from, date_to, store_id),
                "most_returned": self.repo.get_most_returned_products(10, date_from, date_to, store_id),
                "return_reasons": self.repo.get_return_reasons(date_from, date_to, store_id),
                "supplier_stats": self.repo.get_supplier_stats(date_from, date_to),
                "product_sales_report": self.repo.get_product_sales_report(date_from, date_to, store_id),
                "inventory_details": inventory_details,
                "discount_breakdown": discount_breakdown,
            }
        except Exception as exc:
            logger.error("Error fetching dashboard data: %s", exc, exc_info=True)
            return self._empty_dashboard()

    def _build_metrics(
        self,
        sales: Dict,
        returns: Dict,
        inventory_value: float,
        retention: Dict,
        treasury: Dict,
        liquidity: float,
        total_paid: float,
        total_debt: float,
        discounts: Dict,
        prev_sales: Dict = None,
        prev_profit: Dict = None,
        prev_discounts: Dict = None,
    ) -> Dict:
        prev_sales = prev_sales or {}
        prev_profit = prev_profit or {}
        prev_discounts = prev_discounts or {}

        total_sales = float(sales.get("total_sales", 0) or 0)
        prev_sales_val = float(prev_sales.get("total_sales", 0) or 0)
        sales_growth = ((total_sales - prev_sales_val) / prev_sales_val * 100) if prev_sales_val > 0 else 0.0

        net_profit = float(sales.get("net_profit", 0) or 0)
        prev_profit_val = float(prev_profit.get("net_profit", 0) or 0)
        profit_growth = ((net_profit - prev_profit_val) / prev_profit_val * 100) if prev_profit_val > 0 else 0.0

        total_disc = float(discounts.get("total_discounts", 0) or 0)
        prev_disc_val = float(prev_discounts.get("total_discounts", 0) or 0)
        discounts_growth = ((total_disc - prev_disc_val) / prev_disc_val * 100) if prev_disc_val > 0 else 0.0

        total_returns = float(returns.get("total_returns", 0) or 0)
        return_rate = (total_returns / total_sales * 100) if total_sales > 0 else 0

        return {
            **sales,
            **returns,
            "return_rate": return_rate,
            "inventory_value": inventory_value,
            "retention_rate": retention.get("retention_rate", 0),
            "repeat_customers": retention.get("repeat_customers", 0),
            "new_customers": retention.get("new_customers", 0),
            "cash_in": treasury.get("total_in", 0),
            "cash_out": treasury.get("total_out", 0),
            "net_cash": treasury.get("net", 0),
            "vault_liquidity": liquidity,
            "total_paid": total_paid,
            "total_debt": total_debt,
            "total_discounts": total_disc,
            "manual_discount": discounts.get("manual_discount", 0),
            "promo_discount": discounts.get("promo_discount", 0),
            "company_discount": discounts.get("company_discount", 0),
            "sales_growth": sales_growth,
            "profit_growth": profit_growth,
            "discounts_growth": discounts_growth,
        }

    def _get_store_sales(self, date_from: str, date_to: str, store_id: Optional[int] = None) -> List[Dict]:
        store_sales = self.repo.get_sales_by_store(date_from, date_to)
        if not store_id:
            return store_sales

        stores = {store.get("id"): store.get("store_name") for store in self.repo.get_all_stores()}
        selected_store_name = stores.get(store_id)
        return [row for row in store_sales if row.get("store_name") == selected_store_name]

    def _format_daily_chart(self, rows: List[Dict]) -> List[Dict]:
        return [
            {"date": str(row.get("date", "")), "total_sales": float(row.get("total_sales", 0))}
            for row in rows
        ]

    def _format_hourly_chart(self, rows: List[Dict]) -> List[Dict]:
        return [
            {"date": f"{row['hour']}:00", "total_sales": float(row.get("total_sales", 0))}
            for row in rows
            if "hour" in row
        ]

    def _format_payment_chart(self, rows: List[Dict]) -> List[Dict]:
        return [
            {"payment_method": row.get("payment_method", ""), "total": float(row.get("total", 0))}
            for row in rows
        ]

    def _empty_dashboard(self) -> Dict:
        return {
            "metrics": {},
            "daily_chart": [],
            "hourly_chart": [],
            "payment_chart": [],
            "store_sales": [],
            "top_products": [],
            "top_customers": [],
            "most_returned": [],
            "return_reasons": [],
            "supplier_stats": [],
            "product_sales_report": [],
            "inventory_details": [],
        }


class StatsStoresUseCase:
    def __init__(self, repo: StatsRepositoryPort):
        self.repo = repo

    def execute(self) -> List[Dict]:
        return self.repo.get_all_stores()
