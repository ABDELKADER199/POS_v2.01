import logging
from typing import Dict, List

from application.ports.accounts_port import (
    AccountsRepositoryPort,
    PromotionCatalogPort,
)
from application.errors import AccountsValidationError, PromotionCatalogError
from application.ports.audit_port import AuditPort

logger = logging.getLogger(__name__)

RECORD_PAYMENT_ACTION = "accounts.record_payment"
RECORD_SETTLEMENT_ACTION = "accounts.record_settlement"
ADD_EXPENSE_ACTION = "expenses.add"
VOID_EXPENSE_ACTION = "expenses.void"
RECORD_TREASURY_ACTION = "treasury.record_transaction"
UPDATE_CREDIT_LIMIT_ACTION = "customers.update_credit_limit"


class AccountsQueryUseCase:
    def __init__(self, repo: AccountsRepositoryPort):
        self.repo = repo
        self.last_error = ""

    def get_customer_accounts(self) -> List[Dict]:
        return self.repo.get_customer_accounts()

    def get_all_suppliers(self) -> List[Dict]:
        return self.repo.get_all_suppliers()

    def get_account_history(self, account_type, account_id) -> List[Dict]:
        return self.repo.get_account_history(account_type, account_id)

    def get_financial_ledger(self, search="", acc_type="") -> List[Dict]:
        return self.repo.get_financial_ledger(search, acc_type)

    def get_debt_totals(self) -> Dict:
        return self.repo.get_debt_totals()

    def get_debt_aging_report(self) -> List[Dict]:
        return self.repo.get_debt_aging_report()

    def get_treasury_transactions(self) -> List[Dict]:
        return self.repo.get_treasury_transactions()

    def get_treasury_balance(self) -> float:
        return self.repo.get_treasury_balance()

    def get_expenses(self, store_id) -> List[Dict]:
        return self.repo.get_expenses(store_id)

    def get_financial_report(self, store_id, start_date, end_date) -> Dict:
        return self.repo.get_financial_report(store_id, start_date, end_date)

    def get_all_stores(self) -> List[Dict]:
        return self.repo.get_all_stores()


class RecordAccountPaymentUseCase:
    ACCOUNT_TYPES = {"Customer", "Supplier"}
    TREASURY_SOURCE_PAYMENT = "Settlement"

    def __init__(self, repo: AccountsRepositoryPort, audit: AuditPort):
        self.repo = repo
        self.audit = audit

    def execute(
        self, account_type, account_id, amount, user_id, desc, attachment_path=""
    ) -> bool:
        account, amount = self._validate_account_operation(
            account_type, account_id, amount, user_id
        )
        desc = desc or self._default_payment_description(account_type, account)
        treasury_type = "In" if account_type == "Customer" else "Out"
        store_id = self.repo.get_user_store_id(user_id)
        try:
            self.repo.update_account_balance(account_type, account_id, -amount)
            ledger_id = self.repo.insert_ledger_entry(
                account_type=account_type,
                account_id=account_id,
                transaction_type="Debit",
                amount=amount,
                reference_type="Payment",
                description=desc,
                user_id=user_id,
                attachment_path=attachment_path,
            )
            if account_type == "Supplier":
                self.repo.allocate_supplier_payment(account_id, amount)
            self.repo.insert_treasury_entry(
                store_id=store_id,
                transaction_type=treasury_type,
                amount=amount,
                source_type=self.TREASURY_SOURCE_PAYMENT,
                reference_id=ledger_id,
                description=desc,
                user_id=user_id,
            )
            self.repo.commit()
            self.audit.log(
                user_id,
                RECORD_PAYMENT_ACTION,
                entity_type=account_type,
                entity_id=account_id,
                success=True,
                details={"amount": amount, "description": desc},
            )
            return True
        except AccountsValidationError:
            raise
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error recording account payment: %s", exc, exc_info=True)
            return False

    def _validate_account_operation(
        self, account_type: str, account_id: int, amount: float, user_id: int
    ):
        if account_type not in self.ACCOUNT_TYPES:
            raise AccountsValidationError("نوع الحساب غير صحيح")
        if not account_id:
            raise AccountsValidationError("رقم الحساب غير صحيح")
        if not user_id:
            raise AccountsValidationError("لا يوجد مستخدم صالح لتنفيذ العملية")
        amount = round(float(amount or 0), 2)
        if amount <= 0:
            raise AccountsValidationError("المبلغ يجب أن يكون أكبر من صفر")
        account = self.repo.get_account_snapshot(account_type, account_id)
        if not account:
            raise AccountsValidationError("الحساب غير موجود")
        return account, amount

    def _default_payment_description(self, account_type: str, account: dict) -> str:
        name = account.get("name") or account.get("phone") or ""
        if account_type == "Customer":
            return f"تحصيل من العميل {name}".strip()
        return f"دفع للمورد {name}".strip()


