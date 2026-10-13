import sys
import types

if "barcode" not in sys.modules:
    fake_barcode_module = types.ModuleType("barcode")
    fake_barcode_module.get = lambda *args, **kwargs: None
    sys.modules["barcode"] = fake_barcode_module

if "barcode.writer" not in sys.modules:
    fake_barcode_writer_module = types.ModuleType("barcode.writer")
    fake_barcode_writer_module.ImageWriter = lambda: "writer"
    sys.modules["barcode.writer"] = fake_barcode_writer_module

from utils import barcode_service
from utils.barcode_service import BarcodeService
from utils.printer_service import BarcodePrintJob, PrinterService


class FakeBarcode:
    def __init__(self):
        self.saved = None

    def save(self, filepath, options=None):
        self.saved = (filepath, options)
        return f"{filepath}.png"


class FakeBarcodeFactory:
    def __init__(self):
        self.calls = []
        self.barcode = FakeBarcode()

    def get(self, barcode_type, code, writer=None):
        self.calls.append((barcode_type, code, writer))
        return self.barcode


class FakePrinterInfo:
    def __init__(self, name="", is_null=False):
        self._name = name
        self._is_null = is_null

    def printerName(self):
        return self._name

    def isNull(self):
        return self._is_null


def install_fake_qprinter_info(monkeypatch, available=None, default=None):
    fake_print_support = types.ModuleType("PyQt6.QtPrintSupport")

    class FakeQPrinterInfo:
        @staticmethod
        def availablePrinters():
            return available or []

        @staticmethod
        def defaultPrinter():
            return default or FakePrinterInfo(is_null=True)

    fake_print_support.QPrinterInfo = FakeQPrinterInfo
    monkeypatch.setitem(sys.modules, "PyQt6", types.ModuleType("PyQt6"))
    monkeypatch.setitem(sys.modules, "PyQt6.QtPrintSupport", fake_print_support)


def test_barcode_service_generates_default_40x25_options(tmp_path, monkeypatch):
    fake_factory = FakeBarcodeFactory()
    monkeypatch.setattr(barcode_service, "barcode", fake_factory)
    monkeypatch.setattr(barcode_service, "ImageWriter", lambda: "writer")

    path = BarcodeService.generate_barcode("123", "منتج", output_dir=tmp_path)

    expected_filepath = str(tmp_path / "barcode_123_40x25")
    assert path == f"{expected_filepath}.png"
    assert fake_factory.calls == [("code128", "123", "writer")]
    assert fake_factory.barcode.saved == (
        expected_filepath,
        {
            "module_height": 12.0,
            "module_width": 0.45,
            "font_size": 8,
            "text_distance": 2.5,
            "quiet_zone": 1.5,
            "center_text": True,
            "write_text": True,
        },
    )


def test_barcode_service_generates_50x30_and_30x20_options(tmp_path, monkeypatch):
    fake_factory = FakeBarcodeFactory()
    monkeypatch.setattr(barcode_service, "barcode", fake_factory)
    monkeypatch.setattr(barcode_service, "ImageWriter", lambda: "writer")

    BarcodeService.generate_barcode("A1", "منتج", output_dir=tmp_path, label_size="50x30", write_text=False)
    assert fake_factory.barcode.saved[1]["module_height"] == 15.0
    assert fake_factory.barcode.saved[1]["font_size"] == 10
    assert fake_factory.barcode.saved[1]["write_text"] is False

    BarcodeService.generate_barcode("A2", "منتج", output_dir=tmp_path, label_size="30x20")
    assert fake_factory.barcode.saved[1]["module_height"] == 10.0
    assert fake_factory.barcode.saved[1]["font_size"] == 7


def test_barcode_service_returns_none_when_image_writer_missing(monkeypatch):
    monkeypatch.setattr(barcode_service, "ImageWriter", None)
    monkeypatch.setattr(BarcodeService, "_missing_writer_reported", False)

    assert BarcodeService.generate_barcode("123", "منتج") is None
    assert BarcodeService._missing_writer_reported is True


def test_barcode_service_returns_none_when_generation_fails(monkeypatch):
    class FailingBarcodeFactory:
        def get(self, *args, **kwargs):
            raise RuntimeError("bad barcode")

    monkeypatch.setattr(barcode_service, "barcode", FailingBarcodeFactory())
    monkeypatch.setattr(barcode_service, "ImageWriter", lambda: "writer")

    assert BarcodeService.generate_barcode("123", "منتج") is None


def test_format_barcode_price_handles_empty_numeric_and_text_values():
    assert PrinterService._format_barcode_price(None) == ""
    assert PrinterService._format_barcode_price("") == ""
    assert PrinterService._format_barcode_price("12.5").startswith("12.50")
    assert PrinterService._format_barcode_price("سعر خاص") == "سعر خاص"


