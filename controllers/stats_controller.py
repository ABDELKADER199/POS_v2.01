"""Stats Controller - thin adapter between PyQt UI and application services."""
from application.services.stats_service_facade import StatsServiceFacade


class StatsController:
    def __init__(self, service: StatsServiceFacade):
        self.service = service

    def get_dashboard_data(self, *args, **kwargs):
        return self.service.get_dashboard_data(*args, **kwargs)

    def get_stores(self, *args, **kwargs):
        return self.service.get_stores(*args, **kwargs)

    def get_profit_loss_data(self, *args, **kwargs):
        return self.service.get_profit_loss_data(*args, **kwargs)


