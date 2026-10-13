import logging
from typing import Dict, List, Optional, Tuple

import bcrypt

from application.ports.admin_port import AdminRepositoryPort
from utils.permissions import ROLE_ADMIN, ROLE_OWNER, ROLE_DEVELOPER

logger = logging.getLogger(__name__)


class InitializeAdminUseCase:
    def __init__(self, repo: AdminRepositoryPort):
        self.repo = repo

    def execute(self):
        self.repo.ensure_accountant_role()
        self.repo.ensure_store_admin_columns()
        self.repo.ensure_authorized_devices_table()


class AdminUsersUseCase:
    def __init__(self, repo: AdminRepositoryPort):
        self.repo = repo

    def get_all(self) -> List[Dict]:
        return self.repo.get_all_users()

    def get_by_email(self, email: str) -> Optional[Dict]:
        return self.repo.get_user_by_email(email)

    def get_roles(self) -> List[Dict]:
        return self.repo.get_all_roles()

    def add(self, name, email, password, role_id, store_id, phone="") -> bool:
        if not name or not email or not password:
            return False
        try:
            role_id = int(role_id) if role_id is not None else None
            store_id = int(store_id) if store_id is not None else None

            if store_id is None or store_id <= 0:
                logger.warning(
                    "Rejected user creation without valid store_id: "
                    "email=%s role_id=%s store_id=%s",
                    email, role_id, store_id,
                )
                return False

            existing = self.repo.get_user_activation_status_by_email(email)

            if existing and existing.get("is_active"):
                return False

            password_hash = self._hash_password(password)

            if existing:
                self.repo.reactivate_user(
                    existing["id"], name, password_hash, role_id, store_id, phone
                )
            else:
                self.repo.insert_user(
                    name, email, password_hash, role_id, store_id, phone
                )

            self.repo.commit()
            return True

        except Exception as exc:
            self.repo.rollback()
            logger.error("Error adding admin user: %s", exc, exc_info=True)
            return False

    def update(self, user_id: int, name, email, role_id, store_id, phone="", password=None) -> bool:
        if not user_id or not name or not email:
            return False
        try:
            role_id = int(role_id) if role_id is not None else None
            store_id = int(store_id) if store_id is not None else None

            if store_id is None or store_id <= 0:
                return False

            password_hash = self._hash_password(password) if password else None
            self.repo.update_user_record(user_id, name, email, role_id, store_id, phone, password_hash)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error updating admin user: %s", exc, exc_info=True)
            return False

    def delete(self, user_id: int) -> bool:
        if not user_id:
            return False
        if int(user_id) == 1:
            return False
        if self._is_last_administrator(int(user_id)):
            return False
        try:
            self.repo.soft_delete_user(user_id)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error deleting admin user %s: %s", user_id, exc, exc_info=True)
            return False

    def _is_last_administrator(self, user_id: int) -> bool:
        try:
            active_users = self.repo.get_all_users() or []
            target = next((u for u in active_users if int(u.get("id", 0)) == user_id), None)
            if not target:
                return False
            admin_role_ids = {ROLE_ADMIN, ROLE_OWNER, ROLE_DEVELOPER}
            admin_role_names = {"admin", "owner", "developer"}
            is_admin = (
                target.get("role_id") in admin_role_ids
                or str(target.get("role_name") or "").lower() in admin_role_names
            )
            if not is_admin:
                return False
            other_admins = [
                u for u in active_users
                if int(u.get("id", 0)) != user_id
                and (
                    u.get("role_id") in admin_role_ids
                    or str(u.get("role_name") or "").lower() in admin_role_names
                )
            ]
            return len(other_admins) == 0
        except Exception:
            return False

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


class AdminStoresUseCase:
    def __init__(self, repo: AdminRepositoryPort):
        self.repo = repo

    def get_all(self, include_inactive: bool = False) -> List[Dict]:
        return self.repo.get_all_stores(include_inactive)

    def add(self, name, store_type, city="", address="", phone="", manager="", ip_start=None, ip_end=None, require_ip_check=True, is_active=True):
        if not name:
            return False
        try:
            store_id = self.repo.insert_store(name, store_type, city, address, phone, manager, ip_start, ip_end, require_ip_check, is_active)
            self.repo.commit()
            return store_id
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error adding store: %s", exc, exc_info=True)
            return False

    def update(self, store_id, name, store_type, city="", address="", phone="", manager="", ip_start=None, ip_end=None, require_ip_check=True, is_active=True) -> bool:
        if not store_id or not name:
            return False
        try:
            self.repo.update_store_record(store_id, name, store_type, city, address, phone, manager, ip_start, ip_end, require_ip_check, is_active)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error updating store %s: %s", store_id, exc, exc_info=True)
            return False

    def delete(self, store_id: int) -> Tuple[bool, str]:
        if not store_id:
            return False, "رقم الفرع غير صحيح"
        try:
            invoices_count = self.repo.count_store_invoices(store_id)
            if invoices_count > 0:
                return False, f"لا يمكن حذف الفرع لوجود {invoices_count} فاتورة مرتبطة به"
            stock_count = self.repo.count_store_stock_items(store_id)
            if stock_count > 0:
                return False, f"لا يمكن حذف الفرع لوجود {stock_count} صنف في المخزون"
            self.repo.delete_store_record(store_id)
            self.repo.commit()
            return True, "تم حذف الفرع بنجاح"
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error deleting store %s: %s", store_id, exc, exc_info=True)
            return False, "لا يمكن حذف الفرع لارتباطه بسجلات أخرى"


class AdminDrawersUseCase:
    def __init__(self, repo: AdminRepositoryPort):
        self.repo = repo

    def get_report(self) -> List[Dict]:
        return self.repo.get_drawers_report()

    def get_summary(self, drawer_id: int) -> Dict:
        return self.repo.get_drawer_summary(drawer_id)


class AdminDevicesUseCase:
    def __init__(self, repo: AdminRepositoryPort):
        self.repo = repo

    def get_all(self) -> List[Dict]:
        return self.repo.get_authorized_devices()

    def add(self, device_id, device_name, mac, store_id, user_id, reg_by, notes="") -> bool:
        if not device_id or not device_name or not mac:
            return False
        try:
            self.repo.upsert_authorized_device(device_id, device_name, mac, store_id, user_id, reg_by, notes)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error adding authorized device %s: %s", device_id, exc, exc_info=True)
            return False

    def update_status(self, device_id: int, is_active: bool) -> bool:
        if not device_id:
            return False
        try:
            self.repo.update_device_status_record(device_id, is_active)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error updating authorized device %s: %s", device_id, exc, exc_info=True)
            return False

    def delete(self, device_id: int) -> bool:
        if not device_id:
            return False
        try:
            self.repo.delete_device_record(device_id)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error deleting authorized device %s: %s", device_id, exc, exc_info=True)
            return False


class AdminSyncStatsUseCase:
    def __init__(self, repo: AdminRepositoryPort):
        self.repo = repo

    def execute(self) -> Dict:
        return self.repo.get_sync_stats()
