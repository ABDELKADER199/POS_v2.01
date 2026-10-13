from utils.printer_service import PrinterService


class ReceiptPrinterAdapter:
    def print_receipt(self, invoice: dict, items: list[dict], cashier_name: str):
        return PrinterService.print_receipt(invoice, items, cashier_name)

    def save_receipt_as_pdf(self, invoice: dict, items: list[dict], cashier_name: str):
        return PrinterService.save_receipt_as_pdf(invoice, items, cashier_name)
