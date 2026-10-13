"""
Admin Repository - مستودع لوحة الإدارة.
يحافظ على كل استعلامات الإدارة خارج طبقة الواجهة.
"""
import logging
from typing import Dict, List, Optional

import bcrypt

from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class AdminRepository(BaseRepository):
    """مستودع عمليات الإدارة."""

    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def ensure_accountant_role(self):
        """التأكد من وجود دور المحاسب ضمن الأدوار الأساسية."""
        try:
            self._execute("""
                INSERT INTO roles (id, role_name, description)
                VALUES (6, 'accountant', 'محاسب - الحسابات والمالية والمشتريات والتقارير المالية')
                ON DUPLICATE KEY UPDATE
                    role_name = VALUES(role_name),
                    description = VALUES(description)
            """)
            self._execute("""
                INSERT INTO roles (id, role_name, description)
                VALUES (7, 'owner', 'Owner - full system permissions')
                ON DUPLICATE KEY UPDATE
                    role_name = VALUES(role_name),
                    description = VALUES(description)
            """)
            self._commit()
        except Exception as e:
            logger.error(f"Error ensuring accountant role: {e}")

    def ensure_store_admin_columns(self):
        """التأكد من وجود أعمدة إدارة الفروع القادمة من التطبيق القديم."""
        columns = {
            "ip_range_start": "VARCHAR(45) DEFAULT NULL",
            "ip_range_end": "VARCHAR(45) DEFAULT NULL",
            "require_ip_check": "TINYINT(1) DEFAULT 1",
        }
        try:
            existing = {row["Field"] for row in self._fetch_all("SHOW COLUMNS FROM stores")}
            for column, definition in columns.items():
                if column not in existing:
                    self._execute(f"ALTER TABLE stores ADD COLUMN {column} {definition}")
            self._commit()
        except Exception as e:
            logger.error(f"Error ensuring stores admin columns: {e}")

    def ensure_authorized_devices_table(self):
        """التأكد من وجود جدول الأجهزة المصرح بها."""
        try:
            self._execute("""
                CREATE TABLE IF NOT EXISTS authorized_devices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL,
                    device_name VARCHAR(255) DEFAULT NULL,
                    mac_address VARCHAR(100) DEFAULT NULL,
                    store_id INT DEFAULT NULL,
                    user_id INT DEFAULT NULL,
                    is_active TINYINT(1) DEFAULT 1,
                    registered_by INT DEFAULT NULL,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP NULL DEFAULT NULL,
                    notes TEXT DEFAULT NULL,
                    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                    UNIQUE KEY unique_device (device_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            self._commit()
        except Exception as e:
            logger.error(f"Error creating authorized_devices table: {e}")

    def get_all_users(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT u.id, u.name, u.email, u.phone, u.is_active,
                   r.role_name, u.role_id, s.store_name, u.store_id
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            LEFT JOIN stores s ON u.store_id = s.id
            WHERE u.is_active = TRUE
            ORDER BY u.id
        """)

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        return self._fetch_one("""
            SELECT u.*, r.role_name, s.store_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            LEFT JOIN stores s ON u.store_id = s.id
            WHERE u.email = %s
        """, (email,))

    def get_all_roles(self) -> List[Dict]:
        return self._fetch_all("SELECT id, role_name FROM roles ORDER BY id")

    def get_user_activation_status_by_email(self, email: str) -> Optional[Dict]:
        return self._fetch_one("SELECT id, is_active FROM users WHERE email = %s", (email,))

    def insert_user(self, name: str, email: str, password_hash: str,
                    role_id: int, store_id: int, phone: str = "") -> int:
        self._execute("""
            INSERT INTO users (name, email, password, role_id, store_id, phone)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, email, password_hash, role_id, store_id, phone))
        return self._last_id

    def reactivate_user(self, user_id: int, name: str, password_hash: str,
                        role_id: int, store_id: int, phone: str = "") -> None:
        self._execute("""
            UPDATE users
            SET name=%s, password=%s, role_id=%s, store_id=%s, phone=%s, is_active=TRUE
            WHERE id=%s
        """, (name, password_hash, role_id, store_id, phone, user_id))

    def update_user_record(self, user_id: int, name: str, email: str,
                           role_id: int, store_id: int, phone: str = "",
                           password_hash: str = None) -> None:
        if password_hash:
            self._execute("""
                UPDATE users
                SET name=%s, email=%s, password=%s, role_id=%s, store_id=%s, phone=%s, is_active=TRUE
                WHERE id=%s
            """, (name, email, password_hash, role_id, store_id, phone, user_id))
        else:
            self._execute("""
                UPDATE users
                SET name=%s, email=%s, role_id=%s, store_id=%s, phone=%s, is_active=TRUE
                WHERE id=%s
            """, (name, email, role_id, store_id, phone, user_id))

    def soft_delete_user(self, user_id: int) -> None:
        self._execute("UPDATE users SET is_active = FALSE WHERE id = %s", (user_id,))

    def get_all_stores(self, include_inactive: bool = False) -> List[Dict]:
        query = """
            SELECT id, store_name, store_type, city, address, phone, manager_name,
                   is_active, ip_range_start, ip_range_end, require_ip_check
            FROM stores
        """
        if not include_inactive:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY id"
        return self._fetch_all(query)

    def get_drawers_report(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT
                dl.id,
                dl.status,
                dl.opening_date,
                dl.closing_date,
                dl.opening_balance,
                dl.closing_balance,
                u.name as cashier_name,
                s.store_name,
                COALESCE((
                    SELECT SUM(total_amount)
                    FROM invoices
                    WHERE drawer_id = dl.id AND status = 'Completed'
                ), 0) as total_sales,
                COALESCE((
                    SELECT SUM(cash_amount)
                    FROM invoices
                    WHERE drawer_id = dl.id AND status = 'Completed'
                ), 0) as cash_sales,
                COALESCE((
                    SELECT SUM(card_amount)
                    FROM invoices
                    WHERE drawer_id = dl.id AND status = 'Completed'
                ), 0) as card_sales,
                COALESCE((
                    SELECT SUM(sr.total_amount)
                    FROM sales_returns sr
                    JOIN invoices i ON sr.original_invoice_id = i.id
                    WHERE sr.drawer_id = dl.id AND i.cash_amount > 0
                ), 0) as cash_returns
            FROM drawer_logs dl
            JOIN users u ON dl.cashier_id = u.id
            JOIN stores s ON dl.store_id = s.id
            ORDER BY dl.opening_date DESC
            LIMIT 100
        """)

    def get_drawer_summary(self, drawer_id: int) -> Dict:
        drawer = self._fetch_one("""
            SELECT dl.*, u.name as cashier_name, s.store_name
            FROM drawer_logs dl
            LEFT JOIN users u ON dl.cashier_id = u.id
            LEFT JOIN stores s ON dl.store_id = s.id
            WHERE dl.id = %s
        """, (drawer_id,))
        if not drawer:
            return {}

        sales = self._fetch_one("""
            SELECT COUNT(*) as count,
                   COALESCE(SUM(total_amount), 0) as total_sales,
                   COALESCE(SUM(cash_amount), 0) as total_cash,
                   COALESCE(SUM(card_amount), 0) as total_card
            FROM invoices
            WHERE drawer_id = %s AND status = 'Completed'
        """, (drawer_id,)) or {}

        returns = self._fetch_one("""
            SELECT COALESCE(SUM(total_amount), 0) as total_returns,
                   COUNT(*) as count
            FROM sales_returns
            WHERE drawer_id = %s
        """, (drawer_id,)) or {}

        cash_returns = self._fetch_one("""
            SELECT COALESCE(SUM(sr.total_amount), 0) as cash_returns
            FROM sales_returns sr
            JOIN invoices i ON sr.original_invoice_id = i.id
            WHERE sr.drawer_id = %s AND i.cash_amount > 0
        """, (drawer_id,)) or {}

        details = self._fetch_all(
            "SELECT * FROM drawer_closing_details WHERE drawer_log_id = %s",
            (drawer_id,),
        )

        actual_visa = 0.0
        for detail in details:
            if detail.get("denomination") == "Visa":
                actual_visa = float(detail.get("total_amount") or 0)

        opening_balance = float(drawer.get("opening_balance") or 0)
        total_sales = float(sales.get("total_sales") or 0)
        total_cash_sales = float(sales.get("total_cash") or 0)
        total_card_sales = float(sales.get("total_card") or 0)
        total_returns = float(returns.get("total_returns") or 0)
        total_cash_returns = float(cash_returns.get("cash_returns") or 0)
        actual_cash = float(drawer.get("closing_balance") or 0)
        expected_cash = opening_balance + total_cash_sales - total_cash_returns

        return {
            "drawer_id": drawer_id,
            "opened_at": drawer.get("opening_date"),
            "closed_at": drawer.get("closing_date"),
            "cashier_name": drawer.get("cashier_name") or "غير معروف",
            "store_name": drawer.get("store_name") or "غير معروف",
            "opening_balance": opening_balance,
            "total_sales": total_sales,
            "total_cash_sales": total_cash_sales,
            "total_card_sales": total_card_sales,
            "total_deferred": total_sales - total_cash_sales - total_card_sales,
            "sales_count": sales.get("count") or 0,
            "total_returns": total_returns,
            "total_cash_returns": total_cash_returns,
            "returns_count": returns.get("count") or 0,
            "expected_cash": expected_cash,
            "actual_cash": actual_cash,
            "actual_visa": actual_visa,
            "difference": actual_cash - expected_cash,
            "visa_difference": actual_visa - total_card_sales,
            "denominations": details,
        }

    def insert_store(self, name: str, store_type: str, city: str = "", address: str = "",
                     phone: str = "", manager: str = "", ip_start: str = None,
                     ip_end: str = None, require_ip_check: bool = True,
                     is_active: bool = True) -> int:
        self._execute("""
            INSERT INTO stores (
                store_name, store_type, city, address, phone, manager_name,
                ip_range_start, ip_range_end, require_ip_check, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, store_type, city, address, phone, manager,
              ip_start or None, ip_end or None, require_ip_check, is_active))
        return self._last_id

    def update_store_record(self, store_id: int, name: str, store_type: str, city: str = "",
                            address: str = "", phone: str = "", manager: str = "",
                            ip_start: str = None, ip_end: str = None,
                            require_ip_check: bool = True,
                            is_active: bool = True) -> None:
        self._execute("""
            UPDATE stores
            SET store_name=%s, store_type=%s, city=%s, address=%s, phone=%s,
                manager_name=%s, ip_range_start=%s, ip_range_end=%s,
                require_ip_check=%s, is_active=%s
            WHERE id=%s
        """, (name, store_type, city, address, phone, manager,
              ip_start or None, ip_end or None, require_ip_check,
              is_active, store_id))

    def count_store_invoices(self, store_id: int) -> int:
        row = self._fetch_one(
            "SELECT COUNT(*) as count FROM invoices WHERE store_id = %s",
            (store_id,),
        )
        return int(row.get("count") or 0) if row else 0

    def count_store_stock_items(self, store_id: int) -> int:
        row = self._fetch_one("""
            SELECT COUNT(*) as count
            FROM product_inventory
            WHERE store_id = %s AND quantity_in_stock > 0
        """, (store_id,))
        return int(row.get("count") or 0) if row else 0

    def delete_store_record(self, store_id: int) -> None:
        self._execute("DELETE FROM stores WHERE id = %s", (store_id,))

    def get_authorized_devices(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT ad.*, s.store_name, u.name as user_name,
                   ru.name as registered_by_name
            FROM authorized_devices ad
            LEFT JOIN stores s ON ad.store_id = s.id
            LEFT JOIN users u ON ad.user_id = u.id
            LEFT JOIN users ru ON ad.registered_by = ru.id
            ORDER BY ad.registered_at DESC
        """)

    def count_active_authorized_devices(self) -> int:
        row = self._fetch_one("""
            SELECT COUNT(*) AS count
            FROM authorized_devices
            WHERE is_active = TRUE
        """)
        return int(row.get("count") or 0) if row else 0

    def get_authorized_device_for_login(
        self,
        device_id: str,
        mac_address: str,
        user_id: int,
        store_id: int = None,
    ) -> Optional[Dict]:
        return self._fetch_one("""
            SELECT *
            FROM authorized_devices
            WHERE is_active = TRUE
              AND (device_id = %s OR mac_address = %s)
              AND (user_id IS NULL OR user_id = %s)
              AND (store_id IS NULL OR store_id = %s)
            ORDER BY
              CASE WHEN user_id = %s THEN 0 ELSE 1 END,
              CASE WHEN store_id = %s THEN 0 ELSE 1 END,
              id DESC
            LIMIT 1
        """, (device_id, mac_address, user_id, store_id, user_id, store_id))

    def mark_authorized_device_used(self, device_record_id: int) -> None:
        self._execute("""
            UPDATE authorized_devices
            SET last_used = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (device_record_id,))

    def upsert_authorized_device(self, device_id, device_name, mac, store_id,
                                 user_id, reg_by, notes="") -> None:
        self._execute("""
            INSERT INTO authorized_devices (
                device_id, device_name, mac_address, store_id, user_id, registered_by, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                device_name = VALUES(device_name),
                mac_address = VALUES(mac_address),
                store_id = VALUES(store_id),
                user_id = VALUES(user_id),
                registered_by = VALUES(registered_by),
                notes = VALUES(notes),
                is_active = TRUE
        """, (device_id, device_name, mac, store_id, user_id, reg_by, notes))

    def update_device_status_record(self, device_id: int, is_active: bool) -> None:
        self._execute(
            "UPDATE authorized_devices SET is_active = %s WHERE id = %s",
            (is_active, device_id),
        )

    def delete_device_record(self, device_id: int) -> None:
        self._execute("DELETE FROM authorized_devices WHERE id = %s", (device_id,))

    def get_sync_stats(self) -> Dict:
        """جلب إحصائيات المزامنة."""
        try:
            pending = self._fetch_one(
                "SELECT COUNT(*) as count FROM sync_queue WHERE status = 'pending'"
            )
            last_sync = self._fetch_one(
                "SELECT MAX(synced_at) as last_sync FROM sync_queue WHERE status = 'synced'"
            )
            return {
                "pending_count": pending["count"] if pending else 0,
                "last_sync_time": last_sync["last_sync"] if last_sync else None,
            }
        except Exception:
            return {"pending_count": 0, "last_sync_time": None}
