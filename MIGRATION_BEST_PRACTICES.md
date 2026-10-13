# 💡 نصائح وأفضل الممارسات لنقل المميزات
# Tips & Best Practices for Feature Migration

---

## 🎯 أفضل الممارسات

### 1️⃣ Separation of Concerns (فصل المخاوف)

**✅ صحيح:**
```python
# UI - فقط للعرض
class MyView(QWidget):
    def on_button_clicked(self):
        result = self.service.do_something()
        self.display_result(result)

# Service - نسق العمليات
class MyService:
    def do_something(self):
        return self.use_case.execute()

# UseCase - المنطق الأساسي
class MyUseCase:
    def execute(self):
        data = self.repo.get_data()
        return self.process_data(data)

# Repository - الوصول للبيانات
class MyRepository:
    def get_data(self):
        return self.db.execute("SELECT ...")
```

**❌ خطأ:**
```python
# وضع كل شيء في View
class MyView(QWidget):
    def on_button_clicked(self):
        # SQL مباشرة في View!
        self.db.execute("SELECT ... FROM ...")
        # منطق معقد في View!
        result = some_complex_calculation()
        self.display_result(result)
```

---

### 2️⃣ Dependency Injection (حقن الاعتماديات)

**✅ صحيح:**
```python
# Repository يتم حقنه في Service
class MyService:
    def __init__(self, repo: MyRepository):
        self.repo = repo  # تم حقنه

# Service يتم حقنه في View
class MyView:
    def __init__(self, service: MyService):
        self.service = service  # تم حقنه
```

**❌ خطأ:**
```python
# إنشاء اعتماديات مباشرة في الداخل
class MyView:
    def __init__(self):
        self.repo = MyRepository()  # ❌ مرتبط مباشرة
        self.service = MyService()  # ❌ مرتبط مباشرة
```

---

### 3️⃣ Error Handling (معالجة الأخطاء)

**✅ صحيح:**
```python
# معالجة الأخطاء في كل مستوى
class MyRepository:
    def create(self, item):
        try:
            self._execute("INSERT ...")
            self._commit()
            return True
        except Exception as e:
            logger.error(f"Error creating item: {e}")
            self._rollback()
            return False

class MyUseCase:
    def execute(self, name):
        if not name or not name.strip():
            logger.error("Name cannot be empty")
            return False
        return self.repo.create(name)

class MyView:
    def on_save(self):
        if not self.service.create(name):
            QMessageBox.warning(self, "خطأ", "فشلت العملية")
            return
        QMessageBox.information(self, "نجح", "تمت العملية بنجاح")
```

**❌ خطأ:**
```python
# عدم معالجة الأخطاء
class MyView:
    def on_save(self):
        self.service.create(name)  # قد يفشل صامتاً!
```

---

### 4️⃣ Logging (تسجيل العمليات)

**✅ صحيح:**
```python
import logging

logger = logging.getLogger(__name__)

class MyRepository:
    def create(self, item):
        try:
            self._execute("INSERT ...")
            logger.info(f"Item created: {item.name}")  # تسجيل النجاح
            return True
        except Exception as e:
            logger.error(f"Error creating item: {e}")  # تسجيل الفشل
            return False
```

**❌ خطأ:**
```python
# عدم تسجيل العمليات
def create(self, item):
    self._execute("INSERT ...")  # لا أحد يعرف ما حدث!
    return True
```

---

### 5️⃣ Validation (التحقق من الصحة)

**✅ صحيح:**
```python
# التحقق في Use Case (منطق الأعمال)
class CreateItemUseCase:
    def execute(self, name, email):
        # التحقق من أن الاسم ليس فارغاً
        if not name or not name.strip():
            logger.error("Name cannot be empty")
            return False
        
        # التحقق من صيغة البريد الإلكتروني
        if not self.is_valid_email(email):
            logger.error("Invalid email format")
            return False
        
        # إنشاء العنصر
        return self.repo.create(Item(name=name, email=email))
    
    def is_valid_email(self, email):
        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None
```

**❌ خطأ:**
```python
# عدم التحقق من الصحة
def create(self, name, email):
    return self.repo.create(Item(name=name, email=email))  # ❌ لا يتحقق من شيء
```

