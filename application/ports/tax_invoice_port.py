from typing import Dict, Protocol


class TaxInvoiceRepositoryPort(Protocol):
    def get_invoice_id_by_number(self, invoice_number: str):
        ...

    def upsert_tax_details(
        self,
        invoice_id: int,
        company_name: str,
        tax_id_number: str = "",
        commercial_registry: str = "",
        company_address: str = "",
        company_phone: str = "",
        notes: str = "",
    ) -> None:
        ...

    def upsert_tax_customer_details(
        self,
        invoice_id: int,
        company_name: str,
        tax_id_number: str = "",
        commercial_registry: str = "",
        company_address: str = "",
        company_phone: str = "",
        notes: str = "",
    ) -> None:
        ...   

    def get_tax_customer_details(self, invoice_number: str) -> dict:
        ...     

    def get_tax_details(self, invoice_number: str) -> Dict:
        ...

    def commit(self):
        ...

    def rollback(self):
        ...
