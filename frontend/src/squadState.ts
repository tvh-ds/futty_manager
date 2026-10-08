import type { Formation, Lineup, SquadSnapshot } from './api'

export const storageKey = (snapshot: SquadSnapshot) => `scout.lineup.v1:${snapshot.snapshot_id}`
export type SavedSquad = { schema: 'scout-squad-v1'; lineup: Lineup; notes: Record<string, string> }
export function validateSavedSquad(value: unknown, snapshot: SquadSnapshot, formations: Formation[]): SavedSquad {
  if (!value || typeof value !== 'object') throw new Error('Invalid lineup document')
  const saved = value as SavedSquad
  if (saved.schema !== 'scout-squad-v1' || !saved.lineup || !saved.notes || Array.isArray(saved.notes)) throw new Error('Unsupported lineup format')
  const l = saved.lineup
  const formation = formations.find(f => f.id === l.formation_id)
  if (l.snapshot_id !== snapshot.snapshot_id || !formation) throw new Error('This lineup belongs to another snapshot or formation')
  if (!Number.isFinite(l.role_multiplier) || l.role_multiplier < 1 || l.role_multiplier > 3 || Math.abs(l.role_multiplier * 10 - Math.round(l.role_multiplier * 10)) > 1e-8) throw new Error('Invalid role multiplier')
  if (!l.assignments || typeof l.assignments !== 'object' || Array.isArray(l.assignments) || !Array.isArray(l.bench) || l.bench.length > 9) throw new Error('Invalid lineup locations')
  const keys = Object.keys(l.assignments).sort()
  if (JSON.stringify(keys) !== JSON.stringify(formation.slots.map(s => s.id).sort())) throw new Error('Formation slots do not match')
  const ids = [...Object.values(l.assignments).filter(id => id !== null), ...l.bench]
  if (new Set(ids).size !== ids.length || ids.some(id => !snapshot.players.some(p => p.id === id))) throw new Error('Unknown or duplicate player')
  for (const slot of formation.slots) {
    const player = snapshot.players.find(p => p.id === l.assignments[slot.id])
    if (player && (slot.role === 'GK') !== player.roles.includes('GK')) throw new Error('Goalkeepers and outfield players cannot exchange slots')
  }
  if (Object.keys(saved.notes).length > snapshot.players.length || Object.entries(saved.notes).some(([id, note]) => !snapshot.players.some(p => p.id === id) || typeof note !== 'string' || note.length > 5000)) throw new Error('Invalid scouting notes')
  // Copy only documented inputs; never trust exported scores or incidental properties.
  return { schema: 'scout-squad-v1', lineup: { snapshot_id: l.snapshot_id, formation_id: l.formation_id,
    assignments: { ...l.assignments }, bench: [...l.bench], role_multiplier: l.role_multiplier }, notes: { ...saved.notes } }
}
export function swapSlots(lineup: Lineup, a: string, b: string): Lineup {
  if (!(a in lineup.assignments) || !(b in lineup.assignments)) throw new Error('Unknown slot')
  return { ...lineup, assignments: { ...lineup.assignments, [a]: lineup.assignments[b], [b]: lineup.assignments[a] } }
}
export function substitute(lineup: Lineup, slot: string, incoming: string): Lineup {
  if (!(slot in lineup.assignments) || Object.values(lineup.assignments).includes(incoming)) throw new Error('Invalid substitution')
  const outgoing = lineup.assignments[slot]
  const bench = lineup.bench.flatMap(id => id === incoming ? outgoing ? [outgoing] : [] : [id])
  return { ...lineup, assignments: { ...lineup.assignments, [slot]: incoming }, bench }
}
