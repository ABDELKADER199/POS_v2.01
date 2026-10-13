from application.services.license_service import LicenseService
from utils.license_manager import LicenseManager


class FakeLicenseRepository:
    def __init__(self):
        self.records = {}
        self.ensure_called = False

    def ensure_table(self):
        self.ensure_called = True

    def get_active_license(self, hardware_id):
        return self.records.get(hardware_id)

    def activate(self, hardware_id, activation_key):
        self.records[hardware_id] = {
            "hardware_id": hardware_id,
            "activation_key": activation_key,
            "status": "active",
        }


def test_activation_key_is_bound_to_hardware_id():
    hardware_id = "ABCD-1234-EFGH-5678"
    valid_key = LicenseManager.generate_activation_key(hardware_id)

    assert LicenseManager.verify_key(hardware_id, valid_key)
    assert not LicenseManager.verify_key("DIFFERENT-HARDWARE", valid_key)


def test_license_service_activates_and_validates_current_hardware(monkeypatch):
    repo = FakeLicenseRepository()
    monkeypatch.setattr(LicenseManager, "get_hardware_id", classmethod(lambda cls: "AAAA-BBBB-CCCC-DDDD"))
    service = LicenseService(repo)
    key = LicenseManager.generate_activation_key("AAAA-BBBB-CCCC-DDDD")

    assert not service.is_activated()
    assert service.activate(key)
    assert service.is_activated()
    assert repo.ensure_called


def test_license_service_rejects_wrong_key(monkeypatch):
    repo = FakeLicenseRepository()
    monkeypatch.setattr(LicenseManager, "get_hardware_id", classmethod(lambda cls: "AAAA-BBBB-CCCC-DDDD"))
    service = LicenseService(repo)

    assert not service.activate("WRONG-KEY")
    assert not service.is_activated()
