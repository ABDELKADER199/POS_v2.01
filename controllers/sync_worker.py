"""
Sync Worker - العامل الخلفي للمزامنة باستخدام QThread
يدعم الإشارات (signals) للتواصل مع واجهة المستخدم
"""
import logging
import json
import threading
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication

from application.services.sync_service_facade import SyncServiceFacade, get_sync_service
from repositories.sync_queue_repo import get_sync_queue_repo

logger = logging.getLogger(__name__)


class SyncWorkerSignals(QObject):
    """الإشارات المنبعثة من العامل الخلفي"""
    # progress: النسبة (0-100)، الرسالة
    progress = pyqtSignal(int, str)
    # finished: نجاح، عدد العمليات، رسالة
    finished = pyqtSignal(bool, int, str)
    # error: رسالة خطأ
    error = pyqtSignal(str)
    # status_update: تحديث حالة الاتصال، عدد العمليات المعلقة
    status_update = pyqtSignal(bool, int, str)
    # batch_completed: تمت معالجة دفعة
    batch_completed = pyqtSignal(int, int)  # processed, total


class SyncWorker(QThread):
    """
    العامل الخلفي للمزامنة - يعمل في خيط منفصل
    يستخدم QThread لتكامل صحيح مع Qt
    """
    
    def __init__(
        self, 
        sync_service: SyncServiceFacade = None,
        interval_seconds: int = 300,
        batch_limit: int = 100,
        parent: QObject = None
    ):
        super().__init__(parent)
        self.sync_service = sync_service or get_sync_service()
        self.interval_seconds = interval_seconds
        self.batch_limit = batch_limit
        self._stop_requested = False
        self._state_lock = threading.Lock()
        self._wake_event = threading.Event()
        self._running = False
        
        # الإشارات
        self.signals = SyncWorkerSignals()
        
        # ربط الإشارات الداخلية
        self.finished.connect(self._on_thread_finished)
    
    def run(self):
        """نقطة دخول الخيط - مطلوبة من QThread"""
        self._running = True
        self._stop_requested = False
        logger.info(f"🔄 SyncWorker started (interval: {self.interval_seconds}s)")
        
        try:
            while not self._stop_requested:
                self._check_and_sync()
                self._wake_event.wait(self.interval_seconds)
                self._wake_event.clear()
        finally:
            self._running = False
    
    def _check_and_sync(self):
        """فحص طابور المزامنة وتنفيذ المزامنة إذا لزم"""
        if self._stop_requested:
            return
        
        try:
            # التحقق من وجود عمليات معلقة
            pending_count = self._get_pending_count()
            cloud_configured = self.sync_service.is_cloud_configured()
            
            # تحديث حالة الاتصال
            self.signals.status_update.emit(cloud_configured, pending_count, "")
            
            if not cloud_configured:
                self.signals.status_update.emit(False, pending_count, "السحابة غير مهيأة")
                return
            
            if pending_count == 0:
                self.signals.status_update.emit(True, 0, "لا توجد عمليات معلقة")
                return
            
            # تنفيذ المزامنة مع callback للتقدم
            def progress_callback(percentage: int, message: str):
                if not self._stop_requested:
                    self.signals.progress.emit(percentage, message)
            
            def stop_check():
                return self._stop_requested
            
            result = self.sync_service.sync_incremental(
                progress_callback=progress_callback,
                batch_limit=self.batch_limit
            )
            
            success = result.get('success', 0)
            failed = result.get('failed', 0)
            total = result.get('total', 0)
            completed = result.get('completed', True)
            
            if self._stop_requested:
                self.signals.finished.emit(False, 0, "تم إيقاف المزامنة")
            elif failed == 0:
                self.signals.finished.emit(True, success, f"اكتملت: {success} عملية")
                self.signals.status_update.emit(True, 0, f"مكتملة: {success} عملية")
            else:
                self.signals.finished.emit(False, failed, f"فشلت {failed} من {total}")
                self.signals.status_update.emit(True, failed, f"فشلت {failed} عملية")
            
        except Exception as e:
            logger.error(f"SyncWorker error: {e}")
            self.signals.error.emit(str(e))
            self.signals.status_update.emit(False, 0, f"خطأ: {str(e)[:50]}")
    
    def _get_pending_count(self) -> int:
        """الحصول على عدد العمليات المعلقة"""
        try:
            repo = get_sync_queue_repo()
            stats = repo.get_stats()
            return stats.get('pending', 0)
        except Exception:
            return 0
    
    def stop(self):
        """إيقاف العامل"""
        with self._state_lock:
            self._stop_requested = True
            self._running = False
        
        self._wake_event.set()
        self.wait(5000)  # انتظار 5 ثوانٍ كحد أقصى
        logger.info("🛑 SyncWorker stopped")
    
    def force_sync(self):
        """إجبار مزامنة فورية"""
        if not self.isRunning():
            self.start()
        else:
            self._wake_event.set()
    
    def _on_thread_finished(self):
        """معالجة انتهاء الخيط"""
        logger.info("SyncWorker thread finished")
    
    def is_running(self) -> bool:
        """التحقق من حالة التشغيل"""
        with self._state_lock:
            return self._running
    
    def set_interval(self, seconds: int):
        """تغيير فترة الفحص"""
        self.interval_seconds = max(30, seconds)  # حد أدنى 30 ثانية


