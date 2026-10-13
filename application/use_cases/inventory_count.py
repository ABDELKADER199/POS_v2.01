from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from application.ports.inventory_count_port import InventoryCountRepositoryPort
from utils.permissions import Permission, PermissionPolicy

logger = logging.getLogger(__name__)


class InventoryCountStoresUseCase:
    def __init__(self, repo: InventoryCountRepositoryPort):
        self.repo = repo

    def execute(self, user_info: dict) -> List[Dict]:
        stores = self.repo.get_stores()
        policy = PermissionPolicy(user_info)
        if policy.can_view_all_inventory():
            return stores
        scoped_store_id = policy.scoped_store_id()
        return [store for store in stores if store.get("id") == scoped_store_id]


class InventoryCountSessionsUseCase:
    def __init__(self, repo: InventoryCountRepositoryPort):
        self.repo = repo

    def execute(self, user_info: dict, store_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict]:
        policy = PermissionPolicy(user_info)
        scoped_store_id = store_id if policy.can_view_all_inventory() else policy.scoped_store_id(store_id)
        return self.repo.get_sessions(scoped_store_id, status)


class StartInventoryCountUseCase:
    def __init__(self, repo: InventoryCountRepositoryPort):
        self.repo = repo

    def execute(self, user_info: dict, store_id: int, count_type: str, notes: str = "") -> Tuple[bool, str, Optional[int]]:
        policy = PermissionPolicy(user_info)
        if not policy.can(Permission.COUNT_INVENTORY):
            return False, "لا تملك صلاحية إنشاء جرد مخزون.", None
        scoped_store_id = policy.scoped_store_id(store_id)
        if not scoped_store_id:
            return False, "يجب اختيار فرع للجرد.", None
        count_type = count_type if count_type in {"full", "partial", "cycle", "spot"} else "partial"
        try:
            count_number = f"CNT-{datetime.now():%Y%m%d%H%M%S}-{secrets.token_hex(2).upper()}"
            session_id = self.repo.create_session(
                count_number,
                int(scoped_store_id),
                count_type,
                int(user_info.get("id") or 1),
                notes,
            )
            inserted = 0
            if count_type == "full":
                inserted = self.repo.populate_full_session(session_id, int(scoped_store_id))
            self.repo.commit()
            suffix = f" وتم تحميل {inserted} صنف." if count_type == "full" else "."
            return True, f"تم فتح جلسة الجرد رقم {count_number}{suffix}", session_id
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error starting inventory count: %s", exc, exc_info=True)
            return False, f"فشل فتح جلسة الجرد: {exc}", None


class InventoryCountItemsUseCase:
    def __init__(self, repo: InventoryCountRepositoryPort):
        self.repo = repo

    def execute(self, session_id: int, search: str = "", limit: int = 300) -> List[Dict]:
        return self.repo.get_session_items(session_id, search, limit)


class InventoryCountProductSearchUseCase:
    def __init__(self, repo: InventoryCountRepositoryPort):
        self.repo = repo

    def execute(self, term: str, store_id: int) -> List[Dict]:
        term = str(term or "").strip()
        if len(term) < 2:
            return []
        return self.repo.search_products(term, store_id)


class AddInventoryCountItemUseCase:
    def __init__(self, repo: InventoryCountRepositoryPort):
        self.repo = repo

    def execute(self, user_info: dict, session_id: int, product_id: int) -> Tuple[bool, str]:
        try:
            session = self.repo.get_session(session_id)
            if not session:
                return False, "جلسة الجرد غير موجودة."
            if session.get("status") != "open":
                return False, "لا يمكن إضافة أصناف إلا إلى جلسة جرد مفتوحة."
            policy = PermissionPolicy(user_info)
            if not policy.can(Permission.COUNT_INVENTORY):
                return False, "لا تملك صلاحية تعديل الجرد."
            scoped_store_id = policy.scoped_store_id(session.get("store_id"))
            if scoped_store_id != session.get("store_id"):
                return False, "لا تملك صلاحية الجرد لهذا الفرع."
            self.repo.add_product_to_session(session_id, product_id, session["store_id"])
            self.repo.commit()
            return True, "تمت إضافة الصنف إلى الجرد."
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error adding inventory count item: %s", exc, exc_info=True)
            return False, f"فشل إضافة الصنف: {exc}"


