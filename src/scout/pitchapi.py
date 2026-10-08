"""Authenticated, bounded PitchAPI collection; missing evidence never becomes zero."""
import hashlib
import json
import math
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scout.striker_features import FEATURES, derive

BASE = 'https://api.pitchapi.dev/v1'
VERSION = 'pitchapi-measurements-v1'
LEAGUES = {'England': ('ENG', 'Premier League', 380), 'Spain': ('ESP', 'LaLiga', 380),
           'Germany': ('GER', 'Bundesliga', 306), 'Italy': ('ITA', 'Serie A', 380),
           'France': ('FRA', 'Ligue 1', 306)}
ADVANCED = {
    'passes_attempted': ('passing', 'passes'), 'passes_into_penalty_area': ('passing', 'passes_into_box'),
    'through_balls': ('passing', 'through_balls'), 'key_passes': ('passing', 'key_passes'),
    'sca': ('creation', 'sca'), 'take_ons_attempted': ('carrying', 'take_ons'),
    'take_ons_successful': ('carrying', 'take_ons_won'),
    'carries_into_penalty_area': ('carrying', 'carries_into_box'),
    'carries_into_final_third': ('carrying', 'carries_into_final_third'),
    'progressive_carry_distance': ('carrying', 'progressive_carry_distance'),
    'miscontrols': ('carrying', 'miscontrols'), 'dispossessed': ('carrying', 'dispossessed'),
    'aerial_duels_won': ('defending', 'aerials_won'), 'interceptions': ('defending', 'interceptions'),
    'blocks': ('defending', 'blocks')}
# Stable source keys only; never map localized display labels or rounded percentages.
STAT_KEYS = {'minutes': 'minutes_played', 'assists': 'assists', 'xa': 'expected_assists',
             'recoveries': 'recoveries', 'fouls_won': 'was_fouled',
             'touches_opposition_box': 'touches_opp_box', 'offsides': 'Offsides',
             'duels_won': 'duel_won', '_duels_lost': 'duel_lost',
             'shots_on_target': 'ShotsOnTarget', 'blocks': 'shot_blocks',
             'interceptions': 'interceptions', 'dispossessed': 'dispossessed'}
FRACTIONS = {'accurate_passes': ('passes_completed', 'passes_attempted'),
             'duels_won': ('duels_won', 'duels_attempted'),
             'aerials_won': ('aerial_duels_won', 'aerial_duels_attempted')}
LIMITATIONS = [
    'Inferred carries: movement between consecutive team actions, credited to the next actor.',
    'SCA stops at possession boundaries; not identical to the original FBref definition.',
    'Advanced interceptions include blocked passes; blocks are shot blocks.',
    'Key passes include assists; xAG is never substituted for xA.',
    'Attacking-third tackles are unavailable; optional match-stat fields remain unknown when absent.',
    'Base appearance minutes take precedence over advanced minutes, which can include stoppage time.',
    'Missing any appearance-level measurement makes its season total unavailable.']


def identifier(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r'_[A-Za-z0-9]{6}', value):
        raise ValueError('Invalid provider identifier')
    return value


