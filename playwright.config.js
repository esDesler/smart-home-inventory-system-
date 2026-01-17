const { defineConfig, devices } = require('@playwright/test');

const wsEndpoint = process.env.PLAYWRIGHT_MCP_WS_ENDPOINT;
const useConfig = {
  ...devices['Desktop Chrome'],
  baseURL: process.env.BASE_URL,
  screenshot: 'only-on-failure',
  trace: 'on-first-retry',
  video: 'retain-on-failure',
};

if (wsEndpoint) {
  useConfig.connectOptions = { wsEndpoint };
}

module.exports = defineConfig({
  testDir: './tests/ui',
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: [['list']],
  outputDir: 'test-results',
  use: useConfig,
});
