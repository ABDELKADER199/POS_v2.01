## 🚀 طريقة الاستخدام السريعة

### 1️⃣ إعداد قاعدة البيانات والمستخدمين

```bash
# إضافة مستخدم إداري افتراضي
python setup_default_user.py
```

بيانات الدخول الافتراضية:
- 📧 البريد: `admin@hyperpos.com`
- 🔑 كلمة المرور: `Admin@123`

### 2️⃣ تفعيل التطبيق

```bash
# توليد مفتاح التفعيل من السريال
python activate_license.py "78BE-1F72-FC34-FAEA"
# سيعطيك المفتاح: 4552-D7E7-5638-D72E

# تطبيق المفتاح
python activate_and_apply.py "4552-D7E7-5638-D72E"
```

### 3️⃣ تشغيل البرنامج

```bash
python main.py
```

---

## 🎯 ملفات مهمة

| الملف | الوصف | الاستخدام |
|------|-------|---------|
| `setup_default_user.py` | إضافة مستخدم إداري | `python setup_default_user.py` |
| `add_user.py` / `add_user.bat` | إضافة مستخدمين جدد | `python add_user.py` أو انقر `add_user.bat` |
| `check_users.py` | عرض المستخدمين | `python check_users.py` |
| `activate_license.py` | توليد مفاتيح التفعيل | `python activate_license.py` أو انقر `generate_key.bat` |
| `activate_and_apply.py` | تطبيق التفعيل | `python activate_and_apply.py` أو انقر `apply_license.bat` |

---

## 📁 ملفات النظام

| الملف | النوع | الوصف |
|------|------|-------|
| `activate_license.py` | Python Script | مولد مفاتيح التفعيل |
| `activate_and_apply.py` | Python Script | تطبيق التفعيل |
| `generate_key.bat` | Batch File | واجهة سهلة لتوليد المفتاح |
| `apply_license.bat` | Batch File | واجهة سهلة لتطبيق المفتاح |
| `License_System.ps1` | PowerShell Script | نظام تفاعلي كامل |
| `LICENSE_ACTIVATION_README.md` | Documentation | التوثيق الكامل |

---

## ✅ التحقق من التفعيل

بعد التفعيل، يمكنك التأكد من نجاحه:
```bash
python main.py
```

إذا لم تظهر شاشة التفعيل، فقد تم التفعيل بنجاح! ✨
