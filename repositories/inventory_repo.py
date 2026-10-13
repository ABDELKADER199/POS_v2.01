"""
Inventory Repository - مستودع المخزون
"""
import logging
from typing import List, Dict
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class InventoryRepository(BaseRepository):
    """مستودع عمليات المخزون"""

    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def get_stock(self, product_id: int, store_id: int) -> float:
        """جلب الكمية المتاحة لمنتج في فرع"""
        row = self._fetch_one("""
            SELECT quantity_in_stock FROM product_inventory
            WHERE product_id = %s AND store_id = %s
        """, (product_id, store_id))
        return float(row['quantity_in_stock']) if row else 0.0

    def set_stock(self, product_id: int, store_id: int, quantity: float) -> None:
        self._execute("""
            INSERT INTO product_inventory (product_id, store_id, quantity_in_stock)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity_in_stock = %s
        """, (product_id, store_id, quantity, quantity))

    def add_stock(self, product_id: int, store_id: int, quantity: float) -> None:
        self._execute("""
            INSERT INTO product_inventory (product_id, store_id, quantity_in_stock)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity_in_stock = quantity_in_stock + %s
        """, (product_id, store_id, quantity, quantity))

    def subtract_stock(self, product_id: int, store_id: int, quantity: float) -> None:
        self._execute("""
            UPDATE product_inventory
            SET quantity_in_stock = GREATEST(0, quantity_in_stock - %s)
            WHERE product_id = %s AND store_id = %s
        """, (quantity, product_id, store_id))

    def _legacy_update_stock(self, product_id: int, store_id: int,
                     quantity: float, operation: str = 'set') -> bool:
        """تحديث المخزون"""
        try:
            if operation == 'add':
                self._execute("""
                    INSERT INTO product_inventory (product_id, store_id, quantity_in_stock)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE quantity_in_stock = quantity_in_stock + %s
                """, (product_id, store_id, quantity, quantity))
            elif operation == 'subtract':
                self._execute("""
                    UPDATE product_inventory
                    SET quantity_in_stock = GREATEST(0, quantity_in_stock - %s)
                    WHERE product_id = %s AND store_id = %s
                """, (quantity, product_id, store_id))
            else:  # set
                self._execute("""
                    INSERT INTO product_inventory (product_id, store_id, quantity_in_stock)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE quantity_in_stock = %s
                """, (product_id, store_id, quantity, quantity))
            self._commit()
            return True
        except Exception as e:
            self._rollback()
            logger.error(f"Error updating stock: {e}")
            return False

    def _stock_filters(
        self,
        store_id: int = None,
        low_stock_only: bool = False,
        search: str = "",
        filters: dict = None,
    ):
        filters = filters or {}
        params = []
        if store_id:
            join = """
                JOIN stores s ON s.id = %s AND s.is_active = TRUE
                LEFT JOIN product_inventory pi ON p.id = pi.product_id AND pi.store_id = s.id
            """
            params.append(store_id)
        else:
            join = """
                LEFT JOIN product_inventory pi ON p.id = pi.product_id
                LEFT JOIN stores s ON pi.store_id = s.id
            """

        where = "WHERE p.is_active = TRUE AND (s.id IS NULL OR COALESCE(s.store_type, 'Branch') != 'GM')"
        if low_stock_only:
            where += " AND COALESCE(pi.quantity_in_stock, 0) <= COALESCE(pi.minimum_quantity, 10)"

        search = str(search or "").strip()
        if search:
            where += " AND (p.product_code LIKE %s OR p.barcode LIKE %s OR p.product_name LIKE %s)"
            like = f"%{search}%"
            params.extend([like, like, like])

        code = str(filters.get("code") or "").strip()
        if code:
            where += " AND (p.product_code LIKE %s OR p.barcode LIKE %s)"
            like = f"%{code}%"
            params.extend([like, like])

        name = str(filters.get("name") or "").strip()
        if name:
            where += " AND p.product_name LIKE %s"
            params.append(f"%{name}%")

        stock_status = str(filters.get("stock_status") or "").strip()
        if stock_status == "available":
            where += " AND COALESCE(pi.quantity_in_stock, 0) > COALESCE(pi.minimum_quantity, 10)"
        elif stock_status == "low":
            where += " AND COALESCE(pi.quantity_in_stock, 0) > 0 AND COALESCE(pi.quantity_in_stock, 0) <= COALESCE(pi.minimum_quantity, 10)"
        elif stock_status == "out":
            where += " AND COALESCE(pi.quantity_in_stock, 0) <= 0"

        min_qty = filters.get("min_qty")
        if min_qty is not None:
            where += " AND COALESCE(pi.quantity_in_stock, 0) >= %s"
            params.append(int(min_qty))

        max_qty = filters.get("max_qty")
        if max_qty is not None:
            where += " AND COALESCE(pi.quantity_in_stock, 0) <= %s"
            params.append(int(max_qty))

        min_price = filters.get("min_price")
        if min_price is not None:
            where += " AND COALESCE(p.sell_price, 0) >= %s"
            params.append(float(min_price))

        max_price = filters.get("max_price")
        if max_price is not None:
            where += " AND COALESCE(p.sell_price, 0) <= %s"
            params.append(float(max_price))

        return join, where, params

    def get_all_stock(self, store_id: int = None, low_stock_only: bool = False,
                      limit: int = 100, offset: int = 0, search: str = "",
                      filters: dict = None) -> List[Dict]:
        """??? ??????? ?? ?????? ????????? ?? ????? ?????? ????? ??? ?? ?? ??? ??? ???? ????."""
        join, where, params = self._stock_filters(store_id, low_stock_only, search, filters)
        query = """
            SELECT p.id, p.product_code, p.product_name, p.category_id,
                   p.buy_price, p.sell_price, p.unit,
                   COALESCE(pi.quantity_in_stock, 0) AS quantity_in_stock,
                   s.id AS store_id, s.store_name,
                   COALESCE(pi.minimum_quantity, 0) AS min_quantity
            FROM products p
        """ + join + "\n" + where + "\n"

        query += f" ORDER BY {self._stock_order_clause(filters)} LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        return self._fetch_all(query, tuple(params))

    def count_all_stock(self, store_id: int = None, low_stock_only: bool = False,
                        search: str = "", filters: dict = None) -> int:
        join, where, params = self._stock_filters(store_id, low_stock_only, search, filters)
        query = """
            SELECT COUNT(*) AS cnt
            FROM products p
        """ + join + "\n" + where
        row = self._fetch_one(query, tuple(params))
        return int((row or {}).get("cnt") or 0)

    def _stock_order_clause(self, filters: dict = None) -> str:
        filters = filters or {}
        sort_by = (filters.get("sort_by") or "").strip()
        direction = (filters.get("sort_direction") or "").strip().lower()
        direction_sql = "DESC" if direction == "desc" else "ASC"
        allowed = {
            "quantity": "COALESCE(pi.quantity_in_stock, 0)",
            "sell_price": "COALESCE(p.sell_price, 0)",
        }
        column = allowed.get(sort_by)
        if not column:
            return "p.product_name"
        return f"{column} {direction_sql}, p.product_name"

    def _legacy_transfer(self, product_id: int, from_store: int, to_store: int,
                 quantity: float, user_id: int) -> bool:
        """تحويل مخزون بين الفروع"""
        try:
            # التحقق من الكمية المتاحة
            current = self.get_stock(product_id, from_store)
            if current < quantity:
                raise ValueError(f"الكمية المتاحة ({current}) أقل من المطلوب ({quantity})")

            # خصم من المصدر
            self._legacy_update_stock(product_id, from_store, quantity, 'subtract')
            # إضافة إلى الوجهة
            self._legacy_update_stock(product_id, to_store, quantity, 'add')

            # تسجيل التحويل
            self._execute("""
                INSERT INTO inventory_transfers
                    (product_id, from_store_id, to_store_id, quantity, transferred_by, status)
                VALUES (%s, %s, %s, %s, %s, 'Completed')
            """, (product_id, from_store, to_store, quantity, user_id))

            self._commit()
            logger.info(f"✅ Transfer: {quantity} of product {product_id} from store {from_store} to {to_store}")
            return True
        except Exception as e:
            self._rollback()
            logger.error(f"Error in transfer: {e}")
            raise
