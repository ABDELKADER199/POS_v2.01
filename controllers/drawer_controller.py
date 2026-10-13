"""Drawer Controller - thin adapter between PyQt UI and application services."""
from application.services.drawer_service_facade import DrawerServiceFacade
from repositories.drawer_repo import DrawerRepository
from services.audit_service import AuditService


class DrawerController:
    def __init__(self):
        self.service = DrawerServiceFacade(DrawerRepository(), AuditService())

    def get_store_open_drawer(self, *args, **kwargs): return self.service.get_store_open_drawer(*args, **kwargs)
    def get_any_open_drawer(self, *args, **kwargs): return self.service.get_any_open_drawer(*args, **kwargs)
    def get_drawer_status(self, *args, **kwargs): return self.service.get_drawer_status(*args, **kwargs)
    def open_drawer(self, *args, **kwargs): return self.service.open_drawer(*args, **kwargs)
    def close_drawer(self, *args, **kwargs): return self.service.close_drawer(*args, **kwargs)
    def get_drawer_summary(self, *args, **kwargs): return self.service.get_drawer_summary(*args, **kwargs)
    def get_open_drawer_summary(self, *args, **kwargs): return self.service.get_open_drawer_summary(*args, **kwargs)
    def get_closed_drawers_history(self, *args, **kwargs): return self.service.get_closed_drawers_history(*args, **kwargs)
    def get_last_closed_drawer_id(self, *args, **kwargs): return self.service.get_last_closed_drawer_id(*args, **kwargs)
