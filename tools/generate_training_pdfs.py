from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QMarginsF, QRectF, QSizeF, Qt
from PyQt6.QtGui import QColor, QFont, QImage, QPageLayout, QPageSize, QPainter, QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import QApplication
from ui.styles import COLORS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "الدليل_التعليمي_PDF"
PREVIEW_DIR = OUTPUT_DIR / "_معاينة_الصفحات"


@dataclass(frozen=True)
class GuideDocument:
    file_name: str
    title: str
    subtitle: str
    sections: list[tuple[str, str]]


def slug_file_name(name: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*]+', "_", name).strip()
    return clean or "guide.pdf"


def html_page(title: str, subtitle: str, sections: list[tuple[str, str]]) -> str:
    rendered_sections = "\n".join(
        f"""
        <section class="section">
            <h2>{heading}</h2>
            {body}
        </section>
        """
        for heading, body in sections
    )
    return f"""
    <!doctype html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                direction: rtl;
                font-family: "Tahoma", "Arial", sans-serif;
                color: #172033;
                background: #ffffff;
                font-size: 12.5pt;
                line-height: 1.55;
            }}
            .cover {{
                background: #0f172a;
                color: {COLORS['text_on_brand']};
                border-radius: 16px;
                padding: 30px 34px;
                margin-bottom: 22px;
            }}
            .brand {{
                color: #93c5fd;
                font-size: 12pt;
                font-weight: 700;
                letter-spacing: 0.6px;
            }}
            h1 {{
                font-size: 28pt;
                margin: 8px 0 6px;
                color: {COLORS['text_on_brand']};
            }}
            .subtitle {{
                color: #dbeafe;
                font-size: 13pt;
            }}
            h2 {{
                color: #14532d;
                font-size: 18pt;
                margin: 18px 0 8px;
                border-bottom: 2px solid #bbf7d0;
                padding-bottom: 5px;
            }}
            h3 {{
                color: #1e3a8a;
                font-size: 14pt;
                margin: 14px 0 6px;
            }}
            p {{
                margin: 5px 0 9px;
            }}
            ul, ol {{
                margin-top: 4px;
                margin-bottom: 10px;
            }}
            li {{
                margin-bottom: 4px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0 14px;
            }}
            th {{
                background: #1e293b;
                color: {COLORS['text_on_brand']};
                padding: 8px;
                font-weight: 800;
            }}
            td {{
                border: 1px solid #dbe3ef;
                padding: 7px;
                vertical-align: top;
            }}
            tr:nth-child(even) td {{
                background: #f8fafc;
            }}
            .note {{
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-right: 6px solid #2563eb;
                border-radius: 10px;
                padding: 10px 13px;
                margin: 10px 0 14px;
            }}
            .warning {{
                background: #fff7ed;
                border: 1px solid #fed7aa;
                border-right: 6px solid #ea580c;
                border-radius: 10px;
                padding: 10px 13px;
                margin: 10px 0 14px;
            }}
            .checklist {{
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 10px;
                padding: 10px 13px;
            }}
            .footer {{
                color: #64748b;
                font-size: 10pt;
                border-top: 1px solid #e2e8f0;
                padding-top: 8px;
                margin-top: 26px;
            }}
        </style>
    </head>
    <body>
        <div class="cover">
            <div class="brand">HyperPOS V2 — دليل تدريبي للتشغيل الفعلي</div>
            <h1>{title}</h1>
            <div class="subtitle">{subtitle}</div>
        </div>
        {rendered_sections}
        <div class="footer">
            تم توليد هذا الملف من داخل مشروع HyperPOS V2. عند تحديث التطبيق يمكن إعادة توليد الأدلة بنفس السكربت.
        </div>
    </body>
    </html>
    """


def render_document_pages(app: QApplication, document: GuideDocument) -> list[QImage]:
    page_width = 1240
    page_height = 1754
    margin_x = 72
    margin_y = 68
    content_width = page_width - (margin_x * 2)
    content_height = page_height - (margin_y * 2)

    doc = QTextDocument()
    doc.setDefaultFont(app.font())
    doc.setDocumentMargin(0)
    doc.setHtml(html_page(document.title, document.subtitle, document.sections))
    doc.setTextWidth(content_width)
    doc.setPageSize(QSizeF(content_width, content_height))

    page_count = max(1, doc.pageCount())
    pages: list[QImage] = []
    for page_index in range(page_count):
        image = QImage(page_width, page_height, QImage.Format.Format_ARGB32)
        image.fill(QColor("#ffffff"))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.translate(margin_x, margin_y)
        painter.setClipRect(QRectF(0, 0, content_width, content_height))
        painter.translate(0, -page_index * content_height)
        doc.drawContents(
            painter,
            QRectF(0, page_index * content_height, content_width, content_height),
        )
        painter.end()
        pages.append(image)
    return pages