def numeric(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Invalid provider measurement')
    return float(value)


def strict_json(body):
    def reject(value):
        raise ValueError('Non-finite JSON')
    return json.loads(body, parse_constant=reject)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


class RequestBudgetReached(RuntimeError):
    pass


class PitchAPI:
    def __init__(self, key, root: Path, max_requests=200, client=None, sleep=time.sleep):
        if not isinstance(key, str) or not key or '\n' in key or '\r' in key:
            raise ValueError('PitchAPI credential missing or invalid')
        if isinstance(max_requests, bool) or not isinstance(max_requests, int) or not 1 <= max_requests <= 10000:
            raise ValueError('Request budget must be 1–10000')
        self._key, self.root, self.maximum = key, root, max_requests
        self.client = client or httpx.Client(timeout=25, follow_redirects=False)
        self.owned, self.sleep, self.requests = client is None, sleep, 0

    def close(self):
        if self.owned:
            self.client.close()

    def get(self, path, params=None, optional=False):
        if not re.fullmatch(r'/leagues(?:/l_[A-Za-z0-9]{6}/matches)?|/players/p_[A-Za-z0-9]{6}|/matches/m_[A-Za-z0-9]{6}/(?:players(?:/(?:halves|p_[A-Za-z0-9]{6}(?:/halves)?))?|shots|advanced/players)', path):
            raise ValueError('Unsupported source path')
        if params and (set(params) != {'season'} or not re.fullmatch(r'20\d{2}/20\d{2}', params['season'])):
            raise ValueError('Invalid source query')
        url = BASE + path
        token = hashlib.sha256(json.dumps([path, params], sort_keys=True).encode()).hexdigest()
        file = self.root / (token + '.json')
        if file.exists():
            if file.stat().st_size > 40_000_000:
                raise ValueError('Cached snapshot exceeds size limit')
            saved = strict_json(file.read_bytes())
            body = json.dumps(saved['document'], sort_keys=True, allow_nan=False).encode()
            if saved.get('url') != url or saved.get('params') != params or saved.get('sha256') != hashlib.sha256(body).hexdigest():
                raise ValueError('Cached snapshot checksum mismatch')
            return saved
        for attempt in range(3):
            if self.requests >= self.maximum:
                raise RequestBudgetReached('Request budget exhausted; cached progress retained')
            self.requests += 1
            with self.client.stream('GET', url, params=params, headers={'X-API-KEY': self._key},
                                    follow_redirects=False, timeout=25) as response:
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == 2:
                        raise ValueError('Provider unavailable after bounded retries')
                    delay = response.headers.get('Retry-After', '')
                    self.sleep(min(float(delay), 5) if delay.isdigit() else attempt + 1)
                    continue
                body = bytearray()
                for chunk in response.iter_bytes():
                    if len(body) + len(chunk) > 20_000_000:
                        raise ValueError('Source response exceeds 20 MB')
                    body.extend(chunk)
                document = strict_json(body)
                unavailable = (optional and response.status_code == 404 and isinstance(document, dict)
                    and isinstance(document.get('error'), dict)
                    and document['error'].get('code') in (
                        {'HALVES_UNAVAILABLE'} if path.endswith('/halves') else {'ANALYTICS_UNAVAILABLE'}))
                if not unavailable and (response.status_code != 200 or not isinstance(document, dict)
                        or 'data' not in document or 'error' in document):
                    raise ValueError(f'Provider response rejected (HTTP {response.status_code})')
                canonical = json.dumps(document, sort_keys=True, allow_nan=False).encode()
                saved = {'url': url, 'params': params, 'document': document,
                         'retrieved_at': datetime.now(UTC).isoformat(), 'unavailable': unavailable,
                         'sha256': hashlib.sha256(canonical).hexdigest(),
                         'wire_sha256': hashlib.sha256(body).hexdigest()}
                write(file, saved)
                return saved
        raise ValueError('Provider request failed')


def stat_totals(player):
    totals, seen = {}, {}
    groups = player.get('stats')
    if not isinstance(groups, list) or len(groups) > 30:
        raise ValueError('Invalid player statistic groups')
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get('stats'), dict) or len(group['stats']) > 200:
            raise ValueError('Invalid player statistic group')
        for entry in group['stats'].values():
            if not isinstance(entry, dict) or not isinstance(entry.get('stat'), dict):
                raise ValueError('Invalid statistic entry')
            key, stat = entry.get('key'), entry['stat']
            if key not in STAT_KEYS.values() and key not in FRACTIONS:
                continue
            if key in seen:
                if stat != seen[key]:
                    raise ValueError('Conflicting duplicate statistic key')
                continue
            seen[key] = stat
            if key in STAT_KEYS.values():
                if stat.get('type') not in {'integer', 'double'}:
                    raise ValueError('Scalar statistic has unsupported shape')
                target = next(k for k, v in STAT_KEYS.items() if v == key)
                totals[target] = numeric(stat.get('value'))
            if key in FRACTIONS:
                if stat.get('type') != 'fractionWithPercentage':
                    raise ValueError('Required fraction lacks raw numerator/denominator')
                a, b = numeric(stat.get('value')), numeric(stat.get('total'))
                if a is not None and b is not None and a > b:
                    raise ValueError('Fraction numerator exceeds denominator')
                totals.update(zip(FRACTIONS[key], (a, b), strict=True))
    if totals.get('aerial_duels_won') is not None and totals.get('aerial_duels_attempted') is not None:
        totals['aerial_duels_lost'] = totals.pop('aerial_duels_attempted') - totals['aerial_duels_won']
    lost = totals.pop('_duels_lost', None)
    if lost is not None and totals.get('duels_won') is not None:
        totals['duels_attempted'] = lost + totals['duels_won']
    return totals


