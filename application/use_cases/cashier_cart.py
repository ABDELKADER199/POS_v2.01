from typing import Dict, List

from application.ports.cashier_cart_port import CashierCartRepositoryPort
from models.invoice import InvoiceItem
from models.product import Product


import math


def is_product_eligible_for_discount_company(
    company: dict, product_id: int
) -> bool:
    if not company:
        return False
    if company.get("is_active") is False or company.get("is_active") == 0:
        return False
    if product_id is None:
        return False

    target_ids = set()
    for value in (company.get("product_ids") or []):
        try:
            if value is not None and str(value).strip() != "":
                target_ids.add(int(value))
        except (ValueError, TypeError):
            continue

    mode = company.get("eligibility_mode")
    if mode == "include_only":
        return int(product_id) in target_ids
    if mode in ("exclude", "all_except"):
        return int(product_id) not in target_ids
    if mode == "all":
        return True
    # Legacy default: if target_ids is non-empty -> include_only, if empty -> all
    if target_ids:
        return int(product_id) in target_ids
    return True


def distribute_discount_to_lines(
    items: List[InvoiceItem],
    target_indices: List[int],
    total_discount: float,
    item_promo_discounts: List[float],
) -> List[float]:
    allocated = [0.0] * len(items)
    if not items or not target_indices:
        return allocated

    total_discount = max(0.0, round(float(total_discount or 0), 2))
    if total_discount <= 0:
        return allocated

    target_gross = sum(float(items[i].gross_total or 0) for i in target_indices)
    if target_gross <= 0:
        return allocated

    raw_shares = {}
    cents_allocated = {}
    max_capacities = {}

    for i in target_indices:
        gross = float(items[i].gross_total or 0)
        promo_disc = (
            item_promo_discounts[i] if i < len(item_promo_discounts) else 0.0
        )
        line_disc = float(items[i].discount or 0)
        max_allowed = max(0.0, round(gross - line_disc - promo_disc, 2))
        max_capacities[i] = int(round(max_allowed * 100))

        share = (gross / target_gross) * total_discount
        raw_shares[i] = share
        base_cents = int(math.floor(share * 100))
        cents_allocated[i] = min(base_cents, max_capacities[i])

    total_target_cents = int(round(total_discount * 100))
    current_sum_cents = sum(cents_allocated.values())
    remaining_cents = total_target_cents - current_sum_cents

    sorted_by_fraction = sorted(
        target_indices,
        key=lambda idx: (raw_shares[idx] * 100 - math.floor(raw_shares[idx] * 100)),
        reverse=True,
    )

    while remaining_cents > 0:
        distributed_any = False
        for i in sorted_by_fraction:
            if remaining_cents > 0 and cents_allocated[i] < max_capacities[i]:
                cents_allocated[i] += 1
                remaining_cents -= 1
                distributed_any = True
        if not distributed_any:
            break

    for i in target_indices:
        allocated[i] = round(cents_allocated[i] / 100.0, 2)

    return allocated


