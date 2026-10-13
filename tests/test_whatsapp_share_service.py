from pathlib import Path

from services.whatsapp_share_service import WhatsAppShareService


def test_whatsapp_share_service_normalizes_egyptian_phone_and_opens_chat(tmp_path):
    opened_urls = []
    revealed_files = []
    copied_files = []
    pasted = []
    pdf_path = tmp_path / "invoice.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")
    service = WhatsAppShareService(
        opener=lambda url: opened_urls.append(url) or True,
        file_revealer=lambda path: revealed_files.append(path),
        file_copier=lambda path: copied_files.append(path) or True,
        attach_automator=lambda: pasted.append(True) or True,
        attach_delay_seconds=0,
    )

    result = service.prepare_share("01070276578", str(pdf_path), "فاتورة اختبار")

    assert result.opened is True
    assert result.phone == "+201070276578"
    assert result.pdf_path == str(pdf_path.resolve())
    assert "whatsapp://send?phone=201070276578" in opened_urls[0]
    assert revealed_files == [str(pdf_path.resolve())]
    assert copied_files == [str(pdf_path.resolve())]
    assert pasted == [True]


def test_whatsapp_share_service_rejects_missing_pdf():
    service = WhatsAppShareService(opener=lambda url: True, file_revealer=lambda path: None)

    result = service.prepare_share("01070276578", "", "رسالة")

    assert result.opened is False
    assert result.error == "ملف PDF غير موجود"


def test_whatsapp_share_service_falls_back_to_web_when_desktop_protocol_fails(tmp_path):
    opened_urls = []
    copied_files = []
    pasted = []
    pdf_path = tmp_path / "invoice.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")

    def opener(url):
        opened_urls.append(url)
        return url.startswith("https://wa.me/")

    service = WhatsAppShareService(
        opener=opener,
        file_revealer=lambda path: None,
        file_copier=lambda path: copied_files.append(path) or True,
        attach_automator=lambda: pasted.append(True) or True,
        attach_delay_seconds=0,
    )

    result = service.prepare_share("01070276578", str(pdf_path), "message")

    assert result.opened is True
    assert opened_urls[0].startswith("whatsapp://send")
    assert opened_urls[1].startswith("https://wa.me/201070276578")
    assert copied_files == [str(pdf_path.resolve())]
    assert pasted == [True]


def test_whatsapp_share_service_sends_text_without_pdf():
    opened_urls = []
    service = WhatsAppShareService(opener=lambda url: opened_urls.append(url) or True)

    result = service.prepare_text_share("01070276578", "فاتورة\nالإجمالي: 100.00")

    assert result.opened is True
    assert result.phone == "+201070276578"
    assert result.pdf_path == ""
    assert result.message == "فاتورة\nالإجمالي: 100.00"
    assert "whatsapp://send?phone=201070276578" in opened_urls[0]
    assert "%D9%81%D8%A7%D8%AA%D9%88%D8%B1%D8%A9" in opened_urls[0]
