"""
Migration Runner - مشغل الهجرات
ضمان تطبيق هيكل قاعدة البيانات والهجرات عند بدء التشغيل
"""
import os
import logging
import re
from typing import List, Tuple
from repositories.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    يدير تشغيل ملفات SQL للهجرات والهيكل الأساسي
    """
    
    def __init__(self, db: DatabaseConnection = None):
        self.db = db or DatabaseConnection()
        self._migrations_table = 'schema_migrations'
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        """إنشاء جدول تتبع الهجرات المنفذة"""
        try:
            self.db.execute(f"""
                CREATE TABLE IF NOT EXISTS `{self._migrations_table}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version VARCHAR(100) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum VARCHAR(64),
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error creating migrations table: {e}")

    def get_executed_migrations(self) -> List[str]:
        """جلب قائمة الهجرات المنفذة مسبقاً"""
        try:
            results = self.db.fetch_all(
                f"SELECT `version` FROM `{self._migrations_table}` WHERE `success` = TRUE ORDER BY `version`"
            )
            return [row['version'] for row in results]
        except Exception as e:
            logger.error(f"Error getting executed migrations: {e}")
            return []

    def run_schema(self, schema_path: str = None) -> bool:
        """
        تشغيل ملف هيكل قاعدة البيانات الأساسي (database_schema.sql)
        """
        if schema_path is None:
            # البحث عن ملف الهيكل في مسارات محتملة
            possible_paths = [
                os.path.join(os.getcwd(), 'database_schema_complete.sql'),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database_schema_complete.sql'),
                os.path.join(os.getcwd(), 'database_schema.sql'),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database_schema.sql'),
                '/app/database_schema.sql',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    schema_path = path
                    break
        
        if not schema_path or not os.path.exists(schema_path):
            logger.warning(f"Schema file not found at {schema_path}")
            return False

        logger.info(f"Running base schema from: {schema_path}")
        return self._execute_sql_file(schema_path, 'base_schema')

    def run_migrations(self, migrations_dir: str = None) -> bool:
        """
        تشغيل ملفات الهجرة من مجلد migrations
        """
        if migrations_dir is None:
            possible_dirs = [
                os.path.join(os.getcwd(), 'migrations'),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations'),
                '/app/migrations',
            ]
            for dir_path in possible_dirs:
                if os.path.exists(dir_path):
                    migrations_dir = dir_path
                    break
        
        if not migrations_dir or not os.path.exists(migrations_dir):
            logger.info(f"Migrations directory not found at {migrations_dir}")
            return True  # ليس خطأً إذا لم يكن هناك مجلد هجرات

        logger.info(f"Running migrations from: {migrations_dir}")
        
        executed = set(self.get_executed_migrations())
        migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        
        all_success = True
        for filename in migration_files:
            version = self._extract_version(filename)
            if version in executed:
                logger.debug(f"Migration {filename} already executed, skipping")
                continue
            
            filepath = os.path.join(migrations_dir, filename)
            success = self._execute_sql_file(filepath, version, filename)
            all_success = all_success and success
        
        return all_success

    def _extract_version(self, filename: str) -> str:
        """استخراج رقم الإصدار من اسم الملف"""
        # يدعم تنسيقات مثل: 001_add_table.sql, v1.2.3_description.sql, 20240101_001.sql
        match = re.match(r'^(\d+|v?[\d\.]+)', filename)
        if match:
            return match.group(1)
        return filename  # fallback للاسم الكامل

    def _execute_sql_file(self, filepath: str, version: str, name: str = None) -> bool:
        """تنفيذ ملف SQL واحد مع تتبع في جدول الهجرات"""
        name = name or os.path.basename(filepath)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read migration file {filepath}: {e}")
            self._record_migration(version, name, False, str(e))
            return False

        # حساب checksum للتأكد من عدم تعديل الملف
        import hashlib
        checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()

        # التحقق من أن هذه النسخة لم تُنفذ بنجاح مسبقاً
        try:
            existing = self.db.fetch_one(
                f"SELECT `checksum`, `success` FROM `{self._migrations_table}` WHERE `version` = %s",
                (version,)
            )
            if existing and existing['success'] and existing['checksum'] == checksum:
                logger.debug(f"Migration {version} already executed with same checksum")
                return True
            elif existing and existing['success'] and existing['checksum'] != checksum:
                logger.warning(f"Migration {version} checksum changed! Re-executing...")
        except Exception:
            pass

        # تنفيذ محتوى الملف
        try:
            # تعطيل فحص المفاتيح الأجنبية مؤقتاً
            self.db.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            statements = self._parse_sql_statements(content)
            for stmt in statements:
                if stmt.strip():
                    try:
                        self.db.execute(stmt)
                    except Exception as stmt_err:
                        # تجاهل أخطاء "الجدول موجود بالفعل" و "الفهرس موجود"
                        if hasattr(stmt_err, 'errno') and stmt_err.errno in (1050, 1061, 1060, 1826):
                            logger.debug(f"Skipping known safe error: {stmt_err}")
                            continue
                        raise
            
            self.db.commit()
            self.db.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            self._record_migration(version, name, True, None, checksum)
            logger.info(f"✅ Migration executed: {name}")
            return True
            
        except Exception as e:
            self.db.execute("SET FOREIGN_KEY_CHECKS = 1")
            self.db.rollback()
            self._record_migration(version, name, False, str(e), checksum)
            logger.error(f"❌ Migration failed: {name} - {e}")
            return False

    def _parse_sql_statements(self, content: str) -> List[str]:
        """تحليل محتوى SQL إلى استعلامات منفصلة"""
        # إزالة التعليقات
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('--') or line.startswith('#'):
                continue
            lines.append(line)
        content = '\n'.join(lines)
        
        # تقسيم بالفاصلة المنقوطة مع احترام DELIMITER
        statements = []
        current = []
        delimiter = ';'
        
        for line in content.split('\n'):
            stripped = line.strip().upper()
            if stripped.startswith('DELIMITER'):
                parts = line.strip().split()
                if len(parts) > 1:
                    delimiter = parts[1]
                continue
            
            current.append(line)
            if line.strip().endswith(delimiter):
                stmt = '\n'.join(current).strip()
                if stmt.endswith(delimiter):
                    stmt = stmt[:-len(delimiter)].strip()
                if stmt:
                    statements.append(stmt)
                current = []
        
        # أي بقايا
        if current:
            stmt = '\n'.join(current).strip()
            if stmt:
                statements.append(stmt)
        
        return statements

    def _record_migration(
        self, 
        version: str, 
        name: str, 
        success: bool, 
        error: str = None,
        checksum: str = None
    ):
        """تسجيل نتيجة تنفيذ الهجرة"""
        try:
            self.db.execute(
                f"""
                INSERT INTO `{self._migrations_table}` 
                (`version`, `name`, `success`, `error_message`, `checksum`)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    `name` = VALUES(`name`),
                    `success` = VALUES(`success`),
                    `error_message` = VALUES(`error_message`),
                    `checksum` = VALUES(`checksum`),
                    `executed_at` = CURRENT_TIMESTAMP
                """,
                (version, name, success, error, checksum)
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to record migration {version}: {e}")

    def run_all(self, schema_path: str = None, migrations_dir: str = None) -> bool:
        """
        تشغيل الهيكل الأساسي ثم جميع الهجرات
        هذه الدالة تستدعى عند بدء التطبيق
        """
        logger.info("🚀 Starting database migration process...")
        
        # 0. إنشاء جدول تتبع الهجرات أولاً (قبل أي شيء)
        self._ensure_migrations_table()
        
        # 1. تشغيل الهيكل الأساسي
        schema_ok = self.run_schema(schema_path)
        if not schema_ok:
            logger.warning("Base schema execution had issues (may be already applied)")
        
        # 2. تشغيل الهجرات
        migrations_ok = self.run_migrations(migrations_dir)
        
        # 3. تطبيق الفهارس والأداء
        self._apply_performance_indexes()
        
        success = schema_ok or migrations_ok  # يكفي أن أحدهما ينجح (لأن الهيكل قد يكون مطبقاً مسبقاً)
        if success:
            logger.info("✅ Database migration process completed successfully")
        else:
            logger.error("❌ Database migration process failed")
        
        return success

    def _apply_performance_indexes(self):
        """تطبيق فهارس الأداء الإضافية"""
        indexes = [
            ("idx_product_code", "products", "product_code"),
            ("idx_barcode", "products", "barcode"),
            ("idx_inv_product", "product_inventory", "product_id"),
            ("idx_inv_store", "product_inventory", "store_id"),
            ("idx_invoice_date", "invoices", "invoice_date"),
            ("idx_invoice_status", "invoices", "status"),
            ("idx_cust_phone", "invoices", "customer_phone"),
            ("idx_sync_status", "sync_queue", "status"),
            ("idx_sync_table", "sync_queue", "table_name"),
        ]
        
        for idx_name, table, column in indexes:
            try:
                self.db.execute(f"CREATE INDEX IF NOT EXISTS `{idx_name}` ON `{table}`(`{column}`)")
            except Exception as e:
                # تجاهل إذا كان الفهرس موجوداً
                if hasattr(e, 'errno') and e.errno != 1061:
                    logger.debug(f"Index {idx_name} note: {e}")
        
        try:
            self.db.commit()
        except:
            pass


def run_migrations_on_startup(db: DatabaseConnection = None) -> bool:
    """
    دالة مساعدة لتشغيل الهجرات عند بدء التطبيق
    تستدعى من main.py قبل إظهار الواجهة
    """
    runner = MigrationRunner(db)
    return runner.run_all()


# للاختبار المباشر
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        db = DatabaseConnection()
        runner = MigrationRunner(db)
        success = runner.run_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Migration runner failed: {e}")
        sys.exit(1)
