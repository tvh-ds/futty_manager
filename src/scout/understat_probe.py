"""Bounded, one-off real-data feasibility probe, never a publication adapter.

The public league page's own AJAX interface supplies partial numeric evidence.
Recurring collection/public display permission and complete coverage are separate
gates. This command does not infer tactical eligibility or enable monthly jobs.
"""
import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scout.striker_features import FEATURES, derive

LEAGUES = {'England': 'EPL', 'Spain': 'La_liga', 'Germany': 'Bundesliga',
           'Italy': 'Serie_A', 'France': 'Ligue_1'}
FIELDS = {'minutes': 'time', 'non_penalty_goals': 'npg', 'npxg': 'npxG',
          'shots': 'shots', 'assists': 'assists', 'xa': 'xA', 'key_passes': 'key_passes'}
MAX_BYTES = 10_000_000


def normalize_player_shots(document, league_document, competition, season, player_id, retrieved_at):
    """Join a player's shots to completed league fixtures, reconcile before deriving.

    No automatic tactical eligibility, identity merge or public release. Coordinates
    and shot-result categories are retained upstream, not guessed into box/SOT stats.
    """
    url = f'https://understat.com/getLeagueData/{LEAGUES[competition]}/{season}'
    rows, _, _ = normalize(league_document, competition, season, url, retrieved_at)
    for fixture in league_document['dates']:
        if fixture.get('isResult') is True:
            date = datetime.strptime(fixture['datetime'], '%Y-%m-%d %H:%M:%S')
            if not datetime(season, 7, 1) <= date < datetime(season + 1, 8, 1):
                raise ValueError('League fixture outside requested performance season')
    row = next((r for r in rows if r['provider_player_id'] == player_id), None)
    identity = document.get('player') if isinstance(document, dict) else None
    if row is None or not isinstance(identity, dict) or identity.get('id') != player_id:
        raise ValueError('Player identity missing or inconsistent')
    shots = document.get('shots')
    if not isinstance(shots, list) or len(shots) > 10000:
        raise ValueError('Invalid or oversized shot payload')
    fixtures = {str(f['id']) for f in league_document['dates'] if f.get('isResult') is True}
    selected, seen = [], set()
    for shot in shots:
        if not isinstance(shot, dict):
            raise ValueError('Invalid shot row')
        if shot.get('season') != str(season) or str(shot.get('match_id')) not in fixtures:
            continue
        identifier = shot.get('id')
        if (not isinstance(identifier, str) or not re.fullmatch(r'\d{1,12}', identifier)
                or identifier in seen or shot.get('player_id') != player_id
                or shot.get('situation') not in {'OpenPlay', 'FromCorner', 'SetPiece', 'DirectFreekick', 'Penalty'}
                or shot.get('shotType') not in {'Head', 'LeftFoot', 'RightFoot', 'OtherBodyPart'}
                or shot.get('result') not in {'Goal', 'SavedShot', 'MissedShots', 'BlockedShot', 'ShotOnPost'}):
            raise ValueError('Invalid, duplicate or unsupported shot evidence')
        xg = number(shot.get('xG'))
        if xg is None or xg > 1:
            raise ValueError('Invalid shot xG')
        seen.add(identifier)
        selected.append({**shot, 'xG': xg})
    totals = dict(row['totals'])
    non_penalty = [s for s in selected if s['situation'] != 'Penalty']
    if (totals['shots'] != len(selected)
            or totals['non_penalty_goals'] != sum(s['result'] == 'Goal' for s in non_penalty)
            or totals['npxg'] is None
            or not math.isclose(totals['npxg'], sum(s['xG'] for s in non_penalty), rel_tol=1e-5, abs_tol=1e-5)):
        raise ValueError('Shot evidence does not reconcile with league aggregates')
    totals.update(non_penalty_shots=len(non_penalty),
                  open_play_xg=sum(s['xG'] for s in selected if s['situation'] == 'OpenPlay'),
                  headed_shots=sum(s['shotType'] == 'Head' for s in selected))
    return {**row, 'totals': totals, 'features': derive(totals),
            'shot_source_url': f'https://understat.com/getPlayerData/{player_id}',
            'shot_count': len(selected), 'shot_scope': 'Completed fixtures in the exact league and season',
            'limitations': ['Shot coordinates not mapped to box boundaries; SOT categories not approved.',
                            'Partial evidence only; missing abilities and unreviewed roles prevent full rating.']}