class UpdateCreditLimitUseCase:
    def __init__(self, repo: AccountsRepositoryPort, audit: AuditPort):
        self.repo = repo
        self.audit = audit

    def execute(self, customer_id, limit, user_id=None) -> bool:
        if not customer_id:
            raise AccountsValidationError("رقم العميل غير صحيح")
        limit = round(float(limit or 0), 2)
        if limit < 0:
            raise AccountsValidationError("حد الائتمان لا يمكن أن يكون أقل من صفر")
        resolved_user_id = user_id or 1
        try:
            self.repo.update_customer_credit_limit(customer_id, limit)
            self.repo.commit()
            self.audit.log(
                resolved_user_id,
                UPDATE_CREDIT_LIMIT_ACTION,
                entity_type="customer",
                entity_id=customer_id,
                success=True,
                details={"credit_limit": limit},
            )
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error updating credit limit: %s", exc, exc_info=True)
            return False


class RecordSettlementUseCase:
    ACCOUNT_TYPES = {"Customer", "Supplier"}

    def __init__(self, repo: AccountsRepositoryPort, audit: AuditPort):
        self.repo = repo
        self.audit = audit

    def execute(
        self, account_type, account_id, amount, desc, user_id, attachment_path=""
    ) -> bool:
        amount = self._validate_account_operation(
            account_type, account_id, amount, user_id
        )
        desc = desc or "تسوية رصيد حساب"
        store_id = self.repo.get_user_store_id(user_id)
        try:
            self.repo.update_account_balance(account_type, account_id, -amount)
            ledger_id = self.repo.insert_ledger_entry(
                account_type=account_type,
                account_id=account_id,
                transaction_type="Debit",
                amount=amount,
                reference_type="Adjustment",
                description=desc,
                user_id=user_id,
                attachment_path=attachment_path,
                is_settlement=True,
            )
            treasury_type = "Out" if account_type == "Supplier" else "In"
            self.repo.insert_treasury_entry(
                store_id=store_id,
                transaction_type=treasury_type,
                amount=amount,
                source_type="Settlement",
                reference_id=ledger_id,
                description=desc,
                user_id=user_id,
            )
            if account_type == "Supplier":
                self.repo.allocate_supplier_payment(account_id, amount)
            self.repo.commit()
            self.audit.log(
                user_id,
                RECORD_SETTLEMENT_ACTION,
                entity_type=account_type,
                entity_id=account_id,
                success=True,
                details={"amount": amount, "description": desc},
            )
            return True
        except AccountsValidationError:
            raise
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error recording settlement: %s", exc, exc_info=True)
            return False

    def _validate_account_operation(
        self, account_type: str, account_id: int, amount: float, user_id: int
    ) -> float:
        if account_type not in self.ACCOUNT_TYPES:
            raise AccountsValidationError("نوع الحساب غير صحيح")
        if not account_id:
            raise AccountsValidationError("رقم الحساب غير صحيح")
        if not user_id:
            raise AccountsValidationError("لا يوجد مستخدم صالح لتنفيذ العملية")
        amount = round(float(amount or 0), 2)
        if amount <= 0:
            raise AccountsValidationError("المبلغ يجب أن يكون أكبر من صفر")
        if not self.repo.get_account_snapshot(account_type, account_id):
            raise AccountsValidationError("الحساب غير موجود")
        return amount