def write_pdf(app: QApplication, document: GuideDocument) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / slug_file_name(document.file_name)
    pages = render_document_pages(app, document)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(output_path))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)

    painter = QPainter(printer)
    page_rect = printer.pageRect(QPrinter.Unit.Point)
    for index, page in enumerate(pages):
        if index:
            printer.newPage()
        painter.drawImage(page_rect, page)
    painter.end()

    if pages:
        preview_name = output_path.stem + "_صفحة_1.png"
        pages[0].save(str(PREVIEW_DIR / preview_name), "PNG")
    return output_path


def build_documents() -> list[GuideDocument]:
    return [
        GuideDocument(
            "00_فهرس_الدليل.pdf",
            "فهرس الدليل التعليمي",
            "خريطة استخدام التطبيق حسب الأقسام والأدوار داخل السوبرماركت.",
            [
                (
                    "محتويات المجلد",
                    """
                    <table>
                        <tr><th>الملف</th><th>الغرض</th><th>المستخدم المستهدف</th></tr>
                        <tr><td>01 التشغيل وتسجيل الدخول</td><td>بدء اليوم، الدخول، وفهم الواجهة والسايدبار.</td><td>كل المستخدمين</td></tr>
                        <tr><td>02 الكاشير ودرج الكاشير</td><td>فتح الدرج، إنشاء الفاتورة، التعليق، الدفع والطباعة.</td><td>الكاشير ومدير الفرع</td></tr>
                        <tr><td>03 المنتجات والمخزون والباركود</td><td>إدارة الأصناف، الفروع، التحويلات، وطباعة الباركود.</td><td>المالك، المطور، المخزن</td></tr>
                        <tr><td>04 المشتريات والموردين</td><td>فواتير الشراء، الموردين، وسداد المستحقات.</td><td>المحاسب والإدارة</td></tr>
                        <tr><td>05 الحسابات والعروض والمرتجعات</td><td>الخزينة، المصروفات، العملاء، مجلة العروض، والمرتجعات.</td><td>الإدارة والمحاسب</td></tr>
                        <tr><td>06 الإدارة والصلاحيات والتقارير</td><td>المستخدمون، الأدوار، الإحصائيات، ونطاقات الفروع.</td><td>المالك والمطور ومدير الفرع</td></tr>
                        <tr><td>07 التشغيل اليومي والدعم</td><td>قائمة مراجعة افتتاح وإغلاق اليوم وحل الأعطال الشائعة.</td><td>المشرف اليومي</td></tr>
                    </table>
                    """,
                ),
                (
                    "قاعدة الاستخدام العامة",
                    """
                    <div class="note">
                    استخدم كل صفحة لغرضها فقط: البيع من صفحة الكاشير، ضبط الكميات من المخزون، المصروفات من الحسابات، وإدارة المستخدمين من لوحة الإدارة.
                    هذا يقلل الأخطاء المحاسبية ويجعل التقارير قابلة للمراجعة.
                    </div>
                    """,
                ),
            ],
        ),
        GuideDocument(
            "01_التشغيل_وتسجيل_الدخول.pdf",
            "التشغيل وتسجيل الدخول",
            "خطوات بدء البرنامج وفهم الواجهة الرئيسية بعد الانتقال إلى السايدبار.",
            [
                (
                    "تشغيل التطبيق",
                    """
                    <ol>
                        <li>افتح ملف التشغيل من مجلد <b>dist</b>: HyperPOS_V2.exe.</li>
                        <li>تأكد أن قاعدة البيانات تعمل قبل فتح البرنامج.</li>
                        <li>استخدم حسابك الشخصي ولا تشارك كلمة المرور مع موظف آخر.</li>
                        <li>بعد الدخول تظهر الصفحات المسموح بها فقط حسب دور المستخدم.</li>
                    </ol>
                    <div class="warning">
                    إذا لم يفتح التطبيق، تحقق أولًا من تشغيل MySQL ومن ملف الإعدادات .env، ثم أعد فتح التطبيق.
                    </div>
                    """,
                ),
                (
                    "الواجهة الرئيسية",
                    """
                    <table>
                        <tr><th>العنصر</th><th>وظيفته</th></tr>
                        <tr><td>السايدبار</td><td>التنقل بين الصفحات الرئيسية مثل الكاشير، المنتجات، الحسابات، والمشتريات.</td></tr>
                        <tr><td>زر القائمة</td><td>طي أو إظهار السايدبار لتوسيع مساحة العمل.</td></tr>
                        <tr><td>زر تحديث</td><td>إعادة تحميل بيانات الصفحة الحالية من قاعدة البيانات.</td></tr>
                        <tr><td>رسالة حالة الدرج</td><td>تعرض هل يوجد درج كاشير مفتوح في الفرع أم لا.</td></tr>
                    </table>
                    """,
                ),
                (
                    "أفضل ممارسة",
                    """
                    <div class="checklist">
                    <ul>
                        <li>ابدأ اليوم بفتح درج كاشير واضح المسؤولية.</li>
                        <li>لا تترك البرنامج مفتوحًا بحساب مدير على جهاز الكاشير.</li>
                        <li>استخدم زر تسجيل الخروج عند ترك الجهاز.</li>
                        <li>لا تعدل بيانات المنتجات أثناء ذروة البيع إلا عند الضرورة.</li>
                    </ul>
                    </div>
                    """,
                ),
            ],
        ),
        GuideDocument(
            "02_الكاشير_ودرج_الكاشير.pdf",
            "الكاشير ودرج الكاشير",
            "تشغيل نقطة البيع، استخدام الدرج المشترك، وحفظ الفواتير بطريقة قابلة للمراجعة.",
            [
                (
                    "فتح درج الكاشير",
                    """
                    <ol>
                        <li>افتح صفحة <b>درج الكاشير</b>.</li>
                        <li>أدخل الرصيد الافتتاحي الفعلي الموجود في الدرج.</li>
                        <li>اضغط فتح درج، ثم ارجع إلى صفحة الكاشير.</li>
                        <li>إذا كان هناك درج مفتوح في نفس الفرع، يستخدمه الكاشير حسب الصلاحية بدل فتح درج جديد.</li>
                    </ol>
                    """,
                ),
                (
                    "إنشاء فاتورة بيع",
                    """
                    <ol>
                        <li>امسح الباركود أو ابحث باسم المنتج.</li>
                        <li>راجع الكمية والسعر قبل الدفع.</li>
                        <li>أدخل بيانات العميل عند الحاجة فقط.</li>
                        <li>حدد طريقة الدفع والمبلغ المدفوع.</li>
                        <li>اضغط دفع وطباعة أو دفع وحفظ PDF.</li>
                    </ol>
                    <div class="note">
                    إذا لم توجد طابعة، يحفظ التطبيق نسخة PDF في مسار الفواتير/الخزينة حسب الشهر عند السيناريوهات المدعومة.
                    </div>
                    """,
                ),
                (
                    "الفواتير المعلقة والطلبات",
                    """
                    <table>
                        <tr><th>العملية</th><th>متى تستخدم؟</th><th>تنبيه</th></tr>
                        <tr><td>تعليق فاتورة</td><td>عندما يترك العميل الكاشير مؤقتًا.</td><td>لا تترك فواتير معلقة كثيرة بنهاية اليوم.</td></tr>
                        <tr><td>استرجاع فاتورة معلقة</td><td>عند عودة العميل لإكمال الدفع.</td><td>راجع الأسعار قبل الحفظ.</td></tr>
                        <tr><td>سجل الفواتير</td><td>للبحث عن فاتورة سابقة أو إعادة طباعة حسب الصلاحية.</td><td>إعادة الطباعة يجب أن تكون مبررة.</td></tr>
                    </table>
                    """,
                ),
                (
                    "إغلاق الدرج",
                    """
                    <ol>
                        <li>افتح صفحة درج الكاشير.</li>
                        <li>راجع إجمالي النقد المتوقع مقابل النقد الفعلي.</li>
                        <li>سجل أي فرق واضح في الملاحظات.</li>
                        <li>أغلق الدرج واحتفظ بتقرير الإغلاق.</li>
                    </ol>
                    """,
                ),
            ],
        ),
        GuideDocument(
            "03_المنتجات_والمخزون_والباركود.pdf",
            "المنتجات والمخزون والباركود",
            "إدارة الأصناف والكميات والتحويلات وطباعة الباركود داخل الفروع.",
            [
                (
                    "تبويبات إدارة المنتجات",
                    """
                    <table>
                        <tr><th>التبويب</th><th>الاستخدام</th></tr>
                        <tr><td>المنتجات</td><td>إضافة وتعديل بيانات الصنف، الأسعار، الوحدة، المورد، والصورة المحلية.</td></tr>
                        <tr><td>المخزون</td><td>عرض الكمية حسب الفرع، حد الأمان، وتعديل المخزون حسب الصلاحية.</td></tr>
                        <tr><td>إدارة الفئات</td><td>تنظيم الأصناف داخل مجموعات لتسهيل البحث والتقارير.</td></tr>
                        <tr><td>طباعة الباركود</td><td>اختيار المنتجات وعدد الملصقات ثم طباعة أو حفظ PDF.</td></tr>
                    </table>
                    """,
                ),
                (
                    "إضافة منتج جديد",
                    """
                    <ol>
                        <li>اضغط منتج جديد.</li>
                        <li>أدخل اسمًا واضحًا بدون اختصارات مبهمة.</li>
                        <li>أدخل كود الصنف أو الباركود بدقة.</li>
                        <li>حدد سعر الشراء وسعر البيع والوحدة والفئة.</li>
                        <li>أضف صورة المنتج محليًا عند توفرها، خاصة عند استخدام مجلة العروض.</li>
                    </ol>
                    """,
                ),
                (
                    "المخزون والتحويل",
                    """
                    <div class="checklist">
                    <ul>
                        <li>استخدم فلتر الفرع لعرض مخزون فرع محدد.</li>
                        <li>استخدم تعديل المخزون فقط للتسوية أو الجرد.</li>
                        <li>استخدم زر التحويل بجانب المنتج لنقل كمية من فرع إلى فرع.</li>
                        <li>لا تستخدم التسوية بدل التحويل حتى لا تضيع حركة المخزون.</li>
                    </ul>
                    </div>
                    """,
                ),
                (
                    "طباعة الباركود",
                    """
                    <ol>
                        <li>ادخل إلى تبويب طباعة الباركود.</li>
                        <li>ابحث عن المنتجات المطلوبة.</li>
                        <li>حدد عدد الملصقات لكل صنف.</li>
                        <li>اطبع مباشرة إذا كانت الطابعة جاهزة أو احفظ PDF عند عدم توفرها.</li>
                    </ol>
                    """,
                ),
            ],
        ),
        GuideDocument(
            "04_المشتريات_والموردين.pdf",
            "المشتريات والموردين",
            "إدخال فواتير الشراء، متابعة الموردين، وسداد المستحقات.",
            [
                (
                    "فاتورة شراء جديدة",
                    """
                    <ol>
                        <li>اختر المورد والفرع المستلم.</li>
                        <li>أضف الأصناف بالكميات وسعر الشراء.</li>
                        <li>راجع الإجمالي قبل الحفظ.</li>
                        <li>حدد المبلغ المدفوع وطريقة السداد.</li>
                        <li>احفظ الفاتورة لتحديث المخزون وحساب المورد.</li>
                    </ol>
                    """,
                ),
                (
                    "إدارة الموردين",
                    """
                    <table>
                        <tr><th>البيان</th><th>أفضل ممارسة</th></tr>
                        <tr><td>اسم المورد</td><td>استخدم الاسم التجاري الثابت لتجنب التكرار.</td></tr>
                        <tr><td>الهاتف</td><td>سجل رقمًا صالحًا للرجوع إليه عند كشف الحساب.</td></tr>
                        <tr><td>الرصيد المستحق</td><td>راجعه بعد كل فاتورة وسداد.</td></tr>
                        <tr><td>كشف الحساب</td><td>استخدمه عند مطابقة المديونية مع المورد.</td></tr>
                    </table>
                    """,
                ),
                (
                    "سداد المورد",
                    """
                    <ol>
                        <li>افتح سجل الموردين أو الحسابات.</li>
                        <li>اختر المورد واضغط دفع/سداد.</li>
                        <li>أدخل المبلغ الفعلي وطريقة السداد.</li>
                        <li>احفظ العملية وتأكد من انخفاض الرصيد المستحق.</li>
                    </ol>
                    <div class="warning">
                    لا تسدد من خارج النظام ثم تسجل لاحقًا دون مستند؛ هذا يسبب اختلافًا بين الخزينة والديون.
                    </div>
                    """,
                ),
            ],
        ),
        GuideDocument(
            "05_الحسابات_والعروض_والمرتجعات.pdf",
            "الحسابات والعروض والمرتجعات",
            "إدارة الخزينة، المصروفات، العملاء، الموردين، العروض، ومرتجع الفواتير.",
            [
                (
                    "الحسابات والمالية",
                    """
                    <table>
                        <tr><th>التبويب</th><th>المهمة</th></tr>
                        <tr><td>الخزينة</td><td>متابعة حركات النقد والإغلاق والتقارير المالية.</td></tr>
                        <tr><td>العملاء</td><td>متابعة أرصدة العملاء والتسويات.</td></tr>
                        <tr><td>الموردون</td><td>عرض المديونيات والسداد وكشف الحساب.</td></tr>
                        <tr><td>المصروفات</td><td>تسجيل مصروفات الفرع أو المصروفات العامة حسب الصلاحية.</td></tr>
                        <tr><td>السجل المالي</td><td>تتبع الحركات المالية ومراجعة مصدر كل حركة.</td></tr>
                        <tr><td>تحليل الديون</td><td>تحليل المستحقات والمتأخرات.</td></tr>
                    </table>
                    """,
                ),
                (
                    "العروض ومجلة العروض",
                    """
                    <ol>
                        <li>افتح تبويب العروض.</li>
                        <li>حدد المنتج والسعر بعد الخصم وفترة العرض.</li>
                        <li>راجع أن صورة المنتج محفوظة محليًا داخل بيانات المنتج.</li>
                        <li>اضغط إنشاء مجلة العروض PDF.</li>
                        <li>راجع الغلاف والمنتجات والأسعار قبل إرسالها للعملاء أو طباعتها.</li>
                    </ol>
                    <div class="note">
                    تم ضبط مجلة العروض للاعتماد على الصور المحلية فقط؛ لذلك يجب إضافة صورة المنتج يدويًا قبل إنشاء المجلة.
                    </div>
                    """,
                ),
                (
                    "مرتجع الفواتير",
                    """
                    <ol>
                        <li>افتح صفحة مرتجع فواتير.</li>
                        <li>ابحث برقم الفاتورة أو بيانات العميل.</li>
                        <li>حدد الأصناف المرتجعة والكميات بدقة.</li>
                        <li>راجع تأثير المرتجع على المخزون والخزينة.</li>
                        <li>احفظ المرتجع واحتفظ بالمستند الناتج عند الحاجة.</li>
                    </ol>
                    """,
                ),
            ],
        ),
        GuideDocument(
            "06_الإدارة_والصلاحيات_والتقارير.pdf",
            "الإدارة والصلاحيات والتقارير",
            "إدارة المستخدمين والأدوار والإحصائيات مع الحفاظ على نطاق كل فرع.",
            [
                (
                    "الأدوار الأساسية",
                    """
                    <table>
                        <tr><th>الدور</th><th>النطاق</th><th>أهم الصلاحيات</th></tr>
                        <tr><td>المطور</td><td>كل النظام</td><td>كل الصلاحيات، الإعدادات، الإدارة، التقارير، الحسابات.</td></tr>
                        <tr><td>المالك</td><td>كل النظام</td><td>كل الصلاحيات التشغيلية والإدارية.</td></tr>
                        <tr><td>مدير الفرع</td><td>فرعه فقط</td><td>إحصائيات الفرع، مصروفات الفرع، فتح وإغلاق الدرج، متابعة التشغيل.</td></tr>
                        <tr><td>الكاشير</td><td>الكاشير فقط</td><td>فتح وإغلاق الدرج واستخدام الدرج المفتوح في الفرع حسب السياسة.</td></tr>
                        <tr><td>المحاسب</td><td>الحسابات والتقارير</td><td>المشتريات، الحسابات، السداد، التقارير المالية.</td></tr>
                        <tr><td>الكول سنتر</td><td>الأوامر فقط</td><td>إنشاء ومتابعة أوامر العملاء.</td></tr>
                        <tr><td>المخزن</td><td>المخزون</td><td>المنتجات، المخزون، التحويلات حسب الصلاحية.</td></tr>
                    </table>
                    """,
                ),
                (
                    "لوحة الإدارة",
                    """
                    <ol>
                        <li>أضف المستخدمين من لوحة الإدارة فقط.</li>
                        <li>اربط كل موظف بالفرع الصحيح.</li>
                        <li>امنح أقل صلاحية تكفي لأداء العمل.</li>
                        <li>راجع الحسابات غير المستخدمة وأوقفها عند مغادرة الموظف.</li>
                    </ol>
                    """,
                ),
                (
                    "الإحصائيات",
                    """
                    <div class="checklist">
                    <ul>
                        <li>مدير الفرع يرى إحصائيات فرعه فقط.</li>
                        <li>المالك والمطور يريان كل الفروع.</li>
                        <li>استخدم فلترة التاريخ قبل اتخاذ قرار شرائي أو مالي.</li>
                        <li>لا تعتمد على تقرير واحد؛ راجع المبيعات والمخزون والخزينة معًا.</li>
                    </ul>
                    </div>
                    """,
                ),
            ],
        ),
        GuideDocument(
            "07_التشغيل_اليومي_والدعم.pdf",
            "التشغيل اليومي والدعم",
            "قائمة مراجعة عملية لافتتاح اليوم، إغلاقه، والتعامل مع الأعطال الشائعة.",
            [
                (
                    "افتتاح اليوم",
                    """
                    <div class="checklist">
                    <ul>
                        <li>تشغيل قاعدة البيانات والتأكد من الاتصال.</li>
                        <li>فتح التطبيق بحساب كل موظف.</li>
                        <li>فتح درج الكاشير وتسجيل الرصيد الافتتاحي.</li>
                        <li>اختبار ماسح الباركود والطابعة.</li>
                        <li>مراجعة المنتجات منخفضة المخزون قبل الازدحام.</li>
                    </ul>
                    </div>
                    """,
                ),
                (
                    "إغلاق اليوم",
                    """
                    <ol>
                        <li>إنهاء كل الفواتير المعلقة أو توثيق سبب استمرارها.</li>
                        <li>إغلاق درج الكاشير بعد عد النقد.</li>
                        <li>مطابقة النقد الفعلي مع تقرير الدرج.</li>
                        <li>مراجعة المصروفات المسجلة خلال اليوم.</li>
                        <li>حفظ تقارير PDF المهمة في مساراتها الشهرية.</li>
                    </ol>
                    """,
                ),
                (
                    "أعطال شائعة",
                    """
                    <table>
                        <tr><th>المشكلة</th><th>الإجراء الأول</th><th>الإجراء التالي</th></tr>
                        <tr><td>التطبيق لا يفتح</td><td>تأكد من تشغيل MySQL.</td><td>افتح نسخة التشخيص أو راجع السجلات.</td></tr>
                        <tr><td>الطابعة لا تعمل</td><td>تحقق من Windows Printers.</td><td>استخدم حفظ PDF مؤقتًا.</td></tr>
                        <tr><td>الباركود لا يقرأ</td><td>اختبر الماسح في Notepad.</td><td>راجع كود المنتج داخل النظام.</td></tr>
                        <tr><td>اختلاف رصيد المورد</td><td>افتح كشف الحساب.</td><td>راجع فواتير الشراء والسداد حسب التاريخ.</td></tr>
                        <tr><td>صورة لا تظهر في مجلة العروض</td><td>تأكد من إضافة صورة محلية للمنتج.</td><td>أعد إنشاء مجلة العروض بعد الحفظ.</td></tr>
                    </table>
                    """,
                ),
            ],
        ),
    ]


