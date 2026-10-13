import { expect, test } from '@playwright/test';

// This test exercises the Sanctum CSRF flow and then calls a protected API endpoint.
// It requires environment variables PW_EMAIL and PW_PASSWORD to be set for a seeded user.

const email = process.env.PW_EMAIL;
const password = process.env.PW_PASSWORD;

test.describe('API E2E - Auth', () => {
  test('login via csrf cookie then access cashier products', async ({ request }) => {
    test.skip(!email || !password, 'PW_EMAIL and PW_PASSWORD must be set in environment');

    // Acquire CSRF cookie
    const csrf = await request.get('/sanctum/csrf-cookie');
    expect(csrf.ok()).toBeTruthy();

    // Perform login (cookies are stored in the same request context)
    const login = await request.post('/api/login', {
      data: { email, password },
    });
    expect(login.ok()).toBeTruthy();

    // Now call a protected endpoint that requires authentication and permission check
    const products = await request.get('/api/cashier/products');
    expect(products.status()).toBe(200);
  });
});
