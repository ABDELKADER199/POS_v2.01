"""
Customer Entity - كائن العميل
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Customer:
    """نموذج بيانات العميل"""
    id: int = 0
    name: str = ''
    phone: str = ''
    address: str = ''
    balance: float = 0.0
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> 'Customer':
        return cls(
            id=data.get('id', 0),
            name=data.get('name', data.get('customer_name', '')),
            phone=data.get('phone', data.get('customer_phone', '')),
            address=data.get('address', data.get('customer_address', '')),
            balance=float(data.get('balance', data.get('current_balance', 0))),
            is_active=bool(data.get('is_active', True)),
        )
