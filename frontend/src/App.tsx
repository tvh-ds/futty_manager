import { useEffect, useMemo, useState } from 'react'
import * as Tabs from '@radix-ui/react-tabs'
import { useMutation, useQuery, keepPreviousData } from '@tanstack/react-query'
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table'
import { ArrowDownToLine, ArrowRight, Check, ChevronDown, CircleHelp, Search, SlidersHorizontal, Star, X } from 'lucide-react'
import { api, exportJson, type Brief, type Candidate, type Player, type Release, type Results, type Role, type RoleSpec, type Scenario, type Team } from './api'
import { emptySaved, loadSaved, validateSaved, type SavedState } from './storage'
import { Link, useSearchParams } from 'react-router'

const initialBrief: Brief = { role: 'CB', team_id: null, replacement_id: null,
  constraints: { min_age: 15, max_age: 40, min_minutes: 450, foot: null, attributes: [] },
  preferences: {}, weights: { similarity: 1, quality: 1, tactical_fit: 1, replacement_fit: 1, coverage: 0.5 },
  limit: 30, include_verification_required: true }
const componentLabels: Record<string, string> = { similarity: 'Style match', quality: 'Quality proxy',
  tactical_fit: 'Team fit', replacement_fit: 'Replacement', coverage: 'Evidence' }
const number = (value: number, digits = 1) => new Intl.NumberFormat('en', { maximumFractionDigits: digits }).format(value)
const statusLabel = (status: string) => status === 'eligible' ? 'Meets known constraints' : status === 'verification_required' ? 'Verify attributes' : 'Sparse evidence'

function Meter({ value, label }: { value: number | null | undefined; label: string }) {
  return <div className="meter" aria-label={`${label}: ${value == null ? 'unavailable' : number(value)}`}>
    <div className="meter-track"><span style={{ width: `${value ?? 0}%` }} /></div>
    <span>{value == null ? '—' : number(value, 0)}</span>
  </div>
}

function Alert({ children }: { children: React.ReactNode }) {
  return <div className="alert" role="alert"><CircleHelp size={18} /><span>{children}</span></div>
}

