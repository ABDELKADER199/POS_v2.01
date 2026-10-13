"""
Backup Service Facade - واجهة خدمة النسخ الاحتياطي
طبقة الأعمال التي تنسق عمليات النسخ الاحتياطي
"""
import logging
import os
import subprocess
import threading
import time
from datetime import datetime, date
from typing import Dict, Optional, List, Tuple, Callable

from repositories.backup_repo import BackupRepository, get_backup_repository
from repositories.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)


class BackupServiceFacade:
    """
    خدمة النسخ الاحتياطي - تدير عمليات النسخ الاحتياطي التلقائي واليدوي
    """

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or DatabaseConnection()
        self.repo = get_backup_repository()
        self._backup_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_backing_up = False

    # ============================================================
    # Backup Execution
    # ============================================================

    def execute_backup(
        self,
        backup_type: str = 'manual',
        custom_dir: str = None,
        created_by: int = 1,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[bool, str]:
        """
        تنفيذ نسخة احتياطية
        
        Args:
            backup_type: نوع النسخة ('manual', 'auto', 'scheduled')
            custom_dir: مجلد مخصص للنسخ
            created_by: معرف المستخدم المنشئ
            progress_callback: دالة استدعاء للتقدم
            
        Returns:
            (success, message_or_path)
        """
        if self._is_backing_up:
            return False, "Backup already in progress"

        self._is_backing_up = True

        try:
            # تحديد المجلد
            if custom_dir:
                backup_dir = custom_dir
            else:
                backup_dir = self.repo.get_backup_dir()

            # إنشاء المجلد إذا لم يكن موجوداً
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)

            # اسم الملف
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"pos_backup_{timestamp}.sql"
            filepath = os.path.join(backup_dir, filename)

            # تسجيل بداية العملية
            backup_id = self.repo.record_backup_start(filename, filepath, backup_type, created_by)

            if progress_callback:
                progress_callback(10, "جاري التحضير للنسخ الاحتياطي...")

            # الحصول على مسار mysqldump
            mysqldump_path = self.repo.get_mysqldump_path()
            
            if not os.path.exists(mysqldump_path):
                # محاولة البحث في مسارات شائعة
                mysqldump_path = self._find_mysqldump()
                if not mysqldump_path:
                    self.repo.record_backup_complete(backup_id, False, 0, "mysqldump not found")
                    return False, "mysqldump executable not found. Please configure path in settings."

            if progress_callback:
                progress_callback(30, "جاري تنفيذ النسخ الاحتياطي...")

            # بناء أمر mysqldump
            command = [
                mysqldump_path,
                f"--host={self.db.host}",
                f"--user={self.db.user}",
                f"--port={self.db.port}",
                self.db.database,
                f"--result-file={filepath}",
                "--single-transaction",
                "--routines",
                "--triggers",
                "--events",
                "--hex-blob",
                "--quick",
                "--lock-tables=false"
            ]
            
            env = os.environ.copy()
            if self.db.password:
                env['MYSQL_PWD'] = self.db.password

            if progress_callback:
                progress_callback(50, "جاري قراءة البيانات...")

            # تنفيذ الأمر
            try:
                # استخدام Popen مع shell=False للأمان
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                    env=env
                )
                
                # مراقبة التقدم
                while True:
                    if progress_callback and self._stop_event.is_set():
                        process.terminate()
                        self.repo.record_backup_complete(backup_id, False, 0, "Cancelled by user")
                        return False, "Backup cancelled"
                    
                    retcode = process.poll()
                    if retcode is not None:
                        break
                    time.sleep(0.1)
                    if progress_callback:
                        progress_callback(70, "جاري كتابة ملف النسخ...")

                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    self.repo.record_backup_complete(backup_id, False, 0, error_msg)
                    return False, f"mysqldump failed: {error_msg}"

            except Exception as e:
                self.repo.record_backup_complete(backup_id, False, 0, str(e))
                return False, f"Backup execution failed: {e}"

            if progress_callback:
                progress_callback(90, "جاري التحقق من الملف...")

            # التحقق من الملف
            if not os.path.exists(filepath):
                self.repo.record_backup_complete(backup_id, False, 0, "Backup file not created")
                return False, "Backup file was not created"

            file_size = os.path.getsize(filepath)
            if file_size == 0:
                self.repo.record_backup_complete(backup_id, False, 0, "Backup file is empty")
                return False, "Backup file is empty"

            # تسجيل النجاح
            self.repo.record_backup_complete(backup_id, True, file_size)

            if progress_callback:
                progress_callback(100, f"اكتمل النسخ الاحتياطي: {filename}")

            logger.info(f"✅ Backup successful: {filepath} ({file_size} bytes)")
            return True, filepath

        except Exception as e:
            logger.error(f"Backup error: {e}")
            return False, str(e)
        finally:
            self._is_backing_up = False

    def _find_mysqldump(self) -> Optional[str]:
        """البحث عن mysqldump في المسارات الشائعة"""
        common_paths = [
            r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
            r"C:\Program Files\MySQL\MySQL Server 5.7\bin\mysqldump.exe",
            r"C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
            r"C:\xampp\mysql\bin\mysqldump.exe",
            r"C:\wamp64\bin\mysql\mysql5.7\bin\mysqldump.exe",
            "/usr/bin/mysqldump",
            "/usr/local/bin/mysqldump",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        return None

    # ============================================================
    # Auto Backup
    # ============================================================

    def should_run_auto_backup(self) -> bool:
        """التحقق مما إذا كان يجب تشغيل النسخ الاحتياطي التلقائي"""
        if not self.repo.get_auto_backup_enabled():
            return False
        
        last_backup = self.repo.get_last_backup_date()
        if not last_backup:
            return True
        
        today = date.today().isoformat()
        return last_backup != today

    def run_auto_backup(self, created_by: int = 1) -> Tuple[bool, str]:
        """تشغيل النسخ الاحتياطي التلقائي إذا لزم الأمر"""
        if not self.should_run_auto_backup():
            return False, "Auto backup not needed today"

        logger.info("Starting automatic daily backup...")
        success, result = self.execute_backup(backup_type='auto', created_by=created_by)
        
        if success:
            self.repo.set_last_backup_date(date.today().isoformat())
            logger.info(f"✅ Automatic backup successful: {result}")
        else:
            logger.error(f"❌ Automatic backup failed: {result}")
        
        return success, result

    def start_background_auto_backup(self, check_interval_hours: int = 1):
        """بدء مراقبة النسخ الاحتياطي التلقائي في الخلفية"""
        if self._backup_thread and self._backup_thread.is_alive():
            logger.warning("Background auto backup already running")
            return

        self._stop_event.clear()
        self._backup_thread = threading.Thread(
            target=self._auto_backup_loop,
            args=(check_interval_hours * 3600,),
            daemon=True,
            name="AutoBackupMonitor"
        )
        self._backup_thread.start()
        logger.info(f"🔄 Background auto backup monitor started (check every {check_interval_hours}h)")

    def stop_background_auto_backup(self):
        """إيقاف مراقبة النسخ الاحتياطي التلقائي"""
        self._stop_event.set()
        if self._backup_thread:
            self._backup_thread.join(timeout=5)
        logger.info("🛑 Background auto backup monitor stopped")

    def _auto_backup_loop(self, interval_seconds: int):
        """حلقة مراقبة النسخ الاحتياطي التلقائي"""
        while not self._stop_event.is_set():
            try:
                if self.should_run_auto_backup():
                    logger.info("🔄 Running scheduled auto backup...")
                    self.run_auto_backup()
            except Exception as e:
                logger.error(f"Auto backup check error: {e}")
            
            # الانتظار للفترة المحددة أو حتى الإيقاف
            if self._stop_event.wait(interval_seconds):
                break

    # ============================================================
    # Settings & History
    # ============================================================

    def get_backup_settings(self) -> Dict:
        """جلب جميع إعدادات النسخ الاحتياطي"""
        settings = self.repo.get_settings()
        return {
            'backup_path': self.repo.get_backup_dir(),
            'mysqldump_path': self.repo.get_mysqldump_path(),
            'auto_backup_enabled': self.repo.get_auto_backup_enabled(),
            'last_backup_date': self.repo.get_last_backup_date(),
        }

    def update_backup_settings(self, settings: Dict) -> bool:
        """تحديث إعدادات النسخ الاحتياطي"""
        try:
            if 'backup_path' in settings:
                self.repo.set_backup_dir(settings['backup_path'])
            if 'mysqldump_path' in settings:
                self.repo.set_mysqldump_path(settings['mysqldump_path'])
            if 'auto_backup_enabled' in settings:
                self.repo.set_auto_backup_enabled(settings['auto_backup_enabled'])
            return True
        except Exception as e:
            logger.error(f"Error updating backup settings: {e}")
            return False

    def get_backup_history(self, limit: int = 50) -> List[Dict]:
        """جلب سجل النسخ الاحتياطية"""
        return self.repo.get_backup_history(limit)

    def get_last_backup_info(self) -> Optional[Dict]:
        """جلب معلومات آخر نسخة احتياطية ناجحة"""
        return self.repo.get_last_successful_backup()

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """تنظيف النسخ الاحتياطية القديمة"""
        return self.repo.cleanup_old_backups(keep_days)

    @property
    def is_backing_up(self) -> bool:
        return self._is_backing_up

    def get_status(self) -> Dict:
        """الحصول على حالة خدمة النسخ الاحتياطي"""
        last_backup = self.get_last_backup_info()
        return {
            'is_backing_up': self._is_backing_up,
            'auto_backup_enabled': self.repo.get_auto_backup_enabled(),
            'last_backup_date': self.repo.get_last_backup_date(),
            'last_backup_file': last_backup.get('filename') if last_backup else None,
            'last_backup_size': last_backup.get('file_size') if last_backup else None,
            'last_backup_time': last_backup.get('completed_at') if last_backup else None,
            'background_monitor_alive': self._backup_thread.is_alive() if self._backup_thread else False,
        }


# Singleton instance
_backup_service = None

def get_backup_service(db: DatabaseConnection = None) -> BackupServiceFacade:
    """الحصول على نسخة وحيدة من خدمة النسخ الاحتياطي"""
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupServiceFacade(db)
    return _backup_service