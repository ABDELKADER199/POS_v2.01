from typing import Dict, Optional

from application.ports.cashier_query_port import (
    CrossBranchStockQueryPort,
    CustomerQueryPort,
    SettingsQueryPort,
    StockQueryPort,
)


class GetSettingsUseCase:
    def __init__(self, settings_repo: SettingsQueryPort):
        self.settings_repo = settings_repo

    def execute(self) -> Dict:
        return self.settings_repo.get_all()


class FindCustomerByPhoneUseCase:
    def __init__(self, customer_repo: CustomerQueryPort):
        self.customer_repo = customer_repo

    def execute(self, phone: str) -> Optional[Dict]:
        normalized_phone = str(phone or "").strip()
        if not normalized_phone:
            return None
        return self.customer_repo.get_customer_by_phone(normalized_phone)


class GetStockUseCase:
    def __init__(self, inventory_repo: StockQueryPort, active_store_provider):
        self.inventory_repo = inventory_repo
        self.active_store_provider = active_store_provider

    def execute(self, product_id: int, store_id: int = None) -> int:
        resolved_store_id = store_id or self.active_store_provider()
        if not resolved_store_id:
            raise ValueError("لا يوجد فرع تشغيل محدد")
        resolved_store_id = int(resolved_store_id)
        return self.inventory_repo.get_stock(product_id, resolved_store_id)


class GetCrossBranchStockUseCase:
    def __init__(self, stock_repo: CrossBranchStockQueryPort):
        self.stock_repo = stock_repo

    def execute(self, search_term: str) -> Dict:
        normalized_term = str(search_term or "").strip()
        if not normalized_term:
            return {}
        return self.stock_repo.get_product_cross_branch_stock(normalized_term)
