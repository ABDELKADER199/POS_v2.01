"""
Sync Queue Repository - مستودع طابور المزامنة
إدارة عمليات المزامنة المعلقة بين القاعدة المحلية والسحابية
"""
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class SyncQueueRepository(BaseRepository):
    """مستودع لإدارة طابور المزامنة (Offline-first sync queue)"""

    def __init__(self):
        super().__init__()
        self._ensure_table()
        self._refresh_schema()

    def _refresh_schema(self):
        try:
            rows = self._fetch_all("SHOW COLUMNS FROM sync_queue")
            self._queue_columns = {row.get("Field") for row in rows or []}
        except Exception:
            self._queue_columns = set()

    @property
    def _uses_current_schema(self) -> bool:
        return "operation" in self._queue_columns and "payload" in self._queue_columns

    def _ensure_table(self):
        """التأكد من وجود جدول sync_queue مع الفهارس اللازمة"""
        try:
            # إنشاء الجدول إذا لم يكن موجوداً
            self._execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_name VARCHAR(100) NOT NULL,
                    record_id VARCHAR(100) NOT NULL,
                    action_type VARCHAR(50) NOT NULL,
                    data_json LONGTEXT NOT NULL,
                    status ENUM('pending', 'synced', 'failed') DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP NULL,
                    error_message TEXT,
                    retry_count INT DEFAULT 0,
                    INDEX idx_sync_status (status),
                    INDEX idx_sync_table (table_name),
                    INDEX idx_sync_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            self._commit()

            # إضافة عمود retry_count إذا لم يكن موجوداً (للتوافق مع قواعد بيانات قديمة)
            self._execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'sync_queue' AND COLUMN_NAME = 'retry_count'
            """)
            if not self.db.cursor.fetchone():
                self._execute("ALTER TABLE sync_queue ADD COLUMN retry_count INT DEFAULT 0")
                self._commit()
                logger.info("✅ Added retry_count column to sync_queue")

        except Exception as e:
            logger.error(f"Error ensuring sync_queue table: {e}")

    def enqueue(self, table_name: str, record_id: str, action_type: str, data: Dict[str, Any]) -> bool:
        """
        إضافة عملية إلى طابور المزامنة
        
        Args:
            table_name: اسم الجدول المتأثر
            record_id: معرف السجل (يمكن أن يكون composite key)
            action_type: نوع العملية (INSERT, UPDATE, DELETE)
            data: بيانات السجل كاملة كقاموس
        """
        try:
            # تنظيف البيانات من الحقول غير القابلة للتسلسل
            clean_data = self._clean_data_for_sync(data)
            
            if self._uses_current_schema:
                query = """
                    INSERT INTO sync_queue (table_name, record_id, operation, payload)
                    VALUES (%s, %s, %s, %s)
                """
            else:
                query = """
                    INSERT INTO sync_queue (table_name, record_id, action_type, data_json)
                    VALUES (%s, %s, %s, %s)
                """
            self._execute(query, (
                table_name,
                str(record_id),
                action_type.lower() if self._uses_current_schema else action_type.upper(),
                json.dumps(clean_data, ensure_ascii=False, default=str)
            ))
            self._commit()
            logger.debug(f"Enqueued sync: {table_name}.{record_id} [{action_type}]")
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue sync for {table_name}.{record_id}: {e}")
            self._rollback()
            return False

    def _clean_data_for_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """تنظيف البيانات من الحقول المساعدة غير الموجودة في قاعدة البيانات السحابية"""
        helper_cols = {
            'invoice_number', 'product_code', 'category_name', 
            'supplier_name', 'customer_name', 'store_name',
            'cashier_name', 'user_name', 'role_name'
        }
        return {k: v for k, v in data.items() if k not in helper_cols}

    def get_pending(self, limit: int = 1000, max_retries: int = 3) -> List[Dict]:
        """
        جلب العمليات المعلقة للمزامنة
        
        Args:
            limit: الحد الأقصى للعدد
            max_retries: استبعاد العمليات التي فشلت أكثر من هذا العدد
        """
        try:
            query = """
                SELECT * FROM sync_queue
                WHERE status = 'pending' AND (retry_count IS NULL OR retry_count < %s)
                ORDER BY 
                    CASE table_name
                        WHEN 'roles' THEN 1 WHEN 'stores' THEN 1
                        WHEN 'users' THEN 2
                        WHEN 'categories' THEN 3 WHEN 'suppliers' THEN 3 WHEN 'customers' THEN 3
                        WHEN 'products' THEN 4
                        WHEN 'product_inventory' THEN 5 WHEN 'price_history' THEN 5 WHEN 'promotions' THEN 5
                        WHEN 'invoices' THEN 6 WHEN 'purchase_invoices' THEN 6 WHEN 'orders' THEN 6 
                        WHEN 'warehouse_transfers' THEN 6 WHEN 'sales_returns' THEN 6
                        WHEN 'invoice_items' THEN 7 WHEN 'purchase_items' THEN 7 
                        WHEN 'order_items' THEN 7 WHEN 'transfer_items' THEN 7 WHEN 'return_items' THEN 7
                        WHEN 'expenses' THEN 8 WHEN 'treasury' THEN 8 WHEN 'financial_ledger' THEN 8
                        WHEN 'drawer_logs' THEN 8 WHEN 'drawer_closing_details' THEN 8
                        WHEN 'authorized_devices' THEN 9 WHEN 'system_settings' THEN 9 WHEN 'audit_logs' THEN 9
                        ELSE 10
                    END,
                    id ASC
                LIMIT %s
            """
            rows = self._fetch_all(query, (max_retries, limit))
            if self._uses_current_schema:
                for row in rows or []:
                    row.setdefault("action_type", row.get("operation"))
                    row.setdefault("data_json", row.get("payload"))
            return rows
        except Exception as e:
            logger.error(f"Error getting pending syncs: {e}")
            return []

    def mark_synced(self, sync_id: int) -> bool:
        """تمييز عملية كمتمة بنجاح"""
        try:
            if self._uses_current_schema:
                query = "UPDATE sync_queue SET status = 'completed', updated_at = NOW() WHERE id = %s"
            else:
                query = "UPDATE sync_queue SET status = 'synced', synced_at = NOW() WHERE id = %s"
            self._execute(query, (sync_id,))
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error marking sync {sync_id} as synced: {e}")
            self._rollback()
            return False

    def mark_failed(self, sync_id: int, error_message: str = None) -> bool:
        """تسجيل فشل عملية المزامنة مع زيادة عداد المحاولات"""
        try:
            query = """
                UPDATE sync_queue 
                SET retry_count = COALESCE(retry_count, 0) + 1,
                    error_message = %s,
                    status = CASE 
                        WHEN COALESCE(retry_count, 0) + 1 >= 3 THEN 'failed'
                        ELSE 'pending'
                    END
                WHERE id = %s
            """
            self._execute(query, (str(error_message)[:500] if error_message else None, sync_id))
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error marking sync {sync_id} as failed: {e}")
            self._rollback()
            return False

    def get_stats(self) -> Dict[str, int]:
        """إحصائيات طابور المزامنة"""
        try:
            query = """
                SELECT 
                    status,
                    COUNT(*) as count
                FROM sync_queue
                GROUP BY status
            """
            results = self._fetch_all(query)
            stats = {'pending': 0, 'synced': 0, 'failed': 0, 'total': 0}
            for row in results:
                stats[row['status']] = row['count']
                stats['total'] += row['count']
            return stats
        except Exception as e:
            logger.error(f"Error getting sync stats: {e}")
            return {'pending': 0, 'synced': 0, 'failed': 0, 'total': 0}

    def clear_synced(self, older_than_days: int = 30) -> int:
        """حذف العمليات المكتملة القديمة لتوفير المساحة"""
        try:
            if self._uses_current_schema:
                query = "DELETE FROM sync_queue WHERE status = 'completed' AND updated_at < DATE_SUB(NOW(), INTERVAL %s DAY)"
            else:
                query = """
                    DELETE FROM sync_queue
                    WHERE status = 'synced' AND synced_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """
            self._execute(query, (older_than_days,))
            self._commit()
            return self._affected_rows
        except Exception as e:
            logger.error(f"Error clearing old synced records: {e}")
            self._rollback()
            return 0

    def requeue_failed(self, max_retries: int = 3) -> int:
        """إعادة جدولة العمليات الفاشلة للمحاولة مرة أخرى"""
        try:
            query = """
                UPDATE sync_queue 
                SET status = 'pending', retry_count = 0, error_message = NULL
                WHERE status = 'failed' AND retry_count < %s
            """
            self._execute(query, (max_retries,))
            self._commit()
            return self._affected_rows
        except Exception as e:
            logger.error(f"Error requeueing failed syncs: {e}")
            self._rollback()
            return 0

    def bulk_enqueue(self, records: List[Dict[str, Any]]) -> int:
        """
        إضافة متعددة عمليات دفعة واحدة (للرفع الشامل)
        
        Args:
            records: قائمة بالقواميس تحتوي على table_name, record_id, action_type, data
        """
        if not records:
            return 0
            
        try:
            if self._uses_current_schema:
                query = """
                    INSERT INTO sync_queue (table_name, record_id, operation, payload)
                    VALUES (%s, %s, %s, %s)
                """
            else:
                query = """
                    INSERT INTO sync_queue (table_name, record_id, action_type, data_json)
                    VALUES (%s, %s, %s, %s)
                """
            params_list = []
            for rec in records:
                clean_data = self._clean_data_for_sync(rec.get('data', {}))
                params_list.append((
                    rec['table_name'],
                    str(rec['record_id']),
                    rec['action_type'].lower() if self._uses_current_schema else rec['action_type'].upper(),
                    json.dumps(clean_data, ensure_ascii=False, default=str)
                ))
            
            self._execute_many(query, params_list)
            self._commit()
            logger.info(f"Bulk enqueued {len(records)} sync operations")
            return len(records)
        except Exception as e:
            logger.error(f"Error bulk enqueueing syncs: {e}")
            self._rollback()
            return 0


# Singleton instance
_sync_queue_repo = None

def get_sync_queue_repo() -> SyncQueueRepository:
    """الحصول على نسخة وحيدة من مستودع طابور المزامنة"""
    global _sync_queue_repo
    if _sync_queue_repo is None:
        _sync_queue_repo = SyncQueueRepository()
    return _sync_queue_repo
