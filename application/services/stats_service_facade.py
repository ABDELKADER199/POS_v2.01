from application.ports.stats_port import StatsRepositoryPort
from application.use_cases.stats import DashboardStatsUseCase, ProfitLossUseCase, StatsStoresUseCase


class StatsServiceFacade:
    def __init__(self, repo: StatsRepositoryPort):
        self.repo = repo
        self.dashboard_use_case = DashboardStatsUseCase(repo)
        self.stores_use_case = StatsStoresUseCase(repo)
        self.profit_loss_use_case = ProfitLossUseCase(repo)

    def get_dashboard_data(self, date_from, date_to, store_id=None, user_info=None):
        return self.dashboard_use_case.execute(date_from, date_to, store_id, user_info)

    def get_stores(self, user_info):
        return self.stores_use_case.execute(user_info)

    def get_profit_loss_data(self, date_from, date_to, store_id=None, user_info=None):
        return self.profit_loss_use_case.execute(date_from, date_to, store_id, user_info)

