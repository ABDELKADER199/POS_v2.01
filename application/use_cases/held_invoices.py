import logging
from datetime import datetime
from typing import Dict, List

from application.ports.held_invoice_port import (
    HeldInvoiceCartPort,
    HeldInvoiceRepositoryPort,
)
from models.invoice import InvoiceItem

logger = logging.getLogger(__name__)


class SaveHeldInvoiceUseCase:
    def __init__(
        self, invoice_repo: HeldInvoiceRepositoryPort, cart: HeldInvoiceCartPort
    ):
        self.invoice_repo = invoice_repo
        self.cart = cart

    def execute(
        self,
        store_id: int,
        cashier_id: int,
        customer_name: str = "",
        customer_phone: str = "",
        customer_address: str = "",
    ) -> bool:
        items = [item.to_dict() for item in self.cart.items]
        for source, payload in zip(self.cart.items, items):
            payload["unit_price"] = source.unit_price
            payload["discount"] = source.discount
        if not items:
            return False
        try:
            temp_code = f"HOLD-{datetime.now():%Y%m%d%H%M%S}"
            if hasattr(self.cart, "calculate_totals"):
                total = float(self.cart.calculate_totals().get("total") or 0)
            else:
                total = sum(
                    float(item.get("unit_price") or item.get("price") or 0)
                    * float(item.get("quantity") or 0)
                    for item in items
                )
            temp_id = self.invoice_repo.insert_held_invoice_header(
                temp_code,
                store_id,
                cashier_id,
                customer_name,
                customer_phone,
                customer_address,
                total,
            )
            for item in items:
                quantity = round(float(item.get("quantity") or 0), 3)
                unit_price = float(item.get("unit_price") or item.get("price") or 0)
                discount = float(item.get("discount") or 0)
                self.invoice_repo.insert_held_invoice_item(
                    temp_id,
                    item["product_id"],
                    quantity,
                    unit_price,
                    discount,
                    (quantity * unit_price) - discount,
                )
            self.invoice_repo.commit()
            return True
        except Exception as exc:
            self.invoice_repo.rollback()
            logger.error("Error saving held invoice: %s", exc, exc_info=True)
            return False


class ListHeldInvoicesUseCase:
    def __init__(self, invoice_repo: HeldInvoiceRepositoryPort):
        self.invoice_repo = invoice_repo

    def execute(self, store_id: int, search_term: str = None) -> List[Dict]:
        return self.invoice_repo.get_held_invoices(store_id, search_term)


class DeleteHeldInvoiceUseCase:
    def __init__(self, invoice_repo: HeldInvoiceRepositoryPort):
        self.invoice_repo = invoice_repo

    def execute(self, temp_invoice_id: int) -> bool:
        try:
            self.invoice_repo.delete_held_invoice_record(temp_invoice_id)
            self.invoice_repo.commit()
            return True
        except Exception as exc:
            self.invoice_repo.rollback()
            logger.error(
                "Error deleting held invoice %s: %s",
                temp_invoice_id,
                exc,
                exc_info=True,
            )
            return False


class ResumeHeldInvoiceUseCase:
    def __init__(
        self, invoice_repo: HeldInvoiceRepositoryPort, cart: HeldInvoiceCartPort
    ):
        self.invoice_repo = invoice_repo
        self.cart = cart

    def execute(self, temp_invoice_id: int) -> bool:
        rows = self.invoice_repo.get_held_invoice_items(temp_invoice_id)
        if not rows:
            return False

        self.cart.clear()
        for row in rows:
            self.cart.items.append(
                InvoiceItem(
                    product_id=row["product_id"],
                    product_code=row.get("product_code", ""),
                    product_name=row.get("product_name", ""),
                    quantity=float(row.get("quantity") or 1),
                    unit_price=float(
                        row.get("unit_price") or row.get("sell_price") or 0
                    ),
                    discount=float(row.get("discount") or 0),
                    tax_percent=float(row.get("tax_percent") or 0),
                )
            )
        return True
