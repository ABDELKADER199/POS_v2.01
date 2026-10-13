# 📋 خطة نقل المميزات من التطبيق القديم إلى الجديد
# Migration Plan - Clean Architecture

## 🏗️ معمارية التطبيق الجديد (Clean Architecture)

### الطبقات الخمس:

```
┌─────────────────────────────────────────────────────┐
│  UI LAYER (واجهة المستخدم)                        │
│  └─ ui/*.py (PyQt6 Views/Screens)                  │
├─────────────────────────────────────────────────────┤
│  CONTROLLER LAYER (طبقة التحكم - رقيقة جداً)      │
│  └─ controllers/*.py (تمرير الاستدعاءات فقط)     │
├─────────────────────────────────────────────────────┤
│  APPLICATION LAYER (طبقة التطبيق)                  │
│  ├─ application/services/*.py (Facades)            │
│  └─ application/use_cases/*.py (Business Logic)    │
├─────────────────────────────────────────────────────┤
│  DOMAIN LAYER (طبقة المنطق)                        │
│  └─ models/*.py (Business Entities)                │
├─────────────────────────────────────────────────────┤
│  DATA LAYER (طبقة البيانات)                        │
│  ├─ repositories/*.py (Data Access)                │
│  └─ db_connection.py (Database Connection)         │
└─────────────────────────────────────────────────────┘
```

---

## 📊 المميزات الرئيسية المراد نقلها

### ✅ المقسمة حسب الأولوية والتعقيد

---

## 🔴 المرحلة 1: المميزات الأساسية (الأولوية العالية)

### 1. نظام الفواتير والمبيعات (Cashier)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] سلة المشتريات المتقدمة
- [ ] معالجة الخصومات والعروض الترويجية
- [ ] نظام الدفع المتعدد
- [ ] فواتير معلقة
- [ ] ملخص المبيعات اليومية

#### خطوات النقل:
```
1. UI Layer (ui/cashier_view.py - موجودة)
   ├─ تحسين واجهة سلة المشتريات
   ├─ إضافة عناصر تحكم الخصومات
   └─ إضافة عناصر نظام الدفع

2. Controller Layer (controllers/cashier_controller.py - موجودة)
   └─ تمرير الاستدعاءات للـ Service Facade

3. Application Layer
   ├─ application/services/cashier_service_facade.py ✅
   └─ application/use_cases/
      ├─ cashier_cart.py ✅
      ├─ checkout_sale.py ✅
      ├─ held_invoices.py ✅
      └─ receipt_data.py ✅

4. Models Layer
   ├─ models/invoice.py ✅
   └─ models/product.py ✅

5. Data Layer
   ├─ repositories/invoice_repo.py ✅
   ├─ repositories/product_repo.py ✅
   └─ repositories/settings_repo.py ✅
```

---

### 2. إدارة المنتجات (Product Management)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] البحث والفلترة المتقدمة
- [ ] إضافة/تعديل/حذف منتجات
- [ ] إدارة الفئات
- [ ] الأسعار والخصومات
- [ ] استيراد المنتجات من ملفات Excel

#### خطوات النقل:
```
1. UI Layer
   ├─ ui/product_view.py ✅
   └─ تحسين جداول المنتجات

2. Controller Layer
   └─ controllers/product_controller.py ✅

3. Application Layer
   ├─ application/services/product_service_facade.py ✅
   └─ application/use_cases/
      ├─ product_management.py ✅
      ├─ product_lookup.py ✅
      └─ import_products.py ✅

4. Data Layer
   └─ repositories/product_repo.py ✅
```

---

### 3. التقارير والإحصائيات (Statistics)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] تقارير المبيعات اليومية
- [ ] تقارير الأداء
- [ ] الرسوم البيانية والمخططات
- [ ] تقارير الخسائر والأرباح
- [ ] تقارير الجرد

#### خطوات النقل:
```
1. UI Layer
   ├─ ui/stats_view.py ✅
   ├─ ui/custom_charts.py ✅
   └─ ui/profit_loss_dialog.py ✅

2. Controller Layer
   └─ controllers/stats_controller.py ✅

3. Application Layer
   ├─ application/services/stats_service_facade.py ✅
   └─ application/use_cases/stats.py ✅

4. Data Layer
   └─ repositories/stats_repo.py (قد تحتاج إضافة)
```

