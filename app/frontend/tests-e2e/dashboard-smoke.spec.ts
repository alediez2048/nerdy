import { test, expect } from '@playwright/test'

test.describe('dashboard smoke', () => {
  test('app shell renders without console errors', async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })

    await page.goto('/')
    await expect(page).toHaveTitle(/.+/)
    await expect(page.locator('#root')).toBeVisible()
    expect(consoleErrors, consoleErrors.join('\n')).toEqual([])
  })
})
