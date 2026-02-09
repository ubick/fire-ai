import { test, expect } from '@playwright/test';

test.describe('FIRE AI Dashboard', () => {
    test('should display welcome message on dashboard', async ({ page }) => {
        // Navigate to the dashboard
        await page.goto('/');

        // Wait for the welcome message to be visible
        const welcomeHeading = page.getByRole('heading', { name: 'Welcome to FIRE AI' });
        await expect(welcomeHeading).toBeVisible({ timeout: 10000 });

        // Verify the subtitle is also present
        await expect(page.getByText('Your financial independence journey starts here')).toBeVisible();
    });

    test('should display dashboard metrics', async ({ page }) => {
        await page.goto('/');

        // Wait for either the welcome text or the fetch button
        await expect(page.getByText(/Welcome to FIRE AI/i)).toBeVisible();

        const fetchButton = page.getByRole('button', { name: /Fetch from Google Sheets/i });
        const statsCard = page.getByText('Total Spend (12m)');

        // If fetch button is there, click it. Otherwise, we might already have data.
        if (await fetchButton.isVisible()) {
            await fetchButton.click();
        }

        // Wait for stats cards to load
        await expect(statsCard).toBeVisible({ timeout: 20000 });

        // Check if YoY text is visible
        await expect(page.getByText(/YoY/)).toBeVisible();
    });

    test('should have working sidebar navigation', async ({ page }) => {
        await page.goto('/');

        await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
        await expect(page.getByRole('link', { name: 'Import' })).toBeVisible();
        await expect(page.getByRole('link', { name: 'Budget' })).toBeVisible();

        await page.getByRole('link', { name: 'Import' }).click();
        await expect(page.getByRole('heading', { name: 'Import Transactions' })).toBeVisible();
    });

    test('should perform a shadow import flow', async ({ page }) => {
        await page.goto('/import');

        // 1. Select a file (should be pre-selected or we select one)
        const fileSelect = page.locator('select').first();
        await fileSelect.waitFor();

        // 2. Select a month (Auto is default)

        // 3. Click Shadow Mode
        await page.getByRole('button', { name: /Shadow Mode/i }).click();

        // 4. Wait for results
        await expect(page.getByText('Shadow mode preview')).toBeVisible({ timeout: 20000 });

        // 5. Check if table appears
        await expect(page.locator('table')).toBeVisible();
        await expect(page.getByText('Totals')).toBeVisible();
    });
});

test.describe('Budget Page', () => {
    test('should load and allow saving budgets', async ({ page }) => {
        await page.goto('/budget');

        await expect(page.getByRole('heading', { name: 'Budget Manager' })).toBeVisible();

        // Save Changes button should be visible (but disabled if no changes)
        const saveButton = page.getByRole('button', { name: /Save Changes/i });
        await expect(saveButton).toBeVisible();

        // Check if categories load from mock
        await expect(page.getByText('Groceries')).toBeVisible({ timeout: 10000 });
    });
});

test.describe('API Health Check', () => {
    test('API server should be running', async ({ request }) => {
        const response = await request.get('http://localhost:8000/api/health');
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.status).toBe('ok');
    });

    test('API should list CSV files', async ({ request }) => {
        const response = await request.get('http://localhost:8000/api/csv-files');
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data).toHaveProperty('files');
        expect(Array.isArray(data.files)).toBeTruthy();
    });
});
