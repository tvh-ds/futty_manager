"""Private four-source master dataset; no serving database or ratings mutation.

Trust boundary: cached JSON -> validated observations -> parameterized SQLite.
Never execute source strings, infer missing rows as zero, or sum unknown rates.
"""
import csv
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

from scout.master_priority import POLICY_VERSION, PRIORITY, select_priority
from scout.real_data import name_key, read_json
from scout.source_audit import (
    LEAGUES,
    ROOTS,
    audit_opta,
    audit_pitch,
    audit_understat,
    canonical_maps,
    checksum,
)
from scout.source_table_audit import numeric

VERSION = 'four-source-master-v1'
WS_ROOT = Path('data/source-audit/2025-26/browser-whoscored-20261007')
# Candidates only: these do NOT declare equivalence. Row comparisons decide.
ALIASES = [
    {'goals', 'Goals', 'goals.Total'}, {'assists', 'Assists', 'assists.Total'},
    {'mins_played', 'minutes', 'time', 'Mins'}, {'apps', 'games', 'Apps'},
    {'shots', 'shots.Total'}, {'shots_on_target', 'shots.OnTarget'},
    {'xg', 'xG'}, {'xa', 'xA'}, {'npxg', 'np_xg'},
    {'pass_perc', 'PS%'}, {'fouls_won', 'Fouled', 'fouls.Fouled'},
    {'fouls', 'fouls.Fouls'}, {'yel_cards', 'Yel', 'cards.Yellow'},
    {'red_cards', 'Red', 'cards.Red'}, {'key_passes', 'key-passes.Total'},
    {'aerial_duels_won', 'aerial.Won'}, {'aerial_duels', 'aerial.Total'},
    {'successful_take_ons', 'take_ons_successful', 'dribbles.Successful'},
    {'dispossessed', 'possession-loss.Dispossessed'},
    {'miscontrols', 'possession-loss.UnsuccessfulTouches'},
    {'interceptions', 'interception.Total'}, {'clearances', 'clearances.Total'},
]


def compare_values(a, b, minimum=20):
    """Evidence of numerical equivalence, not proof of football definitions.

    Exclude missing/conflicted observations, require varied nonzero evidence,
    and never fit a scale conversion that could confuse per-game and totals.
    """
    pairs = [(a[k], b[k]) for k in sorted(a.keys() & b.keys())
             if isinstance(a[k], (int, float)) and not isinstance(a[k], bool)
             and isinstance(b[k], (int, float)) and not isinstance(b[k], bool)
             and math.isfinite(a[k]) and math.isfinite(b[k])]
    equal = sum(math.isclose(x, y, rel_tol=1e-6, abs_tol=1e-6) for x, y in pairs)
    varied = min(len({x for x, _ in pairs}), len({y for _, y in pairs}))
    nonzero = sum(x != 0 or y != 0 for x, y in pairs)
    status = ('empirical_equivalent' if len(pairs) >= minimum and nonzero >= 10 and varied >= 4
              and equal == len(pairs) else 'insufficient_overlap' if len(pairs) < minimum
              or nonzero < 10 or varied < 4 else 'different_values')
    return {'status': status, 'matched_rows': len(pairs), 'equal_rows': equal,
            'nonzero_rows': nonzero, 'distinct_values_min': varied,
            'agreement': equal / len(pairs) if pairs else None,
            'mean_absolute_difference': sum(abs(x-y) for x, y in pairs) / len(pairs) if pairs else None,
            'examples': [{'row': k, 'left': a[k], 'right': b[k]} for k in sorted(a.keys() & b.keys())
                         if a[k] is not None and b[k] is not None][:5]}


def resolve_cell(values):
    """Coalesce duplicates without silently overwriting conflicting numbers."""
    finite = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)]
    if not finite:
        return None, 'unavailable'
    if all(math.isclose(finite[0], v, abs_tol=1e-6, rel_tol=1e-6) for v in finite[1:]):
        return finite[0], 'observed'
    return None, 'source_conflict'


