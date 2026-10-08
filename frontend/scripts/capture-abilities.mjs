import { chromium } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
const directory = new URL('../../.impeccable/review/', import.meta.url)
await mkdir(directory, { recursive: true })
const browser = await chromium.launch()
try {
  for (const [name, width, height] of [['desktop',1440,1000],['mobile',390,844],['user-700',700,704]]) {
    const context = await browser.newContext({viewport:{width,height}, reducedMotion:'reduce'})
    const page = await context.newPage()
    // Contract fixture for an eligible archetype lacking a calibrated cohort.
    // Broad ST and the normal captures retain the API's current demo response.
    await page.route('**/players/lfc-alexander-isak/abilities', async route => {
      const response = await route.fetch()
      const body = await response.json()
      const role = body.roles.find(r => r.role_id === 'false-nine')
      Object.assign(role, {rating: null, rating_unclipped: null, role_z: null, percentile: null, population_size: 0, rank: null})
      for (const ability of role.abilities) {
        Object.assign(ability, {raw: null, z: null, rating: null, rating_unclipped: null, percentile: null})
        for (const feature of ability.features) Object.assign(feature, {peer_count: 0, peer_mean: null, z: null, percentile: null, stabilized_value: null, reliability: null, density: [], quantiles: []})
      }
      await route.fulfill({response, json: body})
    })
    await page.goto('http://127.0.0.1:5173/')
    await page.locator('.ss-summary[aria-busy=false]').waitFor()
    await page.getByRole('button',{name:/^Select Alexander Isak,/}).click()
    await page.getByRole('button',{name:'Details',exact:true}).click()
    await page.getByLabel('Evaluation role').waitFor()
    await page.evaluate(() => document.fonts.ready)
    const path = suffix => new URL(`${name}-abilities${suffix}.png`,directory).pathname.replace(/^\/([A-Z]:)/,'$1')
    await page.screenshot({path:path('')})
    await page.getByLabel('Compare one striker').selectOption('lfc-hugo-ekitike')
    await page.locator('.av-comparison-polygon').waitFor()
    await page.locator('.av-radar').scrollIntoViewIfNeeded()
    await page.screenshot({path:path('-radar')})
    await page.getByRole('button', {name:'Inspect Non-penalty goals evidence',exact:true}).click()
    await page.locator('.av-evidence-panel').first().scrollIntoViewIfNeeded()
    await page.screenshot({path:path('-distribution')})
    await page.getByLabel('Compare one striker').selectOption('')
    await page.getByLabel('Evaluation role').selectOption('false-nine')
    await page.locator('.av-radar').scrollIntoViewIfNeeded()
    await page.screenshot({path:path('-unrated')})
    if(await page.getByRole('dialog').evaluate(el=>el.scrollWidth > el.clientWidth)) throw new Error(`Dialog overflow at ${width}`)
    await context.close()
  }
} finally {await browser.close()}
