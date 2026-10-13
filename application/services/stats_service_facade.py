from application.use_cases.stats import DashboardStatsUseCase, StatsStoresUseCase


class StatsServiceFacade:
    def __init__(self, repo):
        self.repo = repo
        self.dashboard_use_case = DashboardStatsUseCase(repo)
        self.stores_use_case = StatsStoresUseCase(repo)

    def get_dashboard_data(self, date_from, date_to, store_id=None):
        return self.dashboard_use_case.execute(date_from, date_to, store_id)

    def get_stores(self):
        return self.stores_use_case.execute()
