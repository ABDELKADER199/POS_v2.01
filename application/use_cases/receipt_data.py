from typing import Callable, Dict, List, Optional

from models.invoice import InvoiceItem, TaxInvoiceDetails


class ReceiptDataUseCase:
    def __init__(
        self,
        current_items_provider: Callable[[], List[InvoiceItem]],
        totals_provider: Callable[[], Dict],
        applied_promos_provider: Callable[[], List[Dict]],
        tax_invoice_provider: Callable[[], Optional[TaxInvoiceDetails]],
    ):
        self.current_items_provider = current_items_provider
        self.totals_provider = totals_provider
        self.applied_promos_provider = applied_promos_provider
        self.tax_invoice_provider = tax_invoice_provider

    def execute(
        self,
        invoice_number: str,
        drawer_id: int,
        payment_method: str,
        cash_amount: float,
        card_amount: float,
        paid_amount: float,
        customer_name: str = "",
        customer_phone: str = "",
        customer_address: str = "",
    ) -> tuple[Dict, List[Dict]]:
        totals = self.totals_provider()
        total = totals["total"]
        tax_invoice_data = self.tax_invoice_provider()

        data = {
            "invoice_number": invoice_number,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_address": customer_address,
            "drawer_id": drawer_id,
            "payment_method": payment_method,
            "cash_amount": cash_amount,
            "card_amount": card_amount,
            "gross_total": totals.get("gross_total", total),
            "total_amount": total,
            "subtotal": totals["subtotal"],
            "tax_amount": totals["tax_total"],
            "discount": totals["manual_discount"],
            "company_discount": totals.get("company_discount", 0),
            "discount_company": totals.get("discount_company"),
            "promo_discount": totals["promo_discount"],
            "total_discount": round(
                float(totals.get("manual_discount") or 0)
                + float(totals.get("promo_discount") or 0)
                + float(totals.get("company_discount") or 0),
                2,
            ),
            "applied_promos": self.applied_promos_provider(),
            "tendered": paid_amount,
            "change": max(0, paid_amount - total) if paid_amount > 0 else 0,
            "tax_invoice_data": tax_invoice_data.__dict__ if tax_invoice_data else None,
        }

        promos_by_product = {
            int(promo.get("product_id") or 0): float(promo.get("discount_amount") or 0)
            for promo in self.applied_promos_provider()
        }
        allocations = totals.get("line_allocations") or []
        items = []
        for idx, item in enumerate(self.current_items_provider()):
            payload = item.to_dict()
            alloc = allocations[idx] if idx < len(allocations) else {}
            promo_discount = alloc.get(
                "promo_discount",
                promos_by_product.get(int(item.product_id or 0), 0.0),
            )
            line_discount = alloc.get(
                "total_discount",
                float(item.discount or 0) + promo_discount,
            )
            payload["gross_total"] = item.gross_total
            payload["promo_discount"] = promo_discount
            company_discount = alloc.get("company_discount", 0.0)
            if company_discount:
                payload["company_discount"] = company_discount
            payload["line_discount"] = round(line_discount, 2)
            payload["total"] = round(item.gross_total - line_discount, 2)
            items.append(payload)
        return data, items