---

### 6️⃣ Database Transactions (معاملات قاعدة البيانات)

**✅ صحيح:**
```python
# استخدم Commit و Rollback
class MyRepository:
    def create_multiple(self, items):
        try:
            for item in items:
                self._execute("INSERT ...", (item.field1, item.field2))
            self._commit()  # حفظ جميع التغييرات
            logger.info(f"Created {len(items)} items")
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            self._rollback()  # تراجع عن كل شيء
            return False
```

**❌ خطأ:**
```python
# نسيان Commit أو عدم التعامل مع الأخطاء
def create_multiple(self, items):
    for item in items:
        self._execute("INSERT ...", (item.field1, item.field2))
        # ❌ لم يتم حفظ التغييرات!
        # ❌ لا يوجد Commit!
```

---

### 7️⃣ Type Hints (تلميحات الأنواع)

**✅ صحيح:**
```python
from typing import List, Optional

class MyRepository:
    def get_all(self) -> List[MyItem]:  # نوع الإرجاع
        return [MyItem.from_dict(row) for row in rows]
    
    def get_by_id(self, item_id: int) -> Optional[MyItem]:  # أنواع المعاملات والإرجاع
        row = self._fetch_one("SELECT ...", (item_id,))
        return MyItem.from_dict(row) if row else None
    
    def create(self, item: MyItem) -> bool:  # نوع المعامل والإرجاع
        return self._execute("INSERT ...", (...))
```

**❌ خطأ:**
```python
# بدون تلميحات الأنواع
def get_all(self):  # ❌ ما نوع الإرجاع؟
    return some_data

def get_by_id(self, id):  # ❌ ما نوع id؟ وما نوع الإرجاع؟
    return self.db.fetch_one("SELECT ...")
```

---

### 8️⃣ Constants & Configuration (الثوابت والإعدادات)

**✅ صحيح:**
```python
# استخدم Constants
class Config:
    MAX_NAME_LENGTH = 100
    MIN_NAME_LENGTH = 2
    SALT_ROUNDS = 12
    DATABASE_TIMEOUT = 30
    MAX_RETRY_ATTEMPTS = 3

# في Use Case
class CreateItemUseCase:
    def execute(self, name):
        if len(name) < Config.MIN_NAME_LENGTH:
            logger.error(f"Name must be at least {Config.MIN_NAME_LENGTH} characters")
            return False
        if len(name) > Config.MAX_NAME_LENGTH:
            logger.error(f"Name cannot exceed {Config.MAX_NAME_LENGTH} characters")
            return False
        # ...
```

**❌ خطأ:**
```python
# أرقام موزعة في الكود
def execute(self, name):
    if len(name) < 2:  # ❌ أين أتت 2؟
        return False
    if len(name) > 100:  # ❌ أين أتت 100؟
        return False
```

---

### 9️⃣ Documentation (التوثيق)

**✅ صحيح:**
```python
class MyRepository:
    """مستودع العمليات الخاصة بـ MyItem"""
    
    def create(self, item: MyItem) -> bool:
        """
        إنشاء عنصر جديد في قاعدة البيانات
        
        Args:
            item (MyItem): العنصر المراد إنشاؤه
        
        Returns:
            bool: True إذا نجحت العملية، False وإلا
        
        Raises:
            Exception: إذا حدث خطأ في قاعدة البيانات
        """
        try:
            self._execute("INSERT ...", (...))
            self._commit()
            logger.info(f"Item created: {item.name}")
            return True
        except Exception as e:
            logger.error(f"Error creating item: {e}")
            self._rollback()
            return False
```

**❌ خطأ:**
```python
# بدون توثيق
def create(self, item):
    self._execute("INSERT ...", (...))
    return True
```

---

### 🔟 Testing (الاختبارات)

