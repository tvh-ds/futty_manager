import { writeFileSync } from 'node:fs'

const configured = process.env.VITE_API_URL
const origins = ["'self'"]
if (configured) {
  const url = new URL(configured)
  if (url.protocol !== 'https:' || url.username || url.password)
    throw new Error('Deployed API URL must use HTTPS without credentials.')
  origins.push(url.origin)
}
writeFileSync('dist/staticwebapp.config.json', JSON.stringify({
  navigationFallback: { rewrite: '/index.html', exclude: ['/assets/*', '/*.{ico,png,svg,json}'] },
  globalHeaders: {
    'Content-Security-Policy': `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: https://cdn.pitchapi.dev; connect-src ${origins.join(' ')}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`,
    'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer', 'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  },
}, null, 2))
