import pytest
from application.services.stats_service_facade import StatsServiceFacade
from application.use_cases.stats import DashboardStatsUseCase, ProfitLossUseCase, StatsStoresUseCase, StatsReportError
from controllers.stats_controller import StatsController
from utils.permissions import PermissionDenied



class FakeStatsRepository:
    def __init__(self):
        self.calls = []
        self.fail_on_sales = False

    def get_sales_summary(self, date_from, date_to, store_id=None):
        self.calls.append(("get_sales_summary", date_from, date_to, store_id))
        if self.fail_on_sales:
            raise RuntimeError("database unavailable")
        return {"total_sales": 1000, "invoice_count": 5}

    def get_returns_summary(self, date_from, date_to, store_id=None):
        self.calls.append(("get_returns_summary", date_from, date_to, store_id))
        return {"total_returns": 100}

    def get_inventory_valuation(self, store_id=None):
        self.calls.append(("get_inventory_valuation", store_id))
        return {"total_value": 2500, "details": [{"product_name": "منتج"}]}

    def get_customer_retention_stats(self, date_from, date_to, store_id=None):
        self.calls.append(("get_customer_retention_stats", date_from, date_to, store_id))
        return {"retention_rate": 40, "repeat_customers": 3, "new_customers": 7}

    def get_treasury_period_totals(self, date_from, date_to, store_id=None):
        self.calls.append(("get_treasury_period_totals", date_from, date_to, store_id))
        return {"total_in": 700, "total_out": 200, "net": 500}

    def get_total_treasury_balance(self, store_id=None):
        self.calls.append(("get_total_treasury_balance", store_id))
        return 1500

    def get_total_paid_to_suppliers(self, store_id=None):
        self.calls.append(("get_total_paid_to_suppliers", store_id))
        return 300

    def get_total_supplier_debt(self, store_id=None):
        self.calls.append(("get_total_supplier_debt", store_id))
        return 900

    def get_daily_sales_trend(self, date_from, date_to, store_id=None):
        self.calls.append(("get_daily_sales_trend", date_from, date_to, store_id))
        return [{"date": "2026-05-01", "total_sales": "120.50"}]

    def get_hourly_sales(self, date_from, date_to, store_id=None):
        self.calls.append(("get_hourly_sales", date_from, date_to, store_id))
        return [{"hour": 9, "total_sales": "80"}, {"total_sales": 10}]

    def get_payment_method_distribution(self, date_from, date_to, store_id=None):
        self.calls.append(("get_payment_method_distribution", date_from, date_to, store_id))
        return [{"payment_method": "Cash", "total": "700"}]

    def get_sales_by_store(self, date_from, date_to, store_id=None):
        self.calls.append(("get_sales_by_store", date_from, date_to, store_id))
        rows = [
            {"store_name": "الفرع الرئيسي", "total_sales": 600},
            {"store_name": "فرع ثان", "total_sales": 400},
        ]
        return rows if store_id is None else [rows[store_id - 1]]

    def get_top_selling_products(self, limit, date_from, date_to, store_id=None):
        self.calls.append(("get_top_selling_products", limit, date_from, date_to, store_id))
        return [{"product_name": "منتج", "quantity": 2}]

    def get_top_customers(self, limit, date_from, date_to, store_id=None):
        self.calls.append(("get_top_customers", limit, date_from, date_to, store_id))
        return [{"customer_name": "عميل", "total": 100}]

    def get_most_returned_products(self, limit, date_from, date_to, store_id=None):
        self.calls.append(("get_most_returned_products", limit, date_from, date_to, store_id))
        return [{"product_name": "مرتجع", "quantity": 1}]

    def get_return_reasons(self, date_from, date_to, store_id=None):
        self.calls.append(("get_return_reasons", date_from, date_to, store_id))
        return [{"reason": "تالف", "count": 1}]

    def get_supplier_stats(self, date_from, date_to):
        self.calls.append(("get_supplier_stats", date_from, date_to))
        return [{"supplier_name": "مورد", "total_purchases": 300}]

    def get_product_sales_report(self, date_from, date_to, store_id=None):
        self.calls.append(("get_product_sales_report", date_from, date_to, store_id))
        return [{"product_name": "منتج", "total_sales": 120}]

    def get_all_stores(self):
        self.calls.append(("get_all_stores",))
        return [
            {"id": 1, "store_name": "الفرع الرئيسي"},
            {"id": 2, "store_name": "فرع ثان"},
        ]

    def get_discounts_summary(self, date_from, date_to, store_id=None):
        self.calls.append(("get_discounts_summary", date_from, date_to, store_id))
        return {"total_discounts": 50, "manual_discount": 20, "promo_discount": 20, "company_discount": 10}

    def get_discount_breakdown_details(self, date_from, date_to, store_id=None):
        self.calls.append(("get_discount_breakdown_details", date_from, date_to, store_id))
        return [{"discount_type": "خصم", "amount": 50, "description": "desc"}]

    def get_net_profit_stats(self, date_from, date_to, store_id=None):
        self.calls.append(("get_net_profit_stats", date_from, date_to, store_id))
        return {"net_profit": 500, "profit_margin": 50}

    def get_expenses_breakdown(self, date_from, date_to, store_id=None):
        self.calls.append(("get_expenses_breakdown", date_from, date_to, store_id))
        return [{"expense_type": "إيجار", "total": 200}]


