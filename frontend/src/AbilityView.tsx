import { useEffect, useId, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, exportJson } from './api'
import type { components } from './generated/api'
import './ability.css'

type Profile = components['schemas']['AbilityProfile']
type Ability = components['schemas']['AbilityScore']
type Feature = components['schemas']['FeatureDistribution']
const number = (v: number | null | undefined, digits = 1) => v == null ? 'Unavailable' : v.toFixed(digits)
const gap = (a: number | null | undefined, b: number | null | undefined, digits = 1) => a == null || b == null ? 'Unavailable' : `${a - b > 0 ? '+' : ''}${(a - b).toFixed(digits)}`
function useMorph(target: number[]) {
  const signature = JSON.stringify(target)
  const [values, setValues] = useState(target)
  const current = useRef(target)
  useEffect(() => {
    const next: number[] = JSON.parse(signature)
    const from = current.current
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || from.length !== next.length) {
      current.current = next; setValues(next); return
    }
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / 400)
      const eased = 1 - Math.pow(1 - progress, 3)
      current.current = next.map((n, i) => from[i] + (n - from[i]) * eased)
      setValues(current.current)
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [signature])
  return values
}
const point = (i: number, rating: number, n: number, radius = 128) => {
  const angle = i * 2 * Math.PI / n - Math.PI / 2
  return [210 + Math.cos(angle) * radius * rating / 100, 180 + Math.sin(angle) * radius * rating / 100]
}

