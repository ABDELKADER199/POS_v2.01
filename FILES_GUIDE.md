# 📁 دليل الملفات المهمة

## 🎯 للبدء السريع

### 👉 الخطوة الأولى والوحيدة:
```bash
انقر على: run.bat
```

أو:
```bash
python main.py
```

---

## 🔍 ملفات الإعداد الأولي

### 1. إضافة مستخدم إداري
```bash
python setup_default_user.py
```
**أو**: انقر على أي من الملفات التالية:
- `run.bat` - سيعمل المدقق التلقائي

---

### 2. إضافة مستخدمين إضافيين
```bash
python add_user.py
```
**أو**: انقر على `add_user.bat`

---

### 3. فحص المستخدمين الموجودين
```bash
python check_users.py
```

---

### 4. اختبار تسجيل الدخول
```bash
python test_login.py
```

---

## 🔐 ملفات التفعيل

### 5. توليد مفتاح التفعيل
```bash
python activate_license.py "78BE-1F72-FC34-FAEA"
```
**أو**: انقر على `generate_key.bat`

---

### 6. تطبيق مفتاح التفعيل
```bash
python activate_and_apply.py "4552-D7E7-5638-D72E"
```
**أو**: انقر على `apply_license.bat`

---

## 📚 ملفات التوثيق

| الملف | الموضوع |
|------|--------|
| `QUICK_START.md` | البدء السريع |
| `SETUP_COMPLETE.md` | ملخص الإصلاحات |
| `LICENSE_ACTIVATION_README.md` | نظام التفعيل |
| `USER_AUTHENTICATION_README.md` | نظام المستخدمين |

---

## 🚀 الملفات الرئيسية للتطبيق

| الملف | الوصف |
|------|-------|
| `main.py` | نقطة الإقلاع الرئيسية |
| `requirements.txt` | المكتبات المطلوبة |
| `.env` | بيانات الاتصال بقاعدة البيانات |
| `database_schema.sql` | هيكل قاعدة البيانات |

---

## 📂 هيكل المشروع

```
POS_V2/
├── run.bat                          👈 اضغط هنا للتشغيل السريع!
├── main.py                          👈 تطبيق رئيسي
├── 
├── 🔐 نظام التفعيل
├── activate_license.py
├── activate_and_apply.py
├── generate_key.bat
├── apply_license.bat
├── LICENSE_SYSTEM.ps1
├── LICENSE_ACTIVATION_README.md
├── 
├── 👤 نظام المستخدمين
├── setup_default_user.py
├── add_user.py
├── add_user.bat
├── check_users.py
├── test_login.py
├── USER_AUTHENTICATION_README.md
├── 
├── 📚 التوثيق
├── QUICK_START.md
├── SETUP_COMPLETE.md
├── 
├── 📁 ملفات التطبيق
├── controllers/
├── repositories/
├── services/
├── models/
├── ui/
├── utils/
├── migrations/
├── database_schema.sql
├── .env
└── requirements.txt
```

---

## 🎯 الخطوات الموصى بها

### الخطوة 1: التثبيت الأول
```bash
# 1. تثبيت المكتبات
pip install -r requirements.txt

# 2. إضافة مستخدم إداري (تلقائياً عند التشغيل الأول)
python run.bat
```

### الخطوة 2: التشغيل المنتظم
```bash
python main.py
```

### الخطوة 3: إضافة مستخدمين إضافيين (اختياري)
```bash
python add_user.py "الاسم" "البريد" "كلمة_المرور"
```

---

## 💾 بيانات تسجيل الدخول الافتراضية

```
📧 البريد: admin@hyperpos.com
🔑 كلمة المرور: Admin@123
👑 الدور: مدير نظام (Admin)
```

---

## ⚡ اختصارات مفيدة

| الأمر | الوصف |
|------|-------|
| `python run.bat` | تشغيل التطبيق مع التحقق التلقائي |
| `python main.py` | تشغيل التطبيق مباشرة |
| `python setup_default_user.py` | إضافة مستخدم إداري |
| `python check_users.py` | عرض جميع المستخدمين |
| `python test_login.py` | اختبار تسجيل الدخول |

---

## 🔧 استكشاف المشاكل

### المشكلة: "بيانات الدخول غير صحيحة"
```bash
# الحل:
python setup_default_user.py
python test_login.py
```

### المشكلة: "خطأ في قاعدة البيانات"
```bash
# تأكد من:
# 1. MySQL قيد التشغيل
# 2. بيانات الاتصال صحيحة في .env
```

### المشكلة: "المكتبات غير مثبتة"
```bash
pip install -r requirements.txt
```

---

## 🎊 نصيحة إضافية

للحصول على أفضل أداء:
- ✅ استخدم **`python run.bat`** للتشغيل الأول
- ✅ استخدم **`python main.py`** للتشغيل المنتظم
- ✅ أضف مستخدمين عند الحاجة باستخدام **`add_user.bat`**

---

**تم إعداد التطبيق بنجاح! 🎉**
