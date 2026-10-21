import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: 'tests', testMatch: '**/*.e2e.ts', fullyParallel: false,
  workers: 1, timeout: 30000, use: { browserName: 'chromium', channel: process.env.AIEK_BROWSER_CHANNEL, trace: 'retain-on-failure' },
  reporter: 'list', outputDir: 'test-results',
});
