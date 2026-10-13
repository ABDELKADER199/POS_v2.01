"""Transfers Controller - thin adapter between PyQt UI and application services."""
from application.services.transfers_service_facade import TransfersServiceFacade
from repositories.transfers_repo import TransfersRepository


class TransfersController:
    def __init__(self):
        self.service = TransfersServiceFacade(TransfersRepository())

    def __getattr__(self, name):
        return getattr(self.service, name)
