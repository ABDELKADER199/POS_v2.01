import logging
from datetime import datetime
from typing import Dict, List, Optional

from application.ports.callcenter_port import CallCenterRepositoryPort

logger = logging.getLogger(__name__)

ORDER_STATUS_FILTERS = {
    "Pending": ["Pending", "Confirmed", "Prepared"],
    "Completed": ["Delivered", "Cancelled"],
}

ORDER_STATUS_MAP = {
    "Accepted": "Confirmed",
    "Processing": "Prepared",
    "Prepared": "Prepared",
    "Confirmed": "Confirmed",
    "Delivered": "Delivered",
    "Cancelled": "Cancelled",
}

DELIVERY_STATUS_TRANSITIONS = {
    "Unassigned": {"Assigned"},
    "Assigned": {"PickedUp", "OutForDelivery", "Failed"},
    "PickedUp": {"OutForDelivery", "Failed"},
    "OutForDelivery": {"Delivered", "Failed"},
    "Failed": {"Assigned"},
    "Delivered": set(),
}


class CallCenterStoresUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def execute(self) -> List[Dict]:
        return self.repo.get_all_stores()


class CallCenterProductSearchUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def execute(self, term: str) -> List[Dict]:
        normalized_term = str(term or "").strip()
        if len(normalized_term) < 2:
            return []
        return self.repo.search_products(normalized_term)


class CallCenterCustomerLookupUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def execute(self, phone: str) -> Optional[Dict]:
        normalized_phone = str(phone or "").strip()
        if len(normalized_phone) < 8:
            return None
        return self.repo.get_customer_by_phone(normalized_phone)


class SaveCallCenterOrderUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def execute(
        self,
        customer_name,
        phone,
        address,
        store_id,
        items,
        total,
        user_id,
        source_store_id=None,
    ):
        if not store_id or not items:
            return None
        try:
            normalized_name = str(customer_name or "").strip()
            normalized_phone = str(phone or "").strip()
            normalized_address = str(address or "").strip()
            order_number = f"CC-{datetime.now():%Y%m%d%H%M%S}"
            destination_store_id = store_id
            resolved_source_store_id = source_store_id or destination_store_id
            customer_id = self._get_or_create_customer(
                normalized_name,
                normalized_phone,
                normalized_address,
            )

            order_id = self.repo.create_order_header(
                order_number,
                normalized_name,
                normalized_phone,
                normalized_address,
                None,
                customer_id,
                resolved_source_store_id,
                destination_store_id,
                user_id,
                total,
            )
            for item in items:
                self.repo.insert_order_item(
                    order_id,
                    item["product_id"],
                    item["quantity"],
                    item["price"],
                )

            self.repo.commit()
            return order_number
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error saving call-center order: %s", exc, exc_info=True)
            return None

    def _get_or_create_customer(self, name: str, phone: str, address: str) -> Optional[int]:
        if not name and not phone:
            return None
        if phone:
            existing = self.repo.get_customer_by_phone(phone)
            if existing:
                self.repo.update_customer(existing["id"], name, address)
                return existing["id"]
        return self.repo.create_customer(name or "عميل كول سنتر", phone, address)


class ListCallCenterOrdersUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def execute(self, status=None, store_id=None, search=None) -> List[Dict]:
        normalized_search = str(search or "").strip() or None
        statuses = ORDER_STATUS_FILTERS.get(status)
        return self.repo.get_orders(statuses, store_id, normalized_search)


class UpdateCallCenterOrderStatusUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def execute(self, order_id, status) -> bool:
        if not order_id or not status:
            return False
        if status not in ORDER_STATUS_MAP:
            return False
        try:
            db_status = ORDER_STATUS_MAP[status]
            self.repo.update_order_status(order_id, db_status)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error updating call-center order: %s", exc, exc_info=True)
            return False


class ListDeliveryAgentsUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def execute(self, store_id: int) -> List[Dict]:
        if not store_id:
            return []
        return self.repo.get_delivery_agents(store_id)


class AssignDeliveryAgentUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def execute(self, order_id: int, agent_id: int, store_id: int) -> bool:
        if not order_id or not agent_id or not store_id:
            return False
        try:
            order = self.repo.get_order_by_id(order_id)
            if not order or order.get("status") in ("Delivered", "Cancelled"):
                return False
            order_store_id = order.get("destination_store_id") or order.get("source_store_id")
            if int(order_store_id or 0) != int(store_id):
                return False
            agents = self.repo.get_delivery_agents(store_id)
            if not any(
                int(agent.get("id")) == int(agent_id)
                and int(agent.get("store_id") or 0) == int(store_id)
                for agent in agents
            ):
                return False
            self.repo.assign_delivery_agent(order_id, agent_id)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error assigning delivery agent: %s", exc, exc_info=True)
            return False


class UpdateDeliveryTrackingUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def execute(self, order_id: int, status: str, notes: str = None) -> bool:
        if not order_id or status not in DELIVERY_STATUS_TRANSITIONS:
            return False
        try:
            order = self.repo.get_order_by_id(order_id)
            if not order or not order.get("delivery_agent_id"):
                return False
            current_status = order.get("delivery_status") or "Unassigned"
            if status not in DELIVERY_STATUS_TRANSITIONS[current_status]:
                return False
            self.repo.update_delivery_status(order_id, status, str(notes or "").strip() or None)
            self.repo.commit()
            return True
        except Exception as exc:
            self.repo.rollback()
            logger.error("Error updating delivery tracking: %s", exc, exc_info=True)
            return False


class CallCenterOrderDetailsUseCase:
    def __init__(self, repo: CallCenterRepositoryPort):
        self.repo = repo

    def get_details(self, order_id) -> List[Dict]:
        if not order_id:
            return []
        return self.repo.get_order_details(order_id)

    def get_by_id(self, order_id) -> Optional[Dict]:
        if not order_id:
            return None
        return self.repo.get_order_by_id(order_id)
