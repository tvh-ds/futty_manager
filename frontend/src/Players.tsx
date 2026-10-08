import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router'
import { ArrowLeft, ArrowRight, ArrowUpRight, Info, Search, X } from 'lucide-react'
import { api, type CardPlayer, type CataloguePage, type CatalogueMetadata, type CatalogueDetail } from './api'
import { AbilityView } from './AbilityView'
import { PlayerCardFace } from './PlayerCardFace'
import './squad.css'
import './players.css'

function EvidenceDrawer({ identity, players, close }: { identity: string; players: CardPlayer[]; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const detail = useQuery({ queryKey: ['catalogue-detail', identity], queryFn: () => api<CatalogueDetail>(`/catalogue/players/${identity}`) })
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close() }, [])
  const dismiss = () => { dialog.current?.close(); close() }
  const p = detail.data
  return <dialog ref={dialog} className="ss-dialog pl-detail" aria-label="Player attributes" onCancel={e => { e.preventDefault(); dismiss() }}>
    <div className="ss-dialog-inner"><header><h2>{p?.name || 'Player attributes'}</h2><button autoFocus onClick={dismiss} aria-label="Close player attributes"><X size={22}/></button></header>
      {detail.isError ? <div role="alert"><p>{detail.error.message}</p><button onClick={() => detail.refetch()}>Retry attributes</button></div> : !p ? <p role="status">Loading sourced attributes…</p> : <>
        <p className="ss-muted">{p.team} · {p.league} · {p.position} · {p.minutes.toLocaleString()} minutes</p>

        <AbilityView player={p} players={players}/>
        <details className="ss-methods"><summary>Full attributes list</summary><h3>Observed attributes</h3><p className="ss-muted">{p.numerical_features}/{p.defined_features} numerical features. Numerator and exposure remain from the same provider.</p>
        <div className="pl-feature-table"><table><thead><tr><th>Feature</th><th>Value</th><th>Evidence</th></tr></thead><tbody>{p.features.map(f => <tr key={f.key}><th scope="row">{f.label}<small>{f.unit}</small></th><td>{f.value == null ? f.status === 'not_applicable_zero_attempts' ? 'N/A' : '—' : f.value.toFixed(2)}</td><td><a href={f.source_url} target="_blank" rel="noreferrer">{f.provider}</a><small>{f.numerator ?? '—'} / {f.denominator ?? '—'}</small></td></tr>)}</tbody></table></div></details>
        <details className="ss-methods"><summary>Sources & mapping</summary><p>{p.season} · {p.mapping_status} identity · {[...new Set(p.sources.map(source => String(source.provider)))].join(' / ')}.</p><p>Historical snapshot; source definitions can differ. Complete provenance is included in the evidence export.</p></details>
      </>}
    </div>
  </dialog>
}

function CatalogueCard({ player, open }: { player: CardPlayer; open: () => void }) {
  const scores = Object.fromEntries(player.abilities.map(a => [a.name, a.rating]))
  return <article className="pl-player">
    <button className="pl-card-button" onClick={open} aria-label={`View attributes for ${player.name}`}>
      <PlayerCardFace name={player.name} position={player.position} rating={player.overall} photo={player.portrait_url} country={player.country_label} club={player.team} clubLogo={player.club_logo_url} scores={scores} abilityLayout={player.abilities} caption={'2025/26 · OBSERVED POSITION PROFILE'}/>
    </button>
    <div className="pl-player-meta"><strong title={player.team}>{player.team}</strong><span>{player.league} <i>·</i> {player.minutes.toLocaleString()} min</span><button onClick={open}>Attributes <ArrowUpRight size={13}/></button></div>
  </article>
}

