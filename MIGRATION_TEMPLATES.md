# 📝 قوالب جاهزة (Templates) لنقل المميزات بسرعة
# Ready-to-Use Templates for Feature Migration

## 🚀 كيفية استخدام هذه القوالب

انسخ القالب المناسب لكل طبقة وعدّل الأسماء والتفاصيل حسب مميزتك الجديدة.

---

## 📌 Template 1: Model (نموذج البيانات)

```python
# models/{{feature_name}}.py
"""
{{Feature_Name}} Model - نموذج {{اسم المميزة}}
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class {{FeatureName}}:
    """نموذج {{اسم المميزة}}"""
    id: int = 0
    {{field1}}: str = ""
    {{field2}}: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> '{{FeatureName}}':
        """إنشاء كائن من قاموس"""
        return cls(
            id=data.get('id', 0),
            {{field1}}=data.get('{{field1}}', ''),
            {{field2}}=data.get('{{field2}}'),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    def to_dict(self) -> dict:
        """تحويل إلى قاموس"""
        return {
            'id': self.id,
            '{{field1}}': self.{{field1}},
            '{{field2}}': self.{{field2}},
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
```

---

## 📌 Template 2: Repository (مستودع البيانات)

```python
# repositories/{{feature_name}}_repo.py
"""
{{FeatureName}} Repository - مستودع {{اسم المميزة}}
"""
import logging
from typing import List, Optional
from repositories.base_repo import BaseRepository
from models.{{feature_name}} import {{FeatureName}}

logger = logging.getLogger(__name__)


class {{FeatureName}}Repository(BaseRepository):
    """مستودع عمليات {{اسم المميزة}}"""

    def ensure_table(self) -> None:
        """التأكد من وجود الجدول"""
        self._execute("""
            CREATE TABLE IF NOT EXISTS {{table_name}} (
                id INT PRIMARY KEY AUTO_INCREMENT,
                {{field1}} VARCHAR(100) NOT NULL,
                {{field2}} VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        self._commit()

    def get_all(self, active_only: bool = True) -> List[{{FeatureName}}]:
        """جلب الجميع"""
        query = "SELECT * FROM {{table_name}}"
        if active_only:
            query += " WHERE is_active = TRUE"
        
        rows = self._fetch_all(query)
        return [{{FeatureName}}.from_dict(row) for row in rows]

    def get_by_id(self, {{feature_name}}_id: int) -> Optional[{{FeatureName}}]:
        """جلب بالمعرف"""
        row = self._fetch_one(
            "SELECT * FROM {{table_name}} WHERE id = %s",
            ({{feature_name}}_id,)
        )
        return {{FeatureName}}.from_dict(row) if row else None

    def create(self, {{feature_name}}: {{FeatureName}}) -> bool:
        """إنشاء جديد"""
        try:
            self._execute(
                """
                INSERT INTO {{table_name}} ({{field1}}, {{field2}}, is_active)
                VALUES (%s, %s, %s)
                """,
                ({{feature_name}}.{{field1}}, {{feature_name}}.{{field2}}, {{feature_name}}.is_active)
            )
            self._commit()
            logger.info(f"{{FeatureName}} created: {{{feature_name}}.{{field1}}")
            return True
        except Exception as e:
            logger.error(f"Error creating {{feature_name}}: {e}")
            self._rollback()
            return False

    def update(self, {{feature_name}}: {{FeatureName}}) -> bool:
        """تحديث موجود"""
        try:
            self._execute(
                """
                UPDATE {{table_name}} 
                SET {{field1}} = %s, {{field2}} = %s, is_active = %s
                WHERE id = %s
                """,
                ({{feature_name}}.{{field1}}, {{feature_name}}.{{field2}}, 
                 {{feature_name}}.is_active, {{feature_name}}.id)
            )
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error updating {{feature_name}}: {e}")
            self._rollback()
            return False

    def delete(self, {{feature_name}}_id: int) -> bool:
        """حذف"""
        try:
            self._execute(
                "DELETE FROM {{table_name}} WHERE id = %s",
                ({{feature_name}}_id,)
            )
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting {{feature_name}}: {e}")
            self._rollback()
            return False
```

