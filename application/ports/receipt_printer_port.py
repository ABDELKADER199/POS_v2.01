from typing import Protocol


class ReceiptPrinterPort(Protocol):
    def print_receipt(self, invoice: dict, items: list[dict], cashier_name: str):
        ...

    def save_receipt_as_pdf(self, invoice: dict, items: list[dict], cashier_name: str):
        ...
