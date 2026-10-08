import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'

async function settled(page: import('@playwright/test').Page) {
  await expect(page.locator('.ss-summary')).toHaveAttribute('aria-busy', 'false')
  await expect(page.locator('.ss-position')).toHaveCount(11)
}

test('formation, details, substitutions, undo, export/import and Explore', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto('/'); await settled(page)
  const key = await page.evaluate(() => Object.keys(localStorage).find(k => k.startsWith('scout.lineup.v1:'))!)
  const before = JSON.parse(await page.evaluate(k => localStorage.getItem(k)!, key))
  await page.getByLabel('Formation', { exact: true }).selectOption('4-2-3-1'); await settled(page)
  const after = JSON.parse(await page.evaluate(k => localStorage.getItem(k)!, key))
  expect(Object.values(after.lineup.assignments).sort()).toEqual(Object.values(before.lineup.assignments).sort())
  await page.getByRole('button', { name: /^Details for Virgil van Dijk,/ }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Provisional position metrics', exact: true })).toBeVisible()
  await expect(page.locator('.ss-skill')).not.toHaveCount(0)
  await page.getByLabel('Scouting notes', { exact: true }).fill('Verify receiving under pressure.')
  await page.getByLabel('Close drawer').click()
  await page.getByRole('button', { name: /^Details for Alexander Isak,/ }).click()
  await page.getByLabel('Close drawer').click()
  await page.getByRole('button', { name: 'Substitute Alexander Isak', exact: true }).click()
  await page.getByRole('button', { name: 'Preview Hugo Ekitike', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Confirm substitution' })).toBeEnabled()
  await expect(page.getByText('XI change:', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Cancel preview' }).click()
  await expect(page.getByRole('button', { name: 'Confirm substitution' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Preview Hugo Ekitike', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Confirm substitution' })).toBeEnabled()
  await page.getByRole('button', { name: 'Confirm substitution' }).click(); await settled(page)
  await expect(page.locator('.ss-position').getByText('Ekitike', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Undo', exact: true }).click(); await settled(page)
  await expect(page.locator('.ss-position').getByText('Isak', { exact: true })).toBeVisible()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export', exact: true }).click()
  const download = await downloadPromise
  const exported = JSON.parse(await readFile((await download.path())!, 'utf8'))
  expect(exported.provenance.attribute_evidence).toBe('synthetic')
  expect(exported.provenance.squad_snapshot).toBe(before.lineup.snapshot_id)
  expect(exported.notes['lfc-virgil-van-dijk']).toContain('pressure')
  await page.getByLabel('Import lineup JSON').setInputFiles({ name: 'backup.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(exported)) })
  await expect(page.getByText('Validated lineup imported.', { exact: true })).toBeVisible()
  await page.reload(); await settled(page)
  await expect(page.getByLabel('Formation', { exact: true })).toHaveValue('4-2-3-1')
  await page.getByRole('button', { name: /^Details for Virgil van Dijk,/ }).focus()
  await page.getByRole('link', { name: 'Explore role candidates for Virgil van Dijk' }).click()
  await expect(page).toHaveURL(/\/scout\?role=CB&from=squad/)
  await expect(page.getByText('Actual Liverpool profile matching is unavailable;', { exact: false })).toBeVisible()
  await expect(page.getByLabel('Role family', { exact: true })).toHaveValue('CB')
  expect(errors).toEqual([])
})

test('keyboard swap, goalkeeper restriction, chemistry and reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' }); await page.goto('/'); await settled(page)
  const select = page.getByRole('button', { name: 'Substitute Virgil van Dijk', exact: true })
  await page.getByRole('button', { name: /^Details for Virgil van Dijk,/ }).focus()
  await select.focus(); await page.keyboard.press('Enter')
  const swap = page.getByRole('button', { name: 'Swap position', exact: true })
  await swap.focus(); await page.keyboard.press('Enter')
  const target = page.getByRole('button', { name: /^Swap with Ronald Araujo,/ })
  await target.focus(); await page.keyboard.press('Enter'); await settled(page)
  await expect(page.locator('[data-slot=LCB]').getByText('Araujo', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Undo', exact: true }).click(); await settled(page)
  await page.getByRole('button', { name: /^Details for Alisson Becker,/ }).focus()
  await page.getByRole('button', { name: 'Substitute Alisson Becker', exact: true }).focus()
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: 'Swap position', exact: true }).focus()
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: /^Swap with Alexander Isak,/ }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Goalkeepers and outfield players cannot exchange slots', { exact: true })).toBeVisible()
  await page.keyboard.press('Escape')
  const link = page.getByRole('button', { name: /^Chemistry / }).first()
  await link.focus(); await page.keyboard.press('Enter')
  await expect(page.getByRole('dialog', { name: 'Chemistry — familiarity proxy' })).toBeVisible()
  await expect(page.getByText('Shared competitive minutes', { exact: true })).toBeVisible()
  await page.keyboard.press('Escape')
  expect(await page.locator('.ss-position').first().evaluate(el => getComputedStyle(el).transitionDuration)).toBe('0s')
})

test('corrupt storage and service failure preserve recovery actions', async ({ page }) => {
  const key = 'scout.lineup.v1:liverpool-men-2026-27-20261006-v1'
  await page.addInitScript(k => localStorage.setItem(k, '{broken-original'), key)
  await page.goto('/'); await settled(page)
  await expect(page.getByText('Saved lineup could not be read.', { exact: false })).toBeVisible()
  expect(await page.evaluate(k => localStorage.getItem(k), key)).toBe('{broken-original')
  await page.getByLabel('Import lineup JSON').setInputFiles({ name: 'bad.json', mimeType: 'application/json', buffer: Buffer.from('{"schema":"bad"}') })
  await expect(page.getByText('Import rejected:', { exact: false })).toBeVisible()
  expect(await page.evaluate(k => localStorage.getItem(k), key)).toBe('{broken-original')
  await page.route('**/api/squads/liverpool-men', r => r.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"Temporarily unavailable"}' }))
  await page.reload()
  await expect(page.getByRole('button', { name: 'Retry connection' })).toBeVisible()
})

test('out-of-order evaluation is never displayed as current', async ({ page }) => {
  await page.goto('/'); await settled(page)
  let unblock!: () => void, finished!: () => void
  const hold = new Promise<void>(resolve => { unblock = resolve })
  const done = new Promise<void>(resolve => { finished = resolve })
  await page.route('**/api/squads/liverpool-men/evaluate', async route => {
    const older = route.request().postDataJSON().formation_id === '4-2-3-1'
    if (older) await hold
    const response = await route.fetch()
    await route.fulfill({ response })
    if (older) finished()
  })
  await page.getByLabel('Formation', { exact: true }).selectOption('4-2-3-1')
  await expect(page.locator('.ss-summary')).toHaveAttribute('aria-busy', 'true')
  await expect(page.getByLabel('Formation', { exact: true })).toBeEnabled()
  await page.getByLabel('Formation', { exact: true }).selectOption('4-4-2'); await settled(page)
  const currentScore = await page.locator('.ss-summary').textContent() || ''
  unblock(); await done
  await expect(page.getByLabel('Formation', { exact: true })).toHaveValue('4-4-2')
  await expect(page.locator('.ss-summary')).toHaveAttribute('aria-busy', 'false')
  await expect(page.locator('.ss-summary')).toHaveText(currentScore)
})

test('pointer drag swaps pitch players and dropping a bench player previews first', async ({ page }, info) => {
  test.skip(info.project.name === 'mobile', 'Mobile substitution uses tap; pointer drag tested on desktop')
  await page.goto('/'); await settled(page)
  async function drag(from: import('@playwright/test').Locator, to: import('@playwright/test').Locator) {
    await from.scrollIntoViewIfNeeded()
    await to.scrollIntoViewIfNeeded()
    const a = (await from.boundingBox())!, b = (await to.boundingBox())!
    await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2)
    await page.mouse.down(); await page.waitForTimeout(220); await page.mouse.move(a.x + a.width / 2 + 12, a.y + a.height / 2, { steps: 5 })
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 20 }); await page.mouse.up()
  }
  await drag(page.getByLabel('Move Virgil van Dijk', { exact: true }), page.locator('[data-slot=RCB]'))
  await settled(page)
  await expect(page.locator('[data-slot=RCB]').getByText('Van Dijk', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Show bench', exact: false }).click()
  const handle = page.getByLabel('Move Cody Gakpo', { exact: true })
  await handle.scrollIntoViewIfNeeded()
  const a = (await handle.boundingBox())!
  await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2); await page.mouse.down()
  await page.mouse.move(a.x + a.width / 2 + 12, a.y + a.height / 2, { steps: 5 })
  // The bottom drawer covers the lower pitch; use its visible striker slot.
  const target = (await page.locator('[data-slot=ST]').boundingBox())!
  await page.mouse.move(target.x + target.width / 2, target.y + target.height / 2, { steps: 20 }); await page.mouse.up()
  await expect(page.getByRole('button', { name: 'Confirm substitution' })).toBeEnabled()
  await expect(page.locator('[data-slot=ST]').getByText('Isak', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Confirm substitution' }).click(); await settled(page)
  await expect(page.locator('[data-slot=ST]').getByText('Gakpo', { exact: true })).toBeVisible()
})
