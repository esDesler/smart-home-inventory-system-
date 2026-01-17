const { test, expect } = require('@playwright/test');
const { getBaseUrl } = require('./helpers/baseUrl');

test.describe('Smart home inventory UI', () => {
  test('loads the inventory page', async ({ page }) => {
    await page.goto(getBaseUrl(), { waitUntil: 'domcontentloaded' });

    await expect(page.getByTestId('page-title')).toHaveText(
      'Smart Home Inventory'
    );

    const visibleItems = page.locator(
      '[data-testid="inventory-item"]:not([hidden])'
    );
    await expect(visibleItems).toHaveCount(4);
  });

  test('filters inventory items by search term', async ({ page }) => {
    await page.goto(getBaseUrl(), { waitUntil: 'domcontentloaded' });

    const search = page.getByTestId('inventory-search');
    const visibleItems = page.locator(
      '[data-testid="inventory-item"]:not([hidden])'
    );
    const emptyState = page.getByTestId('empty-state');

    await expect(visibleItems).toHaveCount(4);
    await search.fill('sensor');

    await expect(visibleItems).toHaveCount(2);
    await expect(emptyState).toBeHidden();

    await search.fill('nonexistent');
    await expect(visibleItems).toHaveCount(0);
    await expect(emptyState).toBeVisible();
  });
});