def ws_records(root):
    """Parse only visible cached table rows; retain total/per-game distinctions."""
    records, inputs = [], []
    for path in sorted(root.glob('*.json')):
        doc = read_json(path)
        if doc.get('season') != '2025/2026':
            raise ValueError('Wrong WhoScored performance season')
        league = path.name.split('-')[0].title()
        if league not in LEAGUES:
            raise ValueError('Unknown WhoScored league')
        inputs.append({'path': str(path), 'sha256': checksum(path)})
        for panel in doc['panels']:
            selectors = {s['id']: s['value'] for s in panel.get('selectors', [])}
            category = selectors.get('category') if panel['id'].endswith('-detailed') else None
            accumulation = selectors.get('statsAccumulationType', '0')
            if category and accumulation not in {'0', '1', '2', '4'}:
                raise ValueError('Unknown Detailed accumulation type')
            for table in panel['tables']:
                for row in table['rows']:
                    found = re.search(r'/players/(\d+)', row.get('player') or '')
                    if not found:
                        continue
                    if len(row['cells']) != len(table['headers']):
                        raise ValueError('WhoScored table row/header mismatch')
                    lines = row['cells'][0].splitlines()
                    name = lines[1] if lines and lines[0].isdigit() else lines[0]
                    team = lines[-1].split(',')[0] if len(lines) > 1 else None
                    fields = {}
                    for header, cell in zip(table['headers'], row['cells'], strict=True):
                        if not header or header == 'Player':
                            continue
                        key = f'{category}.{header}' if category and header not in {'Apps', 'Mins', 'Rating'} else header
                        if category and accumulation != '2' and header not in {'Apps', 'Mins', 'Rating'}:
                            key = {'0': 'per_game.', '1': 'per_90.', '4': 'every_x_minutes.'}[accumulation] + key
                        # Standard overview columns explicitly show per-game figures.
                        if not category and header in {'SpG', 'KeyP', 'AvgP', 'AerialsWon', 'Tackles', 'Inter',
                                                       'Fouls', 'Offsides', 'Clear', 'Drb', 'Blocks', 'Crosses',
                                                       'LongB', 'ThrB', 'Fouled', 'Disp', 'UnsTch'}:
                            key = f"per_game.{panel['id'].rsplit('-', 1)[-1]}.{header}"
                        state, value = numeric(cell, empty_zero=True)
                        fields[key] = (state, value, cell)
                    records.append({'provider': 'whoscored', 'id': found[1], 'league': league,
                                    'name': name, 'team': team, 'fields': fields,
                                    'file': str(path), 'url': doc['url'], 'sample': row.get('team') or 'unknown',
                                    'retrieved_at': doc['retrieved_at']})
    return records, inputs


def match_ws(records, identities, vectors):
    """Unique same-name/league candidate plus matching exposure corroboration.

    Identity matching does not use the statistic whose alias is being tested.
    Both minutes and appearances must agree; ambiguous names stay source-local.
    """
    index = defaultdict(set)
    for row, facts in identities.items():
        for name in facts['names']:
            index[(facts['league'], name_key(name))].add(row)
    evidence = defaultdict(dict)
    for r in records:
        person = (r['league'], r['id'])
        for key in ('Mins', 'Apps'):
            if key in r['fields'] and r['fields'][key][0] == 'numeric':
                evidence[person].setdefault(key, set()).add(r['fields'][key][1])
    mapping, audit = {}, []
    for r in records:
        person = (r['league'], r['id'])
        if person in mapping:
            continue
        candidates = index[(r['league'], name_key(r['name']))]
        accepted = []
        for candidate in sorted(candidates):
            mins = [values.get(candidate) for col, values in vectors.items() if col[1] in {'minutes', 'mins_played', 'time'}]
            apps = [values.get(candidate) for col, values in vectors.items() if col[1] in {'apps', 'games'}]
            e = evidence[person]
            if len(e.get('Mins', set())) == len(e.get('Apps', set())) == 1:
                m, a = next(iter(e['Mins'])), next(iter(e['Apps']))
                if m > 0 and a > 0 and m in mins and a in apps:
                    accepted.append(candidate)
        target = accepted[0] if len(accepted) == 1 else f"whoscored:{r['id']}|{r['league']}"
        mapping[person] = target
        audit.append({'league': r['league'], 'provider_id': r['id'], 'name': r['name'], 'row': target,
                      'status': 'corroborated_name_minutes_apps' if len(accepted) == 1 else 'unresolved',
                      'candidate_count': len(candidates)})
    return mapping, audit