class SyncManager(QObject):
    """
    مدير المزامنة عالي المستوى - واجهة للتطبيق
    يدير دورة حياة العامل ويوفر واجهة مبسطة
    """
    
    # إشارات عامة للتطبيق
    sync_started = pyqtSignal()
    sync_finished = pyqtSignal(bool, int, str)
    sync_progress = pyqtSignal(int, str)
    status_changed = pyqtSignal(bool, int, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._worker: Optional[SyncWorker] = None
        self._settings = {
            'interval_seconds': 300,
            'batch_limit': 100,
            'auto_start': True,
        }
    
    def initialize(self, interval_seconds: int = 300, batch_limit: int = 100, auto_start: bool = True):
        """تهيئة مدير المزامنة"""
        if self._worker and self._worker.isRunning():
            self._worker.stop()

        self._settings.update({
            'interval_seconds': interval_seconds,
            'batch_limit': batch_limit,
            'auto_start': auto_start,
        })
        
        self._worker = SyncWorker(
            interval_seconds=interval_seconds,
            batch_limit=batch_limit
        )
        
        # ربط الإشارات
        self._worker.signals.progress.connect(self.sync_progress.emit)
        self._worker.signals.finished.connect(self.sync_finished.emit)
        self._worker.signals.status_update.connect(self.status_changed.emit)
        self._worker.signals.error.connect(self.error_occurred.emit)
        
        if auto_start:
            self.start()
        
        logger.info("✅ SyncManager initialized")
    
    def start(self):
        """بدء المزامنة"""
        if self._worker and not self._worker.isRunning():
            self._worker.start()
            self.sync_started.emit()
            logger.info("🔄 SyncManager: started background sync")
    
    def stop(self):
        """إيقاف المزامنة"""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            logger.info("🛑 SyncManager: stopped background sync")
    
    def force_sync_now(self):
        """إجبار مزامنة فورية"""
        if self._worker:
            self._worker.force_sync()
    
    def set_interval(self, seconds: int):
        """تغيير الفترة"""
        self._settings['interval_seconds'] = max(30, seconds)
        if self._worker:
            self._worker.set_interval(self._settings['interval_seconds'])
    
    def is_running(self) -> bool:
        return self._worker and self._worker.isRunning()
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'running': self.is_running(),
            'interval': self._settings['interval_seconds'],
            'batch_limit': self._settings['batch_limit'],
        }
    
    def cleanup(self):
        """تنظيف الموارد"""
        self.stop()
        if self._worker:
            self._worker.deleteLater()
            self._worker = None


# Singleton instance
_sync_manager = None

def get_sync_manager() -> SyncManager:
    """الحصول على نسخة وحيدة من مدير المزامنة"""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager()
    return _sync_manager