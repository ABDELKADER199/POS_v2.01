from application.services.sync_service_facade import SyncServiceFacade


class LocalDatabase:
    host = "gateway01.eu-central-1.prod.aws.tidbcloud.com"


def service_without_database_connection():
    service = SyncServiceFacade.__new__(SyncServiceFacade)
    service.local_db = LocalDatabase()
    return service


def test_cloud_sync_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("POS_ENABLE_CLOUD_SYNC", raising=False)
    monkeypatch.setenv("POS_CLOUD_DB_HOST", "cloud.example")

    assert service_without_database_connection().is_cloud_configured() is False


def test_cloud_sync_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("POS_ENABLE_CLOUD_SYNC", "true")
    monkeypatch.setenv("POS_CLOUD_DB_HOST", "cloud.example")

    assert service_without_database_connection().is_cloud_configured() is True
