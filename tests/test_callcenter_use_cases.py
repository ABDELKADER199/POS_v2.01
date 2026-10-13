import application.use_cases.callcenter as callcenter_module
from application.services.callcenter_service_facade import CallCenterServiceFacade
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


class FixedDatetime:
    @classmethod
    def now(cls):
        from datetime import datetime

        return datetime(2026, 5, 28, 13, 45, 6)


class FakeCallCenterRepository:
    def __init__(self):
        self.calls = []
        self.stores = [{"id": 1, "store_name": "الرئيسي"}]
        self.products = [{"id": 10, "product_name": "منتج", "sell_price": 25}]
        self.customers_by_phone = {
            "01000000000": {
                "id": 7,
                "customer_name": "عميل قديم",
                "phone": "01000000000",
                "customer_address": "قديم",
            }
        }
        self.orders = [{"id": 1, "order_number": "CC-1"}]
        self.order_details = [{"product_id": 10, "quantity": 2}]
        self.order = {"id": 1, "order_number": "CC-1"}
        self.delivery_agents = []
        self.committed = False
        self.rolled_back = False
        self.raise_on_header = False
        self.raise_on_status = False
        self.next_customer_id = 20
        self.next_order_id = 30

    def get_all_stores(self):
        self.calls.append(("get_all_stores",))
        return self.stores

    def search_products(self, term):
        self.calls.append(("search_products", term))
        return self.products

    def get_customer_by_phone(self, phone):
        self.calls.append(("get_customer_by_phone", phone))
        return self.customers_by_phone.get(phone)

    def update_customer(self, customer_id, name="", address=""):
        self.calls.append(("update_customer", customer_id, name, address))

    def create_customer(self, name, phone="", address=""):
        self.calls.append(("create_customer", name, phone, address))
        return self.next_customer_id

    def create_order_header(
        self,
        order_number,
        customer_name,
        phone,
        address,
        customer_city,
        customer_id,
        source_store_id,
        destination_store_id,
        user_id,
        total,
    ):
        self.calls.append(
            (
                "create_order_header",
                order_number,
                customer_name,
                phone,
                address,
                customer_city,
                customer_id,
                source_store_id,
                destination_store_id,
                user_id,
                total,
            )
        )
        if self.raise_on_header:
            raise RuntimeError("database error")
        return self.next_order_id

    def insert_order_item(self, order_id, product_id, quantity, price):
        self.calls.append(("insert_order_item", order_id, product_id, quantity, price))

    def get_orders(self, statuses=None, store_id=None, search=None):
        self.calls.append(("get_orders", statuses, store_id, search))
        return self.orders

    def update_order_status(self, order_id, status):
        self.calls.append(("update_order_status", order_id, status))
        if self.raise_on_status:
            raise RuntimeError("database error")

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def get_order_details(self, order_id):
        self.calls.append(("get_order_details", order_id))
        return self.order_details

    def get_order_by_id(self, order_id):
        self.calls.append(("get_order_by_id", order_id))
        return self.order

    def get_delivery_agents(self, store_id):
        self.calls.append(("get_delivery_agents", store_id))
        return self.delivery_agents

    def assign_delivery_agent(self, order_id, agent_id):
        self.calls.append(("assign_delivery_agent", order_id, agent_id))

    def update_delivery_status(self, order_id, status, notes=None):
        self.calls.append(("update_delivery_status", order_id, status, notes))


def test_callcenter_stores_use_case_returns_all_stores():
    repo = FakeCallCenterRepository()

    assert CallCenterStoresUseCase(repo).execute() == [{"id": 1, "store_name": "الرئيسي"}]
    assert repo.calls == [("get_all_stores",)]


def test_callcenter_product_search_requires_two_characters_and_trims_term():
    repo = FakeCallCenterRepository()

    assert CallCenterProductSearchUseCase(repo).execute(" أ ") == []
    assert CallCenterProductSearchUseCase(repo).execute(" منتج ") == repo.products
    assert repo.calls == [("search_products", "منتج")]


