from typing import Dict, List, Optional, Protocol


class InvoiceHistoryPort(Protocol):
    def get_recent(self, store_id: int = None, limit: int = 50) -> List[Dict]:
        ...

    def get_completed_invoices(
        self,
        store_id: int,
        search_term: str = None,
        start_date: str = None,
        end_date: str = None,
    ) -> List[Dict]:
        ...

    def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict]:
        ...

    def get_invoice_items_by_id(self, invoice_id: int) -> List[Dict]:
        ...

    def get_items(self, invoice_number: str) -> List[Dict]:
        ...
