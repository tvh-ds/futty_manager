import { useEffect, useState, useSyncExternalStore } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, exportJson, type Evaluation, type Formation, type Lineup, type Rating, type SquadSnapshot } from './api'
import { LineupPlanner, evidenceIdentity, lineupIdentity } from './lineupPlanner'

/** React adapter: keeps request caching and presentation outside planning rules. */
export function useLineupPlanner(snapshot: SquadSnapshot, formations: Formation[], selected: string | null,
  incoming: string | null, benchOpen: boolean) {
  const [planner] = useState(() => new LineupPlanner(snapshot, formations, {
    storage: { getItem: key => localStorage.getItem(key), setItem: (key, value) => localStorage.setItem(key, value) },
    formation: (lineup, formation_id) => api<Lineup>(`/squads/${snapshot.id}/formation`, { lineup, formation_id }),
    evaluate: lineup => api<Evaluation>(`/squads/${snapshot.id}/evaluate`, lineup),
    preserve: original => exportJson('scout-preserved-storage.json', { original }),
  }))
  const state = useSyncExternalStore(planner.subscribe, planner.getSnapshot)
  const lineup = state.saved.lineup
  const evidence = evidenceIdentity(snapshot)
  const [debounced, setDebounced] = useState(lineup)
  useEffect(() => { planner.persist() }, [planner])
  useEffect(() => {
    const onlySettings = lineupIdentity({ ...lineup, role_multiplier: debounced.role_multiplier }) === lineupIdentity(debounced)
    const timer = setTimeout(() => setDebounced(lineup), onlySettings ? 200 : 0)
    return () => clearTimeout(timer)
  }, [lineup, debounced])
  const evaluated = useQuery({ queryKey: ['squad-evaluation', snapshot.id, snapshot.snapshot_id, evidence, debounced],
    queryFn: () => api<Evaluation>(`/squads/${snapshot.id}/evaluate`, debounced), retry: false })
  const evaluation = planner.evaluationFor(evaluated.data)
  const pending = !evaluation
  let previewLineup: Lineup | null = null
  // Presentation selection can briefly outlive an async accepted revision.
  try { if (incoming && selected) previewLineup = planner.preview(selected, incoming) } catch { /* no valid preview */ }
  const preview = useQuery({ queryKey: ['squad-preview', snapshot.id, snapshot.snapshot_id, evidence, previewLineup], enabled: !!previewLineup,
    queryFn: () => api<Evaluation>(`/squads/${snapshot.id}/evaluate`, previewLineup), retry: false })
  const previewData = planner.evaluationFor(preview.data, previewLineup)
  const currentSlot = formations.find(f => f.id === lineup.formation_id)?.slots.find(s => s.id === selected)
  const benchRatings = useQuery({ queryKey: ['squad-position-ratings', snapshot.id, snapshot.snapshot_id, evidence, currentSlot?.role, currentSlot?.label, debounced.role_multiplier],
    enabled: benchOpen && !!currentSlot,
    queryFn: () => api<Record<string, Rating>>(`/squads/${snapshot.id}/position-ratings?role=${encodeURIComponent(currentSlot!.role)}&position=${encodeURIComponent(currentSlot!.label)}&multiplier=${debounced.role_multiplier}`) })
  const benchPending = pending || (!!currentSlot && (!benchRatings.data || debounced.role_multiplier !== lineup.role_multiplier))
  return { planner, ...state, lineup, evaluated, evaluation, pending, previewLineup, preview, previewData, benchRatings, benchPending }
}
