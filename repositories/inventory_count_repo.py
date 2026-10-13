from __future__ import annotations

import logging
from typing import Dict, List, Optional

from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class InventoryCountRepository(BaseRepository):
    def __init__(self):
        super().__init__()
        self.ensure_tables()

    def ensure_tables(self) -> None:
        try:
            self._execute("""
                CREATE TABLE IF NOT EXISTS inventory_count_sessions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    count_number VARCHAR(50) NOT NULL UNIQUE,
                    store_id INT NOT NULL,
                    count_type ENUM('full', 'partial', 'cycle', 'spot') NOT NULL DEFAULT 'partial',
                    status ENUM('open', 'review', 'approved', 'cancelled') NOT NULL DEFAULT 'open',
                    notes TEXT,
                    created_by INT NOT NULL,
                    approved_by INT NULL,
                    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    approved_at DATETIME NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (store_id) REFERENCES stores(id),
                    FOREIGN KEY (created_by) REFERENCES users(id),
                    FOREIGN KEY (approved_by) REFERENCES users(id),
                    INDEX idx_count_store_status (store_id, status),
                    INDEX idx_count_started (started_at)
                )
            """)
            self._execute("""
                CREATE TABLE IF NOT EXISTS inventory_count_items (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    session_id INT NOT NULL,
                    product_id INT NOT NULL,
                    book_quantity INT NOT NULL DEFAULT 0,
                    actual_quantity INT NULL,
                    variance INT NULL,
                    unit_cost DECIMAL(12, 2) NOT NULL DEFAULT 0,
                    notes VARCHAR(255),
                    counted_by INT NULL,
                    counted_at DATETIME NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES inventory_count_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    FOREIGN KEY (counted_by) REFERENCES users(id),
                    UNIQUE KEY unique_session_product (session_id, product_id),
                    INDEX idx_count_items_session (session_id),
                    INDEX idx_count_items_variance (variance)
                )
            """)
            self._execute("""
                CREATE TABLE IF NOT EXISTS inventory_count_adjustments (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    session_id INT NOT NULL,
                    item_id INT NOT NULL,
                    product_id INT NOT NULL,
                    store_id INT NOT NULL,
                    old_quantity INT NOT NULL DEFAULT 0,
                    new_quantity INT NOT NULL DEFAULT 0,
                    variance INT NOT NULL DEFAULT 0,
                    unit_cost DECIMAL(12, 2) NOT NULL DEFAULT 0,
                    adjustment_value DECIMAL(12, 2) NOT NULL DEFAULT 0,
                    adjustment_type ENUM('increase', 'decrease', 'no_change') NOT NULL DEFAULT 'no_change',
                    created_by INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES inventory_count_sessions(id),
                    FOREIGN KEY (item_id) REFERENCES inventory_count_items(id),
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    FOREIGN KEY (store_id) REFERENCES stores(id),
                    FOREIGN KEY (created_by) REFERENCES users(id),
                    INDEX idx_count_adjustments_session (session_id),
                    INDEX idx_count_adjustments_store (store_id)
                )
            """)
            self._commit()
        except Exception as exc:
            self._rollback()
            logger.error("Error ensuring inventory count tables: %s", exc, exc_info=True)
            raise

    def commit(self) -> None:
        self._commit()

    def rollback(self) -> None:
        self._rollback()

    def get_stores(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT id, store_name, store_type
            FROM stores
            WHERE is_active = TRUE
              AND COALESCE(store_type, 'Branch') != 'GM'
            ORDER BY id
        """)

    def create_session(self, count_number: str, store_id: int, count_type: str, user_id: int, notes: str = "") -> int:
        self._execute("""
            INSERT INTO inventory_count_sessions
                (count_number, store_id, count_type, status, notes, created_by)
            VALUES (%s, %s, %s, 'open', %s, %s)
        """, (count_number, store_id, count_type, notes, user_id))
        return self._last_id

    def populate_full_session(self, session_id: int, store_id: int) -> int:
        self._execute("""
            INSERT IGNORE INTO inventory_count_items
                (session_id, product_id, book_quantity, unit_cost)
            SELECT
                %s,
                p.id,
                COALESCE(pi.quantity_in_stock, 0),
                COALESCE(p.buy_price, 0)
            FROM products p
            LEFT JOIN product_inventory pi
                ON pi.product_id = p.id AND pi.store_id = %s
            WHERE p.is_active = TRUE
        """, (session_id, store_id))
        return self._affected_rows

    def get_sessions(self, store_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict]:
        query = """
            SELECT s.*, st.store_name, u.name AS created_by_name,
                   COUNT(i.id) AS item_count,
                   SUM(CASE WHEN i.actual_quantity IS NOT NULL THEN 1 ELSE 0 END) AS counted_count,
                   SUM(CASE WHEN COALESCE(i.variance, 0) != 0 THEN 1 ELSE 0 END) AS variance_count,
                   SUM(COALESCE(i.variance, 0) * COALESCE(i.unit_cost, 0)) AS variance_value
            FROM inventory_count_sessions s
            JOIN stores st ON st.id = s.store_id
            LEFT JOIN users u ON u.id = s.created_by
            LEFT JOIN inventory_count_items i ON i.session_id = s.id
            WHERE 1=1
        """
        params = []
        if store_id:
            query += " AND s.store_id = %s"
            params.append(store_id)
        if status and status != "all":
            query += " AND s.status = %s"
            params.append(status)
        query += """
            GROUP BY s.id, st.store_name, u.name
            ORDER BY s.started_at DESC, s.id DESC
            LIMIT 100
        """
        return self._fetch_all(query, tuple(params))

    def get_session(self, session_id: int) -> Optional[Dict]:
        return self._fetch_one("""
            SELECT s.*, st.store_name
            FROM inventory_count_sessions s
            JOIN stores st ON st.id = s.store_id
            WHERE s.id = %s
        """, (session_id,))

    def get_session_items(self, session_id: int, search: str = "", limit: int = 300) -> List[Dict]:
        query = """
            SELECT i.id, i.session_id, i.product_id, p.product_code, p.barcode,
                   p.product_name, i.book_quantity, i.actual_quantity,
                   i.variance, i.unit_cost, i.notes, i.counted_at
            FROM inventory_count_items i
            JOIN products p ON p.id = i.product_id
            WHERE i.session_id = %s
        """
        params = [session_id]
        if search:
            query += " AND (p.product_code LIKE %s OR p.barcode LIKE %s OR p.product_name LIKE %s)"
            like = f"%{search}%"
            params.extend([like, like, like])
        query += " ORDER BY ABS(COALESCE(i.variance, 0)) DESC, p.product_name LIMIT %s"
        params.append(int(limit))
        return self._fetch_all(query, tuple(params))

    def search_products(self, term: str, store_id: int, limit: int = 50) -> List[Dict]:
        like = f"%{term}%"
        return self._fetch_all("""
            SELECT p.id, p.product_code, p.barcode, p.product_name,
                   COALESCE(pi.quantity_in_stock, 0) AS quantity_in_stock,
                   COALESCE(p.buy_price, 0) AS buy_price
            FROM products p
            LEFT JOIN product_inventory pi
                ON pi.product_id = p.id AND pi.store_id = %s
            WHERE p.is_active = TRUE
              AND (p.product_code LIKE %s OR p.barcode LIKE %s OR p.product_name LIKE %s)
            ORDER BY p.product_name
            LIMIT %s
        """, (store_id, like, like, like, int(limit)))

    def add_product_to_session(self, session_id: int, product_id: int, store_id: int) -> None:
        self._execute("""
            INSERT IGNORE INTO inventory_count_items
                (session_id, product_id, book_quantity, unit_cost)
            SELECT %s, p.id, COALESCE(pi.quantity_in_stock, 0), COALESCE(p.buy_price, 0)
            FROM products p
            LEFT JOIN product_inventory pi
                ON pi.product_id = p.id AND pi.store_id = %s
            WHERE p.id = %s AND p.is_active = TRUE
        """, (session_id, store_id, product_id))

    def update_count_item(self, session_id: int, product_id: int, actual_quantity: float, notes: str, user_id: int) -> None:
        self._execute("""
            UPDATE inventory_count_items
            SET actual_quantity = %s,
                variance = %s - book_quantity,
                notes = %s,
                counted_by = %s,
                counted_at = NOW()
            WHERE session_id = %s AND product_id = %s
        """, (actual_quantity, actual_quantity, notes, user_id, session_id, product_id))

    def get_counted_items(self, session_id: int) -> List[Dict]:
        return self._fetch_all("""
            SELECT i.*, p.product_name
            FROM inventory_count_items i
            JOIN products p ON p.id = i.product_id
            WHERE i.session_id = %s AND i.actual_quantity IS NOT NULL
        """, (session_id,))

    def set_inventory_quantity(self, product_id: int, store_id: int, quantity: float, user_id: int, notes: str) -> None:
        self._execute("""
            INSERT INTO product_inventory
                (product_id, store_id, quantity_in_stock, last_count_date, last_counted_by, notes)
            VALUES (%s, %s, %s, NOW(), %s, %s)
            ON DUPLICATE KEY UPDATE
                quantity_in_stock = VALUES(quantity_in_stock),
                last_count_date = NOW(),
                last_counted_by = VALUES(last_counted_by),
                notes = VALUES(notes)
        """, (product_id, store_id, quantity, user_id, notes))

    def insert_adjustment(self, session_id: int, item_id: int, item: Dict, store_id: int, user_id: int) -> None:
        variance = float(item.get("variance") or 0)
        adjustment_type = "increase" if variance > 0 else "decrease" if variance < 0 else "no_change"
        unit_cost = float(item.get("unit_cost") or 0)
        self._execute("""
            INSERT INTO inventory_count_adjustments
                (session_id, item_id, product_id, store_id, old_quantity, new_quantity,
                 variance, unit_cost, adjustment_value, adjustment_type, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id,
            item_id,
            item.get("product_id"),
            store_id,
            float(item.get("book_quantity") or 0),
            float(item.get("actual_quantity") or 0),
            variance,
            unit_cost,
            variance * unit_cost,
            adjustment_type,
            user_id,
        ))

    def mark_session_approved(self, session_id: int, user_id: int) -> None:
        self._execute("""
            UPDATE inventory_count_sessions
            SET status = 'approved', approved_by = %s, approved_at = NOW()
            WHERE id = %s
        """, (user_id, session_id))

    def mark_session_cancelled(self, session_id: int) -> None:
        self._execute("""
            UPDATE inventory_count_sessions
            SET status = 'cancelled'
            WHERE id = %s AND status != 'approved'
        """, (session_id,))
