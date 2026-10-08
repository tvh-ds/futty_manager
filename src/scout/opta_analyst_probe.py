"""Bounded collection of the public Analyst feed; never activates a rating release."""
import hashlib
import json
import math
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import httpx

from scout.pitchapi_coverage import audit
from scout.striker_features import derive

LEAGUES = {'England': 'premier-league', 'Spain': 'la-liga', 'Germany': 'bundesliga',
           'Italy': 'serie-a', 'France': 'ligue-1'}
MAX_BYTES = 20_000_000
# Read from the public season-select menus, 2026-10-06. Never guess season IDs.
SEASONS_2025 = {
    'England': ('51r6ph2woavlbbpk8f29nynf8', 'premier-league'),
    'Spain': ('80zg2v1cuqcfhphn56u4qpyqc', 'primera-división'),
    'Germany': ('2bchmrj23l9u42d68ntcekob8', 'bundesliga'),
    'Italy': ('emdmtfr1v8rey2qru3xzfwges', 'serie-a'),
    'France': ('dbxs75cag7zyip5re0ppsanmc', 'ligue-1'),
}
FIELDS = {
    ('attack', 'overall'): {'shots': 'shots', 'shots_on_target': 'shots_on_target'},
    ('attack', 'nonPenalty'): {'non_penalty_goals': 'np_goals', 'npxg': 'np_xg',
                             'non_penalty_shots': 'np_shots'},
    ('possession', 'chanceCreation'): {'xa': 'xa', 'assists': 'assists'},
    ('possession', 'passing'): {'passes_attempted': 'passes', 'passes_completed': 'successful_passes',
                              'through_balls': 'through_balls'},
    ('defending', 'overall'): {'aerial_duels_attempted': 'aerial_duels', 'aerial_duels_won': 'aerial_duels_won',
                             'interceptions': 'interceptions', 'recoveries': 'recoveries', 'blocks': 'blocks'},
    ('defending', 'discipline'): {'offsides': 'offsides', 'fouls_won': 'fouls_won'},
    ('goalkeeping', 'overall'): {'saves_made': 'saves_made', 'goals_conceded': 'goals_conceded',
                                'xgot_conceded': 'xgot_conceded'},
}


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tmcl = self.season = None
        self.capture = False
        self.buffer = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div' and 'hub-navigation-container' in attrs.get('class', '').split():
            data = json.loads(attrs['data-attributes'])
            self.season = data['nav_dropdown']['selected']
        if tag == 'script' and attrs.get('class') == 'attributes':
            self.capture = True
            self.buffer = ''

    def handle_data(self, data):
        if self.capture:
            self.buffer += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.capture:
            data = json.loads(self.buffer)
            if data.get('feed_resource') == 'soccerdata':
                self.tmcl = data.get('tmcl')
            self.capture = False

    def validated(self):
        if not isinstance(self.tmcl, str) or not re.fullmatch('[a-z0-9]{20,32}', self.tmcl):
            raise ValueError('Missing public tournament identifier')
        if not isinstance(self.season, str) or not re.fullmatch(r'20\d{2}/20\d{2}', self.season):
            raise ValueError('Missing observed season')
        start, end = map(int, self.season.split('/'))
        if end != start + 1:
            raise ValueError('Invalid observed season')
        return self.tmcl, self.season


