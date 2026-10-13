from typing import Dict, List, Optional

from application.ports.invoice_history_port import InvoiceHistoryPort


class InvoiceHistoryUseCase:
    def __init__(self, invoice_repo: InvoiceHistoryPort):
        self.invoice_repo = invoice_repo

    def get_recent_invoices(self, store_id: int = None, limit: int = 50) -> List[Dict]:
        return self.invoice_repo.get_recent(store_id=store_id, limit=limit)

    def get_completed_invoices(
        self,
        store_id: int,
        search_term: str = None,
        start_date: str = None,
        end_date: str = None,
    ) -> List[Dict]:
        return self.invoice_repo.get_completed_invoices(
            store_id,
            search_term,
            start_date,
            end_date,
        )

    def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict]:
        return self.invoice_repo.get_invoice_by_id(invoice_id)

    def get_invoice_items_by_id(self, invoice_id: int) -> List[Dict]:
        return self.invoice_repo.get_invoice_items_by_id(invoice_id)

    def get_invoice_items(self, invoice_number: str) -> List[Dict]:
        return self.invoice_repo.get_items(invoice_number)
