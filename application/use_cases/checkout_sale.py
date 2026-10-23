from typing import Callable, Optional

from application.ports.checkout_port import CheckoutRepositoryPort
from models.invoice import InvoiceItem, TaxInvoiceDetails


class CheckoutSaleUseCase:
    MIN_PROFIT_RATE = 0.05  # Require minimum 5% markup over buy cost

    def __init__(
        self,
        invoice_repo: CheckoutRepositoryPort,
        totals_calculator: Callable[[], dict],
        promo_discount_for_product: Callable[[int], float],
        current_items_provider: Callable[[], list[InvoiceItem]],
        tax_invoice_provider: Callable[[], Optional[TaxInvoiceDetails]],
        company_promo_discount_for_product: Optional[Callable[[int], float]] = None,
        supplier_promotion_claims_provider: Optional[Callable[[], list[dict]]] = None,
    ):
        self.invoice_repo = invoice_repo
        self.totals_calculator = totals_calculator
        self.promo_discount_for_product = promo_discount_for_product
        self.company_promo_discount_for_product = (
            company_promo_discount_for_product or promo_discount_for_product
        )
        self.current_items_provider = current_items_provider
        self.tax_invoice_provider = tax_invoice_provider
        self.supplier_promotion_claims_provider = (
            supplier_promotion_claims_provider or (lambda: [])
        )

    def execute(
        self,
        store_id: int,
        cashier_id: int,
        drawer_id: int,
        payment_method: str,
        cash_amount: float,
        card_amount: float,
        customer_name: str = "",
        customer_phone: str = "",
        customer_address: str = "",
    ) -> str:
        items = self.current_items_provider()
        if not items:
            raise ValueError("لا توجد أصناف في الفاتورة")

        totals = self.totals_calculator()
        total_amount = float(totals["total"])
        if total_amount < 0:
            raise ValueError("إجمالي الفاتورة يجب أن يكون أكبر من صفر")
        paid_amount = float(cash_amount or 0) + float(card_amount or 0)

        if payment_method != "Credit" and paid_amount < total_amount - 0.01:
            raise ValueError(
                "الدفع غير مكتمل. اختر آجل إذا كان هناك مبلغ متبقٍ على العميل."
            )
        if payment_method == "Credit" and not customer_phone and not customer_name:
            raise ValueError("البيع الآجل يحتاج اسم العميل أو رقم الهاتف.")

        customer = (
            self.invoice_repo.get_customer_by_phone(customer_phone)
            if customer_phone
            else None
        )
        if customer and total_amount - paid_amount > 0:
            ok, message = self.invoice_repo.check_credit_limit(
                customer["id"], total_amount - paid_amount
            )
            if not ok:
                raise ValueError(message)

        self._ensure_minimum_profit(items, totals)

        items_payload = [item.to_dict() for item in items]
        allocations = totals.get("line_allocations") or []
        for idx, (source, payload) in enumerate(zip(items, items_payload)):
            alloc = allocations[idx] if idx < len(allocations) else None
            if alloc and "total_discount" in alloc:
                total_discount = alloc["total_discount"]
            else:
                total_discount = source.discount + self.promo_discount_for_product(
                    source.product_id
                )
            payload["unit_price"] = source.unit_price
            payload["discount"] = round(float(total_discount or 0), 2)
            payload["tax_percent"] = source.tax_percent

        tax_invoice_data = self.tax_invoice_provider()
        tax_payload = tax_invoice_data.__dict__ if tax_invoice_data else None

        try:
            invoice_number = self.invoice_repo.get_next_number()
            customer_id = self.invoice_repo.get_or_create_customer(
                customer_name, customer_phone, customer_address
            )
            remaining_amount = max(total_amount - paid_amount, 0)

            self.invoice_repo.validate_sale_stock(items_payload, store_id)

            discount_company = totals.get("discount_company") or {}
            discount_company_id = discount_company.get("id")
            discount_company_name = discount_company.get("name")
            company_discount_amount = float(totals.get("company_discount") or 0.0)

            header_kwargs = {
                "invoice_number": invoice_number,
                "store_id": store_id,
                "cashier_id": cashier_id,
                "customer_id": customer_id,
                "customer_name": customer_name or "Cash Customer",
                "customer_phone": customer_phone,
                "customer_address": customer_address,
                "drawer_id": drawer_id,
                "payment_method": payment_method,
                "cash_amount": cash_amount,
                "card_amount": card_amount,
                "total_amount": total_amount,
                "paid_amount": paid_amount,
                "remaining_amount": remaining_amount,
                "subtotal_amount": totals["subtotal"],
                "tax_amount": totals["tax_total"],
            }
            if discount_company_id or discount_company_name or company_discount_amount > 0:
                header_kwargs["discount_company_id"] = discount_company_id
                header_kwargs["discount_company_name"] = discount_company_name
                header_kwargs["company_discount_amount"] = company_discount_amount

            try:
                invoice_id = self.invoice_repo.insert_invoice_header(**header_kwargs)
            except TypeError:
                if discount_company_id or company_discount_amount > 0:
                    raise RuntimeError(
                        "مستودع الفواتير لا يدعم تسجيل بيانات شركة الخصم في رأس الفاتورة"
                    )
                for k in (
                    "discount_company_id",
                    "discount_company_name",
                    "company_discount_amount",
                ):
                    header_kwargs.pop(k, None)
                invoice_id = self.invoice_repo.insert_invoice_header(**header_kwargs)

            self._insert_sale_items(invoice_id, items_payload, store_id)
            self.invoice_repo.apply_sale_financial_effects(
                invoice_id=invoice_id,
                invoice_number=invoice_number,
                store_id=store_id,
                cashier_id=cashier_id,
                customer_id=customer_id,
                cash_amount=cash_amount,
                remaining_amount=remaining_amount,
            )
            self.invoice_repo.record_supplier_promotion_claims(
                sale_invoice_id=invoice_id,
                invoice_number=invoice_number,
                user_id=cashier_id,
                claims=self.supplier_promotion_claims_provider(),
            )
            self.invoice_repo.save_sale_tax_details(invoice_id, tax_payload)
            self.invoice_repo.commit()
            return invoice_number
        except Exception:
            self.invoice_repo.rollback()
            raise

    def _insert_sale_items(
        self, invoice_id: int, items: list[dict], store_id: int
    ) -> None:
        for item in items:
            product_id = int(item["product_id"])
            quantity = round(float(item.get("quantity") or 0), 3)
            unit_price = float(item.get("unit_price") or item.get("price") or 0)
            discount = round(float(item.get("discount") or 0), 2)
            total_price = round((quantity * unit_price) - discount, 2)
            item_tax = self._calculate_inclusive_tax(
                total_price, float(item.get("tax_percent") or 0)
            )
            item_subtotal = round(total_price - item_tax, 2)
            buy_price = self.invoice_repo.get_product_buy_price(product_id)

            self.invoice_repo.insert_sale_item(
                invoice_id=invoice_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                discount=discount,
                total_price=total_price,
                buy_price=buy_price,
                item_subtotal=item_subtotal,
                item_tax=item_tax,
            )
            self.invoice_repo.decrease_product_inventory(product_id, store_id, quantity)

    def _calculate_inclusive_tax(self, total: float, tax_percent: float) -> float:
        if tax_percent <= 0:
            return 0.0
        return round(total - (total / (1 + tax_percent / 100)), 2)

    def _ensure_minimum_profit(self, items: list[InvoiceItem], totals: dict) -> None:
        total_gross = sum(float(item.gross_total or 0) for item in items)
        manual_discount = float(totals.get("manual_discount") or 0)

        for item in items:
            quantity = round(float(item.quantity or 0), 3)
            if quantity <= 0:
                continue

            buy_price = float(
                self.invoice_repo.get_product_buy_price(item.product_id) or 0
            )
            if buy_price <= 0:
                continue

            item_gross = float(item.gross_total or 0)
            item_manual_discount = (
                manual_discount * (item_gross / total_gross)
                if total_gross > 0 and manual_discount > 0
                else 0.0
            )
            item_promo_discount = float(
                self.company_promo_discount_for_product(item.product_id) or 0
            )
            item_discount = (
                float(item.discount or 0) + item_promo_discount + item_manual_discount
            )
            final_total = round(item_gross - item_discount, 2)
            minimum_total = round(buy_price * (1 + self.MIN_PROFIT_RATE) * quantity, 2)

            if final_total + 0.01 < minimum_total:
                minimum_unit_price = round(buy_price * (1 + self.MIN_PROFIT_RATE), 2)
                max_discount = max(round(item_gross - minimum_total, 2), 0.0)
                raise ValueError(
                    "لا يمكن إتمام البيع لأن الخصم يجعل ربح الصنف أقل من 5%.\n"
                    f"الصنف: {item.product_name}\n"
                    f"أقل سعر مسموح للوحدة: {minimum_unit_price:,.2f} ج.م\n"
                    f"أقصى خصم مسموح لهذا الصنف في الفاتورة: {max_discount:,.2f} ج.م"
                )
