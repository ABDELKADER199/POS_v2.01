# 🧪 دليل الاختبار و Debugging
# Testing & Debugging Guide

---

## 🧪 كتابة الاختبارات

### 1. اختبار المستودع (Repository Tests)

```python
# tests/test_category_repository.py
"""
اختبارات مستودع الفئات
"""
import pytest
from repositories.category_repo import CategoryRepository
from models.category import Category


@pytest.fixture
def repo():
    """إنشاء مستودع للاختبار"""
    return CategoryRepository()


class TestCategoryRepository:
    """مجموعة اختبارات مستودع الفئات"""
    
    def test_ensure_table_creates_table(self, repo):
        """اختبار: التأكد من إنشاء الجدول"""
        repo.ensure_table()  # يجب أن لا يرفع أي استثناء
        
        # تحقق من وجود الجدول
        result = repo._fetch_one("SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='categories'")
        assert result is not None
    
    def test_create_category(self, repo):
        """اختبار: إنشاء فئة جديدة"""
        repo.ensure_table()
        category = Category(category_name="ملابس", description="الملابس والأحذية")
        
        result = repo.create(category)
        
        assert result is True
        assert category.id > 0
    
    def test_create_duplicate_category(self, repo):
        """اختبار: منع إنشاء فئات مكررة"""
        repo.ensure_table()
        category1 = Category(category_name="ملابس")
        category2 = Category(category_name="ملابس")
        
        repo.create(category1)
        result = repo.create(category2)
        
        assert result is False
    
    def test_get_all_categories(self, repo):
        """اختبار: جلب جميع الفئات"""
        repo.ensure_table()
        
        # إنشاء عدة فئات
        repo.create(Category(category_name="ملابس"))
        repo.create(Category(category_name="إلكترونيات"))
        repo.create(Category(category_name="كتب"))
        
        categories = repo.get_all()
        
        assert len(categories) >= 3
    
    def test_get_category_by_id(self, repo):
        """اختبار: جلب فئة بالمعرف"""
        repo.ensure_table()
        category = Category(category_name="ملابس", description="ملابس رجالية")
        repo.create(category)
        
        retrieved = repo.get_by_id(category.id)
        
        assert retrieved is not None
        assert retrieved.category_name == "ملابس"
        assert retrieved.description == "ملابس رجالية"
    
    def test_update_category(self, repo):
        """اختبار: تحديث فئة"""
        repo.ensure_table()
        category = Category(category_name="ملابس")
        repo.create(category)
        
        # تحديث الفئة
        category.category_name = "ملابس رجالية"
        category.description = "تحديث جديد"
        result = repo.update(category)
        
        assert result is True
        updated = repo.get_by_id(category.id)
        assert updated.category_name == "ملابس رجالية"
    
    def test_delete_category(self, repo):
        """اختبار: حذف فئة"""
        repo.ensure_table()
        category = Category(category_name="ملابس")
        repo.create(category)
        
        result = repo.delete(category.id)
        
        assert result is True
        retrieved = repo.get_by_id(category.id)
        assert retrieved is None
    
    def test_search_categories(self, repo):
        """اختبار: البحث في الفئات"""
        repo.ensure_table()
        repo.create(Category(category_name="ملابس رجالية"))
        repo.create(Category(category_name="ملابس نسائية"))
        repo.create(Category(category_name="إلكترونيات"))
        
        results = repo.search("ملابس")
        
        assert len(results) == 2
        names = [cat.category_name for cat in results]
        assert "ملابس رجالية" in names
        assert "ملابس نسائية" in names
```

---

### 2. اختبار Use Cases

