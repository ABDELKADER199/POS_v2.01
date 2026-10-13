import pytest

from application.use_cases.invoice_history import InvoiceHistoryUseCase
from application.use_cases.open_orders import (
    ListOpenOrdersUseCase,
    LoadOrderItemsUseCase,
    MarkOrderDeliveredUseCase,
)


class FakeInvoiceHistoryRepository:
    def __init__(self):
        self.calls = []
        self.recent = [{"id": 1, "invoice_number": "INV-1"}]
        self.completed = [{"id": 2, "invoice_number": "INV-2"}]
        self.invoice = {"id": 3, "invoice_number": "INV-3"}
        self.items_by_id = [{"product_name": "منتج", "quantity": 2}]
        self.items_by_number = [{"product_name": "منتج آخر", "quantity": 1}]

    def get_recent(self, store_id=None, limit=50):
        self.calls.append(("get_recent", store_id, limit))
        return self.recent

    def get_completed_invoices(self, store_id, search_term=None, start_date=None, end_date=None):
        self.calls.append(("get_completed_invoices", store_id, search_term, start_date, end_date))
        return self.completed

    def get_invoice_by_id(self, invoice_id):
        self.calls.append(("get_invoice_by_id", invoice_id))
        return self.invoice if invoice_id == 3 else None

    def get_invoice_items_by_id(self, invoice_id):
        self.calls.append(("get_invoice_items_by_id", invoice_id))
        return self.items_by_id

    def get_items(self, invoice_number):
        self.calls.append(("get_items", invoice_number))
        return self.items_by_number


class FakeOpenOrderRepository:
    def __init__(self):
        self.calls = []
        self.open_orders = [{"id": 1, "customer_name": "عميل"}]
        self.order_items = [
            {
                "product_id": 10,
                "product_code": "P10",
                "product_name": "منتج 10",
                "quantity": 2,
                "unit_price": 15,
                "tax_percent": 14,
            },
            {
                "product_id": 20,
                "product_code": "P20",
                "product_name": "منتج 20",
                "quantity": None,
                "sell_price": 8,
            },
        ]
        self.committed = False
        self.rolled_back = False
        self.raise_on_update = False

    def get_open_orders(self, store_id, search_term=None):
        self.calls.append(("get_open_orders", store_id, search_term))
        return self.open_orders

    def get_order_items(self, order_id):
        self.calls.append(("get_order_items", order_id))
        return self.order_items if order_id == 1 else []

    def update_order_status_record(self, order_id, status):
        self.calls.append(("update_order_status_record", order_id, status))
        if self.raise_on_update:
            raise RuntimeError("database error")

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeInventoryRepository:
    def __init__(self, stock_by_product=None):
        self.stock_by_product = stock_by_product or {10: 5, 20: 1}
        self.calls = []

    def get_stock(self, product_id, store_id):
        self.calls.append(("get_stock", product_id, store_id))
        return self.stock_by_product.get(product_id, 0)


class FakeCart:
    def __init__(self):
        self.active_store_id = 7
        self.items = ["old item"]
        self.cleared = False

    def clear(self):
        self.cleared = True
        self.items.clear()


def test_invoice_history_use_case_delegates_queries():
    repo = FakeInvoiceHistoryRepository()
    use_case = InvoiceHistoryUseCase(repo)

    assert use_case.get_recent_invoices(store_id=2, limit=10) == repo.recent
    assert use_case.get_completed_invoices(2, "INV", "2026-05-01", "2026-05-31") == repo.completed
    assert use_case.get_invoice_by_id(3) == repo.invoice
    assert use_case.get_invoice_by_id(99) is None
    assert use_case.get_invoice_items_by_id(3) == repo.items_by_id
    assert use_case.get_invoice_items("INV-3") == repo.items_by_number
    assert repo.calls == [
        ("get_recent", 2, 10),
        ("get_completed_invoices", 2, "INV", "2026-05-01", "2026-05-31"),
        ("get_invoice_by_id", 3),
        ("get_invoice_by_id", 99),
        ("get_invoice_items_by_id", 3),
        ("get_items", "INV-3"),
    ]


def test_list_open_orders_delegates_store_and_search():
    repo = FakeOpenOrderRepository()

    result = ListOpenOrdersUseCase(repo).execute(3, "010")

    assert result == [{"id": 1, "customer_name": "عميل"}]
    assert repo.calls == [("get_open_orders", 3, "010")]


def test_load_order_items_clears_cart_and_loads_invoice_items():
    order_repo = FakeOpenOrderRepository()
    inventory_repo = FakeInventoryRepository()
    cart = FakeCart()

    result = LoadOrderItemsUseCase(order_repo, inventory_repo, cart).execute(1)

    assert result is True
    assert cart.cleared is True
    assert len(cart.items) == 2
    assert cart.items[0].product_id == 10
    assert cart.items[0].product_code == "P10"
    assert cart.items[0].product_name == "منتج 10"
    assert cart.items[0].quantity == 2
    assert cart.items[0].unit_price == 15
    assert cart.items[0].tax_percent == 14
    assert cart.items[1].product_id == 20
    assert cart.items[1].quantity == 1
    assert cart.items[1].unit_price == 8
    assert inventory_repo.calls == [
        ("get_stock", 10, 7),
        ("get_stock", 20, 7),
    ]


def test_load_order_items_returns_false_when_order_has_no_items():
    order_repo = FakeOpenOrderRepository()
    inventory_repo = FakeInventoryRepository()
    cart = FakeCart()

    result = LoadOrderItemsUseCase(order_repo, inventory_repo, cart).execute(999)

    assert result is False
    assert cart.cleared is False
    assert cart.items == ["old item"]


def test_load_order_items_rejects_when_stock_is_not_enough():
    order_repo = FakeOpenOrderRepository()
    inventory_repo = FakeInventoryRepository(stock_by_product={10: 1, 20: 1})
    cart = FakeCart()

    with pytest.raises(ValueError):
        LoadOrderItemsUseCase(order_repo, inventory_repo, cart).execute(1)

    assert cart.cleared is False
    assert cart.items == ["old item"]


def test_mark_order_delivered_updates_status_and_commits():
    repo = FakeOpenOrderRepository()

    result = MarkOrderDeliveredUseCase(repo).execute(5)

    assert result is True
    assert ("update_order_status_record", 5, "Delivered") in repo.calls
    assert repo.committed is True
    assert repo.rolled_back is False


def test_mark_order_delivered_rejects_empty_order_id():
    repo = FakeOpenOrderRepository()

    result = MarkOrderDeliveredUseCase(repo).execute(0)

    assert result is False
    assert repo.calls == []
    assert repo.committed is False


def test_mark_order_delivered_rolls_back_on_repository_error():
    repo = FakeOpenOrderRepository()
    repo.raise_on_update = True

    result = MarkOrderDeliveredUseCase(repo).execute(5)

    assert result is False
    assert repo.committed is False
    assert repo.rolled_back is True