---

## 📌 Template 3: Use Cases (حالات الاستخدام)

```python
# application/use_cases/{{feature_name}}_management.py
"""
{{FeatureName}} Management Use Cases - حالات الاستخدام
"""
import logging
from typing import List, Optional
from repositories.{{feature_name}}_repo import {{FeatureName}}Repository
from models.{{feature_name}} import {{FeatureName}}

logger = logging.getLogger(__name__)


class GetAll{{FeatureName}}UseCase:
    """جلب الكل"""
    def __init__(self, repo: {{FeatureName}}Repository):
        self.repo = repo
    
    def execute(self) -> List[{{FeatureName}}]:
        return self.repo.get_all()


class Get{{FeatureName}}ByIdUseCase:
    """جلب بالمعرف"""
    def __init__(self, repo: {{FeatureName}}Repository):
        self.repo = repo
    
    def execute(self, {{feature_name}}_id: int) -> Optional[{{FeatureName}}]:
        return self.repo.get_by_id({{feature_name}}_id)


class Create{{FeatureName}}UseCase:
    """إنشاء جديد"""
    def __init__(self, repo: {{FeatureName}}Repository):
        self.repo = repo
    
    def execute(self, {{field1}}: str, {{field2}}: str = None) -> bool:
        # التحقق من الصحة
        if not {{field1}} or not {{field1}}.strip():
            logger.error("{{field1}} cannot be empty")
            return False
        
        # إنشاء
        {{feature_name}} = {{FeatureName}}(
            {{field1}}={{field1}}.strip(),
            {{field2}}={{field2}},
            is_active=True
        )
        
        return self.repo.create({{feature_name}})


class Update{{FeatureName}}UseCase:
    """تحديث موجود"""
    def __init__(self, repo: {{FeatureName}}Repository):
        self.repo = repo
    
    def execute(self, {{feature_name}}_id: int, {{field1}}: str, 
                {{field2}}: str = None) -> bool:
        # التحقق من الصحة
        if not {{field1}} or not {{field1}}.strip():
            logger.error("{{field1}} cannot be empty")
            return False
        
        existing = self.repo.get_by_id({{feature_name}}_id)
        if not existing:
            logger.error(f"{{FeatureName}} not found: {{{feature_name}}_id}")
            return False
        
        {{feature_name}} = {{FeatureName}}(
            id={{feature_name}}_id,
            {{field1}}={{field1}}.strip(),
            {{field2}}={{field2}},
            is_active=existing.is_active
        )
        
        return self.repo.update({{feature_name}})


class Delete{{FeatureName}}UseCase:
    """حذف"""
    def __init__(self, repo: {{FeatureName}}Repository):
        self.repo = repo
    
    def execute(self, {{feature_name}}_id: int) -> bool:
        return self.repo.delete({{feature_name}}_id)
```

---

## 📌 Template 4: Service Facade (واجهة الخدمة)

