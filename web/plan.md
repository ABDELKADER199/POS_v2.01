خطة تنفيذية مُختصرة (أولوية: تسجيل الدخول، صلاحيات، صفحة الكاشير)

1) إعداد المشروع
- Scaffold Laravel backend و Angular frontend (أوامر موجودة في README).

2) المصادقة والصلاحيات
- Laravel: Sanctum للمصادقة، Spatie للـ roles & permissions.
- API endpoints: `POST /api/login`, `POST /api/logout`, `GET /api/me`, `GET /api/permissions`.

3) طبقة الـ Use Cases (معمارية نظيفة)
- فصل منطقي: Controllers -> DTOs -> UseCases (Services) -> Repositories -> Models.
- إنشاء `app/UseCases/Cashier/*` لعمليات البيع، إنشاء فاتورة، دفع، وخزن الجلسة.

4) الواجهة (Angular)
- AuthService + JWT interceptor أو تكامل Sanctum.
- Route Guards للـ roles/permissions.
- CashierComponent: واجهة سريعة لاختيار منتجات، إضافة للسلة، حساب ودفع.

5) اختبارات وأمن
- Backend: Feature tests (PHPUnit) للمصادقة وauthorization والـ cashier flows.
- Frontend: Unit tests و e2e بسيطة (Playwright/Protractor).
- إعداد CORS، rate limiting، input validation، واختبارات أمان (OWASP basics).

6) CI/CD و مستندات التشغيل
- ملف `.github/workflows/ci.yml` لتشغيل اختبارات و lint.

مخرجات متوقعة للمرحلة الأولى (أسبوع عمل تقريبي): API للمصادقة + واجهة تسجيل دخول، وحالة مستخدم مع صلاحيات، وصفحة كاشير بسيطة.
