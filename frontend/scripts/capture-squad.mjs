import { chromium } from '@playwright/test'
import { mkdir } from 'node:fs/promises'

const directory = new URL('../../.impeccable/review/', import.meta.url)
await mkdir(directory, { recursive: true })
const browser = await chromium.launch()
try {
  for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844], ['user-700', 700, 704]]) {
    const context = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce' })
    const page = await context.newPage()
    await page.goto('http://127.0.0.1:5173/')
    await page.locator('.ss-summary[aria-busy="false"]').waitFor()
    await page.evaluate(() => document.fonts.ready)
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error(`Overflow at ${width}`)
    await page.screenshot({ path: new URL(`${name}.png`, directory).pathname.replace(/^\/([A-Z]:)/, '$1'), fullPage: true })
    if (name !== 'user-700') {
      await page.getByRole('button', { name: /^Select Alexander Isak,/ }).click()
      await page.getByRole('button', { name: 'Substitute', exact: true }).click()
      await page.getByRole('button', { name: 'Preview Hugo Ekitike', exact: true }).click()
      await page.getByRole('button', { name: 'Confirm substitution' }).waitFor()
      await page.locator('.ss-sub-preview[aria-busy="false"]').waitFor()
      await page.screenshot({ path: new URL(`${name}-bench.png`, directory).pathname.replace(/^\/([A-Z]:)/, '$1') })
      await page.getByLabel('Close bench').click()
      await page.getByRole('button', { name: 'Details', exact: true }).click()
      await page.getByRole('dialog').waitFor()
      await page.screenshot({ path: new URL(`${name}-details.png`, directory).pathname.replace(/^\/([A-Z]:)/, '$1') })
    }
    await context.close()
  }
} finally { await browser.close() }