```python
# application/services/{{feature_name}}_service_facade.py
"""
{{FeatureName}} Service Facade - واجهة الخدمة
"""
from typing import List, Optional
from repositories.{{feature_name}}_repo import {{FeatureName}}Repository
from models.{{feature_name}} import {{FeatureName}}
from application.use_cases.{{feature_name}}_management import (
    GetAll{{FeatureName}}UseCase,
    Get{{FeatureName}}ByIdUseCase,
    Create{{FeatureName}}UseCase,
    Update{{FeatureName}}UseCase,
    Delete{{FeatureName}}UseCase,
)


class {{FeatureName}}ServiceFacade:
    """واجهة خدمات {{اسم المميزة}}"""
    
    def __init__(self, repo: {{FeatureName}}Repository = None):
        self.repo = repo or {{FeatureName}}Repository()
        self.repo.ensure_table()
        
        # تهيئة Use Cases
        self.get_all_use_case = GetAll{{FeatureName}}UseCase(self.repo)
        self.get_by_id_use_case = Get{{FeatureName}}ByIdUseCase(self.repo)
        self.create_use_case = Create{{FeatureName}}UseCase(self.repo)
        self.update_use_case = Update{{FeatureName}}UseCase(self.repo)
        self.delete_use_case = Delete{{FeatureName}}UseCase(self.repo)
    
    def get_all(self) -> List[{{FeatureName}}]:
        return self.get_all_use_case.execute()
    
    def get_by_id(self, {{feature_name}}_id: int) -> Optional[{{FeatureName}}]:
        return self.get_by_id_use_case.execute({{feature_name}}_id)
    
    def create(self, {{field1}}: str, {{field2}}: str = None) -> bool:
        return self.create_use_case.execute({{field1}}, {{field2}})
    
    def update(self, {{feature_name}}_id: int, {{field1}}: str, {{field2}}: str = None) -> bool:
        return self.update_use_case.execute({{feature_name}}_id, {{field1}}, {{field2}})
    
    def delete(self, {{feature_name}}_id: int) -> bool:
        return self.delete_use_case.execute({{feature_name}}_id)
```

---

## 📌 Template 5: Controller (المتحكم)

```python
# controllers/{{feature_name}}_controller.py
"""
{{FeatureName}} Controller - متحكم {{اسم المميزة}}
"""
from application.services.{{feature_name}}_service_facade import {{FeatureName}}ServiceFacade
from repositories.{{feature_name}}_repo import {{FeatureName}}Repository


class {{FeatureName}}Controller:
    """متحكم {{اسم المميزة}}"""
    
    def __init__(self):
        self.service = {{FeatureName}}ServiceFacade({{FeatureName}}Repository())
    
    def __getattr__(self, name):
        return getattr(self.service, name)
    
    def __setattr__(self, name, value):
        if name == "service":
            super().__setattr__(name, value)
            return
        if "service" in self.__dict__:
            if hasattr(self.service, name):
                setattr(self.service, name, value)
                return
        super().__setattr__(name, value)
```

---

## 📌 Template 6: View (واجهة المستخدم)

```python
# ui/{{feature_name}}_view.py
"""
{{FeatureName}} View - واجهة {{اسم المميزة}}
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt
from application.services.{{feature_name}}_service_facade import {{FeatureName}}ServiceFacade
from ui.styles import COLORS, INPUT_STYLE, get_button_style

logger = logging.getLogger(__name__)


class {{FeatureName}}View(QWidget):
    """واجهة {{اسم المميزة}}"""
    
    def __init__(self, service: {{FeatureName}}ServiceFacade, parent=None):
        super().__init__(parent)
        self.service = service
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        """بناء الواجهة"""
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg_app']}; }}")
        
        layout = QVBoxLayout(self)
        
        # الأدوات العلوية
        toolbar = QHBoxLayout()
        
        # زر الإضافة
        self.add_btn = QPushButton("إضافة")
        self.add_btn.setStyleSheet(get_button_style("primary"))
        self.add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(self.add_btn)
        
        # زر التحديث
        self.refresh_btn = QPushButton("تحديث")
        self.refresh_btn.setStyleSheet(get_button_style("secondary"))
        self.refresh_btn.clicked.connect(self._load_data)
        toolbar.addWidget(self.refresh_btn)
        
        layout.addLayout(toolbar)
        
        # جدول البيانات
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["المعرف", "البيانات", "الإجراءات"])
        layout.addWidget(self.table)
    
    def _load_data(self):
        """تحميل البيانات"""
        try:
            data = self.service.get_all()
            self._populate_table(data)
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            QMessageBox.critical(self, "خطأ", f"خطأ: {e}")
    
    def _populate_table(self, data):
        """ملء الجدول"""
        self.table.setRowCount(len(data))
        # أضف الصفوف هنا
    
    def _on_add(self):
        """إضافة جديد"""
        dialog = {{FeatureName}}Dialog(self.service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_data()


class {{FeatureName}}Dialog(QDialog):
    """نموذج إضافة/تعديل"""
    
    def __init__(self, service: {{FeatureName}}ServiceFacade, item=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.item = item
        self.setWindowTitle("عنصر جديد" if not item else "تعديل العنصر")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._init_ui()
    
    def _init_ui(self):
        """بناء الواجهة"""
        layout = QVBoxLayout()
        
        # حقول الإدخال
        layout.addWidget(QLabel("الحقل 1:"))
        self.field1_input = QLineEdit()
        self.field1_input.setStyleSheet(INPUT_STYLE)
        layout.addWidget(self.field1_input)
        
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
        """حفظ"""
        # أضف منطق الحفظ هنا
        self.accept()
```

