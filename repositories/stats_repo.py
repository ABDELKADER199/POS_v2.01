"""
Stats Repository - مستودع الإحصائيات
جميع استعلامات الإحصائيات والتقارير
متوافق مع schema قاعدة البيانات الفعلية (stocks)
"""
import logging
from typing import List, Dict, Optional
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class StatsRepository(BaseRepository):
    """مستودع عمليات الإحصائيات والتقارير"""

    # ── Key Metrics ────────────────────────────────────
    def get_sales_summary(self, date_from: str, date_to: str, store_id: int = None) -> Dict:
        """ملخص المبيعات غير الحساس؛ الربح والتكلفة لهما استعلام مفوض منفصل."""
        store_filter = "AND i.store_id = %s" if store_id else ""
        params = [date_from, date_to]
        if store_id:
            params.append(store_id)

        row = self._fetch_one(f"""
            SELECT
                COALESCE(SUM(i.total_amount), 0) as total_sales,
                COUNT(i.id) as invoice_count,
                COALESCE(AVG(i.total_amount), 0) as avg_ticket
            FROM invoices i
            WHERE i.status = 'Completed'
            AND DATE(i.invoice_date) BETWEEN %s AND %s
            {store_filter}
        """, tuple(params))

        total_sales = float(row.get('total_sales', 0)) if row else 0
        invoice_count = int(row.get('invoice_count', 0)) if row else 0
        avg_ticket = float(row.get('avg_ticket', 0)) if row else 0

        return {
            'total_sales': total_sales,
            'invoice_count': invoice_count,
            'avg_ticket': avg_ticket,
        }

    def get_returns_summary(self, date_from: str, date_to: str, store_id: int = None) -> Dict:
        """ملخص المرتجعات - متوافق مع sales_returns"""
        try:
            store_filter = "AND r.store_id = %s" if store_id else ""
            params = [date_from, date_to]
            if store_id:
                params.append(store_id)

            row = self._fetch_one(f"""
                SELECT COALESCE(SUM(r.total_amount), 0) as total_returns,
                       COUNT(r.id) as return_count
                FROM sales_returns r
                WHERE DATE(r.return_date) BETWEEN %s AND %s
                {store_filter}
            """, tuple(params))

            return {
                'total_returns': float(row.get('total_returns', 0)) if row else 0,
                'return_count': int(row.get('return_count', 0)) if row else 0,
            }
        except Exception as e:
            logger.warning(f"Returns query failed: {e}")
            return {'total_returns': 0, 'return_count': 0}

    def get_expenses_breakdown(self, date_from: str = None, date_to: str = None, store_id: int = None) -> List[Dict]:
        """تفصيل المصروفات التشغيلية لتغذية قائمة الدخل"""
        try:
            query = "SELECT expense_type, SUM(amount) as total FROM expenses WHERE is_personal = 0"
            params = []
            if store_id:
                query += " AND store_id = %s"
                params.append(store_id)
            if date_from and date_to:
                query += " AND DATE(created_at) BETWEEN %s AND %s"
                params.extend([date_from, date_to])
            query += " GROUP BY expense_type ORDER BY total DESC"
            
            return self._fetch_all(query, tuple(params))
        except Exception as e:
            logger.error(f"Error fetching expenses breakdown: {e}")
            return []

    def get_net_profit_stats(self, date_from: str, date_to: str, store_id: int = None) -> Dict:
        """جلب تفاصيل الأرباح والمبيعات والتكلفة لقائمة الدخل"""
        try:
            invoice_params = [date_from, date_to]
            invoice_store_filter = ""
            if store_id:
                invoice_store_filter = " AND i.store_id = %s"
                invoice_params.append(store_id)

            # Sales
            sales_q = f"""
                SELECT COALESCE(SUM(i.total_amount), 0) as total_sales,
                       COUNT(i.id) as invoice_count
                FROM invoices i
                WHERE i.status = 'Completed'
                AND DATE(i.invoice_date) BETWEEN %s AND %s
                {invoice_store_filter}
            """
            sales_data = self._fetch_one(sales_q, tuple(invoice_params))

            # COGS
            cogs_q = f"""
                SELECT COALESCE(SUM(ii.quantity * COALESCE(ii.buy_price, p.buy_price, 0)), 0) as total_cogs
                FROM invoice_items ii
                JOIN invoices i ON ii.invoice_id = i.id
                JOIN products p ON ii.product_id = p.id
                WHERE i.status = 'Completed'
                AND DATE(i.invoice_date) BETWEEN %s AND %s
                {invoice_store_filter}
            """
            cogs_data = self._fetch_one(cogs_q, tuple(invoice_params))

            # Returns
            ret_params = [date_from, date_to]
            ret_store_filter = ""
            if store_id:
                ret_store_filter = " AND sr.store_id = %s"
                ret_params.append(store_id)
                
            ret_q = f"""
                SELECT COALESCE(SUM(total_amount), 0) as total_returns
                FROM sales_returns sr
                WHERE DATE(sr.return_date) BETWEEN %s AND %s
                {ret_store_filter}
            """
            ret_data = self._fetch_one(ret_q, tuple(ret_params))

            # Returned COGS
            cost_q = f"""
                SELECT COALESCE(SUM(ri.quantity * COALESCE(ri.buy_price, p.buy_price, 0)), 0) as total_returned_cost
                FROM sales_returns sr
                JOIN return_items ri ON sr.id = ri.return_id
                JOIN products p ON ri.product_id = p.id
                WHERE DATE(sr.return_date) BETWEEN %s AND %s
                {ret_store_filter}
            """
            cost_data = self._fetch_one(cost_q, tuple(ret_params))

            # Operational expenses
            expense_params = [date_from, date_to]
            expense_store_filter = ""
            if store_id:
                expense_store_filter = " AND store_id = %s"
                expense_params.append(store_id)
            expenses_data = self._fetch_one(f"""
                SELECT COALESCE(SUM(amount), 0) as total_expenses
                FROM expenses
                WHERE is_personal = 0
                  AND DATE(created_at) BETWEEN %s AND %s
                  {expense_store_filter}
            """, tuple(expense_params))

            supplier_claims = self._get_supplier_promotion_claims_total(date_from, date_to, store_id)

            total_sales = float(sales_data.get('total_sales', 0)) if sales_data else 0
            total_cogs = float(cogs_data.get('total_cogs', 0)) if cogs_data else 0
            invoice_count = int(sales_data.get('invoice_count', 0)) if sales_data else 0
            total_returns = float(ret_data.get('total_returns', 0)) if ret_data else 0
            total_returned_cost = float(cost_data.get('total_returned_cost', 0)) if cost_data else 0
            total_expenses = float(expenses_data.get('total_expenses', 0)) if expenses_data else 0

            net_sales = total_sales - total_returns
            adjusted_net_sales = net_sales + supplier_claims
            net_cogs = total_cogs - total_returned_cost
            gross_profit = adjusted_net_sales - net_cogs
            net_profit = gross_profit - total_expenses

            return {
                'total_sales': total_sales,
                'supplier_promotion_claims': supplier_claims,
                'adjusted_net_sales': adjusted_net_sales,
                'total_cogs': total_cogs,
                'total_returns': total_returns,
                'total_returned_cost': total_returned_cost,
                'total_expenses': total_expenses,
                'invoice_count': invoice_count,
                'net_sales': net_sales,
                'net_cogs': net_cogs,
                'gross_profit': gross_profit,
                'net_profit': net_profit,
                'avg_ticket': total_sales / invoice_count if invoice_count > 0 else 0,
                'profit_margin': (net_profit / adjusted_net_sales * 100) if adjusted_net_sales > 0 else 0,
                'return_rate': (total_returns / total_sales * 100) if total_sales > 0 else 0,
            }
        except Exception as e:
            logger.error(f"Error fetching P&L stats: {e}")
            return {}

    def _get_supplier_promotion_claims_total(self, date_from: str, date_to: str, store_id: int = None) -> float:
        try:
            store_filter = ""
            params = [date_from, date_to]
            if store_id:
                store_filter = "AND i.store_id = %s"
                params.append(store_id)
            row = self._fetch_one(f"""
                SELECT COALESCE(SUM(spc.amount), 0) AS total
                FROM supplier_promotion_claims spc
                JOIN invoices i ON spc.sale_invoice_id = i.id
                WHERE i.status = 'Completed'
                  AND DATE(i.invoice_date) BETWEEN %s AND %s
                  AND COALESCE(spc.status, 'pending') != 'cancelled'
                  {store_filter}
            """, tuple(params))
            return float(row.get("total", 0)) if row else 0.0
        except Exception:
            return 0.0

    # ── Inventory Valuation ────────────────────────────
    def get_inventory_valuation(self, store_id: int = None) -> dict:
        """إجمالي تكلفة البضاعة المتاحة وتفاصيل الأصناف"""
        params = []
        store_filter = " AND pi.store_id IN (SELECT id FROM stores WHERE COALESCE(is_active, TRUE) = TRUE AND COALESCE(store_type, 'Branch') != 'GM') "
        if store_id:
            store_filter = " AND pi.store_id = %s "
            params.append(store_id)
            
        row = self._fetch_one(f"""
            SELECT COALESCE(SUM(pi.quantity_in_stock * p.buy_price), 0) as total_value
            FROM product_inventory pi
            JOIN products p ON pi.product_id = p.id
            WHERE p.is_active = TRUE AND pi.quantity_in_stock > 0 {store_filter}
        """, tuple(params))
        total_value = float(row['total_value']) if row else 0.0

        details = self._fetch_all(f"""
            SELECT p.product_code, p.product_name, SUM(pi.quantity_in_stock) as qty,
                   p.buy_price, SUM(pi.quantity_in_stock * p.buy_price) as total_product_value
            FROM product_inventory pi
            JOIN products p ON pi.product_id = p.id
            WHERE p.is_active = TRUE AND pi.quantity_in_stock > 0 {store_filter}
            GROUP BY p.id, p.product_code, p.product_name, p.buy_price
            ORDER BY total_product_value DESC
        """, tuple(params))
        
        return {
            'total_value': total_value,
            'details': details
        }


    def get_total_paid_to_suppliers(self, store_id: int = None) -> float:
        """إجمالي المسدد للموردين من السجل المالي."""
        try:
            params = []
            store_filter = ""
            if store_id:
                store_filter = "AND store_id = %s"
                params.append(store_id)

            row = self._fetch_one(f"""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM treasury
                WHERE transaction_type = 'Out'
                  AND source_type IN ('Purchase', 'PurchasePayment', 'Settlement', 'Payment')
                  {store_filter}
            """, tuple(params))
            return float(row.get('total', 0)) if row else 0.0
        except Exception as e:
            err = str(e)
            if "source_type" in err or "reference_type" in err:
                try:
                    params = []
                    if store_id:
                        params.append(store_id)
                    row = self._fetch_one(f"""
                        SELECT COALESCE(SUM(amount), 0) as total
                        FROM treasury
                        WHERE transaction_type = 'Out'
                          AND reference_type IN ('Purchase', 'PurchasePayment', 'Settlement', 'Payment')
                          {('AND store_id = %s' if store_id else '')}
                    """, tuple(params))
                    return float(row.get('total', 0)) if row else 0.0
                except Exception as fallback_exc:
                    logger.error(f"Error fetching supplier payments (legacy fallback): {fallback_exc}")
                    return 0.0
            logger.error(f"Error fetching supplier payments: {e}")
            return 0.0

    def get_total_supplier_debt(self, store_id: int = None) -> float:
        """إجمالي مديونية الموردين الحالية."""
        try:
            if store_id:
                row = self._fetch_one("""
                    SELECT COALESCE(SUM(pi.remaining_amount), 0) as total_debt
                    FROM purchase_invoices pi
                    JOIN users u ON pi.created_by = u.id
                    WHERE u.store_id = %s
                      AND pi.remaining_amount > 0
                """, (store_id,))
            else:
                row = self._fetch_one("""
                    SELECT COALESCE(SUM(current_balance), 0) as total_debt
                    FROM suppliers
                    WHERE is_active = TRUE
                """)
            return float(row.get('total_debt', 0)) if row else 0.0
        except Exception as e:
            logger.error(f"Error fetching supplier debt: {e}")
            return 0.0

    def get_total_treasury_balance(self, store_id: int = None) -> float:
        """رصيد الخزينة الحالي تراكميًا."""
        try:
            query = """
                SELECT COALESCE(SUM(CASE WHEN transaction_type = 'In' THEN amount ELSE -amount END), 0) as balance
                FROM treasury
                WHERE 1=1
            """
            params = []
            if store_id:
                query += " AND store_id = %s"
                params.append(store_id)
            row = self._fetch_one(query, tuple(params))
            return float(row.get('balance', 0)) if row else 0.0
        except Exception as e:
            logger.error(f"Error fetching treasury balance: {e}")
            return 0.0

    def get_treasury_period_totals(self, date_from: str, date_to: str, store_id: int = None) -> Dict:
        """إجمالي الداخل والخارج من الخزينة خلال فترة محددة."""
        try:
            base = "FROM treasury WHERE DATE(created_at) BETWEEN %s AND %s"
            params = [date_from, date_to]
            if store_id:
                base += " AND store_id = %s"
                params.append(store_id)

            total_in = self._fetch_one(
                f"SELECT COALESCE(SUM(amount), 0) as total {base} AND transaction_type = 'In'",
                tuple(params),
            )
            total_out = self._fetch_one(
                f"SELECT COALESCE(SUM(amount), 0) as total {base} AND transaction_type = 'Out'",
                tuple(params),
            )
            in_value = float(total_in.get('total', 0)) if total_in else 0.0
            out_value = float(total_out.get('total', 0)) if total_out else 0.0
            return {'total_in': in_value, 'total_out': out_value, 'net': in_value - out_value}
        except Exception as e:
            logger.error(f"Error fetching treasury period totals: {e}")
            return {'total_in': 0.0, 'total_out': 0.0, 'net': 0.0}

    # ── Charts Data ────────────────────────────────────
    def get_daily_sales_trend(self, date_from: str, date_to: str, store_id: int = None) -> List[Dict]:
        """اتجاه المبيعات اليومية"""
        store_filter = "AND store_id = %s" if store_id else ""
        params = [date_from, date_to]
        if store_id:
            params.append(store_id)

        return self._fetch_all(f"""
            SELECT DATE(invoice_date) as date,
                   SUM(total_amount) as total_sales
            FROM invoices
            WHERE status = 'Completed'
            AND DATE(invoice_date) BETWEEN %s AND %s
            {store_filter}
            GROUP BY DATE(invoice_date)
            ORDER BY date
        """, tuple(params))

    def get_hourly_sales(self, date_from: str, date_to: str, store_id: int = None) -> List[Dict]:
        """توزيع المبيعات حسب الساعة"""
        store_filter = "AND store_id = %s" if store_id else ""
        params = [date_from, date_to]
        if store_id:
            params.append(store_id)

        return self._fetch_all(f"""
            SELECT HOUR(invoice_date) as hour,
                   SUM(total_amount) as total_sales,
                   COUNT(*) as invoice_count
            FROM invoices
            WHERE status = 'Completed'
            AND DATE(invoice_date) BETWEEN %s AND %s
            {store_filter}
            GROUP BY HOUR(invoice_date)
            ORDER BY hour
        """, tuple(params))

    def get_payment_method_distribution(self, date_from: str, date_to: str, store_id: int = None) -> List[Dict]:
        """توزيع طرق الدفع من مبالغ النقد والفيزا الفعلية."""
        store_filter = "AND store_id = %s" if store_id else ""
        params = [date_from, date_to]
        if store_id:
            params.append(store_id)

        row = self._fetch_one(f"""
            SELECT COALESCE(SUM(cash_amount), 0) as cash_total,
                   COALESCE(SUM(card_amount), 0) as card_total
            FROM invoices
            WHERE status = 'Completed'
            AND DATE(invoice_date) BETWEEN %s AND %s
            {store_filter} 
        """, tuple(params))
        if not row:
            return []
        result = []
        cash_total = float(row.get('cash_total', 0) or 0)
        card_total = float(row.get('card_total', 0) or 0)
        if cash_total > 0:
            result.append({'payment_method': 'Cash', 'total': cash_total, 'count': 0})
        if card_total > 0:
            result.append({'payment_method': 'Visa', 'total': card_total, 'count': 0})
        return result

    # ── Branch Performance ─────────────────────────────
    def get_sales_by_store(self, date_from: str, date_to: str, store_id: int = None) -> List[Dict]:
        """مبيعات كل فرع"""
        store_filter = "AND s.id = %s" if store_id is not None else ""
        params = [date_from, date_to]
        if store_id is not None:
            params.append(store_id)
        return self._fetch_all(f"""
            SELECT s.store_name,
                   COALESCE(SUM(i.total_amount), 0) as total_sales,
                   COUNT(i.id) as invoice_count
            FROM stores s
            LEFT JOIN invoices i ON s.id = i.store_id
                AND i.status = 'Completed'
                AND DATE(i.invoice_date) BETWEEN %s AND %s
            WHERE COALESCE(s.is_active, TRUE) = TRUE
              AND COALESCE(s.store_type, 'Branch') != 'GM'
              {store_filter}
            GROUP BY s.id, s.store_name
            ORDER BY total_sales DESC
        """, tuple(params))

    # ── Top Products ───────────────────────────────────
    def get_top_selling_products(self, limit: int, date_from: str, date_to: str,
                                  store_id: int = None) -> List[Dict]:
        """أكثر المنتجات مبيعاً"""
        store_filter = "AND i.store_id = %s" if store_id else ""
        params = [date_from, date_to]
        if store_id:
            params.append(store_id)
        params.append(limit)

        return self._fetch_all(f"""
            SELECT p.product_name,
                   SUM(ii.quantity) as total_qty,
                   SUM(ii.total_price) as total_revenue
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            JOIN products p ON ii.product_id = p.id
            WHERE i.status = 'Completed'
            AND DATE(i.invoice_date) BETWEEN %s AND %s
            {store_filter}
            GROUP BY p.id, p.product_name
            ORDER BY total_qty DESC
            LIMIT %s
        """, tuple(params))

    # ── Top Customers ──────────────────────────────────
    def get_top_customers(self, limit: int, date_from: str, date_to: str,
                           store_id: int = None) -> List[Dict]:
        """كبار العملاء مع المنتج المفضل كما في التطبيق القديم."""
        store_filter = "AND i.store_id = %s" if store_id else ""
        params = [date_from, date_to]
        if store_id:
            params.append(store_id)
        params.append(limit)

        return self._fetch_all(f"""
            SELECT i.customer_name,
                   i.customer_phone,
                   SUM(i.total_amount) as total_spent,
                   COUNT(i.id) as visit_count,
                   (
                       SELECT p.product_name
                       FROM invoice_items ii2
                       JOIN invoices i2 ON ii2.invoice_id = i2.id
                       JOIN products p ON ii2.product_id = p.id
                       WHERE (i2.customer_phone = i.customer_phone OR i2.customer_name = i.customer_name)
                       GROUP BY p.id, p.product_name
                       ORDER BY SUM(ii2.quantity) DESC
                       LIMIT 1
                   ) as favorite_product
            FROM invoices i
            WHERE i.status = 'Completed'
            AND DATE(i.invoice_date) BETWEEN %s AND %s
            AND i.customer_name IS NOT NULL AND i.customer_name != ''
            {store_filter}
            GROUP BY i.customer_name, i.customer_phone
            ORDER BY total_spent DESC
            LIMIT %s
        """, tuple(params))

    def get_most_returned_products(self, limit: int, date_from: str, date_to: str, store_id: int = None) -> List[Dict]:
        """الأكثر ارتجاعاً"""
        store_filter = "AND sr.store_id = %s" if store_id else ""
        params = [date_from, date_to]
        if store_id:
            params.append(store_id)
        params.append(limit)

        return self._fetch_all(f"""
            SELECT p.product_name as product,
                   SUM(ri.quantity) as returned_qty
            FROM return_items ri
            JOIN sales_returns sr ON ri.return_id = sr.id
            JOIN products p ON ri.product_id = p.id
            WHERE DATE(sr.return_date) BETWEEN %s AND %s
            {store_filter}
            GROUP BY p.id, p.product_name
            ORDER BY returned_qty DESC
            LIMIT %s
        """, tuple(params))

    def get_return_reasons(self, date_from: str, date_to: str, store_id: int = None) -> List[Dict]:
        """أسباب المرتجع"""
        store_filter = "AND store_id = %s" if store_id else ""
        params = [date_from, date_to]
        if store_id:
            params.append(store_id)

        return self._fetch_all(f"""
            SELECT CASE WHEN reason IS NULL OR reason = '' THEN 'غير محدد' ELSE reason END as reason,
                   COUNT(*) as reason_count
            FROM sales_returns
            WHERE DATE(return_date) BETWEEN %s AND %s
            {store_filter}
            GROUP BY CASE WHEN reason IS NULL OR reason = '' THEN 'غير محدد' ELSE reason END
            ORDER BY reason_count DESC
        """, tuple(params))

    def get_customer_retention_stats(self, date_from: str, date_to: str, store_id: int = None) -> Dict:
        """نسبة العملاء المتكررين داخل الفترة."""
        try:
            store_filter = "AND store_id = %s" if store_id else ""
            params = [date_from, date_to]
            if store_id:
                params.append(store_id)
            row = self._fetch_one(f"""
                SELECT
                    COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) as repeat_customers,
                    COALESCE(SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END), 0) as new_customers,
                    COUNT(*) as total_customers
                FROM (
                    SELECT customer_phone, COUNT(*) as order_count
                    FROM invoices
                    WHERE status = 'Completed'
                      AND DATE(invoice_date) BETWEEN %s AND %s
                      AND customer_phone IS NOT NULL AND customer_phone != ''
                      {store_filter}
                    GROUP BY customer_phone
                ) customer_orders
            """, tuple(params))
            if not row:
                return {'repeat_customers': 0, 'new_customers': 0, 'total_customers': 0, 'retention_rate': 0}
            total = int(row.get('total_customers', 0) or 0)
            repeat = int(row.get('repeat_customers', 0) or 0)
            new = int(row.get('new_customers', 0) or 0)
            return {
                'repeat_customers': repeat,
                'new_customers': new,
                'total_customers': total,
                'retention_rate': (repeat / total * 100) if total else 0,
            }
        except Exception as e:
            logger.error(f"Error fetching customer retention: {e}")
            return {'repeat_customers': 0, 'new_customers': 0, 'total_customers': 0, 'retention_rate': 0}

    def get_product_sales_report(self, date_from: str, date_to: str, store_id: int = None) -> List[Dict]:
        """تقرير مبيعات الأصناف اليومية لكل فرع."""
        store_filter = "AND i.store_id = %s" if store_id else ""
        params = [date_from, date_to]
        if store_id:
            params.append(store_id)
        return self._fetch_all(f"""
            SELECT p.product_code,
                   p.product_name,
                   s.store_name,
                   DATE(i.invoice_date) as sale_date,
                   SUM(ii.quantity) as total_qty,
                   SUM(ii.total_price) as total_revenue,
                   SUM(ii.quantity * COALESCE(p.buy_price, 0)) as total_cost
            FROM invoice_items ii
            JOIN products p ON ii.product_id = p.id
            JOIN invoices i ON ii.invoice_id = i.id
            JOIN stores s ON i.store_id = s.id
            WHERE i.status = 'Completed'
              AND DATE(i.invoice_date) BETWEEN %s AND %s
              {store_filter}
            GROUP BY p.id, p.product_code, p.product_name, s.id, s.store_name, DATE(i.invoice_date)
            ORDER BY sale_date DESC, total_qty DESC
        """, tuple(params))

    def get_supplier_stats(self, date_from: str, date_to: str) -> List[Dict]:
        """إحصائيات الموردين"""
        return self._fetch_all("""
            SELECT s.name as supplier_name,
                   COALESCE((
                       SELECT SUM(pi.total_amount)
                       FROM purchase_invoices pi
                       WHERE pi.supplier_id = s.id AND DATE(pi.invoice_date) BETWEEN %s AND %s
                   ), 0) as total_purchases,
                   COALESCE((
                       SELECT SUM(pi.total_amount)
                       FROM purchase_invoices pi
                       WHERE pi.supplier_id = s.id AND DATE(pi.invoice_date) BETWEEN %s AND %s
                   ), 0) + COALESCE((
                       SELECT SUM(l.amount)
                       FROM financial_ledger l
                       WHERE l.account_type = 'Supplier'
                         AND l.transaction_type = 'Debit'
                         AND l.account_id = s.id
                         AND DATE(l.transaction_date) BETWEEN %s AND %s
                   ), 0) as total_paid,
                   s.current_balance as remaining_balance,
                   COALESCE((
                       SELECT COUNT(*)
                       FROM purchase_invoices pi
                       WHERE pi.supplier_id = s.id AND DATE(pi.invoice_date) BETWEEN %s AND %s
                   ), 0) as invoice_count,
                   COALESCE((
                       SELECT SUM(pitems.quantity)
                       FROM purchase_items pitems
                       JOIN purchase_invoices pi ON pitems.purchase_invoice_id = pi.id
                       WHERE pi.supplier_id = s.id AND DATE(pi.invoice_date) BETWEEN %s AND %s
                   ), 0) as items_count
            FROM suppliers s
            WHERE s.is_active = TRUE
            ORDER BY total_purchases DESC
            LIMIT 50
        """, (
            date_from, date_to,
            date_from, date_to,
            date_from, date_to,
            date_from, date_to,
            date_from, date_to,
        ))

    # ── Stores List ────────────────────────────────────
    def get_all_stores(self) -> List[Dict]:
        """جلب جميع الفروع"""
        return self._fetch_all("""
            SELECT id, store_name
            FROM stores
            WHERE COALESCE(is_active, TRUE) = TRUE
              AND COALESCE(store_type, 'Branch') != 'GM'
            ORDER BY store_name
        """)

    # ── Discounts & Promotions Stats ───────────────────
    def _columns(self, table_name: str) -> set:
        try:
            rows = self._fetch_all(f"SHOW COLUMNS FROM `{table_name}`")
            return {row.get("Field") or row.get("field") for row in rows}
        except Exception:
            return set()

    def get_discounts_summary(self, date_from: str, date_to: str, store_id: int = None) -> Dict:
        try:
            store_filter = "AND i.store_id = %s" if store_id else ""
            params = [date_from, date_to]
            if store_id:
                params.append(store_id)
            
            invoice_cols = self._columns("invoices")
            has_company_disc = "company_discount_amount" in invoice_cols
            company_col_sql = "COALESCE(SUM(i.company_discount_amount), 0)" if has_company_disc else "0"

            row = self._fetch_one(f"""
                SELECT
                    COALESCE(SUM(ii.discount), 0) as items_discount,
                    {company_col_sql} as company_discount
                FROM invoices i
                LEFT JOIN invoice_items ii ON i.id = ii.invoice_id
                WHERE i.status = 'Completed'
                  AND DATE(i.invoice_date) BETWEEN %s AND %s
                  {store_filter}
            """, tuple(params))
            
            items_disc = float(row.get("items_discount", 0) or 0) if row else 0.0
            comp_disc = float(row.get("company_discount", 0) or 0) if row else 0.0
            
            return {
                "manual_discount": max(0.0, items_disc - comp_disc),
                "promo_discount": 0.0,
                "company_discount": comp_disc,
                "total_discounts": items_disc,
            }
        except Exception as e:
            logger.error(f"Error fetching discounts summary: {e}")
            return {
                "manual_discount": 0.0,
                "promo_discount": 0.0,
                "company_discount": 0.0,
                "total_discounts": 0.0,
            }

    def get_discount_breakdown_details(self, date_from: str, date_to: str, store_id: int = None) -> List[Dict]:
        try:
            store_filter = "AND i.store_id = %s" if store_id else ""
            params = [date_from, date_to]
            if store_id:
                params.append(store_id)

            breakdown = []
            summary = self.get_discounts_summary(date_from, date_to, store_id)
            total_items_disc = float(summary.get("total_discounts", 0) or 0.0)
            company_disc = float(summary.get("company_discount", 0) or 0.0)

            # 1. Company discounts by company name
            try:
                invoice_cols = self._columns("invoices")
                if "discount_company_name" in invoice_cols and "company_discount_amount" in invoice_cols:
                    comp_rows = self._fetch_all(f"""
                        SELECT discount_company_name as company_name, COALESCE(SUM(company_discount_amount), 0) as total
                        FROM invoices i
                        WHERE i.status = 'Completed'
                          AND DATE(i.invoice_date) BETWEEN %s AND %s
                          AND discount_company_name IS NOT NULL
                          AND discount_company_name != ''
                          {store_filter}
                        GROUP BY discount_company_name
                    """, tuple(params))
                    for r in comp_rows:
                        cname = r.get("company_name") or "شركة خصم"
                        amount = float(r.get("total", 0) or 0)
                        if amount > 0:
                            breakdown.append({
                                "discount_type": f"خصم شركة: {cname}",
                                "amount": amount,
                                "description": f"خصم شركة الخصم المعتمدة '{cname}'",
                            })
            except Exception as e:
                logger.debug(f"Company discount breakdown query info: {e}")

            remaining_items_disc = max(0.0, total_items_disc - company_disc)

            # 2. Promotions / Magazine offers from active promotions table
            try:
                active_promos = self._fetch_all("""
                    SELECT name FROM promotions
                    WHERE is_active = TRUE
                      AND (start_date <= %s AND end_date >= %s)
                    ORDER BY id DESC
                    LIMIT 3
                """, (date_to, date_from))

                if active_promos and remaining_items_disc > 0 and len(active_promos) == 0:
                    pass
                # If there is remaining item discount and active promotions, attribute promotional portion or keep manual
                # In this case, if remaining items disc is manual discount:
                if remaining_items_disc > 0:
                    breakdown.append({
                        "discount_type": "الخصم اليدوي المباشر",
                        "amount": round(remaining_items_disc, 2),
                        "description": "الخصومات المباشرة والمخصصة على الفواتير أو الأصناف",
                    })
            except Exception:
                if remaining_items_disc > 0:
                    breakdown.append({
                        "discount_type": "الخصم اليدوي المباشر",
                        "amount": round(remaining_items_disc, 2),
                        "description": "الخصومات المباشرة والمخصصة على الفواتير أو الأصناف",
                    })

            return breakdown or [{
                "discount_type": "لا توجد خصومات مسجلة",
                "amount": 0.0,
                "description": "لا توجد خصومات خلال هذه الفترة",
            }]
        except Exception as e:
            logger.error(f"Error fetching discount breakdown details: {e}")
            return []
