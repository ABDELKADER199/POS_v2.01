# 📖 مثال عملي كامل: نقل مميزة (مثال: إدارة الفئات)
# Complete Example: Migrating a Feature (Categories Management)

## 🎯 المميزة المختارة: إدارة فئات المنتجات (Categories Management)

هذا المثال يوضح كيفية نقل مميزة كاملة من التطبيق القديم إلى الجديد بنفس معمارية Clean Architecture.

---

## 📊 خطوات النقل الكاملة

### الخطوة 1️⃣: تحليل المميزة من التطبيق القديم

**ما هي المميزة؟**
- إضافة فئة منتج جديدة
- تعديل فئة موجودة
- حذف فئة
- عرض قائمة الفئات
- البحث والفلترة في الفئات

**الشاشات المتعلقة:**
- شاشة إدارة الفئات (Categories Screen)
- نموذج إضافة/تعديل فئة (Add/Edit Category Dialog)

**العمليات المتعلقة:**
- قاعدة البيانات: جدول `categories`
- التحقق من الصحة: اسم الفئة فريد وليس فارغ
- التدقيق: تسجيل العمليات

---

### الخطوة 2️⃣: إنشاء Model (كائن البيانات)

```python
# models/category.py
"""
Category Model - نموذج الفئة
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Category:
    """نموذج فئة المنتج"""
    id: int = 0
    category_name: str = ""
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Category':
        """إنشاء كائن Category من قاموس"""
        return cls(
            id=data.get('id', 0),
            category_name=data.get('category_name', ''),
            description=data.get('description'),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    def to_dict(self) -> dict:
        """تحويل الكائن إلى قاموس"""
        return {
            'id': self.id,
            'category_name': self.category_name,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
```

---

### الخطوة 3️⃣: إنشاء Repository (طبقة الوصول للبيانات)

```python
# repositories/category_repo.py
"""
Category Repository - مستودع الفئات
الوصول والتعديل على بيانات الفئات في قاعدة البيانات
"""
import logging
from typing import List, Optional
from repositories.base_repo import BaseRepository
from models.category import Category

logger = logging.getLogger(__name__)


class CategoryRepository(BaseRepository):
    """مستودع عمليات الفئات"""

    def ensure_table(self) -> None:
        """التأكد من وجود جدول الفئات"""
        self._execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT PRIMARY KEY AUTO_INCREMENT,
                category_name VARCHAR(100) NOT NULL UNIQUE,
                description VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        self._commit()

    def get_all(self, active_only: bool = True) -> List[Category]:
        """جلب جميع الفئات"""
        query = "SELECT * FROM categories"
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY category_name"
        
        rows = self._fetch_all(query)
        return [Category.from_dict(row) for row in rows]

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """جلب فئة بالمعرف"""
        row = self._fetch_one(
            "SELECT * FROM categories WHERE id = %s",
            (category_id,)
        )
        return Category.from_dict(row) if row else None

    def get_by_name(self, name: str) -> Optional[Category]:
        """جلب فئة بالاسم"""
        row = self._fetch_one(
            "SELECT * FROM categories WHERE category_name = %s",
            (name,)
        )
        return Category.from_dict(row) if row else None

    def create(self, category: Category) -> bool:
        """إنشاء فئة جديدة"""
        try:
            # التحقق من عدم وجود فئة بنفس الاسم
            existing = self.get_by_name(category.category_name)
            if existing:
                logger.warning(f"Category already exists: {category.category_name}")
                return False

            self._execute(
                """
                INSERT INTO categories (category_name, description, is_active)
                VALUES (%s, %s, %s)
                """,
                (category.category_name, category.description, category.is_active)
            )
            self._commit()
            logger.info(f"Category created: {category.category_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            self._rollback()
            return False

    def update(self, category: Category) -> bool:
        """تحديث فئة موجودة"""
        try:
            self._execute(
                """
                UPDATE categories 
                SET category_name = %s, description = %s, is_active = %s
                WHERE id = %s
                """,
                (category.category_name, category.description, category.is_active, category.id)
            )
            self._commit()
            logger.info(f"Category updated: {category.category_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            self._rollback()
            return False

    def delete(self, category_id: int) -> bool:
        """حذف فئة"""
        try:
            # التحقق من عدم استخدام الفئة
            products_count = self._fetch_one(
                "SELECT COUNT(*) as count FROM products WHERE category_id = %s",
                (category_id,)
            )
            
            if products_count['count'] > 0:
                logger.warning(f"Cannot delete category: has products")
                return False

            self._execute(
                "DELETE FROM categories WHERE id = %s",
                (category_id,)
            )
            self._commit()
            logger.info(f"Category deleted: {category_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            self._rollback()
            return False

    def search(self, query: str) -> List[Category]:
        """البحث في الفئات"""
        search_pattern = f"%{query}%"
        rows = self._fetch_all(
            """
            SELECT * FROM categories 
            WHERE category_name LIKE %s OR description LIKE %s
            ORDER BY category_name
            """,
            (search_pattern, search_pattern)
        )
        return [Category.from_dict(row) for row in rows]
```

