import json
import threading

from application.services.sync_service_facade import SyncServiceFacade


class FakeDatabase:
    host = "cloud.test"

    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def commit(self):
        pass

    def rollback(self):
        pass


class InMemorySyncQueue:
    def __init__(self, count):
        self.items = {
            item_id: {
                "id": item_id,
                "table_name": "products",
                "action_type": "INSERT",
                "data_json": json.dumps({"id": item_id, "sequence": item_id}),
                "status": "pending",
                "retry_count": 0,
            }
            for item_id in range(count)
        }

    def get_pending(self, limit=1000):
        return [
            item for item in self.items.values()
            if item["status"] == "pending"
        ][:limit]

    def mark_synced(self, sync_id):
        self.items[sync_id]["status"] = "synced"
        return True

    def mark_failed(self, sync_id, error_message=None):
        item = self.items[sync_id]
        item["retry_count"] += 1
        item["error_message"] = error_message
        return True

    def stats(self):
        return {
            status: sum(item["status"] == status for item in self.items.values())
            for status in ("pending", "synced", "failed")
        }


def build_facade(queue):
    facade = SyncServiceFacade(local_db=FakeDatabase())
    facade.sync_repo = queue
    facade._cloud_db = FakeDatabase()
    facade._ensure_cloud_schema = lambda _cloud_db: None
    return facade


def test_sync_incremental_processes_large_batch_without_losing_items(monkeypatch):
    queue = InMemorySyncQueue(2048)
    facade = build_facade(queue)
    monkeypatch.setattr(facade, "_execute_sync_operation", lambda *args: True)

    result = facade.sync_incremental(batch_limit=2048)

    assert result["success"] == 2048
    assert result["failed"] == 0
    assert all(item["status"] == "synced" for item in queue.items.values())


def test_sync_incremental_keeps_unprocessed_items_pending_after_stop(monkeypatch):
    queue = InMemorySyncQueue(1000)
    facade = build_facade(queue)
    stop_event = threading.Event()

    def execute_operation(_cloud_db, _table, _action, data):
        if data["sequence"] == 136:
            stop_event.set()
        return True

    monkeypatch.setattr(facade, "_execute_sync_operation", execute_operation)
    result = facade.sync_incremental(batch_limit=1000, stop_event=stop_event)

    assert result["completed"] is False
    assert sum(item["status"] == "synced" for item in queue.items.values()) == 137
    assert sum(item["status"] == "pending" for item in queue.items.values()) == 863

    result = facade.sync_incremental(batch_limit=1000, stop_event=threading.Event())

    assert result["success"] == 863
    assert all(item["status"] == "synced" for item in queue.items.values())


def test_sync_incremental_retries_temporary_failure_on_next_cycle(monkeypatch):
    queue = InMemorySyncQueue(100)
    facade = build_facade(queue)
    failed_once = set()

    def execute_operation(_cloud_db, _table, _action, data):
        if data["sequence"] == 17 and data["sequence"] not in failed_once:
            failed_once.add(data["sequence"])
            return False
        return True

    monkeypatch.setattr(facade, "_execute_sync_operation", execute_operation)

    first_result = facade.sync_incremental(batch_limit=100)

    assert first_result["failed"] == 1
    assert queue.items[17]["status"] == "pending"
    assert queue.items[17]["retry_count"] == 1

    second_result = facade.sync_incremental(batch_limit=100)

    assert second_result["success"] == 1
    assert all(item["status"] == "synced" for item in queue.items.values())