class TreasuryTransactionUseCase:
    VALID_TRANSACTION_TYPES = {"In", "Out"}

    def __init__(self, repo: AccountsRepositoryPort, audit: AuditPort):
        self.repo = repo
        self.audit = audit

    def execute(
        self,
        store_id,
        trans_type,
        amount,
        source_type,
        source_id,
        desc,
        user_id,
    ) -> bool:
        if not store_id:
            raise AccountsValidationError("لا يوجد فرع صالح لتسجيل حركة الخزينة")
        if not user_id:
            raise AccountsValidationError("لا يوجد مستخدم صالح لتنفيذ العملية")
        trans_type = (trans_type or "").strip()
        if trans_type not in self.VALID_TRANSACTION_TYPES:
            raise AccountsValidationError("نوع حركة الخزينة غير صحيح")
        amount = self._validate_amount(amount)
        source_type = (source_type or "Adjustment").strip()
        desc = (desc or "").strip() or "حركة خزينة يدوية"

        try:
            transaction_id = self.repo.insert_treasury_entry(
                store_id=store_id,
                transaction_type=trans_type,
                amount=amount,
                source_type=source_type,
                reference_id=source_id,
                description=desc,
                user_id=user_id,
            )
            self.repo.commit()
            self.audit.log(
                user_id,
                RECORD_TREASURY_ACTION,
                entity_type="treasury",
                entity_id=transaction_id,
                store_id=store_id,
                success=True,
                details={
                    "transaction_type": trans_type,
                    "amount": amount,
                    "source_type": source_type,
                    "description": desc,
                },
            )
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error recording treasury transaction: %s", exc, exc_info=True)
            return False

    def _validate_amount(self, amount: float) -> float:
        amount = round(float(amount or 0), 2)
        if amount <= 0:
            raise AccountsValidationError("المبلغ يجب أن يكون أكبر من صفر")
        return amount


class ExpenseUseCase:
    TREASURY_SOURCE_EXPENSE = "Expense"
    TREASURY_SOURCE_ADJUSTMENT = "Adjustment"

    def __init__(self, repo: AccountsRepositoryPort, audit: AuditPort):
        self.repo = repo
        self.audit = audit

    def add(self, store_id, user_id, expense_type, amount, desc, is_personal) -> bool:
        if not store_id:
            raise AccountsValidationError("لا يوجد فرع صالح لتسجيل المصروف")
        if not user_id:
            raise AccountsValidationError("لا يوجد مستخدم صالح لتنفيذ العملية")
        amount = self._validate_amount(amount)
        expense_type = (expense_type or "").strip()
        if not expense_type:
            raise AccountsValidationError("نوع المصروف مطلوب")
        desc = desc or ""
        entry_description = f"مصروف: {expense_type}"
        if desc:
            entry_description += f" - {desc}"

        try:
            expense_id = self.repo.insert_expense(
                store_id=store_id,
                user_id=user_id,
                expense_type=expense_type,
                amount=amount,
                description=desc,
                is_personal=is_personal,
            )
            self.repo.insert_treasury_entry(
                store_id=store_id,
                transaction_type="Out",
                amount=amount,
                source_type=self.TREASURY_SOURCE_EXPENSE,
                reference_id=expense_id,
                description=entry_description,
                user_id=user_id,
            )
            self.repo.insert_ledger_entry(
                account_type="Expense",
                account_id=user_id,
                transaction_type="Debit",
                amount=amount,
                reference_type="Expense",
                reference_id=expense_id,
                description=entry_description,
                user_id=user_id,
            )
            self.repo.commit()
            self.audit.log(
                user_id,
                ADD_EXPENSE_ACTION,
                entity_type="expense",
                entity_id=expense_id,
                store_id=store_id,
                success=True,
                details={
                    "type": expense_type,
                    "amount": amount,
                    "is_personal": is_personal,
                },
            )
            return True
        except AccountsValidationError:
            raise
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error adding expense: %s", exc, exc_info=True)
            return False

    def void(self, expense_id, user_id=None, reason="") -> bool:
        resolved_user_id = user_id or 1
        if not expense_id:
            raise AccountsValidationError("رقم المصروف غير صحيح")
        expense = self.repo.get_expense(expense_id)
        if not expense:
            raise AccountsValidationError("المصروف غير موجود")
        if bool(expense.get("is_voided")):
            raise AccountsValidationError("المصروف ملغى بالفعل")

        amount = float(expense.get("amount") or 0)
        store_id = int(expense.get("store_id") or 0)
        reason = reason or "إلغاء مصروف"
        description = f"قيد عكسي لإلغاء مصروف #{expense_id}: {reason}"

        try:
            self.repo.mark_expense_voided(expense_id, resolved_user_id, reason)
            self.repo.insert_treasury_entry(
                store_id=store_id,
                transaction_type="In",
                amount=amount,
                source_type=self.TREASURY_SOURCE_ADJUSTMENT,
                reference_id=expense_id,
                description=description,
                user_id=resolved_user_id,
            )
            self.repo.insert_ledger_entry(
                account_type="Expense",
                account_id=resolved_user_id,
                transaction_type="Credit",
                amount=amount,
                reference_type="Expense",
                reference_id=expense_id,
                description=description,
                user_id=resolved_user_id,
            )
            self.repo.commit()
            self.audit.log(
                resolved_user_id,
                VOID_EXPENSE_ACTION,
                entity_type="expense",
                entity_id=expense_id,
                success=True,
                details={"reason": reason},
            )
            return True
        except AccountsValidationError:
            raise
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error voiding expense: %s", exc, exc_info=True)
            return False

    def _validate_amount(self, amount: float) -> float:
        amount = round(float(amount or 0), 2)
        if amount <= 0:
            raise AccountsValidationError("المبلغ يجب أن يكون أكبر من صفر")
        return amount