**✅ صحيح:**
```python
# اكتب اختبارات لكل وحدة
import pytest

def test_create_item():
    """اختبار إنشاء عنصر جديد"""
    repo = MyRepository()
    item = MyItem(name="Test", description="Test Item")
    
    result = repo.create(item)
    
    assert result is True
    assert repo.get_by_id(item.id) is not None

def test_create_item_with_empty_name():
    """اختبار إنشاء عنصر باسم فارغ"""
    repo = MyRepository()
    item = MyItem(name="", description="Test Item")
    
    result = repo.create(item)
    
    assert result is False

def test_update_item():
    """اختبار تحديث عنصر موجود"""
    repo = MyRepository()
    # إنشاء عنصر أولاً
    item = MyItem(name="Old Name", description="Old Description")
    repo.create(item)
    
    # تحديث العنصر
    item.name = "New Name"
    result = repo.update(item)
    
    assert result is True
    updated = repo.get_by_id(item.id)
    assert updated.name == "New Name"
```

**❌ خطأ:**
```python
# بدون اختبارات - كيف تعرف أن الكود يعمل؟
# لا أحد يعرف!
```

---

## 🚀 نصائح الأداء

### 1. استخدم Prepared Statements:
```python
# ✅ صحيح - يحمي من SQL Injection
self._execute("SELECT * FROM items WHERE id = %s", (item_id,))

# ❌ خطأ - معرض لـ SQL Injection
self._execute(f"SELECT * FROM items WHERE id = {item_id}")
```

### 2. استخدم Indexes في قاعدة البيانات:
```python
# في Repository ensure_table():
CREATE TABLE items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP,
    INDEX idx_name (name),        # ✅ إضافة index
    INDEX idx_created_at (created_at)  # ✅ إضافة index
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3. تجنب N+1 Queries:
```python
# ❌ خطأ - N+1 queries
def get_items_with_categories(self):
    items = self._fetch_all("SELECT * FROM items")
    for item in items:
        # استعلام لكل عنصر!
        item.category = self._fetch_one(
            "SELECT * FROM categories WHERE id = %s",
            (item.category_id,)
        )
    return items

# ✅ صحيح - استعلام واحد فقط
def get_items_with_categories(self):
    return self._fetch_all("""
        SELECT i.*, c.* FROM items i
        JOIN categories c ON i.category_id = c.id
    """)
```

### 4. استخدم Caching للبيانات الثابتة:
```python
class MyRepository:
    def __init__(self):
        super().__init__()
        self._categories_cache = None
    
    def get_all_categories(self):
        if self._categories_cache is None:
            # جلب من قاعدة البيانات مرة واحدة فقط
            self._categories_cache = self._fetch_all("SELECT * FROM categories")
        return self._categories_cache
    
    def invalidate_cache(self):
        self._categories_cache = None
```

---

## 🐛 استكشاف الأخطاء

### استراتيجيات استكشاف الأخطاء:

#### 1. استخدم Logging بكثرة:
```python
logger.debug(f"Starting operation with params: {params}")
logger.info(f"Operation completed successfully")
logger.warning(f"Operation encountered issue but continued: {issue}")
logger.error(f"Operation failed with error: {error}")
```

#### 2. استخدم Try-Except بحكمة:
```python
try:
    result = self.service.create(item)
    logger.info("Item created successfully")
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

#### 3. استخدم Assertions للتطوير:
```python
def create(self, item: MyItem) -> bool:
    assert isinstance(item, MyItem), "item must be MyItem instance"
    assert item.name, "item name cannot be empty"
    # ...
```

---

## 🔒 الأمان

### 1. Always Validate Input:
```python
def create(self, name: str, email: str) -> bool:
    # تحقق من الفراغات
    if not name or not name.strip():
        logger.error("Name cannot be empty")
        return False
    
    # تحقق من الطول
    if len(name) > 100:
        logger.error("Name too long")
        return False
    
    # تحقق من الصيغة
    if not self.is_valid_email(email):
        logger.error("Invalid email format")
        return False
    
    # الآن آمن للعملية
    return self.repo.create(MyItem(name=name, email=email))
```

### 2. Use Parameterized Queries:
```python
# ✅ آمن من SQL Injection
self._execute("SELECT * FROM users WHERE email = %s", (email,))

# ❌ معرض للخطر
self._execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### 3. Hash Passwords:
```python
import bcrypt

# عند الإنشاء
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
self._execute("INSERT INTO users (...) VALUES (...)", (..., password_hash, ...))

# عند التحقق
if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
    # كلمة المرور صحيحة
    pass