def match_measurements(players, advanced, shots, match):
    """Measurements per appearance. Shot absence is zero only in a complete shot response."""
    if not isinstance(players, list) or len(players) > 100:
        raise ValueError('Invalid appearance list')
    if advanced is not None and (not isinstance(advanced, dict) or advanced.get('match_id') != match['id']
            or not isinstance(advanced.get('players'), list) or len(advanced['players']) > 100):
        raise ValueError('Invalid advanced player response')
    if not isinstance(shots, dict) or shots.get('match_id') != match['id'] or not isinstance(shots.get('periods'), list):
        raise ValueError('Invalid shot response')
    adv = {}
    for a in advanced['players'] if advanced else []:
        pid = identifier(a['player']['id'], 'p')
        if pid in adv:
            raise ValueError('Duplicate advanced player')
        adv[pid] = a
    shot_rows, seen_shots = [], set()
    for period in shots['periods']:
        if period.get('period') not in {'FirstHalf', 'SecondHalf'}:
            raise ValueError('League match has unsupported shot period')
        if not isinstance(period.get('shots'), list):
            raise ValueError('Invalid shot list')
        shot_rows.extend(period['shots'])
    if len(shot_rows) > 500:
        raise ValueError('Oversized shot list')
    for shot in shot_rows:
        sid = identifier(shot['id'], 's')
        if sid in seen_shots:
            raise ValueError('Duplicate match-scoped shot')
        seen_shots.add(sid)
        identifier(shot['player']['id'], 'p')
        identifier(shot['team_id'], 't')
        if shot.get('situation') not in {'RegularPlay', 'FromCorner', 'SetPiece', 'FastBreak', 'FreeKick', 'ThrowInSetPiece', 'Penalty', 'IndividualPlay'}:
            raise ValueError('Unsupported shot situation')
        if shot.get('event_type') not in {'Goal', 'AttemptSaved', 'Miss', 'Post'}:
            raise ValueError('Unsupported shot result')
        if shot.get('shot_type') not in {'RightFoot', 'LeftFoot', 'Header', 'OtherBodyParts'}:
            raise ValueError('Unsupported shot body part')
        if numeric(shot.get('expected_goals')) is None or shot['expected_goals'] > 1:
            raise ValueError('Missing or invalid shot xG')
        if not all(isinstance(shot.get(k), bool) for k in ('is_on_target', 'is_inside_box')):
            raise ValueError('Missing shot classification')
        for flag in ('is_blocked', 'is_own_goal'):
            if flag in shot and not isinstance(shot[flag], bool):
                raise ValueError('Invalid optional shot classification')
    rows, identities = [], set()
    teams = {match['home_team']['id'], match['away_team']['id']}
    for player in players:
        pid = identifier(player['player']['id'], 'p')
        team = identifier(player['team_id'], 't')
        name = player['player']['name']
        if pid in identities or team not in teams or not isinstance(name, str) or not 1 <= len(name) <= 150:
            raise ValueError('Invalid or duplicated player appearance')
        identities.add(pid)
        totals = stat_totals(player)
        a = adv.get(pid)
        if not player['stats'] and not a and not any(s['player']['id'] == pid for s in shot_rows):
            # The provider includes unused named substitutes, without statistics.
            continue
        if a:
            if a.get('team_id') != team:
                raise ValueError('Advanced player team mismatch')
            minutes = numeric(a.get('minutes_played'))
            if totals.get('minutes') is None:
                totals['minutes'] = minutes
            for raw, (group, field) in ADVANCED.items():
                # Group absent is unknown, not zero; raw fractions take precedence.
                if raw not in totals:
                    totals[raw] = numeric((a.get(group) or {}).get(field))
            aerials = numeric((a.get('defending') or {}).get('aerials'))
            if totals.get('aerial_duels_lost') is None and aerials is not None and totals.get('aerial_duels_won') is not None:
                totals['aerial_duels_lost'] = aerials - totals['aerial_duels_won']
                numeric(totals['aerial_duels_lost'])
        if totals.get('minutes') is None or not 0 < totals['minutes'] <= 130:
            raise ValueError('Missing or invalid appearance minutes')
        own = [s for s in shot_rows if s['player']['id'] == pid]
        if any(s['team_id'] != team for s in own):
            raise ValueError('Shot player/team mismatch')
        own = [s for s in own if not s.get('is_own_goal', False)]
        non_penalty = [s for s in own if s['situation'] != 'Penalty']
        sot = totals.get('shots_on_target')
        if sot is None and all(not s['is_on_target'] or 'is_blocked' in s for s in own):
            sot = sum(s['is_on_target'] and not s.get('is_blocked', False) for s in own)
        totals.update(shots=len(own), non_penalty_shots=len(non_penalty),
            non_penalty_goals=sum(s['event_type'] == 'Goal' for s in non_penalty),
            npxg=sum(s['expected_goals'] for s in non_penalty),
            shots_on_target=sot,
            shots_inside_box=sum(s['is_inside_box'] for s in own),
            headed_shots=sum(s['shot_type'] == 'Header' for s in own),
            open_play_xg=sum(s['expected_goals'] for s in own if s['situation'] in {'RegularPlay', 'FastBreak', 'IndividualPlay'}))
        rows.append({'provider_player_id': pid, 'name': name, 'provider_team_id': team,
                     'match_id': match['id'], 'totals': totals})
    if any(s['player']['id'] not in identities for s in shot_rows) or set(adv) - identities:
        raise ValueError('Events reference missing player appearances')
    return rows


