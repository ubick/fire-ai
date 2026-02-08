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

    test('should have working sidebar navigation', async ({ page }) => {
        await page.goto('/');

        // Check sidebar has Dashboard and Import links
        await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
        await expect(page.getByRole('link', { name: 'Import' })).toBeVisible();

        // Click on Import link
        await page.getByRole('link', { name: 'Import' }).click();

        // Verify we're on the import page
        await expect(page.getByRole('heading', { name: 'Import Transactions' })).toBeVisible();
    });

    test('should display import page controls', async ({ page }) => {
        await page.goto('/import');

        // Wait for page to load
        await expect(page.getByRole('heading', { name: 'Import Transactions' })).toBeVisible();

        // Check for action buttons (main functionality)
        await expect(page.getByRole('button', { name: /Shadow Mode/i })).toBeVisible();
        await expect(page.getByRole('button', { name: /Live Import/i })).toBeVisible();
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
