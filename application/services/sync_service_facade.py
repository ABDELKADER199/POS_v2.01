"""
Sync Service Facade - واجهة خدمة المزامنة
طبقة التطبيق التي تنسق بين المستودعات وتنفيذ عمليات المزامنة
"""
import logging
import threading
import time
import json
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime

from repositories.sync_queue_repo import SyncQueueRepository, get_sync_queue_repo
from repositories.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)


class SyncServiceFacade:
    """
    خدمة المزامنة - تدير مزامنة البيانات بين القاعدة المحلية والسحابية
    تدعم: المزامنة التدريجية، الرفع الشامل، المزامنة في الخلفية
    """

    # ترتيب أولويات الجداول لضمان سلامة المفاتيح الخارجية
    TABLE_PRIORITY = {
        'roles': 1, 'stores': 1,
        'users': 2,
        'categories': 3, 'suppliers': 3, 'customers': 3,
        'products': 4,
        'product_inventory': 5, 'price_history': 5, 'promotions': 5,
        'invoices': 6, 'purchase_invoices': 6, 'orders': 6,
        'warehouse_transfers': 6, 'sales_returns': 6,
        'invoice_items': 7, 'purchase_items': 7, 'order_items': 7,
        'transfer_items': 7, 'return_items': 7,
        'expenses': 8, 'treasury': 8, 'financial_ledger': 8,
        'drawer_logs': 8, 'drawer_closing_details': 8,
        'authorized_devices': 9, 'system_settings': 9, 'audit_logs': 9,
        'payments': 8, 'settlements': 8,
    }

    def __init__(self, local_db: DatabaseConnection = None):
        self.local_db = local_db or DatabaseConnection()
        self.sync_repo = get_sync_queue_repo()
        self._cloud_db: Optional[DatabaseConnection] = None
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_syncing = False

    def is_cloud_configured(self) -> bool:
        """التحقق من تفعيل المزامنة السحابية بشكل صريح."""
        import os
        enabled = os.getenv("POS_ENABLE_CLOUD_SYNC", "false").strip().lower()
        if enabled not in {"1", "true", "yes", "on"}:
            return False

        explicit_cloud = os.getenv('POS_CLOUD_DB_HOST')
        if explicit_cloud:
            return True
            
        # Fallback to check if the main DB is remote
        cloud_host = self.local_db.host
        return (
            bool(cloud_host) and 
            cloud_host not in ['localhost', '127.0.0.1', 'HIDDEN', '']
        )

    def _get_cloud_connection(self) -> Optional[DatabaseConnection]:
        """الحصول على اتصال بقاعدة البيانات السحابية"""
        if self._cloud_db is None and self.is_cloud_configured():
            try:
                import os
                cloud_host = os.getenv('POS_CLOUD_DB_HOST') or os.getenv('POS_DB_HOST')
                if cloud_host:
                    from repositories.db_connection import DatabaseConnection
                    self._cloud_db = self._create_cloud_connection()
            except Exception as e:
                logger.error(f"Failed to create cloud connection: {e}")
        return self._cloud_db

    def _create_cloud_connection(self) -> Optional[DatabaseConnection]:
        """إنشاء اتصال بقاعدة البيانات السحابية"""
        try:
            import os
            import mysql.connector
            from repositories.db_connection import DatabaseConnection
            
            # Create a completely separate instance bypassing the singleton logic
            cloud_db = object.__new__(DatabaseConnection)
            cloud_db._initialized = True
            
            cloud_db.host = os.getenv('POS_CLOUD_DB_HOST', os.getenv('POS_DB_HOST', ''))
            cloud_db.port = int(os.getenv('POS_CLOUD_DB_PORT', os.getenv('POS_DB_PORT', '3306')))
            cloud_db.user = os.getenv('POS_CLOUD_DB_USER', os.getenv('POS_DB_USER', 'root'))
            cloud_db.password = os.getenv('POS_CLOUD_DB_PASSWORD', os.getenv('POS_DB_PASSWORD', ''))
            cloud_db.database = os.getenv('POS_CLOUD_DB_NAME', os.getenv('POS_DB_NAME', 'inventory_pos'))
            cloud_db.ssl_ca = os.getenv('POS_CLOUD_DB_SSL_CA', os.getenv('POS_DB_SSL_CA', ''))
            
            if cloud_db.port == 4000:  # TiDB usually requires SSL
                import ssl
                cloud_db.ssl_ca = cloud_db.ssl_ca or ''
            
            cloud_db._connect()
            logger.info(f"☁️ Connected to cloud database: {cloud_db.database}@{cloud_db.host}")
            return cloud_db
        except Exception as e:
            logger.error(f"Failed to connect to cloud database: {e}")
            return None

    def sync_incremental(
        self, 
        progress_callback: Optional[Callable[[int, str], None]] = None,
        stop_event: Optional[threading.Event] = None,
        batch_limit: int = 1000
    ) -> Dict[str, Any]:
        """
        مزامنة تدريجية للعمليات المعلقة في الطابور
        
        Args:
            progress_callback: دالة استدعاء للتقدم (percentage, message)
            stop_event: حدث للإيقاف
            batch_limit: الحد الأقصى للعمليات في كل جولة
            
        Returns:
            قاموس بالنتيجة: success_count, fail_count, total
        """
        if self._is_syncing:
            return {'success': 0, 'failed': 0, 'total': 0, 'error': 'Sync already in progress'}
        
        if not self.is_cloud_configured() and self._cloud_db is None:
            return {'success': 0, 'failed': 0, 'total': 0, 'error': 'Cloud not configured'}

        cloud_db = self._get_cloud_connection()
        if not cloud_db:
            return {'success': 0, 'failed': 0, 'total': 0, 'error': 'Failed to connect to cloud'}

        self._is_syncing = True
        stop_event = stop_event or self._stop_event
        success_count = 0
        fail_count = 0

        try:
            # جلب العمليات المعلقة
            pending = self.sync_repo.get_pending(limit=batch_limit)
            total = len(pending)
            
            if total == 0:
                if progress_callback:
                    progress_callback(100, "لا توجد بيانات للمزامنة")
                return {'success': 0, 'failed': 0, 'total': 0, 'message': 'No pending syncs'}

            logger.info(f"Starting incremental sync: {total} operations")
            
            # التأكد من وجود الجداول في السحاب
            self._ensure_cloud_schema(cloud_db)

            # تعطيل فحص المفاتيح الخارجية للسرعة
            cloud_db.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            try:
                for i, item in enumerate(pending):
                    # التحقق من طلب الإيقاف
                    if stop_event.is_set():
                        logger.warning("Sync stopped by user request")
                        break

                    sync_id = item['id']
                    table = item['table_name']
                    action = item['action_type']
                    data = json.loads(item['data_json'])

                    if progress_callback:
                        progress_callback(
                            int((i / total) * 100), 
                            f"مزامنة {table} ({i+1}/{total})..."
                        )

                    try:
                        success = self._execute_sync_operation(cloud_db, table, action, data)
                        if success:
                            self.sync_repo.mark_synced(sync_id)
                            success_count += 1
                        else:
                            self.sync_repo.mark_failed(sync_id, "Sync operation returned False")
                            fail_count += 1
                    except Exception as e:
                        self.sync_repo.mark_failed(sync_id, str(e))
                        fail_count += 1
                        logger.error(f"Error syncing {table} #{sync_id}: {e}")

            finally:
                # إعادة تفعيل فحص المفاتيح الخارجية
                try:
                    cloud_db.execute("SET FOREIGN_KEY_CHECKS = 1")
                except:
                    pass

            if progress_callback:
                progress_callback(100, f"اكتملت المزامنة: {success_count} نجاح، {fail_count} فشل")

            logger.info(f"Incremental sync complete: {success_count}/{total} success, {fail_count} failed")
            return {
                'success': success_count, 
                'failed': fail_count, 
                'total': total,
                'completed': not stop_event.is_set()
            }

        except Exception as e:
            logger.error(f"Incremental sync error: {e}")
            return {'success': success_count, 'failed': fail_count, 'total': total, 'error': str(e)}
        finally:
            self._is_syncing = False

    def _execute_sync_operation(
        self, 
        cloud_db: DatabaseConnection, 
        table: str, 
        action: str, 
        data: Dict
    ) -> bool:
        """تنفيذ عملية مزامنة واحدة"""
        action = action.upper()
        
        if action == 'INSERT':
            return self._sync_insert(cloud_db, table, data)
        elif action == 'UPDATE':
            return self._sync_update(cloud_db, table, data)
        elif action == 'DELETE':
            return self._sync_delete(cloud_db, table, data)
        else:
            logger.warning(f"Unknown sync action: {action}")
            return False

    def _sync_insert(self, cloud_db: DatabaseConnection, table: str, data: Dict) -> bool:
        """مزامنة عملية إدراج"""
        try:
            # حل المعرفات للجداول التابعة
            data = self._resolve_foreign_keys(cloud_db, table, data)
            
            # التحقق من الأعمدة الموجودة
            columns = self._get_valid_columns(cloud_db, table, data)
            if not columns:
                return True
            
            col_names = ", ".join([f"`{c}`" for c in columns])
            placeholders = ", ".join(["%s"] * len(columns))
            update_clause = ", ".join([f"`{c}` = VALUES(`{c}`)" for c in columns if c != 'id'])
            
            query = f"INSERT INTO `{table}` ({col_names}) VALUES ({placeholders})"
            if update_clause:
                query += f" ON DUPLICATE KEY UPDATE {update_clause}"
            
            values = [data.get(col) for col in columns]
            cloud_db.execute(query, tuple(values))
            cloud_db.commit()
            return True
        except Exception as e:
            logger.error(f"Sync insert error for {table}: {e}")
            cloud_db.rollback()
            return False

    def _sync_update(self, cloud_db: DatabaseConnection, table: str, data: Dict) -> bool:
        """مزامنة عملية تحديث"""
        try:
            # نحتاج لمعرف السجل
            record_id = data.get('id')
            if not record_id:
                logger.warning(f"Update without ID for {table}")
                return False
            
            data = self._resolve_foreign_keys(cloud_db, table, data)
            columns = self._get_valid_columns(cloud_db, table, data)
            
            # استبعاد id من التحديث
            update_cols = [c for c in columns if c != 'id']
            if not update_cols:
                return True
            
            set_clause = ", ".join([f"`{c}` = %s" for c in update_cols])
            values = [data.get(col) for col in update_cols] + [record_id]
            
            query = f"UPDATE `{table}` SET {set_clause} WHERE `id` = %s"
            cloud_db.execute(query, tuple(values))
            cloud_db.commit()
            return True
        except Exception as e:
            logger.error(f"Sync update error for {table}: {e}")
            cloud_db.rollback()
            return False

    def _sync_delete(self, cloud_db: DatabaseConnection, table: str, data: Dict) -> bool:
        """مزامنة عملية حذف"""
        try:
            record_id = data.get('id')
            if not record_id:
                logger.warning(f"Delete without ID for {table}")
                return False
            
            query = f"DELETE FROM `{table}` WHERE `id` = %s"
            cloud_db.execute(query, (record_id,))
            cloud_db.commit()
            return True
        except Exception as e:
            logger.error(f"Sync delete error for {table}: {e}")
            cloud_db.rollback()
            return False

    def _resolve_foreign_keys(self, cloud_db: DatabaseConnection, table: str, data: Dict) -> Dict:
        """حل المعرفات الخارجية (product_code -> product_id, invoice_number -> invoice_id, إلخ)"""
        data = dict(data)  # نسخة قابلة للتعديل
        
        child_tables = [
            'invoice_items', 'product_inventory', 'purchase_items',
            'order_items', 'transfer_items', 'return_items', 'price_history'
        ]
        
        if table in child_tables:
            # حل product_code -> product_id
            p_code = data.get('product_code')
            if p_code:
                try:
                    result = cloud_db.fetch_one(
                        "SELECT `id` FROM `products` WHERE `product_code` = %s", 
                        (p_code,)
                    )
                    if result:
                        data['product_id'] = result['id']
                    else:
                        logger.warning(f"Product {p_code} not found in cloud for {table}")
                except Exception as e:
                    logger.debug(f"Could not resolve product_code {p_code}: {e}")
            
            # حل invoice_number -> invoice_id
            inv_num = data.get('invoice_number')
            if inv_num and table in ['invoice_items', 'return_items']:
                try:
                    result = cloud_db.fetch_one(
                        "SELECT `id` FROM `invoices` WHERE `invoice_number` = %s", 
                        (inv_num,)
                    )
                    if result:
                        data['invoice_id'] = result['id']
                except Exception as e:
                    logger.debug(f"Could not resolve invoice_number {inv_num}: {e}")

        if table == 'products':
            # حل category_name -> category_id
            cat_name = data.get('category_name')
            if cat_name:
                try:
                    result = cloud_db.fetch_one(
                        "SELECT `id` FROM `categories` WHERE `category_name` = %s", 
                        (cat_name,)
                    )
                    if result:
                        data['category_id'] = result['id']
                except Exception as e:
                    logger.debug(f"Could not resolve category_name {cat_name}: {e}")

        return data

    def _get_valid_columns(self, cloud_db: DatabaseConnection, table: str, data: Dict) -> List[str]:
        """الحصول على الأعمدة الصالحة الموجودة في الجدول السحابي"""
        try:
            cloud_db.execute(f"DESCRIBE `{table}`")
            cloud_columns = {row['Field'] for row in cloud_db.cursor.fetchall()}
            return [col for col in data.keys() if col in cloud_columns]
        except Exception as e:
            logger.warning(f"Could not describe table {table}: {e}")
            return list(data.keys())

    def _ensure_cloud_schema(self, cloud_db: DatabaseConnection):
        """التأكد من وجود الجداول في السحاب (تشغيل migrations إذا لزم الأمر)"""
        # في الإصدار الحالي، نفترض أن الجداول موجودة
        # يمكن إضافة منطق إنشاء الجداول تلقائياً لاحقاً
        pass

    # ============================================================
    # Bulk Upload (Direct Upload) - رفع شامل وسريع
    # ============================================================

    def bulk_upload_all(
        self,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        stop_event: Optional[threading.Event] = None,
        chunk_size: int = 2000
    ) -> Dict[str, Any]:
        """
        رفع مباشر لجميع البيانات إلى السحاب بدون استخدام الطابور
        مناسب للرفع الأول أو إعادة المزامنة الكاملة
        """
        if not self.is_cloud_configured():
            return {'success': False, 'error': 'Cloud not configured'}

        cloud_db = self._get_cloud_connection()
        if not cloud_db:
            return {'success': False, 'error': 'Failed to connect to cloud'}

        stop_event = stop_event or self._stop_event
        total_records = 0
        tables_processed = 0

        # ترتيب الجداول حسب التبعيات
        table_queries = self._get_ordered_table_queries()

        try:
            # تعطيل القيود للسرعة القصوى
            cloud_db.execute("SET FOREIGN_KEY_CHECKS = 0")
            cloud_db.execute("SET UNIQUE_CHECKS = 0")
            cloud_db.execute("SET AUTOCOMMIT = 0")

            for table_idx, (table_name, query) in enumerate(table_queries):
                if stop_event.is_set():
                    break

                if progress_callback:
                    progress_callback(
                        int((table_idx / len(table_queries)) * 100),
                        f"رفع {table_name} ({table_idx+1}/{len(table_queries)})..."
                    )

                try:
                    # قراءة البيانات من القاعدة المحلية
                    self.local_db.execute(query)
                    rows = self.local_db.cursor.fetchall()
                except Exception as e:
                    logger.warning(f"Skipping {table_name}: {e}")
                    continue

                if not rows:
                    logger.info(f"⏭️ {table_name}: empty")
                    continue

                # الحصول على أعمدة الجدول في السحاب
                try:
                    cloud_db.execute(f"DESCRIBE `{table_name}`")
                    cloud_columns = {row['Field'] for row in cloud_db.cursor.fetchall()}
                except Exception:
                    # محاولة إنشاء الجدول
                    if not self._create_table_in_cloud(cloud_db, table_name):
                        continue
                    cloud_db.execute(f"DESCRIBE `{table_name}`")
                    cloud_columns = {row['Field'] for row in cloud_db.cursor.fetchall()}

                # تنظيف الأعمدة
                first_row = dict(rows[0])
                valid_columns = [col for col in first_row.keys() if col in cloud_columns]
                if not valid_columns:
                    continue

                # بناء استعلام INSERT
                col_names = ", ".join([f"`{c}`" for c in valid_columns])
                placeholders = ", ".join(["%s"] * len(valid_columns))
                update_parts = ", ".join([f"`{c}` = VALUES(`{c}`)" for c in valid_columns if c != 'id'])
                
                insert_query = f"INSERT INTO `{table_name}` ({col_names}) VALUES ({placeholders})"
                if update_parts:
                    insert_query += f" ON DUPLICATE KEY UPDATE {update_parts}"

                # رفع البيانات بدفعات
                row_count = len(rows)
                for chunk_start in range(0, row_count, chunk_size):
                    if stop_event.is_set():
                        break
                    
                    chunk_end = min(chunk_start + chunk_size, row_count)
                    chunk = rows[chunk_start:chunk_end]
                    
                    values_batch = []
                    for row in chunk:
                        row_dict = dict(row)
                        values_batch.append(tuple(row_dict.get(col) for col in valid_columns))
                    
                    try:
                        cloud_db.execute_many(insert_query, values_batch)
                        cloud_db.commit()
                    except Exception as e:
                        logger.error(f"Error uploading {table_name} chunk: {e}")
                        cloud_db.rollback()
                        continue
                    
                    total_records += len(chunk)
                    
                    if progress_callback:
                        progress_callback(
                            int((table_idx / len(table_queries)) * 100),
                            f"رفع {table_name}: {chunk_end}/{row_count} ({total_records} إجمالي)..."
                        )

                tables_processed += 1
                logger.info(f"✅ {table_name}: uploaded {row_count} records")

            # إعادة تفعيل القيود
            cloud_db.execute("SET FOREIGN_KEY_CHECKS = 1")
            cloud_db.execute("SET UNIQUE_CHECKS = 1")
            cloud_db.execute("SET AUTOCOMMIT = 1")

            if progress_callback:
                progress_callback(100, f"✅ اكتمل الرفع الشامل: {total_records} سجل من {tables_processed} جدول")

            return {
                'success': True, 
                'total_records': total_records, 
                'tables_processed': tables_processed
            }

        except Exception as e:
            logger.error(f"Bulk upload error: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            try:
                cloud_db.execute("SET FOREIGN_KEY_CHECKS = 1")
                cloud_db.execute("SET UNIQUE_CHECKS = 1")
                cloud_db.execute("SET AUTOCOMMIT = 1")
            except:
                pass

    def _get_ordered_table_queries(self) -> List[tuple]:
        """استعلامات الجداول مرتبة حسب التبعيات"""
        return [
            ('roles', "SELECT * FROM `roles`"),
            ('stores', "SELECT * FROM `stores`"),
            ('users', "SELECT * FROM `users`"),
            ('categories', "SELECT * FROM `categories`"),
            ('suppliers', "SELECT * FROM `suppliers`"),
            ('customers', "SELECT * FROM `customers`"),
            ('products', "SELECT * FROM `products`"),
            ('product_inventory', "SELECT * FROM `product_inventory`"),
            ('price_history', "SELECT * FROM `price_history`"),
            ('promotions', "SELECT * FROM `promotions`"),
            ('invoices', "SELECT * FROM `invoices`"),
            ('invoice_items', "SELECT * FROM `invoice_items`"),
            ('sales_returns', "SELECT * FROM `sales_returns`"),
            ('return_items', "SELECT * FROM `return_items`"),
            ('purchase_invoices', "SELECT * FROM `purchase_invoices`"),
            ('purchase_items', "SELECT * FROM `purchase_items`"),
            ('orders', "SELECT * FROM `orders`"),
            ('order_items', "SELECT * FROM `order_items`"),
            ('warehouse_transfers', "SELECT * FROM `warehouse_transfers`"),
            ('transfer_items', "SELECT * FROM `transfer_items`"),
            ('expenses', "SELECT * FROM `expenses`"),
            ('treasury', "SELECT * FROM `treasury`"),
            ('financial_ledger', "SELECT * FROM `financial_ledger`"),
            ('drawer_logs', "SELECT * FROM `drawer_logs`"),
            ('drawer_closing_details', "SELECT * FROM `drawer_closing_details`"),
            ('authorized_devices', "SELECT * FROM `authorized_devices`"),
            ('system_settings', "SELECT * FROM `system_settings`"),
            ('audit_logs', "SELECT * FROM `audit_logs`"),
        ]

    def _create_table_in_cloud(self, cloud_db: DatabaseConnection, table_name: str) -> bool:
        """إنشاء جدول في السحاب من خلال نسخه من القاعدة المحلية"""
        try:
            self.local_db.execute(f"SHOW CREATE TABLE `{table_name}`")
            result = self.local_db.cursor.fetchone()
            if result:
                create_sql = result.get('Create Table') or result.get(list(result.keys())[1])
                cloud_db.execute(create_sql)
                cloud_db.commit()
                logger.info(f"✅ Created table {table_name} in cloud")
                return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name} in cloud: {e}")
        return False

    # ============================================================
    # Background Sync
    # ============================================================

    def start_background_sync(self, interval_seconds: int = 600):
        """بدء المزامنة التلقائية في الخلفية"""
        if self._sync_thread and self._sync_thread.is_alive():
            logger.warning("Background sync already running")
            return

        self._stop_event.clear()
        self._sync_thread = threading.Thread(
            target=self._background_sync_loop,
            args=(interval_seconds,),
            daemon=True,
            name="BackgroundSync"
        )
        self._sync_thread.start()
        logger.info(f"🔄 Background sync started (interval: {interval_seconds}s)")

    def stop_background_sync(self):
        """إيقاف المزامنة في الخلفية"""
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        logger.info("🛑 Background sync stopped")

    def _background_sync_loop(self, interval: int):
        """حلقة المزامنة في الخلفية"""
        while not self._stop_event.is_set():
            try:
                logger.info("🔄 Starting background sync cycle...")
                result = self.sync_incremental(stop_event=self._stop_event)
                logger.info(f"Background sync result: {result}")
            except Exception as e:
                logger.error(f"Background sync error: {e}")
            
            # الانتظار للفترة المحددة أو حتى الإيقاف
            if self._stop_event.wait(interval):
                break

    @property
    def is_syncing(self) -> bool:
        return self._is_syncing

    def get_sync_status(self) -> Dict[str, Any]:
        """الحصول على حالة المزامنة"""
        stats = self.sync_repo.get_stats()
        return {
            'is_syncing': self._is_syncing,
            'cloud_configured': self.is_cloud_configured(),
            'queue_stats': stats,
            'background_thread_alive': self._sync_thread.is_alive() if self._sync_thread else False
        }


# Singleton instance
_sync_service = None

def get_sync_service(local_db: DatabaseConnection = None) -> SyncServiceFacade:
    """الحصول على نسخة وحيدة من خدمة المزامنة"""
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncServiceFacade(local_db)
    return _sync_service