class UpdateInventoryCountItemUseCase:
    def __init__(self, repo: InventoryCountRepositoryPort):
        self.repo = repo

    def execute(
        self,
        user_info: dict,
        session_id: int,
        product_id: int,
        actual_quantity: float,
        notes: str = "",
    ) -> Tuple[bool, str]:
        if actual_quantity < 0:
            return False, "الكمية الفعلية لا يمكن أن تكون سالبة."
        try:
            session = self.repo.get_session(session_id)
            if not session:
                return False, "جلسة الجرد غير موجودة."
            if session.get("status") != "open":
                return False, "لا يمكن تعديل جرد غير مفتوح."
            policy = PermissionPolicy(user_info)
            if not policy.can(Permission.COUNT_INVENTORY):
                return False, "لا تملك صلاحية تعديل الجرد."
            scoped_store_id = policy.scoped_store_id(session.get("store_id"))
            if scoped_store_id != session.get("store_id"):
                return False, "لا تملك صلاحية الجرد لهذا الفرع."
            self.repo.update_count_item(
                session_id,
                product_id,
                float(actual_quantity),
                notes,
                int(user_info.get("id") or 1),
            )
            self.repo.commit()
            return True, "تم حفظ كمية الجرد."
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error updating inventory count item: %s", exc, exc_info=True)
            return False, f"فشل حفظ كمية الجرد: {exc}"


class ApproveInventoryCountUseCase:
    def __init__(self, repo: InventoryCountRepositoryPort):
        self.repo = repo

    def execute(self, user_info: dict, session_id: int) -> Tuple[bool, str]:
        policy = PermissionPolicy(user_info)
        if not policy.can(Permission.APPROVE_INVENTORY_COUNT):
            return False, "لا تملك صلاحية اعتماد الجرد."
        try:
            session = self.repo.get_session(session_id)
            if not session:
                return False, "جلسة الجرد غير موجودة."
            if session.get("status") == "approved":
                return False, "تم اعتماد هذه الجلسة من قبل."
            if session.get("status") == "cancelled":
                return False, "لا يمكن اعتماد جلسة ملغاة."
            scoped_store_id = policy.scoped_store_id(session.get("store_id"))
            if scoped_store_id != session.get("store_id"):
                return False, "لا تملك صلاحية اعتماد جرد هذا الفرع."

            counted_items = self.repo.get_counted_items(session_id)
            if not counted_items:
                return False, "لا يمكن اعتماد جرد بدون أي كمية فعلية مسجلة."

            user_id = int(user_info.get("id") or 1)
            for item in counted_items:
                actual_quantity = float(item.get("actual_quantity") or 0)
                self.repo.set_inventory_quantity(
                    int(item["product_id"]),
                    int(session["store_id"]),
                    actual_quantity,
                    user_id,
                    f"تسوية جرد {session.get('count_number')}",
                )
                self.repo.insert_adjustment(session_id, int(item["id"]), item, int(session["store_id"]), user_id)
            self.repo.mark_session_approved(session_id, user_id)
            self.repo.commit()
            return True, f"تم اعتماد الجرد وتسوية {len(counted_items)} صنف."
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error approving inventory count: %s", exc, exc_info=True)
            return False, f"فشل اعتماد الجرد: {exc}"


class CancelInventoryCountUseCase:
    def __init__(self, repo: InventoryCountRepositoryPort):
        self.repo = repo

    def execute(self, user_info: dict, session_id: int) -> Tuple[bool, str]:
        if not PermissionPolicy(user_info).can(Permission.COUNT_INVENTORY):
            return False, "لا تملك صلاحية إلغاء الجرد."
        try:
            session = self.repo.get_session(session_id)
            if not session:
                return False, "جلسة الجرد غير موجودة."
            if session.get("status") == "approved":
                return False, "لا يمكن إلغاء جرد معتمد."
            scoped_store_id = PermissionPolicy(user_info).scoped_store_id(session.get("store_id"))
            if scoped_store_id != session.get("store_id"):
                return False, "لا تملك صلاحية إلغاء جرد هذا الفرع."
            self.repo.mark_session_cancelled(session_id)
            self.repo.commit()
            return True, "تم إلغاء جلسة الجرد."
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error cancelling inventory count: %s", exc, exc_info=True)
            return False, f"فشل إلغاء الجرد: {exc}"
