"""Admin Controller - thin adapter between PyQt UI and application services."""
from application.services.admin_service_facade import AdminServiceFacade
from repositories.admin_repo import AdminRepository


class AdminController:
    def __init__(self):
        self.service = AdminServiceFacade(AdminRepository())
        from services.audit_service import AuditService
        self.audit_service = AuditService()

    def get_all_users(self): return self.service.get_all_users()
    def get_user_by_email(self, email): return self.service.get_user_by_email(email)
    def get_all_roles(self): return self.service.get_all_roles()
    def get_all_stores(self, include_inactive=False): return self.service.get_all_stores(include_inactive)
    def add_user(self, *args, **kwargs): return self.service.add_user(*args, **kwargs)
    def update_user(self, *args, **kwargs): return self.service.update_user(*args, **kwargs)
    def delete_user(self, user_id): return self.service.delete_user(user_id)
    def get_drawers_report(self): return self.service.get_drawers_report()
    def get_drawer_summary(self, drawer_id): return self.service.get_drawer_summary(drawer_id)
    def add_store(self, *args, **kwargs): return self.service.add_store(*args, **kwargs)
    def update_store(self, *args, **kwargs): return self.service.update_store(*args, **kwargs)
    def delete_store(self, store_id): return self.service.delete_store(store_id)
    def get_authorized_devices(self): return self.service.get_authorized_devices()
    def add_authorized_device(self, *args, **kwargs): return self.service.add_authorized_device(*args, **kwargs)
    def update_device_status(self, device_id, is_active): return self.service.update_device_status(device_id, is_active)
    def delete_device(self, device_id): return self.service.delete_device(device_id)
    def get_sync_stats(self): return self.service.get_sync_stats()
        
    def get_audit_logs(self, limit: int = 1000):
        return self.audit_service.repo.fetch_logs(limit)