```python
# tests/test_category_use_cases.py
"""
اختبارات حالات الاستخدام الخاصة بالفئات
"""
import pytest
from repositories.category_repo import CategoryRepository
from application.use_cases.category_management import (
    CreateCategoryUseCase,
    UpdateCategoryUseCase,
    DeleteCategoryUseCase,
)


@pytest.fixture
def repo():
    repo = CategoryRepository()
    repo.ensure_table()
    return repo


class TestCreateCategoryUseCase:
    """اختبارات إنشاء فئة جديدة"""
    
    def test_create_valid_category(self, repo):
        """اختبار: إنشاء فئة بصحة تامة"""
        use_case = CreateCategoryUseCase(repo)
        
        result = use_case.execute("ملابس", "الملابس والأحذية")
        
        assert result is True
    
    def test_create_category_with_empty_name(self, repo):
        """اختبار: منع إنشاء فئة باسم فارغ"""
        use_case = CreateCategoryUseCase(repo)
        
        result = use_case.execute("", "description")
        
        assert result is False
    
    def test_create_category_with_short_name(self, repo):
        """اختبار: منع إنشاء فئة باسم قصير جداً"""
        use_case = CreateCategoryUseCase(repo)
        
        result = use_case.execute("م", "description")
        
        assert result is False
    
    def test_create_category_with_spaces_only(self, repo):
        """اختبار: منع إنشاء فئة باسم فارغ (فقط مسافات)"""
        use_case = CreateCategoryUseCase(repo)
        
        result = use_case.execute("   ", "description")
        
        assert result is False


class TestUpdateCategoryUseCase:
    """اختبارات تحديث فئة"""
    
    def test_update_existing_category(self, repo):
        """اختبار: تحديث فئة موجودة"""
        # إنشاء فئة أولاً
        create_use_case = CreateCategoryUseCase(repo)
        create_use_case.execute("ملابس", "الملابس")
        
        categories = repo.get_all()
        category_id = categories[0].id
        
        # تحديث الفئة
        update_use_case = UpdateCategoryUseCase(repo)
        result = update_use_case.execute(
            category_id,
            "ملابس رجالية",
            "الملابس الرجالية"
        )
        
        assert result is True
    
    def test_update_non_existing_category(self, repo):
        """اختبار: منع تحديث فئة غير موجودة"""
        update_use_case = UpdateCategoryUseCase(repo)
        
        result = update_use_case.execute(999, "اسم جديد")
        
        assert result is False


class TestDeleteCategoryUseCase:
    """اختبارات حذف فئة"""
    
    def test_delete_category(self, repo):
        """اختبار: حذف فئة"""
        # إنشاء فئة أولاً
        create_use_case = CreateCategoryUseCase(repo)
        create_use_case.execute("ملابس")
        
        categories = repo.get_all()
        category_id = categories[0].id
        
        # حذف الفئة
        delete_use_case = DeleteCategoryUseCase(repo)
        result = delete_use_case.execute(category_id)
        
        assert result is True
```

---

### 3. اختبار Service Facade

```python
# tests/test_category_service.py
"""
اختبارات واجهة خدمات الفئات
"""
import pytest
from repositories.category_repo import CategoryRepository
from application.services.category_service_facade import CategoryServiceFacade


@pytest.fixture
def service():
    repo = CategoryRepository()
    repo.ensure_table()
    return CategoryServiceFacade(repo)


class TestCategoryServiceFacade:
    """اختبارات واجهة خدمات الفئات"""
    
    def test_get_all_categories(self, service):
        """اختبار: جلب جميع الفئات"""
        # إنشاء عدة فئات
        service.create_category("ملابس")
        service.create_category("إلكترونيات")
        
        categories = service.get_all_categories()
        
        assert len(categories) >= 2
    
    def test_create_and_retrieve_category(self, service):
        """اختبار: إنشاء وجلب فئة"""
        # إنشاء
        service.create_category("ملابس", "الملابس والأحذية")
        
        # جلب
        categories = service.search_categories("ملابس")
        
        assert len(categories) > 0
        assert categories[0].category_name == "ملابس"
    
    def test_update_category_through_service(self, service):
        """اختبار: تحديث عبر الخدمة"""
        # إنشاء
        service.create_category("ملابس")
        categories = service.search_categories("ملابس")
        category_id = categories[0].id
        
        # تحديث
        result = service.update_category(
            category_id,
            "ملابس رجالية",
            "تحديث الوصف"
        )
        
        assert result is True
        updated = service.get_category(category_id)
        assert updated.category_name == "ملابس رجالية"
    
    def test_delete_category_through_service(self, service):
        """اختبار: حذف عبر الخدمة"""
        # إنشاء
        service.create_category("ملابس")
        categories = service.search_categories("ملابس")
        category_id = categories[0].id
        
        # حذف
        result = service.delete_category(category_id)
        
        assert result is True
        deleted = service.get_category(category_id)
        assert deleted is None
```

