import logging
from typing import Dict, List, Optional

from application.ports.audit_port import AuditPort
from application.ports.drawer_port import DrawerPort

logger = logging.getLogger(__name__)

OPEN_DRAWER_ACTION = "drawer.open"
CLOSE_OWN_DRAWER_ACTION = "drawer.close_own"


class DrawerQueryUseCase:
    def __init__(self, drawer_repo: DrawerPort):
        self.drawer_repo = drawer_repo

    def get_store_open_drawer(self, store_id: int) -> Optional[Dict]:
        if not store_id:
            return None
        return self.drawer_repo.get_store_open_drawer(store_id)

    def get_any_open_drawer(self) -> Optional[Dict]:
        return self.drawer_repo.get_any_open_drawer()

    def get_operational_stores(self) -> List[Dict]:
        if hasattr(self.drawer_repo, "get_operational_stores"):
            return self.drawer_repo.get_operational_stores()
        return []

    def get_drawer_status(self, user_id: int) -> Optional[Dict]:
        return self.drawer_repo.get_drawer_status(user_id)

    def get_drawer_summary(self, drawer_id: int) -> Optional[Dict]:
        return self.drawer_repo.get_drawer_summary(drawer_id)

    def get_open_drawer_summary(self, drawer_id: int) -> Optional[Dict]:
        return self.drawer_repo.get_open_drawer_summary(drawer_id)

    def get_closed_drawers_history(
        self,
        store_id: int,
        date_from: str = None,
        date_to: str = None,
    ) -> List[Dict]:
        return self.drawer_repo.get_closed_drawers_history(store_id, date_from, date_to)

    def get_last_closed_drawer_id(self, store_id: int, user_id: int) -> Optional[int]:
        return self.drawer_repo.get_last_closed_drawer_id(store_id, user_id)


class OpenDrawerUseCase:
    def __init__(self, drawer_repo: DrawerPort, audit: AuditPort):
        self.drawer_repo = drawer_repo
        self.audit = audit

    def execute(self, store_id: int, user_id: int, opening_balance: float = 0) -> bool:
        if not store_id:
            logger.warning("Cannot open drawer: missing store_id for user %s", user_id)
            self.audit.log(
                user_id,
                OPEN_DRAWER_ACTION,
                entity_type="drawer",
                store_id=None,
                success=False,
                details={
                    "opening_balance": opening_balance,
                    "error": "missing_store_id",
                },
            )
            return False

        if not user_id:
            logger.warning("Cannot open drawer: missing user_id for store %s", store_id)
            return False

        existing_drawer = self.drawer_repo.get_store_open_drawer(store_id)
        if existing_drawer:
            logger.warning(
                "Cannot open drawer: already open by user %s",
                existing_drawer.get("cashier_id"),
            )
            return False

        try:
            drawer_id = self.drawer_repo.insert_open_drawer(store_id, user_id, opening_balance)
            self.drawer_repo.commit()
            self.audit.log(
                user_id,
                OPEN_DRAWER_ACTION,
                entity_type="drawer",
                entity_id=drawer_id,
                store_id=store_id,
                success=True,
                details={"opening_balance": opening_balance},
            )
            return True
        except Exception as exc:
            self.drawer_repo.rollback()
            logger.error("Error opening drawer: %s", exc, exc_info=True)
            self.audit.log(
                user_id,
                OPEN_DRAWER_ACTION,
                entity_type="drawer",
                store_id=store_id,
                success=False,
                details={"opening_balance": opening_balance, "error": str(exc)},
            )
            return False


class CloseDrawerUseCase:
    def __init__(self, drawer_repo: DrawerPort, audit: AuditPort):
        self.drawer_repo = drawer_repo
        self.audit = audit

    def execute(
        self,
        drawer_id: int,
        closing_balance: float,
        denomination_details: dict = None,
        user_id: int = None,
        store_id: int = None,
    ) -> bool:
        details = denomination_details or {}
        try:
            self.drawer_repo.mark_drawer_closed(drawer_id, closing_balance)
            if details:
                self.drawer_repo.replace_closing_details(drawer_id, details)
            self.drawer_repo.commit()
            self.audit.log(
                user_id,
                CLOSE_OWN_DRAWER_ACTION,
                entity_type="drawer",
                entity_id=drawer_id,
                store_id=store_id,
                success=True,
                details=details,
            )
            return True
        except Exception as exc:
            self.drawer_repo.rollback()
            logger.error("Error closing drawer %s: %s", drawer_id, exc, exc_info=True)
            self.audit.log(
                user_id,
                CLOSE_OWN_DRAWER_ACTION,
                entity_type="drawer",
                entity_id=drawer_id,
                store_id=store_id,
                success=False,
                details={**details, "error": str(exc)},
            )
            return False
