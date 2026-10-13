from application.ports.receipt_printer_port import ReceiptPrinterPort


class PrintReceiptUseCase:
    def __init__(self, printer: ReceiptPrinterPort):
        self.printer = printer

    def execute(self, invoice: dict, items: list[dict], cashier_name: str, as_pdf: bool = False):
        if as_pdf:
            return self.printer.save_receipt_as_pdf(invoice, items, cashier_name)
        return self.printer.print_receipt(invoice, items, cashier_name)
