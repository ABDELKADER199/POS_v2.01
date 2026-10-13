import logging
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from application.ports.transfers_port import TransfersRepositoryPort
from utils.permissions import PermissionPolicy

logger = logging.getLogger(__name__)


class TransferStoresUseCase:
    def __init__(self, repo: TransfersRepositoryPort):
        self.repo = repo

    def execute(self) -> List[Dict]:
        return self.repo.get_stores()


class TransferProductSearchUseCase:
    def __init__(self, repo: TransfersRepositoryPort):
        self.repo = repo

    def execute(self, term: str, store_id: Optional[int] = None) -> List[Dict]:
        normalized_term = str(term or "").strip()
        if len(normalized_term) < 2:
            return []
        return self.repo.search_products(normalized_term, store_id=store_id)


class ListTransfersUseCase:
    def __init__(self, repo: TransfersRepositoryPort):
        self.repo = repo

    def execute(self, user_info: dict, status: Optional[str] = None) -> List[Dict]:
        store_id = None
        if not PermissionPolicy(user_info).can_view_all_inventory():
            store_id = user_info.get("store_id")
        return self.repo.get_transfers(store_id=store_id, status=status)


class CreateTransferUseCase:
    def __init__(self, repo: TransfersRepositoryPort):
        self.repo = repo

    def execute(
        self,
        product_id: int,
        from_store_id: int,
        to_store_id: int,
        quantity: int,
        user_id: int,
        notes: str = "",
    ) -> Tuple[bool, str]:
        if from_store_id == to_store_id:
            return False, "لا يمكن التحويل إلى نفس الفرع."
        if quantity <= 0:
            return False, "الكمية يجب أن تكون أكبر من صفر."

        try:
            available = self.repo.get_stock(product_id, from_store_id)
            if available < quantity:
                return False, f"الكمية المتاحة ({available}) أقل من المطلوب ({quantity})."

            transfer_number = f"TRF-{datetime.now():%Y%m%d%H%M%S}-{secrets.token_hex(2).upper()}"
            transfer_id = self.repo.create_transfer_header(
                transfer_number,
                from_store_id,
                to_store_id,
                user_id,
                notes,
            )
            self.repo.insert_transfer_item(transfer_id, product_id, quantity, notes)
            self.repo.decrease_inventory(product_id, from_store_id, quantity)
            self.repo.commit()
            return True, f"تم إنشاء التحويل رقم {transfer_number}."
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error creating transfer: %s", exc, exc_info=True)
            return False, f"فشل إنشاء التحويل: {exc}"


class ReceiveTransferUseCase:
    def __init__(self, repo: TransfersRepositoryPort):
        self.repo = repo

    def execute(self, transfer_id: int, user_info: dict) -> Tuple[bool, str]:
        try:
            transfer = self.repo.get_transfer_for_receiving(transfer_id)
            if not transfer:
                return False, "التحويل غير موجود."
            if transfer["status"] == "Received":
                return False, "تم استلام هذا التحويل من قبل."
            if transfer["status"] == "Cancelled":
                return False, "لا يمكن استلام تحويل ملغي."

            self.repo.increase_inventory(
                transfer["product_id"],
                transfer["to_store_id"],
                transfer["quantity_sent"],
            )
            self.repo.mark_transfer_received(transfer_id, user_info.get("id", 1))
            self.repo.commit()
            return True, "تم استلام التحويل وتحديث مخزون الفرع."
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error receiving transfer: %s", exc, exc_info=True)
            return False, f"فشل استلام التحويل: {exc}"


class CancelTransferUseCase:
    def __init__(self, repo: TransfersRepositoryPort):
        self.repo = repo

    def execute(self, transfer_id: int) -> Tuple[bool, str]:
        try:
            transfer = self.repo.get_transfer_for_cancellation(transfer_id)
            if not transfer:
                return False, "التحويل غير موجود."
            if transfer["status"] == "Received":
                return False, "لا يمكن إلغاء تحويل تم استلامه."
            if transfer["status"] == "Cancelled":
                return False, "التحويل ملغي بالفعل."

            self.repo.increase_inventory(
                transfer["product_id"],
                transfer["from_store_id"],
                transfer["quantity_sent"],
            )
            self.repo.mark_transfer_cancelled(transfer_id)
            self.repo.commit()
            return True, "تم إلغاء التحويل وإرجاع الكمية للمصدر."
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error cancelling transfer: %s", exc, exc_info=True)
            return False, f"فشل إلغاء التحويل: {exc}"
