import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { DragDropProvider, DragOverlay, useDraggable, useDroppable, PointerSensor, KeyboardSensor, type DragEndEvent } from '@dnd-kit/react'
import { ArrowLeftRight, ArrowUpRight, ChevronDown, Download, GripVertical, Info, RotateCcw, Shield, Undo2, Upload, Users, X } from 'lucide-react'
import { api, exportJson, type CatalogueDetail, type Chemistry, type Formation, type Lineup, type Rating, type SquadPlayer, type SquadSnapshot } from './api'
import { useLineupPlanner } from './useLineupPlanner'
import { evidenceIdentity } from './lineupPlanner'
import './squad.css'
import './squadStadium.css'
import { AbilityView } from './AbilityView'
import { ClubBadge, PlayerCardFace, PlayerPortrait } from './PlayerCardFace'

const score = (n: number | null | undefined, digits = 0) => n == null ? '—' : n.toFixed(digits)
const roleName: Record<string, string> = { GK: 'Goalkeeper', CB: 'Centre-back', 'FB/WB': 'Full-back / wing-back', DM: 'Defensive midfielder', CM: 'Central midfielder', AM: 'Attacking midfielder', W: 'Winger', ST: 'Striker' }
const sensors = [PointerSensor, KeyboardSensor]


// Presentation only: the keeper is docked as in the reference. Slot identities,
// assignment matching and the chemistry topology still come from the server.
function stadiumFormation(source: Formation): Formation {
  const rows = [...new Set(source.slots.filter(s => s.role !== 'GK').map(s => s.y))].sort((a,b) => a-b)
  return { ...source, slots: source.slots.map(slot => {
    if (slot.role === 'GK') return { ...slot, x: .085, y: .17 }
    if (source.id === '4-3-3') {
      const locations: Record<string, [number,number]> = {
        LW:[.25,.18], ST:[.50,.18], RW:[.75,.18], LCM:[.30,.49], RCM:[.70,.49], DM:[.50,.51],
        LB:[.18,.83], LCB:[.39,.83], RCB:[.61,.83], RB:[.82,.83],
      }
      const [x,y] = locations[slot.id]
      return { ...slot, x, y }
    }
    const row = rows.indexOf(slot.y)
    const members = source.slots.filter(s => s.y === slot.y).sort((a,b)=>a.x-b.x)
    const index = members.findIndex(s=>s.id===slot.id)
    const x = members.length === 1 ? .50 : row === 0 ? .25 + index * .50 / (members.length - 1)
      : .18 + index * .64 / (members.length - 1)
    return { ...slot, x, y: .17 + row * .66 / (rows.length - 1) }
  }) }
}

function PlayerCard({ player, label, rating, selected, pending, actions }: {
  player: SquadPlayer; label: string; rating?: Rating; selected?: boolean; pending: boolean; actions?: ReactNode
}) {
  return <div className={`ss-card ${selected ? 'selected' : ''}`}>
    <span className="ss-position-banner">{label}</span>
    <PlayerCardFace compact finish="stadium" name={player.name} shortName={player.short_name} position={label} rating={rating?.score} ratingDescription={rating?.score == null ? rating?.warnings.join(' ') : undefined}
      photo={player.portrait_url} country={player.country_label} club="Liverpool" clubLogo={player.club_logo_url} scores={rating?.ability_scores || player.ability_scores || {}} pending={pending} number={player.number}
      caption={player.attribute_evidence === 'observed' ? '2025/26 · OBSERVED' : player.attribute_evidence === 'unavailable' ? 'NO MAPPED EVIDENCE' : 'DEMONSTRATION'}/>
    {rating?.warnings.length ? <span className="ss-role-warning" title={rating.warnings.join('. ')}>!</span> : null}
    {actions}
  </div>
}

function PitchCard({ player, slot, label, rating, pending, selected, select, details, bench, explore, swapMode }: {
  player: SquadPlayer; slot: string; label: string; rating?: Rating; pending: boolean; selected: boolean;
  select: () => void; details: () => void; bench: () => void; explore: string; swapMode: boolean
}) {
  const drag = useDraggable({ id: `pitch:${slot}` })
  const drop = useDroppable({ id: `pitch:${slot}` })
  return <div ref={el => { drag.ref(el); drop.ref(el) }} className={`ss-card-wrap ${drop.isDropTarget ? 'drop-target' : ''} ${drag.isDragging ? 'dragging' : ''}`} data-slot={slot}>
    <PlayerCard player={player} label={label} rating={rating} selected={selected} pending={pending} actions={<>
      <button className="ss-card-select" onClick={swapMode ? select : details} aria-label={`${swapMode ? 'Swap with' : 'Details for'} ${player.name}, ${label}`} aria-pressed={selected} />
      <button ref={drag.handleRef} className="ss-drag-handle" aria-label={`Move ${player.name}`} title="Drag to swap · keyboard: Space, arrows, Space"><GripVertical size={14} /></button>
      <div className="ss-card-actions">
        <button onClick={bench} aria-label={`Substitute ${player.name}`}>Sub</button>
        <Link to={explore} aria-label={`Explore role candidates for ${player.name}`}>Explore</Link>
      </div>
    </>} />
  </div>
}

