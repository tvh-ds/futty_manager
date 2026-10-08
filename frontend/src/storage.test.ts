import { describe, expect, it } from 'vitest'
import { validateSaved } from './storage'

describe('local evidence import boundary', () => {
  it('accepts an evidence export and deduplicates identifiers', () => {
    expect(validateSaved({ saved: { watchlist: ['p1', 'p1'], notes: { p1: 'Verify pressure receiving' } } }))
      .toEqual({ watchlist: ['p1'], notes: { p1: 'Verify pressure receiving' } })
  })
  const invalid: unknown[] = [null, [], { watchlist: ['../p1'], notes: {} },
    { watchlist: [], notes: { constructor: 'unsafe key' } },
    { watchlist: [], notes: { p1: 'x'.repeat(5001) } },
    { saved: null }, { saved: 42 }, { watchlist: [], notes: [] }]
  it('rejects unsupported imports', () => {
    invalid.forEach(value => expect(() => validateSaved(value)).toThrow())
  })
})