def probe_player(root: Path, league_snapshot: Path, player_id: str, competition='England', season=2025, client=None):
    """One requested player, fixed source host, private evidence; never a bulk crawler."""
    if (competition not in LEAGUES or not re.fullmatch(r'\d{1,12}', player_id)
            or isinstance(season, bool) or not isinstance(season, int)
            or not 2024 <= season <= datetime.now(UTC).year):
        raise ValueError('Invalid player probe scope')
    if league_snapshot.stat().st_size > MAX_BYTES:
        raise ValueError('League snapshot bound exceeded')
    league_body = league_snapshot.read_bytes()
    league_document = json.loads(league_body)
    # Check membership before making any network request.
    rows, _, _ = normalize(league_document, competition, season, '', '')
    if not any(r['provider_player_id'] == player_id for r in rows):
        raise ValueError('Player absent from validated league snapshot')
    root.mkdir(parents=True, exist_ok=False)
    owned = client is None
    client = client or httpx.Client(timeout=25, follow_redirects=False)
    try:
        url = f'https://understat.com/getPlayerData/{player_id}'
        with client.stream('GET', url, headers={'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'https://understat.com/player/{player_id}'}) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                if len(body) + len(chunk) > MAX_BYTES:
                    raise ValueError('Player snapshot bound exceeded')
                body.extend(chunk)
        (root / 'bronze.json').write_bytes(body)
        row = normalize_player_shots(json.loads(body), league_document, competition, season,
                                     player_id, datetime.now(UTC).isoformat())
        row['snapshot_sha256'] = hashlib.sha256(body).hexdigest()
        row['league_snapshot_sha256'] = hashlib.sha256(league_body).hexdigest()
        (root / 'measurements.json').write_text(json.dumps(row, indent=2, allow_nan=False), encoding='utf-8')
        return row
    finally:
        if owned:
            client.close()


def number(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError('Invalid numeric type')
    if isinstance(value, str) and not re.fullmatch(r'\d+(?:\.\d+)?', value):
        raise ValueError('Invalid numeric text')
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError('Non-finite or negative total')
    return result


def normalize(document, competition, season, source_url, retrieved_at):
    if competition not in LEAGUES or not isinstance(document, dict):
        raise ValueError('Invalid source scope')
    players, fixtures = document.get('players'), document.get('dates')
    if not isinstance(players, list) or len(players) > 5000 or not isinstance(fixtures, list) or len(fixtures) > 2000:
        raise ValueError('Invalid or oversized league payload')
    rows, quarantine, identities = [], [], set()
    for index, player in enumerate(players):
        try:
            if not isinstance(player, dict):
                raise ValueError('Invalid player row')
            identifier = player.get('id')
            name, team, position = player.get('player_name'), player.get('team_title'), player.get('position')
            if (not isinstance(identifier, str) or not re.fullmatch(r'\d{1,12}', identifier)
                    or identifier in identities or not isinstance(name, str) or not 1 <= len(name) <= 150
                    or not isinstance(team, str) or not 1 <= len(team) <= 500
                    or not isinstance(position, str) or len(position) > 100):
                raise ValueError('Missing, duplicated or invalid source identity')
            totals = {key: number(player.get(field)) for key, field in FIELDS.items()}
            goals = number(player.get('goals'))
            if (totals['non_penalty_goals'] is not None and goals is not None
                    and totals['non_penalty_goals'] > goals):
                raise ValueError('Non-penalty goals exceed goals')
            if goals is not None and totals['shots'] is not None and goals > totals['shots']:
                raise ValueError('Goals exceed shots')
            values = derive(totals)
            if any(v is not None and not math.isfinite(v) for v in values.values()):
                raise ValueError('Non-finite derived feature')
            identities.add(identifier)
            rows.append({'provider_player_id': identifier, 'name': name,
                'source_team_title': team, 'source_position': position,
                'competition': competition, 'season': f'{season}/{str(season + 1)[-2:]}',
                'totals': totals, 'features': values, 'source_url': source_url,
                'retrieved_at': retrieved_at, 'identity_reviewed': False,
                'publication_approved': False, 'role_eligibility': 'unreviewed'})
        except (ValueError, TypeError, OverflowError):
            quarantine.append({'index': index, 'reason': 'Invalid source identity, totals or derived values'})
    completed = []
    for fixture in fixtures:
        if not isinstance(fixture, dict) or fixture.get('isResult') is not True:
            continue
        date = fixture.get('datetime')
        if not isinstance(date, str):
            raise ValueError('Completed fixture missing date')
        datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        completed.append(date)
    available = {f.key: sum(r['features'][f.key] is not None for r in rows) for f in FEATURES}
    coverage = {'players': len(players), 'validated_players': len(rows),
        'quarantined_players': len(quarantine), 'completed_fixtures': len(completed),
        'latest_completed_fixture_source_time': max(completed) if completed else None,
        'fixture_timezone': 'unverified; source time is not an approved UTC observation cutoff',
        'maximum_minutes': max((r['totals']['minutes'] or 0 for r in rows), default=None),
        'players_with_900_minutes': sum((r['totals']['minutes'] or 0) >= 900 for r in rows),
        'available_feature_counts': available,
        'unavailable_features': [key for key, count in available.items() if count == 0]}
    return rows, quarantine, coverage


def probe(root: Path, season: int = 2026, client=None):
    if isinstance(season, bool) or not isinstance(season, int) or not 2024 <= season <= datetime.now(UTC).year:
        raise ValueError('Requires a season 2024/25 or newer, not in the future')
    # A dedicated fresh directory prevents overwriting source evidence.
    root.mkdir(parents=True, exist_ok=False)
    report = {'season': f'{season}/{str(season + 1)[-2:]}', 'checked_at': datetime.now(UTC).isoformat(),
              'provider': 'Understat', 'mode': 'one-off feasibility probe', 'activated': False,
              'recurring_collection_approved': False, 'publication_approved': False, 'leagues': {},
              'limitations': ['Partial registry; no full striker rating or tactical eligibility claim.',
                             'Source times, exact cross-provider definitions, permissions and identity/stint mapping need review.']}
    owned = client is None
    client = client or httpx.Client(timeout=25, follow_redirects=False)
    try:
        for league, slug in LEAGUES.items():
            url = f'https://understat.com/getLeagueData/{slug}/{season}'
            try:
                with client.stream('GET', url, headers={'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f'https://understat.com/league/{slug}/{season}'}) as response:
                    response.raise_for_status()
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        if len(body) + len(chunk) > MAX_BYTES:
                            raise ValueError('Source snapshot bound exceeded')
                        body.extend(chunk)
                def reject_constant(token):
                    raise ValueError('Non-finite JSON constant')
                document = json.loads(body, parse_constant=reject_constant)
                retrieved_at = datetime.now(UTC).isoformat()
                rows, quarantine, coverage = normalize(document, league, season, url, retrieved_at)
                folder = root / slug
                folder.mkdir()
                (folder / 'bronze.json').write_bytes(body)
                (folder / 'measurements.json').write_text(json.dumps(rows, indent=2, allow_nan=False), encoding='utf-8')
                (folder / 'quarantine.json').write_text(json.dumps(quarantine, indent=2), encoding='utf-8')
                report['leagues'][league] = {**coverage, 'source_url': url, 'retrieved_at': retrieved_at,
                    'snapshot_sha256': hashlib.sha256(body).hexdigest()}
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
                report['leagues'][league] = {'failure': type(error).__name__, 'source_url': url}
    finally:
        if owned:
            client.close()
    (root / 'coverage.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    return report
