"""Auth Controller - thin adapter between PyQt UI and application services."""
from application.services.auth_service_facade import AuthServiceFacade
from repositories.admin_repo import AdminRepository
from repositories.user_repo import UserRepository


class AuthController:
    def __init__(self):
        device_repo = AdminRepository()
        device_repo.ensure_authorized_devices_table()
        self.service = AuthServiceFacade(UserRepository(), device_repo)

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
