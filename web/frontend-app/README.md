دليل سريع لإنشاء واجهة Angular وربط مكونات مصممة مسبقاً

الخطوات لإنشاء مشروع Angular جديد ثم استخدام المكونات في `frontend-app/src/app/`:

1) تثبيت Angular CLI (إن لم يكن مثبتاً):
```bash
npm install -g @angular/cli
```

2) إنشاء مشروع جديد داخل workspace (مثال):
```bash
cd "d:/Python Desktop/POS_V2/web"
ng new frontend --routing --style=scss
cd frontend
```

3) انسخ ملفات المجلد `frontend-app/src/app/` من هذا المستودع إلى `frontend/src/app/` (استبدال أو دمج حسب الحاجة).

4) ثبت الحزم الموصى بها:
```bash
npm install @angular/material @auth0/angular-jwt
```

5) إعداد proxy إلى backend (اختياري) عن طريق إنشاء `proxy.conf.json` في `frontend/`:
```json
{
  "/api": {
    "target": "http://localhost:8000",
    "secure": false,
    "changeOrigin": true
  }
}
```

ثم تشغيل التطوير:
```bash
ng serve --proxy-config proxy.conf.json
```

ملاحظة: المكونات هنا تعتمد على وجود API endpoints: `POST /api/login`, `POST /api/logout`, `GET /api/me`.
