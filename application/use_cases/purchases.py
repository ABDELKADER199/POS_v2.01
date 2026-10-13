import logging
from decimal import Decimal
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

from application.errors import PurchaseValidationError
from application.ports.purchase_port import PurchaseRepositoryPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PurchaseTotals:
    subtotal: float
    discount: float
    supplier_direct_discount: float
    tax: float
    total: float
    paid: float
    remaining: float
    payment_status: str
    payment_method: str


class ListSuppliersUseCase:
    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(self) -> List[Dict]:
        return self.repo.get_all_suppliers()


class AddSupplierUseCase:
    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(self, name, phone, address, tax_number, opening_balance) -> bool:
        name = (name or "").strip()
        if not name:
            raise ValueError("اسم المورد مطلوب")
        return self.repo.add_supplier(name, phone, address, tax_number, opening_balance)


class UpdateSupplierUseCase:
    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(self, supplier_id, name, phone, address, tax_number) -> bool:
        if not supplier_id:
            raise ValueError("المورد غير صحيح")
        name = (name or "").strip()
        if not name:
            raise ValueError("اسم المورد مطلوب")
        return self.repo.update_supplier(supplier_id, name, phone, address, tax_number)


class SoftDeleteSupplierUseCase:
    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(self, supplier_id) -> bool:
        if not supplier_id:
            raise ValueError("المورد غير صحيح")
        supplier = self.repo.get_supplier(supplier_id)
        if not supplier:
            raise ValueError("المورد غير موجود")
        balance = float(supplier.get("current_balance") or 0)
        if balance > 0:
            raise ValueError("لا يمكن حذف مورد له رصيد مستحق")
        return self.repo.soft_delete_supplier(supplier_id)


class SearchPurchaseProductUseCase:
    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(self, term: str) -> Optional[Dict]:
        term = (term or "").strip()
        if not term:
            return None
        return self.repo.search_product(term)