ARABIC_FORMS = {
    "ء": ("\ufe80", "\ufe80", None, None),
    "آ": ("\ufe81", "\ufe82", None, None),
    "أ": ("\ufe83", "\ufe84", None, None),
    "ؤ": ("\ufe85", "\ufe86", None, None),
    "إ": ("\ufe87", "\ufe88", None, None),
    "ئ": ("\ufe89", "\ufe8a", "\ufe8b", "\ufe8c"),
    "ا": ("\ufe8d", "\ufe8e", None, None),
    "ب": ("\ufe8f", "\ufe90", "\ufe91", "\ufe92"),
    "ة": ("\ufe93", "\ufe94", None, None),
    "ت": ("\ufe95", "\ufe96", "\ufe97", "\ufe98"),
    "ث": ("\ufe99", "\ufe9a", "\ufe9b", "\ufe9c"),
    "ج": ("\ufe9d", "\ufe9e", "\ufe9f", "\ufea0"),
    "ح": ("\ufea1", "\ufea2", "\ufea3", "\ufea4"),
    "خ": ("\ufea5", "\ufea6", "\ufea7", "\ufea8"),
    "د": ("\ufea9", "\ufeaa", None, None),
    "ذ": ("\ufeab", "\ufeac", None, None),
    "ر": ("\ufead", "\ufeae", None, None),
    "ز": ("\ufeaf", "\ufeb0", None, None),
    "س": ("\ufeb1", "\ufeb2", "\ufeb3", "\ufeb4"),
    "ش": ("\ufeb5", "\ufeb6", "\ufeb7", "\ufeb8"),
    "ص": ("\ufeb9", "\ufeba", "\ufebb", "\ufebc"),
    "ض": ("\ufebd", "\ufebe", "\ufebf", "\ufec0"),
    "ط": ("\ufec1", "\ufec2", "\ufec3", "\ufec4"),
    "ظ": ("\ufec5", "\ufec6", "\ufec7", "\ufec8"),
    "ع": ("\ufec9", "\ufeca", "\ufecb", "\ufecc"),
    "غ": ("\ufecd", "\ufece", "\ufecf", "\ufed0"),
    "ف": ("\ufed1", "\ufed2", "\ufed3", "\ufed4"),
    "ق": ("\ufed5", "\ufed6", "\ufed7", "\ufed8"),
    "ك": ("\ufed9", "\ufeda", "\ufedb", "\ufedc"),
    "ل": ("\ufedd", "\ufede", "\ufedf", "\ufee0"),
    "م": ("\ufee1", "\ufee2", "\ufee3", "\ufee4"),
    "ن": ("\ufee5", "\ufee6", "\ufee7", "\ufee8"),
    "ه": ("\ufee9", "\ufeea", "\ufeeb", "\ufeec"),
    "و": ("\ufeed", "\ufeee", None, None),
    "ى": ("\ufeef", "\ufef0", None, None),
    "ي": ("\ufef1", "\ufef2", "\ufef3", "\ufef4"),
}
ARABIC_CHARS = set(ARABIC_FORMS)
DUAL_JOINING = {char for char, forms in ARABIC_FORMS.items() if forms[2]}


