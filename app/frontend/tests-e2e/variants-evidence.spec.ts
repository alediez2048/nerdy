import { test, expect } from '@playwright/test'

test.describe('variants Evidence panel (PI-08)', () => {
  test.fixme('renders 8 dimensions with rationales for a v2 MediaEvaluation', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('evidence-panel')).toBeVisible()
  })

  test.fixme('shows legacy badge for sessions with pre-PI scoring', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(/legacy scoring/i)).toBeVisible()
  })
})
