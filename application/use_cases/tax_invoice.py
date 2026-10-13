from typing import Optional

import logging

from application.ports.tax_invoice_port import TaxInvoiceRepositoryPort
from models.invoice import TaxInvoiceDetails

logger = logging.getLogger(__name__)


class TaxInvoiceUseCase:
    def __init__(self):
        self.data: Optional[TaxInvoiceDetails] = None

    def set(self, data: dict):
        self.data = TaxInvoiceDetails.from_dict(data)

    def clear(self):
        self.data = None

    def is_enabled(self) -> bool:
        return self.data is not None


class SaveTaxInvoiceDetailsUseCase:
    def __init__(self, invoice_repo: TaxInvoiceRepositoryPort):
        self.invoice_repo = invoice_repo

    def execute(
        self,
        invoice_number: str,
        company_name: str,
        tax_id_number: str = "",
        commercial_registry: str = "",
        company_address: str = "",
        company_phone: str = "",
        notes: str = "",
    ) -> bool:
        invoice_number = (invoice_number or "").strip()
        company_name = (company_name or "").strip()
        if not invoice_number or not company_name:
            return False
        try:
            invoice_id = self.invoice_repo.get_invoice_id_by_number(invoice_number)
            if not invoice_id:
                return False
            self.invoice_repo.upsert_tax_customer_details(
                invoice_id,
                company_name,
                tax_id_number,
                commercial_registry,
                company_address,
                company_phone,
                notes,
            )
            self.invoice_repo.commit()
            return True
        except Exception as exc:
            self.invoice_repo.rollback()
            logger.error("Error saving tax invoice details: %s", exc, exc_info=True)
            return False