---

## 📝 نقائمة فحص سريعة (Quick Checklist)

عند نقل أي مميزة، تأكد من:

```
المرحلة 1: التخطيط
☐ تحليل المميزة من التطبيق القديم
☐ تحديد الجداول المطلوبة
☐ تحديد عمليات قاعدة البيانات

المرحلة 2: الإنشاء
☐ إنشاء Model
☐ إنشاء Repository مع ensure_table()
☐ إنشاء Use Cases
☐ إنشاء Service Facade
☐ إنشاء Controller
☐ إنشاء View

المرحلة 3: الربط
☐ إضافة Controller في main.py
☐ إضافة View في main.py
☐ ربط الأزرار والفعاليات

المرحلة 4: الاختبار
☐ اختبار الإضافة
☐ اختبار التحديث
☐ اختبار الحذف
☐ اختبار البحث/الفلترة

المرحلة 5: التحسين
☐ معالجة الأخطاء
☐ التوثيق
☐ إضافة رسائل التأكيد
☐ التحقق من الصحة
```

---

## 🔑 نقاط مهمة جداً

### ✅ يجب فعله:

1. **استخدم Clean Architecture** - فصل المخاوف
2. **وثق كل شيء** - قم بإضافة docstrings
3. **اختبر كل وحدة** - اكتب tests
4. **استخدم Constants** - لا تكرر الأرقام
5. **تعامل مع الأخطاء** - جميع الحالات الاستثنائية

### ❌ لا تفعل:

1. **لا تضع Logic في UI** - UI فقط للعرض
2. **لا تصل مباشرة للـ DB من View** - استخدم Repository
3. **لا تكرر الكود** - أنشئ functions مشتركة
4. **لا تنسَ التحقق من الصحة** - في Use Case
5. **لا تنسَ log الأخطاء** - استخدم logger

---

## 🎓 أمثلة إضافية

### استدعاء الخدمة من الـ View:
```python
# في الـ View
def on_button_clicked(self):
    result = self.service.create(name, description)
    if result:
        QMessageBox.information(self, "نجح", "تم بنجاح")
    else:
        QMessageBox.warning(self, "فشل", "فشل العملية")
```

### إضافة حقول جديدة:
```python
# في Model - أضف حقل جديد
@dataclass
class {{FeatureName}}:
    id: int = 0
    new_field: str = ""  # ← الحقل الجديد
    
# في Repository - حدّث SQL
def create(self, {{feature_name}}):
    self._execute(
        """INSERT INTO {{table}} 
        (field1, new_field) VALUES (%s, %s)""",
        ({{feature_name}}.field1, {{feature_name}}.new_field)
    )

# في View - أضف عنصر إدخال
self.new_field_input = QLineEdit()
layout.addWidget(self.new_field_input)
```

---

استخدم هذه القوالب كنقطة بداية وعدّلها حسب احتياجات مميزتك!
