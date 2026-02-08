import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',
    use: {
        baseURL: 'http://localhost:3000',
        trace: 'on-first-retry',
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
    webServer: [
        {
            command: '../.venv/bin/python ../api/server.py',
            url: 'http://localhost:8000/api/health',
            reuseExistingServer: !process.env.CI,
            timeout: 30000,
        },
        {
            command: 'npm run dev',
            url: 'http://localhost:3000',
            reuseExistingServer: !process.env.CI,
            timeout: 60000,
            env: {
                PATH: `/opt/homebrew/opt/node@24/bin:${process.env.PATH}`,
            },
        },
    ],
});