def _can_connect_to_previous(char: str) -> bool:
    return char in ARABIC_CHARS


def _can_connect_to_next(char: str) -> bool:
    return char in DUAL_JOINING


def _shape_arabic_word(word: str) -> str:
    shaped = []
    for index, char in enumerate(word):
        forms = ARABIC_FORMS.get(char)
        if not forms:
            shaped.append(char)
            continue
        previous_char = word[index - 1] if index else ""
        next_char = word[index + 1] if index + 1 < len(word) else ""
        joins_previous = _can_connect_to_next(previous_char) and _can_connect_to_previous(char)
        joins_next = _can_connect_to_next(char) and _can_connect_to_previous(next_char)
        if joins_previous and joins_next:
            shaped.append(forms[3])
        elif joins_previous:
            shaped.append(forms[1])
        elif joins_next:
            shaped.append(forms[2])
        else:
            shaped.append(forms[0])
    return "".join(shaped)[::-1]


def _visual_text(text: str) -> str:
    tokens = re.findall(r"\S+|\s+", text)
    visual_tokens = []
    for token in tokens:
        if token.isspace():
            visual_tokens.append(token)
        elif any(char in ARABIC_CHARS for char in token):
            visual_tokens.append(_shape_arabic_word(token))
        else:
            visual_tokens.append(token)
    return "".join(reversed(visual_tokens))