ADMIN = {"id": 1, "role_id": 1, "store_id": 1}
MANAGER = {"id": 2, "role_id": 2, "store_id": 1}


def test_dashboard_stats_builds_metrics_and_charts():
    repo = FakeStatsRepository()
    data = DashboardStatsUseCase(repo).execute("2026-05-01", "2026-05-31", user_info=ADMIN)

    assert data["metrics"]["total_sales"] == 1000
    assert data["metrics"]["total_returns"] == 100
    assert data["metrics"]["return_rate"] == 10
    assert data["metrics"]["inventory_value"] == 2500
    assert data["metrics"]["cash_in"] == 700
    assert data["metrics"]["cash_out"] == 200
    assert data["metrics"]["net_cash"] == 500
    assert data["metrics"]["vault_liquidity"] == 1500
    assert data["daily_chart"] == [{"date": "2026-05-01", "total_sales": 120.50}]
    assert data["hourly_chart"] == [{"date": "9:00", "total_sales": 80.0}]
    assert data["payment_chart"] == [{"payment_method": "Cash", "total": 700.0}]
    assert data["top_products"] == [{"product_name": "منتج", "quantity": 2}]
    assert data["supplier_stats"] == [{"supplier_name": "مورد", "total_purchases": 300}]


def test_stats_service_facade_exposes_repository_for_profit_loss_dialog():
    repo = FakeStatsRepository()
    service = StatsServiceFacade(repo)

    assert service.repo is repo


def test_dashboard_stats_passes_store_scope_to_scoped_queries():
    repo = FakeStatsRepository()
    DashboardStatsUseCase(repo).execute("2026-05-01", "2026-05-31", store_id=2, user_info=ADMIN)

    assert ("get_sales_summary", "2026-05-01", "2026-05-31", 2) in repo.calls
    assert ("get_returns_summary", "2026-05-01", "2026-05-31", 2) in repo.calls
    assert ("get_inventory_valuation", 2) in repo.calls
    assert ("get_total_treasury_balance", 2) in repo.calls
    assert ("get_top_selling_products", 10, "2026-05-01", "2026-05-31", 2) in repo.calls
    assert ("get_product_sales_report", "2026-05-01", "2026-05-31", 2) in repo.calls


def test_dashboard_stats_filters_store_sales_for_selected_store():
    repo = FakeStatsRepository()
    data = DashboardStatsUseCase(repo).execute("2026-05-01", "2026-05-31", store_id=2, user_info=ADMIN)

    assert data["store_sales"] == [{"store_name": "فرع ثان", "total_sales": 400}]


def test_dashboard_stats_handles_zero_sales_return_rate():
    repo = FakeStatsRepository()
    repo.get_sales_summary = lambda date_from, date_to, store_id=None: {"total_sales": 0}

    data = DashboardStatsUseCase(repo).execute("2026-05-01", "2026-05-31", user_info=ADMIN)

    assert data["metrics"]["return_rate"] == 0


