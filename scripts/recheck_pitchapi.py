"""Bounded fresh recheck: existing match cache stays immutable and secrets are never printed."""
import hashlib
import json
from pathlib import Path

from scout.pitchapi import LEAGUES, PitchAPI, write
from scout.pitchapi_coverage import audit
from scout.settings import Settings

root = Path('data/pitchapi/live-probe-2025')
destination = Path('data/pitchapi/recheck-20261006')
key = Settings().pitchapi_key.get_secret_value()
if not key:
    raise SystemExit('PitchAPI key is not configured')
rows = json.loads((root / 'measurements.json').read_text())
write(destination / 'coverage-90.json', audit(rows))


def cached(path, params=None):
    token = hashlib.sha256(json.dumps([path, params], sort_keys=True).encode()).hexdigest()
    return json.loads((root / 'snapshots' / (token + '.json')).read_text())['document']['data']


catalogue = cached('/leagues')['leagues']
api = PitchAPI(key, destination / 'snapshots', max_requests=60)
report = {'matches': [], 'activated': False}
try:
    for country, (code, name, _) in LEAGUES.items():
        league = next(item for item in catalogue if item['country_code'] == code and item['name'] == name)
        matches = cached('/leagues/' + league['id'] + '/matches', {'season': '2025/2026'})['matches']
        # First + mid-season: two independent windows in every league.
        for match in sorted(matches, key=lambda m: (m['time_utc'], m['id']))[::len(matches)//2][:2]:
            mid = match['id']
            old = cached('/matches/' + mid + '/players')
            new = api.get('/matches/' + mid + '/players')['document']['data']
            advanced = api.get('/matches/' + mid + '/advanced/players', optional=True)
            halves = api.get('/matches/' + mid + '/players/halves', optional=True)
            # Inspect a player with one of the problem fields absent, without guessing a value.
            player = next((p for p in new if p['stats'] and not any(
                e.get('key') == 'expected_assists' for g in p['stats'] for e in g['stats'].values())), new[0])
            detail = api.get('/matches/' + mid + '/players/' + player['player']['id'])
            report['matches'].append({'competition': country, 'match_id': mid,
                'base_changed': old != new, 'advanced_unavailable': advanced['unavailable'],
                'halves_unavailable': halves['unavailable'],
                'detail_keys': sorted(detail['document']['data']) if isinstance(detail['document']['data'], dict) else [],
                'player_id': player['player']['id']})
except Exception as error:
    report['failure'] = type(error).__name__
finally:
    report['requests'] = api.requests
    api.close()
    write(destination / 'recheck.json', report)
print(json.dumps(report, indent=2))
