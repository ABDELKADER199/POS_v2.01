"""
User Entity - كائن المستخدم
"""
from dataclasses import dataclass
from typing import Optional
from utils.permissions import PermissionPolicy


@dataclass
class User:
    """نموذج بيانات المستخدم"""
    id: int = 0
    email: str = ''
    name: str = ''
    role: str = 'cashier'
    role_id: int = 3
    store_id: int = 1
    store_name: str = ''
    is_active: bool = True

    @property
    def is_admin(self) -> bool:
        """الإدارة العليا والمطور"""
        return PermissionPolicy(self).is_admin

    @property
    def is_manager(self) -> bool:
        """يشمل المدير العام ومدير الفرع"""
        return PermissionPolicy(self).is_manager

    @property
    def can_view_buy_price(self) -> bool:
        """فقط الإدارة العليا والمطور (مدير الفرع لا يرى سعر الشراء)"""
        return PermissionPolicy(self).can_view_buy_price()

    @property
    def can_edit_products(self) -> bool:
        """فقط الإدارة العليا والمطور"""
        return PermissionPolicy(self).can_edit_products()

    @property
    def can_manage_users(self) -> bool:
        """فقط الإدارة العليا والمطور"""
        return PermissionPolicy(self).can_manage_users()

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        return cls(
            id=data.get('id', 0),
            email=data.get('email', ''),
            name=data.get('name', ''),
            role=data.get('role_name', data.get('role', 'cashier')),
            role_id=data.get('role_id', 3),
            store_id=data.get('store_id', 1),
            store_name=data.get('store_name', ''),
            is_active=bool(data.get('is_active', True)),
        )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'full_name': self.name,
            'username': self.email,
            'role': self.role,
            'role_id': self.role_id,
            'role_name': self.role,
            'store_id': self.store_id,
            'store_name': self.store_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'can_view_buy': self.can_view_buy_price,
            'can_edit_products': self.can_edit_products
        }
