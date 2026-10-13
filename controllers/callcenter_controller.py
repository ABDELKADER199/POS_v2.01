"""Call Center Controller - thin adapter between PyQt UI and application services."""
from application.services.callcenter_service_facade import CallCenterServiceFacade
from repositories.callcenter_repo import CallCenterRepository


class CallCenterController:
    def __init__(self):
        self.service = CallCenterServiceFacade(CallCenterRepository())

    def get_all_stores(self, *args, **kwargs): return self.service.get_all_stores(*args, **kwargs)
    def search_products(self, *args, **kwargs): return self.service.search_products(*args, **kwargs)
    def get_customer_by_phone(self, *args, **kwargs): return self.service.get_customer_by_phone(*args, **kwargs)
    def save_order(self, *args, **kwargs): return self.service.save_order(*args, **kwargs)
    def get_orders(self, *args, **kwargs): return self.service.get_orders(*args, **kwargs)
    def update_order_status(self, *args, **kwargs): return self.service.update_order_status(*args, **kwargs)
    def get_order_details(self, *args, **kwargs): return self.service.get_order_details(*args, **kwargs)
    def get_order_by_id(self, *args, **kwargs): return self.service.get_order_by_id(*args, **kwargs)
    def get_delivery_agents(self, *args, **kwargs): return self.service.get_delivery_agents(*args, **kwargs)
    def assign_delivery_agent(self, *args, **kwargs): return self.service.assign_delivery_agent(*args, **kwargs)
    def update_delivery_status(self, *args, **kwargs): return self.service.update_delivery_status(*args, **kwargs)