class CreatePurchaseInvoiceUseCase:
    PAYMENT_METHODS = {
        "نقدي": "Cash",
        "كاش": "Cash",
        "Cash": "Cash",
        "آجل": "Credit",
        "Credit": "Credit",
        "شيك": "Cheque",
        "Cheque": "Cheque",
        "تحويل": "Bank Transfer",
        "Bank Transfer": "Bank Transfer",
        "Visa": "Visa",
    }

    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(
        self,
        supplier_id,
        store_id,
        user_id,
        ref_number,
        items,
        subtotal,
        discount,
        tax,
        total,
        paid,
        payment_method,
    ):
        try:
            supplier = self._validate_header(supplier_id, store_id, user_id)
            normalized_items = self._validate_items(items)
            totals = self._build_totals(
                normalized_items, discount, tax, paid, payment_method
            )

            invoice = self.repo.create_purchase_invoice_header(
                supplier_id=supplier_id,
                store_id=store_id,
                user_id=user_id,
                ref_number=(ref_number or "").strip(),
                subtotal=totals.subtotal,
                discount=totals.discount,
                tax=totals.tax,
                total=totals.total,
                paid=totals.paid,
                remaining=totals.remaining,
                payment_method=totals.payment_method,
                payment_status=totals.payment_status,
            )

            for item in normalized_items:
                product = self.repo.get_product_snapshot(item["product_id"])
                if not product:
                    raise PurchaseValidationError(f"الصنف غير موجود: {item['name']}")

                old_quantity = Decimal(
                    str(self.repo.get_product_total_stock(item["product_id"]) or 0)
                )

                old_cost = Decimal(str(product.get("buy_price") or 0))

                received_quantity = Decimal(str(item.get("received_quantity") or 0))

                quantity = Decimal(str(item.get("quantity") or 0))

                cost = Decimal(str(item.get("cost") or 0))

                supplier_direct_discount = Decimal(
                    str(item.get("supplier_direct_discount") or 0)
                )

                new_quantity = old_quantity + received_quantity

                effective_line_cost = (quantity * cost) - supplier_direct_discount

                effective_unit_cost = (
                    effective_line_cost / received_quantity
                    if received_quantity > 0
                    else cost
                )

                weighted_cost = (
                    ((old_quantity * old_cost) + effective_line_cost) / new_quantity
                    if new_quantity > 0
                    else effective_unit_cost
                )

                try:
                    self.repo.insert_purchase_item(
                        invoice_id=invoice["id"],
                        product_id=item["product_id"],
                        quantity=item["quantity"],
                        unit_cost=item["cost"],
                        expiry_date=item.get("expiry_date"),
                        supplier_support_type=item.get("supplier_support_type", "none"),
                        supplier_support_value=item.get("supplier_support_value", 0),
                        free_quantity=item.get("free_quantity", 0),
                    )
                except TypeError:
                    self.repo.insert_purchase_item(
                        invoice_id=invoice["id"],
                        product_id=item["product_id"],
                        quantity=item["quantity"],
                        unit_cost=item["cost"],
                        expiry_date=item.get("expiry_date"),
                    )
                self.repo.add_inventory_quantity(
                    item["product_id"], store_id, item["received_quantity"]
                )
                self.repo.update_product_after_purchase(
                    product_id=item["product_id"],
                    new_cost=weighted_cost,
                    buy_price=item.get("buy_price"),
                    sell_price=item.get("sell_price"),
                    supplier_id=supplier_id,
                    supplier_name=supplier.get("name", ""),
                )
                supplier_support_amount = float(item.get("supplier_claim_amount") or 0)
                if supplier_support_amount > 0:
                    try:
                        self.repo.create_supplier_funded_promotion(
                            supplier_id=supplier_id,
                            product_id=item["product_id"],
                            product_name=item["name"],
                            discount_value=supplier_support_amount,
                            invoice_id=invoice["id"],
                            support_type=item.get(
                                "supplier_support_type", "claim_per_unit"
                            ),
                            support_value=item.get(
                                "supplier_support_value", supplier_support_amount
                            ),
                            promo_type="fixed_per_unit",
                        )
                    except TypeError:
                        self.repo.create_supplier_funded_promotion(
                            supplier_id=supplier_id,
                            product_id=item["product_id"],
                            product_name=item["name"],
                            discount_value=supplier_support_amount,
                            invoice_id=invoice["id"],
                        )

            if totals.remaining > 0:
                self.repo.increase_supplier_balance(supplier_id, totals.remaining)
            if totals.remaining > 0:
                self.repo.record_supplier_purchase_debt(
                    supplier_id=supplier_id,
                    store_id=store_id,
                    user_id=user_id,
                    invoice_id=invoice["id"],
                    amount=totals.remaining,
                    description=f"مديونية فاتورة شراء {invoice['invoice_number']}",
                )

                self.repo.increase_supplier_balance(
                    supplier_id,
                    totals.remaining,
                )

            if totals.paid > 0:
                self.repo.record_supplier_payment(
                    supplier_id=supplier_id,
                    store_id=store_id,
                    user_id=user_id,
                    invoice_id=invoice["id"],
                    amount=totals.paid,
                    payment_method=totals.payment_method,
                    description=f"دفعة مباشرة لفاتورة شراء {invoice['invoice_number']}",
                    record_ledger=False,
                )

            self.repo.sync_supplier_balance_from_open_invoices(supplier_id)
            self.repo.commit()
            return invoice
        except PurchaseValidationError:
            raise
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error saving purchase invoice: %s", exc, exc_info=True)
            return None

    def _validate_header(self, supplier_id: int, store_id: int, user_id: int) -> Dict:
        if not supplier_id:
            raise PurchaseValidationError("يجب اختيار المورد")
        if not store_id:
            raise PurchaseValidationError("لا يوجد فرع/مخزن مرتبط بالمستخدم")
        if not user_id:
            raise PurchaseValidationError("لا يوجد مستخدم صالح لتنفيذ العملية")
        supplier = self.repo.get_supplier(supplier_id)
        if not supplier:
            raise PurchaseValidationError("المورد غير موجود")
        if "is_active" in supplier and not bool(supplier.get("is_active")):
            raise PurchaseValidationError("المورد غير نشط")
        return supplier

    def _validate_items(self, items: List[Dict]) -> List[Dict]:
        if not items:
            raise PurchaseValidationError("الفاتورة فارغة")
        normalized = []
        for index, item in enumerate(items, 1):
            product_id = item.get("product_id")
            quantity = float(item.get("quantity") or 0)
            free_quantity = float(item.get("free_quantity") or 0)
            cost = float(item.get("cost") or 0)
            sell_price = float(item.get("sell_price") or 0)
            expiry_date = self._normalize_expiry(item.get("expiry_date"))
            if not product_id:
                raise PurchaseValidationError(f"الصنف رقم {index} غير مرتبط بمنتج")
            if quantity <= 0:
                raise PurchaseValidationError(
                    f"كمية الصنف رقم {index} يجب أن تكون أكبر من صفر"
                )
            if free_quantity < 0:
                raise PurchaseValidationError(
                    f"الكمية المجانية للصنف رقم {index} لا يمكن أن تكون سالبة"
                )
            if cost < 0:
                raise PurchaseValidationError(
                    f"تكلفة الصنف رقم {index} لا يمكن أن تكون سالبة"
                )
            if sell_price < 0:
                raise PurchaseValidationError(
                    f"سعر بيع الصنف رقم {index} لا يمكن أن يكون سالبًا"
                )
            legacy_support_amount = float(item.get("supplier_support_amount") or 0)
            supplier_support_type = (item.get("supplier_support_type") or "").strip()
            if not supplier_support_type:
                supplier_support_type = (
                    "claim_per_unit" if legacy_support_amount > 0 else "none"
                )
            allowed_support_types = {
                "none",
                "claim_per_unit",
                "claim_percent",
                "direct_per_unit",
                "direct_percent",
                "free_quantity",
            }
            if supplier_support_type not in allowed_support_types:
                raise PurchaseValidationError("نوع دعم المورد غير صحيح")
            supplier_support_value = round(
                float(
                    item.get(
                        "supplier_support_value", item.get("supplier_support_amount", 0)
                    )
                    or 0
                ),
                2,
            )
            if supplier_support_value < 0:
                raise PurchaseValidationError("دعم المورد لا يمكن أن يكون سالبًا")
            if (
                supplier_support_type == "claim_per_unit"
                and sell_price > 0
                and supplier_support_value >= sell_price
            ):
                raise PurchaseValidationError("دعم المورد يجب أن يكون أقل من سعر البيع")
            if (
                supplier_support_type in {"claim_percent", "direct_percent"}
                and supplier_support_value > 100
            ):
                raise PurchaseValidationError("نسبة دعم المورد لا يمكن أن تتجاوز 100%")
            supplier_claim_amount = 0.0
            supplier_direct_discount = 0.0
            if supplier_support_type == "claim_per_unit":
                supplier_claim_amount = supplier_support_value
            elif supplier_support_type == "claim_percent":
                supplier_claim_amount = round(
                    cost * (supplier_support_value / 100.0), 2
                )
            elif supplier_support_type == "direct_per_unit":
                supplier_direct_discount = round(supplier_support_value * quantity, 2)
            elif supplier_support_type == "direct_percent":
                supplier_direct_discount = round(
                    (quantity * cost) * (supplier_support_value / 100.0), 2
                )
            line_total = round(quantity * cost, 2)
            if supplier_direct_discount > line_total:
                raise PurchaseValidationError(
                    "خصم المورد المباشر أكبر من إجمالي سطر الشراء"
                )
            received_quantity = quantity + free_quantity
            normalized.append(
                {
                    "product_id": product_id,
                    "name": item.get("name")
                    or item.get("product_name")
                    or str(product_id),
                    "quantity": quantity,
                    "free_quantity": free_quantity,
                    "received_quantity": received_quantity,
                    "cost": cost,
                    "sell_price": sell_price if sell_price > 0 else None,
                    "expiry_date": expiry_date,
                    "supplier_support_type": supplier_support_type,
                    "supplier_support_value": supplier_support_value,
                    "supplier_claim_amount": supplier_claim_amount,
                    "supplier_direct_discount": supplier_direct_discount,
                }
            )
        return normalized

    def _build_totals(
        self,
        items: List[Dict],
        discount: float,
        tax: float,
        paid: float,
        payment_method: str,
    ) -> PurchaseTotals:
        subtotal = round(sum(item["quantity"] * item["cost"] for item in items), 2)
        supplier_direct_discount = round(
            sum(item.get("supplier_direct_discount", 0) for item in items), 2
        )
        discount = round(float(discount or 0), 2)
        tax = round(float(tax or 0), 2)
        paid = round(float(paid or 0), 2)
        if discount < 0:
            raise PurchaseValidationError("الخصم لا يمكن أن يكون سالبًا")
        if tax < 0:
            raise PurchaseValidationError("الضريبة لا يمكن أن تكون سالبة")
        if discount + supplier_direct_discount > subtotal:
            raise PurchaseValidationError("الخصم أكبر من إجمالي الفاتورة")
        total = round(subtotal - discount - supplier_direct_discount + tax, 2)
        if total <= 0:
            raise PurchaseValidationError("صافي الفاتورة يجب أن يكون أكبر من صفر")
        if paid < 0:
            raise PurchaseValidationError("المدفوع لا يمكن أن يكون سالبًا")
        if paid > total:
            raise PurchaseValidationError("المدفوع أكبر من صافي الفاتورة")
        method = self._normalize_payment_method(payment_method)
        if method == "Credit":
            paid = 0.0
        remaining = round(total - paid, 2)
        status = "paid" if remaining <= 0 else "partial" if paid > 0 else "unpaid"
        return PurchaseTotals(
            subtotal=subtotal,
            discount=round(discount + supplier_direct_discount, 2),
            supplier_direct_discount=supplier_direct_discount,
            tax=tax,
            total=total,
            paid=paid,
            remaining=remaining,
            payment_status=status,
            payment_method=method,
        )

    def _normalize_payment_method(self, payment_method: str) -> str:
        return self.PAYMENT_METHODS.get(payment_method, payment_method or "Cash")

    def _normalize_expiry(self, value) -> Optional[str]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        text = str(value).strip()
        if not text:
            return None
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError as exc:
            raise PurchaseValidationError(f"تاريخ الصلاحية غير صحيح: {text}") from exc
        return text