def _plain_lines_from_html(value: str) -> list[str]:
    import html

    text = value
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<\s*/\s*(p|div|section|table|tr|ol|ul)\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<\s*li\s*>", "\n• ", text, flags=re.I)
    text = re.sub(r"<\s*/\s*(td|th)\s*>", " | ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip(" |")
        if clean:
            lines.append(clean)
    return lines


def _font(name: str, size: int):
    from PIL import ImageFont

    font_file = "tahomabd.ttf" if name == "bold" else "tahoma.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / font_file), size=size)


def _measure(draw, text: str, font) -> int:
    if not text:
        return 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _wrap_rtl(draw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[list[str]] = []
    current: list[str] = []
    for word in words:
        candidate = current + [word]
        if current and _measure(draw, _visual_text(" ".join(candidate)), font) > max_width:
            lines.append(current)
            current = [word]
        else:
            current = candidate
    if current:
        lines.append(current)
    return [_visual_text(" ".join(line)) for line in lines]


def _draw_rtl(draw, text: str, x_right: int, y: int, font, fill: str, max_width: int, line_gap: int = 8) -> int:
    for line in _wrap_rtl(draw, text, font, max_width):
        draw.text((x_right, y), line, font=font, fill=fill, anchor="ra")
        y += font.size + line_gap
    return y


def _new_page():
    from PIL import Image, ImageDraw

    page = Image.new("RGB", (1240, 1754), "#ffffff")
    return page, ImageDraw.Draw(page)


def write_pdf(_app, document: GuideDocument) -> Path:
    from PIL import ImageDraw

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / slug_file_name(document.file_name)

    margin = 74
    x_right = 1240 - margin
    max_width = 1240 - (margin * 2)
    bottom = 1754 - margin
    pages = []
    page, draw = _new_page()

    title_font = _font("bold", 46)
    subtitle_font = _font("regular", 24)
    heading_font = _font("bold", 30)
    body_font = _font("regular", 23)
    small_font = _font("regular", 18)

    draw.rounded_rectangle((margin, 62, 1240 - margin, 256), radius=22, fill="#0f172a")
    y = 98
    y = _draw_rtl(draw, "هايبر بوس ٢ — دليل تدريبي للتشغيل الفعلي", x_right - 26, y, small_font, "#93c5fd", max_width - 52, 6)
    y = _draw_rtl(draw, document.title, x_right - 26, y + 8, title_font, COLORS['text_on_brand'], max_width - 52, 10)
    _draw_rtl(draw, document.subtitle, x_right - 26, y + 6, subtitle_font, "#dbeafe", max_width - 52, 8)
    y = 304

    for heading, body in document.sections:
        if y > bottom - 180:
            pages.append(page)
            page, draw = _new_page()
            y = margin
        y = _draw_rtl(draw, heading, x_right, y, heading_font, "#14532d", max_width, 8)
        draw.line((margin, y + 4, x_right, y + 4), fill="#bbf7d0", width=3)
        y += 22
        for line in _plain_lines_from_html(body):
            if y > bottom - 90:
                pages.append(page)
                page, draw = _new_page()
                y = margin
            is_bullet = line.startswith("•")
            if "|" in line:
                draw.rounded_rectangle((margin, y - 6, x_right, y + 42), radius=8, fill="#f8fafc", outline="#dbe3ef")
                clean_line = line.replace("|", "  │  ")
                y = _draw_rtl(draw, clean_line, x_right - 14, y, small_font, "#172033", max_width - 28, 7) + 6
            elif is_bullet:
                draw.ellipse((x_right - 12, y + 9, x_right - 2, y + 19), fill="#14532d")
                y = _draw_rtl(draw, line[1:].strip(), x_right - 26, y, body_font, "#172033", max_width - 38, 8) + 4
            else:
                y = _draw_rtl(draw, line, x_right, y, body_font, "#172033", max_width, 8) + 4
        y += 18

    footer = "تم توليد هذا الملف من داخل مشروع هايبر بوس. عند تحديث التطبيق يمكن إعادة توليد الأدلة بنفس السكربت."
    draw.line((margin, bottom + 12, x_right, bottom + 12), fill="#e2e8f0", width=2)
    _draw_rtl(draw, footer, x_right, bottom + 28, small_font, "#64748b", max_width, 5)
    pages.append(page)

    pages[0].save(output_path, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    pages[0].save(PREVIEW_DIR / f"{output_path.stem}_صفحة_1.png", "PNG")
    return output_path


def main() -> int:
    generated = [write_pdf(None, document) for document in build_documents()]
    print(f"Generated {len(generated)} PDF files in: {OUTPUT_DIR}")
    for path in generated:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
