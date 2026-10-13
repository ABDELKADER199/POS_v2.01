"""Stats Controller - thin adapter between PyQt UI and application services."""
from application.services.stats_service_facade import StatsServiceFacade
from repositories.stats_repo import StatsRepository


class StatsController:
    def __init__(self):
        self.service = StatsServiceFacade(StatsRepository())

    def get_dashboard_data(self, *args, **kwargs):
        return self.service.get_dashboard_data(*args, **kwargs)

    def get_stores(self, *args, **kwargs):
        return self.service.get_stores(*args, **kwargs)
