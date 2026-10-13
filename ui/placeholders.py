"""
Placeholder Views - واجهات مؤقتة للوحدات قيد التطوير
تُستخدم حتى يتم بناء كل وحدة بالكامل وفقاً لـ Clean Architecture
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.styles import COLORS


class PlaceholderView(QWidget):
    """واجهة مؤقتة لأي وحدة قيد التطوير"""

    def __init__(self, module_name: str, features: list = None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🚧")
        icon.setFont(QFont("Segoe UI Emoji", 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel(f"{module_name}")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text_primary']}; margin-bottom: 10px;")
        layout.addWidget(title)

        subtitle = QLabel("هذه الوحدة قيد الترحيل للمعمارية الجديدة")
        subtitle.setFont(QFont("Arial", 13))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(subtitle)

        if features:
            features_label = QLabel("\n".join([f"  • {f}" for f in features]))
            features_label.setFont(QFont("Arial", 12))
            features_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            features_label.setStyleSheet(f"color: {COLORS['text_secondary']}; margin-top: 15px;")
            layout.addWidget(features_label)


class PurchasesPlaceholder(PlaceholderView):
    def __init__(self, user_info=None, parent=None):
        super().__init__("🛒 المشتريات والموردين", [
            "إدارة الموردين", "فواتير المشتريات", "حسابات الموردين", "سجل المدفوعات"
        ], parent)


class AccountsPlaceholder(PlaceholderView):
    def __init__(self, user_info=None, parent=None):
        super().__init__("💰 الحسابات والمالية", [
            "الخزينة", "المصروفات", "الإيرادات", "التقارير المالية"
        ], parent)


class PromotionsPlaceholder(PlaceholderView):
    def __init__(self, user_info=None, parent=None):
        super().__init__("🏷️ العروض والتخفيضات", [
            "إنشاء عروض", "جدولة العروض", "عروض الكمية", "خصومات المنتجات"
        ], parent)


class ReturnsPlaceholder(PlaceholderView):
    def __init__(self, user_info=None, parent=None):
        super().__init__("↩️ مرتجع الفواتير", [
            "مرتجع جزئي", "مرتجع كامل", "إعادة المخزون", "تقارير المرتجعات"
        ], parent)


class CallCenterPlaceholder(PlaceholderView):
    def __init__(self, user_info=None, parent=None):
        super().__init__("📞 كول سنتر", [
            "إنشاء طلبات", "تتبع الطلبات", "إدارة التوصيل"
        ], parent)
