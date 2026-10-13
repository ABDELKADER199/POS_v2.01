"""
Sync Controller - متحكم المزامنة مع دعم مؤشر الاتصال
طبقة رقيقة بين واجهة PyQt وخدمة المزامنة مع إشارات الحالة
"""
from PyQt6.QtCore import QObject, pyqtSignal
from application.services.sync_service_facade import SyncServiceFacade, get_sync_service
from controllers.sync_worker import SyncWorker, SyncWorkerSignals, SyncManager
from repositories.db_connection import DatabaseConnection


class SyncController(QObject):
    """متحكم عمليات المزامنة مع إشارات الحالة"""
    
    # إشارات للحالة
    sync_started = pyqtSignal()
    sync_finished = pyqtSignal(bool, int, str)
    sync_progress = pyqtSignal(int, str)
    status_changed = pyqtSignal(bool, int, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, local_db: DatabaseConnection = None):
        super().__init__()
        self.service = get_sync_service(local_db)
        self._manager = SyncManager(self)
        
        # ربط إشارات العامل مع إشارات الـ Controller
        self._manager.sync_started.connect(self.sync_started.emit)
        self._manager.sync_finished.connect(self.sync_finished.emit)
        self._manager.sync_progress.connect(self.sync_progress.emit)
        self._manager.status_changed.connect(self.status_changed.emit)
        self._manager.error_occurred.connect(self.error_occurred.emit)

    def start_background_sync(self, interval_seconds: int = 300):
        """بدء المزامنة في الخلفية"""
        self._manager.initialize(
            interval_seconds=interval_seconds,
            batch_limit=100,
            auto_start=False
        )
        self._manager.start()

    def stop_background_sync(self):
        """إيقاف المزامنة في الخلفية"""
        self._manager.stop()

    def force_sync_now(self):
        """إجبار مزامنة فورية"""
        self._manager.force_sync_now()

    def is_cloud_configured(self) -> bool:
        return self.service.is_cloud_configured()

    def get_sync_status(self) -> dict:
        return self._manager.get_status()