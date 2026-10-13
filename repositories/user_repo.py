"""
User Repository - مستودع المستخدمين
"""
import logging
import hashlib
from typing import Optional, List
from repositories.base_repo import BaseRepository
from models.user import User

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """مستودع عمليات المستخدمين"""

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """التحقق من بيانات الدخول"""
        row = self._fetch_one("""
            SELECT u.id, u.name, u.email, u.password as password_hash, u.role_id, u.store_id, u.is_active,
                   r.role_name, s.store_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            LEFT JOIN stores s ON u.store_id = s.id
            WHERE u.email = %s AND u.is_active = 1
        """, (email,))

        if not row:
            logger.warning(f"No active user found with email: {email}")
            return None

        import bcrypt
        stored_hash = row.get('password_hash', '')
        
        try:
            # Handle if stored_hash is already bytes
            hash_bytes = stored_hash if isinstance(stored_hash, bytes) else stored_hash.encode('utf-8')
            
            is_valid = bcrypt.checkpw(password.encode('utf-8'), hash_bytes)
            logger.info(f"Password check for {email}: {is_valid}")
            
            if is_valid:
                return User.from_dict(row)
        except Exception as e:
            logger.error(f"Password check failed: {e}")
            
        return None

    def get_by_id(self, user_id: int) -> Optional[User]:
        """جلب مستخدم بالمعرف"""
        row = self._fetch_one("""
            SELECT u.*, s.store_name
            FROM users u
            LEFT JOIN stores s ON u.store_id = s.id
            WHERE u.id = %s
        """, (user_id,))
        return User.from_dict(row) if row else None

    def get_all(self, active_only: bool = True) -> List[User]:
        """جلب جميع المستخدمين"""
        query = "SELECT u.*, s.store_name FROM users u LEFT JOIN stores s ON u.store_id = s.id"
        if active_only:
            query += " WHERE u.is_active = TRUE"
        query += " ORDER BY u.full_name"
        rows = self._fetch_all(query)
        return [User.from_dict(r) for r in rows]