export default function Players() {
  const [params, setParams] = useSearchParams()
  const paramsRef = useRef(params)
  useEffect(() => { paramsRef.current = params }, [params])
  const [search, setSearch] = useState(params.get('name') || '')
  const [selected, setSelected] = useState<string | null>(null)
  const metadata = useQuery({ queryKey: ['player-catalogue'], queryFn: () => api<CatalogueMetadata>('/catalogue') })
  const offset = Math.max(0, Number(params.get('offset')) || 0)
  const league = params.get('league') || ''
  function filter(key: string, value: string) {
    const next = new URLSearchParams(paramsRef.current)
    value ? next.set(key, value) : next.delete(key)
    next.delete('offset')
    if (key === 'league') next.delete('team')
    paramsRef.current = next
    setParams(next)
  }
  function clearFilters() { setSearch(''); paramsRef.current = new URLSearchParams(); setParams({}) }
  useEffect(() => { document.title = 'Scout · Players' }, [])
  useEffect(() => { const timer = setTimeout(() => { if (search !== (params.get('name') || '')) filter('name', search) }, 250); return () => clearTimeout(timer) }, [search, params])
  const request = new URLSearchParams(params); request.set('limit', '24')
  const catalogue = useQuery({ queryKey: ['player-cards', request.toString()], queryFn: () => api<CataloguePage>(`/catalogue/players?${request}`), retry: false })
  const teams = metadata.data ? league ? metadata.data.teams[league] || [] : [...new Set(Object.values(metadata.data.teams).flat())].sort() : []
  function page(nextOffset: number) { setParams(previous => { const next = new URLSearchParams(previous); next.set('offset', String(nextOffset)); return next }); window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }) }
  return <div className="squad-studio players-page">
    <a className="skip-link" href="#player-catalogue">Skip to player cards</a>
    <header className="ss-header"><Link className="ss-brand" to="/">SCOUT<span> / PLAYER DATABASE</span></Link><nav aria-label="Scout navigation"><Link to="/">Squad</Link><Link className="active" to="/players">Players</Link><Link to="/scout">Recruitment <ArrowUpRight size={13}/></Link></nav><span className="ss-snapshot">PERFORMANCE <b>2025/26</b></span></header>
    <main id="player-catalogue">
      <div className="pl-heading"><div><h1>Players</h1><p>Five leagues. Every imported profile, with its evidence in view.</p></div><p className="pl-squad-link">Your squad <Link to="/">Liverpool 2026/27 <ArrowUpRight size={14}/></Link></p></div>
      <div className="pl-filters" aria-label="Player filters">
        <label className="pl-search"><span>Search players</span><div><Search size={17}/><input type="search" placeholder="Name, e.g. Cody Gakpo" value={search} onChange={e => setSearch(e.target.value)}/></div></label>
        <label><span>League</span><select value={league} onChange={e => filter('league', e.target.value)}><option value="">All leagues</option>{metadata.data?.leagues.map(l => <option key={l}>{l}</option>)}</select></label>
        <label><span>Team · 2025/26</span><select value={params.get('team') || ''} onChange={e => filter('team', e.target.value)}><option value="">All teams</option>{teams.map(t => <option key={t}>{t}</option>)}</select></label>
        <label><span>Position</span><select value={params.get('position') || ''} onChange={e => filter('position', e.target.value)}><option value="">All positions</option>{metadata.data?.positions.map(p => <option key={p}>{p}</option>)}</select></label>
        <label><span>OVR min</span><input type="number" min="0" placeholder="Any" value={params.get('minimum') || ''} onChange={e => filter('minimum', e.target.value)}/></label>
        <label><span>OVR max</span><input type="number" min="0" placeholder="Any" value={params.get('maximum') || ''} onChange={e => filter('maximum', e.target.value)}/></label>
        <label><span>Rating availability</span><select value={params.get('rating_status') || 'all'} onChange={e => filter('rating_status', e.target.value)}><option value="all">All profiles</option><option value="rated">Rated only</option><option value="unrated">OVR unavailable</option></select></label>
        <button className="pl-clear" onClick={clearFilters}>Clear filters</button>
      </div>
      <div className="pl-results-bar"><p role="status">{catalogue.isFetching ? 'Loading profiles…' : catalogue.data ? `${catalogue.data.total.toLocaleString()} matching profiles` : 'Player catalogue'}</p><label>Sort <select value={params.get('sort') || 'name'} onChange={e => filter('sort', e.target.value)}><option value="name">Name A–Z</option><option value="rating">Highest OVR</option></select></label></div>
      <p className="pl-evidence-notice"><Info size={16}/><span>Real 2025/26 snapshots. Six abilities use position-specific models. Ratings require compatible evidence and peers. “—” means unavailable, never zero. Unresolved source identities may appear separately.</span></p>
      {catalogue.isError || metadata.isError ? <div className="pl-state" role="alert"><h2>Players could not be loaded</h2><p>{catalogue.error?.message || metadata.error?.message}</p><button onClick={() => { catalogue.refetch(); metadata.refetch() }}>Retry connection</button></div>
        : !catalogue.data ? <div className="pl-loading" aria-busy="true" role="status">Preparing the player catalogue…</div>
        : !catalogue.data.items.length ? <div className="pl-state"><h2>No matching players</h2><p>Try a different team or wider filters. OVR requires all six calibrated abilities, at least 900 minutes and enough compatible top-five-league peers.</p><button onClick={clearFilters}>Reset filters</button></div>
        : <div className="pl-card-grid" aria-busy={catalogue.isFetching}>{catalogue.data.items.map(p => <CatalogueCard key={p.id} player={p} open={() => setSelected(p.id)}/>)}</div>}
      {catalogue.data && catalogue.data.total > 24 && <nav className="pl-pagination" aria-label="Player pages"><button disabled={offset === 0 || catalogue.isFetching} onClick={() => page(Math.max(0, offset - 24))}><ArrowLeft size={16}/> Previous</button><span>Page {Math.floor(offset / 24) + 1} of {Math.ceil(catalogue.data.total / 24)}</span><button disabled={offset + 24 >= catalogue.data.total || catalogue.isFetching} onClick={() => page(offset + 24)}>Next <ArrowRight size={16}/></button></nav>}
      <footer className="ss-footer">Source-backed attributes · strict missingness · current lineups available for Liverpool only</footer>
    </main>
    {selected && <EvidenceDrawer key={selected} identity={selected} players={catalogue.data?.items || []} close={() => setSelected(null)}/>}
  </div>
}
