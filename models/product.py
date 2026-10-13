"""
Product Entity - كائن المنتج
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Product:
    """نموذج بيانات المنتج"""
    id: int = 0
    product_code: str = ''
    product_name: str = ''
    category_id: int = 1
    supplier_id: Optional[int] = None
    buy_price: float = 0.0
    sell_price: float = 0.0
    unit: str = 'قطعة'
    barcode: Optional[str] = None
    description: Optional[str] = None
    image_path: Optional[str] = None
    tax_percent: float = 0.0
    min_quantity: int = 0
    is_active: bool = True
    import_status: str = 'ready'
    import_notes: Optional[str] = None

    @property
    def profit_margin(self) -> float:
        """هامش الربح"""
        if self.buy_price > 0:
            return ((self.sell_price - self.buy_price) / self.buy_price) * 100
        return 0.0

    @classmethod
    def from_dict(cls, data: dict) -> 'Product':
        """إنشاء كائن من dict (نتيجة قاعدة البيانات)"""
        return cls(
            id=data.get('id', 0),
            product_code=data.get('product_code', ''),
            product_name=data.get('product_name', ''),
            category_id=data.get('category_id', 1),
            supplier_id=data.get('supplier_id'),
            buy_price=float(data.get('buy_price', 0)),
            sell_price=float(data.get('sell_price', 0)),
            unit=data.get('unit', 'قطعة'),
            barcode=data.get('barcode'),
            description=data.get('description'),
            image_path=data.get('image_path'),
            tax_percent=float(data.get('tax_percent', 0)),
            min_quantity=data.get('min_quantity', 0),
            is_active=bool(data.get('is_active', True)),
            import_status=data.get('import_status') or 'ready',
            import_notes=data.get('import_notes'),
        )

    def to_dict(self) -> dict:
        """تحويل الكائن إلى dict"""
        return {
            'id': self.id,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'category_id': self.category_id,
            'supplier_id': self.supplier_id,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'unit': self.unit,
            'barcode': self.barcode,
            'description': self.description,
            'image_path': self.image_path,
            'tax_percent': self.tax_percent,
            'min_quantity': self.min_quantity,
            'is_active': self.is_active,
            'import_status': self.import_status,
            'import_notes': self.import_notes,
        }
