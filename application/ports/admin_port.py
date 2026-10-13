from typing import Dict, List, Optional, Protocol, Tuple


class AdminRepositoryPort(Protocol):
    def ensure_accountant_role(self):
        ...

    def ensure_store_admin_columns(self):
        ...

    def ensure_authorized_devices_table(self):
        ...

    def get_all_users(self) -> List[Dict]:
        ...

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        ...

    def get_all_roles(self) -> List[Dict]:
        ...

    def get_all_stores(self, include_inactive: bool = False) -> List[Dict]:
        ...

    def get_user_activation_status_by_email(self, email: str) -> Optional[Dict]:
        ...

    def insert_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        role_id: int,
        store_id: Optional[int],
        phone: str = "",
    ) -> int:
        ...

    def reactivate_user(
        self,
        user_id: int,
        name: str,
        password_hash: str,
        role_id: int,
        store_id: Optional[int],
        phone: str = "",
    ) -> None:
        ...

    def update_user_record(
        self,
        user_id: int,
        name: str,
        email: str,
        role_id: int,
        store_id: Optional[int],
        phone: str = "",
        password_hash: Optional[str] = None,
    ) -> None:
        ...

    def soft_delete_user(self, user_id: int) -> None:
        ...

    def commit(self):
        ...

    def rollback(self):
        ...

    def get_drawers_report(self) -> List[Dict]:
        ...

    def get_drawer_summary(self, drawer_id: int) -> Dict:
        ...

    def insert_store(
        self,
        name: str,
        store_type: str,
        city: str = "",
        address: str = "",
        phone: str = "",
        manager: str = "",
        ip_start: Optional[str] = None,
        ip_end: Optional[str] = None,
        require_ip_check: bool = True,
        is_active: bool = True,
    ) -> int:
        ...

    def update_store_record(
        self,
        store_id: int,
        name: str,
        store_type: str,
        city: str = "",
        address: str = "",
        phone: str = "",
        manager: str = "",
        ip_start: Optional[str] = None,
        ip_end: Optional[str] = None,
        require_ip_check: bool = True,
        is_active: bool = True,
    ) -> None:
        ...

    def count_store_invoices(self, store_id: int) -> int:
        ...

    def count_store_stock_items(self, store_id: int) -> int:
        ...

    def delete_store_record(self, store_id: int) -> None:
        ...

    def get_authorized_devices(self) -> List[Dict]:
        ...

    def count_active_authorized_devices(self) -> int:
        ...

    def get_authorized_device_for_login(
        self,
        device_id: str,
        mac_address: str,
        user_id: int,
        store_id: int = None,
    ) -> Optional[Dict]:
        ...

    def mark_authorized_device_used(self, device_record_id: int) -> None:
        ...

    def upsert_authorized_device(
        self,
        device_id,
        device_name,
        mac,
        store_id,
        user_id,
        reg_by,
        notes: str = "",
    ) -> None:
        ...

    def update_device_status_record(self, device_id: int, is_active: bool) -> None:
        ...

    def delete_device_record(self, device_id: int) -> None:
        ...

    def get_sync_stats(self) -> Dict:
        ...
