from services.inventory_count_pdf_report_service import InventoryCountPdfReportService


def test_inventory_count_pdf_report_uses_approved_count_data(monkeypatch):
    captured = {}

    def fake_save_pdf(html_content, width_pts, filename_prefix, category, auto_open):
        captured["html"] = html_content
        captured["width_pts"] = width_pts
        captured["filename_prefix"] = filename_prefix
        captured["category"] = category
        captured["auto_open"] = auto_open
        return True, "inventory-count.pdf"

    monkeypatch.setattr(
        "services.inventory_count_pdf_report_service.PrinterService._save_as_pdf",
        staticmethod(fake_save_pdf),
    )

    result = InventoryCountPdfReportService().create_pdf(
        {
            "count_number": "CNT-1",
            "store_name": "فرع الاختبار",
            "count_type": "full",
        },
        [
            {
                "product_code": "1001",
                "product_name": "صنف زائد",
                "book_quantity": 10,
                "actual_quantity": 12,
                "variance": 2,
                "unit_cost": 5,
            },
            {
                "product_code": "1002",
                "product_name": "صنف ناقص",
                "book_quantity": 4,
                "actual_quantity": 1,
                "variance": -3,
                "unit_cost": 8,
            },
            {
                "product_code": "1003",
                "product_name": "صنف غير معدود",
                "book_quantity": 8,
                "actual_quantity": None,
                "variance": None,
                "unit_cost": 3,
            },
        ],
        {"name": "المطور"},
    )

    assert result == {"saved": True, "pdf_path": "inventory-count.pdf"}
    assert captured["width_pts"] == 595
    assert captured["category"] == "تقارير الجرد"
    assert captured["auto_open"] is True
    assert "تقرير اعتماد جرد المخزون" in captured["html"]
    assert "CNT-1" in captured["html"]
    assert "صنف زائد" in captured["html"]
    assert "صنف ناقص" in captured["html"]
    assert "صنف غير معدود" not in captured["html"]
    assert "صافي أثر الجرد" in captured["html"]
