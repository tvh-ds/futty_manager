import { describe, expect, it, vi } from 'vitest'
import { LineupPlanner, type PlanningAdapters } from './lineupPlanner'
import type { Evaluation, Formation, Lineup, SquadSnapshot } from './api'

const formation = { id: '4-3-3', slots: [{ id: 'GK', role: 'GK' }, { id: 'ST', role: 'ST' }, { id: 'RW', role: 'W' }] } as Formation
const alternative = { ...formation, id: '4-4-2' }
const lineup = { snapshot_id: 'fixture-v1', formation_id: '4-3-3', assignments: { GK: 'keeper', ST: 'striker', RW: 'winger' },
  bench: ['sub'], role_multiplier: 1.5 } as Lineup
const snapshot = { snapshot_id: 'fixture-v1', default_lineup: lineup, players: [
  { id: 'keeper', roles: ['GK'] }, { id: 'striker', roles: ['ST'] },
  { id: 'winger', roles: ['W'] }, { id: 'sub', roles: ['ST'] },
] } as SquadSnapshot
const result = (lineup: Lineup) => ({ lineup, team_rating: 60 }) as Evaluation
const file = (lineup: Lineup) => ({ size: 200, text: async () => JSON.stringify({ schema: 'scout-squad-v1', lineup, notes: {} }) })
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}
function setup(raw: string | null = null, overrides: Partial<PlanningAdapters> = {}) {
  const storage = { getItem: vi.fn(() => raw), setItem: vi.fn((_key: string, value: string) => { raw = value }) }
  const adapters = { storage, formation: vi.fn(async (l: Lineup, id: string) => ({ ...l, formation_id: id })),
    evaluate: vi.fn(async (l: Lineup) => result(l)), preserve: vi.fn(), ...overrides }
  return { planner: new LineupPlanner(snapshot, [formation, alternative], adapters), adapters, storage }
}

describe('lineup planning interface', () => {
  it('commits unique substitutions, undo, notes and persistence together', () => {
    const { planner, storage } = setup()
    planner.commit(planner.preview('ST', 'sub'))
    expect(planner.getSnapshot().saved.lineup.bench).toEqual(['striker'])
    planner.setNote('striker', 'Keep this note')
    planner.undo()
    expect(planner.getSnapshot().saved.lineup).toEqual(lineup)
    expect(planner.getSnapshot().saved.notes.striker).toBe('Keep this note')
    expect(JSON.parse(storage.setItem.mock.lastCall![1]).lineup).toEqual(lineup)
    expect(() => planner.swap('GK', 'ST')).toThrow('Goalkeepers')
    expect(() => planner.commit({ ...lineup, bench: ['striker'] })).toThrow('duplicate')
    expect(planner.getSnapshot().history).toHaveLength(0)
  })
  it('preserves corrupted storage through edits and rejected imports until explicit recovery', async () => {
    const { planner, storage, adapters } = setup('{original-corrupt')
    planner.persist(); planner.swap('ST', 'RW')
    expect(storage.setItem).not.toHaveBeenCalled()
    expect(await planner.importFile({ size: 4, text: async () => '{bad' })).toBe(false)
    expect(storage.setItem).not.toHaveBeenCalled()
    expect(await planner.importFile(file(lineup))).toBe(true)
    expect(adapters.preserve).toHaveBeenCalledWith('{original-corrupt')
    expect(planner.getSnapshot().storageWritable).toBe(true)
    expect(storage.setItem).toHaveBeenCalled()
  })
  it('keeps exportable state when persistence fails and supports recovery', () => {
    const { planner, storage } = setup()
    storage.setItem.mockImplementationOnce(() => { throw Error('unavailable') })
    planner.swap('ST', 'RW')
    expect(planner.getSnapshot().saved.lineup.assignments.ST).toBe('winger')
    expect(planner.getSnapshot().storageWritable).toBe(false)
    planner.recoverStorage()
    expect(planner.getSnapshot().storageWritable).toBe(true)
  })
  it('rejects formation and import results started before a newer edit', async () => {
    const formationResponse = deferred<Lineup>(), evaluation = deferred<Evaluation>()
    const { planner } = setup(null, { formation: () => formationResponse.promise, evaluate: () => evaluation.promise })
    const changing = planner.changeFormation('4-4-2')
    planner.swap('ST', 'RW')
    formationResponse.resolve({ ...lineup, formation_id: '4-4-2' })
    expect(await changing).toBe(false)
    expect(planner.getSnapshot().saved.lineup.formation_id).toBe('4-3-3')
    const importing = planner.importFile(file(lineup))
    await Promise.resolve(); planner.setNote('striker', 'New edit')
    evaluation.resolve(result(lineup))
    expect(await importing).toBe(false)
    expect(planner.getSnapshot().saved.notes.striker).toBe('New edit')
  })
  it('only the latest async operation can commit, even at the same revision', async () => {
    const first = deferred<Lineup>(), second = deferred<Lineup>()
    const { planner } = setup(null, { formation: vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise) })
    const a = planner.changeFormation('4-4-2'), b = planner.changeFormation('4-3-3')
    second.resolve(lineup); expect(await b).toBe(true)
    first.resolve({ ...lineup, formation_id: '4-4-2' }); expect(await a).toBe(false)
    expect(planner.getSnapshot().saved.lineup).toEqual(lineup)
    expect(planner.getSnapshot().changing).toBe(false)
  })
  it('accepts reordered response keys but never displays a stale or different snapshot evaluation', () => {
    const { planner } = setup()
    const reordered = { ...lineup, assignments: { RW: 'winger', GK: 'keeper', ST: 'striker' } }
    expect(planner.evaluationFor(result(reordered))).toBeTruthy()
    planner.swap('ST', 'RW')
    expect(planner.evaluationFor(result(lineup))).toBeUndefined()
    expect(planner.evaluationFor(result({ ...lineup, snapshot_id: 'old' }))).toBeUndefined()
    expect(planner.evaluationFor({ ...result(planner.getSnapshot().saved.lineup), peer_version: 'older-release' })).toBeUndefined()
    expect(planner.evaluationFor(result(lineup), null)).toBeUndefined()
  })
  it('rejects malformed formation responses and mismatched import evaluations', async () => {
    const { planner } = setup(null, {
      formation: async () => ({ ...lineup, assignments: { ...lineup.assignments, ST: 'sub' }, bench: ['striker'] }),
      evaluate: async () => result({ ...lineup, snapshot_id: 'old' }),
    })
    expect(await planner.changeFormation('4-4-2')).toBe(false)
    expect(await planner.importFile(file(lineup))).toBe(false)
    expect(planner.getSnapshot().saved.lineup).toEqual(lineup)
  })
})
