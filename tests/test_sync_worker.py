"""Behavior tests for the background sync worker."""
import threading

from PyQt6.QtCore import QCoreApplication

import controllers.sync_worker as sync_worker_module
from controllers.sync_worker import SyncWorker


class FakeSyncRepository:
    def get_stats(self):
        return {'pending': 1, 'synced': 0, 'failed': 0, 'total': 1}


class FakeSyncService:
    def __init__(self):
        self.sync_thread_id = None
        self.sync_called = threading.Event()

    def is_cloud_configured(self):
        return True

    def sync_incremental(self, progress_callback=None, batch_limit=100):
        self.sync_thread_id = threading.get_ident()
        self.sync_called.set()
        return {'success': 1, 'failed': 0, 'total': 1, 'completed': True}


def test_sync_worker_runs_sync_in_background_thread(monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    service = FakeSyncService()
    monkeypatch.setattr(sync_worker_module, 'get_sync_queue_repo', lambda: FakeSyncRepository())
    worker = SyncWorker(sync_service=service, interval_seconds=60)

    caller_thread_id = threading.get_ident()
    worker.start()

    assert service.sync_called.wait(2)
    worker.stop()

    assert service.sync_thread_id != caller_thread_id