"""Inventory count controller."""

from application.services.inventory_count_service_facade import InventoryCountServiceFacade
from repositories.inventory_count_repo import InventoryCountRepository


class InventoryCountController:
    def __init__(self):
        self.service = InventoryCountServiceFacade(InventoryCountRepository())

    def get_stores(self, user_info):
        return self.service.get_stores(user_info)

    def get_sessions(self, user_info, store_id=None, status=None):
        return self.service.get_sessions(user_info, store_id, status)

    def start_session(self, user_info, store_id, count_type, notes=""):
        return self.service.start_session(user_info, store_id, count_type, notes)

    def get_items(self, session_id, search="", limit=300):
        return self.service.get_items(session_id, search, limit)

    def search_products(self, term, store_id):
        return self.service.search_products(term, store_id)

    def add_item(self, user_info, session_id, product_id):
        return self.service.add_item(user_info, session_id, product_id)

    def update_item(self, user_info, session_id, product_id, actual_quantity, notes=""):
        return self.service.update_item(user_info, session_id, product_id, actual_quantity, notes)

    def approve_session(self, user_info, session_id):
        return self.service.approve_session(user_info, session_id)

    def cancel_session(self, user_info, session_id):
        return self.service.cancel_session(user_info, session_id)
