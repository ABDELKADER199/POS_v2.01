"""Professional PDF report builder for dashboard statistics.

The PDF is rendered by Qt QTextDocument, so the HTML intentionally avoids
modern CSS such as grid/flex/gradients and uses stable table-based layout.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from utils.printer_service import PrinterService
from ui.styles import COLORS


class StatsPdfReportService:
    """Builds a polished RTL statistics report and exports it as PDF."""

    def create_pdf(
        self,
        data: dict[str, Any],
        date_from: str,
        date_to: str,
        store_name: str,
        user_name: str,
    ) -> dict[str, Any]:
        html_content = self._build_html(data, date_from, date_to, store_name, user_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stats_report_{date_from}_{date_to}_{timestamp}".replace(":", "-")
        saved, pdf_path = PrinterService._save_as_pdf(
            html_content,
            width_pts=595,
            filename_prefix=filename,
            category="تقارير الإحصائيات",
            auto_open=True,
        )
        return {"saved": saved, "pdf_path": pdf_path}

    def _build_html(
        self,
        data: dict[str, Any],
        date_from: str,
        date_to: str,
        store_name: str,
        user_name: str,
    ) -> str:
        metrics = data.get("metrics") or {}
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
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
                .page {{
                    width: 100%;
                    background-color: #ffffff;
                }}
                .cover {{
                    background-color: #10224a;
                    color: {COLORS['text_on_brand']};
                    padding: 18px;
                    border-bottom: 5px solid #2563eb;
                }}
                .brand {{
                    color: #bfdbfe;
                    font-size: 12px;
                    font-weight: 800;
                }}
                .title {{
                    color: {COLORS['text_on_brand']};
                    font-size: 27px;
                    font-weight: 900;
                    margin-top: 5px;
                }}
                .meta {{
                    color: #dbeafe;
                    font-size: 11px;
                    line-height: 1.8;
                    margin-top: 8px;
                }}
                .content {{
                    padding: 14px;
                }}
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
                .metric-label {{
                    color: #64748b;
                    font-size: 10px;
                    font-weight: 800;
                    margin-bottom: 5px;
                }}
                .metric-value {{
                    color: #0f172a;
                    font-size: 17px;
                    font-weight: 900;
                }}
                .positive {{ color: #047857; }}
                .negative {{ color: #dc2626; }}
                .section {{
                    margin-top: 14px;
                }}
                .section-title {{
                    color: #0f172a;
                    background-color: #eaf1ff;
                    border-right: 5px solid #2563eb;
                    padding: 7px 10px;
                    font-size: 16px;
                    font-weight: 900;
                    margin-bottom: 7px;
                }}
                .data-table {{
                    width: 100%;
                    border-collapse: collapse;
                    table-layout: fixed;
                    font-size: 9.5px;
                }}
                .data-table th {{
                    background-color: #0f172a;
                    color: {COLORS['text_on_brand']};
                    padding: 7px 5px;
                    border: 1px solid #1e293b;
                    font-weight: 900;
                }}
                .data-table td {{
                    padding: 6px 5px;
                    border: 1px solid #dbe3ef;
                    text-align: center;
                    vertical-align: middle;
                    color: #111827;
                }}
                .even td {{
                    background-color: #f8fafc;
                }}
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
                    <div class="title">تقرير الإحصائيات</div>
                    <div class="meta">
                        الفترة: {self._safe(date_from)} إلى {self._safe(date_to)}<br>
                        الفرع: {self._safe(store_name)}<br>
                        المستخدم: {self._safe(user_name)}<br>
                        وقت الإنشاء: {self._safe(generated_at)}
                    </div>
                </div>

                <div class="content">
                    {self._metrics_table(metrics)}

                    {self._table_section("مبيعات الفروع", data.get("store_sales"), [
                        ("store_name", "الفرع"), ("total_sales", "المبيعات"), ("invoice_count", "عدد الفواتير")
                    ])}
                    {self._table_section("الأكثر مبيعًا", data.get("top_products"), [
                        ("product_name", "الصنف"), ("total_qty", "الكمية"), ("total_revenue", "الإيراد")
                    ])}
                    {self._table_section("كبار العملاء", data.get("top_customers"), [
                        ("customer_name", "العميل"), ("customer_phone", "الهاتف"), ("total_spent", "إجمالي الشراء"), ("favorite_product", "الصنف المفضل")
                    ])}
                    {self._table_section("الأكثر ارتجاعًا", data.get("most_returned"), [
                        ("product", "الصنف"), ("returned_qty", "الكمية المرتجعة")
                    ])}
                    {self._table_section("أسباب المرتجعات", data.get("return_reasons"), [
                        ("reason", "السبب"), ("reason_count", "التكرار")
                    ])}
                    {self._table_section("إحصائيات الموردين", data.get("supplier_stats"), [
                        ("supplier_name", "المورد"), ("total_purchases", "المشتريات"), ("total_paid", "المسدد"), ("remaining_balance", "المتبقي"), ("items_count", "الأصناف"), ("invoice_count", "الفواتير")
                    ], limit=15)}
                    {self._table_section("مبيعات الأصناف اليومية", data.get("product_sales_report"), [
                        ("product_code", "الكود"), ("product_name", "الصنف"), ("store_name", "الفرع"), ("sale_date", "التاريخ"), ("total_qty", "الكمية"), ("total_revenue", "الإيراد"), ("total_cost", "التكلفة")
                    ], limit=25)}
                    {self._table_section("تفاصيل الخصومات والعروض الترويجية", data.get("discount_breakdown"), [
                        ("discount_type", "نوع الخصم / العرض"), ("amount", "إجمالي المبلغ"), ("description", "الوصف والتفاصيل")
                    ])}
                </div>

                <div class="footer">
                    تم إنشاء التقرير تلقائيًا من نظام HyperPOS V2 بناءً على بيانات صفحة الإحصائيات الحالية.
                </div>
            </div>
        </body>
        </html>
        """

    def _metrics_table(self, metrics: dict[str, Any]) -> str:
        cards = [
            ("إجمالي المبيعات", self._money(metrics.get("total_sales")), ""),
            ("صافي الربح", self._money(metrics.get("net_profit")), self._class_for(metrics.get("net_profit"))),
            ("عدد الفواتير", self._number(metrics.get("invoice_count")), ""),
            ("متوسط البيع", self._money(metrics.get("avg_ticket")), ""),
            ("هامش الربح", f'{float(metrics.get("profit_margin") or 0):.1f}%', ""),
            ("المرتجعات", self._money(metrics.get("total_returns")), "negative"),
            ("المقبوضات النقدية", self._money(metrics.get("cash_in")), "positive"),
            ("المدفوعات النقدية", self._money(metrics.get("cash_out")), "negative"),
            ("صافي الحركة النقدية", self._money(metrics.get("net_cash")), self._class_for(metrics.get("net_cash"))),
            ("السيولة الحالية", self._money(metrics.get("vault_liquidity")), self._class_for(metrics.get("vault_liquidity"))),
            ("إجمالي المسدد", self._money(metrics.get("total_paid")), "positive"),
            ("إجمالي المديونية", self._money(metrics.get("total_debt")), "negative"),
        ]
        rows = []
        for index in range(0, len(cards), 3):
            cells = "".join(self._metric_cell(*card) for card in cards[index:index + 3])
            rows.append(f"<tr>{cells}</tr>")
        return f'<table class="metric-table" dir="rtl">{''.join(rows)}</table>'

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

    def _table_section(self, title: str, rows: Any, columns: list[tuple[str, str]], limit: int = 20) -> str:
        rows = list(rows or [])[:limit]
        if not rows:
            return ""
        header = "".join(f"<th>{self._safe(label)}</th>" for _, label in columns)
        body_rows = []
        for index, row in enumerate(rows):
            row_class = ' class="even"' if index % 2 else ""
            cells = "".join(f"<td>{self._format_cell(row.get(key))}</td>" for key, _ in columns)
            body_rows.append(f"<tr{row_class}>{cells}</tr>")
        return f"""
        <div class="section">
            <div class="section-title">{self._safe(title)}</div>
            <table class="data-table" dir="rtl">
                <thead><tr>{header}</tr></thead>
                <tbody>{''.join(body_rows)}</tbody>
            </table>
        </div>
        """

    def _format_cell(self, value: Any) -> str:
        if isinstance(value, float):
            return self._safe(f"{value:,.2f}")
        if isinstance(value, int):
            return self._safe(f"{value:,}")
        return self._safe(value if value not in (None, "") else "-")

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
            return "positive" if float(value or 0) >= 0 else "negative"
        except (TypeError, ValueError):
            return ""

    def _safe(self, value: Any) -> str:
        return html.escape(str(value))
