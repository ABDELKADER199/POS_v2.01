from application.use_cases.print_receipt import PrintReceiptUseCase
from application.use_cases.receipt_data import ReceiptDataUseCase
from application.use_cases.tax_invoice import SaveTaxInvoiceDetailsUseCase, TaxInvoiceUseCase
from models.invoice import InvoiceItem, TaxInvoiceDetails
from utils.printer_service import PrinterService


class FakeReceiptPrinter:
    def __init__(self):
        self.calls = []

    def print_receipt(self, invoice, items, cashier_name):
        self.calls.append(("print", invoice, items, cashier_name))
        return {"printed": True, "saved": True, "pdf_path": "receipt.pdf"}

    def save_receipt_as_pdf(self, invoice, items, cashier_name):
        self.calls.append(("pdf", invoice, items, cashier_name))
        return True


class FakeTaxInvoiceRepository:
    def __init__(self):
        self.invoice_id = 10
        self.upserted = None
        self.committed = False
        self.rolled_back = False
        self.raise_on_upsert = False

    def get_invoice_id_by_number(self, invoice_number):
        return self.invoice_id if invoice_number == "INV-1" else None

    def upsert_tax_details(
        self,
        invoice_id,
        company_name,
        tax_id_number,
        commercial_registry,
        company_address,
        company_phone,
        notes,
    ):
        if self.raise_on_upsert:
            raise RuntimeError("database error")
        self.upserted = {
            "invoice_id": invoice_id,
            "company_name": company_name,
            "tax_id_number": tax_id_number,
            "commercial_registry": commercial_registry,
            "company_address": company_address,
            "company_phone": company_phone,
            "notes": notes,
        }

    upsert_tax_customer_details = upsert_tax_details

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_receipt_data_builds_invoice_and_item_payloads():
    tax_details = TaxInvoiceDetails(
        company_name="شركة الاختبار",
        tax_id_number="123456789",
        company_address="القاهرة",
    )
    use_case = ReceiptDataUseCase(
        current_items_provider=lambda: [
            InvoiceItem(
                product_id=1,
                product_code="1001",
                product_name="منتج",
                quantity=2,
                unit_price=50,
                discount=5,
                tax_percent=14,
            )
        ],
        totals_provider=lambda: {
            "subtotal": 90,
            "tax_total": 10,
            "manual_discount": 5,
            "promo_discount": 3,
            "total": 100,
        },
        applied_promos_provider=lambda: [{"name": "عرض"}],
        tax_invoice_provider=lambda: tax_details,
    )

    invoice, items = use_case.execute(
        "INV-1",
        drawer_id=7,
        payment_method="Mixed",
        cash_amount=60,
        card_amount=40,
        paid_amount=120,
        customer_name="عميل",
        customer_phone="010",
        customer_address="عنوان",
    )

    assert invoice["invoice_number"] == "INV-1"
    assert invoice["drawer_id"] == 7
    assert invoice["payment_method"] == "Mixed"
    assert invoice["cash_amount"] == 60
    assert invoice["card_amount"] == 40
    assert invoice["total_amount"] == 100
    assert invoice["change"] == 20
    assert invoice["tax_invoice_data"]["company_name"] == "شركة الاختبار"
    assert invoice["applied_promos"] == [{"name": "عرض"}]
    assert items == [
        {
            "product_id": 1,
            "product_code": "1001",
            "product_name": "منتج",
            "quantity": 2,
            "price": 50,
            "total": 95,
            "tax_percent": 14,
            "discount": 5,
            "gross_total": 100,
            "promo_discount": 0.0,
            "line_discount": 5.0,
        }
    ]


def test_receipt_data_does_not_create_change_for_unpaid_invoice():
    use_case = ReceiptDataUseCase(
        current_items_provider=lambda: [],
        totals_provider=lambda: {
            "subtotal": 100,
            "tax_total": 0,
            "manual_discount": 0,
            "promo_discount": 0,
            "total": 100,
        },
        applied_promos_provider=lambda: [],
        tax_invoice_provider=lambda: None,
    )

    invoice, items = use_case.execute("INV-2", 1, "Credit", 0, 0, paid_amount=0)

    assert invoice["change"] == 0
    assert invoice["tax_invoice_data"] is None
    assert items == []


