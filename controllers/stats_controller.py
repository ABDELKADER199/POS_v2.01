"""Stats Controller - thin adapter between PyQt UI and application services."""
from application.services.stats_service_facade import StatsServiceFacade


class StatsController:
    def __init__(self, service: StatsServiceFacade):
        self.service = service

    def get_dashboard_data(self, date_from: str, date_to: str, store_id: int | None = None, user_info: dict | None = None):
        return self.service.get_dashboard_data(date_from, date_to, store_id, user_info)

    def get_stores(self, user_info: dict | None):
        return self.service.get_stores(user_info)

    def get_profit_loss_data(self, date_from: str, date_to: str, store_id: int | None = None, user_info: dict | None = None):
        return self.service.get_profit_loss_data(date_from, date_to, store_id, user_info)

    def export_dashboard(self, date_from: str, date_to: str, store_id: int | None, user_info: dict | None, store_name: str, user_name: str):
        return self.service.export_dashboard(date_from, date_to, store_id, user_info, store_name, user_name)

    def export_profit_loss(self, date_from: str, date_to: str, store_id: int | None, user_info: dict | None, store_name: str, user_name: str):
        return self.service.export_profit_loss(date_from, date_to, store_id, user_info, store_name, user_name)


