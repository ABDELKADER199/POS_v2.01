import { expect, test } from '@playwright/test';

// This test assumes the frontend dev server is running on http://localhost:4200
// and the backend API is running on http://localhost:8000 with Sanctum configured.

test.describe('Login flow', () => {
  test('user can login and reach cashier', async ({ page, request }) => {
    // Make sure a test user exists via API (adjust endpoint as needed)
    const apiBase = 'http://localhost:8000';
    // create or ensure user exists; skip if not available
    try {
      await request.post(`${apiBase}/api/test-helpers/create-user`, {
        data: { email: 'e2e@example.com', password: 'password' }
      });
    } catch (e) {
      // ignore if helper not present
    }

    await page.goto('/login');

      // perform login via fetch in page context (ensures cookies are set in browser)
      const loginResult = await page.evaluate(async () => {
        await fetch('/sanctum/csrf-cookie', { credentials: 'include' });
        const resp = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ email: 'e2e@example.com', password: 'password' })
        });
        const json = await resp.json().catch(() => null);
        return { status: resp.status, body: json };
      });
      console.log('page-login', loginResult);

    // navigate to cashier after successful login (cookies are set)
    if (loginResult.status === 200) {
      // reload app so AppComponent.loadUser() runs after cookie is set
      await page.reload();
      // debug: confirm /api/me now returns the user
      const me = await page.evaluate(async () => {
        const r = await fetch('/api/me', { credentials: 'include' });
        try { return { status: r.status, body: await r.json() }; } catch(e) { return { status: r.status, body: null }; }
      });
      console.log('me after reload', me);
      await page.goto('/cashier');
    } else {
      throw new Error('Login failed: ' + loginResult.body);
    }
    await expect(page).toHaveURL(/\/cashier/);
    // check for an element on cashier page
    await expect(page.locator('app-cashier')).toHaveCount(1);
  });
});