class CashierCartUseCase:
    def __init__(
        self,
        inventory_repo: CashierCartRepositoryPort,
        invoice_repo: CashierCartRepositoryPort,
    ):
        self.inventory_repo = inventory_repo
        self.invoice_repo = invoice_repo
        self.items: List[InvoiceItem] = []
        self.manual_discount: float = 0.0
        self.discount_company = None
        self.promo_discount: float = 0.0
        self.applied_promos: List[Dict] = []
        self.active_store_id: int = None

    def set_store(self, store_id: int):
        if not store_id:
            raise ValueError("لا يوجد فرع تشغيل محدد")
        self.active_store_id = int(store_id)

    def add_item(self, product: Product, quantity: float = 1.0) -> List[InvoiceItem]:
        quantity = round(float(quantity or 0), 3)
        if quantity < 0.001:
            raise ValueError("كمية الصنف يجب أن تكون 0.001 أو أكبر")
        if (
            float(product.sell_price or 0) <= 0
            or getattr(product, "import_status", "ready") == "needs_pricing"
        ):
            raise ValueError("لا يمكن بيع هذا المنتج قبل تحديد سعر البيع")
        self._ensure_stock_available(product.id, quantity)
        for item in self.items:
            if item.product_id == product.id:
                self._ensure_stock_available(product.id, item.quantity + quantity)
                item.quantity += quantity
                return self.items

        self.items.append(
            InvoiceItem(
                product_id=product.id,
                product_code=product.product_code,
                product_name=product.product_name,
                quantity=quantity,
                unit_price=product.sell_price,
                tax_percent=product.tax_percent,
            )
        )
        return self.items

    def update_item_quantity(self, index: int, quantity: float) -> List[InvoiceItem]:
        quantity = round(float(quantity or 0), 3)
        if 0 <= index < len(self.items):
            if quantity < 0.001:
                self.items.pop(index)
            else:
                self._ensure_stock_available(self.items[index].product_id, quantity)
                self.items[index].quantity = quantity
        return self.items

    def remove_item(self, index: int) -> List[InvoiceItem]:
        if 0 <= index < len(self.items):
            self.items.pop(index)
        return self.items

    def clear(self):
        self.items.clear()
        self.manual_discount = 0.0
        self.promo_discount = 0.0
        self.applied_promos = []
        self.discount_company = None

    def set_discount_company(self, company):
        self.discount_company = dict(company) if company else None

    def clear_discount_company(self):
        self.discount_company = None

    def calculate_totals(self) -> Dict:
        total_gross = sum(item.gross_total for item in self.items)
        promo_payload = [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.unit_price,
            }
            for item in self.items
        ]
        self.applied_promos, self.promo_discount = (
            self.invoice_repo.calculate_promotions(promo_payload)
        )
        item_promo_discounts = [
            self.promo_discount_for_product(item.product_id) for item in self.items
        ]

        company_discount = 0.0
        eligible_indices = []
        if self.discount_company:
            eligible_indices = [
                idx
                for idx, item in enumerate(self.items)
                if is_product_eligible_for_discount_company(
                    self.discount_company, item.product_id
                )
            ]
            eligible_gross = sum(
                self.items[idx].gross_total for idx in eligible_indices
            )
            discount_percent = float(
                self.discount_company.get("discount_percent") or 0
            )
            company_discount = round(eligible_gross * (discount_percent / 100.0), 2)

        if self.discount_company:
            allocated_company = distribute_discount_to_lines(
                self.items,
                eligible_indices,
                company_discount,
                item_promo_discounts,
            )
            effective_company_discount = round(sum(allocated_company), 2)
        else:
            allocated_company = [0.0] * len(self.items)
            effective_company_discount = 0.0

        if self.manual_discount > 0:
            manual_target_indices = [
                idx for idx, item in enumerate(self.items) if item.gross_total > 0
            ]
            prior_discounts = [
                round(item_promo_discounts[i] + allocated_company[i], 2)
                for i in range(len(self.items))
            ]
            allocated_manual = distribute_discount_to_lines(
                self.items,
                manual_target_indices,
                self.manual_discount,
                prior_discounts,
            )
            effective_manual_discount = round(sum(allocated_manual), 2)
        else:
            allocated_manual = [0.0] * len(self.items)
            effective_manual_discount = 0.0

        total_tax = 0.0
        line_allocations = []

        for idx, item in enumerate(self.items):
            item_promo = item_promo_discounts[idx]
            item_comp = allocated_company[idx]
            item_man = allocated_manual[idx]
            total_line_discount = round(
                float(item.discount or 0) + item_promo + item_comp + item_man, 2
            )
            item_net = max(0.0, round(item.gross_total - total_line_discount, 2))

            item_tax = 0.0
            if item.tax_percent > 0 and item_net > 0:
                item_tax = round(
                    item_net - (item_net / (1 + item.tax_percent / 100.0)), 2
                )
                total_tax += item_tax

            item_subtotal = round(item_net - item_tax, 2)

            line_allocations.append(
                {
                    "item_index": idx,
                    "product_id": item.product_id,
                    "gross_total": round(item.gross_total, 2),
                    "line_discount": round(float(item.discount or 0), 2),
                    "promo_discount": round(item_promo, 2),
                    "company_discount": round(item_comp, 2),
                    "manual_discount": round(item_man, 2),
                    "total_discount": total_line_discount,
                    "net_total": item_net,
                    "tax_amount": item_tax,
                    "subtotal": item_subtotal,
                }
            )

        total_after_discount = round(
            total_gross
            - effective_manual_discount
            - effective_company_discount
            - self.promo_discount,
            2,
        )
        total_after_discount = max(0.0, total_after_discount)
        total_tax = round(total_tax, 2)
        subtotal = round(total_after_discount - total_tax, 2)

        return {
            "gross_total": round(total_gross, 2),
            "manual_discount": round(effective_manual_discount, 2),
            "company_discount": round(effective_company_discount, 2),
            "discount_company": self.discount_company,
            "promo_discount": round(self.promo_discount, 2),
            "tax_total": total_tax,
            "subtotal": subtotal,
            "total": total_after_discount,
            "line_allocations": line_allocations,
        }

    def promo_discount_for_product(self, product_id: int) -> float:
        for promo in self.applied_promos:
            if int(promo.get("product_id") or 0) == int(product_id):
                return float(promo.get("discount_amount") or 0)
        return 0.0

    def company_promo_discount_for_product(self, product_id: int) -> float:
        for promo in self.applied_promos:
            if int(promo.get("product_id") or 0) == int(product_id):
                if promo.get("funding_source") == "supplier":
                    return float(promo.get("company_discount_amount") or 0)
                return float(
                    promo.get(
                        "company_discount_amount", promo.get("discount_amount", 0)
                    )
                    or 0
                )
        return 0.0

    def supplier_promotion_claims(self) -> List[Dict]:
        claims = []
        for promo in self.applied_promos:
            if promo.get("funding_source") != "supplier":
                continue
            supplier_id = promo.get("supplier_id")
            amount = round(float(promo.get("discount_amount") or 0), 2)
            if not supplier_id or amount <= 0:
                continue
            claims.append(
                {
                    "promotion_id": promo.get("promo_id"),
                    "supplier_id": supplier_id,
                    "product_id": promo.get("product_id"),
                    "quantity": promo.get("quantity") or 0,
                    "amount": amount,
                    "description": promo.get("promo_name")
                    or "Supplier funded promotion",
                }
            )
        return claims

    def _ensure_stock_available(self, product_id: int, requested_quantity: float):
        available = float(
            self.inventory_repo.get_stock(product_id, self.active_store_id) or 0
        )
        if requested_quantity > available + 0.0005:
            raise ValueError(f"الكمية غير متاحة. المتاح: {available}")