def test_print_receipt_use_case_dispatches_to_physical_print():
    printer = FakeReceiptPrinter()
    invoice = {"invoice_number": "INV-1"}
    items = [{"product_name": "منتج"}]

    result = PrintReceiptUseCase(printer).execute(invoice, items, "الكاشير")

    assert result == {"printed": True, "saved": True, "pdf_path": "receipt.pdf"}
    assert printer.calls == [("print", invoice, items, "الكاشير")]


def test_print_receipt_use_case_dispatches_to_pdf():
    printer = FakeReceiptPrinter()
    invoice = {"invoice_number": "INV-1"}
    items = [{"product_name": "منتج"}]

    result = PrintReceiptUseCase(printer).execute(invoice, items, "الكاشير", as_pdf=True)

    assert result is True
    assert printer.calls == [("pdf", invoice, items, "الكاشير")]


def test_printer_service_print_receipt_generates_html_and_archives_pdf(monkeypatch):
    captured = {}

    def fake_print_html(html, receipt_height_est, filename_prefix, category, **kwargs):
        captured.update(
            {
                "html": html,
                "receipt_height_est": receipt_height_est,
                "filename_prefix": filename_prefix,
                "category": category,
                **kwargs,
            }
        )
        return {"printed": False, "saved": True, "pdf_path": "invoice.pdf"}

    monkeypatch.setattr(
        PrinterService,
        "_load_settings",
        staticmethod(
            lambda: {
                "store_name": "HyperPOS",
                "business_legal_name": "HyperPOS LLC",
                "tax_number": "123",
                "tax_enabled": "0",
            }
        ),
    )
    monkeypatch.setattr(PrinterService, "_get_barcode_html", staticmethod(lambda code: f"<barcode>{code}</barcode>"))
    monkeypatch.setattr(PrinterService, "_print_html_document", staticmethod(fake_print_html))

    result = PrinterService.print_receipt(
        {
            "invoice_number": "INV-5",
            "drawer_id": 2,
            "payment_method": "Cash",
            "subtotal": 120,
            "discount": 10,
            "promo_discount": 5,
            "tax_amount": 0,
            "total_amount": 105,
            "tendered": 110,
            "change": 5,
            "customer_name": "عميل",
        },
        [{"product_name": "<منتج>", "product_code": "P-1", "quantity": 2, "price": 60, "total": 120}],
        "الكاشير",
    )

    assert result == {"printed": False, "saved": True, "pdf_path": "invoice.pdf"}
    assert captured["filename_prefix"] == "INV-5"
    assert captured["receipt_height_est"] == 545
    assert "HyperPOS LLC" in captured["html"]
    assert "&lt;منتج&gt;" in captured["html"]
    assert "<منتج>" not in captured["html"]
    assert "<barcode>INV-5</barcode>" in captured["html"]


def test_printer_service_save_receipt_as_pdf_uses_thermal_width(monkeypatch):
    captured = {}

    def fake_save_pdf(html, width_pts, filename_prefix, category, auto_open):
        captured.update(
            {
                "html": html,
                "width_pts": width_pts,
                "filename_prefix": filename_prefix,
                "category": category,
                "auto_open": auto_open,
            }
        )
        return True, "invoice.pdf"

    monkeypatch.setattr(PrinterService, "_load_settings", staticmethod(lambda: {"store_name": "HyperPOS"}))
    monkeypatch.setattr(PrinterService, "_get_barcode_html", staticmethod(lambda code: ""))
    monkeypatch.setattr(PrinterService, "_save_as_pdf", staticmethod(fake_save_pdf))

    result = PrinterService.save_receipt_as_pdf(
        {"invoice_number": "INV-6", "total_amount": 50},
        [{"product_name": "منتج", "quantity": 1, "price": 50}],
        "الكاشير",
    )

    assert result == {"printed": False, "saved": True, "pdf_path": "invoice.pdf"}
    assert captured["width_pts"] == 226
    assert captured["filename_prefix"] == "INV-6"
    assert captured["auto_open"] is True


