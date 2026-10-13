"""
Base Repository - المستودع الأساسي
جميع المستودعات ترث من هذا الكلاس
"""
import logging
from repositories.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)


class BaseRepository:
    """
    كلاس أساسي لجميع المستودعات.
    يوفر الوصول لقاعدة البيانات ودوال مشتركة.
    """

    def __init__(self):
        self.db = DatabaseConnection()

    def _fetch_one(self, query: str, params: tuple = None) -> dict:
        """جلب سجل واحد"""
        return self.db.fetch_one(query, params)

    def _fetch_all(self, query: str, params: tuple = None) -> list:
        """جلب جميع السجلات"""
        return self.db.fetch_all(query, params)

    def _execute(self, query: str, params: tuple = None):
        """تنفيذ استعلام"""
        return self.db.execute(query, params)

    def _execute_many(self, query: str, params_list: list):
        """تنفيذ مجموعة استعلامات"""
        return self.db.execute_many(query, params_list)

    def _commit(self):
        """حفظ التغييرات"""
        self.db.commit()

    def _rollback(self):
        """التراجع"""
        self.db.rollback()

    @property
    def _last_id(self) -> int:
        return self.db.last_insert_id

    @property
    def _affected_rows(self) -> int:
        return self.db.rows_affected