def test_callcenter_customer_lookup_requires_valid_phone_and_trims_value():
    repo = FakeCallCenterRepository()

    assert CallCenterCustomerLookupUseCase(repo).execute("010") is None
    assert CallCenterCustomerLookupUseCase(repo).execute(" 01000000000 ") == repo.customers_by_phone["01000000000"]
    assert repo.calls == [("get_customer_by_phone", "01000000000")]


def test_save_callcenter_order_updates_existing_customer_and_commits(monkeypatch):
    monkeypatch.setattr(callcenter_module, "datetime", FixedDatetime)
    repo = FakeCallCenterRepository()

    order_number = SaveCallCenterOrderUseCase(repo).execute(
        customer_name=" عميل محدث ",
        phone=" 01000000000 ",
        address=" عنوان جديد ",
        store_id=2,
        source_store_id=1,
        items=[
            {"product_id": 10, "quantity": 2, "price": 15},
            {"product_id": 20, "quantity": 1, "price": 8},
        ],
        total=38,
        user_id=5,
    )

    assert order_number == "CC-20260528134506"
    assert ("get_customer_by_phone", "01000000000") in repo.calls
    assert ("update_customer", 7, "عميل محدث", "عنوان جديد") in repo.calls
    assert (
        "create_order_header",
        "CC-20260528134506",
        "عميل محدث",
        "01000000000",
        "عنوان جديد",
        None,
        7,
        1,
        2,
        5,
        38,
    ) in repo.calls
    assert ("insert_order_item", 30, 10, 2, 15) in repo.calls
    assert ("insert_order_item", 30, 20, 1, 8) in repo.calls
    assert repo.committed is True
    assert repo.rolled_back is False


def test_save_callcenter_order_creates_customer_when_phone_is_new(monkeypatch):
    monkeypatch.setattr(callcenter_module, "datetime", FixedDatetime)
    repo = FakeCallCenterRepository()

    order_number = SaveCallCenterOrderUseCase(repo).execute(
        customer_name="",
        phone="01111111111",
        address="عنوان",
        store_id=2,
        items=[{"product_id": 10, "quantity": 1, "price": 15}],
        total=15,
        user_id=5,
    )

    assert order_number == "CC-20260528134506"
    assert ("create_customer", "عميل كول سنتر", "01111111111", "عنوان") in repo.calls
    assert (
        "create_order_header",
        "CC-20260528134506",
        "",
        "01111111111",
        "عنوان",
        None,
        20,
        2,
        2,
        5,
        15,
    ) in repo.calls


def test_save_callcenter_order_rejects_missing_store_or_items():
    repo = FakeCallCenterRepository()
    use_case = SaveCallCenterOrderUseCase(repo)

    assert use_case.execute("عميل", "010", "عنوان", None, [{"product_id": 1}], 10, 1) is None
    assert use_case.execute("عميل", "010", "عنوان", 1, [], 10, 1) is None
    assert repo.calls == []
    assert repo.committed is False


def test_save_callcenter_order_rolls_back_on_repository_error(monkeypatch):
    monkeypatch.setattr(callcenter_module, "datetime", FixedDatetime)
    repo = FakeCallCenterRepository()
    repo.raise_on_header = True

    result = SaveCallCenterOrderUseCase(repo).execute(
        "عميل",
        "01000000000",
        "عنوان",
        2,
        [{"product_id": 10, "quantity": 1, "price": 15}],
        15,
        5,
    )

    assert result is None
    assert repo.committed is False
    assert repo.rolled_back is True


def test_list_callcenter_orders_maps_status_filters_and_trims_search():
    repo = FakeCallCenterRepository()

    assert ListCallCenterOrdersUseCase(repo).execute("Pending", 2, " 010 ") == repo.orders
    assert repo.calls == [("get_orders", ["Pending", "Confirmed", "Prepared"], 2, "010")]