---

## 🐛 استراتيجيات Debugging

### 1. استخدام Logging مكثف

```python
import logging

# في __init__.py من المجلد
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# في كل ملف
logger = logging.getLogger(__name__)

# في الكود
logger.debug(f"Starting operation with params: {params}")
logger.info(f"Operation completed successfully")
logger.warning(f"Operation encountered issue: {issue}")
logger.error(f"Operation failed: {error}")
logger.critical(f"Critical error: {error}")
```

---

### 2. استخدام Print Debugging (مؤقتاً فقط)

```python
def create_category(self, name, description):
    print(f"[DEBUG] Creating category: name={name}, description={description}")
    
    # تحقق من الصحة
    print(f"[DEBUG] Validating input...")
    if not name:
        print(f"[DEBUG] Name is empty!")
        return False
    print(f"[DEBUG] Validation passed")
    
    # إنشاء
    print(f"[DEBUG] Creating in database...")
    result = self.repo.create(Category(name=name, description=description))
    print(f"[DEBUG] Result: {result}")
    
    return result
```

**ملاحظة**: احذف `print` عندما تنتهي من الـ Debugging واستخدم `logger` بدلاً منه.

---

### 3. استخدام Python Debugger

```python
import pdb

def problematic_function(self, data):
    pdb.set_trace()  # سيتوقف هنا عند التنفيذ
    # الآن يمكنك:
    # - print(data) - طباعة المتغيرات
    # - c - متابعة التنفيذ
    # - n - الخطوة التالية
    # - s - الدخول للدالة
    # - l - عرض السطور
    # - q - الخروج
    
    result = self.service.do_something(data)
    return result
```

---

### 4. استخدام Assertions للتطوير

```python
def create_category(self, name, description):
    # تأكد من أن name موجود ونوع صحيح
    assert name, "name cannot be None or empty"
    assert isinstance(name, str), f"name must be str, got {type(name)}"
    
    # تأكد من أن description نوع صحيح (إن وجد)
    assert description is None or isinstance(description, str), \
        f"description must be str or None, got {type(description)}"
    
    # الآن نعرف أن المدخلات صحيحة
    category = Category(name=name, description=description)
    return self.repo.create(category)
```

---

## 🔍 نصائح الـ Debugging

### 1. اقرأ رسالة الخطأ بعناية

```
❌ خطأ:
TypeError: 'NoneType' object is not subscriptable
  File "repo.py", line 25, in create
    name = data['name']
```

**معنى الخطأ:**
- `data` قيمتها `None`
- تحاول الوصول إلى `data['name']` (وهو خطأ)

**الحل:**
```python
def create(self, data):
    if data is None:
        logger.error("Data is None")
        return False
    if 'name' not in data:
        logger.error("'name' key not found in data")
        return False
    # الآن آمن
    name = data['name']
```

---

### 2. تتبع تدفق البيانات

```python
def create_item(self, name):
    print(f"[1] Input: name={name}, type={type(name)}")
    
    # التحقق من الصحة
    if not name:
        print(f"[2] Validation failed: name is empty/None")
        return False
    print(f"[2] Validation passed")
    
    # إنشاء كائن
    item = Category(name=name)
    print(f"[3] Created item: {item}")
    
    # حفظ
    result = self.repo.create(item)
    print(f"[4] Save result: {result}")
    
    return result
```

**الناتج المتوقع:**
```
[1] Input: name='ملابس', type=<class 'str'>
[2] Validation passed
[3] Created item: Category(name='ملابس')
[4] Save result: True
```

---

### 3. اختبر الأجزاء بمعزل عن البقية

```python
# اختبر Repository وحده
repo = CategoryRepository()
repo.ensure_table()
success = repo.create(Category(name="ملابس"))
print(f"Repository test: {success}")

# اختبر Use Case وحده
use_case = CreateCategoryUseCase(repo)
success = use_case.execute("إلكترونيات")
print(f"Use Case test: {success}")

# اختبر Service وحده
service = CategoryServiceFacade(repo)
success = service.create_category("كتب")
print(f"Service test: {success}")
```