class PurchaseHistoryUseCase:
    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(self, page: int = 1, per_page: int = 100) -> List[Dict]:
        page = max(int(page or 1), 1)
        per_page = min(max(int(per_page or 100), 1), 500)
        try:
            self.repo.reconcile_purchase_return_credits()
            self.repo.sync_supplier_balance_from_open_invoices()
            self.repo.commit()
        except Exception as exc:
            self.repo.rollback()
            logger.warning("Could not reconcile purchase return credits: %s", exc)
        return self.repo.get_purchase_history(page=page, per_page=per_page)


class PurchaseInvoiceDetailsUseCase:
    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(self, search_term: str) -> Optional[Dict]:
        search_term = (search_term or "").strip()
        if not search_term:
            raise PurchaseValidationError("أدخل رقم فاتورة الشراء")
        invoice = self.repo.get_purchase_invoice_details(search_term)
        if not invoice:
            raise PurchaseValidationError("فاتورة الشراء غير موجودة")
        return invoice


class CreatePurchaseReturnUseCase:
    SETTLEMENT_CREDIT = "credit"
    SETTLEMENT_CASH = "cash_refund"

    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(
        self,
        invoice_id,
        supplier_id,
        store_id,
        user_id,
        items,
        settlement_method,
        reason="",
    ):
        if not invoice_id:
            raise PurchaseValidationError("رقم فاتورة الشراء غير صحيح")
        if not supplier_id:
            raise PurchaseValidationError("لا يوجد مورد مرتبط بالفاتورة")
        if not store_id:
            raise PurchaseValidationError("اختر فرع المرتجع")
        if not user_id:
            raise PurchaseValidationError("لا يوجد مستخدم صالح لتنفيذ مرتجع الشراء")

        settlement_method = settlement_method or self.SETTLEMENT_CREDIT
        if settlement_method not in (self.SETTLEMENT_CREDIT, self.SETTLEMENT_CASH):
            raise PurchaseValidationError("طريقة تسوية مرتجع الشراء غير صحيحة")

        normalized_items = self._validate_items(items)
        total_amount = round(
            sum(item["quantity"] * item["unit_cost"] for item in normalized_items), 2
        )
        if total_amount <= 0:
            raise PurchaseValidationError("إجمالي مرتجع الشراء يجب أن يكون أكبر من صفر")

        try:
            for item in normalized_items:
                available_to_return = self.repo.get_purchase_item_remaining_quantity(
                    invoice_id,
                    item["product_id"],
                )
                if item["quantity"] > available_to_return:
                    raise PurchaseValidationError(
                        f"كمية مرتجع {item['product_name']} أكبر من الكمية المتاحة للارتجاع"
                    )
                branch_stock = self.repo.get_inventory_quantity(
                    item["product_id"], store_id
                )
                if item["quantity"] > branch_stock:
                    raise PurchaseValidationError(
                        f"مخزون الفرع لا يكفي لارتجاع {item['product_name']}: المتاح {branch_stock}"
                    )

            purchase_return = self.repo.create_purchase_return_header(
                purchase_invoice_id=invoice_id,
                supplier_id=supplier_id,
                store_id=store_id,
                user_id=user_id,
                total_amount=total_amount,
                settlement_method=settlement_method,
                reason=(reason or "").strip(),
            )
            for item in normalized_items:
                self.repo.insert_purchase_return_item(
                    return_id=purchase_return["id"],
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    unit_cost=item["unit_cost"],
                )
                self.repo.decrease_inventory_quantity(
                    item["product_id"], store_id, item["quantity"]
                )

            if settlement_method == self.SETTLEMENT_CREDIT:
                self.repo.reconcile_purchase_return_credits(invoice_id)
                self.repo.record_supplier_purchase_return_credit(
                    supplier_id=supplier_id,
                    store_id=store_id,
                    user_id=user_id,
                    return_id=purchase_return["id"],
                    amount=total_amount,
                    description=f"مرتجع شراء {purchase_return['return_number']}",
                )
            else:
                self.repo.record_purchase_return_cash_refund(
                    supplier_id=supplier_id,
                    store_id=store_id,
                    user_id=user_id,
                    return_id=purchase_return["id"],
                    amount=total_amount,
                    description=f"استرداد نقدي لمرتجع شراء {purchase_return['return_number']}",
                )

            self.repo.sync_supplier_balance_from_open_invoices(supplier_id)
            self.repo.commit()
            return {
                **purchase_return,
                "total_amount": total_amount,
                "items": normalized_items,
                "settlement_method": settlement_method,
            }
        except PurchaseValidationError:
            self.repo.rollback()
            raise
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error creating purchase return: %s", exc, exc_info=True)
            return None

    def _validate_items(self, items: List[Dict]) -> List[Dict]:
        normalized = []
        for item in items or []:
            quantity = float(item.get("return_quantity") or item.get("quantity") or 0)
            if quantity <= 0:
                continue
            product_id = item.get("product_id")
            unit_cost = float(item.get("unit_cost") or item.get("cost") or 0)
            if not product_id:
                raise PurchaseValidationError("يوجد صنف غير مرتبط بمنتج")
            if unit_cost < 0:
                raise PurchaseValidationError("تكلفة الصنف لا يمكن أن تكون سالبة")
            normalized.append(
                {
                    "product_id": product_id,
                    "product_name": item.get("product_name")
                    or item.get("name")
                    or str(product_id),
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total": round(quantity * unit_cost, 2),
                }
            )
        if not normalized:
            raise PurchaseValidationError("حدد كمية واحدة على الأقل لمرتجع الشراء")
        return normalized