---

### الخطوة 4️⃣: إنشاء Use Case (منطق الأعمال)

```python
# application/use_cases/category_management.py
"""
Category Management Use Case - حالات الاستخدام الخاصة بالفئات
منطق الأعمال المتعلق بإدارة الفئات
"""
import logging
from typing import List, Optional
from repositories.category_repo import CategoryRepository
from models.category import Category

logger = logging.getLogger(__name__)


class GetAllCategoriesUseCase:
    """حالة الاستخدام: جلب جميع الفئات"""
    
    def __init__(self, repo: CategoryRepository):
        self.repo = repo
    
    def execute(self, active_only: bool = True) -> List[Category]:
        """تنفيذ العملية"""
        return self.repo.get_all(active_only)


class GetCategoryByIdUseCase:
    """حالة الاستخدام: جلب فئة بالمعرف"""
    
    def __init__(self, repo: CategoryRepository):
        self.repo = repo
    
    def execute(self, category_id: int) -> Optional[Category]:
        """تنفيذ العملية"""
        return self.repo.get_by_id(category_id)


class CreateCategoryUseCase:
    """حالة الاستخدام: إنشاء فئة جديدة"""
    
    def __init__(self, repo: CategoryRepository):
        self.repo = repo
    
    def execute(self, category_name: str, description: str = None) -> bool:
        """تنفيذ العملية مع التحقق من الصحة"""
        
        # التحقق من الصحة
        if not category_name or not category_name.strip():
            logger.error("Category name cannot be empty")
            return False
        
        if len(category_name) < 2:
            logger.error("Category name must be at least 2 characters")
            return False
        
        # إنشاء الفئة
        category = Category(
            category_name=category_name.strip(),
            description=description,
            is_active=True
        )
        
        return self.repo.create(category)


class UpdateCategoryUseCase:
    """حالة الاستخدام: تحديث فئة موجودة"""
    
    def __init__(self, repo: CategoryRepository):
        self.repo = repo
    
    def execute(self, category_id: int, category_name: str, 
                description: str = None, is_active: bool = True) -> bool:
        """تنفيذ العملية مع التحقق من الصحة"""
        
        # التحقق من الصحة
        if not category_name or not category_name.strip():
            logger.error("Category name cannot be empty")
            return False
        
        # التحقق من وجود الفئة
        existing = self.repo.get_by_id(category_id)
        if not existing:
            logger.error(f"Category not found: {category_id}")
            return False
        
        # تحديث الفئة
        category = Category(
            id=category_id,
            category_name=category_name.strip(),
            description=description,
            is_active=is_active
        )
        
        return self.repo.update(category)


class DeleteCategoryUseCase:
    """حالة الاستخدام: حذف فئة"""
    
    def __init__(self, repo: CategoryRepository):
        self.repo = repo
    
    def execute(self, category_id: int) -> bool:
        """تنفيذ العملية"""
        return self.repo.delete(category_id)


class SearchCategoriesUseCase:
    """حالة الاستخدام: البحث في الفئات"""
    
    def __init__(self, repo: CategoryRepository):
        self.repo = repo
    
    def execute(self, query: str) -> List[Category]:
        """تنفيذ العملية"""
        return self.repo.search(query)
```

---

### الخطوة 5️⃣: إنشاء Service Facade (واجهة الخدمة)

