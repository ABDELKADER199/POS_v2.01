import logging
from typing import Dict, List

from application.ports.open_order_port import (
    OpenOrderRepositoryPort,
    OrderCartPort,
    OrderInventoryPort,
)
from models.invoice import InvoiceItem

logger = logging.getLogger(__name__)


class ListOpenOrdersUseCase:
    def __init__(self, order_repo: OpenOrderRepositoryPort):
        self.order_repo = order_repo

    def execute(self, store_id: int, search_term: str = None) -> List[Dict]:
        return self.order_repo.get_open_orders(store_id, search_term)


class LoadOrderItemsUseCase:
    def __init__(
        self,
        order_repo: OpenOrderRepositoryPort,
        inventory_repo: OrderInventoryPort,
        cart: OrderCartPort,
    ):
        self.order_repo = order_repo
        self.inventory_repo = inventory_repo
        self.cart = cart

    def execute(self, order_id: int) -> bool:
        rows = self.order_repo.get_order_items(order_id)
        if not rows:
            return False

        for row in rows:
            product_id = row["product_id"]
            quantity = round(float(row.get("quantity") or 1), 3)
            available = self.inventory_repo.get_stock(
                product_id, self.cart.active_store_id
            )
            if available < quantity:
                raise ValueError(
                    f"المخزون غير كافٍ. المتاح: {available}، المطلوب: {quantity}"
                )

        self.cart.clear()
        for row in rows:
            self.cart.items.append(
                InvoiceItem(
                    product_id=row["product_id"],
                    product_code=row.get("product_code", ""),
                    product_name=row.get("product_name", ""),
                    quantity=round(float(row.get("quantity") or 1), 3),
                    unit_price=float(
                        row.get("unit_price") or row.get("sell_price") or 0
                    ),
                    tax_percent=float(row.get("tax_percent") or 0),
                )
            )
        return True


class MarkOrderDeliveredUseCase:
    def __init__(self, order_repo: OpenOrderRepositoryPort):
        self.order_repo = order_repo

    def execute(self, order_id: int) -> bool:
        if not order_id:
            return False
        try:
            self.order_repo.update_order_status_record(order_id, "Delivered")
            self.order_repo.commit()
            return True
        except Exception as exc:
            self.order_repo.rollback()
            logger.error(
                "Error marking order delivered %s: %s", order_id, exc, exc_info=True
            )
            return False