class SupplierPaymentUseCase:
    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(self, supplier_id, amount, store_id=None, user_id=None) -> bool:
        amount = float(amount or 0)
        if not supplier_id:
            raise ValueError("يجب اختيار المورد")
        if amount <= 0:
            raise ValueError("قيمة السداد يجب أن تكون أكبر من صفر")
        if not store_id or not user_id:
            raise ValueError("يجب تحديد الفرع والمستخدم قبل تسجيل السداد")
        try:
            self.repo.decrease_supplier_balance(supplier_id, amount)
            self.repo.allocate_supplier_payment(supplier_id, amount)
            self.repo.record_supplier_payment(
                supplier_id=supplier_id,
                store_id=store_id,
                user_id=user_id,
                invoice_id=None,
                amount=amount,
                payment_method="Cash",
                description="سداد عام لمورد",
                record_ledger=True,
            )
            self.repo.sync_supplier_balance_from_open_invoices(supplier_id)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error making supplier payment: %s", exc, exc_info=True)
            return False


class PayPurchaseInvoiceUseCase:
    def __init__(self, repo: PurchaseRepositoryPort):
        self.repo = repo

    def execute(self, invoice_id, amount, payment_method, user_id, store_id) -> bool:
        if not invoice_id:
            raise PurchaseValidationError("رقم الفاتورة غير صحيح")
        amount = float(amount or 0)
        if amount <= 0:
            raise PurchaseValidationError("قيمة السداد يجب أن تكون أكبر من صفر")

        invoice = self.repo.get_purchase_invoice_for_payment(invoice_id)
        if not invoice:
            raise PurchaseValidationError("فاتورة الشراء غير موجودة")

        remaining = float(invoice.get("remaining_amount") or 0)
        if remaining <= 0:
            raise PurchaseValidationError("الفاتورة مسددة بالفعل")
        if amount > remaining:
            raise PurchaseValidationError("قيمة السداد أكبر من المتبقي")

        current_paid = float(invoice.get("paid_amount") or 0)
        new_paid = current_paid + amount
        new_remaining = max(remaining - amount, 0)
        status = "paid" if new_remaining <= 0 else "partial"
        method = self._normalize_payment_method(payment_method)

        try:
            self.repo.update_purchase_invoice_payment_state(
                invoice_id=invoice_id,
                paid_amount=new_paid,
                remaining_amount=new_remaining,
                payment_status=status,
                payment_method=method,
            )
            self.repo.decrease_supplier_balance(invoice["supplier_id"], amount)
            self.repo.record_supplier_payment(
                supplier_id=invoice["supplier_id"],
                store_id=store_id,
                user_id=user_id,
                invoice_id=invoice_id,
                amount=amount,
                payment_method=method,
                description=f"سداد فاتورة شراء {invoice.get('invoice_number') or invoice_id}",
                record_ledger=False,
            )
            self.repo.sync_supplier_balance_from_open_invoices(invoice["supplier_id"])
            self.repo.commit()
            return True
        except PurchaseValidationError:
            raise
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error updating purchase payment: %s", exc, exc_info=True)
            return False

    def _normalize_payment_method(self, payment_method: str) -> str:
        return CreatePurchaseInvoiceUseCase.PAYMENT_METHODS.get(
            payment_method, payment_method or "Cash"
        )