def test_update_callcenter_order_status_maps_ui_status_and_commits():
    repo = FakeCallCenterRepository()

    assert UpdateCallCenterOrderStatusUseCase(repo).execute(1, "Accepted") is True

    assert repo.calls == [("update_order_status", 1, "Confirmed")]
    assert repo.committed is True
    assert repo.rolled_back is False


def test_update_callcenter_order_status_rejects_invalid_input():
    repo = FakeCallCenterRepository()
    use_case = UpdateCallCenterOrderStatusUseCase(repo)

    assert use_case.execute(None, "Accepted") is False
    assert use_case.execute(1, "") is False
    assert use_case.execute(1, "DeliveredX") is False
    assert repo.calls == []
    assert repo.committed is False


def test_update_callcenter_order_status_rolls_back_on_repository_error():
    repo = FakeCallCenterRepository()
    repo.raise_on_status = True

    assert UpdateCallCenterOrderStatusUseCase(repo).execute(1, "Prepared") is False

    assert repo.calls == [("update_order_status", 1, "Prepared")]
    assert repo.committed is False
    assert repo.rolled_back is True


def test_assign_delivery_agent_requires_active_agent_in_order_store():
    repo = FakeCallCenterRepository()
    repo.order.update({"destination_store_id": 2, "status": "Prepared"})
    repo.delivery_agents = [{"id": 44, "store_id": 2, "name": "مندوب"}]

    assert AssignDeliveryAgentUseCase(repo).execute(1, 44, 2) is True
    assert ("assign_delivery_agent", 1, 44) in repo.calls
    assert repo.committed is True


def test_assign_delivery_agent_rejects_agent_from_other_store():
    repo = FakeCallCenterRepository()
    repo.order.update({"destination_store_id": 2, "status": "Prepared"})
    repo.delivery_agents = [{"id": 44, "store_id": 3, "name": "مندوب"}]

    assert AssignDeliveryAgentUseCase(repo).execute(1, 44, 2) is False
    assert not any(call[0] == "assign_delivery_agent" for call in repo.calls)


def test_delivery_tracking_allows_only_valid_transition_after_assignment():
    repo = FakeCallCenterRepository()
    repo.order.update({"delivery_agent_id": 44, "delivery_status": "Assigned"})
    use_case = UpdateDeliveryTrackingUseCase(repo)

    assert use_case.execute(1, "OutForDelivery", "في الطريق") is True
    assert ("update_delivery_status", 1, "OutForDelivery", "في الطريق") in repo.calls

    repo.calls.clear()
    assert use_case.execute(1, "Delivered", None) is False
    assert repo.calls == [("get_order_by_id", 1)]


def test_delivery_agents_query_requires_store_id():
    repo = FakeCallCenterRepository()
    assert ListDeliveryAgentsUseCase(repo).execute(None) == []


def test_callcenter_order_details_guard_empty_ids_and_delegate():
    repo = FakeCallCenterRepository()
    use_case = CallCenterOrderDetailsUseCase(repo)

    assert use_case.get_details(None) == []
    assert use_case.get_by_id(None) is None
    assert use_case.get_details(1) == repo.order_details
    assert use_case.get_by_id(1) == repo.order
    assert repo.calls == [("get_order_details", 1), ("get_order_by_id", 1)]


def test_callcenter_service_facade_delegates_to_use_cases():
    repo = FakeCallCenterRepository()
    service = CallCenterServiceFacade(repo)

    assert service.get_all_stores() == repo.stores
    assert service.search_products("منتج") == repo.products
    assert service.get_customer_by_phone("01000000000") == repo.customers_by_phone["01000000000"]
    assert service.get_orders("Completed", store_id=1, search="CC") == repo.orders
    assert service.update_order_status(1, "Delivered") is True
    assert service.get_order_details(1) == repo.order_details
    assert service.get_order_by_id(1) == repo.order