class PromotionsUseCase:
    ALLOWED_PROMOTION_FIELDS = {
        "name",
        "promo_type",
        "value",
        "min_quantity",
        "buy_quantity",
        "apply_to",
        "apply_to_id",
        "start_date",
        "end_date",
        "funding_source",
        "supplier_id",
        "promotion_subtype",
        "second_item_discount_percent",
        "bundle_product_id",
        "bundle_price",
        "supplier_support_type",
        "supplier_support_value",
        "minimum_margin_percent",
        "is_active",
    }

    def __init__(self, repo: AccountsRepositoryPort):
        self.repo = repo

    def get_categories(self) -> List[Dict]:
        return self.repo.get_promotion_categories()

    def search_products(self, term="") -> List[Dict]:
        return self.repo.search_promotion_products(term)

    def list(self) -> List[Dict]:
        return self.repo.get_all_promotions()

    def add(self, **kwargs) -> bool:
        self.last_error = ""
        try:
            data = self._validate_promotion_payload(kwargs, require_all=True)
            self._ensure_promotion_keeps_minimum_margin(data)
            self.repo.insert_promotion(**data)
            self.repo.commit()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.repo.rollback()
            logger.error("Error adding promotion: %s", exc, exc_info=True)
            return False

    def update(self, promo_id, **kwargs) -> bool:
        self.last_error = ""
        if not promo_id:
            self.last_error = "رقم العرض غير صحيح."
            return False
        try:
            data = self._validate_promotion_payload(kwargs, require_all=False)
            if not data:
                return True
            if hasattr(self.repo, "get_promotion_by_id"):
                current = self.repo.get_promotion_by_id(promo_id) or {}
                self._ensure_promotion_keeps_minimum_margin({**current, **data})
            self.repo.update_promotion_record(promo_id, data)
            self.repo.commit()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.repo.rollback()
            logger.error(
                "Error updating promotion %s: %s", promo_id, exc, exc_info=True
            )
            return False

    def toggle(self, promo_id) -> bool:
        if not promo_id:
            return False
        try:
            self.repo.toggle_promotion_active(promo_id)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error(
                "Error toggling promotion %s: %s", promo_id, exc, exc_info=True
            )
            return False

    def delete(self, promo_id) -> bool:
        if not promo_id:
            return False
        try:
            self.repo.delete_promotion_record(promo_id)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error(
                "Error deleting promotion %s: %s", promo_id, exc, exc_info=True
            )
            return False

    def _validate_promotion_payload(self, data: Dict, require_all: bool) -> Dict:
        filtered = {
            key: value
            for key, value in (data or {}).items()
            if key in self.ALLOWED_PROMOTION_FIELDS
        }
        if require_all:
            required = {
                "name",
                "promo_type",
                "value",
                "min_quantity",
                "buy_quantity",
                "apply_to",
                "apply_to_id",
                "start_date",
                "end_date",
            }
            missing = required - filtered.keys()
            if missing:
                raise AccountsValidationError("بيانات العرض غير مكتملة")
        if "name" in filtered:
            filtered["name"] = (filtered["name"] or "").strip()
            if not filtered["name"]:
                raise AccountsValidationError("اسم العرض مطلوب")
        if "value" in filtered:
            filtered["value"] = round(float(filtered["value"] or 0), 2)
            if filtered["value"] <= 0:
                raise AccountsValidationError("قيمة العرض يجب أن تكون أكبر من صفر")
            if (
                filtered.get("promo_type")
                in {"percentage", "min_qty_discount", "second_item_percentage"}
                and filtered["value"] > 100
            ):
                raise AccountsValidationError("نسبة الخصم لا يمكن أن تتجاوز 100%")
        for quantity_field in ("min_quantity", "buy_quantity"):
            if quantity_field in filtered:
                filtered[quantity_field] = int(filtered[quantity_field] or 0)
                if filtered[quantity_field] < 0:
                    raise AccountsValidationError(
                        "كميات العرض لا يمكن أن تكون أقل من صفر"
                    )
        if "apply_to" in filtered and filtered["apply_to"] not in {
            "all",
            "category",
            "product",
        }:
            raise AccountsValidationError("نطاق تطبيق العرض غير صحيح")
        if "funding_source" in filtered:
            filtered["funding_source"] = (
                filtered["funding_source"] or "company"
            ).strip()
            if filtered["funding_source"] not in {"company", "supplier"}:
                raise AccountsValidationError("مصدر تمويل العرض غير صحيح")
        if "supplier_id" in filtered:
            filtered["supplier_id"] = int(filtered["supplier_id"] or 0) or None
        if "bundle_product_id" in filtered:
            filtered["bundle_product_id"] = (
                int(filtered["bundle_product_id"] or 0) or None
            )
        for money_field in ("bundle_price", "supplier_support_value"):
            if money_field in filtered:
                filtered[money_field] = round(float(filtered[money_field] or 0), 2)
                if filtered[money_field] < 0:
                    raise AccountsValidationError("قيم العرض لا يمكن أن تكون سالبة")
        if "second_item_discount_percent" in filtered:
            filtered["second_item_discount_percent"] = round(
                float(filtered["second_item_discount_percent"] or 0), 2
            )
            if (
                filtered["second_item_discount_percent"] < 0
                or filtered["second_item_discount_percent"] > 100
            ):
                raise AccountsValidationError("نسبة خصم القطعة الثانية غير صحيحة")
        if "minimum_margin_percent" in filtered:
            filtered["minimum_margin_percent"] = round(
                float(filtered["minimum_margin_percent"] or 5), 2
            )
            if (
                filtered["minimum_margin_percent"] < 0
                or filtered["minimum_margin_percent"] > 100
            ):
                raise AccountsValidationError("هامش الربح الأدنى غير صحيح")
        if "supplier_support_type" in filtered:
            filtered["supplier_support_type"] = (
                filtered["supplier_support_type"] or "claim_per_unit"
            ).strip()
            if filtered["supplier_support_type"] not in {
                "claim_per_unit",
                "claim_percent",
                "direct_per_unit",
                "direct_percent",
                "free_quantity",
            }:
                raise AccountsValidationError("نوع دعم المورد غير صحيح")
        if filtered.get("funding_source") == "supplier" and not filtered.get(
            "supplier_id"
        ):
            raise AccountsValidationError(
                "يجب اختيار المورد عند جعل العرض ممولًا من المورد"
            )
        return filtered

    def _ensure_promotion_keeps_minimum_margin(self, promo: Dict) -> None:
        if not hasattr(self.repo, "get_promotion_margin_products"):
            return
        apply_to = promo.get("apply_to")
        if apply_to not in {"all", "category", "product"}:
            return

        products = self.repo.get_promotion_margin_products(
            apply_to, promo.get("apply_to_id")
        )
        if not products:
            return

        minimum_margin = float(promo.get("minimum_margin_percent") or 5) / 100.0
        company_funded = (promo.get("funding_source") or "company") != "supplier"
        failing = []

        for product in products:
            sell_price = float(product.get("sell_price") or 0)
            buy_price = float(product.get("buy_price") or 0)
            if sell_price <= 0 or buy_price <= 0:
                continue

            scenario = self._promotion_margin_scenario(
                promo, sell_price, company_funded
            )
            if not scenario:
                continue

            received_total, cost_quantity = scenario
            minimum_total = buy_price * (1 + minimum_margin) * cost_quantity
            if received_total + 0.01 < minimum_total:
                failing.append(
                    {
                        "name": product.get("product_name")
                        or f"Product #{product.get('id')}",
                        "received": round(received_total, 2),
                        "minimum": round(minimum_total, 2),
                        "shortfall": round(minimum_total - received_total, 2),
                        "margin_percent": round(minimum_margin * 100, 2),
                    }
                )
                if len(failing) >= 5:
                    break

        if failing:
            details = "\n".join(
                f"- {item['name']}: بعد الخصم سيصل العائد إلى {item['received']:,.2f} ج.م، "
                f"بينما أقل عائد مسموح للحفاظ على هامش {item['margin_percent']:g}% هو {item['minimum']:,.2f} ج.م. "
                f"العجز {item['shortfall']:,.2f} ج.م."
                for item in failing
            )
            raise AccountsValidationError(
                "لا يمكن حفظ العرض لأن الخصم يجعل بيع بعض الأصناف أقل من هامش الربح الأدنى المحدد.\n"
                "السبب:\n"
                f"{details}"
            )

    def _promotion_margin_scenario(
        self, promo: Dict, sell_price: float, company_funded: bool
    ):
        promo_type = promo.get("promo_type")
        value = float(promo.get("value") or 0)
        min_quantity = max(int(promo.get("min_quantity") or 1), 1)
        buy_quantity = max(int(promo.get("buy_quantity") or 0), 0)

        if not company_funded:
            return None

        if promo_type in {"percentage", "min_qty_discount"}:
            quantity = min_quantity
            discount = sell_price * quantity * (value / 100.0)
            return sell_price * quantity - discount, quantity
        if promo_type == "fixed":
            quantity = min_quantity
            return max(sell_price * quantity - value, 0), quantity
        if promo_type == "fixed_per_unit":
            quantity = min_quantity
            return max(sell_price - value, 0) * quantity, quantity
        if promo_type == "buy_x_get_y":
            free_quantity = int(value or 0)
            if buy_quantity <= 0 or free_quantity <= 0:
                return None
            total_quantity = buy_quantity + free_quantity
            return sell_price * buy_quantity, total_quantity
        if promo_type == "second_item_percentage":
            quantity = 2
            return sell_price * 2 - (sell_price * (value / 100.0)), quantity
        if promo_type == "second_item_fixed":
            quantity = 2
            return sell_price * 2 - min(value, sell_price), quantity
        return None


