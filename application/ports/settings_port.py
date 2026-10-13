from typing import Dict, Protocol


class SettingsPort(Protocol):
    def get_all(self) -> Dict[str, str]:
        ...

    def get(self, key: str, default: str = "") -> str:
        ...

    def upsert_setting(self, key: str, value: str) -> None:
        ...

    def upsert_settings(self, settings: Dict[str, str]) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
