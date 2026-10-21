"""Stats Controller - thin adapter between PyQt UI and application services."""
from typing import Optional
from application.services.stats_service_facade import StatsServiceFacade
from repositories.stats_repo import StatsRepository


class StatsController:
    def __init__(self, service: Optional[StatsServiceFacade] = None, repo=None):
        if service:
            self.service = service
        elif repo:
            self.service = StatsServiceFacade(repo)
        else:
            self.service = StatsServiceFacade(StatsRepository())

    def get_dashboard_data(self, *args, **kwargs):
        return self.service.get_dashboard_data(*args, **kwargs)

    def get_stores(self, *args, **kwargs):
        return self.service.get_stores(*args, **kwargs)

    def get_profit_loss_data(self, *args, **kwargs):
        return self.service.get_profit_loss_data(*args, **kwargs)