class CreatePromotionsCatalogUseCase:
    def __init__(self, promotion_catalog_service: PromotionCatalogPort):
        self.promotion_catalog_service = promotion_catalog_service

    def execute(self, download_missing_images=True, refresh_images=True):
        try:
            return self.promotion_catalog_service.create_pdf(
                download_missing_images, refresh_images
            )
        except PromotionCatalogError:
            raise
        except Exception as exc:
            logger.error("Error creating promotions catalog: %s", exc, exc_info=True)
            return None


class DiscountCompaniesUseCase:
    def __init__(self, repo: AccountsRepositoryPort):
        self.repo = repo
        self.last_error = ""

    def list(self, active_only=False):
        companies = self.repo.get_discount_companies(active_only)
        for company in companies:
            company["product_ids"] = self.repo.get_discount_company_products(
                company["id"]
            )
        return companies

    def add(self, name, discount_percent, product_ids=None):
        self.last_error = ""
        try:
            name = str(name or "").strip()
            discount_percent = round(float(discount_percent or 0), 2)
            if not name:
                raise ValueError("اسم شركة الخصم مطلوب")
            if not 0 < discount_percent <= 100:
                raise ValueError("نسبة خصم الشركة يجب أن تكون بين 0 و100")
            self.repo.insert_discount_company(name, discount_percent, product_ids or [])
            self.repo.commit()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.repo.rollback()
            return False

    def update(
        self, company_id, name, discount_percent, is_active=True, product_ids=None
    ):
        self.last_error = ""
        try:
            if not company_id:
                raise ValueError("رقم شركة الخصم غير صحيح")
            name = str(name or "").strip()
            discount_percent = round(float(discount_percent or 0), 2)
            if not name:
                raise ValueError("اسم شركة الخصم مطلوب")
            if not 0 < discount_percent <= 100:
                raise ValueError("نسبة خصم الشركة يجب أن تكون بين 0 و100")
            self.repo.update_discount_company(
                company_id,
                {
                    "name": name,
                    "discount_percent": discount_percent,
                    "is_active": bool(is_active),
                },
                product_ids or [],
            )
            self.repo.commit()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.repo.rollback()
            return False

    def delete(self, company_id):
        try:
            self.repo.delete_discount_company(company_id)
            self.repo.commit()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.repo.rollback()
            return False

    def search_eligible_products(self, term="", min_margin_percent=0.0):
        """بحث عن المنتجات المؤهلة للخصم (التي يوجد فارق ربح بين سعر الشراء والبيع)."""
        return self.repo.search_discount_eligible_products(term, min_margin_percent)
