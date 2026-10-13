"""Call Center Repository - SQL access for call-center orders."""
from typing import Dict, List, Optional

from repositories.base_repo import BaseRepository


class CallCenterRepository(BaseRepository):
    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def get_all_stores(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT id, store_name
            FROM stores
            WHERE COALESCE(is_active, TRUE) = TRUE
              AND COALESCE(store_type, 'Branch') != 'GM'
            ORDER BY id
        """)

    def search_products(self, term: str) -> List[Dict]:
        like = f"%{term}%"
        return self._fetch_all("""
            SELECT p.id, p.product_code, p.product_name, p.sell_price, p.barcode,
                   c.category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = TRUE
            AND (p.product_name LIKE %s OR p.product_code LIKE %s OR p.barcode LIKE %s)
            LIMIT 100
        """, (like, like, like))

    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        return self._fetch_one("""
            SELECT id, name as customer_name, phone,
                   address, address as customer_address
            FROM customers WHERE phone = %s LIMIT 1
        """, (phone,))

    def update_customer(self, customer_id: int, name: str = "", address: str = ""):
        updates = []
        params = []
        if name:
            updates.append("name = %s")
            params.append(name)
        if address:
            updates.append("address = %s")
            params.append(address)
        if not updates:
            return
        params.append(customer_id)
        self._execute(f"UPDATE customers SET {', '.join(updates)} WHERE id = %s", tuple(params))

    def create_customer(self, name: str, phone: str = "", address: str = "") -> int:
        self._execute(
            "INSERT INTO customers (name, phone, address) VALUES (%s, %s, %s)",
            (name, phone or None, address or None),
        )
        return self._last_id

    def create_order_header(
        self,
        order_number: str,
        customer_name: str,
        phone: str,
        address: str,
        customer_city: Optional[str],
        customer_id: Optional[int],
        source_store_id: int,
        destination_store_id: int,
        user_id: int,
        total: float,
    ) -> int:
        self._execute("""
            INSERT INTO orders
            (order_number, customer_name, customer_phone, customer_address,
             customer_city, customer_id, source_store_id, destination_store_id,
             call_center_user_id, total_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
        """, (
            order_number,
            customer_name,
            phone,
            address,
            customer_city,
            customer_id,
            source_store_id,
            destination_store_id,
            user_id,
            total,
        ))
        return self._last_id

    def insert_order_item(self, order_id: int, product_id: int, quantity: float, price: float):
        self._execute("""
            INSERT INTO order_items
            (order_id, product_id, quantity, unit_price, total_price)
            VALUES (%s, %s, %s, %s, %s)
        """, (order_id, product_id, quantity, price, quantity * price))

    def get_orders(self, statuses: list[str] = None, store_id: int = None,
                   search: str = None) -> List[Dict]:
        query = """
            SELECT o.id, o.order_number, o.customer_name, o.customer_phone,
                   o.customer_address, dst.store_name as target_store,
                   src.store_name as source_store,
                     o.total_amount, o.status, o.delivery_status,
                     o.delivery_agent_id, da.name as delivery_agent_name,
                     o.order_date, o.created_at, o.notes
            FROM orders o
            LEFT JOIN stores dst ON o.destination_store_id = dst.id
            LEFT JOIN stores src ON o.source_store_id = src.id
                 LEFT JOIN users da ON o.delivery_agent_id = da.id
        """
        conditions = []
        params = []

        if statuses:
            placeholders = ", ".join(["%s"] * len(statuses))
            conditions.append(f"o.status IN ({placeholders})")
            params.extend(statuses)
        if store_id:
            conditions.append("COALESCE(o.destination_store_id, o.source_store_id) = %s")
            params.append(store_id)
        if search:
            conditions.append("(o.order_number LIKE %s OR o.customer_name LIKE %s OR o.customer_phone LIKE %s)")
            like = f"%{search}%"
            params.extend([like, like, like])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY o.order_date DESC LIMIT 1000"
        return self._fetch_all(query, tuple(params))

    def get_order_details(self, order_id: int) -> List[Dict]:
        return self._fetch_all("""
            SELECT oi.*, p.product_code, p.product_name
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order_id,))

    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        return self._fetch_one("""
            SELECT o.*, dst.store_name as target_store, src.store_name as source_store,
                 u.name as agent_name, da.name as delivery_agent_name
            FROM orders o
            LEFT JOIN stores dst ON o.destination_store_id = dst.id
            LEFT JOIN stores src ON o.source_store_id = src.id
            LEFT JOIN users u ON o.call_center_user_id = u.id
             LEFT JOIN users da ON o.delivery_agent_id = da.id
            WHERE o.id = %s
        """, (order_id,))

    def update_order_status(self, order_id: int, status: str):
        self._execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))

    def get_delivery_agents(self, store_id: int) -> List[Dict]:
        return self._fetch_all("""
            SELECT u.id, u.name, u.phone, u.store_id
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE u.store_id = %s
              AND COALESCE(u.is_active, TRUE) = TRUE
              AND r.role_name IN ('delivery', 'delivery_agent')
            ORDER BY u.name
        """, (store_id,))

    def assign_delivery_agent(self, order_id: int, agent_id: int):
        self._execute("""
            UPDATE orders
            SET delivery_agent_id = %s,
                delivery_status = 'Assigned',
                delivery_assigned_at = NOW()
            WHERE id = %s
        """, (agent_id, order_id))

    def update_delivery_status(self, order_id: int, status: str, notes: str = None):
        self._execute("""
            UPDATE orders
            SET delivery_status = %s, delivery_notes = COALESCE(%s, delivery_notes)
            WHERE id = %s
        """, (status, notes, order_id))