---

## 🟡 المرحلة 2: المميزات المتوسطة

### 4. إدارة الفروع والأدراج (Drawer Management)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] فتح/إغلاق الأدراج
- [ ] تسليم الأدراج
- [ ] تقارير الأدراج
- [ ] تتبع النقود

#### خطوات النقل:
```
1. UI Layer
   └─ ui/drawer_view.py ✅

2. Controller Layer
   └─ controllers/drawer_controller.py ✅

3. Application Layer
   ├─ application/services/drawer_service_facade.py ✅
   └─ application/use_cases/manage_drawer.py ✅

4. Data Layer
   └─ repositories/drawer_repo.py ✅
```

---

### 5. إدارة المشتريات (Purchases)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] إضافة طلبيات شراء
- [ ] تتبع الطلبيات
- [ ] استقبال البضائع
- [ ] فاتورة الدخول
- [ ] إدارة الموردين

#### خطوات النقل:
```
1. UI Layer
   └─ ui/purchases_view.py ✅

2. Controller Layer
   └─ controllers/purchases_controller.py ✅

3. Application Layer
   ├─ application/services/purchases_service_facade.py ✅
   └─ application/use_cases/purchases.py ✅

4. Data Layer
   └─ repositories/purchases_repo.py ✅
```

---

### 6. الحسابات والعملاء (Accounts)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] إدارة العملاء
- [ ] حسابات العملاء
- [ ] الديون والاستحقاقات
- [ ] سجل العملاء

#### خطوات النقل:
```
1. UI Layer
   └─ ui/accounts_view.py ✅

2. Controller Layer
   └─ controllers/accounts_controller.py ✅

3. Application Layer
   ├─ application/services/accounts_service_facade.py ✅
   └─ application/use_cases/accounts.py ✅

4. Data Layer
   └─ repositories/accounts_repo.py ✅
```

---

## 🟢 المرحلة 3: المميزات المتقدمة

### 7. إدارة المردود (Returns)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] معالجة المردود
- [ ] إرجاع المنتجات
- [ ] ملاحظات المردود
- [ ] تقارير المردود

---

### 8. مركز الاتصالات (Call Center)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] إدارة الطلبات من العملاء
- [ ] متابعة الطلبات
- [ ] إدارة الاتصالات

---

### 9. جرد المخزون (Inventory Count)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] إنشاء جلسات جرد
- [ ] إدخال الكميات المعدودة
- [ ] مقارنة ومعالجة الفروقات

---

### 10. التحويلات بين الفروع (Transfers)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] طلب تحويل منتجات
- [ ] استقبال التحويلات
- [ ] تتبع التحويلات

---

## 🔵 المرحلة 4: المميزات الإضافية

### 11. الإدارة والإعدادات (Admin & Settings)
**الحالة الحالية**: ✅ موجودة جزئياً

#### ما يجب إضافته:
- [ ] إدارة المستخدمين
- [ ] إدارة الأدوار والصلاحيات
- [ ] إعدادات النظام
- [ ] سجل التدقيق
- [ ] النسخ الاحتياطي

---

### 12. المتطلبات التقنية الإضافية
- [ ] نظام المزامنة (Sync System) ✅
- [ ] نظام النسخ الاحتياطي (Backup) ✅
- [ ] نظام الطباعة (Print System)
- [ ] نظام الترميز (Barcode System)

---

## 📋 جدول العمل الموصى به

### الأسبوع 1-2: المرحلة 1 (المميزات الأساسية)
- [ ] إكمال نظام الفواتير
- [ ] إكمال إدارة المنتجات
- [ ] إكمال التقارير الأساسية

### الأسبوع 3-4: المرحلة 2 (المميزات المتوسطة)
- [ ] إدارة الأدراج
- [ ] المشتريات
- [ ] الحسابات

### الأسبوع 5-6: المرحلة 3 (المميزات المتقدمة)
- [ ] المردود
- [ ] Call Center
- [ ] الجرد
- [ ] التحويلات

