"""
Backup Controller - متحكم النسخ الاحتياطي
طبقة رقيقة بين واجهة PyQt وخدمة النسخ الاحتياطي
"""
from application.services.backup_service_facade import BackupServiceFacade, get_backup_service
from repositories.db_connection import DatabaseConnection


class BackupController:
    """متحكم عمليات النسخ الاحتياطي"""

    def __init__(self, local_db: DatabaseConnection = None):
        self.service = get_backup_service(local_db)

    def __getattr__(self, name):
        return getattr(self.service, name)

    def __setattr__(self, name, value):
        if name == "service":
            super().__setattr__(name, value)
            return
        if "service" in self.__dict__ and hasattr(self.service, name):
            setattr(self.service, name, value)
            return
        super().__setattr__(name, value)