def number(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Invalid numeric measurement')
    return float(value)


def normalize(document, competition, season, source_url, retrieved_at):
    """Join reports by exact player AND team UUID, with matching exposure."""
    base = document['attack']['overall']
    if not isinstance(base, list) or not base or len(base) > 10000:
        raise ValueError('Invalid player inventory')
    keepers = document.get('goalkeeping', {}).get('overall', [])
    if not isinstance(keepers, list) or len(keepers) > 10000:
        raise ValueError('Invalid goalkeeper inventory')
    keys = {(p['player_uuid'], p['team_uuid']) for p in base}
    base = [*base, *[p for p in keepers if (p['player_uuid'], p['team_uuid']) not in keys]]
    indexes = {}
    for section in FIELDS:
        entries = document.get(section[0], {}).get(section[1], [])
        if not isinstance(entries, list) or len(entries) > 10000:
            raise ValueError('Invalid report inventory')
        index = {}
        for entry in entries:
            key = (entry['player_uuid'], entry['team_uuid'])
            if key in index:
                raise ValueError('Duplicate player/team in source report')
            index[key] = entry
        indexes[section] = index
    rows, quarantine = [], []
    for player in base:
        try:
            key = (player['player_uuid'], player['team_uuid'])
            player_key, team_key = key
            valid_player = (isinstance(player_key, str) and re.fullmatch('[a-z0-9]{20,32}', player_key)
                            or isinstance(player_key, int) and not isinstance(player_key, bool) and player_key > 0)
            if not valid_player or not isinstance(team_key, str) or not re.fullmatch('[a-z0-9]{20,32}', team_key):
                raise ValueError('Invalid identity')
            minutes = number(player.get('mins_played'))
            totals = {'minutes': minutes}
            for section, mapping in FIELDS.items():
                entry = indexes[section].get(key)
                if entry is None:
                    continue
                if number(entry.get('mins_played')) != minutes:
                    raise ValueError('Conflicting report exposure')
                totals.update({target: number(entry.get(source)) for target, source in mapping.items()})
            defense = indexes[('defending', 'overall')].get(key)
            if defense is not None:
                for target, ground, aerial in [('duels_attempted', 'ground_duels', 'aerial_duels'),
                                               ('duels_won', 'ground_duels_won', 'aerial_duels_won')]:
                    a, b = number(defense.get(ground)), number(defense.get(aerial))
                    totals[target] = a + b if a is not None and b is not None else None
            won, attempted = totals.get('aerial_duels_won'), totals.get('aerial_duels_attempted')
            totals['aerial_duels_lost'] = attempted - won if won is not None and attempted is not None else None
            for won_key, attempted_key in [('duels_won', 'duels_attempted'),
                                           ('aerial_duels_won', 'aerial_duels_attempted'),
                                           ('passes_completed', 'passes_attempted'), ('shots_on_target', 'shots')]:
                if totals.get(won_key) is not None and totals.get(attempted_key) is not None:
                    if totals[won_key] > totals[attempted_key]:
                        raise ValueError('Inconsistent count fraction')
            rows.append({'provider_player_id': str(key[0]), 'provider_team_id': key[1], 'name': player['player'],
                'identity_namespace': 'opta-numeric' if isinstance(key[0], int) else 'opta-uuid',
                'competition': competition, 'season': season, 'source_position': player.get('squad_position_detailed'),
                'totals': totals, 'features': derive(totals), 'source_url': source_url, 'retrieved_at': retrieved_at,
                'measurement_version': 'opta-analyst-probe-v2-gk', 'identity_reviewed': False})
        except (KeyError, TypeError, ValueError):
            quarantine.append({'reason': 'Invalid identity, count or inconsistent report exposure'})
    return rows, quarantine


def fetch(client, url):
    """Fixed hosts, no redirects or credentials, bounded streaming responses."""
    if not (re.fullmatch(r'https://theanalyst\.com/competition/(premier-league|la-liga|bundesliga|serie-a|ligue-1)/stats', url)
            or re.fullmatch(r'https://dataviz\.theanalyst\.com/project-data/soccer/[a-z0-9]{20,32}/player-stats\.json', url)):
        raise ValueError('Unsupported public source URL')
    with client.stream('GET', url, follow_redirects=False, timeout=30) as response:
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError('Source redirect rejected')
        body = bytearray()
        for chunk in response.iter_bytes():
            if len(body) + len(chunk) > MAX_BYTES:
                raise ValueError('Source response bound exceeded')
            body.extend(chunk)
        return bytes(body)


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def reprocess(source: Path, destination: Path):
    """Rebuild normalized measurements from immutable bronze without requests."""
    from scout.real_data import read_json
    report = read_json(source / 'coverage.json')
    if report.get('requested_season') != '2025/2026':
        raise ValueError('Expected completed 2025/26 snapshots')
    destination.mkdir(parents=True, exist_ok=False)
    all_rows, appearances = [], []
    for league, slug in LEAGUES.items():
        folder = destination / slug
        folder.mkdir()
        facts = report['leagues'][league]
        body = (source / slug / 'bronze.json').read_bytes()
        if hashlib.sha256(body).hexdigest() != facts['snapshot_sha256']:
            raise ValueError('Bronze checksum mismatch')
        (folder / 'bronze.json').write_bytes(body)
        rows, quarantined = normalize(read_json(source / slug / 'bronze.json'), league,
                                     report['requested_season'], facts['source_url'], facts['retrieved_at'])
        save(folder / 'measurements.json', rows)
        save(folder / 'quarantine.json', quarantined)
        audited = rows + [{'competition': league, 'totals': {}} for _ in quarantined]
        positive = [r for r in rows if (r['totals'].get('minutes') or 0) > 0]
        facts.update(players=len(rows), quarantined=len(quarantined), coverage=audit(audited), appearance_coverage=audit(positive))
        all_rows.extend(audited)
        appearances.extend(positive)
    report.update(coverage=audit(all_rows), appearance_coverage=audit(appearances),
                  reprocessed_from=str(source), transform_version='opta-analyst-probe-v2-gk',
                  reprocessed_at=datetime.now(UTC).isoformat(), activated=False)
    save(destination / 'coverage.json', report)
    return report


def probe(root: Path, requested_season=2025, client=None):
    if isinstance(requested_season, bool) or not isinstance(requested_season, int) or not 2024 <= requested_season <= datetime.now(UTC).year:
        raise ValueError('Invalid requested season')
    root.mkdir(parents=True, exist_ok=False)
    report = {'provider': 'Opta Analyst', 'requested_season': f'{requested_season}/{requested_season + 1}',
        'consent': 'User confirmed consent to use Opta Analyst on 2026-10-06',
        'activated': False, 'leagues': {}, 'limitations': [
            'Observed season must match requested season before any replacement import.',
            'Exact identity/stint mappings and measurement definitions require review.',
            'Only unambiguous counts mapped; provider percentages do not supply undefined zero-attempt rates.',
            'Aggregate duels are the sum of source ground and aerial counts; distinct source version.',
            'Carry progressive_distance can be signed; not mapped to unsigned progressive carry distance.',
            'Probe inventory is not an independent full-season player population verification.']}
    all_rows = []
    appearance_rows = []
    owned = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=False)
    try:
        for league, slug in LEAGUES.items():
            folder = root / slug
            folder.mkdir()
            try:
                if requested_season == 2025:
                    tmcl, source_slug = SEASONS_2025[league]
                    season = '2025/2026'
                    page_url = f'https://optaplayerstats.statsperform.com/en_GB/soccer/{source_slug}-2025-2026/{tmcl}/results'
                else:
                    page_url = f'https://theanalyst.com/competition/{slug}/stats'
                    page = fetch(client, page_url)
                    (folder / 'page.html').write_bytes(page)
                    parser = PageMetadata()
                    parser.feed(page.decode('utf-8'))
                    tmcl, season = parser.validated()
                url = f'https://dataviz.theanalyst.com/project-data/soccer/{tmcl}/player-stats.json'
                body = fetch(client, url)
                (folder / 'bronze.json').write_bytes(body)
                document = json.loads(body, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
                retrieved = datetime.now(UTC).isoformat()
                rows, quarantine = normalize(document, league, season, url, retrieved)
                save(folder / 'measurements.json', rows)
                save(folder / 'quarantine.json', quarantine)
                audited = rows + [{'competition': league, 'totals': {}} for _ in quarantine]
                report['leagues'][league] = {'observed_season': season, 'requested_season_match': season == report['requested_season'],
                    'players': len(rows), 'quarantined': len(quarantine), 'source_url': url, 'page_url': page_url,
                    'retrieved_at': retrieved, 'source_last_updated': document.get('lastUpdated'),
                    'snapshot_sha256': hashlib.sha256(body).hexdigest(), 'coverage': audit(audited),
                    'appearance_coverage': audit([r for r in rows if (r['totals'].get('minutes') or 0) > 0])}
                all_rows.extend(audited)
                appearance_rows.extend(r for r in rows if (r['totals'].get('minutes') or 0) > 0)
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
                report['leagues'][league] = {'failure': type(error).__name__}
    finally:
        if owned:
            client.close()
    report['coverage'] = audit(all_rows)
    report['appearance_coverage'] = audit(appearance_rows)
    report['requested_window_available'] = len(report['leagues']) == 5 and all(
        x.get('requested_season_match') is True for x in report['leagues'].values())
    report['source_validation_passed'] = report['requested_window_available'] and all(
        not x.get('quarantined') for x in report['leagues'].values())
    save(root / 'coverage.json', report)
    return report