def collect(root, key, season=2025, max_requests=200, matches_per_league=None, client=None):
    """Resumable full-season collection or bounded five-league feasibility sample."""
    if isinstance(season, bool) or not isinstance(season, int) or not 2024 <= season < datetime.now(UTC).year:
        raise ValueError('Requires a completed season 2024/25 or newer')
    if matches_per_league is not None and not 1 <= matches_per_league <= 10:
        raise ValueError('Sample size must be 1–10 matches per league')
    api = PitchAPI(key, root / 'snapshots', max_requests, client)
    report = {'season': f'{season}/{season + 1}', 'measurement_version': VERSION,
        'checked_at': datetime.now(UTC).isoformat(), 'rights': 'User confirmed free access and reuse rights',
        'complete': False, 'leagues': {}, 'limitations': LIMITATIONS, 'activated': False, 'quarantine': []}
    appearances = []
    try:
        catalogue = api.get('/leagues')['document']['data']['leagues']
        if not isinstance(catalogue, list) or len(catalogue) > 500:
            raise ValueError('Invalid league catalogue')
        for country, (code, name, expected) in LEAGUES.items():
            candidates = [league for league in catalogue if league.get('country_code') == code and league.get('name') == name]
            if len(candidates) != 1 or report['season'] not in candidates[0].get('seasons', []):
                raise ValueError('Required league/season missing or ambiguous')
            league_id = identifier(candidates[0]['id'], 'l')
            snapshot = api.get(f'/leagues/{league_id}/matches', {'season': report['season']})
            data = snapshot['document']['data']
            if data.get('league', {}).get('season') != report['season'] or data.get('league', {}).get('id') != league_id:
                raise ValueError('League response scope mismatch')
            matches = data.get('matches')
            if not isinstance(matches, list) or len(matches) > 500:
                raise ValueError('Invalid match inventory')
            ids = set()
            for m in matches:
                mid = identifier(m['id'], 'm')
                date = datetime.fromisoformat(m['time_utc'].replace('Z', '+00:00'))
                if mid in ids or m.get('status') != 'finished' or date.tzinfo is None or not datetime(season, 7, 1, tzinfo=UTC) <= date < datetime(season + 1, 7, 1, tzinfo=UTC):
                    raise ValueError('Duplicate, unfinished or out-of-season fixture')
                ids.add(mid)
                identifier(m['home_team']['id'], 't')
                identifier(m['away_team']['id'], 't')
            status = {'inventory': len(matches), 'expected_matches': expected, 'processed': 0, 'advanced_unavailable': 0}
            report['leagues'][country] = status
            selected = sorted(matches, key=lambda m: (m['time_utc'], m['id']))
            if matches_per_league:
                selected = selected[:matches_per_league]
            for match in selected:
                mid = match['id']
                players = api.get(f'/matches/{mid}/players')
                advanced = api.get(f'/matches/{mid}/advanced/players', optional=True)
                shots = api.get(f'/matches/{mid}/shots')
                try:
                    rows = match_measurements(players['document']['data'],
                        None if advanced['unavailable'] else advanced['document']['data'], shots['document']['data'], match)
                except (ValueError, KeyError, TypeError, AttributeError) as error:
                    report['quarantine'].append({'match_id': mid, 'competition': country,
                                                 'reason': type(error).__name__})
                    if len(report['quarantine']) >= 20:
                        raise ValueError('Repeated invalid match schemas; collection halted') from None
                    continue
                retrieved = min(s['retrieved_at'] for s in (players, advanced, shots))
                for row in rows:
                    appearances.append({**row, 'competition': country, 'retrieved_at': retrieved,
                        'source_url': BASE + f'/matches/{mid}/players',
                        'source_urls': [s['url'] for s in (players, advanced, shots)]})
                status['processed'] += 1
                status['advanced_unavailable'] += advanced['unavailable']
                if status['processed'] % 10 == 0:
                    write(root / 'collection-progress.json', {
                        'season': report['season'], 'leagues': report['leagues'],
                        'requests': api.requests, 'updated_at': datetime.now(UTC).isoformat(),
                        'complete': False, 'activated': False})
        report['complete'] = (matches_per_league is None and len(report['leagues']) == 5
            and all(league['inventory'] == league['expected_matches'] == league['processed'] for league in report['leagues'].values()))
        if report['quarantine']:
            report['failure'] = 'MatchValidationFailed'
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError, RequestBudgetReached) as error:
        report['failure'] = type(error).__name__  # Never expose credentials, headers or provider error bodies.
    finally:
        report['requests'] = api.requests
        api.close()
    grouped = {}
    raw_keys = {f.numerator for f in FEATURES} | {f.denominator for f in FEATURES} | {'aerial_duels_lost'}
    raw_keys -= {'finishing_delta', 'aerial_duels_attempted'}
    for row in appearances:
        grouped.setdefault((row['competition'], row['provider_player_id']), []).append(row)
    measurements = []
    for (country, pid), rows in sorted(grouped.items()):
        totals = {k: sum(r['totals'][k] for r in rows) if all(r['totals'].get(k) is not None for r in rows) else None for k in raw_keys}
        measurements.append({'provider_player_id': pid, 'name': rows[-1]['name'], 'competition': country,
            'season': f'{season}/{str(season + 1)[-2:]}', 'provider_team_ids': sorted({r['provider_team_id'] for r in rows}),
            'last_provider_team_id': rows[-1]['provider_team_id'],
            'totals': totals, 'features': derive(totals), 'appearance_count': len(rows),
            'source_url': rows[0]['source_url'], 'retrieved_at': min(r['retrieved_at'] for r in rows),
            'source_urls': sorted({u for r in rows for u in r['source_urls']}),
            'measurement_version': VERSION, 'complete_season': report['complete']})
    report['players'] = len(measurements)
    report['missing_feature_counts'] = {f.key: sum(r['features'][f.key] is None for r in measurements) for f in FEATURES}
    from scout.pitchapi_coverage import coverage
    report['feature_coverage'] = coverage(measurements, threshold=90.0)
    write(root / 'measurements.json', measurements)
    write(root / 'coverage.json', report)
    return measurements, report


