import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import type { Evaluation, Formation, Lineup, SquadSnapshot } from './api'
import { useLineupPlanner } from './useLineupPlanner'
import { evidenceIdentity } from './lineupPlanner'

const { transport } = vi.hoisted(() => ({ transport: vi.fn() }))
vi.mock('./api', () => ({ api: transport, exportJson: vi.fn() }))
afterEach(() => { cleanup(); localStorage.clear(); transport.mockReset() })
const formation = { id: '4-3-3', slots: [{ id: 'GK', role: 'GK' }, { id: 'ST', role: 'ST' }] } as Formation
const lineup = { snapshot_id: 'hook-fixture', formation_id: '4-3-3', assignments: { GK: 'keeper', ST: 'striker' },
  bench: ['sub'], role_multiplier: 1.5 } as Lineup
const snapshot = { id: 'squad', snapshot_id: 'hook-fixture', default_lineup: lineup, players: [
  { id: 'keeper', roles: ['GK'] }, { id: 'striker', roles: ['ST'] }, { id: 'sub', roles: ['ST'] },
] } as SquadSnapshot
const evaluation = (lineup: Lineup, score: number) => ({ lineup, team_rating: score }) as Evaluation
function context() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>
  return { wrapper, client }
}

it('marks changed scores pending and ignores a delayed previous lineup response', async () => {
  const pending: { lineup: Lineup; resolve: (result: Evaluation) => void }[] = []
  transport.mockImplementation((_path: string, lineup: Lineup) => new Promise<Evaluation>(resolve => {
    pending.push({ lineup, resolve })
  }))
  const { wrapper, client } = context()
  const { result } = renderHook(() => useLineupPlanner(snapshot, [formation], null, null, false), { wrapper })
  await waitFor(() => expect(pending).toHaveLength(1))
  act(() => result.current.planner.commit(result.current.planner.preview('ST', 'sub')))
  expect(result.current.pending).toBe(true)
  expect(result.current.evaluation).toBeUndefined()
  await waitFor(() => expect(pending).toHaveLength(2))
  await act(async () => pending[1].resolve(evaluation(pending[1].lineup, 75)))
  await waitFor(() => expect(result.current.evaluation?.team_rating).toBe(75))
  await act(async () => pending[0].resolve(evaluation(pending[0].lineup, 22)))
  await waitFor(() => expect(client.getQueryData<Evaluation>(['squad-evaluation', snapshot.id,
    snapshot.snapshot_id, evidenceIdentity(snapshot), lineup])?.team_rating).toBe(22))
  expect(result.current.evaluation?.team_rating).toBe(75)
  expect(result.current.pending).toBe(false)
  client.clear()
})

it('clears invalid preview evidence when an accepted edit outlives presentation selection', async () => {
  transport.mockImplementation((path: string, input: Lineup) => Promise.resolve(
    path.includes('position-ratings') ? {} : evaluation(input, 60)))
  const { wrapper, client } = context()
  const { result } = renderHook(() => useLineupPlanner(snapshot, [formation], 'ST', 'sub', true), { wrapper })
  await waitFor(() => expect(result.current.previewData).toBeTruthy())
  act(() => result.current.planner.commit(result.current.previewLineup!))
  expect(result.current.previewLineup).toBeNull()
  expect(result.current.previewData).toBeUndefined()
  await waitFor(() => expect(result.current.pending).toBe(false))
  client.clear()
})