```python
# application/services/category_service_facade.py
"""
Category Service Facade - واجهة خدمات الفئات
تجميع جميع Use Cases الخاصة بالفئات
"""
from typing import List, Optional
from repositories.category_repo import CategoryRepository
from models.category import Category
from application.use_cases.category_management import (
    GetAllCategoriesUseCase,
    GetCategoryByIdUseCase,
    CreateCategoryUseCase,
    UpdateCategoryUseCase,
    DeleteCategoryUseCase,
    SearchCategoriesUseCase,
)


class CategoryServiceFacade:
    """واجهة خدمات الفئات"""
    
    def __init__(self, repo: CategoryRepository = None):
        self.repo = repo or CategoryRepository()
        self.repo.ensure_table()
        
        # تهيئة Use Cases
        self.get_all_use_case = GetAllCategoriesUseCase(self.repo)
        self.get_by_id_use_case = GetCategoryByIdUseCase(self.repo)
        self.create_use_case = CreateCategoryUseCase(self.repo)
        self.update_use_case = UpdateCategoryUseCase(self.repo)
        self.delete_use_case = DeleteCategoryUseCase(self.repo)
        self.search_use_case = SearchCategoriesUseCase(self.repo)
    
    def get_all_categories(self, active_only: bool = True) -> List[Category]:
        """جلب جميع الفئات"""
        return self.get_all_use_case.execute(active_only)
    
    def get_category(self, category_id: int) -> Optional[Category]:
        """جلب فئة بالمعرف"""
        return self.get_by_id_use_case.execute(category_id)
    
    def create_category(self, category_name: str, description: str = None) -> bool:
        """إنشاء فئة جديدة"""
        return self.create_use_case.execute(category_name, description)
    
    def update_category(self, category_id: int, category_name: str, 
                       description: str = None, is_active: bool = True) -> bool:
        """تحديث فئة موجودة"""
        return self.update_use_case.execute(category_id, category_name, description, is_active)
    
    def delete_category(self, category_id: int) -> bool:
        """حذف فئة"""
        return self.delete_use_case.execute(category_id)
    
    def search_categories(self, query: str) -> List[Category]:
        """البحث في الفئات"""
        return self.search_use_case.execute(query)
```

---

### الخطوة 6️⃣: إنشاء Controller (التحكم)

```python
# controllers/category_controller.py
"""
Category Controller - متحكم الفئات
طبقة رقيقة جداً - تمرر الاستدعاءات فقط
"""
from application.services.category_service_facade import CategoryServiceFacade
from repositories.category_repo import CategoryRepository


class CategoryController:
    """متحكم عمليات الفئات"""
    
    def __init__(self):
        self.service = CategoryServiceFacade(CategoryRepository())
    
    def __getattr__(self, name):
        """تمرير الاستدعاءات للـ Service"""
        return getattr(self.service, name)
    
    def __setattr__(self, name, value):
        """تعيين القيم"""
        if name == "service":
            super().__setattr__(name, value)
            return
        if "service" in self.__dict__ and hasattr(self.service, name):
            setattr(self.service, name, value)
            return
        super().__setattr__(name, value)
```

---

### الخطوة 7️⃣: إنشاء View (واجهة المستخدم)