---

### 4. استخدم Try-Except للحصول على تفاصيل الخطأ

```python
try:
    result = self.service.create_category(name, description)
except TypeError as e:
    logger.error(f"Type error: {e}")
    import traceback
    traceback.print_exc()
except ValueError as e:
    logger.error(f"Value error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
```

---

## 📊 استراتيجية اختبار شاملة

### الخطوات:

1. **Unit Tests** - اختبر كل وحدة بمعزل:
   ```
   Model ✅
   Repository ✅
   Use Case ✅
   Service ✅
   ```

2. **Integration Tests** - اختبر التفاعل بين الوحدات:
   ```
   Repository + Use Case ✅
   Use Case + Service ✅
   Service + Controller ✅
   ```

3. **End-to-End Tests** - اختبر المسار الكامل:
   ```
   User clicks button → Controller → Service → Use Case → Repository → Database → عرض النتيجة ✅
   ```

4. **Edge Cases** - اختبر الحالات الحدية:
   ```
   إدخال فارغ ✅
   إدخال كبير جداً ✅
   إدخال خاص جداً ✅
   خطأ قاعدة البيانات ✅
   ```

---

## 🚨 الأخطاء الشائعة و حلولها

### خطأ 1: NoneType

```python
❌ الخطأ:
TypeError: 'NoneType' object is not subscriptable
result = data['key']

✅ الحل:
if data is None:
    logger.error("Data is None")
    return False
result = data.get('key')  # استخدم get بدلاً من []
```

---

### خطأ 2: Uncommitted Changes

```python
❌ الخطأ:
def create(self, item):
    self._execute("INSERT ...", (...))
    # نسيان commit!
    return self._last_id  # لم تُحفظ البيانات!

✅ الحل:
def create(self, item):
    self._execute("INSERT ...", (...))
    self._commit()  # حفظ التغييرات
    return self._last_id
```

---

### خطأ 3: SQL Injection

```python
❌ الخطأ:
self._execute(f"SELECT * FROM items WHERE name = '{name}'")
# خطير جداً!

✅ الحل:
self._execute("SELECT * FROM items WHERE name = %s", (name,))
# استخدم parameterized queries
```

---

### خطأ 4: Infinite Loop

```python
❌ الخطأ:
while True:
    result = self.service.create(item)
    # لن يخرج من الحلقة أبداً!

✅ الحل:
max_attempts = 3
for attempt in range(max_attempts):
    result = self.service.create(item)
    if result:
        break
    logger.warning(f"Attempt {attempt + 1} failed")
```

---

### خطأ 5: Memory Leak

```python
❌ الخطأ:
class MyService:
    def __init__(self):
        self.cache = []  # قائمة تنمو بلا حدود!
    
    def add_to_cache(self, item):
        self.cache.append(item)

✅ الحل:
class MyService:
    def __init__(self):
        self.cache = {}  # استخدم dictionary مع حد أقصى
        self.max_cache_size = 100
    
    def add_to_cache(self, item):
        if len(self.cache) >= self.max_cache_size:
            # احذف العناصر القديمة
            oldest_key = list(self.cache.keys())[0]
            del self.cache[oldest_key]
        self.cache[item.id] = item
```

---

## 📋 قائمة تحقق قبل الإطلاق

```
☐ جميع الاختبارات تمر بنجاح
☐ لا توجد رسائل خطأ غير المعالجة
☐ جميع المتغيرات مهيأة قبل الاستخدام
☐ جميع العمليات لها commit أو rollback
☐ لا توجد SQL Injection
☐ جميع الإدخالات تم التحقق منها
☐ جميع الأخطاء يتم تسجيلها
☐ لا توجد طباعات debug في الكود
☐ جميع الوثائق محدثة
☐ لا توجد hardcoded values
☐ جميع الموارد يتم تحريرها (close connections, etc)
☐ الأداء مقبولة
☐ الأمان كافٍ
```

---

استمتع بالـ Debugging! 🚀