function Radar({ abilities, comparison, selected, select, highlight }: {
  abilities: Ability[]; comparison?: Ability[]; selected: number; select: (i: number) => void; highlight: boolean
}) {
  const id = useId().replace(/:/g, '')
  const ratings = useMorph(abilities.map(a => a.rating ?? 0))
  const compareRatings = useMorph(comparison?.map(a => a.rating ?? 0) ?? [])
  const maximum = Math.max(100, ...abilities.map(a => a.rating ?? 0), ...(comparison?.map(a => a.rating ?? 0) ?? []), ...ratings, ...compareRatings)
  const ceiling = Math.ceil(maximum / 25) * 25
  const coordinate = (i: number, value: number, radius = 128) => point(i, value * 100 / ceiling, abilities.length, radius)
  const rings = [...new Set([20, 35, 50, 65, 80, 95, ...Array.from({length: Math.max(0, (ceiling - 100) / 25)}, (_, i) => 125 + i * 25)])]
  const complete = abilities.every(a => a.rating != null)
  const polygon = (values: number[]) => values.map((a, i) => coordinate(i, a).join(',')).join(' ')
  return <svg className="av-radar" viewBox="0 0 420 365" role="group" aria-label="Six position ability ratings. Select an axis to inspect its underlying features.">
    <defs><linearGradient id={id} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#dfceb0" stopOpacity=".38"/><stop offset="1" stopColor="#a73042" stopOpacity=".16"/></linearGradient></defs>
    {rings.map(r => <g key={r} className={r === 50 ? 'av-average' : 'av-ring'}><polygon points={abilities.map((_, i) => coordinate(i, r).join(',')).join(' ')} fill="none"/><text x="215" y={180 - r / ceiling * 128 + 4}>{r}{r === 50 ? ' · average' : ''}</text></g>)}
    {abilities.map((_, i) => <line key={i} className={selected === i ? 'av-spoke selected' : 'av-spoke'} x1="210" y1="180" x2={coordinate(i, ceiling)[0]} y2={coordinate(i, ceiling)[1]}/>)}
    {complete && <polygon className="av-player-polygon" fill={`url(#${id})`} points={polygon(ratings)}/>}
    {comparison?.every(a => a.rating != null) && <polygon className="av-comparison-polygon" points={polygon(compareRatings)}/>}
    {abilities.map((a, i) => {
      const [x, y] = coordinate(i, ceiling, 155)
      const [px, py] = coordinate(i, ratings[i])
      return <g key={a.name} className={`av-axis ${selected === i ? 'selected' : ''} ${highlight && selected !== i ? 'muted' : ''}`} role="button" tabIndex={0} aria-pressed={selected === i}
        aria-label={`${a.name}, rating ${number(a.rating)}, percentile ${number(a.percentile)}, ${number(a.z)} standard deviations.${comparison ? ` Comparison rating ${number(comparison[i].rating)}, rating gap ${gap(a.rating, comparison[i].rating)}, SD gap ${gap(a.z, comparison[i].z)}.` : ''} Show features.`}
        onClick={() => select(i)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(i) } else if (['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].includes(e.key)) { e.preventDefault(); const next = (i + (['ArrowRight', 'ArrowDown'].includes(e.key) ? 1 : -1) + abilities.length) % abilities.length; select(next); (e.currentTarget.parentElement?.querySelectorAll<SVGGElement>('.av-axis')[next])?.focus() } }}>
        <title>{a.name}: {number(a.rating)} rating · {number(a.percentile)} percentile · {number(a.z)} SD · {a.available}/{a.defined} features</title>
        {a.rating != null && <circle cx={px} cy={py} r="4"/>}<rect x={x - 65} y={y - 18} width="130" height="44" rx="4" fill="transparent"/>
        <text x={x} y={y - 3} textAnchor="middle">{a.name === 'Link-Up / Creation' ? 'Link-Up' : a.name === 'Defensive Activity' ? 'Defensive' : a.name}</text>
        <text className="av-axis-number" x={x} y={y + 17} textAnchor="middle">{a.rating == null ? '—' : number(ratings[i], 0)}</text>
      </g>
    })}
  </svg>
}

function Density({ feature: f, comparison, emphasize }: { feature: Feature; comparison?: Feature; emphasize: (v: boolean) => void }) {
  const [scan, setScan] = useState<number | null>(null)
  const [inspect, setInspect] = useState(false)
  const persistentScan = useRef(false)
  const values = f.density
  const left = Math.min(values[0]?.[0] ?? 0, f.value ?? Infinity, comparison?.value ?? Infinity)
  const right = Math.max(values.at(-1)?.[0] ?? 1, f.value ?? -Infinity, comparison?.value ?? -Infinity)
  const width = right - left || 1
  const x = (v: number) => 12 + (v - left) / width * 456
  const markers = useMorph([f.value == null ? 12 : x(f.value), f.peer_mean == null ? 12 : x(f.peer_mean), comparison?.value == null ? 12 : x(comparison.value)])
  const max = Math.max(...values.map(v => v[1]), 1e-12)
  const line = values.map(([v, density]) => `${x(v)},${78 - density / max * 56}`).join(' ')
  const nearest = scan == null ? null : values.reduce((a, b) => Math.abs(b[0] - scan) < Math.abs(a[0] - scan) ? b : a, values[0])
  const q = scan == null ? null : f.quantiles.reduce((a, b) => Math.abs(b[0] - scan) < Math.abs(a[0] - scan) ? b : a, f.quantiles[0])
  return <article className="av-feature" onMouseEnter={() => emphasize(true)} onMouseLeave={() => { emphasize(false); if (!persistentScan.current) setScan(null) }}>
    <div className="av-feature-title"><h4>{f.label}</h4><span>{f.direction < 0 ? '↓ Lower is better' : f.direction === 0 ? 'Context only' : '↑ Higher is better'} · {(f.weight * 100).toFixed(0)}% weight</span></div>
    {f.evidence_status === 'unrecorded_zero' ? <p className="av-missing">Not recorded (zero-filled). Its weight is redistributed proportionally to the remaining features.</p> : f.value == null ? <p className="av-missing">Measurement unavailable — no numeric evidence for this feature.</p> : <div className="av-feature-numbers"><strong>{number(f.value, 2)} <small>{f.unit}</small></strong><span>Peer average <b>{number(f.peer_mean, 2)}</b></span><span>Percentile <b>{number(f.percentile)}</b></span><span>SD gap <b>{number(f.z)}</b></span></div>}
    {values.length === 0 ? <p className="av-feature-foot">Peer distribution unavailable; this measurement has no calibrated reference.</p> : <svg className="av-density" viewBox="0 0 480 124" role="img" aria-label={`${f.label}. ${f.peer_count} role peers. Player ${number(f.value)} ${f.unit}; peer average ${number(f.peer_mean)}. Raw gap ${gap(f.value, f.peer_mean, 3)} ${f.unit}; directional gap ${number(f.z)} standard deviations. Raw values increase left to right.`}
      onPointerMove={e => { persistentScan.current = false; const box = e.currentTarget.getBoundingClientRect(); setScan(Math.max(left, Math.min(right, left + ((e.clientX - box.left) / box.width * 480 - 12) / 456 * width))) }}>
      {values.length > 0 && <><polygon className="av-density-area" points={`12,78 ${line} 468,78`}/><polyline className="av-density-line" points={line}/></>}
      <line className="av-baseline" x1="12" y1="78" x2="468" y2="78"/>
      {f.peer_mean != null && <line className="av-mean" x1={markers[1]} x2={markers[1]} y1="15" y2="80"><title>Role average: {number(f.peer_mean, 3)}</title></line>}
      {f.value != null && <g className="av-player-marker"><line x1={markers[0]} x2={markers[0]} y1="10" y2="80"/><path d={`M${markers[0] - 5},8 L${markers[0] + 5},8 L${markers[0]},15 Z`}/><title>Player: {number(f.value, 3)} · average gap {number(f.value - (f.peer_mean ?? 0), 3)} · {number(f.z)} SD · {number(f.percentile)} percentile · {f.peer_count} peers</title></g>}
      {comparison?.value != null && <line className="av-compare-marker" x1={markers[2]} x2={markers[2]} y1="10" y2="80"><title>Comparison: {number(comparison.value, 3)}</title></line>}
      {f.value != null && f.peer_mean != null && <g className="av-gap" aria-label={`Distance from peer average: ${gap(f.value, f.peer_mean, 3)} ${f.unit}, ${number(f.z)} directional standard deviations`}>
        <line x1={markers[1]} x2={markers[0]} y1="92" y2="92"/>
        <line x1={markers[1]} x2={markers[1]} y1="88" y2="96"/>
        <line x1={markers[0]} x2={markers[0]} y1="88" y2="96"/>
      </g>}
      {scan != null && <line className="av-scanner" x1={x(scan)} x2={x(scan)} y1="8" y2="80"/>}
      <text x="12" y="119">{number(left, 2)}</text><text x="468" y="119" textAnchor="end">{number(right, 2)} {f.unit}</text>
    </svg>}

    <button className="av-inspect" aria-expanded={inspect} onClick={() => setInspect(!inspect)}>Inspect {f.label} evidence</button>
    {inspect && <div className="av-evidence-panel"><dl><dt>Player raw value</dt><dd>{number(f.value, 3)} {f.unit}</dd><dt>Role peer average</dt><dd>{number(f.peer_mean, 3)} {f.unit}</dd><dt>Raw gap to average</dt><dd>{f.value == null || f.peer_mean == null ? 'Unavailable' : number(f.value - f.peer_mean, 3)} {f.unit}</dd><dt>Directional SD gap</dt><dd>{number(f.z)}</dd><dt>Performance percentile</dt><dd>{number(f.percentile)}</dd><dt>Peer population</dt><dd>{f.peer_count}</dd>{comparison && <><dt>Comparison raw value</dt><dd>{number(comparison.value, 3)} {f.unit}</dd><dt>Gap to comparison</dt><dd>{f.value == null || comparison.value == null ? 'Unavailable' : number(f.value - comparison.value, 3)} {f.unit}</dd></>}</dl><label>Scan {f.label} distribution<input type="range" disabled={values.length === 0} min={left} max={right || 1} step={width / 100} value={scan ?? f.value ?? left} onChange={e => { persistentScan.current = true; setScan(Number(e.target.value)) }}/></label><p aria-live="polite">{values.length === 0 ? 'Scanning unavailable until a reference distribution exists.' : scan == null ? 'Use the slider, arrow keys or the graph to scan the distribution.' : `Raw value ${number(scan, 3)}, approximate raw percentile ${number(q?.[1])}, density ${number(nearest?.[1], 3)}.`}</p></div>}
  </article>
}

type AnalysisPlayer = { id: string; name: string; short_name: string; roles?: string[]; position?: string }

/** Shared analysis for squad and catalogue player identities. */
export function AbilityView({ player, squadId, players, assignedPosition }: { player: AnalysisPlayer; squadId?: string; players: AnalysisPlayer[]; assignedPosition?: string }) {
  const endpoint = (id: string) => squadId ? `/squads/${squadId}/players/${id}/abilities${assignedPosition ? `?position=${encodeURIComponent(assignedPosition)}` : ''}` : `/catalogue/players/${id}/abilities`
  const scope = `${squadId ?? 'catalogue'}:${assignedPosition ?? 'natural'}`
  const [roleId, setRoleId] = useState('ST')
  const [selected, setSelected] = useState(0)
  const [highlight, setHighlight] = useState(false)
  const [compareId, setCompareId] = useState('')
  const profile = useQuery({ queryKey: ['abilities', scope, player.id], queryFn: () => api<Profile>(endpoint(player.id)) })
  const comparison = useQuery({ queryKey: ['abilities', scope, compareId], enabled: !!compareId, queryFn: () => api<Profile>(endpoint(compareId)) })
  if (profile.isPending) return <p role="status" className="ss-callout">Loading versioned position abilities…</p>
  if (profile.isError) return <div role="alert"><p>Position evidence could not be loaded: {profile.error.message}</p><button onClick={() => profile.refetch()}>Retry abilities</button></div>
  const p = profile.data
  const role = p.roles.find(r => r.role_id === roleId) ?? p.roles[0]
  if (!role) return <p role="status" className="ss-callout">No eligible position evidence is available for this snapshot.</p>
  const ability = role.abilities[selected]
  const other = comparison.data
  const compatible = other && other.evidence === p.evidence && other.season === p.season && (p.evidence === 'observed' || other.competition === p.competition) && other.reference_population_id === p.reference_population_id && other.observed_through === p.observed_through && other.feature_version === p.feature_version && other.weighting_version === p.weighting_version && other.normalization_version === p.normalization_version
  const compare = compatible ? other.roles.find(r => r.role_id === role.role_id) : undefined
  return <section className="ability-view" aria-label="Position ability analysis">
    <div className="av-role-toolbar"><label>Evaluation role<select value={role.role_id} onChange={e => setRoleId(e.target.value)}>{p.roles.map(r => <option value={r.role_id} key={r.role_id}>{r.label}</option>)}</select></label><label>Compare one player<select value={compareId} onChange={e => setCompareId(e.target.value)}><option value="">Role average only</option>{players.filter(v => v.id !== player.id).map(v => <option value={v.id} key={v.id}>{v.name}</option>)}</select></label></div>
    <div className="av-role-summary"><div><span>{role.label} rating</span><strong>{number(role.rating, 0)}</strong></div><p><b>{number(role.percentile)}</b> percentile<br/><b>{number(role.role_z)}</b> SD above role average · rank {role.rank ?? '—'}/{role.population_size}</p><p>Primary role: <b>{p.primary_role_id?.replaceAll('-', ' ') ?? 'Unavailable'}</b> · {number(p.primary_rating)}<br/>Versatility: {number(p.versatility)} · separate from position rating</p></div>

    {comparison.isFetching && <p role="status">Loading comparison…</p>}{comparison.isError && <p role="alert">Comparison unavailable. Choose another player or retry.</p>}
    {other && !compatible && <p role="status" className="ss-callout">Comparison unavailable: these players use different evidence, observation windows or reference cohorts. Choose a player from the same position scoring cohort.</p>}
    {role.abilities.some(a => a.rating == null) && <p role="status" className="ss-callout">Insufficient evidence for a complete ability polygon. Unavailable axes remain unscored; inspect the available measurements below.</p>}
    <div className="av-analysis-grid"><div className="av-radar-plane"><Radar abilities={role.abilities} comparison={compare?.abilities} selected={selected} select={setSelected} highlight={highlight}/><div className="av-legend"><span>{role.abilities.every(a => a.rating != null) ? `Solid champagne · ${player.short_name}` : 'No calibrated player polygon'}</span><span>Dashed silver · average 50</span>{compare?.abilities.every(a => a.rating != null) && <span>Dashed cyan · {players.find(v => v.id === compareId)?.short_name}</span>}</div><p className="ss-muted">Select an ability to inspect its measurements. Arrow keys move between axes.</p></div>
    <div className="av-ability-details" key={selected}><header><div><h3>{ability.name}</h3><p>{ability.available}/{ability.defined} features · {role.population_size} role peers · minimum {p.minimum_minutes} minutes</p></div><strong>{number(ability.rating, 0)}</strong></header><p>{number(ability.percentile)} percentile · {number(ability.z)} SD from average</p>{compare && <p className="av-comparison-readout">Player {number(ability.rating)} · comparison {number(compare.abilities[selected].rating)} · rating gap {gap(ability.rating, compare.abilities[selected].rating)} · latent gap {gap(ability.z, compare.abilities[selected].z)} SD</p>}
      {ability.features.map(f => <Density key={f.key} feature={f} comparison={compare?.abilities[selected].features.find(v => v.key === f.key)} emphasize={setHighlight}/>)}</div></div>
    <details className="ss-methods"><summary>Rating method</summary><p>Reliability shrinkage → directional feature z-scores → weighted ability composites → re-standardization → weighted OVR and re-standardization.</p><p>Rating = max(1, 50 + 15 × z), with no upper cap. Minimum 900 minutes and 30 compatible top-five-league peers. Zero-filled unrecorded features redistribute weight proportionally; recorded zeros keep their weight. Percentiles describe rank, separately from rating.</p><button onClick={() => exportJson(`${player.id}-abilities.json`, p)}>Export evidence</button></details>
  </section>
}
