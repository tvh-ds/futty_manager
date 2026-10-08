import { useId, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Flag, Shield } from 'lucide-react'
import './playerCards.css'

const strikerAbilities = [
  ['Finishing', 'FIN'], ['Box Threat', 'BOX'], ['Link-Up / Creation', 'LNK'],
  ['Carrying / 1v1', 'CAR'], ['Physicality', 'PHY'], ['Defensive Activity', 'DEF'],
]
const abilityAbbreviations: Record<string,string> = { 'Chance Creation':'CRE', Scoring:'SCO', 'Penalty-Area Threat':'BOX', 'Ball Retention':'RET', 'Defensive Support':'DEF', 'Ball Progression':'PRO', 'Retention / Circulation':'RET', 'Ball Recovery':'REC', 'Duel Contribution':'DUE', 'Goal Threat':'SCO', 'Combination / Retention':'LNK', 'Screening / Recovery':'SCR', 'Ground Duels':'DUE', 'Build-Up / Progression':'PRO', 'Aerial Contribution':'AIR', Discipline:'DIS', 'Wide Creation':'CRE', 'Carrying / Progression':'CAR', 'Ground Defending':'GRD', 'Aerial Defending':'AIR', 'Reading / Interventions':'INT', 'Build-Up Passing':'PAS', 'Carrying / Control':'CAR', 'Recovery / Cover':'REC', 'Shot Stopping':'STP', 'Claims / Aerial Control':'CLM', 'Sweeping / Interventions':'SWP', 'Build-Up Distribution':'BLD', 'Long Distribution':'LNG', 'Ball Security':'SEC', ...Object.fromEntries(strikerAbilities) }
export function PlayerPortrait({ url, name, number }: { url?: string | null; name: string; number?: number }) {
  const [failed, setFailed] = useState(false)
  return url && !failed ? <img className="pc-portrait" src={url} alt={name} loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => setFailed(true)} />
    : <div className="pc-portrait pc-fallback" aria-label={`Portrait unavailable for ${name}`}>
      <svg viewBox="0 0 100 110" aria-hidden="true"><path d="M32 12 16 20 3 45 20 53 25 41 25 100 75 100 75 41 80 53 97 45 84 20 68 12 60 17 40 17Z"/><path className="pc-seam" d="M32 12Q50 38 68 12"/><text x="50" y="72" textAnchor="middle">{number ?? name.split(' ').map(n => n[0]).slice(0, 2).join('')}</text></svg>
    </div>
}

const countryCodes: Record<string, string> = { England: 'gb-eng', Scotland: 'gb-sct', Wales: 'gb-wls', Brazil: 'br', Georgia: 'ge', Czechia: 'cz', France: 'fr', Netherlands: 'nl', Hungary: 'hu', Argentina: 'ar', Egypt: 'eg', Italy: 'it', Spain: 'es', Germany: 'de', Portugal: 'pt', Japan: 'jp', NorthernIreland: 'gb-nir', 'Northern Ireland': 'gb-nir', 'Republic of Ireland': 'ie', Ireland: 'ie', Sweden: 'se', Denmark: 'dk', Norway: 'no', Poland: 'pl', Belgium: 'be', Colombia: 'co', Uruguay: 'uy', Senegal: 'sn', 'Ivory Coast': 'ci', Switzerland: 'ch' }

export function ratingTier(rating?: number | null) {
  return rating == null ? 'unrated' : rating < 50 ? 'graphite' : rating < 70 ? 'bronze' : rating < 80 ? 'silver' : rating < 90 ? 'gold' : 'elite'
}

export function ClubBadge({ url, name }: { url?: string | null; name: string }) {
  const [failed, setFailed] = useState(false)
  return url && !failed ? <img src={url} className="pc-club-logo" alt={`${name} crest`} loading="lazy" onError={() => setFailed(true)}/> : <Shield className="pc-club-unknown" size={22} aria-label={`Club crest unavailable: ${name}`}/>
}

