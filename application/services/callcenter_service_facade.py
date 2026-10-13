from application.use_cases.callcenter import (
    CallCenterCustomerLookupUseCase,
    CallCenterOrderDetailsUseCase,
    CallCenterProductSearchUseCase,
    CallCenterStoresUseCase,
    ListCallCenterOrdersUseCase,
    SaveCallCenterOrderUseCase,
    AssignDeliveryAgentUseCase,
    ListDeliveryAgentsUseCase,
    UpdateDeliveryTrackingUseCase,
    UpdateCallCenterOrderStatusUseCase,
)


class CallCenterServiceFacade:
    def __init__(self, repo):
        self.stores_use_case = CallCenterStoresUseCase(repo)
        self.product_search_use_case = CallCenterProductSearchUseCase(repo)
        self.customer_lookup_use_case = CallCenterCustomerLookupUseCase(repo)
        self.save_order_use_case = SaveCallCenterOrderUseCase(repo)
        self.list_orders_use_case = ListCallCenterOrdersUseCase(repo)
        self.update_order_status_use_case = UpdateCallCenterOrderStatusUseCase(repo)
        self.order_details_use_case = CallCenterOrderDetailsUseCase(repo)
        self.delivery_agents_use_case = ListDeliveryAgentsUseCase(repo)
        self.assign_delivery_agent_use_case = AssignDeliveryAgentUseCase(repo)
        self.update_delivery_tracking_use_case = UpdateDeliveryTrackingUseCase(repo)

    def get_all_stores(self):
        return self.stores_use_case.execute()

    def search_products(self, term):
        return self.product_search_use_case.execute(term)

    def get_customer_by_phone(self, phone):
        return self.customer_lookup_use_case.execute(phone)

    def save_order(self, customer_name, phone, address, store_id, items, total, user_id, source_store_id=None):
        return self.save_order_use_case.execute(
            customer_name,
            phone,
            address,
            store_id,
            items,
            total,
            user_id,
            source_store_id,
        )

    def get_orders(self, status=None, store_id=None, search=None):
        return self.list_orders_use_case.execute(status, store_id, search)

    def update_order_status(self, order_id, status):
        return self.update_order_status_use_case.execute(order_id, status)

    def get_order_details(self, order_id):
        return self.order_details_use_case.get_details(order_id)

    def get_order_by_id(self, order_id):
        return self.order_details_use_case.get_by_id(order_id)

    def get_delivery_agents(self, store_id):
        return self.delivery_agents_use_case.execute(store_id)

    def assign_delivery_agent(self, order_id, agent_id, store_id):
        return self.assign_delivery_agent_use_case.execute(order_id, agent_id, store_id)

    def update_delivery_status(self, order_id, status, notes=None):
        return self.update_delivery_tracking_use_case.execute(order_id, status, notes)