def column_groups(vectors):
    """Exact names first; candidate aliases only after pairwise value checks."""
    columns = sorted(vectors)
    parent = {col: col for col in columns}

    def find(col):
        while parent[col] != col:
            col = parent[col]
        return col

    decisions = []
    # Exact means case-sensitive, full column label; stripping provider is all.
    for index, left in enumerate(columns):
        for right in columns[index + 1:]:
            exact = left[1] == right[1]
            alias = any(left[1] in names and right[1] in names for names in ALIASES)
            fuzzy = SequenceMatcher(None, left[1].casefold(), right[1].casefold()).ratio() >= .82
            if not (exact or alias or fuzzy):
                continue
            # Numeric agreement cannot erase the distinction between total and rate.
            def grain(label):
                return next((prefix for prefix in ('per_game.', 'per_90.', 'every_x_minutes.') if label.startswith(prefix)), 'total')
            if grain(left[1]) != grain(right[1]):
                continue
            comparison = compare_values(vectors[left], vectors[right])
            merge = exact or comparison['status'] == 'empirical_equivalent'
            # Avoid transitive alias merges contradicted by another group member.
            if merge and not exact:
                members_l = [c for c in columns if find(c) == find(left)]
                members_r = [c for c in columns if find(c) == find(right)]
                merge = all(compare_values(vectors[a], vectors[b])['status'] == 'empirical_equivalent'
                            for a in members_l for b in members_r)
            if merge:
                parent[find(right)] = find(left)
            decisions.append({'left': list(left), 'right': list(right),
                              'reason': 'exact_name' if exact else 'candidate_alias',
                              'merged': merge, **comparison})
    groups = defaultdict(list)
    for col in columns:
        groups[find(col)].append(col)
    return list(groups.values()), decisions


