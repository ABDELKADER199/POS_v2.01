"""
Print Controller - متحكم الطباعة
طبقة رقيقة بين واجهة PyQt وخدمة الطباعة
"""
from application.services.print_service_facade import PrintServiceFacade, get_print_service
from repositories.settings_repo import SettingsRepository


class PrintController:
    """متحكم عمليات الطباعة"""

    def __init__(self, settings_repo: SettingsRepository = None):
        self.service = get_print_service(settings_repo)

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