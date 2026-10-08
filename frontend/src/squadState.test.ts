import { describe, expect, it } from 'vitest'
import { substitute, swapSlots, validateSavedSquad } from './squadState'
import type { Formation, SquadSnapshot } from './api'

const formation = { id: '4-3-3', slots: [{ id: 'GK', role: 'GK' }, { id: 'ST', role: 'ST' }, { id: 'RW', role: 'W' }] } as Formation
const snapshot = { snapshot_id: 'fixture-v1', players: [
  { id: 'keeper', roles: ['GK'] }, { id: 'striker', roles: ['ST'] },
  { id: 'winger', roles: ['W'] }, { id: 'sub', roles: ['ST'] }, { id: 'reserve', roles: ['W'] },
] } as SquadSnapshot
const saved = { schema: 'scout-squad-v1', notes: {}, lineup: { snapshot_id: 'fixture-v1', formation_id: '4-3-3',
  assignments: { GK: 'keeper', ST: 'striker', RW: 'winger' }, bench: ['sub'], role_multiplier: 1.5 } } as const

describe('squad persistence and lineup operations', () => {
  it('copies documented inputs and strips exported scores', () => {
    const parsed = validateSavedSquad({ ...saved, evaluation: { team_rating: 999 } }, snapshot, [formation])
    expect(parsed).toEqual(saved)
    expect(parsed.lineup).not.toBe(saved.lineup)
  })
  it('swaps uniquely and returns outgoing substitute to its bench location', () => {
    const l = validateSavedSquad(saved, snapshot, [formation]).lineup
    expect(swapSlots(l, 'ST', 'RW').assignments).toEqual({ GK: 'keeper', ST: 'winger', RW: 'striker' })
    const next = substitute(l, 'ST', 'sub')
    expect(next.bench).toEqual(['striker'])
    expect(next.assignments.ST).toBe('sub')
    expect(new Set([...Object.values(next.assignments), ...next.bench]).size).toBe(4)
    expect(substitute(l, 'RW', 'reserve').bench).toEqual(['sub'])
    expect(() => substitute(l, 'RW', 'striker')).toThrow()
    expect(() => swapSlots(l, 'bad', 'ST')).toThrow()
  })
  it('rejects stale, corrupt, duplicate, malformed and goalkeeper exchanges', () => {
    const l = validateSavedSquad(saved, snapshot, [formation]).lineup
    const invalid = [null, [], {}, { ...saved, schema: 'bad' }, { ...saved, notes: [] },
      { ...saved, notes: { striker: 'x'.repeat(5001) } }, { ...saved, notes: { unknown: 'unsafe' } },
      ...[{ snapshot_id: 'old' }, { role_multiplier: 1.55 }, { role_multiplier: Infinity },
        { bench: ['striker'] }, { bench: ['unknown'] }, { assignments: { ST: 'striker' } },
        { assignments: { ...l.assignments, RW: 'striker' } }, { assignments: { ...l.assignments, RW: 2 } },
        { assignments: swapSlots(l, 'GK', 'ST').assignments }].map(p => ({ ...saved, lineup: { ...l, ...p } }))]
    invalid.forEach(value => expect(() => validateSavedSquad(value, snapshot, [formation])).toThrow())
  })
})
