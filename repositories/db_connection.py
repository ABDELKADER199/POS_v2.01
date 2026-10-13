"""
Database Connection Manager
إدارة الاتصال بقاعدة البيانات بشكل مركزي (Singleton)
"""
import os
import logging
import threading
import sys
import mysql.connector
import mysql.connector.locales.eng.client_error
from mysql.connector import pooling
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from the project directory
_project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_active_env_dir = _project_dir


def _candidate_env_dirs() -> list[str]:
    dirs: list[str] = []
    if getattr(sys, "frozen", False):
        dirs.append(os.path.dirname(sys.executable))
        bundle_dir = getattr(sys, "_MEIPASS", "")
        if bundle_dir:
            dirs.append(bundle_dir)
    dirs.extend([os.getcwd(), _project_dir])

    seen: set[str] = set()
    unique_dirs: list[str] = []
    for directory in dirs:
        if not directory:
            continue
        normalized = os.path.abspath(directory)
        if normalized not in seen:
            seen.add(normalized)
            unique_dirs.append(normalized)
    return unique_dirs


def _load_database_env() -> None:
    global _active_env_dir
    for directory in _candidate_env_dirs():
        env_path = os.path.join(directory, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)
            _active_env_dir = directory
            logger.info("Loaded database environment from: %s", env_path)
            return
    logger.warning("No .env file found for database configuration")


_load_database_env()


class DatabaseConnection:
    """
    إدارة الاتصال بقاعدة البيانات MySQL - يعمل كـ Singleton.
    جميع المستودعات (Repositories) تستخدم هذا الكائن للوصول لقاعدة البيانات.
    """
    _instance = None
    _lock = threading.Lock()
    _pool = None
    _HIDDEN_VALUES = {"", "HIDDEN", "hidden", "None", "none", "NULL", "null"}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def _deobfuscate(self, token: str, key: str = "") -> str:
        """استعادة النص الأصلي من الرمز المشفر"""
        if not token: return ""
        import base64
        try:
            decoded = base64.b64decode(token.encode('utf-8')).decode('utf-8')
            result = []
            for i in range(len(decoded)):
                char = decoded[i]
                key_char = key[i % len(key)]
                result.append(chr(ord(char) ^ ord(key_char)))
            return "".join(result)
        except Exception:
            return token

    @classmethod
    def _env(cls, key: str, default: str = "") -> str:
        value = os.getenv(key)
        if value is None:
            return default
        value = value.strip()
        return default if value in cls._HIDDEN_VALUES else value

    @classmethod
    def _env_int(cls, key: str, default: int) -> int:
        try:
            return int(cls._env(key, str(default)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _resolve_env_path(path: str) -> str:
        if not path or os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(_active_env_dir, path))

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        import threading
        self._local = threading.local()
        
        # 1. حاول من ملف .env
        env_host = self._env('POS_DB_HOST')
        if env_host:
            self.host = env_host
            self.port = self._env_int('POS_DB_PORT', 3306)
            self.user = self._env('POS_DB_USER', 'root')
            self.password = self._env('POS_DB_PASSWORD', '')
            self.database = self._env('POS_DB_NAME', 'inventory_pos')
            self.ssl_ca = self._resolve_env_path(self._env('POS_DB_SSL_CA', ''))
        else:
            # 2. الإعدادات المحلية المحمية للإنتاج
            # It seems the app relies on working locally and synchronizing periodically!
            logger.warning("POS_DB_HOST is not configured; using local database defaults without embedded secrets")
            self.host = 'localhost'
            self.user = self._env('POS_DB_USER', 'root')
            self.password = self._env('POS_DB_PASSWORD', '')
            self.database = self._env('POS_DB_NAME', 'stocks')
            self.port = 3306
            self.ssl_ca = self._resolve_env_path(self._env('POS_DB_SSL_CA', ''))

    @property
    def conn(self):
        if not hasattr(self, '_local'):
            import threading
            self._local = threading.local()
        if not hasattr(self._local, 'conn'):
            self._connect()
        return self._local.conn
        
    @property
    def cursor(self):
        if not hasattr(self, '_local'):
            import threading
            self._local = threading.local()
        if not hasattr(self._local, 'cursor'):
            self._connect()
        return self._local.cursor

    def _connect(self):
        """إنشاء اتصال بقاعدة البيانات"""
        try:
            conn_kwargs = {
                'host': self.host,
                'port': self.port,
                'user': self.user,
                'password': self.password,
                'database': self.database,
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'autocommit': False,
                'connection_timeout': 30,
                'read_timeout': 300,
                'write_timeout': 300,
                'buffered': True,
                'use_pure': True
            }
            if self.port == 4000: # Usually TiDB requires SSL
                conn_kwargs['ssl_verify_identity'] = True
                conn_kwargs['ssl_ca'] = self.ssl_ca
                
            self._local.conn = mysql.connector.connect(**conn_kwargs)
            self._local.cursor = self._local.conn.cursor(dictionary=True, buffered=True)
            logger.info(f"✅ Connected to database: {self.database}@{self.host}")
        except mysql.connector.Error as err:
            logger.error(f"❌ Database connection failed: {err}")
            raise

    def ensure_connection(self):
        """التأكد من أن الاتصال نشط وإعادة الاتصال إذا لزم الأمر"""
        try:
            if not hasattr(self, '_local'):
                import threading
                self._local = threading.local()
            if not hasattr(self._local, 'conn') or getattr(self._local, 'conn') is None or not getattr(self._local, 'conn').is_connected():
                self._connect()
                return
            self._local.conn.ping(reconnect=True, attempts=3, delay=1)
        except Exception:
            self._connect()

    def execute(self, query: str, params: tuple = None) -> 'cursor':
        """تنفيذ استعلام مع التأكد من الاتصال"""
        self.ensure_connection()
        self.cursor.execute(query, params)
        return self.cursor

    def execute_many(self, query: str, params_list: list):
        """تنفيذ استعلام دفعة واحدة"""
        self.ensure_connection()
        self.cursor.executemany(query, params_list)

    def fetch_one(self, query: str, params: tuple = None) -> dict:
        """جلب سجل واحد"""
        self.execute(query, params)
        return self.cursor.fetchone()

    def fetch_all(self, query: str, params: tuple = None) -> list:
        """جلب جميع السجلات"""
        self.execute(query, params)
        return self.cursor.fetchall()

    def commit(self):
        """حفظ التغييرات"""
        self.conn.commit()

    def rollback(self):
        """التراجع عن التغييرات"""
        try:
            self.conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            if hasattr(self, '_local'):
                if hasattr(self._local, 'cursor') and self._local.cursor:
                    self._local.cursor.close()
                if hasattr(self._local, 'conn') and self._local.conn and self._local.conn.is_connected():
                    self._local.conn.close()
                self._local.cursor = None
                self._local.conn = None
        except Exception:
            pass

    @property
    def last_insert_id(self) -> int:
        """آخر ID تم إدخاله"""
        return self.cursor.lastrowid

    @property
    def rows_affected(self) -> int:
        """عدد الصفوف المتأثرة"""
        return self.cursor.rowcount
