"""
Invoice & InvoiceItem Entities - كائنات الفاتورة
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class InvoiceItem:
    """بند واحد في الفاتورة"""
    product_id: int = 0
    product_code: str = ''
    product_name: str = ''
    quantity: float = 1.0
    unit_price: float = 0.0
    discount: float = 0.0
    tax_percent: float = 0.0

    @property
    def gross_total(self) -> float:
        """الإجمالي قبل الخصم"""
        return self.unit_price * self.quantity

    @property
    def net_total(self) -> float:
        """الإجمالي بعد الخصم"""
        return self.gross_total - self.discount

    @property
    def tax_amount(self) -> float:
        """مبلغ الضريبة (مستخرج من السعر الشامل)"""
        if self.tax_percent > 0:
            return self.net_total - (self.net_total / (1 + self.tax_percent / 100))
        return 0.0

    @property
    def subtotal(self) -> float:
        """الصافي بدون ضريبة"""
        return self.net_total - self.tax_amount

    @classmethod
    def from_dict(cls, data: dict) -> 'InvoiceItem':
        return cls(
            product_id=data.get('product_id', 0),
            product_code=data.get('product_code', ''),
            product_name=data.get('product_name', ''),
            quantity=float(data.get('quantity', 1)),
            unit_price=float(data.get('unit_price', data.get('price', 0))),
            discount=float(data.get('discount', 0)),
            tax_percent=float(data.get('tax_percent', 0)),
        )

    def to_dict(self) -> dict:
        return {
            'product_id': self.product_id,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'price': self.unit_price,
            'total': self.net_total,
            'tax_percent': self.tax_percent,
            'discount': self.discount,
        }


@dataclass
class TaxInvoiceDetails:
    """بيانات الفاتورة الضريبية للشركات (B2B)"""
    company_name: str = ''
    tax_id_number: str = ''
    commercial_registry: str = ''
    company_address: str = ''
    company_phone: str = ''
    notes: str = ''

    @classmethod
    def from_dict(cls, data: dict) -> 'TaxInvoiceDetails':
        if not data:
            return None
        return cls(
            company_name=data.get('company_name', ''),
            tax_id_number=data.get('tax_id_number', ''),
            commercial_registry=data.get('commercial_registry', ''),
            company_address=data.get('company_address', ''),
            company_phone=data.get('company_phone', ''),
            notes=data.get('notes', ''),
        )


@dataclass
class Invoice:
    """نموذج بيانات الفاتورة الكاملة"""
    id: int = 0
    invoice_number: str = ''
    store_id: int = 1
    cashier_id: int = 1
    drawer_id: Optional[int] = None
    customer_name: str = ''
    customer_phone: str = ''
    customer_address: str = ''
    payment_method: str = 'Cash'
    cash_amount: float = 0.0
    card_amount: float = 0.0
    subtotal_amount: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    discount: float = 0.0
    promo_discount: float = 0.0
    status: str = 'Completed'
    invoice_date: Optional[datetime] = None
    items: List[InvoiceItem] = field(default_factory=list)
    tax_details: Optional[TaxInvoiceDetails] = None

    @property
    def is_tax_invoice(self) -> bool:
        """هل هي فاتورة ضريبية؟"""
        return self.tax_details is not None and bool(self.tax_details.company_name)

    @property
    def paid_amount(self) -> float:
        return self.cash_amount + self.card_amount

    def calculate_totals(self):
        """حساب إجمالي الفاتورة من البنود"""
        total_tax = 0.0
        total_gross = sum(item.gross_total for item in self.items)

        for item in self.items:
            # توزيع نسبي للخصم اليدوي
            if total_gross > 0:
                item_manual_discount = self.discount * (item.gross_total / total_gross)
            else:
                item_manual_discount = 0.0

            item_net = item.gross_total - item.discount - item_manual_discount
            if item.tax_percent > 0:
                total_tax += item_net - (item_net / (1 + item.tax_percent / 100))

        self.tax_amount = round(total_tax, 2)
        self.total_amount = round(self.paid_amount, 2)
        self.subtotal_amount = round(self.total_amount - self.tax_amount, 2)
