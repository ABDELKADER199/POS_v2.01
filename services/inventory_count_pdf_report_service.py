"""Professional PDF report for approved inventory count sessions."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from utils.printer_service import PrinterService
from ui.styles import COLORS


class InventoryCountPdfReportService:
    def create_pdf(self, session: dict[str, Any], items: list[dict[str, Any]], user_info: dict[str, Any]) -> dict[str, Any]:
        counted_items = [item for item in items if item.get("actual_quantity") is not None]
        html_content = self._build_html(session, counted_items, user_info)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        count_number = str(session.get("count_number") or "inventory_count").replace("/", "-").replace("\\", "-")
        filename = f"inventory_count_{count_number}_{timestamp}"
        saved, pdf_path = PrinterService._save_as_pdf(
            html_content,
            width_pts=595,
            filename_prefix=filename,
            category="تقارير الجرد",
            auto_open=True,
        )
        return {"saved": saved, "pdf_path": pdf_path}

    def _build_html(self, session: dict[str, Any], items: list[dict[str, Any]], user_info: dict[str, Any]) -> str:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        summary = self._summary(items)
        return f"""
        <!doctype html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: #eef3fb;
                    color: #0f172a;
                    font-family: "Tahoma", "Segoe UI", Arial, sans-serif;
                    direction: rtl;
                }}
                .page {{ width: 100%; background-color: #ffffff; }}
                .cover {{
                    background-color: #0f2248;
                    color: {COLORS['text_on_brand']};
                    padding: 18px;
                    border-bottom: 5px solid #16a34a;
                }}
                .brand {{ color: #bbf7d0; font-size: 12px; font-weight: 800; }}
                .title {{ color: {COLORS['text_on_brand']}; font-size: 27px; font-weight: 900; margin-top: 5px; }}
                .meta {{ color: #dbeafe; font-size: 11px; line-height: 1.9; margin-top: 8px; }}
                .content {{ padding: 14px; }}
                .metric-table {{
                    width: 100%;
                    border-collapse: separate;
                    border-spacing: 6px;
                    margin-bottom: 14px;
                }}
                .metric-box {{
                    background-color: #f8fafc;
                    border: 1px solid #dbe3ef;
                    padding: 9px;
                    text-align: right;
                }}
                .metric-label {{ color: #64748b; font-size: 10px; font-weight: 800; margin-bottom: 5px; }}
                .metric-value {{ color: #0f172a; font-size: 16px; font-weight: 900; }}
                .positive {{ color: #047857; }}
                .negative {{ color: #dc2626; }}
                .section-title {{
                    color: #0f172a;
                    background-color: #ecfdf5;
                    border-right: 5px solid #16a34a;
                    padding: 8px 10px;
                    font-size: 16px;
                    font-weight: 900;
                    margin: 12px 0 7px 0;
                }}
                .data-table {{
                    width: 100%;
                    border-collapse: collapse;
                    table-layout: fixed;
                    font-size: 9px;
                }}
                .data-table th {{
                    background-color: #0f172a;
                    color: {COLORS['text_on_brand']};
                    padding: 7px 4px;
                    border: 1px solid #1e293b;
                    font-weight: 900;
                }}
                .data-table td {{
                    padding: 6px 4px;
                    border: 1px solid #dbe3ef;
                    text-align: center;
                    vertical-align: middle;
                    color: #111827;
                }}
                .even td {{ background-color: #f8fafc; }}
                .increase {{ color: #047857; font-weight: 900; }}
                .decrease {{ color: #dc2626; font-weight: 900; }}
                .footer {{
                    margin: 18px 14px 0 14px;
                    padding: 10px 0;
                    border-top: 1px solid #dbe3ef;
                    color: #64748b;
                    font-size: 10px;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="page">
                <div class="cover">
                    <div class="brand">HyperPOS V2</div>
                    <div class="title">تقرير اعتماد جرد المخزون</div>
                    <div class="meta">
                        رقم الجرد: {self._safe(session.get("count_number"))}<br>
                        الفرع: {self._safe(session.get("store_name"))}<br>
                        نوع الجرد: {self._count_type_label(session.get("count_type"))}<br>
                        الحالة: معتمد<br>
                        المستخدم: {self._safe(user_info.get("name") or user_info.get("full_name") or user_info.get("username") or "مستخدم")}<br>
                        وقت إنشاء التقرير: {self._safe(generated_at)}
                    </div>
                </div>
                <div class="content">
                    {self._metrics_table(summary)}
                    <div class="section-title">تفاصيل الأصناف المعدودة</div>
                    {self._items_table(items)}
                </div>
                <div class="footer">
                    هذا التقرير يوثق تسوية الجرد المعتمدة. يتم تحديث المخزون للأصناف التي لها كمية فعلية مسجلة فقط.
                </div>
            </div>
        </body>
        </html>
        """

    def _summary(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        total_items = len(items)
        increases = sum(1 for item in items if int(item.get("variance") or 0) > 0)
        decreases = sum(1 for item in items if int(item.get("variance") or 0) < 0)
        no_change = sum(1 for item in items if int(item.get("variance") or 0) == 0)
        positive_value = sum(
            int(item.get("variance") or 0) * float(item.get("unit_cost") or 0)
            for item in items
            if int(item.get("variance") or 0) > 0
        )
        negative_value = sum(
            int(item.get("variance") or 0) * float(item.get("unit_cost") or 0)
            for item in items
            if int(item.get("variance") or 0) < 0
        )
        net_value = positive_value + negative_value
        return {
            "total_items": total_items,
            "increases": increases,
            "decreases": decreases,
            "no_change": no_change,
            "positive_value": positive_value,
            "negative_value": negative_value,
            "net_value": net_value,
        }

    def _metrics_table(self, summary: dict[str, Any]) -> str:
        cards = [
            ("الأصناف المعدودة", self._number(summary["total_items"]), ""),
            ("زيادات الكمية", self._number(summary["increases"]), "positive"),
            ("عجز الكمية", self._number(summary["decreases"]), "negative"),
            ("بدون فرق", self._number(summary["no_change"]), ""),
            ("قيمة الزيادة", self._money(summary["positive_value"]), "positive"),
            ("قيمة العجز", self._money(summary["negative_value"]), "negative"),
            ("صافي أثر الجرد", self._money(summary["net_value"]), self._class_for(summary["net_value"])),
        ]
        rows = []
        for index in range(0, len(cards), 3):
            cells = "".join(self._metric_cell(*card) for card in cards[index:index + 3])
            rows.append(f"<tr>{cells}</tr>")
        return f'<table class="metric-table" dir="rtl">{"".join(rows)}</table>'

    def _metric_cell(self, label: str, value: str, value_class: str = "") -> str:
        value_cls = f"metric-value {value_class}".strip()
        return (
            '<td width="33%" valign="top">'
            '<div class="metric-box">'
            f'<div class="metric-label">{self._safe(label)}</div>'
            f'<div class="{value_cls}">{self._safe(value)}</div>'
            "</div>"
            "</td>"
        )

    def _items_table(self, items: list[dict[str, Any]]) -> str:
        if not items:
            return '<div class="metric-box">لا توجد أصناف معدودة في هذا الجرد.</div>'
        rows = []
        for index, item in enumerate(items):
            variance = int(item.get("variance") or 0)
            unit_cost = float(item.get("unit_cost") or 0)
            variance_class = "increase" if variance > 0 else "decrease" if variance < 0 else ""
            row_class = ' class="even"' if index % 2 else ""
            rows.append(
                f"""
                <tr{row_class}>
                    <td>{index + 1}</td>
                    <td>{self._safe(item.get("product_code") or item.get("barcode") or "-")}</td>
                    <td>{self._safe(item.get("product_name"))}</td>
                    <td>{self._number(item.get("book_quantity"))}</td>
                    <td>{self._number(item.get("actual_quantity"))}</td>
                    <td class="{variance_class}">{self._number(variance)}</td>
                    <td>{self._money(unit_cost)}</td>
                    <td class="{variance_class}">{self._money(variance * unit_cost)}</td>
                    <td>{self._safe(item.get("notes") or "-")}</td>
                </tr>
                """
            )
        return f"""
        <table class="data-table" dir="rtl">
            <thead>
                <tr>
                    <th width="5%">م</th>
                    <th width="13%">الكود</th>
                    <th width="27%">الصنف</th>
                    <th width="9%">الدفتري</th>
                    <th width="9%">الفعلي</th>
                    <th width="8%">الفرق</th>
                    <th width="10%">التكلفة</th>
                    <th width="11%">قيمة الفرق</th>
                    <th width="8%">ملاحظة</th>
                </tr>
            </thead>
            <tbody>{"".join(rows)}</tbody>
        </table>
        """

    def _count_type_label(self, count_type: Any) -> str:
        labels = {
            "full": "جرد كامل",
            "partial": "جرد جزئي",
            "cycle": "جرد دوري",
            "spot": "جرد سريع",
        }
        return self._safe(labels.get(str(count_type or ""), count_type or "-"))

    def _money(self, value: Any) -> str:
        try:
            return f"{float(value or 0):,.2f} ج.م"
        except (TypeError, ValueError):
            return "0.00 ج.م"

    def _number(self, value: Any) -> str:
        try:
            return f"{int(value or 0):,}"
        except (TypeError, ValueError):
            return "0"

    def _class_for(self, value: Any) -> str:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            number = 0
        if number > 0:
            return "positive"
        if number < 0:
            return "negative"
        return ""

    def _safe(self, value: Any) -> str:
        return html.escape(str(value if value not in (None, "") else "-"))
