import logging
from datetime import datetime
from typing import Dict, List, Optional

from application.ports.returns_port import ReturnsRepositoryPort

logger = logging.getLogger(__name__)


class ReturnInvoiceQueryUseCase:
    def __init__(self, repo: ReturnsRepositoryPort):
        self.repo = repo

    def search_invoice(self, invoice_number: str) -> Optional[Dict]:
        invoice_number = str(invoice_number or "").strip()
        if not invoice_number:
            return None
        return self.repo.get_invoice_by_number(invoice_number)

    def get_invoice_items(self, invoice_id: int) -> List[Dict]:
        if not invoice_id:
            return []
        return self.repo.get_invoice_items(invoice_id)


class ProcessReturnUseCase:
    def __init__(self, repo: ReturnsRepositoryPort):
        self.repo = repo
        self.last_error = ""

    def execute(self, invoice_id, items, reason, user_id, store_id, drawer_id=None):
        self.last_error = ""
        try:
            if not invoice_id:
                raise ValueError("رقم الفاتورة غير صحيح")
            if not items:
                raise ValueError("يجب اختيار صنف واحد على الأقل للمرتجع")
            if not user_id:
                raise ValueError("لا يوجد مستخدم صالح لتنفيذ المرتجع")
            if not store_id:
                raise ValueError("لا يوجد فرع صالح لتنفيذ المرتجع")

            try:
                invoice = self.repo.get_invoice_for_return(invoice_id, for_update=True)
            except TypeError:
                invoice = self.repo.get_invoice_for_return(invoice_id)

            if not invoice or invoice.get("status") != "Completed":
                raise ValueError("لا يمكن تنفيذ مرتجع إلا لفاتورة مكتملة")
            if int(invoice.get("store_id") or 0) != int(store_id):
                raise ValueError("لا يمكن تنفيذ المرتجع على فرع مختلف عن فرع الفاتورة")

            normalized_items = self._normalize_return_items(invoice_id, items)
            total_return = sum(item["total_price"] for item in normalized_items)
            if total_return <= 0:
                raise ValueError("إجمالي المرتجع يجب أن يكون أكبر من صفر")

            return_number = f"RET-{datetime.now():%Y%m%d%H%M%S%f}"
            return_id = self.repo.create_return_header(
                return_number=return_number,
                invoice_id=invoice_id,
                store_id=store_id,
                user_id=user_id,
                total_return=total_return,
                reason=reason,
                drawer_id=drawer_id,
            )

            for item in normalized_items:
                self.repo.insert_return_item(return_id, item)
                self.repo.add_inventory_quantity(
                    item["product_id"], store_id, item["quantity"]
                )

            credit_adjustment = self._calculate_credit_adjustment(invoice, total_return)
            cash_refund = self._calculate_cash_refund(
                invoice, total_return, credit_adjustment
            )

            if cash_refund > 0:
                self.repo.record_cash_refund(
                    store_id,
                    cash_refund,
                    return_id,
                    invoice.get("invoice_number"),
                    return_number,
                    user_id,
                )

            customer_id = invoice.get("customer_id")
            if customer_id and credit_adjustment > 0:
                self.repo.reduce_customer_balance(customer_id, credit_adjustment)
                self.repo.record_customer_return_ledger(
                    customer_id,
                    credit_adjustment,
                    return_id,
                    invoice.get("invoice_number"),
                    user_id,
                )

            self.repo.commit()
            return {
                "return_id": return_id,
                "return_number": return_number,
                "invoice_number": invoice.get("invoice_number"),
                "total_amount": total_return,
                "cash_refund": cash_refund,
                "credit_adjustment": credit_adjustment,
                "reason": reason,
                "items": normalized_items,
            }
        except Exception as exc:
            self.last_error = str(exc)
            logger.error("Error processing return: %s", exc, exc_info=True)
            self.repo.rollback()
            return None

    def _normalize_return_items(self, invoice_id: int, items: list) -> List[Dict]:
        from decimal import Decimal, ROUND_HALF_UP

        invoice_lines = self.repo.get_invoice_items(invoice_id)
        if not invoice_lines:
            raise ValueError("لا توجد أصناف مسجلة في هذه الفاتورة")

        lines_by_item_id = {}
        lines_by_product_id = {}
        for idx, row in enumerate(invoice_lines, start=1):
            line_id = row.get("invoice_item_id") or row.get("id") or idx
            row["invoice_item_id"] = line_id
            lines_by_item_id[line_id] = row
            pid = int(row["product_id"])
            lines_by_product_id.setdefault(pid, []).append(row)

        requested_lines = {}
        for item in items:
            req_qty = Decimal(str(item.get("quantity") or 0))
            if req_qty <= Decimal("0"):
                continue

            line_id = item.get("invoice_item_id")
            if line_id is not None:
                if line_id not in lines_by_item_id:
                    raise ValueError(f"سطر الفاتورة رقم {line_id} غير موجود في هذه الفاتورة")
            else:
                pid = int(item.get("product_id") or 0)
                matching = lines_by_product_id.get(pid, [])
                if not matching:
                    raise ValueError("تم اختيار صنف غير موجود في الفاتورة")
                if len(matching) > 1:
                    raise ValueError(
                        f"الصنف '{matching[0].get('product_name')}' مسجل في أكثر من سطر بالفاتورة بأسعار مختلفة؛ "
                        f"يجب تحديد سطر الفاتورة (invoice_item_id) بدقة لمنع الخطأ في الحساب."
                    )
                line_id = matching[0]["invoice_item_id"]

            requested_lines[line_id] = requested_lines.get(line_id, Decimal("0.0")) + req_qty

        normalized_items = []
        for line_id, return_qty in requested_lines.items():
            line = lines_by_item_id[line_id]

            if line.get("is_ambiguous_return"):
                raise ValueError(
                    f"الفاتورة تحتوي على مرتجع تاريخي غير محدد السطر للصنف '{line.get('product_name')}'. "
                    f"لا يمكن معالجة المرتجع آلياً لمنع الانحراف المالي، ويرجى مراجعة إدارة الحسابات."
                )

            sold_qty = Decimal(str(line.get("quantity") or 0))
            returned_qty = Decimal(str(line.get("returned_quantity") or 0))
            available_qty = max(Decimal("0.0"), sold_qty - returned_qty)

            if return_qty <= Decimal("0.0") or return_qty > available_qty:
                raise ValueError(
                    f"كمية المرتجع غير صحيحة للصنف: {line.get('product_name')} "
                    f"(المطلوب: {return_qty}، المتاح: {available_qty})"
                )

            unit_price = Decimal(str(line.get("unit_price") or 0))
            buy_price = Decimal(str(line.get("buy_price") or 0))
            tot_price_val = line.get("total_price")
            sold_total_price = (
                Decimal(str(tot_price_val))
                if tot_price_val is not None
                else (unit_price * sold_qty)
            )

            effective_unit_price = (
                (sold_total_price / sold_qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if sold_qty > Decimal("0")
                else unit_price
            )

            prev_refund = Decimal(str(line.get("line_returned_amount") or "0.0"))
            if prev_refund <= Decimal("0.0") and returned_qty > Decimal("0.0"):
                prev_refund = (returned_qty * effective_unit_price).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            if return_qty == available_qty:
                line_refund = max(Decimal("0.0"), sold_total_price - prev_refund)
            else:
                line_refund = (return_qty * effective_unit_price).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if prev_refund + line_refund > sold_total_price:
                    line_refund = max(Decimal("0.0"), sold_total_price - prev_refund)

            normalized_items.append(
                {
                    "invoice_item_id": line_id,
                    "product_id": int(line["product_id"]),
                    "product_name": line.get("product_name", ""),
                    "quantity": float(return_qty),
                    "unit_price": float(effective_unit_price),
                    "buy_price": float(buy_price),
                    "total_price": float(line_refund),
                }
            )
        return normalized_items

    def _calculate_credit_adjustment(self, invoice: Dict, total_return: float) -> float:
        payment_method = (invoice.get("payment_method") or "").lower()
        customer_id = invoice.get("customer_id")
        remaining_amount = float(invoice.get("remaining_amount") or 0)
        if not customer_id:
            return 0.0
        if payment_method == "credit":
            return min(total_return, max(remaining_amount, 0.0))
        if remaining_amount > 0:
            return min(total_return, remaining_amount)
        return 0.0

    def _calculate_cash_refund(
        self, invoice: Dict, total_return: float, credit_adjustment: float
    ) -> float:
        payment_method = (invoice.get("payment_method") or "").lower()
        cash_amount = float(invoice.get("cash_amount") or 0)
        refundable = max(0.0, total_return - credit_adjustment)
        if payment_method == "card":
            return 0.0
        if cash_amount > 0:
            return min(refundable, cash_amount)
        if payment_method in ("cash", "mixed"):
            return refundable
        return 0.0


class ReturnsHistoryUseCase:
    def __init__(self, repo: ReturnsRepositoryPort):
        self.repo = repo

    def execute(self, **kwargs):
        return self.repo.get_returns_history(**kwargs)


class ReturnsDrawerQueryUseCase:
    def __init__(self, repo: ReturnsRepositoryPort):
        self.repo = repo

    def get_drawer_status(self, user_id):
        if not user_id:
            return None
        return self.repo.get_drawer_status(user_id)

    def get_store_open_drawer(self, store_id):
        if not store_id:
            return None
        return self.repo.get_store_open_drawer(store_id)
