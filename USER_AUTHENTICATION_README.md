# 👤 نظام المستخدمين والمصادقة - User Authentication System

## 🔍 المشكلة والحل

### ❌ المشكلة الأصلية:
عند محاولة تسجيل الدخول، تظهر رسالة **"بيانات الدخول غير صحيحة"**

### ✅ السبب والحل:
السبب: **لا توجد أي مستخدمين في قاعدة البيانات**

الحل: **إضافة مستخدم واحد على الأقل قبل تسجيل الدخول**

---

## 📋 الملفات الرئيسية

### 1️⃣ `setup_default_user.py` - إنشاء المستخدم الإداري الافتراضي
**الغرض**: إضافة مستخدم إداري افتراضي بسهولة

**الاستخدام**:
```bash
python setup_default_user.py
```

**النتيجة**:
- ✅ مستخدم جديد: `admin@hyperpos.com`
- 🔑 كلمة المرور: `Admin@123`
- 👑 الدور: مدير نظام (Admin)

---

### 2️⃣ `add_user.py` - إضافة مستخدمين جدد
**الغرض**: إضافة مستخدمين إضافيين بأدوار مختلفة

**الاستخدام من سطر الأوامر**:
```bash
python add_user.py "الاسم" "البريد" "كلمة_المرور" "الدور" "الفرع"
```

**مثال**:
```bash
python add_user.py "أحمد محمد" "ahmed@hyperpos.com" "Pass@123" "cashier" 1
```

**الاستخدام التفاعلي**:
```bash
python add_user.py
```

---

### 3️⃣ `add_user.bat` - واجهة سهلة لإضافة مستخدمين
**الغرض**: واجهة رسومية بسيطة (Windows)

**الاستخدام**: انقر مباشرة على `add_user.bat`

---

### 4️⃣ `check_users.py` - فحص المستخدمين الموجودين
**الغرض**: عرض جميع المستخدمين في قاعدة البيانات

**الاستخدام**:
```bash
python check_users.py
```

---

## 🚀 خطوات الإعداد الأولي

### الخطوة 1️⃣: تشغيل قاعدة البيانات
```bash
# تأكد من أن MySQL قيد التشغيل
# والاتصال صحيح في ملف .env
```

### الخطوة 2️⃣: إضافة المستخدم الافتراضي
```bash
python setup_default_user.py
```

### الخطوة 3️⃣: إضافة مستخدمين إضافيين (اختياري)
```bash
python add_user.py "اسم" "بريد" "كلمة_مرور" "دور"
```

### الخطوة 4️⃣: التحقق من المستخدمين
```bash
python check_users.py
```

### الخطوة 5️⃣: تشغيل البرنامج
```bash
python main.py
```

---

## 👥 الأدوار المتاحة

| الدور | الكود | الصلاحيات |
|------|------|---------|
| **مدير النظام** | `admin` | جميع الصلاحيات |
| **مدير المخزن** | `manager` | إدارة المخزن والموظفين |
| **كاشير** | `cashier` | المبيعات والفواتير |
| **Call Center** | `call_center` | إدارة الطلبات |
| **موظف المخزن** | `warehouse_staff` | إدارة المخزون |
| **محاسب** | `accountant` | التقارير المالية |
| **صاحب** | `owner` | صلاحيات كاملة |

---

## 📊 معلومات قاعدة البيانات

### جدول المستخدمين (`users`)
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,       -- كلمة مرور مشفرة بـ bcrypt
    phone VARCHAR(20),
    role_id INT NOT NULL,                 -- معرف الدور
    store_id INT NOT NULL,                -- معرف الفرع
    is_active BOOLEAN DEFAULT TRUE,       -- حالة المستخدم
    last_login TIMESTAMP,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

### تشفير كلمات المرور
- **الأسلوب**: bcrypt (مع salt rounds = 12)
- **الأمان**: مشفرة بشكل آمن وغير قابلة للفك

---

## 🔐 أمان تسجيل الدخول

### التحقق من الهوية
1. ✅ البحث عن المستخدم بالبريد الإلكتروني
2. ✅ التحقق من أن المستخدم مفعّل (`is_active = 1`)
3. ✅ المقارنة الآمنة لكلمة المرور باستخدام bcrypt
4. ✅ التحقق من صلاحيات الدور
5. ✅ التحقق من تفويض الجهاز (اختياري)

---

## 🛠️ استكشاف الأخطاء

### ❌ "بيانات الدخول غير صحيحة"
**المسببات الممكنة**:
1. ❌ لا توجد مستخدمون → **الحل**: `python setup_default_user.py`
2. ❌ البريد غير صحيح → **الحل**: تحقق من البيانات المدخلة
3. ❌ كلمة المرور خاطئة → **الحل**: أعد إنشاء المستخدم
4. ❌ المستخدم معطّل → **الحل**: تفعيل المستخدم من قاعدة البيانات

### ❌ "الدور غير موجود"
**الحل**: 
```bash
python add_user.py    # سيعرض الأدوار المتاحة
```

### ❌ "الفرع غير موجود"
**الحل**: تأكد من وجود فرع واحد على الأقل في جدول `stores`

---

## 📝 أمثلة عملية

### مثال 1: إضافة مستخدم إداري
```bash
python add_user.py "محمد علي" "admin@store.com" "SecurePass@123" "admin" 1
```

### مثال 2: إضافة كاشير
```bash
python add_user.py "أحمد محمود" "cashier1@store.com" "CashierPass@123" "cashier" 1
```

### مثال 3: إضافة مدير مخزن
```bash
python add_user.py "فاطمة حسن" "manager@store.com" "ManagerPass@123" "manager" 1
```

---

## 🔄 تغيير كلمة المرور

### من قاعدة البيانات مباشرة:
```python
import bcrypt
from repositories.db_connection import DatabaseConnection

db = DatabaseConnection()
new_password = "NewPass@123"
password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt(rounds=12))

db.execute(
    "UPDATE users SET password = %s WHERE email = %s",
    (password_hash, 'admin@hyperpos.com')
)
db.commit()
```

---

## 🎯 الخطوة التالية

بعد إضافة المستخدم بنجاح:
```bash
python main.py
```

ثم:
1. أدخل البريد: `admin@hyperpos.com`
2. أدخل كلمة المرور: `Admin@123`
3. اضغط تسجيل الدخول ✅

---

## 📚 ملفات التوثيق الأخرى

- [LICENSE_ACTIVATION_README.md](LICENSE_ACTIVATION_README.md) - نظام التفعيل
- [QUICK_START.md](QUICK_START.md) - البدء السريع
