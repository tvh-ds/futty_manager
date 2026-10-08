"""Audited source-priority resolution of private master cells."""
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from scout.master_snapshot import SnapshotChange, transition
from scout.real_data import read_json
from scout.source_audit import checksum
from scout.source_table_audit import numeric

PRIORITY = ('opta', 'pitchapi', 'understat', 'whoscored')
POLICY_VERSION = 'source-priority-v1'


def select_priority(candidates):
    for provider in PRIORITY:
        available = [r for r in candidates if r['provider'] == provider
                     and isinstance(r.get('value'), (int, float)) and not isinstance(r['value'], bool)
                     and math.isfinite(r['value'])]
        if not available:
            continue
        first = available[0]
        if not all(math.isclose(first['value'], r['value'], abs_tol=1e-6, rel_tol=1e-6) for r in available):
            raise ValueError(f'Conflicting values within {provider}; source priority cannot decide this')
        return first
    raise ValueError('No available numeric source value')


def resolve_master(folder: Path):
    return transition(folder, 'priority', POLICY_VERSION, _resolve, __file__)


def _resolve(con):
    measurement_cache = {}
    resolutions = []
    conflicts = con.execute("SELECT master_row,column_id,provenance_json FROM cells WHERE status='source_conflict'").fetchall()
    if not conflicts:
        return SnapshotChange({'resolved': 0, 'remaining': 0, 'priority': list(PRIORITY)}, 'conflict-resolution.json')
    columns = {r[0]: json.loads(r[1]) for r in con.execute('SELECT column_id,members_json FROM columns')}
    for row, cid, provenance in conflicts:
        league = row.rsplit('|', 1)[1]
        candidates = []
        for origin in json.loads(provenance):
            provider = origin['provider']
            if 'field' in origin:
                results = con.execute('''SELECT value_json FROM observations
                    WHERE master_row=? AND provider=? AND player_id=? AND field=? AND sample=? AND status='numeric' ''',
                    (row, provider, origin['player_id'], origin['field'], origin['sample'])).fetchall()
                values = [json.loads(r[0]) for r in results]
            elif provider == 'pitchapi':
                path = Path(origin['file']).resolve()
                if not path.is_relative_to(Path.cwd().resolve()):
                    raise ValueError('Measurement path outside workspace')
                if path not in measurement_cache:
                    measurement_cache[path] = {(r['competition'], str(r['provider_player_id'])): r['totals']
                                               for r in read_json(path)}
                totals = measurement_cache[path].get((league, origin['player_id']), {})
                values = [totals.get(label) for p, label in columns[cid] if p == provider]
            elif provider == 'whoscored':
                state, value = numeric(origin['raw_cell'], empty_zero=True)
                values = [value] if state == 'numeric' else []
            else:
                raise ValueError('Unsupported cell provenance')
            candidates.extend({'provider': provider, 'value': value, 'origin': origin} for value in values)
        selected = select_priority(candidates)
        resolutions.append({'master_row': row, 'column_id': cid, 'previous_status': 'source_conflict',
                            'previous_value': None, 'selected_provider': selected['provider'],
                            'selected_value': selected['value'], 'candidates': candidates,
                            'policy_version': POLICY_VERSION})
    con.execute('''CREATE TABLE IF NOT EXISTS conflict_resolutions(
        master_row TEXT, column_id TEXT, policy_version TEXT, selected_provider TEXT,
        selected_value REAL, audit_json TEXT, PRIMARY KEY(master_row,column_id,policy_version))''')
    for r in resolutions:
        con.execute('INSERT INTO conflict_resolutions VALUES(?,?,?,?,?,?)',
                    (r['master_row'], r['column_id'], POLICY_VERSION, r['selected_provider'], r['selected_value'], json.dumps(r, ensure_ascii=False)))
        con.execute("UPDATE cells SET value=?,status='resolved_by_priority' WHERE master_row=? AND column_id=? AND status='source_conflict'",
                    (r['selected_value'], r['master_row'], r['column_id']))
    remaining = con.execute("SELECT COUNT(*) FROM cells WHERE status='source_conflict'").fetchone()[0]
    summary = {'policy_version': POLICY_VERSION, 'priority': list(PRIORITY),
               'resolved_at': datetime.now(UTC).isoformat(), 'resolved': len(resolutions), 'remaining': remaining,
               'selected_sources': dict(Counter(r['selected_provider'] for r in resolutions)),
               'code_sha256': checksum(__file__), 'resolutions': resolutions}
    return SnapshotChange({k: v for k, v in summary.items() if k != 'resolutions'}, 'conflict-resolution.json', audit=summary,
        metadata={'conflict_policy': {k: v for k, v in summary.items() if k != 'resolutions'}},
        limitations=('Cross-source conflicts select Opta > PitchAPI > Understat > WhoScored; values remain auditable, not averaged.',),
        remove_limitations=('source_conflict status',))
