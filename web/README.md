مرحباً — دليل بدء سريع لمشروع الويب (Laravel API + Angular)

الغرض: تحويل تطبيق POS الموجود إلى نسخة ويب مع الحفاظ على معمارية نظيفة، تسجيل دخول مع Sanctum وصلاحيات عبر Spatie، وواجهة Angular مع صفحة كاشير.

Backend (Laravel API) — خطوات سريعة:

1) إنشاء مشروع Laravel:
```bash
composer create-project laravel/laravel backend
cd backend
```

2) تثبيت الحزم المطلوبة:
```bash
composer require laravel/sanctum
composer require spatie/laravel-permission
```

3) نشر وضبط الحزم:
```bash
php artisan vendor:publish --provider="Laravel\Sanctum\SanctumServiceProvider"
php artisan vendor:publish --provider="Spatie\Permission\PermissionServiceProvider"
php artisan migrate
```
- أضف `\Laravel\Sanctum\Http\Middleware\EnsureFrontendRequestsAreStateful::class` إذا استخدمت SPA sessions.

4) نماذج مبدئية: سأضع مقتطفات للـ API (تسجيل دخول، خروج، معلومات المستخدم، صلاحيات) في `web/backend-snippets`.

Frontend (Angular) — خطوات سريعة:

1) إنشاء مشروع Angular:
```bash
npx @angular/cli new frontend --routing --style=scss
cd frontend
ng add @angular/material
npm install @auth0/angular-jwt
```

2) بنية مبدئية:
- `src/app/auth/` : خدمات تسجيل الدخول و guards
- `src/app/cashier/` : صفحة الكاشير (POS UI)

3) التكامل مع API: استخدم HttpClient مع `Authorization: Bearer <token>` أو سانكتوم مع تهيئة CORS و credentials.

ملفات/مقتطفات إضافية: راجع `web/backend-snippets` و `web/frontend-snippets`.

الخطة التالية: تنفيذ endpoints أساسيّة (login, logout, me, permissions) ثم واجهة تسجيل الدخول وحماية Routes وبدء صفحة الكاشير.