def test_print_barcode_labels_counts_successful_copies(monkeypatch):
    calls = []
    results = iter([True, False, True])

    def fake_print_direct(name, code, printer_name, label_size="40x25", price=None, store_name=None):
        calls.append((name, code, printer_name, label_size, price, store_name))
        return next(results)

    monkeypatch.setattr(PrinterService, "print_barcode_direct", staticmethod(fake_print_direct))

    count = PrinterService.print_barcode_labels(
        BarcodePrintJob(
            name="منتج",
            code="123",
            printer_name="Printer",
            label_size="50x30",
            price="20",
            store_name="فرع",
            copies=3,
        )
    )

    assert count == 2
    assert calls == [
        ("منتج", "123", "Printer", "50x30", "20", "فرع"),
        ("منتج", "123", "Printer", "50x30", "20", "فرع"),
        ("منتج", "123", "Printer", "50x30", "20", "فرع"),
    ]


def test_print_barcode_labels_prints_at_least_one_copy(monkeypatch):
    calls = []
    monkeypatch.setattr(
        PrinterService,
        "print_barcode_direct",
        staticmethod(lambda *args, **kwargs: calls.append((args, kwargs)) or True),
    )

    count = PrinterService.print_barcode_labels(BarcodePrintJob(name="منتج", code="123", copies=0))

    assert count == 1
    assert len(calls) == 1


def test_print_barcode_direct_returns_false_when_image_missing(monkeypatch):
    monkeypatch.setattr(BarcodeService, "generate_barcode", staticmethod(lambda *args, **kwargs: None))

    assert PrinterService.print_barcode_direct("منتج", "123", "Printer") is False


def test_print_barcode_direct_saves_image_when_no_real_printer(tmp_path, monkeypatch):
    barcode_path = tmp_path / "barcode.png"
    barcode_path.write_bytes(b"barcode-bytes")
    captured = {}

    install_fake_qprinter_info(monkeypatch)
    monkeypatch.setattr(
        BarcodeService,
        "generate_barcode",
        staticmethod(lambda code, name, label_size="40x25", write_text=True: str(barcode_path)),
    )
    monkeypatch.setattr(PrinterService, "_is_virtual_printer", staticmethod(lambda printer: True))
    monkeypatch.setattr(
        PrinterService,
        "_save_barcode_as_image",
        staticmethod(
            lambda html, w_pts, h_pts, code, name="", price_str="", label_size="40x25": captured.update(
                {
                    "html": html,
                    "w_pts": w_pts,
                    "h_pts": h_pts,
                    "code": code,
                    "name": name,
                    "price_str": price_str,
                    "label_size": label_size,
                }
            )
            or True
        ),
    )

    result = PrinterService.print_barcode_direct("منتج", "123", "Virtual PDF", label_size="30x20", price="12.5")

    assert result is True
    assert captured["w_pts"] == 85.0
    assert captured["h_pts"] == 56.7
    assert captured["code"] == "123"
    assert captured["name"] == "منتج"
    assert captured["price_str"].startswith("12.50")
    assert captured["label_size"] == "30x20"
    assert "data:image/png;base64,YmFyY29kZS1ieXRlcw==" in captured["html"]


def test_print_barcode_direct_uses_physical_printer_when_available(tmp_path, monkeypatch):
    barcode_path = tmp_path / "barcode.png"
    barcode_path.write_bytes(b"barcode-bytes")
    physical = FakePrinterInfo("Thermal")
    captured = {}

    install_fake_qprinter_info(monkeypatch, available=[physical], default=FakePrinterInfo(is_null=True))
    monkeypatch.setattr(
        BarcodeService,
        "generate_barcode",
        staticmethod(lambda code, name, label_size="40x25", write_text=True: str(barcode_path)),
    )
    monkeypatch.setattr(PrinterService, "_is_virtual_printer", staticmethod(lambda printer: False))
    monkeypatch.setattr(
        PrinterService,
        "_print_html_document",
        staticmethod(
            lambda html, receipt_height_est, width_pts, printer_name, filename_prefix: captured.update(
                {
                    "html": html,
                    "receipt_height_est": receipt_height_est,
                    "width_pts": width_pts,
                    "printer_name": printer_name,
                    "filename_prefix": filename_prefix,
                }
            )
            or {"printed": True}
        ),
    )

    result = PrinterService.print_barcode_direct("منتج", "123", "Thermal", label_size="50x30", price="10")

    assert result == {"printed": True}
    assert captured["receipt_height_est"] == 85.0
    assert captured["width_pts"] == 141.7
    assert captured["printer_name"] == "Thermal"
    assert captured["filename_prefix"] == "Barcode"
