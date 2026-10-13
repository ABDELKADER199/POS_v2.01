Playwright E2E

Prerequisites:
- Frontend dev server: `npm start` (http://localhost:4200)
- Backend API: running on http://localhost:8000 with Sanctum enabled

Install browsers and run tests:

```bash
cd web/frontend
npm ci
npm run e2e:install
npm run e2e
```

Notes:
- The test attempts to call a helper endpoint `/api/test-helpers/create-user` to create a test user; implement this endpoint in the backend for faster runs, or pre-create the user manually.
- Adjust selectors in `e2e/login.spec.ts` to match your login/cashier markup.
