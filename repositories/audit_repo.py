"""
Audit Repository - سجل العمليات الحساسة.
"""
import json
import logging
from typing import Any

from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class AuditRepository(BaseRepository):
    def ensure_table(self):
        try:
            self._execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL,
                    action VARCHAR(100) NOT NULL,
                    entity_type VARCHAR(100) DEFAULT NULL,
                    entity_id VARCHAR(100) DEFAULT NULL,
                    store_id INT NULL,
                    success TINYINT(1) DEFAULT 1,
                    details TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_audit_action (action),
                    INDEX idx_audit_user (user_id),
                    INDEX idx_audit_store (store_id),
                    INDEX idx_audit_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            existing = {row["Field"] for row in self._fetch_all("SHOW COLUMNS FROM audit_logs")}
            required_columns = {
                "entity_type": "VARCHAR(100) DEFAULT NULL",
                "entity_id": "VARCHAR(100) DEFAULT NULL",
                "store_id": "INT NULL",
                "success": "TINYINT(1) DEFAULT 1",
                "details": "TEXT DEFAULT NULL",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            }
            for column, definition in required_columns.items():
                if column not in existing:
                    self._execute(f"ALTER TABLE audit_logs ADD COLUMN {column} {definition}")
            if "user_id" in existing:
                self._execute("ALTER TABLE audit_logs MODIFY user_id INT NULL")
            self._commit()
        except Exception as e:
            logger.error(f"Error ensuring audit table: {e}")

    def record(
        self,
        user_id: int | None,
        action: str,
        entity_type: str = "",
        entity_id: Any = None,
        store_id: int | None = None,
        success: bool = True,
        details: dict | str | None = None,
    ) -> bool:
        try:
            if isinstance(details, dict):
                details_text = json.dumps(details, ensure_ascii=False, default=str)
            else:
                details_text = details
            self._execute("""
                INSERT INTO audit_logs
                    (user_id, action, entity_type, entity_id, store_id, success, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                action,
                entity_type or None,
                str(entity_id) if entity_id is not None else None,
                store_id,
                1 if success else 0,
                details_text,
            ))
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error recording audit log: {e}")
            self._rollback()
            return False

    def fetch_logs(self, limit: int = 1000) -> list[dict]:
        """Fetch recent audit logs ordered by created_at DESC."""
        try:
            return self._fetch_all("""
                SELECT 
                    a.id, 
                    u.name as user_name, 
                    a.action, 
                    a.entity_type, 
                    a.entity_id, 
                    s.store_name, 
                    a.success, 
                    a.details, 
                    a.created_at
                FROM audit_logs a
                LEFT JOIN users u ON a.user_id = u.id
                LEFT JOIN stores s ON a.store_id = s.id
                ORDER BY a.created_at DESC
                LIMIT %s
            """, (limit,))
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            return []