function BenchCard({ player, rating, pending, incoming, details, eligible, substituting, position }: {
  player: SquadPlayer; rating?: Rating; pending: boolean; incoming: () => void; details: () => void; eligible: boolean; substituting: boolean; position?: string
}) {
  const drag = useDraggable({ id: `bench:${player.id}`, disabled: !eligible })
  return <div ref={drag.ref} className={`ss-bench-card ${drag.isDragging ? 'dragging' : ''}`}>
    <button className="ss-bench-select" onClick={substituting ? incoming : details} disabled={!eligible} aria-label={`${substituting ? 'Preview' : 'Details for'} ${player.name}`}>
      <PlayerCardFace compact finish="stadium" name={player.name} shortName={player.short_name} position={position || rating?.role || player.roles[0]} rating={rating?.score} ratingDescription={rating?.score == null ? rating?.warnings.join(' ') : undefined}
        photo={player.portrait_url} country={player.country_label} club="Liverpool" clubLogo={player.club_logo_url} scores={rating?.ability_scores || player.ability_scores || {}} pending={pending} number={player.number}
        caption={player.attribute_evidence === 'observed' ? '2025/26 · OBSERVED' : player.attribute_evidence === 'synthetic' ? 'DEMONSTRATION' : 'NO MAPPED EVIDENCE'}/>
    </button>
    <button onClick={details} aria-label={`Details for ${player.name}`}><Info size={16} /></button>
    <button ref={drag.handleRef} disabled={!eligible} className="ss-bench-handle" aria-label={`Move ${player.name}`}><GripVertical size={16} /></button>
  </div>
}

function Drawer({ title, close, children, wide = false }: { title: string; close: () => void; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close() }, [])
  const dismiss = () => { ref.current?.close(); close() }
  return <dialog ref={ref} className={`ss-dialog ${wide ? 'wide' : ''}`} aria-label={title} onCancel={event => { event.preventDefault(); dismiss() }} onClick={event => { if (event.target === event.currentTarget) dismiss() }}>
    <div className="ss-dialog-inner"><header><h2>{title}</h2><button autoFocus onClick={dismiss} aria-label="Close drawer"><X size={22} /></button></header>{children}</div>
  </dialog>
}

