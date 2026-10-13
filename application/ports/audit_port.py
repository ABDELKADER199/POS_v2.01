from typing import Protocol


class AuditPort(Protocol):
    def log(
        self,
        user_id,
        action,
        entity_type="",
        entity_id=None,
        store_id=None,
        success=True,
        details=None,
    ):
        ...