def canonical_records(measurements, report, config):
    """Only full inventories and explicitly reviewed identity/role mappings enter scoring."""
    if (not report['complete'] or report.get('failure')
            or report.get('feature_coverage', {}).get('all_features_accepted') is not True):
        return []
    records = []
    for row in measurements:
        identity = config['identities'].get(row['provider_player_id'])
        if not identity or not identity['reviewed'] or not set(row['provider_team_ids']).issubset(identity['team_ids']):
            continue
        shot_keys = {'shots', 'non_penalty_shots', 'non_penalty_goals', 'npxg', 'shots_on_target',
                     'shots_inside_box', 'headed_shots', 'open_play_xg'}
        citations = {}
        for key, value in row['totals'].items():
            if value is not None:
                suffix = '/shots' if key in shot_keys else '/advanced/players' if key in ADVANCED else '/players'
                citations[key] = next(u for u in row['source_urls'] if u.endswith(suffix))
        records.append({'player_id': identity['player_id'], 'provider_player_id': row['provider_player_id'],
            'name': row['name'], 'team_id': 'pitchapi-' + row['last_provider_team_id'],
            'competition': row['competition'], 'season': row['season'], 'roles': identity['roles'],
            'totals': row['totals'], 'source_urls': citations, 'source_documents': row['source_urls'],
            'observed_through': config['observed_through'], 'retrieved_at': row['retrieved_at'],
            'identity_reviewed': True, 'publication_approved': config['publication_approved'],
            'measurement_version': VERSION})
    return records
