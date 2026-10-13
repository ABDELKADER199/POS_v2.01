from application.use_cases.inventory_count import (
    AddInventoryCountItemUseCase,
    ApproveInventoryCountUseCase,
    CancelInventoryCountUseCase,
    InventoryCountItemsUseCase,
    InventoryCountProductSearchUseCase,
    InventoryCountSessionsUseCase,
    InventoryCountStoresUseCase,
    StartInventoryCountUseCase,
    UpdateInventoryCountItemUseCase,
)


class InventoryCountServiceFacade:
    def __init__(self, repo):
        self.stores_use_case = InventoryCountStoresUseCase(repo)
        self.sessions_use_case = InventoryCountSessionsUseCase(repo)
        self.start_use_case = StartInventoryCountUseCase(repo)
        self.items_use_case = InventoryCountItemsUseCase(repo)
        self.search_products_use_case = InventoryCountProductSearchUseCase(repo)
        self.add_item_use_case = AddInventoryCountItemUseCase(repo)
        self.update_item_use_case = UpdateInventoryCountItemUseCase(repo)
        self.approve_use_case = ApproveInventoryCountUseCase(repo)
        self.cancel_use_case = CancelInventoryCountUseCase(repo)

    def get_stores(self, user_info):
        return self.stores_use_case.execute(user_info)

    def get_sessions(self, user_info, store_id=None, status=None):
        return self.sessions_use_case.execute(user_info, store_id, status)

    def start_session(self, user_info, store_id, count_type, notes=""):
        return self.start_use_case.execute(user_info, store_id, count_type, notes)

    def get_items(self, session_id, search="", limit=300):
        return self.items_use_case.execute(session_id, search, limit)

    def search_products(self, term, store_id):
        return self.search_products_use_case.execute(term, store_id)

    def add_item(self, user_info, session_id, product_id):
        return self.add_item_use_case.execute(user_info, session_id, product_id)

    def update_item(self, user_info, session_id, product_id, actual_quantity, notes=""):
        return self.update_item_use_case.execute(user_info, session_id, product_id, actual_quantity, notes)

    def approve_session(self, user_info, session_id):
        return self.approve_use_case.execute(user_info, session_id)

    def cancel_session(self, user_info, session_id):
        return self.cancel_use_case.execute(user_info, session_id)
