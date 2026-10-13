"""
Backup Repository - مستودع النسخ الاحتياطي
إدارة إعدادات النسخ الاحتياطي وسجل النسخ
"""
import logging
import os
import subprocess
from datetime import datetime, date
from typing import Dict, Optional, List, Tuple
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class BackupRepository(BaseRepository):
    """مستودع لإدارة النسخ الاحتياطي"""

    def __init__(self):
        super().__init__()
        self._ensure_table()

    def _ensure_table(self):
        """التأكد من وجود جدول سجل النسخ الاحتياطي"""
        try:
            self._execute("""
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    filepath VARCHAR(500) NOT NULL,
                    backup_type ENUM('manual', 'auto', 'scheduled') DEFAULT 'manual',
                    status ENUM('success', 'failed', 'in_progress') DEFAULT 'in_progress',
                    file_size BIGINT DEFAULT 0,
                    error_message TEXT,
                    created_by INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    INDEX idx_backup_date (created_at),
                    INDEX idx_backup_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            self._commit()
        except Exception as e:
            logger.error(f"Error ensuring backup_history table: {e}")

    def get_settings(self) -> Dict[str, str]:
        """Get all backup-related settings."""
        rows = self._fetch_all(
            """
            SELECT setting_key, setting_value
            FROM system_settings
            WHERE setting_key IN (
                'backup_path',
                'mysqldump_path',
                'auto_backup_enabled',
                'last_backup_date'
            )
            """
        )
        return {
            row['setting_key']: row['setting_value']
            for row in rows
        }

    def get_backup_dir(self) -> str:
        """جلب مجلد النسخ الاحتياطي"""
        settings = self.get_settings()
        backup_dir = settings.get('backup_path', 'backups')
        if not os.path.isabs(backup_dir):
            backup_dir = os.path.join(os.getcwd(), backup_dir)
        return backup_dir

    def set_backup_dir(self, path: str) -> bool:
        """تعيين مجلد النسخ الاحتياطي"""
        try:
            self.upsert_setting('backup_path', path)
            return True
        except Exception as e:
            logger.error(f"Error setting backup directory: {e}")
            return False

    def get_mysqldump_path(self) -> str:
        """جلب مسار mysqldump"""
        settings = self.get_settings()
        return settings.get('mysqldump_path', r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe")

    def set_mysqldump_path(self, path: str) -> bool:
        """تعيين مسار mysqldump"""
        try:
            self.upsert_setting('mysqldump_path', path)
            return True
        except Exception as e:
            logger.error(f"Error setting mysqldump path: {e}")
            return False

    def get_auto_backup_enabled(self) -> bool:
        """جلب حالة النسخ الاحتياطي التلقائي"""
        settings = self.get_settings()
        return settings.get('auto_backup_enabled', 'true').lower() == 'true'

    def set_auto_backup_enabled(self, enabled: bool) -> bool:
        """تعيين حالة النسخ الاحتياطي التلقائي"""
        try:
            self.upsert_setting('auto_backup_enabled', 'true' if enabled else 'false')
            return True
        except Exception as e:
            logger.error(f"Error setting auto backup enabled: {e}")
            return False

    def get_last_backup_date(self) -> Optional[str]:
        """جلب تاريخ آخر نسخة احتياطية"""
        settings = self.get_settings()
        return settings.get('last_backup_date')

    def set_last_backup_date(self, backup_date: str) -> bool:
        """تعيين تاريخ آخر نسخة احتياطية"""
        try:
            self.upsert_setting('last_backup_date', backup_date)
            return True
        except Exception as e:
            logger.error(f"Error setting last backup date: {e}")
            return False

    def upsert_setting(self, key: str, value: str) -> None:
        """إدراج أو تحديث إعداد"""
        self._execute("""
            INSERT INTO system_settings (setting_key, setting_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
        """, (key, str(value)))
        self._commit()

    def record_backup_start(self, filename: str, filepath: str, backup_type: str, created_by: int) -> int:
        """تسجيل بداية عملية نسخ احتياطي"""
        self._execute("""
            INSERT INTO backup_history (filename, filepath, backup_type, status, created_by)
            VALUES (%s, %s, %s, 'in_progress', %s)
        """, (filename, filepath, backup_type, created_by))
        self._commit()
        return self._last_id

    def record_backup_complete(self, backup_id: int, success: bool, file_size: int = 0, error_message: str = None) -> bool:
        """تسجيل اكتمال عملية النسخ الاحتياطي"""
        try:
            status = 'success' if success else 'failed'
            self._execute("""
                UPDATE backup_history 
                SET status = %s, file_size = %s, error_message = %s, completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, file_size, error_message, backup_id))
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error recording backup completion: {e}")
            return False

    def get_backup_history(self, limit: int = 50) -> List[Dict]:
        """جلب سجل النسخ الاحتياطية"""
        return self._fetch_all("""
            SELECT bh.*, u.name as created_by_name
            FROM backup_history bh
            LEFT JOIN users u ON bh.created_by = u.id
            ORDER BY bh.created_at DESC
            LIMIT %s
        """, (limit,))

    def get_last_successful_backup(self) -> Optional[Dict]:
        """جلب آخر نسخة احتياطية ناجحة"""
        return self._fetch_one("""
            SELECT * FROM backup_history 
            WHERE status = 'success' 
            ORDER BY completed_at DESC 
            LIMIT 1
        """)

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """تنظيف النسخ الاحتياطية القديمة (حذف الملفات والسجلات)"""
        try:
            # جلب السجلات القديمة
            old_backups = self._fetch_all("""
                SELECT filepath FROM backup_history 
                WHERE status = 'success' AND created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (keep_days,))
            
            deleted_files = 0
            for backup in old_backups:
                filepath = backup.get('filepath')
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        deleted_files += 1
                    except Exception as e:
                        logger.warning(f"Could not delete backup file {filepath}: {e}")
            
            # حذف السجلات من قاعدة البيانات
            self._execute("""
                DELETE FROM backup_history 
                WHERE status = 'success' AND created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (keep_days,))
            self._commit()
            
            return deleted_files
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
            return 0


def get_backup_repository() -> BackupRepository:
    """الحصول على نسخة وحيدة من مستودع النسخ الاحتياطي"""
    return BackupRepository()