def test_dashboard_stats_raises_error_on_repository_failure():
    repo = FakeStatsRepository()
    repo.fail_on_sales = True

    with pytest.raises(StatsReportError):
        DashboardStatsUseCase(repo).execute("2026-05-01", "2026-05-31", user_info=ADMIN)


def test_dashboard_stats_permission_scoping_hides_sensitive_data():
    repo = FakeStatsRepository()
    # Cashier user: role_id = 3, store_id = 1
    with pytest.raises(PermissionDenied):
        DashboardStatsUseCase(repo).execute("2026-05-01", "2026-05-31", user_info={"id": 3, "role_id": 3, "store_id": 1})


def test_stats_service_facade_get_profit_loss_data():
    repo = FakeStatsRepository()
    repo.get_net_profit_stats = lambda df, dt, sid: {"net_profit": 500}
    repo.get_expenses_breakdown = lambda df, dt, sid: [{"expense_type": "إيجار", "total": 200}]
    
    service = StatsServiceFacade(repo)
    pl = service.get_profit_loss_data("2026-05-01", "2026-05-31", store_id=1, user_info=ADMIN)

    assert pl["net_profit_stats"] == {"net_profit": 500}
    assert pl["expenses_breakdown"] == [{"expense_type": "إيجار", "total": 200}]


def test_stats_stores_returns_all_stores():
    repo = FakeStatsRepository()

    stores = StatsStoresUseCase(repo).execute(ADMIN)

    assert stores == [
        {"id": 1, "store_name": "الفرع الرئيسي"},
        {"id": 2, "store_name": "فرع ثان"},
    ]


@pytest.mark.parametrize("user_info", [None, {}, {"id": 1}])
def test_dashboard_rejects_missing_or_unverified_identity_before_repository_access(user_info):
    repo = FakeStatsRepository()
    with pytest.raises(PermissionDenied):
        DashboardStatsUseCase(repo).execute("2026-05-01", "2026-05-31", user_info=user_info)
    assert repo.calls == []


def test_branch_user_cannot_request_another_store_and_never_fetches_it():
    repo = FakeStatsRepository()
    with pytest.raises(PermissionDenied):
        DashboardStatsUseCase(repo).execute("2026-05-01", "2026-05-31", store_id=2, user_info=MANAGER)
    assert repo.calls == []


def test_branch_stats_are_scoped_and_do_not_fetch_cost_details():
    repo = FakeStatsRepository()
    data = DashboardStatsUseCase(repo).execute("2026-05-01", "2026-05-31", user_info=MANAGER)
    assert ("get_sales_summary", "2026-05-01", "2026-05-31", 1) in repo.calls
    assert not any(call[0] == "get_inventory_valuation" for call in repo.calls)
    assert "net_profit" not in data["metrics"]


def test_profit_loss_requires_cost_permission_and_enforces_store_scope():
    repo = FakeStatsRepository()
    use_case = ProfitLossUseCase(repo)
    with pytest.raises(PermissionDenied):
        use_case.execute("2026-05-01", "2026-05-31", 1, MANAGER)
    with pytest.raises(PermissionDenied):
        use_case.execute("2026-05-01", "2026-05-31", 2, {"id": 3, "role_id": 6, "store_id": 1})
    assert use_case.execute("2026-05-01", "2026-05-31", None, ADMIN)["net_profit_stats"]["net_profit"] == 500


def test_profit_loss_service_rejects_missing_user_before_fetching_data():
    repo = FakeStatsRepository()
    with pytest.raises(PermissionDenied):
        StatsServiceFacade(repo).get_profit_loss_data("2026-05-01", "2026-05-31", store_id=1)
    assert repo.calls == []


def test_stats_controller_accepts_a_fully_fake_service_without_a_repository():
    class FakeService:
        def get_stores(self, user_info):
            return []

    controller = StatsController(FakeService())
    assert controller.get_stores(ADMIN) == []