def build(output=Path('data/master/2025-26'), roots=None, ws_root=WS_ROOT,
          identity_manifest=Path('data/real-data/catalogue-with-gk-report.json'),
          identity_db=Path('data/scout.db'), resume_observations=None):
    roots = roots or ROOTS
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'master.sqlite').exists():
        raise FileExistsError('Use a new output directory; existing master snapshots are preserved')
    mappings = canonical_maps(identity_db, read_json(identity_manifest))
    identities, vectors, provenance = {}, defaultdict(lambda: defaultdict(list)), defaultdict(list)
    inputs = [{'path': str(identity_manifest), 'sha256': checksum(identity_manifest)}]
    db = output / 'master.sqlite.pending'
    if db.exists():
        raise FileExistsError('Pending build exists; use a new output directory')
    con = sqlite3.connect(db)
    con.executescript('''
        CREATE TABLE observations(provider TEXT, player_id TEXT, league TEXT, season TEXT,
          master_row TEXT, field TEXT, scope TEXT, sample TEXT, status TEXT, value_json TEXT);
        CREATE TABLE players(master_row TEXT PRIMARY KEY, league TEXT, names_json TEXT, sources_json TEXT);
        CREATE TABLE cells(master_row TEXT, column_id TEXT, value REAL, status TEXT, provenance_json TEXT,
          PRIMARY KEY(master_row, column_id));
        CREATE TABLE columns(column_id TEXT PRIMARY KEY, label TEXT, members_json TEXT);
    ''')
    cached_report = None
    if resume_observations:
        if roots != ROOTS:
            raise ValueError('Observation resumption requires the original source roots')
        with sqlite3.connect(f'file:{Path(resume_observations).resolve().as_posix()}?mode=ro', uri=True) as previous:
            if previous.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Invalid observation checkpoint')
            if previous.execute("SELECT COUNT(*) FROM observations WHERE season != '2025/26' OR provider NOT IN ('opta','pitchapi','understat')").fetchone()[0]:
                raise ValueError('Incompatible observation checkpoint')
            if {r[0] for r in previous.execute('SELECT DISTINCT provider FROM observations')} != set(ROOTS):
                raise ValueError('Observation checkpoint is incomplete')
            previous.backup(con)
        latest = read_json(Path('data/source-audit/2025-26/latest.json'))
        audit_path = Path('data/source-audit/2025-26') / latest['report']
        if checksum(audit_path) != latest['sha256']:
            raise ValueError('Invalid cached audit checksum')
        cached_report = read_json(audit_path)
        inputs.append({'path': str(resume_observations), 'sha256': checksum(resume_observations)})
    counts = {}

    def identity(provider, league, pid, name):
        canonical = mappings.get((provider, league, pid), f'{provider}:{pid}')
        key = f'{canonical}|{league}'
        facts = identities.setdefault(key, {'league': league, 'names': set(), 'sources': set()})
        if name:
            facts['names'].add(name)
        facts['sources'].add(f'{provider}:{pid}')
        return key

    def put(provider, label, row, value, origin):
        if value is not None and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            vectors[(provider, label)][row].append(value)
            provenance[(provider, label, row)].append(origin)

    try:
        for provider, audit in [('opta', audit_opta), ('understat', audit_understat), ('pitchapi', audit_pitch)]:
            print(f'Loading {provider} cached observations', flush=True)
            inv = None if cached_report else audit(roots[provider])
            if inv:
                inv.apply_empty_cell_policy()
            inputs.extend(cached_report['providers'][provider]['inputs'] if cached_report else inv.inputs)
            measurements = [roots[provider] / 'measurements.json'] if provider == 'pitchapi' else sorted(roots[provider].glob('*/measurements.json'))
            names = {}
            for path in measurements:
                inputs.append({'path': str(path), 'sha256': checksum(path)})
                for r in read_json(path):
                    if r['competition'] not in LEAGUES or r['season'] not in {2025, '2025/26', '2025/2026'}:
                        raise ValueError('Wrong normalized season/league')
                    person = (r['competition'], str(r['provider_player_id']))
                    names[person] = r['name']
                    master_row = identity(provider, *person, r['name'])
                    # Pitch's validated season totals are usable without summing raw
                    # percentages, average distances, ratings, or event coordinates.
                    if provider == 'pitchapi':
                        for label, value in r['totals'].items():
                            put(provider, label, master_row, value,
                                {'provider': provider, 'player_id': person[1], 'file': str(path),
                                 'scope': 'validated_partial_player_league_season',
                                 'complete_season': r.get('complete_season')})
                        # Calculated unavailable slots remain N/A, not zero.
            if cached_report:
                # The completed raw stages are copied exactly, not recomputed.
                for league, pid in con.execute('SELECT DISTINCT league,player_id FROM observations WHERE provider=?', (provider,)):
                    identity(provider, league, pid, names.get((league, pid)))
                if provider != 'pitchapi':
                    query = '''SELECT league,player_id,field,scope,MIN(sample),MIN(value_json)
                        FROM observations WHERE provider=? AND scope IN ('aggregate','identity')
                        GROUP BY league,player_id,field,scope HAVING COUNT(*)=1 AND MIN(status)='numeric' '''
                    for league, pid, field, scope, sample, value in con.execute(query, (provider,)):
                        row = identity(provider, league, pid, names.get((league, pid)))
                        put(provider, field.rsplit('.', 1)[-1], row, json.loads(value),
                            {'provider': provider, 'player_id': pid, 'field': field,
                             'sample': sample, 'scope': scope, 'checkpoint': str(resume_observations)})
                counts[provider] = {'players': con.execute('SELECT COUNT(DISTINCT player_id) FROM observations WHERE provider=?', (provider,)).fetchone()[0],
                                    'observations': con.execute('SELECT COUNT(*) FROM observations WHERE provider=?', (provider,)).fetchone()[0]}
                continue
            count = 0
            for field in inv.fields.values():
                if field.group == 'calculated':
                    continue
                for person, samples in field.observations.items():
                    row = identity(provider, *person, names.get(person))
                    batch = []
                    for sample, (state, value) in samples.items():
                        batch.append((provider, person[1], person[0], '2025/26', row, field.key,
                                      field.scope, sample, state, json.dumps(value, ensure_ascii=False, allow_nan=False)))
                        # Multi-team season rows aren't summed without a definition.
                        if provider != 'pitchapi' and field.scope in {'aggregate', 'identity'} and len(samples) == 1:
                            label = field.key.rsplit('.', 1)[-1]
                            if state == 'numeric':
                                put(provider, label, row, value, {'provider': provider, 'player_id': person[1],
                                    'field': field.key, 'sample': sample, 'scope': field.scope,
                                    'unit': field.unit})
                    con.executemany('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?)', batch)
                    count += len(batch)
            counts[provider] = {'players': len({p[1] for p in inv.players}), 'observations': count}
            con.commit()
            del inv
        # Repeated native columns get one comparison value only when consistent.
        resolved = {col: {row: resolve_cell(values)[0] for row, values in rows.items()} for col, rows in vectors.items()}
        ws, ws_inputs = ws_records(ws_root)
        inputs.extend(ws_inputs)
        ws_mapping, mapping_audit = match_ws(ws, identities, resolved)
        for r in ws:
            row = ws_mapping[(r['league'], r['id'])]
            facts = identities.setdefault(row, {'league': r['league'], 'names': set(), 'sources': set()})
            facts['names'].add(r['name'])
            facts['sources'].add(f"whoscored:{r['id']}")
            for label, (state, value, raw) in r['fields'].items():
                con.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?)',
                            ('whoscored', r['id'], r['league'], '2025/26', row, label, 'aggregate', r['sample'], state,
                             json.dumps(value, allow_nan=False)))
                if state == 'numeric':
                    put('whoscored', label, row, value, {'provider': 'whoscored', 'player_id': r['id'],
                        'file': r['file'], 'source_url': r['url'], 'retrieved_at': r['retrieved_at'],
                        'raw_cell': raw, 'scope': 'player_team_season' if not label.startswith('per_game.') else 'per_game'})
        counts['whoscored'] = {'players': len({r['id'] for r in ws}), 'table_records': len(ws),
                               'identity_matches': sum(r['status'] != 'unresolved' for r in mapping_audit), 'complete': False}
        resolved = {col: {row: resolve_cell(values)[0] for row, values in rows.items()} for col, rows in vectors.items()}
        groups, decisions = column_groups(resolved)
        conflicts = Counter()
        headers = ['master_row', 'league', 'season', 'names', 'source_ids']
        column_info = []
        wide = defaultdict(dict)
        for members in groups:
            cid = 'c_' + hashlib.sha256(json.dumps(members).encode()).hexdigest()[:16]
            label = members[0][1] if len({c[1] for c in members}) == 1 else ' / '.join(sorted({c[1] for c in members}))
            headers.append(cid)
            column_info.append({'id': cid, 'label': label, 'members': members})
            con.execute('INSERT INTO columns VALUES(?,?,?)', (cid, label, json.dumps(members)))
            people = set().union(*(vectors[c].keys() for c in members))
            for row in sorted(people):
                values = [v for c in members for v in vectors[c].get(row, [])]
                value, state = resolve_cell(values)
                selected = None
                if state == 'source_conflict':
                    candidates = [{'provider': c[0], 'field': c[1], 'value': v}
                                  for c in members for v in vectors[c].get(row, [])]
                    selected = select_priority(candidates)
                    value, state = selected['value'], 'resolved_by_priority'
                conflicts[state] += 1
                wide[row][cid] = value
                prov = [p for c in members for p in provenance.get((*c, row), [])]
                if selected:
                    prov.append({'provider': selected['provider'], 'selection': selected,
                                 'policy_version': POLICY_VERSION, 'competing_values': candidates})
                con.execute('INSERT INTO cells VALUES(?,?,?,?,?)', (row, cid, value, state, json.dumps(prov, ensure_ascii=False)))
        with (output / 'players.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            for row, facts in sorted(identities.items()):
                names, sources = sorted(facts['names']), sorted(facts['sources'])
                con.execute('INSERT INTO players VALUES(?,?,?,?)', (row, facts['league'], json.dumps(names), json.dumps(sources)))
                writer.writerow([row, facts['league'], '2025/26', ' | '.join(names), ' | '.join(sources),
                                 *[wide[row].get(c['id']) for c in column_info]])
        con.executescript('CREATE INDEX observations_player ON observations(master_row); '
                          'CREATE INDEX observations_field ON observations(provider,field); '
                          'CREATE INDEX cells_column ON cells(column_id,status);')
        con.commit()
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Master SQLite integrity check failed')
        con.close()
        db.rename(output / 'master.sqlite')
        report = {'version': VERSION, 'season': '2025/26', 'created_at': datetime.now(UTC).isoformat(),
                  'code_sha256': checksum(__file__), 'scope': 'private_local', 'activated': False,
                  'sources': counts, 'master_rows': len(identities), 'input_numeric_columns': len(vectors),
                  'master_numeric_columns': len(groups), 'cell_status': dict(conflicts),
                  'conflict_policy': {'policy_version': POLICY_VERSION, 'priority': list(PRIORITY)},
                  'identity_audit': mapping_audit, 'column_decisions': decisions, 'columns': column_info,
                  'inputs': inputs, 'limitations': [
                      'WhoScored is a 69-player preview, not the entire 2842-entry inventory.',
                      'Understat remains private; this dataset is not approved for public redistribution.',
                      'Exact-name duplicates coalesce; conflicts select Opta > PitchAPI > Understat > WhoScored with original values retained.',
                      'Empirical aliases need 20 matched varied rows with 100% numerical agreement; this is numerical evidence, not definition certification.',
                      'No automatic scale conversion; totals, per-game rates, match observations and events remain distinct.',
                      'Multi-team Opta observations remain in observations; unknown aggregates are not summed.',
                      'Calculated unavailable PitchAPI totals remain missing; present empty raw numeric cells are zero.',
                  ]}
        report['outputs'] = {p.name: checksum(p) for p in (output/'master.sqlite', output/'players.csv')}
        (output/'manifest.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        (output/'columns.json').write_text(json.dumps(column_info, indent=2), encoding='utf-8')
        return report
    except Exception:
        con.close()
        raise
