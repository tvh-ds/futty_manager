import type { Evaluation, Formation, Lineup, SquadSnapshot } from './api'
import { storageKey, substitute, swapSlots, validateSavedSquad, type SavedSquad } from './squadState'

export type PlanningAdapters = {
  storage: Pick<Storage, 'getItem' | 'setItem'>
  formation: (lineup: Lineup, formation: string) => Promise<Lineup>
  evaluate: (lineup: Lineup) => Promise<Evaluation>
  preserve: (original: string | null) => void
}
type PlanningState = {
  saved: SavedSquad; history: Lineup[]; revision: number; notice: string
  storageWritable: boolean; changing: boolean
}
export const lineupIdentity = (lineup: Lineup) => JSON.stringify({
  snapshot: lineup.snapshot_id, formation: lineup.formation_id, multiplier: lineup.role_multiplier,
  assignments: Object.entries(lineup.assignments).sort(([a], [b]) => a.localeCompare(b)), bench: lineup.bench,
})
export const evidenceIdentity = (value: Pick<SquadSnapshot, 'peer_version' | 'feature_version' | 'rating_version' | 'chemistry_version'>) =>
  JSON.stringify([value.peer_version, value.feature_version, value.rating_version, value.chemistry_version])

/** Owns accepted planning revisions, recovery and async commit ownership. */
export class LineupPlanner {
  private state: PlanningState
  private listeners = new Set<() => void>()
  private operation = 0
  constructor(private snapshot: SquadSnapshot, private formations: Formation[], private adapters: PlanningAdapters) {
    let saved = this.validate({ schema: 'scout-squad-v1', lineup: snapshot.default_lineup, notes: {} })
    let notice = '', storageWritable = true
    try {
      const raw = adapters.storage.getItem(storageKey(snapshot))
      if (raw) saved = this.validate(JSON.parse(raw))
    } catch {
      notice = 'Saved lineup could not be read. Original storage is preserved until you import a valid backup or explicitly recover.'
      storageWritable = false
    }
    this.state = { saved, history: [], revision: 0, notice, storageWritable, changing: false }
  }
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener) } }
  getSnapshot = () => this.state
  private update(patch: Partial<PlanningState>) {
    this.state = { ...this.state, ...patch }
    this.listeners.forEach(listener => listener())
  }
  private validate(saved: unknown) { return validateSavedSquad(saved, this.snapshot, this.formations) }
  setNotice = (notice: string) => this.update({ notice })
  persist = () => {
    if (!this.state.storageWritable) return
    try { this.adapters.storage.setItem(storageKey(this.snapshot), JSON.stringify(this.state.saved)) }
    catch { this.update({ notice: 'Browser storage is unavailable. Export your lineup before leaving.', storageWritable: false }) }
  }
  commit = (lineup: Lineup, notes = this.state.saved.notes) => {
    const saved = this.validate({ schema: 'scout-squad-v1', lineup, notes })
    this.update({ saved, history: [...this.state.history.slice(-29), this.state.saved.lineup], revision: this.state.revision + 1 })
    this.persist()
  }
  swap = (a: string, b: string) => {
    this.commit(swapSlots(this.state.saved.lineup, a, b))
    this.setNotice(a === b ? 'Lineup unchanged.' : 'Players swapped.')
  }
  preview = (slot: string, incoming: string) => this.validate({ ...this.state.saved,
    lineup: substitute(this.state.saved.lineup, slot, incoming) }).lineup
  undo = () => {
    const previous = this.state.history.at(-1)
    if (!previous) return
    const saved = this.validate({ ...this.state.saved, lineup: previous })
    this.update({ saved, history: this.state.history.slice(0, -1), revision: this.state.revision + 1,
      notice: 'Previous planning state restored; notes retained.' })
    this.persist()
  }
  reset = () => { this.commit(this.snapshot.default_lineup); this.setNotice('Default planning lineup restored.') }
  setNote = (id: string, note: string) => {
    const saved = this.validate({ ...this.state.saved, notes: { ...this.state.saved.notes, [id]: note } })
    this.update({ saved, revision: this.state.revision + 1 }); this.persist()
  }
  preserveOriginal = () => this.adapters.preserve(this.adapters.storage.getItem(storageKey(this.snapshot)))
  recoverStorage = () => {
    this.update({ storageWritable: true, notice: 'Storage recovered by your request.' }); this.persist()
  }
  evaluationFor = (result: Evaluation | undefined, lineup: Lineup | null = this.state.saved.lineup) =>
    result && lineup && evidenceIdentity(result) === evidenceIdentity(this.snapshot) &&
      lineupIdentity(result.lineup) === lineupIdentity(lineup) ? result : undefined

  changeFormation = async (id: string) => {
    const revision = this.state.revision, ticket = ++this.operation
    const lineup = this.state.saved.lineup
    this.update({ changing: true })
    try {
      const next = await this.adapters.formation(lineup, id)
      if (ticket !== this.operation) return false
      if (revision !== this.state.revision) {
        this.setNotice('The lineup changed during reassignment. Choose the formation again.'); return false
      }
      // Validate the response, including preservation of the selected eleven.
      this.validate({ ...this.state.saved, lineup: next })
      if (next.formation_id !== id || next.role_multiplier !== lineup.role_multiplier ||
          JSON.stringify(next.bench) !== JSON.stringify(lineup.bench))
        throw new Error('Formation response changed unrelated planning settings')
      if (JSON.stringify(Object.values(next.assignments).sort()) !== JSON.stringify(Object.values(lineup.assignments).sort()))
        throw new Error('Formation response changed the selected players')
      this.commit(next); this.setNotice('Formation changed; your eleven players were preserved.')
      return true
    } catch (error) {
      if (ticket === this.operation) this.setNotice((error as Error).message)
      return false
    } finally { if (ticket === this.operation) this.update({ changing: false }) }
  }
  importFile = async (file: Pick<File, 'size' | 'text'>) => {
    const revision = this.state.revision, ticket = ++this.operation
    // A newer import supersedes an in-flight formation request.
    this.update({ changing: false })
    try {
      if (file.size > 1000000) throw new Error('Lineup files must be smaller than 1 MB')
      const imported = this.validate(JSON.parse(await file.text()))
      const evaluated = await this.adapters.evaluate(imported.lineup)
      if (ticket !== this.operation) return false
      if (revision !== this.state.revision) throw new Error('Lineup changed during import. Import again to apply it.')
      if (!this.evaluationFor(evaluated, imported.lineup)) throw new Error('Import evaluation does not match the lineup')
      if (!this.state.storageWritable) this.preserveOriginal()
      this.commit(imported.lineup, imported.notes)
      this.update({ storageWritable: true, notice: 'Validated lineup imported.' }); this.persist()
      return true
    } catch (error) {
      if (ticket === this.operation) this.setNotice(`Import rejected: ${(error as Error).message}. Existing storage is preserved.`)
      return false
    }
  }
}