```python
# ui/category_view.py
"""
Category View - واجهة إدارة الفئات
واجهة PyQt6 لعرض وإدارة الفئات
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from application.services.category_service_facade import CategoryServiceFacade
from ui.styles import COLORS, INPUT_STYLE, get_button_style

logger = logging.getLogger(__name__)


class CategoryView(QWidget):
    """واجهة إدارة الفئات"""
    
    def __init__(self, service: CategoryServiceFacade, parent=None):
        super().__init__(parent)
        self.service = service
        self._init_ui()
        self._load_categories()
    
    def _init_ui(self):
        """بناء واجهة المستخدم"""
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg_app']}; }}")
        
        layout = QVBoxLayout(self)
        
        # الأدوات العلوية
        toolbar = QHBoxLayout()
        
        # حقل البحث
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ابحث عن فئة...")
        self.search_input.setStyleSheet(INPUT_STYLE)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)
        
        # زر الإضافة
        self.add_btn = QPushButton("إضافة فئة")
        self.add_btn.setStyleSheet(get_button_style("primary"))
        self.add_btn.clicked.connect(self._on_add_category)
        toolbar.addWidget(self.add_btn)
        
        # زر التحديث
        self.refresh_btn = QPushButton("تحديث")
        self.refresh_btn.setStyleSheet(get_button_style("secondary"))
        self.refresh_btn.clicked.connect(self._load_categories)
        toolbar.addWidget(self.refresh_btn)
        
        layout.addLayout(toolbar)
        
        # جدول الفئات
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["المعرف", "اسم الفئة", "الوصف", "الإجراءات"])
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {COLORS['bg_panel']}; }}
            QHeaderView::section {{ background-color: {COLORS['bg_input']}; }}
        """)
        layout.addWidget(self.table)
    
    def _load_categories(self):
        """تحميل الفئات من قاعدة البيانات"""
        try:
            categories = self.service.get_all_categories()
            self._populate_table(categories)
        except Exception as e:
            logger.error(f"Error loading categories: {e}")
            QMessageBox.critical(self, "خطأ", f"خطأ في تحميل الفئات: {e}")
    
    def _populate_table(self, categories):
        """ملء جدول الفئات"""
        self.table.setRowCount(len(categories))
        
        for row, category in enumerate(categories):
            # المعرف
            id_item = QTableWidgetItem(str(category.id))
            self.table.setItem(row, 0, id_item)
            
            # اسم الفئة
            name_item = QTableWidgetItem(category.category_name)
            self.table.setItem(row, 1, name_item)
            
            # الوصف
            desc_item = QTableWidgetItem(category.description or "")
            self.table.setItem(row, 2, desc_item)
            
            # الإجراءات (أزرار تعديل وحذف)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            
            # زر التعديل
            edit_btn = QPushButton("تعديل")
            edit_btn.setStyleSheet(get_button_style("secondary"))
            edit_btn.clicked.connect(lambda checked, c=category: self._on_edit_category(c))
            actions_layout.addWidget(edit_btn)
            
            # زر الحذف
            delete_btn = QPushButton("حذف")
            delete_btn.setStyleSheet(get_button_style("danger"))
            delete_btn.clicked.connect(lambda checked, c=category: self._on_delete_category(c))
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            self.table.setCellWidget(row, 3, actions_widget)
    
    def _on_search(self, query):
        """البحث عن فئات"""
        if not query.strip():
            self._load_categories()
            return
        
        try:
            results = self.service.search_categories(query)
            self._populate_table(results)
        except Exception as e:
            logger.error(f"Search error: {e}")
    
    def _on_add_category(self):
        """إضافة فئة جديدة"""
        dialog = CategoryDialog(self.service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_categories()
    
    def _on_edit_category(self, category):
        """تعديل فئة"""
        dialog = CategoryDialog(self.service, category, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_categories()
    
    def _on_delete_category(self, category):
        """حذف فئة"""
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            f"هل تريد حذف الفئة '{category.category_name}'؟"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.service.delete_category(category.id):
                    QMessageBox.information(self, "نجح", "تم حذف الفئة بنجاح")
                    self._load_categories()
                else:
                    QMessageBox.warning(self, "فشل", "لا يمكن حذف الفئة (قد تحتوي على منتجات)")
            except Exception as e:
                logger.error(f"Delete error: {e}")
                QMessageBox.critical(self, "خطأ", f"خطأ في حذف الفئة: {e}")


class CategoryDialog(QDialog):
    """نموذج إضافة/تعديل فئة"""
    
    def __init__(self, service: CategoryServiceFacade, category=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.category = category
        self.setWindowTitle("فئة المنتج" if category else "فئة جديدة")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._init_ui()
    
    def _init_ui(self):
        """بناء الواجهة"""
        layout = QVBoxLayout()
        
        # اسم الفئة
        layout.addWidget(QLabel("اسم الفئة:"))
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet(INPUT_STYLE)
        if self.category:
            self.name_input.setText(self.category.category_name)
        layout.addWidget(self.name_input)
        
        # الوصف
        layout.addWidget(QLabel("الوصف:"))
        self.desc_input = QLineEdit()
        self.desc_input.setStyleSheet(INPUT_STYLE)
        if self.category:
            self.desc_input.setText(self.category.description or "")
        layout.addWidget(self.desc_input)
        
        # الأزرار
        buttons = QHBoxLayout()
        
        save_btn = QPushButton("حفظ")
        save_btn.setStyleSheet(get_button_style("primary"))
        save_btn.clicked.connect(self._on_save)
        buttons.addWidget(save_btn)
        
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet(get_button_style("secondary"))
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        
        layout.addLayout(buttons)
        self.setLayout(layout)
    
    def _on_save(self):
        """حفظ الفئة"""
        name = self.name_input.text().strip()
        description = self.desc_input.text().strip() or None
        
        if not name:
            QMessageBox.warning(self, "تحذير", "أدخل اسم الفئة")
            return
        
        try:
            if self.category:
                # تحديث
                if self.service.update_category(self.category.id, name, description):
                    QMessageBox.information(self, "نجح", "تم تحديث الفئة بنجاح")
                    self.accept()
                else:
                    QMessageBox.warning(self, "فشل", "فشل تحديث الفئة")
            else:
                # إضافة جديدة
                if self.service.create_category(name, description):
                    QMessageBox.information(self, "نجح", "تم إضافة الفئة بنجاح")
                    self.accept()
                else:
                    QMessageBox.warning(self, "فشل", "فشل إضافة الفئة (قد تكون موجودة بالفعل)")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ: {e}")
```