```

---

## 📊 مثال كامل متقدم

```python
# models/advanced_item.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class AdvancedItem:
    id: int
    name: str
    email: str
    status: str = "active"
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AdvancedItem':
        return cls(
            id=data['id'],
            name=data['name'],
            email=data['email'],
            status=data.get('status', 'active'),
            created_at=data.get('created_at'),
        )

# repositories/advanced_item_repo.py
import logging
from typing import List, Optional
from repositories.base_repo import BaseRepository
from models.advanced_item import AdvancedItem

logger = logging.getLogger(__name__)

class AdvancedItemRepository(BaseRepository):
    def ensure_table(self):
        self._execute("""
            CREATE TABLE IF NOT EXISTS advanced_items (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        self._commit()
        logger.info("Advanced items table ensured")
    
    def create(self, item: AdvancedItem) -> bool:
        try:
            # تحقق من عدم وجود بريد مكرر
            existing = self._fetch_one(
                "SELECT id FROM advanced_items WHERE email = %s",
                (item.email,)
            )
            if existing:
                logger.warning(f"Email already exists: {item.email}")
                return False
            
            self._execute(
                """INSERT INTO advanced_items (name, email, status)
                   VALUES (%s, %s, %s)""",
                (item.name, item.email, item.status)
            )
            self._commit()
            logger.info(f"Item created: {item.name} ({item.email})")
            return True
        except Exception as e:
            logger.error(f"Error creating item: {e}")
            self._rollback()
            return False
    
    def get_all(self, status: Optional[str] = None) -> List[AdvancedItem]:
        if status:
            query = "SELECT * FROM advanced_items WHERE status = %s ORDER BY created_at DESC"
            rows = self._fetch_all(query, (status,))
        else:
            query = "SELECT * FROM advanced_items ORDER BY created_at DESC"
            rows = self._fetch_all(query)
        
        return [AdvancedItem.from_dict(row) for row in rows]
    
    def search(self, query: str) -> List[AdvancedItem]:
        search_pattern = f"%{query}%"
        rows = self._fetch_all(
            """SELECT * FROM advanced_items 
               WHERE name LIKE %s OR email LIKE %s
               ORDER BY created_at DESC""",
            (search_pattern, search_pattern)
        )
        return [AdvancedItem.from_dict(row) for row in rows]

# application/use_cases/advanced_item_management.py
from repositories.advanced_item_repo import AdvancedItemRepository
from models.advanced_item import AdvancedItem
import re

logger = logging.getLogger(__name__)

class CreateAdvancedItemUseCase:
    def __init__(self, repo: AdvancedItemRepository):
        self.repo = repo
    
    def execute(self, name: str, email: str) -> bool:
        # التحقق من الصحة
        if not self.validate_input(name, email):
            return False
        
        # إنشاء العنصر
        item = AdvancedItem(
            id=0,
            name=name.strip(),
            email=email.strip().lower(),
            status="active"
        )
        
        return self.repo.create(item)
    
    def validate_input(self, name: str, email: str) -> bool:
        # تحقق من الاسم
        if not name or not name.strip():
            logger.error("Name cannot be empty")
            return False
        
        if len(name) < 2 or len(name) > 100:
            logger.error(f"Name must be 2-100 characters")
            return False
        
        # تحقق من البريد الإلكتروني
        if not email or not email.strip():
            logger.error("Email cannot be empty")
            return False
        
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_pattern, email):
            logger.error(f"Invalid email format: {email}")
            return False
        
        return True
```

---

## ✨ الخلاصة

اتبع هذه النقاط:

1. **فصل المخاوف** - كل طبقة لها مسؤولية واحدة
2. **معالجة الأخطاء** - لا تتجاهل الأخطاء
3. **التحقق من الصحة** - تحقق من جميع الإدخالات
4. **التسجيل** - سجل كل شيء مهم
5. **الاختبار** - اكتب اختبارات شاملة
6. **التوثيق** - وثق كل جزء من الكود
7. **الأداء** - فكر في الأداء من البداية
8. **الأمان** - استخدم أفضل ممارسات الأمان

وتذكر: **الكود الذي يسهل فهمه وصيانته أفضل من الكود الذي يعمل فقط!**