### الأسبوع 7-8: المرحلة 4 (الإدارة والتحسينات)
- [ ] الإدارة والإعدادات
- [ ] النسخ الاحتياطي
- [ ] الطباعة والترميز

---

## ✅ قائمة تحقق للنقل

### لكل مميزة، يجب:

```
☐ 1. تحليل المميزة في التطبيق القديم
   ├─ شاشاته وعناصره
   ├─ منطق عمله
   └─ قاعدة بيانات

☐ 2. إنشاء Use Case الخاص به
   └─ application/use_cases/feature_name.py

☐ 3. إنشاء Repository إذا لم يكن موجوداً
   └─ repositories/feature_repo.py

☐ 4. إنشاء Model الخاص به
   └─ models/feature_model.py

☐ 5. إنشاء Service Facade
   └─ application/services/feature_service_facade.py

☐ 6. إنشاء Controller
   └─ controllers/feature_controller.py

☐ 7. إنشاء View
   └─ ui/feature_view.py

☐ 8. ربط View مع Controller
   └─ main.py

☐ 9. اختبار المميزة
   └─ tests/test_feature.py

☐ 10. توثيق المميزة
   └─ documentation
```

---

## 🔄 نمط النقل الموحد

### لكل مميزة:

#### 1. **Database/Model**
```python
# models/feature.py
@dataclass
class Feature:
    id: int
    name: str
    # ... other fields
```

#### 2. **Repository**
```python
# repositories/feature_repo.py
class FeatureRepository(BaseRepository):
    def get_all(self):
        return self._fetch_all("SELECT * FROM features")
    
    def create(self, feature: Feature):
        self._execute(
            "INSERT INTO features (...) VALUES (...)",
            (feature.id, feature.name, ...)
        )
        self._commit()
```

#### 3. **Use Case**
```python
# application/use_cases/feature.py
class FeatureUseCase:
    def __init__(self, repo: FeatureRepository):
        self.repo = repo
    
    def execute(self):
        return self.repo.get_all()
```

#### 4. **Service Facade**
```python
# application/services/feature_service_facade.py
class FeatureServiceFacade:
    def __init__(self, repo: FeatureRepository):
        self.use_case = FeatureUseCase(repo)
    
    def get_all_features(self):
        return self.use_case.execute()
```

#### 5. **Controller**
```python
# controllers/feature_controller.py
class FeatureController:
    def __init__(self):
        self.service = FeatureServiceFacade(FeatureRepository())
    
    def __getattr__(self, name):
        return getattr(self.service, name)
```

#### 6. **View**
```python
# ui/feature_view.py
class FeatureView(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._init_ui()
    
    def _init_ui(self):
        # PyQt6 UI elements
        pass
    
    def on_button_clicked(self):
        result = self.service.get_all_features()
        # Update UI
```

#### 7. **Wiring (main.py)**
```python
# main.py
from controllers.feature_controller import FeatureController
from ui.feature_view import FeatureView

self.feature_ctrl = FeatureController()
self.feature_view = FeatureView(self.feature_ctrl.service)
self.stacked_widget.addWidget(self.feature_view)
```

---

## 🎯 نقاط مهمة في النقل

### ✅ ماذا يجب عمله:
1. **الالتزام بـ Clean Architecture** - كل طبقة لها دورها
2. **فصل المخاوف** - UI منفصل عن Business Logic
3. **قابلية الاختبار** - كود يسهل اختباره
4. **إعادة الاستخدام** - كود يمكن إعادة استخدامه
5. **التوثيق الجيد** - شرح واضح للكود

### ❌ ماذا يجب تجنبه:
1. **وضع Logic في UI** - UI فقط لعرض البيانات
2. **الاتصال المباشر بـ DB من View** - استخدم Repository
3. **عدم التوثيق** - وثق كل وحدة
4. **Hardcoding** - استخدم Constants
5. **تكرار الكود** - استخدم Functions المشتركة

---

## 📚 مثال عملي كامل

سيتم إنشاء مثال عملي تفصيلي لنقل مميزة واحدة بالكامل.

---

## 🔗 المراجع

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Design Patterns](https://refactoring.guru/design-patterns)