def test_purchase_invoice_pdf_uses_cart_item_name_without_unknown(monkeypatch):
    captured = {}

    def fake_save_pdf(html, width_pts, filename_prefix, category, auto_open):
        captured.update(
            {
                "html": html,
                "width_pts": width_pts,
                "filename_prefix": filename_prefix,
                "category": category,
                "auto_open": auto_open,
            }
        )
        return True, "purchase.pdf"

    monkeypatch.setattr(PrinterService, "_load_settings", staticmethod(lambda: {"store_name": "HyperPOS"}))
    monkeypatch.setattr(PrinterService, "_save_as_pdf", staticmethod(fake_save_pdf))

    result = PrinterService.save_purchase_invoice_as_pdf(
        {"invoice_number": "PUR-1", "total_amount": 1600, "supplier_name": "مورد"},
        [{"name": "<منتج شراء>", "quantity": 10, "cost": 160}],
        "المطور",
    )

    assert result == {"saved": True, "pdf_path": "purchase.pdf"}
    assert captured["width_pts"] == 226
    assert captured["filename_prefix"] == "Purchase_PUR-1"
    assert "&lt;منتج شراء&gt;" in captured["html"]
    assert "Unknown" not in captured["html"]


def test_tax_invoice_use_case_sets_and_clears_details():
    use_case = TaxInvoiceUseCase()

    use_case.set({"company_name": "شركة", "tax_id_number": "123"})

    assert use_case.is_enabled() is True
    assert use_case.data.company_name == "شركة"
    assert use_case.data.tax_id_number == "123"

    use_case.clear()

    assert use_case.is_enabled() is False
    assert use_case.data is None


def test_save_tax_invoice_details_validates_required_fields():
    repo = FakeTaxInvoiceRepository()
    use_case = SaveTaxInvoiceDetailsUseCase(repo)

    assert use_case.execute("", "شركة") is False
    assert use_case.execute("INV-1", "") is False
    assert repo.upserted is None
    assert repo.committed is False


def test_save_tax_invoice_details_upserts_and_commits():
    repo = FakeTaxInvoiceRepository()

    result = SaveTaxInvoiceDetailsUseCase(repo).execute(
        " INV-1 ",
        " شركة ",
        tax_id_number="123",
        commercial_registry="456",
        company_address="القاهرة",
        company_phone="010",
        notes="ملاحظة",
    )

    assert result is True
    assert repo.upserted == {
        "invoice_id": 10,
        "company_name": "شركة",
        "tax_id_number": "123",
        "commercial_registry": "456",
        "company_address": "القاهرة",
        "company_phone": "010",
        "notes": "ملاحظة",
    }
    assert repo.committed is True
    assert repo.rolled_back is False


def test_save_tax_invoice_details_rolls_back_on_repository_error():
    repo = FakeTaxInvoiceRepository()
    repo.raise_on_upsert = True

    result = SaveTaxInvoiceDetailsUseCase(repo).execute("INV-1", "شركة")

    assert result is False
    assert repo.committed is False
    assert repo.rolled_back is True



def test_purchase_return_pdf_uses_return_items_and_purchase_return_folder(monkeypatch):
    captured = {}

    def fake_save_pdf(html, width_pts, filename_prefix, category, auto_open):
        captured.update(
            {
                "html": html,
                "width_pts": width_pts,
                "filename_prefix": filename_prefix,
                "category": category,
                "auto_open": auto_open,
            }
        )
        return True, "purchase_return.pdf"

    monkeypatch.setattr(PrinterService, "_load_settings", staticmethod(lambda: {"store_name": "HyperPOS"}))
    monkeypatch.setattr(PrinterService, "_get_barcode_html", staticmethod(lambda code: f"<barcode>{code}</barcode>"))
    monkeypatch.setattr(PrinterService, "_save_as_pdf", staticmethod(fake_save_pdf))

    result = PrinterService.save_purchase_return_as_pdf(
        {
            "return_number": "PR-1",
            "invoice_number": "PUR-1",
            "supplier_name": "Supplier",
            "total_amount": 60,
            "settlement_method": "credit",
            "reason": "Damaged",
        },
        [{"product_name": "<Return Item>", "quantity": 2, "unit_cost": 30}],
        "Tester",
    )

    assert result == {"saved": True, "pdf_path": "purchase_return.pdf"}
    assert captured["width_pts"] == 226
    assert captured["filename_prefix"] == "Purchase_Return_PR-1"
    assert captured["category"] == "\u0627\u0644\u0645\u0634\u062a\u0631\u064a\u0627\u062a/\u0645\u0631\u062a\u062c\u0639\u0627\u062a \u0627\u0644\u0645\u0634\u062a\u0631\u064a\u0627\u062a"
    assert "&lt;Return Item&gt;" in captured["html"]
    assert "<barcode>PR-1</barcode>" in captured["html"]
