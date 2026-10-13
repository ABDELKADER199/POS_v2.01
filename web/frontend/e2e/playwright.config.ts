import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: {
    timeout: 5000,
  },
  use: {
    // API tests will target the backend running locally on port 8000.
    baseURL: 'http://localhost:8000',
    actionTimeout: 0,
    trace: 'on-first-retry',
  },
});