export function PlayerCardFace({ name, shortName, position, rating, photo, scores, compact = false, pending = false, number, caption, country, club, clubLogo, children, finish = 'stadium', abilityLayout, ratingDescription }: {
  name: string; shortName?: string; position: string; rating?: number | null; photo?: string | null;
  scores: Record<string, number | null>; compact?: boolean; pending?: boolean; number?: number; caption?: string; country?: string | null; club?: string; clubLogo?: string | null; children?: ReactNode; finish?: 'metal' | 'stadium'; abilityLayout?: {name:string; abbreviation:string}[]; ratingDescription?: string
}) {
  const id = useId().replace(/:/g, '')
  const code = country ? countryCodes[country] : undefined
  const digits = rating == null ? 1 : String(Math.round(rating)).length
  const cardName = shortName || name
  const abilities = abilityLayout?.map(a=>[a.name,a.abbreviation]) ?? (Object.keys(scores).length === 6 ? Object.keys(scores).map(n=>[n,abilityAbbreviations[n] ?? n.slice(0,3).toUpperCase()]) : strikerAbilities)
  const striker = abilities.every(([n])=>strikerAbilities.some(([s])=>s===n))
  const style = { '--pc-glow': rating == null || pending ? 0 : Math.max(0, Math.min(.22, (rating - 40) / 400)),
    '--pc-ovr-font': `${Math.min(22, 48 / digits)}cqw`,
    '--pc-name-font': `${Math.min(9, 115 / cardName.length)}cqw`,
  } as CSSProperties
  return <div className={`pc-face pc-tier-${ratingTier(rating)} ${compact ? 'pc-compact' : ''} ${finish === 'stadium' ? 'pc-stadium' : ''}`} aria-description={caption} style={style}>
    <svg className="pc-frame" viewBox="0 0 220 310" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={`${id}-metal`} x1="0" y1="0" x2="1" y2=".8"><stop stopColor="var(--pc-light)"/><stop offset=".42" stopColor="var(--pc-body)"/><stop offset=".73" stopColor="var(--pc-light)"/><stop offset="1" stopColor="var(--pc-deep)"/></linearGradient>
        <linearGradient id={`${id}-ribbon`} x1="0" y1="0" x2="1" y2=".2"><stop stopColor="var(--pc-light)"/><stop offset="1" stopColor="var(--pc-body)"/></linearGradient>
        <pattern id={`${id}-grain`} width="18" height="18" patternUnits="userSpaceOnUse"><path d="m7 6 4 4m-4 0 4-4" stroke="var(--pc-ink)" strokeWidth=".45" opacity=".12"/></pattern>
        <clipPath id={`${id}-clip`}><path d="M8 45Q31 44 35 21Q110 -10 185 21Q189 44 212 45V263Q212 275 197 280Q126 298 110 310Q94 298 23 280Q8 275 8 263Z"/></clipPath>
      </defs>
      <g clipPath={`url(#${id}-clip)`}>
        <rect width="220" height="310" fill={`url(#${id}-metal)`}/>
        <rect width="220" height="195" fill={`url(#${id}-grain)`}/>
        <path d="M-20 174Q78 96 243 14L243 35Q79 122-20 194Z" fill="var(--pc-light)" opacity=".65"/>
        <path d="M-10 201Q107 115 237 58L237 68Q119 125-10 211Z" fill="var(--pc-ink)" opacity=".12"/>
        <path d="M-10 212Q60 160 127 152Q215 139 234 110V138Q209 164 127 168Q57 174-10 230Z" fill="var(--pc-light)" opacity=".65"/>
        <path d="M17 191Q102 119 219 99" fill="none" stroke="var(--pc-light)" strokeWidth="1.4" opacity=".6"/>
        <rect y="182" width="220" height="128" fill={`url(#${id}-ribbon)`}/>
        <path d="M8 182H212" stroke="var(--pc-light)" strokeWidth="1" opacity=".6"/>
      </g>
    </svg>
    <div className="pc-top"><strong title={pending ? 'Recalculating' : ratingDescription ?? (rating == null ? 'OVR unavailable: incomplete evidence or position model pending' : 'Observed ability model; provisional scoring weights')}>{pending ? '···' : rating == null ? '—' : Math.round(rating)}<small>OVR</small></strong><span>{position}</span><div className="pc-identity-marks">{code ? <img className="fi pc-flag" src={`/flags/${code}.svg`} alt={`${country} flag`} aria-label={`${country} flag`} title={country || undefined}/> : <Flag size={20} aria-label="Nationality unavailable"/>}<ClubBadge key={clubLogo || club} url={clubLogo} name={club || 'Club unknown'}/></div></div>
    <PlayerPortrait key={photo || name} url={photo} name={name} number={number}/>
    <div className="pc-name" title={name}>{cardName}</div>
    <div className="pc-abilities" aria-label={`Six ${striker ? 'striker' : 'position'} abilities for ${name}`}>
      {abilities.map(([label, abbreviation]) => <div key={label} title={`${label}: ${scores[label] == null ? 'unavailable' : scores[label]?.toFixed(1)}. ${striker ? 'ST profile only.' : 'Observed position profile.'}`}><b style={{fontSize:`min(8cqw, 4.3cqh, ${24 / String(Math.round(scores[label] ?? 0)).length}cqw)`}}>{pending ? '·' : scores[label] == null ? '—' : Math.round(scores[label]!)}</b><span>{abbreviation}</span></div>)}
    </div>
    {children}
  </div>
}