function PlayerDetails({ player, rating, pending, snapshot, note, setNote, role }: {
  player: SquadPlayer; rating?: Rating; pending: boolean; snapshot: SquadSnapshot; note: string; setNote: (text: string) => void; role: string
}) {
  const attributes = useQuery({ queryKey: ['catalogue-detail', player.catalogue_id], enabled: !!player.catalogue_id,
    queryFn: () => api<CatalogueDetail>(`/catalogue/players/${player.catalogue_id}`) })
  return <>
    <div className="ss-player-heading"><div className="ss-detail-portrait"><PlayerPortrait key={player.portrait_url || player.id} url={player.portrait_url} name={player.name} number={player.number}/></div><div><h3>{player.name}</h3><p className="ss-tag">{player.attribute_evidence === 'observed' ? 'Observed 2025/26 attributes · demo chemistry' : player.attribute_evidence === 'unavailable' ? 'Performance evidence unavailable' : 'Demonstration measurements'}</p><p>Sourced identity · #{player.number}</p><p>{player.country_label} · {player.category}</p><a href={player.source_url} target="_blank" rel="noreferrer">Official player source <ArrowUpRight size={14} /></a></div></div>
    <p className="ss-callout">{player.attribute_evidence === 'synthetic' ? 'Sourced Liverpool identity with demonstration measurements. Not live statistics.' : 'Current Liverpool roster; completed 2025/26 performance. Six abilities and OVR use the assigned position.'}</p>
    <div className="ss-detail-summary"><div><span>Assigned {role}</span><strong>{pending ? '···' : score(rating?.score, 1)}</strong></div><div><span>Performance position {rating?.primary_role || player.roles[0]}</span><strong>{pending ? '···' : score(rating?.normal_role_score, 1)}</strong></div><div><span>Feature coverage</span><strong>{pending ? '···' : `${rating?.available ?? 0}/${rating?.defined ?? 0}`}</strong></div></div>
    <details className="ss-methods"><summary>Planning role and identity evidence</summary><p>Planning roles: {player.roles.map(r => roleName[r]).join(', ')}. Specific positions and sides are manual assignments. Country tags are not complete citizenship records.</p></details>
    {rating?.score == null && rating?.warnings.map(w => <p className="ss-callout" key={w}>{w}</p>)}
    {player.attribute_evidence !== 'synthetic' || player.roles.includes('ST') ? <AbilityView player={player} squadId={snapshot.id} assignedPosition={role} players={snapshot.players} /> : player.attribute_evidence === 'synthetic' ? <>
      <h3>Provisional position metrics</h3><p className="ss-muted">This position uses standardized raw metrics, with 50 representing the role-cohort average. Its rigorous ability feature set has not yet been supplied.</p>
      <div className="ss-skill-list">{rating?.skills.map(c => <div className="ss-skill" key={c.skill.key}><div><strong>{c.skill.label}</strong><span>{c.emphasized ? 'Role emphasis' : 'Supporting metric'}</span></div><p>{c.skill.raw_value == null ? 'Unavailable measurement' : `${c.skill.raw_value.toFixed(3)} ${c.skill.unit}`} · {c.skill.lower_is_better ? 'lower is better' : 'higher is better'}</p><p>{pending ? 'Contribution pending' : c.contribution == null ? 'Missing contribution' : `${c.contribution.toFixed(3)} contribution to raw latent composite`}</p></div>)}</div>
      <p className="ss-muted">Latent composites are standardized against a fixed demonstration role cohort. Display = 50 + 15 × z, with a floor of 1 and no upper cap. Missing evidence and role mismatch do not introduce hidden penalties.</p>
    </> : null}
    {player.attribute_evidence !== 'synthetic' && <><h3>Mapped source attributes</h3>
      {attributes.isError ? <p role="alert">Attributes unavailable. <button onClick={() => attributes.refetch()}>Retry attributes</button></p> : attributes.data ? <>
        <p className="ss-muted">{attributes.data.numerical_features}/{attributes.data.defined_features} numeric features · {attributes.data.mapping_status} mapping. These measurements do not imply a position rating.</p>
        <table className="ss-real-features"><thead><tr><th>Feature</th><th>Value</th><th>Source</th></tr></thead><tbody>{attributes.data.features.map(f => <tr key={f.key}><th scope="row">{f.label}<small>{f.unit}</small></th><td>{f.value == null ? f.status === 'not_applicable_zero_attempts' ? 'N/A' : '—' : f.value.toFixed(2)}</td><td><a href={f.source_url} target="_blank" rel="noreferrer">{f.provider}</a></td></tr>)}</tbody></table>
        <Link to={`/players?name=${encodeURIComponent(player.name)}`}>Open in player database <ArrowUpRight size={14}/></Link>
      </> : <p>{player.catalogue_id ? 'Loading observed attributes…' : 'No matched 2025/26 top-five-league evidence. No demonstration values are substituted.'}</p>}
    </>}
    <label className="ss-field">Scouting notes<textarea maxLength={5000} value={note} onChange={e => setNote(e.target.value)} placeholder="What would you investigate in a match?" /></label>
    <p className="ss-muted">Notes remain in this browser. Export a backup to retain them.</p>
    <Link className="ss-primary" to={`/scout?role=${encodeURIComponent(role)}&from=squad`}>Explore role candidates — demo <ArrowUpRight size={16} /></Link>
    <p className="ss-muted">Actual Liverpool profile matching is unavailable. The recruitment dataset contains fictional players.</p>
    <details className="ss-methods"><summary>Provenance and limitations</summary><p>{snapshot.observation_window}</p><p>{snapshot.snapshot_id} · {snapshot.feature_version} · {snapshot.peer_version}</p><p>{snapshot.rating_version} · {snapshot.chemistry_version}</p>{snapshot.limitations.map(l => <p key={l}>{l}</p>)}</details>
  </>
}

function PairDetails({ pair, players }: { pair: Chemistry; players: SquadPlayer[] }) {
  return <><p className="ss-muted">{players.find(p => p.id === pair.player_a)?.name} + {players.find(p => p.id === pair.player_b)?.name}</p>
    <div className="ss-pair-score"><strong>{score(pair.score, 2)}<small>/10</small></strong><span>{pair.available}/5 measures · {pair.band === 'unknown' ? 'Insufficient evidence' : pair.band + ' band'}</span></div>
    <p className="ss-callout">Demonstration inputs. These values make no claims about actual languages, ages, nationalities, career overlap or shared minutes.</p>
    {pair.components.map(c => <div className="ss-pair-component" key={c.key}><div><strong>{c.label}</strong><b>{score(c.score, 2)} /10</b></div><p>{c.explanation}</p><small>{({ nationality: '10 for verified overlap; otherwise 0 only with complete records.', club_tenure: '10 × min(overlapping same-club days / 365, 1).', language: '10 for a verified shared language; unknown when absence cannot be established.', age: '10 × max(0, 1 − age gap / 10).', minutes: '10 × min(concurrent teammate minutes / 1,800, 1).' } as Record<string, string>)[c.key]}</small></div>)}
    <p className="ss-muted">Equal-weight average of available components; at least three required. Unknown is never zero. Rounded to two decimals: red ≤3.33, yellow 3.34–6.66, green ≥6.67. Familiarity is not tactical compatibility or a probability of playing well together.</p></>
}

