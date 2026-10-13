from typing import Dict

from application.use_cases.settings import GetSettingsUseCase, SaveSettingsUseCase
from repositories.settings_repo import SettingsRepository


class SettingsServiceFacade:
    def __init__(self, settings_repo=None):
        self.settings_repo = settings_repo or SettingsRepository()
        self.get_settings_use_case = GetSettingsUseCase(self.settings_repo)
        self.save_settings_use_case = SaveSettingsUseCase(self.settings_repo)

    def get_all(self) -> Dict[str, str]:
        return self.get_settings_use_case.execute()

    def update_many(self, settings: Dict[str, str]) -> bool:
        return self.save_settings_use_case.execute(settings)