function CandidateDetail({ candidate, labels, note, setNote, close }: {
  candidate: Candidate; labels: Record<string, string>; note: string; setNote: (note: string) => void; close: () => void
}) {
  return <aside className="evidence-pane" aria-label="Player evidence">
    <div className="pane-heading"><h2>{candidate.player.name}</h2><button className="icon-button" onClick={close} aria-label="Close evidence"><X size={20} /></button></div>
    <p className="muted">{candidate.player.league} · {candidate.player.roles.join(', ')} · {number(candidate.player.minutes, 0)} minutes</p>
    <p className="evidence-status">{statusLabel(candidate.status)}</p>
    <h3>Why this player appears</h3>
    <ul className="explanations">{candidate.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>
    {candidate.unknowns.length > 0 && <><h3>Next scouting questions</h3><ul className="explanations">{candidate.unknowns.map(item => <li key={item}>{item}</li>)}</ul></>}
    <h3>Role evidence</h3><p className="muted small">90% posterior ranges where event counts are available. These describe statistical rates, not transfer outcomes.</p>
    <div className="metric-list">{Object.entries(candidate.profile.values).map(([key, value]) => <div className="metric-row" key={key}>
      <div><strong>{labels[key] || key}</strong><span className="muted small">{candidate.player.metrics[key]?.evidence}</span></div>
      <div><strong>{number(value, 2)}</strong><span className="muted small">{candidate.profile.intervals[key].map(item => number(item, 2)).join(' – ')}</span></div>
    </div>)}</div>
    {Object.keys(candidate.replacement_changes).length > 0 && <><h3>Change from replacement</h3><div className="metric-list">{Object.entries(candidate.replacement_changes).map(([key, value]) => <div className="metric-row" key={key}><span>{labels[key] || key}<small className="muted">{candidate.replacement_functions?.[key]}</small></span><strong>{value > 0 ? '+' : ''}{number(value, 2)}</strong></div>)}</div><p className="muted small">Labels describe metric direction and tolerance, not causal gains. A higher value is not always an improvement.</p></>}
    <label className="field">Scouting notes<textarea maxLength={5000} value={note} onChange={event => setNote(event.target.value)} placeholder="What would you verify in the next match?" /></label>
    <p className="muted small">Notes remain in this browser.</p>
  </aside>
}

function ScenarioPanel({ teams, players, release }: { teams: Team[]; players: Candidate[]; release?: Release }) {
  const [playerId, setPlayerId] = useState('')
  const [teamId, setTeamId] = useState('')
  const [minutes, setMinutes] = useState(2400)
  const [adaptation, setAdaptation] = useState(0.9)
  const [availability, setAvailability] = useState(0.85)
  const [seed, setSeed] = useState(42)
  const [assignments, setAssignments] = useState<Record<string, Role | null>>({})
  const [fees, setFees] = useState<Record<string, string>>({})
  const [budget, setBudget] = useState('')
  const [required, setRequired] = useState<Partial<Record<Role, number>>>({})
  const mutation = useMutation({ mutationFn: (body: unknown) => api<Scenario>('/scenarios/simulate', body) })
  const selectedPlayer = playerId || players[0]?.player.id || ''
  const selectedTeam = teamId || teams[0]?.id || ''
  const roster = useQuery({ queryKey: ['scenario-roster', selectedTeam], enabled: !!selectedTeam,
    queryFn: () => api<{ players: Player[] }>(`/teams/${selectedTeam}`) })
  const recruit = players.find(item => item.player.id === selectedPlayer)?.player
  const pool = useMemo(() => [...(roster.data?.players || []).filter(item => item.player_id !== recruit?.player_id),
    ...(recruit ? [recruit] : [])], [roster.data, recruit])
  const roleFamilies: Role[] = ['GK', 'CB', 'FB/WB', 'DM', 'CM', 'AM', 'W', 'ST']
  const scenarioAssignments = Object.fromEntries(pool.filter(item => assignments[item.id] !== null)
    .map(item => [item.id, assignments[item.id] || item.roles[0]]))
  const scenarioFees = Object.fromEntries(pool.filter(item => scenarioAssignments[item.id] && fees[item.id]?.trim())
    .map(item => [item.id, Number(fees[item.id])]))
  return <section className="scenario-layout">
    <form className="brief-pane" onSubmit={event => { event.preventDefault(); mutation.mutate({ player_id: selectedPlayer, team_id: selectedTeam,
      season_minutes: minutes, adaptation_mean: adaptation, adaptation_sd: 0.12, availability_mean: availability, seed, samples: 2000,
      assignments: scenarioAssignments, fees: scenarioFees, budget: budget === '' ? null : Number(budget), role_requirements: required }) }}>
      <h2>Explore a transfer scenario</h2><p className="muted">Adjust explicit assumptions and see the range of possible contributions.</p>
      <label className="field">Recruit<select aria-label="Recruit" value={selectedPlayer} onChange={event => setPlayerId(event.target.value)}>{players.map(item => <option key={item.player.id} value={item.player.id}>{item.player.name}</option>)}</select></label>
      <label className="field">Destination<select aria-label="Destination" value={selectedTeam} onChange={event => setTeamId(event.target.value)}>{teams.map(team => <option key={team.id} value={team.id}>{team.name}</option>)}</select></label>
      <label className="field">Planned minutes<input type="number" min={0} max={4500} step={1} value={minutes} onChange={event => setMinutes(Number(event.target.value))} /></label>
      <label className="field">Adaptation multiplier <strong>{adaptation.toFixed(2)}</strong><input type="range" min={0.1} max={1.5} step={0.05} value={adaptation} onChange={event => setAdaptation(Number(event.target.value))} /></label>
      <label className="field">Expected availability <strong>{number(availability * 100, 0)}%</strong><input type="range" min={0} max={1} step={0.05} value={availability} onChange={event => setAvailability(Number(event.target.value))} /></label>
      <label className="field">Simulation seed<input type="number" min={0} max={4294967295} value={seed} onChange={event => setSeed(Number(event.target.value))} /></label>
      <details className="brief-section"><summary>Squad assignments and fees</summary><p className="muted small">One role per player. Blank fees remain unknown. Values are your scenario assumptions; no market prices are inferred.</p>
        {roster.error && <Alert>{roster.error.message}</Alert>}
        {pool.map(item => <div key={item.id}><label className="field">{item.name} role<select value={assignments[item.id] === null ? '' : assignments[item.id] || item.roles[0]}
          onChange={event => setAssignments({ ...assignments, [item.id]: event.target.value ? event.target.value as Role : null })}>
          <option value="">Exclude from scenario</option>{item.roles.map(role => <option key={role} value={role}>{role}</option>)}</select></label>
          <label className="field">{item.name} fee (€)<input type="number" min={0} max={1e9} value={fees[item.id] || ''}
            onChange={event => setFees({ ...fees, [item.id]: event.target.value })} /></label></div>)}
        <button type="button" className="secondary" onClick={() => setFees(previous => ({ ...previous,
          ...Object.fromEntries(pool.filter(item => item.id !== selectedPlayer).map(item => [item.id, '0'])) }))}>
          Assume existing squad fees are €0</button>
        <label className="field">Scenario budget (€)<input type="number" min={0} max={1e10} value={budget} onChange={event => setBudget(event.target.value)} /></label>
      </details>
      <details className="brief-section"><summary>Minimum squad depth by role</summary><p className="muted small">Counts describe squad depth, not a simultaneous formation or registration eligibility.</p>
        {roleFamilies.map(role => <label className="field" key={role}>{role} minimum<input type="number" min={0} max={10} value={required[role] ?? 1}
          onChange={event => setRequired({ ...required, [role]: Number(event.target.value) })} /></label>)}
      </details>
      <button className="primary" disabled={!selectedPlayer || mutation.isPending || roster.isPending}>Run scenario <ArrowRight size={17} /></button>
      {mutation.error && <Alert>{mutation.error.message}</Alert>}
    </form>
    <div className="scenario-results">
      <h2>Assumptions become ranges</h2><p className="muted">These are simulations, not learned transfer forecasts. Results describe the selected recruit; role counts describe the destination squad plus that recruit.</p>
      {mutation.isPending && <p role="status">Running reproducible simulation…</p>}
      {mutation.data ? <>
        <div className="section-toolbar"><h3>Contribution ranges</h3><button className="secondary" onClick={() => exportJson('scout-scenario.json', mutation.data)}><ArrowDownToLine size={16} /> Export scenario</button></div>
        <table className="plain-table"><thead><tr><th>Outcome</th><th>Low · p10</th><th>Median</th><th>High · p90</th></tr></thead><tbody>
          <tr><th>Minutes</th>{mutation.data.minutes_interval.map((value, index) => <td key={index}>{number(value, 0)}</td>)}</tr>
          {Object.entries(mutation.data.outcomes).map(([key, values]) => <tr key={key}><th>{key.replace(' / 90', ' · total')}</th>{values.map((value, index) => <td key={index}>{number(value, 0)}</td>)}</tr>)}
        </tbody></table>
        <h3>Squad role coverage</h3><div className="coverage-grid">{Object.entries(mutation.data.squad_coverage).map(([role, count]) => <div key={role}><span>{role}</span><strong>{count}</strong><small>{count === 0 ? 'Gap to investigate' : 'Players assigned'}</small></div>)}</div>
        <p className="muted">{mutation.data.total_fee === null ? 'Some assigned player fees are unknown. Budget feasibility remains unknown.' :
          `Entered fees total €${number(mutation.data.total_fee, 0)}. Budget: ${mutation.data.budget_satisfied === null ? 'not supplied' : mutation.data.budget_satisfied ? 'within entered budget' : 'exceeds entered budget'}.`}
          {' '}Registration eligibility remains unverified.</p>
        {mutation.data.squad_gaps.length > 0 && <p className="caution">Below requested depth: {mutation.data.squad_gaps.join(', ')}</p>}
        <ul className="explanations">{mutation.data.limitations.map(item => <li key={item}>{item}</li>)}</ul>
        <p className="muted small">Seed {mutation.data.seed} · {mutation.data.release.id}</p>
      </> : <div className="empty-state"><SlidersHorizontal size={30} /><h3>Set a destination and your assumptions</h3><p>Run a scenario to inspect minutes, contributions and squad coverage.</p><span className="muted small">{release?.season} · No fees are assumed.</span></div>}
    </div>
  </section>
}

export default function App() {
  useEffect(() => { document.title = 'Scout · Recruitment workbench' }, [])
  const [params] = useSearchParams()
  const requestedRole = params.get('role')
  const bridgeRole = (['GK', 'CB', 'FB/WB', 'DM', 'CM', 'AM', 'W', 'ST'].includes(requestedRole || '') ? requestedRole : 'CB') as Role
  const datasets = useQuery({ queryKey: ['datasets'], queryFn: () => api<{ active: Release; releases: Release[] }>('/datasets') })
  const teams = useQuery({ queryKey: ['teams'], queryFn: () => api<Team[]>('/teams') })
  const roles = useQuery({ queryKey: ['roles'], queryFn: () => api<RoleSpec[]>('/roles') })
  const [brief, setBrief] = useState<Brief>({ ...initialBrief, role: bridgeRole })
  const [submitted, setSubmitted] = useState<Brief | null>(null)
  const [text, setText] = useState('I need an athletic left-footed CB who can defend a high line, break lines with passing and receive under pressure.')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Candidate | null>(null)
  const [comparison, setComparison] = useState<Candidate[]>([])
  const [startup] = useState(() => { try { return { saved: loadSaved(), recovered: true } }
    catch { return { saved: emptySaved, recovered: false } } })
  const [saved, setSaved] = useState<SavedState>(startup.saved)
  const [storageWritable, setStorageWritable] = useState(startup.recovered)
  const [notice, setNotice] = useState(startup.recovered ? '' :
    'Stored notes could not be read. Original browser data is preserved. Import a backup or clear local notes in Data & methods to resume saving.')
  const [watchOnly, setWatchOnly] = useState(false)
  const [tab, setTab] = useState('recruitment')
  const results = useQuery({ queryKey: ['recommendations', submitted], enabled: submitted !== null && !!datasets.data,
    queryFn: () => api<Results>('/recommendations', submitted), placeholderData: keepPreviousData })
  const roster = useQuery({ queryKey: ['roster', brief.team_id], enabled: !!brief.team_id,
    queryFn: () => api<{ players: Player[] }>(`/teams/${brief.team_id}`) })
  const interpretation = useMutation({ mutationFn: () => api<{ brief: Brief; warnings: string[]; method: string }>('/briefs/interpret', { text }),
    onSuccess: response => { setBrief({ ...response.brief, team_id: brief.team_id }); setNotice(response.warnings.join(' ')) } })
  const activeRole = roles.data?.find(role => role.id === brief.role)
  const labels = activeRole?.metric_labels || {}
  const dirty = JSON.stringify(brief) !== JSON.stringify(submitted)
  const release = results.data?.release || datasets.data?.active
  useEffect(() => { if (teams.data?.length && !submitted) {
    const next = { ...initialBrief, role: bridgeRole, team_id: teams.data[0].id }; setBrief(next); setSubmitted(next)
  } }, [teams.data, submitted, bridgeRole])
  useEffect(() => { if (!storageWritable) return
    try { localStorage.setItem('scout.saved.v1', JSON.stringify(saved)) }
    catch { setNotice('Browser storage is unavailable. Export your notes and watchlist before leaving.') } }, [saved, storageWritable])
  useEffect(() => { setComparison([]); setSelected(null) }, [results.data?.release.id])
  const toggleWatch = (identity: string) => setSaved(previous => ({ ...previous, watchlist: previous.watchlist.includes(identity)
    ? previous.watchlist.filter(item => item !== identity) : [...previous.watchlist, identity] }))
  const toggleCompare = (candidate: Candidate) => setComparison(previous => previous.some(item => item.player.id === candidate.player.id)
    ? previous.filter(item => item.player.id !== candidate.player.id) : previous.length < 4 ? [...previous, candidate] : previous)
  const columns = useMemo(() => {
    const column = createColumnHelper<Candidate>()
    return [
      column.display({ id: 'select', header: 'Compare', cell: ({ row }) => <input aria-label={`Compare ${row.original.player.name}`} type="checkbox"
        checked={comparison.some(item => item.player.id === row.original.player.id)} disabled={comparison.length >= 4 && !comparison.some(item => item.player.id === row.original.player.id)}
        onChange={() => toggleCompare(row.original)} /> }),
      column.accessor(item => item.player.name, { id: 'player', header: 'Player', cell: ({ row }) => <button className="player-name" onClick={() => setSelected(row.original)}>
        <strong>{row.original.player.name}</strong><span>{row.original.player.league} · {row.original.player.age ?? 'Age unknown'} · {row.original.player.foot ?? 'Foot unknown'}</span></button> }),
      column.accessor('score', { header: 'Overall', cell: ({ getValue }) => <strong className="overall">{number(getValue(), 0)}</strong> }),
      column.display({ id: 'similarity', header: 'Style', cell: ({ row }) => <Meter value={row.original.components.similarity} label="Style match" /> }),
      column.display({ id: 'quality', header: 'Quality', cell: ({ row }) => <Meter value={row.original.components.quality} label="Quality proxy" /> }),
      column.display({ id: 'coverage', header: 'Evidence', cell: ({ row }) => <div><Meter value={row.original.components.coverage} label="Coverage" /><span className="small muted">{row.original.unknowns.length ? `${row.original.unknowns.length} to verify` : 'Known constraints met'}</span></div> }),
      column.display({ id: 'watch', header: 'Save', cell: ({ row }) => <button className="icon-button" aria-label={`Save ${row.original.player.name}`}
        aria-pressed={saved.watchlist.includes(row.original.player.id)} onClick={() => toggleWatch(row.original.player.id)}><Star size={18} fill={saved.watchlist.includes(row.original.player.id) ? 'currentColor' : 'none'} /></button> }),
    ]
  }, [comparison, saved.watchlist])
  const visible = useMemo(() => (results.data?.recommendations || []).filter(item =>
    item.player.name.toLowerCase().includes(search.toLowerCase()) && (!watchOnly || saved.watchlist.includes(item.player.id))),
    [results.data, search, watchOnly, saved.watchlist])
  const table = useReactTable({ data: visible, columns, getCoreRowModel: getCoreRowModel() })
  const componentWeight = (key: string, value: number) => setBrief({ ...brief, weights: { ...brief.weights, [key]: value } })
  const constraint = (key: string, value: unknown) => setBrief({ ...brief, constraints: {
    min_age: 15, max_age: 40, min_minutes: 450, foot: null, attributes: [], ...brief.constraints, [key]: value,
  } })
  const importSaved = async (file?: File) => { if (!file) return
    try { if (file.size > 2_000_000) throw new Error('Choose a Scout export smaller than 2 MB.')
      setSaved(validateSaved(JSON.parse(await file.text()))); setStorageWritable(true); setNotice('Watchlist and notes imported into this browser.')
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Could not import this file.') }
  }
  return <div className="app-shell">
    <a href="#workspace" className="skip-link">Skip to workbench</a>
    <header className="app-header"><Link className="wordmark" to="/" aria-label="Scout home">Scout<span className="wordmark-dot" /></Link><Link to="/">Squad Studio</Link>
      <p>Football recruitment workbench</p><div className="header-status"><span className="status-dot" />{release ? `${release.season} cohort` : 'Connecting to data'}</div></header>
    {release?.kind === 'synthetic' && <div className="demo-banner"><CircleHelp size={17} /><span><strong>Synthetic demonstration.</strong> Every player, club and statistic is fictional. Real-data access and publication rights are pending validation.</span></div>}
    {params.get('from') === 'squad' && <div className="demo-banner">Explore role candidates — demo. The requested role is carried over. Actual Liverpool profile matching is unavailable; these candidates are fictional.</div>}
    <Tabs.Root value={tab} onValueChange={setTab}>
      <div className="navigation"><Tabs.List aria-label="Workbench sections"><Tabs.Trigger value="recruitment">Recruitment</Tabs.Trigger>
        <Tabs.Trigger value="compare">Compare <span className="count">{comparison.length}</span></Tabs.Trigger><Tabs.Trigger value="squad">Squad scenarios</Tabs.Trigger><Tabs.Trigger value="data">Data & methods</Tabs.Trigger></Tabs.List>
        <button className="text-button" disabled={!results.data} onClick={() => exportJson('scout-recruitment.json', { ...results.data, saved, exported_at: new Date().toISOString() })}><ArrowDownToLine size={16} /> Export evidence</button></div>
      <main id="workspace">
        {notice && <div className="notice" role="status"><span>{notice}</span><button className="icon-button" aria-label="Dismiss notice" onClick={() => setNotice('')}><X size={18} /></button></div>}
        {(datasets.error || teams.error || roles.error) && <Alert>{datasets.error?.message || teams.error?.message || roles.error?.message} <button className="text-button" onClick={() => { datasets.refetch(); teams.refetch(); roles.refetch() }}>Retry connection</button></Alert>}
        {!release && datasets.isPending && <p className="connection-state" role="status">Connecting to the recruitment dataset… A sleeping demo service can take a moment to start.</p>}
        <Tabs.Content value="recruitment" className="workbench">
          <form className="brief-pane" onSubmit={event => { event.preventDefault(); setSubmitted(structuredClone(brief)); setSelected(null) }}>
            <div className="pane-heading"><h1>Recruitment brief</h1><SlidersHorizontal size={20} /></div><p className="muted">Define the role. Make the trade-offs explicit.</p>
            <label className="field">Recruiting for<select aria-label="Recruiting for" value={brief.team_id || ''} onChange={event => setBrief({ ...brief, team_id: event.target.value, replacement_id: null })}><option value="" disabled>Select a team</option>{teams.data?.map(team => <option key={team.id} value={team.id}>{team.name} · {team.league}</option>)}</select></label>
            <label className="field">Role family<select aria-label="Role family" value={brief.role} onChange={event => { setBrief({ ...brief, role: event.target.value as Role, preferences: {}, intended_style: {}, replacement_id: null }); setSelected(null) }}>{roles.data?.map(role => <option key={role.id} value={role.id}>{role.label}</option>)}</select></label>
            <label className="field">Player to replace<select aria-label="Player to replace" value={brief.replacement_id || ''} onChange={event => setBrief({ ...brief, replacement_id: event.target.value || null })}><option value="">New squad need</option>{roster.data?.players.filter(player => player.roles.includes(brief.role)).map(player => <option value={player.id} key={player.id}>{player.name}</option>)}</select></label>
            <details className="brief-section"><summary>Coach's words <ChevronDown size={16} /></summary><label className="field"><span className="sr-only">Coach request</span><textarea maxLength={3000} value={text} onChange={event => setText(event.target.value)} /></label>
              <button type="button" className="secondary" disabled={interpretation.isPending} onClick={() => interpretation.mutate()}>{interpretation.isPending ? 'Interpreting…' : 'Suggest editable criteria'}</button>{interpretation.error && <Alert>{interpretation.error.message}</Alert>}</details>
            <h2 className="form-subheading">Requirements</h2>
            <div className="field-pair"><label className="field">Min age<input type="number" min={15} max={55} value={brief.constraints?.min_age ?? 15} onChange={event => constraint('min_age', Number(event.target.value))} /></label><label className="field">Max age<input type="number" min={15} max={55} value={brief.constraints?.max_age ?? 40} onChange={event => constraint('max_age', Number(event.target.value))} /></label></div>
            <label className="field">Minimum minutes<input type="number" min={0} max={15000} step={90} value={brief.constraints?.min_minutes ?? 450} onChange={event => constraint('min_minutes', Number(event.target.value))} /></label>
            <label className="field">Required foot<select aria-label="Required foot" value={brief.constraints?.foot || ''} onChange={event => constraint('foot', event.target.value || null)}><option value="">Any / no hard constraint</option><option value="left">Left</option><option value="right">Right</option><option value="both">Both</option></select></label>
            <label className="check-field"><input type="checkbox" checked={brief.include_verification_required ?? true} onChange={event => setBrief({ ...brief, include_verification_required: event.target.checked })} />Include players who need verification</label>
            {(brief.constraints?.attributes || []).length > 0 && <p className="small caution">To verify: {brief.constraints!.attributes!.map(item => item.replaceAll('_', ' ')).join(', ')}</p>}
            <details className="brief-section"><summary>Intended team style</summary><p className="muted small">Blank uses available team observations. Entered targets define your intended style and are labelled as manual assumptions.</p>
              {activeRole?.style_metrics.map(key => <label className="field" key={key}>{labels[key] || key}<input type="number" min={0}
                max={key.endsWith('pct') || key.endsWith('share') ? 1 : 10000} step="any" value={brief.intended_style?.[key] ?? ''}
                onChange={event => { const next = { ...brief.intended_style }; if (event.target.value === '') delete next[key];
                  else next[key] = Number(event.target.value); setBrief({ ...brief, intended_style: next }) }} /></label>)}
            </details>
            <details className="brief-section" open><summary>Ranking priorities <ChevronDown size={16} /></summary>{Object.entries(componentLabels).map(([key, label]) => <label className="range-field" key={key}><span>{label}</span><strong>{number(brief.weights?.[key as keyof Brief['weights']] ?? 0, 1)}</strong><input type="range" min={0} max={3} step={0.25} value={brief.weights?.[key as keyof Brief['weights']] ?? 0} onChange={event => componentWeight(key, Number(event.target.value))} /></label>)}</details>
            <button className="primary" type="submit" disabled={!release || results.isFetching}>Find candidates <ArrowRight size={18} /></button>
            <p className="muted small">Unavailable components are omitted. Sparse evidence reduces the overall score.</p>
          </form>
          <section className="candidate-pane" aria-label="Candidate results">
            <div className="results-heading"><div><h2>Candidate shortlist</h2><p className="muted">A starting point for scouting, with the evidence in view.</p></div><span className="result-count">{visible.length} players</span></div>
            <div className="results-tools"><label className="search-field"><Search size={18} /><input aria-label="Search candidates" placeholder="Search candidates" value={search} onChange={event => setSearch(event.target.value)} /></label><button className={`secondary ${watchOnly ? 'selected-control' : ''}`} aria-pressed={watchOnly} onClick={() => setWatchOnly(!watchOnly)}><Star size={16} /> Watchlist ({saved.watchlist.length})</button></div>
            {dirty && results.data && <p className="stale-result" role="status">Brief changed. Select “Find candidates” to update this shortlist.</p>}
            {results.isFetching && <p role="status" className="loading-line">Evaluating role profiles and available evidence…</p>}
            {results.error && <Alert>{results.error.message}</Alert>}
            <div className="table-scroll"><table className="candidate-table"><thead>{table.getHeaderGroups().map(group => <tr key={group.id}>{group.headers.map(header => <th key={header.id} scope="col">{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.map((row, index) => <tr key={row.id} className={selected?.player.id === row.original.player.id ? 'selected-row' : ''}>{row.getVisibleCells().map(cell => <td key={cell.id}>{cell.column.id === 'player' && <span className="row-index">{String(index + 1).padStart(2, '0')}</span>}{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody></table></div>
            {!results.isFetching && results.data && visible.length === 0 && <div className="empty-state"><Search size={28} /><h3>No candidates match this view</h3><p>Relax a requirement, enable verification, or clear your search and watchlist filter.</p></div>}
            <div className="ledger-footer"><span>{results.data?.brief.role} profiles · {results.data?.release.season}</span><button className="text-button" onClick={() => setTab('compare')} disabled={!comparison.length}>Compare selected ({comparison.length}/4) <ArrowRight size={16} /></button></div>
            <p className="small muted">Quality uses role peers within each league. Scores do not establish equivalent talent across leagues.</p>
          </section>
          {selected && <CandidateDetail candidate={selected} labels={labels} note={saved.notes[selected.player.id] || ''} close={() => setSelected(null)} setNote={note => setSaved(previous => ({ ...previous, notes: { ...previous.notes, [selected.player.id]: note } }))} />}
        </Tabs.Content>
        <Tabs.Content value="compare" className="full-pane"><div className="section-toolbar"><div><h1>Compare the evidence</h1><p className="muted">Up to four profiles, with missing values kept visible.</p></div><button className="secondary" onClick={() => exportJson('scout-comparison.json', { release, candidates: comparison })} disabled={!comparison.length}><ArrowDownToLine size={16} /> Export comparison</button></div>
          {comparison.length ? <div className="table-scroll"><table className="plain-table comparison-table"><thead><tr><th>Evidence</th>{comparison.map(item => <th key={item.player.id}>{item.player.name}<button className="icon-button" aria-label={`Remove ${item.player.name}`} onClick={() => toggleCompare(item)}><X size={16} /></button><span className="muted small">{item.player.league} · {item.player.roles.join(', ')}</span></th>)}</tr></thead><tbody>
            {Object.entries(componentLabels).map(([key, label]) => <tr key={key}><th>{label}</th>{comparison.map(item => <td key={item.player.id}><Meter value={item.components[key]} label={label} /></td>)}</tr>)}
            {[...new Set(comparison.flatMap(item => Object.keys(item.profile.values)))].map(key => <tr key={key}><th>{labels[key] || key}</th>{comparison.map(item => <td key={item.player.id}>{item.profile.values[key] == null ? 'Unavailable' : number(item.profile.values[key], 2)}<span className="muted small">{item.player.metrics[key]?.evidence || 'No measurement'}</span></td>)}</tr>)}
            <tr><th>Scouting questions</th>{comparison.map(item => <td key={item.player.id}>{item.unknowns.join('; ') || 'No unresolved hard constraints'}</td>)}</tr>
          </tbody></table></div> : <div className="empty-state"><h2>Select players from the shortlist</h2><p>Use the comparison checkboxes beside a player, then return here.</p><button className="secondary" onClick={() => setTab('recruitment')}>Return to recruitment</button></div>}
        </Tabs.Content>
        <Tabs.Content value="squad"><ScenarioPanel teams={teams.data || []} players={results.data?.recommendations || []} release={release} /></Tabs.Content>
        <Tabs.Content value="data" className="full-pane data-pane"><h1>Know the evidence behind the shortlist</h1><p className="lead">Every result belongs to a specific data release. Unavailable evidence remains unavailable.</p>
          {release && <><dl className="release-facts"><dt>Release</dt><dd>{release.id}</dd><dt>Data kind</dt><dd>{release.kind}</dd><dt>Season</dt><dd>{release.season}</dd><dt>Source</dt><dd>{release.source}</dd><dt>Published snapshot</dt><dd>{release.created_at ? new Date(release.created_at).toLocaleString() : 'Unavailable'}</dd><dt>Feature version</dt><dd>{release.feature_version}</dd><dt>Scoring version</dt><dd>{release.scoring_version}</dd><dt>Model version</dt><dd>{release.model_version}</dd></dl><h2>Coverage and limitations</h2><ul className="explanations">{release.limitations.map(item => <li key={item}>{item}</li>)}</ul></>}
          <h2>How to read the scores</h2><p>Style compares robustly scaled role metrics. Quality combines league-relative peer percentiles after shrinking count-based rates towards role priors. Team fit uses the available team targets. Replacement fit describes the measured profile preserved. Evidence is the share of supported role metrics available.</p>
          <p>Posterior intervals rely on simplified count models. They omit opponent difficulty, team instructions and match-to-match dependence. Synthetic demonstrations test software behaviour; they do not validate football recommendations.</p>
          <h2>Watchlist and notes</h2><p>Stored in this browser. Export a copy before switching devices or clearing browser storage.</p><div className="section-toolbar"><button className="secondary" onClick={() => exportJson('scout-watchlist.json', { saved, release_id: release?.id })}><ArrowDownToLine size={16} /> Export watchlist</button><label className="secondary file-control">Import watchlist<input aria-label="Import watchlist" type="file" accept="application/json,.json" onChange={event => importSaved(event.target.files?.[0])} /></label><button className="text-button" onClick={() => { setSaved(emptySaved); setStorageWritable(true); setNotice('Local watchlist and notes cleared.') }}>Clear local notes</button></div>
          <h2>Real-data release gate</h2><p>Current candidate publication requires verified access to all five leagues, a common completed season from 2024/25, resolved role coverage and documented display permission. A synthetic release never satisfies this gate.</p>
        </Tabs.Content>
      </main>
    </Tabs.Root>
    <footer className="app-footer"><span>Scout · Evidence before certainty</span><span>{release?.id || 'No active release'} <Check size={14} aria-hidden="true" /></span></footer>
  </div>
}
