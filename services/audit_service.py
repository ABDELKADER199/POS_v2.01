"""
Audit Service - واجهة آمنة لتسجيل العمليات الحساسة بدون تعطيل العملية الأساسية.
"""
import logging

from repositories.audit_repo import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self):
        self.repo = AuditRepository()
        self.repo.ensure_table()

    def log(self, user_id, action, entity_type="", entity_id=None,
            store_id=None, success=True, details=None):
        try:
            self.repo.record(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                store_id=store_id,
                success=success,
                details=details,
            )
        except Exception as e:
            logger.warning(f"Audit log skipped: {e}")
