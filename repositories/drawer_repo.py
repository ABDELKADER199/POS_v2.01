"""
Drawer Repository - مستودع الدرج النقدي
"""
import logging
from typing import Dict, List, Optional
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class DrawerRepository(BaseRepository):
    """مستودع عمليات الدرج النقدي"""

    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def get_store_open_drawer(self, store_id: int) -> Optional[Dict]:
        """جلب الدرج المفتوح في الفرع"""
        return self._fetch_one("""
            SELECT dl.id, dl.store_id, dl.cashier_id, dl.opening_balance,
                   dl.opening_date as opened_at,
                   u.name as cashier_name,
                   s.store_name,
                   s.store_type
            FROM drawer_logs dl
            JOIN users u ON dl.cashier_id = u.id
            LEFT JOIN stores s ON dl.store_id = s.id
            WHERE dl.store_id = %s
              AND dl.status = 'Open'
              AND COALESCE(s.store_type, 'Branch') = 'Branch'
            ORDER BY dl.opening_date DESC LIMIT 1
        """, (store_id,))

    def get_any_open_drawer(self) -> Optional[Dict]:
        """جلب أحدث درج مفتوح على مستوى كل الفروع."""
        return self._fetch_one("""
            SELECT dl.id, dl.store_id, dl.cashier_id, dl.opening_balance,
                   dl.opening_date as opened_at,
                   u.name as cashier_name,
                   s.store_name,
                   s.store_type
            FROM drawer_logs dl
            JOIN users u ON dl.cashier_id = u.id
            LEFT JOIN stores s ON dl.store_id = s.id
            WHERE dl.status = 'Open'
              AND COALESCE(s.store_type, 'Branch') = 'Branch'
            ORDER BY dl.opening_date DESC LIMIT 1
        """)

    def get_operational_stores(self) -> List[Dict]:
        return self._fetch_all("""
            SELECT id, store_name, store_type
            FROM stores
            WHERE is_active = TRUE
              AND COALESCE(store_type, 'Branch') = 'Branch'
            ORDER BY
              CASE COALESCE(store_type, 'Branch')
                WHEN 'Branch' THEN 0
                WHEN 'Main' THEN 1
                WHEN 'Warehouse' THEN 2
                ELSE 3
              END,
              id
        """)

    def get_drawer_status(self, user_id: int) -> Optional[Dict]:
        """جلب حالة الدرج للمستخدم"""
        row = self._fetch_one("""
            SELECT dl.id, dl.store_id, dl.cashier_id, dl.opening_balance, dl.opening_date,
                   dl.status, (dl.status = 'Open') as is_open
            FROM drawer_logs dl
            LEFT JOIN stores s ON dl.store_id = s.id
            WHERE dl.cashier_id = %s
              AND dl.status = 'Open'
              AND COALESCE(s.store_type, 'Branch') = 'Branch'
            ORDER BY opening_date DESC LIMIT 1
        """, (user_id,))
        return row

    def insert_open_drawer(self, store_id: int, user_id: int, opening_balance: float) -> int:
        self._execute("""
            INSERT INTO drawer_logs (store_id, cashier_id, opening_balance, status)
            VALUES (%s, %s, %s, 'Open')
        """, (store_id, user_id, opening_balance))
        return self._last_id

    def mark_drawer_closed(self, drawer_id: int, closing_balance: float) -> None:
        self._execute("""
            UPDATE drawer_logs
            SET status = 'Closed', closing_balance = %s, closing_date = NOW()
            WHERE id = %s AND status = 'Open'
        """, (closing_balance, drawer_id))

    def replace_closing_details(self, drawer_id: int, denomination_details: dict) -> None:
        self._execute("DELETE FROM drawer_closing_details WHERE drawer_log_id = %s", (drawer_id,))
        for denom, qty in (denomination_details or {}).items():
            if denom in ("Visa", "Cash"):
                quantity = 1
                total_amount = float(qty or 0)
            else:
                quantity = int(qty or 0)
                total_amount = float(qty or 0)
            self._execute("""
                INSERT INTO drawer_closing_details
                (drawer_log_id, denomination, quantity, total_amount)
                VALUES (%s, %s, %s, %s)
            """, (drawer_id, str(denom), quantity, total_amount))

    def _legacy_open_drawer(self, store_id: int, user_id: int, opening_balance: float) -> bool:
        """فتح درج جديد"""
        try:
            self._execute("""
                INSERT INTO drawer_logs (store_id, cashier_id, opening_balance, status)
                VALUES (%s, %s, %s, 'Open')
            """, (store_id, user_id, opening_balance))
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error opening drawer: {e}")
            self._rollback()
            return False

    def _legacy_close_drawer(self, drawer_id: int, closing_balance: float,
                     denomination_details: dict = None) -> bool:
        """إغلاق الدرج"""
        try:
            self._execute("""
                UPDATE drawer_logs
                SET status = 'Closed', closing_balance = %s, closing_date = NOW()
                WHERE id = %s AND status = 'Open'
            """, (closing_balance, drawer_id))

            # Save denomination details
            if denomination_details:
                self._execute("DELETE FROM drawer_closing_details WHERE drawer_log_id = %s", (drawer_id,))
                for denom, qty in denomination_details.items():
                    if denom in ("Visa", "Cash"):
                        quantity = 1
                        total_amount = float(qty or 0)
                    else:
                        quantity = int(qty or 0)
                        total_amount = float(qty or 0)
                    self._execute("""
                        INSERT INTO drawer_closing_details
                        (drawer_log_id, denomination, quantity, total_amount)
                        VALUES (%s, %s, %s, %s)
                    """, (drawer_id, str(denom), quantity, total_amount))

            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error closing drawer: {e}")
            self._rollback()
            return False

    def get_drawer_summary(self, drawer_id: int) -> Optional[Dict]:
        """جلب ملخص الدرج"""
        drawer = self._fetch_one("""
            SELECT dl.*, u.name as cashier_name, s.store_name
            FROM drawer_logs dl
            JOIN users u ON dl.cashier_id = u.id
            JOIN stores s ON dl.store_id = s.id
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

        details = self._fetch_all("""
            SELECT *
            FROM drawer_closing_details
            WHERE drawer_log_id = %s
            ORDER BY id
        """, (drawer_id,))

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

    def get_open_drawer_summary(self, drawer_id: int) -> Optional[Dict]:
        """ملخص لحظي للدرج المفتوح قبل الإغلاق."""
        return self.get_drawer_summary(drawer_id)

    def get_closed_drawers_history(self, store_id: int,
                                    date_from: str = None, date_to: str = None) -> List[Dict]:
        """جلب سجل الأدراج المغلقة"""
        if date_from and date_to:
            return self._fetch_all("""
                SELECT dl.id, u.name as cashier_name, dl.closing_date,
                       dl.opening_balance, dl.closing_balance,
                       COALESCE((
                           SELECT SUM(cash_amount)
                           FROM invoices
                           WHERE drawer_id = dl.id AND status = 'Completed'
                       ), 0) as cash_sales,
                       COALESCE((
                           SELECT SUM(sr.total_amount)
                           FROM sales_returns sr
                           JOIN invoices i ON sr.original_invoice_id = i.id
                           WHERE sr.drawer_id = dl.id AND i.cash_amount > 0
                       ), 0) as cash_returns,
                       COALESCE((
                           SELECT SUM(card_amount)
                           FROM invoices
                           WHERE drawer_id = dl.id AND status = 'Completed'
                       ), 0) as card_sales,
                       COALESCE((
                           SELECT SUM(total_amount)
                           FROM invoices
                           WHERE drawer_id = dl.id AND status = 'Completed'
                       ), 0) as total_sales
                FROM drawer_logs dl
                JOIN users u ON dl.cashier_id = u.id
                WHERE dl.store_id = %s AND dl.status = 'Closed'
                AND DATE(dl.closing_date) BETWEEN %s AND %s
                ORDER BY dl.closing_date DESC
            """, (store_id, date_from, date_to))
        return self._fetch_all("""
            SELECT dl.id, u.name as cashier_name, dl.closing_date,
                   dl.opening_balance, dl.closing_balance,
                   COALESCE((
                       SELECT SUM(cash_amount)
                       FROM invoices
                       WHERE drawer_id = dl.id AND status = 'Completed'
                   ), 0) as cash_sales,
                   COALESCE((
                       SELECT SUM(sr.total_amount)
                       FROM sales_returns sr
                       JOIN invoices i ON sr.original_invoice_id = i.id
                       WHERE sr.drawer_id = dl.id AND i.cash_amount > 0
                   ), 0) as cash_returns,
                   COALESCE((
                       SELECT SUM(card_amount)
                       FROM invoices
                       WHERE drawer_id = dl.id AND status = 'Completed'
                   ), 0) as card_sales,
                   COALESCE((
                       SELECT SUM(total_amount)
                       FROM invoices
                       WHERE drawer_id = dl.id AND status = 'Completed'
                   ), 0) as total_sales
            FROM drawer_logs dl
            JOIN users u ON dl.cashier_id = u.id
            WHERE dl.store_id = %s AND dl.status = 'Closed'
            ORDER BY dl.closing_date DESC LIMIT 50
        """, (store_id,))

    def get_last_closed_drawer_id(self, store_id: int, user_id: int) -> Optional[int]:
        """جلب آخر درج مغلق"""
        row = self._fetch_one("""
            SELECT id FROM drawer_logs
            WHERE store_id = %s AND cashier_id = %s AND status = 'Closed'
            ORDER BY closing_date DESC LIMIT 1
        """, (store_id, user_id))
        return row['id'] if row else None
