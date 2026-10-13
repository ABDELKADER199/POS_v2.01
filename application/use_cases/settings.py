import logging
from typing import Dict

from application.ports.settings_port import SettingsPort

logger = logging.getLogger(__name__)


class GetSettingsUseCase:
    def __init__(self, settings_repo: SettingsPort):
        self.settings_repo = settings_repo

    def execute(self) -> Dict[str, str]:
        return self.settings_repo.get_all()


class SaveSettingsUseCase:
    def __init__(self, settings_repo: SettingsPort):
        self.settings_repo = settings_repo

    def execute(self, settings: Dict[str, str]) -> bool:
        cleaned_settings = {
            str(key).strip(): "" if value is None else str(value)
            for key, value in (settings or {}).items()
            if str(key).strip()
        }
        if not cleaned_settings:
            return True
        try:
            self.settings_repo.upsert_settings(cleaned_settings)
            self.settings_repo.commit()
            return True
        except Exception as exc:
            self.settings_repo.rollback()
            logger.error("Error saving settings: %s", exc)
            return False