---

### الخطوة 8️⃣: الربط في main.py

```python
# في main.py، أضف:

from controllers.category_controller import CategoryController
from ui.category_view import CategoryView

class MainWindow(QMainWindow):
    def __init__(self):
        # ... existing code ...
        
        # إضافة Category Controller
        self.category_ctrl = CategoryController()
        
        # إنشاء View وإضافتها للـ Stacked Widget
        self.category_view = CategoryView(self.category_ctrl.service)
        self.stacked_widget.addWidget(self.category_view)
```

---

### الخطوة 9️⃣: الاختبار

```python
# tests/test_category.py
"""
Unit Tests for Category Feature
"""
import pytest
from repositories.category_repo import CategoryRepository
from application.services.category_service_facade import CategoryServiceFacade
from models.category import Category


def test_create_category():
    """اختبار إنشاء فئة جديدة"""
    service = CategoryServiceFacade()
    
    # إنشاء فئة
    result = service.create_category("ملابس", "الملابس والأحذية")
    assert result is True
    
    # التحقق من الإنشاء
    category = service.search_categories("ملابس")
    assert len(category) > 0
    assert category[0].category_name == "ملابس"


def test_update_category():
    """اختبار تحديث فئة"""
    service = CategoryServiceFacade()
    
    # إنشاء فئة
    service.create_category("إلكترونيات", "الأجهزة الإلكترونية")
    
    # جلب الفئة
    categories = service.search_categories("إلكترونيات")
    category = categories[0]
    
    # تحديث الفئة
    result = service.update_category(category.id, "الإلكترونيات", "جميع الأجهزة")
    assert result is True


def test_delete_category():
    """اختبار حذف فئة"""
    service = CategoryServiceFacade()
    
    # إنشاء فئة
    service.create_category("الأثاث", "الأثاث المنزلي")
    
    # جلب الفئة
    categories = service.search_categories("الأثاث")
    category = categories[0]
    
    # حذف الفئة
    result = service.delete_category(category.id)
    assert result is True
    
    # التحقق من الحذف
    category = service.get_category(category.id)
    assert category is None
```

---

### الخطوة 🔟: التوثيق

```markdown
# Category Feature Documentation

## نظرة عامة
هذه الميزة توفر إدارة كاملة لفئات المنتجات في النظام.

## الميزات
- ✅ إضافة فئات جديدة
- ✅ تعديل الفئات الموجودة
- ✅ حذف الفئات
- ✅ البحث والفلترة
- ✅ عرض الفئات في جدول

## الملفات المتعلقة
- `models/category.py` - نموذج الفئة
- `repositories/category_repo.py` - مستودع البيانات
- `application/use_cases/category_management.py` - منطق الأعمال
- `application/services/category_service_facade.py` - واجهة الخدمة
- `controllers/category_controller.py` - المتحكم
- `ui/category_view.py` - واجهة المستخدم

## طريقة الاستخدام
```python
from controllers.category_controller import CategoryController

# إنشاء المتحكم
controller = CategoryController()

# الوصول للخدمات
categories = controller.get_all_categories()
```
```

---

## 📋 الملخص

هذا المثال يوضح الخطوات الكاملة لنقل مميزة واحدة من التطبيق القديم إلى الجديد:

1. ✅ **Model** - كائن البيانات
2. ✅ **Repository** - الوصول للبيانات
3. ✅ **Use Cases** - منطق الأعمال
4. ✅ **Service Facade** - واجهة الخدمة
5. ✅ **Controller** - المتحكم
6. ✅ **View** - واجهة المستخدم
7. ✅ **Wiring** - الربط في main.py
8. ✅ **Testing** - الاختبارات
9. ✅ **Documentation** - التوثيق

كل خطوة مستقلة وقابلة للاختبار والصيانة!
