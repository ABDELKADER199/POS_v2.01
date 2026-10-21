from application.use_cases.stats import DashboardStatsUseCase, StatsStoresUseCase


class StatsServiceFacade:
    def __init__(self, repo):
        self.repo = repo
        self.dashboard_use_case = DashboardStatsUseCase(repo)
        self.stores_use_case = StatsStoresUseCase(repo)

    def get_dashboard_data(self, date_from, date_to, store_id=None, user_info=None):
        return self.dashboard_use_case.execute(date_from, date_to, store_id, user_info)

    def get_stores(self):
        return self.stores_use_case.execute()

    def get_profit_loss_data(self, date_from, date_to, store_id=None):
        return {
            "net_profit_stats": self.repo.get_net_profit_stats(date_from, date_to, store_id),
            "expenses_breakdown": self.repo.get_expenses_breakdown(date_from, date_to, store_id),
        }

