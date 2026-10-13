"""Transfers Repository - SQL access for warehouse transfers."""
from typing import Dict, List, Optional

from repositories.base_repo import BaseRepository


class TransfersRepository(BaseRepository):
    """Data access for warehouse transfer workflow."""

    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def get_stores(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT id, store_name, store_type
            FROM stores
            WHERE COALESCE(is_active, TRUE) = TRUE
              AND COALESCE(store_type, 'Branch') != 'GM'
            ORDER BY id
        """)

    def search_products(self, term: str, store_id: int = None, limit: int = 25) -> List[Dict]:
        query = """
            SELECT p.id, p.product_code, p.product_name, p.barcode, p.sell_price,
                   COALESCE(pi.quantity_in_stock, 0) AS quantity_in_stock,
                   pi.store_id, s.store_name
            FROM products p
            LEFT JOIN product_inventory pi ON p.id = pi.product_id
            LEFT JOIN stores s ON pi.store_id = s.id
            WHERE p.is_active = TRUE
              AND (p.product_code LIKE %s OR p.product_name LIKE %s OR p.barcode LIKE %s)
        """
        like = f"%{term}%"
        params = [like, like, like]
        if store_id:
            query += " AND pi.store_id = %s"
            params.append(store_id)
        query += " ORDER BY p.product_name LIMIT %s"
        params.append(limit)
        return self._fetch_all(query, tuple(params))

    def get_stock(self, product_id: int, store_id: int) -> int:
        row = self._fetch_one("""
            SELECT quantity_in_stock
            FROM product_inventory
            WHERE product_id = %s AND store_id = %s
        """, (product_id, store_id))
        return int(row["quantity_in_stock"]) if row else 0

    def get_transfers(self, store_id: int = None, status: str = None) -> List[Dict]:
        query = """
            SELECT wt.id, wt.transfer_number, wt.from_store_id, wt.to_store_id,
                   fs.store_name AS from_store_name, ts.store_name AS to_store_name,
                   wt.status, wt.transfer_date, wt.received_date, wt.notes,
                   ti.product_id, p.product_code, p.product_name,
                   ti.quantity_sent, ti.quantity_received
            FROM warehouse_transfers wt
            JOIN stores fs ON wt.from_store_id = fs.id
            JOIN stores ts ON wt.to_store_id = ts.id
            JOIN transfer_items ti ON wt.id = ti.transfer_id
            JOIN products p ON ti.product_id = p.id
            WHERE 1=1
        """
        params = []
        if store_id:
            query += " AND (wt.from_store_id = %s OR wt.to_store_id = %s)"
            params.extend([store_id, store_id])
        if status and status != "All":
            query += " AND wt.status = %s"
            params.append(status)
        query += " ORDER BY wt.transfer_date DESC, wt.id DESC LIMIT 200"
        return self._fetch_all(query, tuple(params))

    def create_transfer_header(self, transfer_number: str, from_store_id: int,
                               to_store_id: int, user_id: int, notes: str = "") -> int:
        self._execute("""
            INSERT INTO warehouse_transfers
                (transfer_number, from_store_id, to_store_id, created_by, status, notes)
            VALUES (%s, %s, %s, %s, 'Pending', %s)
        """, (transfer_number, from_store_id, to_store_id, user_id, notes))
        return self._last_id

    def insert_transfer_item(self, transfer_id: int, product_id: int, quantity: int,
                             notes: str = ""):
        self._execute("""
            INSERT INTO transfer_items
                (transfer_id, product_id, quantity_sent, notes)
            VALUES (%s, %s, %s, %s)
        """, (transfer_id, product_id, quantity, notes))

    def decrease_inventory(self, product_id: int, store_id: int, quantity: int):
        self._execute("""
            UPDATE product_inventory
            SET quantity_in_stock = quantity_in_stock - %s
            WHERE product_id = %s AND store_id = %s
        """, (quantity, product_id, store_id))

    def increase_inventory(self, product_id: int, store_id: int, quantity: int):
        self._execute("""
            INSERT INTO product_inventory (product_id, store_id, quantity_in_stock)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity_in_stock = quantity_in_stock + VALUES(quantity_in_stock)
        """, (product_id, store_id, quantity))

    def get_transfer_for_receiving(self, transfer_id: int) -> Optional[Dict]:
        return self._fetch_one("""
            SELECT wt.id, wt.to_store_id, wt.status,
                   ti.product_id, ti.quantity_sent
            FROM warehouse_transfers wt
            JOIN transfer_items ti ON wt.id = ti.transfer_id
            WHERE wt.id = %s
        """, (transfer_id,))

    def get_transfer_for_cancellation(self, transfer_id: int) -> Optional[Dict]:
        return self._fetch_one("""
            SELECT wt.id, wt.from_store_id, wt.status,
                   ti.product_id, ti.quantity_sent
            FROM warehouse_transfers wt
            JOIN transfer_items ti ON wt.id = ti.transfer_id
            WHERE wt.id = %s
        """, (transfer_id,))

    def mark_transfer_received(self, transfer_id: int, user_id: int):
        self._execute("""
            UPDATE transfer_items
            SET quantity_received = quantity_sent
            WHERE transfer_id = %s
        """, (transfer_id,))
        self._execute("""
            UPDATE warehouse_transfers
            SET status = 'Received', received_by = %s, received_date = NOW()
            WHERE id = %s
        """, (user_id, transfer_id))

    def mark_transfer_cancelled(self, transfer_id: int):
        self._execute("""
            UPDATE warehouse_transfers
            SET status = 'Cancelled'
            WHERE id = %s
        """, (transfer_id,))
