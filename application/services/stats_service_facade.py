from typing import Any, Mapping, Optional

from application.ports.report_export_port import ReportExportPort
from application.ports.stats_port import StatsRepositoryPort
from application.use_cases.stats import (
    DashboardExportUseCase,
    DashboardStatsUseCase,
    ProfitLossExportUseCase,
    ProfitLossUseCase,
    StatsReportError,
    StatsStoresUseCase,
)


class StatsServiceFacade:
    def __init__(self, repo: StatsRepositoryPort, exporter: Optional[ReportExportPort] = None):
        self.repo = repo
        self.dashboard_use_case = DashboardStatsUseCase(repo)
        self.stores_use_case = StatsStoresUseCase(repo)
        self.profit_loss_use_case = ProfitLossUseCase(repo)
        self.dashboard_export_use_case = DashboardExportUseCase(self.dashboard_use_case, exporter) if exporter else None
        self.profit_loss_export_use_case = ProfitLossExportUseCase(self.profit_loss_use_case, exporter) if exporter else None

    def get_dashboard_data(self, date_from: str, date_to: str, store_id: Optional[int] = None, user_info: Optional[dict] = None) -> dict:
        return self.dashboard_use_case.execute(date_from, date_to, store_id, user_info)

    def get_stores(self, user_info: Optional[dict]) -> list[dict]:
        return self.stores_use_case.execute(user_info)

    def get_profit_loss_data(self, date_from: str, date_to: str, store_id: Optional[int] = None, user_info: Optional[dict] = None):
        return self.profit_loss_use_case.execute(date_from, date_to, store_id, user_info)

    def export_dashboard(self, date_from: str, date_to: str, store_id: Optional[int], user_info: Optional[dict], store_name: str, user_name: str) -> Mapping[str, Any]:
        if not self.dashboard_export_use_case:
            raise StatsReportError("مسار التصدير غير مهيأ")
        return self.dashboard_export_use_case.execute(date_from, date_to, store_id, user_info, store_name, user_name)

    def export_profit_loss(self, date_from: str, date_to: str, store_id: Optional[int], user_info: Optional[dict], store_name: str, user_name: str) -> Mapping[str, Any]:
        if not self.profit_loss_export_use_case:
            raise StatsReportError("مسار التصدير غير مهيأ")
        return self.profit_loss_export_use_case.execute(date_from, date_to, store_id, user_info, store_name, user_name)

