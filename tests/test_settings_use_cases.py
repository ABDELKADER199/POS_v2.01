from application.services.settings_service_facade import SettingsServiceFacade
from application.use_cases.settings import GetSettingsUseCase, SaveSettingsUseCase


class FakeSettingsRepository:
    def __init__(self):
        self.settings = {"store_name": "HyperPOS", "tax_enabled": "1"}
        self.upserted = None
        self.committed = False
        self.rolled_back = False
        self.raise_on_upsert = False

    def get_all(self):
        return dict(self.settings)

    def get(self, key, default=""):
        return self.settings.get(key, default)

    def upsert_setting(self, key, value):
        self.upsert_settings({key: value})

    def upsert_settings(self, settings):
        if self.raise_on_upsert:
            raise RuntimeError("database error")
        self.upserted = dict(settings)
        self.settings.update(settings)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_get_settings_returns_all_settings():
    repo = FakeSettingsRepository()

    result = GetSettingsUseCase(repo).execute()

    assert result == {"store_name": "HyperPOS", "tax_enabled": "1"}


def test_save_settings_cleans_keys_and_values_then_commits():
    repo = FakeSettingsRepository()

    result = SaveSettingsUseCase(repo).execute(
        {
            " store_name ": " متجر ",
            "tax_number": 12345,
            "receipt_footer": None,
            "   ": "ignored",
            "": "ignored",
        }
    )

    assert result is True
    assert repo.upserted == {
        "store_name": " متجر ",
        "tax_number": "12345",
        "receipt_footer": "",
    }
    assert repo.committed is True
    assert repo.rolled_back is False


def test_save_settings_noops_when_payload_is_empty():
    repo = FakeSettingsRepository()

    assert SaveSettingsUseCase(repo).execute({" ": "ignored", "": None}) is True
    assert SaveSettingsUseCase(repo).execute(None) is True

    assert repo.upserted is None
    assert repo.committed is False
    assert repo.rolled_back is False


def test_save_settings_rolls_back_on_repository_error():
    repo = FakeSettingsRepository()
    repo.raise_on_upsert = True

    result = SaveSettingsUseCase(repo).execute({"store_name": "HyperPOS"})

    assert result is False
    assert repo.committed is False
    assert repo.rolled_back is True


def test_settings_service_facade_delegates_get_and_update():
    repo = FakeSettingsRepository()
    service = SettingsServiceFacade(settings_repo=repo)

    assert service.get_all() == {"store_name": "HyperPOS", "tax_enabled": "1"}
    assert service.update_many({"store_phone": "010"}) is True
    assert repo.settings["store_phone"] == "010"
    assert repo.committed is True
