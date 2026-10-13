"""
Returns Controller - متحكم المرتجعات
طبقة رقيقة بين واجهة PyQt وخدمات تطبيق المرتجعات.
"""
from application.services.returns_service_facade import ReturnsServiceFacade
from repositories.returns_repo import ReturnsRepository


class ReturnsController:
    def __init__(self):
        self.service = ReturnsServiceFacade(ReturnsRepository())

    def __getattr__(self, name):
        return getattr(self.service, name)