function Studio({ snapshot, formations }: { snapshot: SquadSnapshot; formations: Formation[] }) {
  const realMode = snapshot.players.some(p => p.attribute_evidence === 'observed' || p.attribute_evidence === 'unavailable')
  useEffect(() => { document.title = `Scout · Squad Studio · ${snapshot.team} ${snapshot.season}` }, [snapshot.team, snapshot.season])
  const [benchOpen, setBenchOpen] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [swapFrom, setSwapFrom] = useState<string | null>(null)
  const [details, setDetails] = useState<string | null>(null)
  const [pairKey, setPairKey] = useState<string | null>(null)
  const [chemistryOn, setChemistryOn] = useState(true)
  const [incoming, setIncoming] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [dragName, setDragName] = useState('')
  const { planner, saved, lineup, history, notice, storageWritable, changing,
    evaluated, evaluation, pending, previewLineup, preview, previewData, benchRatings, benchPending } =
    useLineupPlanner(snapshot, formations, selected, incoming, benchOpen)
  const { setNotice } = planner
  const formation = useMemo(() => stadiumFormation(formations.find(f => f.id === lineup.formation_id)!), [formations, lineup.formation_id])
  const players = Object.fromEntries(snapshot.players.map(p => [p.id, p]))
  const pitchRef = useRef<HTMLElement>(null)
  useEffect(() => {
    const fit = () => {
      const pitch = pitchRef.current
      if (!pitch || window.innerWidth <= 760) return
      const height = Math.max(390, window.innerHeight - pitch.getBoundingClientRect().top - 8)
      const spacing = formation.id === '4-2-3-1' ? .22 : .30
      pitch.style.setProperty('--ss-fit-height', `${height}px`)
      const cardHeight = Math.max(76, Math.min(238, height * spacing - 18, pitch.clientWidth * (formation.id === '3-5-2' ? .12 : .145) / .85))
      pitch.style.setProperty('--ss-fit-card-height', `${cardHeight}px`)
      pitch.style.setProperty('--ss-stadium-card-width', `${cardHeight * .85}px`)
      pitch.closest<HTMLElement>('.ss-planning-space')?.style.setProperty('--ss-fit-height', `${height}px`)
    }
    fit(); window.addEventListener('resize', fit)
    const observer = new ResizeObserver(fit)
    if (pitchRef.current) observer.observe(pitchRef.current)
    return () => { observer.disconnect(); window.removeEventListener('resize', fit) }
  }, [formation, notice, changing, swapFrom])
  const fileInput = useRef<HTMLInputElement>(null)
  const benchRef = useRef<HTMLElement>(null)
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  useEffect(() => { if (benchOpen) { benchRef.current?.scrollTo({ top: 0, behavior: 'auto' }); if (window.innerWidth <= 760) benchRef.current?.parentElement?.scrollTo({ left: benchRef.current.offsetLeft, behavior: reducedMotion ? 'auto' : 'smooth' }) } else if (window.innerWidth <= 760) pitchRef.current?.closest('.ss-planning-space')?.scrollTo({ left: 0, behavior: 'auto' }) }, [benchOpen, incoming, reducedMotion])
  const currentId = selected ? lineup.assignments[selected] : null
  const currentPlayer = currentId ? players[currentId] : null
  const currentSlot = formation.slots.find(s => s.id === selected)
  useEffect(() => {
    const cancel = (event: KeyboardEvent) => { if (event.key === 'Escape') { setSwapFrom(null); setIncoming(null); setSelected(null); setBenchOpen(false) } }
    window.addEventListener('keydown', cancel); return () => window.removeEventListener('keydown', cancel)
  }, [])
  function commit(next: Lineup) { planner.commit(next); setIncoming(null) }
  function swap(a: string, b: string) {
    try { planner.swap(a, b); setIncoming(null) }
    catch (error) { setNotice((error as Error).message) }
    setSwapFrom(null)
  }
  function selectSlot(slot: string) {
    if (swapFrom) { swap(swapFrom, slot); return }
    setSelected(selected === slot ? null : slot); setIncoming(null)
  }
  function openSub(slot: string) { setSelected(slot); setIncoming(null); setBenchOpen(true); setSwapFrom(null) }
  function previewIncoming(pid: string, slot = selected) {
    if (!slot) { setNotice('Select a pitch player, then choose a substitute.'); return }
    try { planner.preview(slot, pid); setSelected(slot); setIncoming(pid); setBenchOpen(true) }
    catch (error) { setNotice((error as Error).message) }
  }
  async function changeFormation(id: string) {
    if (await planner.changeFormation(id)) { setSelected(null); setSwapFrom(null); setIncoming(null) }
  }
  function dragEnd(event: DragEndEvent) {
    setDragName('')
    if (event.canceled) return
    const source = String(event.operation.source?.id || ''), target = String(event.operation.target?.id || '')
    if (!target.startsWith('pitch:') || source === target) return
    if (source.startsWith('pitch:')) swap(source.slice(6), target.slice(6))
    else if (source.startsWith('bench:')) previewIncoming(source.slice(6), target.slice(6))
  }
  async function importLineup(file?: File) {
    if (file && await planner.importFile(file)) { setSelected(null); setIncoming(null); setSwapFrom(null) }
  }
  const reserves = snapshot.players.filter(p => !Object.values(lineup.assignments).includes(p.id) && !lineup.bench.includes(p.id)).map(p => p.id)
  const visible = (ids: string[]) => ids.filter(id => players[id].name.toLowerCase().includes(search.toLowerCase()) && (filter === 'all' || players[id].roles.includes(filter as never)))
  const outfieldEdge = (edge: {slot_a:string;slot_b:string}) => formation.slots.find(s=>s.id===edge.slot_a)?.role !== 'GK' && formation.slots.find(s=>s.id===edge.slot_b)?.role !== 'GK'
  const displayedEdges = evaluation?.edges.filter(outfieldEdge) || []
  const scoredLinks = displayedEdges.map(e=>e.chemistry.score).filter((s):s is number=>s != null)
  const displayedChemistry = scoredLinks.length ? scoredLinks.reduce((sum,s)=>sum+s,0)/scoredLinks.length : null
  const pair = displayedEdges.find(e => `${e.slot_a}:${e.slot_b}` === pairKey)?.chemistry
  const detailPlayer = details ? players[details] : null
  const detailSlot = formation.slots.find(s => lineup.assignments[s.id] === details)
  const delta = (a: number | null | undefined, b: number | null | undefined) => a == null || b == null ? 'Unavailable' : `${a - b >= 0 ? '+' : ''}${(a - b).toFixed(1)}`
  const affected = previewData?.edges.filter(e => outfieldEdge(e) && (e.slot_a === selected || e.slot_b === selected)) || []
  return <div className="squad-studio ss-stadium">
    <a className="ss-skip" href="#squad-pitch">Skip to formation pitch</a>
    <header className="ss-header"><Link className="ss-brand" to="/">SCOUT<span> / SQUAD STUDIO</span></Link><nav aria-label="Scout navigation"><Link className="active" to="/">Squad</Link><Link to="/players">Players</Link><Link to="/scout">Recruitment <ArrowUpRight size={13} /></Link></nav><span className="ss-snapshot">SNAPSHOT <b>06 OCT 2026</b></span></header>
    <main>
      <section className="ss-titlebar"><div className="ss-club-mark"><ClubBadge url={snapshot.club_logo_url} name="Liverpool"/></div><div className="ss-club-title"><h1>Liverpool <span>2026/27</span></h1><p>Men’s first team</p></div><div className="ss-catalogue"><label>League<select aria-label="League" value="England" onChange={() => {}}><option>England</option>{['Spain', 'Germany', 'Italy', 'France'].map(l => <option disabled key={l}>{l} — unavailable</option>)}</select></label><label>Team<select aria-label="Team" value="Liverpool" onChange={() => {}}><option>Liverpool</option><option disabled>Other teams — unavailable</option></select></label></div></section>
      <div className="ss-toolbar"><label className="ss-formation-label"><span>FORMATION</span><select aria-label="Formation" value={lineup.formation_id} disabled={changing} onChange={e => changeFormation(e.target.value)}>{formations.map(f => <option key={f.id}>{f.id}</option>)}</select><ChevronDown size={14} /></label>
        <button onClick={() => setBenchOpen(!benchOpen)} aria-expanded={benchOpen} className={benchOpen ? 'on' : ''}><Users size={17} />{benchOpen ? 'Hide bench' : 'Show bench'} <span className="ss-count">9</span></button>
        <button aria-pressed={chemistryOn} onClick={() => setChemistryOn(!chemistryOn)}><span className={`ss-toggle ${chemistryOn ? 'on' : ''}`} />Chemistry</button>
        <button disabled={!history.length} onClick={() => { planner.undo(); setIncoming(null); setSelected(null); setSwapFrom(null); setNotice('Previous planning state restored; notes retained.') }}><Undo2 size={17} />Undo</button>
        <div className="ss-toolbar-end"><button aria-label="Export" onClick={() => exportJson('scout-liverpool-lineup.json', { ...saved, evaluation: evaluation ?? null, presentation: { chemistry_scope: 'outfield_links', chemistry: displayedChemistry }, provenance: { squad_snapshot: snapshot.snapshot_id, roster_date: snapshot.snapshot_date, feature_version: snapshot.feature_version, peer_version: snapshot.peer_version, rating_version: snapshot.rating_version, chemistry_version: snapshot.chemistry_version, attribute_evidence: realMode ? 'observed_or_unavailable' : 'synthetic', chemistry_evidence: 'synthetic', performance_season: realMode ? '2025/26' : null, role_multiplier: lineup.role_multiplier, limitations: snapshot.limitations, sources: snapshot.sources }, exported_at: new Date().toISOString() })}><Download size={16} /><span>Export</span></button><button aria-label="Import" onClick={() => fileInput.current?.click()}><Upload size={16} /><span>Import</span></button><button onClick={() => { if (window.confirm('Reset the planning lineup? Notes will be retained.')) { planner.reset(); setIncoming(null); setSelected(null); setSwapFrom(null) } }} aria-label="Reset lineup"><RotateCcw size={16} /></button></div>
        <input ref={fileInput} className="sr-only" type="file" aria-label="Import lineup JSON" accept=".json,application/json" onChange={e => { importLineup(e.target.files?.[0]); e.target.value = '' }} />
      </div>
      <div className="ss-summary" aria-busy={pending}><div><span>STARTING XI RATING</span><strong>{pending ? '···' : score(evaluation?.team_rating, 1)}</strong></div><div title="Mean chemistry of visible outfield links"><span>CHEMISTRY</span><strong>{pending ? '···' : score(displayedChemistry, 2)}<i>/10</i></strong></div><p className="ss-demo-notice"><Info size={15} />{realMode ? <>Mapped attributes use 2025/26 source evidence.<br />Unavailable ratings stay unscored. Chemistry is demo data.</> : <>Liverpool squad identities are sourced.<br />Ratings and chemistry are demonstration data.</>}</p></div>
      <div className="ss-feedback" role="status" aria-live="polite">{changing ? 'Matching your eleven to the new formation…' : swapFrom ? 'Choose another pitch player to swap. Escape cancels.' : notice}
        {!storageWritable && <><button onClick={() => { planner.preserveOriginal() }}>Export original</button><button onClick={() => { if (window.confirm('Recover using the current planning lineup? Export the original first if you need it.')) { planner.recoverStorage() } }}>Recover storage</button></>}
      </div>
      {evaluated.error && <div className="ss-error" role="alert">Scores unavailable: {evaluated.error.message} <button onClick={() => evaluated.refetch()}>Retry evaluation</button></div>}
      <DragDropProvider sensors={sensors} onDragEnd={dragEnd} onDragStart={event => { const id = String(event.operation.source?.id || ''); const pid = id.startsWith('pitch:') ? lineup.assignments[id.slice(6)] : id.slice(6); setDragName(pid ? players[pid]?.name || '' : '') }}>
        <p className="ss-pan-hint">Scroll across the pitch to view every position →</p>
        <div className={`ss-planning-space ${benchOpen ? 'bench-open' : ''}`}>
        <div className="ss-pitch-scroll" role="region" aria-label="Scrollable formation canvas" tabIndex={0}>
        <section ref={pitchRef} className="ss-stage" id="squad-pitch" aria-label="Formation pitch">
          <div className="ss-stage-caption"><span>{lineup.formation_id} <i>/</i> {chemistryOn ? 'CHEMISTRY — FAMILIARITY PROXY' : 'LINKS HIDDEN'}</span><span>ATTACK ↑</span></div>
          <svg className="ss-pitch" role="group" viewBox="0 0 1000 760" preserveAspectRatio="none" aria-label="Football pitch and familiarity links">
            <defs><linearGradient id="pitch-light" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#163f32" /><stop offset=".5" stopColor="#215640" /><stop offset="1" stopColor="#103f30" /></linearGradient><pattern id="pitch-stripes" width="1000" height="152" patternUnits="userSpaceOnUse"><rect width="1000" height="76" fill="#ffffff" opacity=".024" /></pattern></defs>
            <path className="ss-turf-fallback" d="M58 25H942L982 734H18Z" fill="url(#pitch-light)" />
            <path className="ss-turf-fallback" d="M58 25H942L982 734H18Z" fill="url(#pitch-stripes)" />
            <g className="ss-pitch-markings" fill="none"><path d="M235 120H765L981 731H19ZM143 381H857" /><ellipse cx="500" cy="381" rx="101" ry="58" /><ellipse cx="500" cy="381" rx="2" ry="2" fill="currentColor" /><path d="M393 120 366 216H634L607 120M451 120 445 158H555L549 120M290 731 323 587H677L710 731M392 731 403 669H597L608 731M446 216Q500 253 554 216M436 587Q500 551 564 587" /><path d="M471 120V107H529V120M463 731V748H537V731" /></g>
            {chemistryOn && !pending && displayedEdges.map(edge => {
              const a = formation.slots.find(s => s.id === edge.slot_a)!, b = formation.slots.find(s => s.id === edge.slot_b)!
              const key = `${a.id}:${b.id}`, active = !selected || selected === a.id || selected === b.id
              return <g key={key} className={`ss-link ${edge.chemistry.band} ${a.role === 'GK' || b.role === 'GK' ? 'keeper' : ''} ${active ? '' : 'dim'}`}>
                <line x1={a.x * 1000} y1={a.y * 760} x2={b.x * 1000} y2={b.y * 760} />
                <g role="button" tabIndex={0} aria-label={`Chemistry ${players[lineup.assignments[a.id]!].short_name} and ${players[lineup.assignments[b.id]!].short_name}: ${score(edge.chemistry.score, 2)}, ${edge.chemistry.available}/5, demo`} onClick={() => setPairKey(key)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setPairKey(key) } }}>
                  <line className="ss-link-hit" x1={a.x * 1000} y1={a.y * 760} x2={b.x * 1000} y2={b.y * 760} />
                  <g className="ss-link-label" transform={`translate(${(a.x + b.x) * 500} ${(a.y + b.y) * 380})`}><rect x="-22" y="-12" width="44" height="24" rx="5" /><text textAnchor="middle" y="5">{score(edge.chemistry.score, 1)}</text></g>
                </g>
              </g>
            })}
          </svg>
          {formation.slots.map(slot => { const pid = lineup.assignments[slot.id]; return <div key={pid || slot.id} className="ss-position" style={{ left: `${slot.x * 100}%`, top: `${slot.y * 100}%` }}>
            {pid ? <PitchCard player={players[pid]} slot={slot.id} label={slot.label} rating={evaluation?.ratings[pid]} pending={pending} selected={selected === slot.id} swapMode={!!swapFrom} select={() => selectSlot(slot.id)} details={() => setDetails(pid)} bench={() => openSub(slot.id)} explore={`/scout?role=${encodeURIComponent(slot.role)}&from=squad`} /> : <button className="ss-empty-slot" onClick={() => openSub(slot.id)}>+ {slot.label}</button>}
          </div> })}
          <div className="ss-pitch-footer"><span><i className="green" />6.67–10 <i className="yellow" />3.34–6.66 <i className="red" />0–3.33 <i className="unknown" />Unknown</span><p>{pending ? 'Authoritative evaluation pending' : 'Select a link to inspect evidence'}</p></div>
        </section>
        </div>
        {selected && <div className="ss-selection-bar"><span><b>{currentPlayer?.name || 'Empty slot'}</b> · {selected}</span><button onClick={() => currentId && setDetails(currentId)} disabled={!currentId}>Details</button><button onClick={() => openSub(selected)}>Substitute</button><button onClick={() => { setSwapFrom(selected); setBenchOpen(false); setIncoming(null) }} disabled={!currentId}><ArrowLeftRight size={15} />Swap position</button><button onClick={() => { setSelected(null); setSwapFrom(null); setIncoming(null) }} aria-label="Deselect player"><X size={17} /></button></div>}
        {benchOpen && <section ref={benchRef} className="ss-bench" aria-label="Bench and reserves"><header><h2>Bench & reserves <span>{snapshot.players.length} players</span></h2><button onClick={() => { setBenchOpen(false); setIncoming(null) }} aria-label="Close bench"><X size={20} /></button></header>
          <div className="ss-bench-controls"><input aria-label="Search squad" placeholder="Search squad…" value={search} onChange={e => setSearch(e.target.value)} /><select aria-label="Squad role filter" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All positions</option>{Object.entries(roleName).map(([r, name]) => <option key={r} value={r}>{name}</option>)}</select><p>{selected ? `Previewing ${selected} position ratings; tap a player to preview.` : 'Natural-role ratings. Select a pitch player for a substitution.'}</p></div>
          {incoming && <div className="ss-sub-preview" aria-busy={!previewData}><div><h3>Preview: {currentPlayer?.short_name || selected} → {players[incoming].short_name} </h3><p>Position rating {score(evaluation?.ratings[currentId || '']?.score, 1)} → {score(previewData?.ratings[incoming]?.score, 1)} <span>XI change: {delta(previewData?.team_rating, evaluation?.team_rating)}</span></p><p>{players[incoming].roles.includes(currentSlot?.role as never) ? 'Supported planning role.' : 'Role mismatch: outside manually assigned roles.'} Coverage {previewData?.ratings[incoming]?.available ?? '…'}/{previewData?.ratings[incoming]?.defined ?? '…'} observed position-registry features. Unavailable ratings stay unscored; chemistry is illustrative.</p></div>
            <div className="ss-sub-links">{affected.map(e => { const old = evaluation?.edges.find(o => o.slot_a === e.slot_a && o.slot_b === e.slot_b); return <span key={`${e.slot_a}:${e.slot_b}`}>{e.slot_a} ↔ {e.slot_b}: {score(old?.chemistry.score, 2)} → {score(e.chemistry.score, 2)} <small>{e.chemistry.available}/5</small></span> })}</div><div className="ss-sub-buttons"><button className="ss-primary" disabled={!previewData || !previewLineup} onClick={() => { if (previewData && previewLineup && planner.evaluationFor(previewData, previewLineup)) { commit(previewLineup); setNotice('Substitution confirmed.'); setBenchOpen(false) } }}>Confirm substitution</button><button onClick={() => setIncoming(null)}>Cancel preview</button></div>{preview.error && <p role="alert">Preview unavailable: {preview.error.message}</p>}</div>}
          {benchRatings.error && currentSlot && <p role="alert">Position ratings unavailable: {benchRatings.error.message}</p>}
          {['bench', 'reserves'].map(group => { const ids = visible(group === 'bench' ? lineup.bench : reserves); return <div className="ss-bench-group" key={group}><h3>{group === 'bench' ? `Planning bench · ${lineup.bench.length}/9` : `Reserves · ${reserves.length}`}</h3><div className="ss-bench-grid">{ids.map(pid => <BenchCard key={pid} player={players[pid]} position={currentSlot?.label} pending={benchPending} rating={currentSlot ? benchRatings.data?.[pid] : evaluation?.ratings[pid]} substituting={!!currentSlot} eligible={!currentSlot || (currentSlot.role === 'GK') === players[pid].roles.includes('GK')} incoming={() => previewIncoming(pid)} details={() => setDetails(pid)} />)}{ids.length === 0 && <p className="ss-muted">No players match these filters.</p>}</div></div> })}
        </section>}
        </div>
        <DragOverlay dropAnimation={reducedMotion ? null : { duration: 220, easing: 'ease-out' }}><div className="ss-drag-preview">{dragName || 'Moving player'}</div></DragOverlay>
      </DragDropProvider>
      <footer className="ss-footer"><p><Shield size={14} />Browser-local planning · source snapshot {snapshot.snapshot_date} · no live match data</p></footer>
    </main>
    {detailPlayer && <Drawer title="Player details" close={() => setDetails(null)}><PlayerDetails player={detailPlayer} rating={detailSlot || !currentSlot || !benchOpen ? evaluation?.ratings[detailPlayer.id] : benchRatings.data?.[detailPlayer.id]} pending={detailSlot || !benchOpen ? pending : benchPending} snapshot={snapshot} note={saved.notes[detailPlayer.id] || ''} role={detailSlot?.label || (benchOpen ? currentSlot?.label : null) || detailPlayer.roles[0]} setNote={text => planner.setNote(detailPlayer.id, text)} /></Drawer>}
    {pair && <Drawer title="Chemistry — familiarity proxy" close={() => setPairKey(null)}><PairDetails pair={pair} players={snapshot.players} /></Drawer>}

  </div>
}

export default function SquadStudio() {
  const squad = useQuery({ queryKey: ['squad-snapshot'], queryFn: () => api<SquadSnapshot>('/squads/liverpool-men') })
  const formations = useQuery({ queryKey: ['formations'], queryFn: () => api<Formation[]>('/formations') })
  if (squad.error || formations.error) return <div className="squad-studio ss-loading"><Shield size={40} /><h1>Squad Studio is unavailable</h1><p role="alert">{squad.error?.message || formations.error?.message}</p><button onClick={() => { squad.refetch(); formations.refetch() }}>Retry connection</button><Link to="/scout">Open recruitment</Link></div>
  if (!squad.data || !formations.data) return <div className="squad-studio ss-loading" role="status"><Shield size={40} /><h1>Preparing your squad</h1><p>A sleeping demo service may need a moment to start.</p></div>
  return <Studio key={`${squad.data.snapshot_id}:${evidenceIdentity(squad.data)}`} snapshot={squad.data} formations={formations.data} />
}
