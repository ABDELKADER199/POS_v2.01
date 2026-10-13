# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: login.spec.ts >> Login flow >> user can login and reach cashier
- Location: e2e\login.spec.ts:7:7

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected pattern: /\/cashier/
Received string:  "http://localhost:4200/login"
Timeout: 5000ms

Call log:
  - Expect "toHaveURL" with timeout 5000ms
    14 × unexpected value "http://localhost:4200/login"

```

```yaml
- text: تسجيل الدخول البريد الإلكتروني
- textbox "البريد الإلكتروني"
- text: كلمة المرور
- textbox "كلمة المرور"
- button "دخول"
- heading "تسجيل الدخول" [level=2]
- text: البريد الإلكتروني
- textbox
- text: كلمة المرور
- textbox
- button "دخول"
```

# Test source

```ts
  1  | import { expect, test } from '@playwright/test';
  2  | 
  3  | // This test assumes the frontend dev server is running on http://localhost:4200
  4  | // and the backend API is running on http://localhost:8000 with Sanctum configured.
  5  | 
  6  | test.describe('Login flow', () => {
  7  |   test('user can login and reach cashier', async ({ page, request }) => {
  8  |     // Make sure a test user exists via API (adjust endpoint as needed)
  9  |     const apiBase = 'http://localhost:8000';
  10 |     // create or ensure user exists; skip if not available
  11 |     try {
  12 |       await request.post(`${apiBase}/api/test-helpers/create-user`, {
  13 |         data: { email: 'e2e@example.com', password: 'password' }
  14 |       });
  15 |     } catch (e) {
  16 |       // ignore if helper not present
  17 |     }
  18 | 
  19 |     await page.goto('/login');
  20 | 
  21 |       // perform login via fetch in page context (ensures cookies are set in browser)
  22 |       const loginResult = await page.evaluate(async () => {
  23 |         await fetch('/sanctum/csrf-cookie', { credentials: 'include' });
  24 |         const resp = await fetch('/api/login', {
  25 |           method: 'POST',
  26 |           headers: { 'Content-Type': 'application/json' },
  27 |           credentials: 'include',
  28 |           body: JSON.stringify({ email: 'e2e@example.com', password: 'password' })
  29 |         });
  30 |         const json = await resp.json().catch(() => null);
  31 |         return { status: resp.status, body: json };
  32 |       });
  33 |       console.log('page-login', loginResult);
  34 | 
  35 |     // navigate to cashier after successful login (cookies are set)
  36 |     if (loginResult.status === 200) {
  37 |       // reload app so AppComponent.loadUser() runs after cookie is set
  38 |       await page.reload();
  39 |       // debug: confirm /api/me now returns the user
  40 |       const me = await page.evaluate(async () => {
  41 |         const r = await fetch('/api/me', { credentials: 'include' });
  42 |         try { return { status: r.status, body: await r.json() }; } catch(e) { return { status: r.status, body: null }; }
  43 |       });
  44 |       console.log('me after reload', me);
  45 |       await page.goto('/cashier');
  46 |     } else {
  47 |       throw new Error('Login failed: ' + loginResult.body);
  48 |     }
> 49 |     await expect(page).toHaveURL(/\/cashier/);
     |                        ^ Error: expect(page).toHaveURL(expected) failed
  50 |     // check for an element on cashier page
  51 |     await expect(page.locator('app-cashier')).toHaveCount(1);
  52 |   });
  53 | });
  54 | 
```