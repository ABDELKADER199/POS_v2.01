"""
Settings Repository - مستودع الإعدادات
"""
import logging
from typing import Dict
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class SettingsRepository(BaseRepository):
    """مستودع إعدادات النظام"""

    def commit(self) -> None:
        self._commit()

    def rollback(self) -> None:
        self._rollback()

    def get_all(self) -> Dict[str, str]:
        """جلب جميع الإعدادات"""
        try:
            rows = self._fetch_all("SELECT setting_key, setting_value FROM system_settings")
            return {row['setting_key']: row['setting_value'] for row in rows}
        except Exception:
            return {}

    def get(self, key: str, default: str = '') -> str:
        """جلب إعداد محدد"""
        row = self._fetch_one(
            "SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,)
        )
        return row['setting_value'] if row else default

    def set(self, key: str, value: str) -> bool:
        """تحديث أو إنشاء إعداد"""
        try:
            self.upsert_setting(key, value)
            self.commit()
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Error saving setting {key}: {e}")
            return False

    def update_many(self, settings: Dict[str, str]) -> bool:
        """تحديث مجموعة إعدادات"""
        try:
            self.upsert_settings(settings)
            self.commit()
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Error updating settings: {e}")
            return False

    def upsert_setting(self, key: str, value: str) -> None:
        self._execute("""
            INSERT INTO system_settings (setting_key, setting_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
        """, (key, str(value)))

    def upsert_settings(self, settings: Dict[str, str]) -> None:
        for key, val in settings.items():
            self.upsert_setting(key, val)
