Playwright E2E (API-focused)

Prerequisites:
- Backend running locally on http://localhost:8000 with seeded user credentials.
- Set environment variables `PW_EMAIL` and `PW_PASSWORD` to the test user's credentials (e.g., admin@example.com / password).

Install Playwright browsers and run tests:

```bash
cd web/frontend
npm ci
npm run e2e:install
npm run e2e
```

Notes:
- This test uses API requests to validate the Sanctum CSRF flow and protected endpoint access, avoiding fragile UI selectors.
- To integrate in CI, ensure the backend is started and reachable, and provide credentials via secrets.
