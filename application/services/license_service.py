"""Application activation service."""

from __future__ import annotations

import logging

from repositories.license_repo import LicenseRepository
from utils.license_manager import LicenseManager

logger = logging.getLogger(__name__)


class LicenseService:
    def __init__(self, repo: LicenseRepository | None = None):
        self.repo = repo or LicenseRepository()
        self.repo.ensure_table()

    @property
    def hardware_id(self) -> str:
        return LicenseManager.get_hardware_id()

    def is_activated(self) -> bool:
        hardware_id = self.hardware_id
        record = self.repo.get_active_license(hardware_id)
        if not record:
            return False
        stored_key = record.get("activation_key") or ""
        return LicenseManager.verify_key(hardware_id, stored_key)

    def activate(self, activation_key: str) -> bool:
        hardware_id = self.hardware_id
        if not LicenseManager.verify_key(hardware_id, activation_key):
            logger.warning("Invalid activation key for hardware id: %s", hardware_id)
            return False
        self.repo.activate(hardware_id, activation_key.strip().upper())
        return True
