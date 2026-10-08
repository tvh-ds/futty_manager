"""User-authorized same-normalized-name/league merge, retaining original evidence."""
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from scout.master_priority import PRIORITY
from scout.master_snapshot import SnapshotChange, transition
from scout.real_data import name_key
from scout.source_audit import checksum

VERSION = 'same-name-league-v1'


def identity_groups(players):
    parent = {r['row']: r['row'] for r in players}

    def find(row):
        while parent[row] != row:
            parent[row] = parent[parent[row]]
            row = parent[row]
        return row

    names = {}
    for r in sorted(players, key=lambda r: r['row']):
        for name in r['names']:
            normalized = name_key(name)
            if not normalized:
                continue
            key = (r['league'], normalized)
            if key in names:
                parent[find(r['row'])] = find(names[key])
            names[key] = r['row']
    groups = defaultdict(list)
    for r in players:
        groups[find(r['row'])].append(r)
    return list(groups.values())


def provider_rank(provider):
    return PRIORITY.index(provider) if provider in PRIORITY else len(PRIORITY)


def choose_cell(candidates):
    available = [r for r in candidates if isinstance(r['value'], (int, float))
                 and not isinstance(r['value'], bool) and math.isfinite(r['value'])]
    if not available:
        return None
    # Priority first. A same-provider tie keeps the existing resolved profile
    # with most populated features, then a stable original row ID.
    return min(available, key=lambda r: (provider_rank(r['provider']), -r['coverage'], r['original_row']))


def merge_names(folder: Path):
    return transition(folder, 'identity', VERSION, _merge, __file__)


def _merge(con):
    players = [{'row': row, 'league': league, 'names': json.loads(names), 'sources': json.loads(sources)}
               for row, league, names, sources in con.execute('SELECT master_row,league,names_json,sources_json FROM players')]
    groups = identity_groups(players)
    if len(groups) == len(players):
        return SnapshotChange({'rows_before': len(players), 'rows_after': len(groups), 'duplicates_removed': 0}, 'identity-merge.json')
    if con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='players_pre_name_merge'").fetchone()[0]:
        raise FileExistsError('A previous name merge is preserved; review it before another merge')
    cell_rows = list(con.execute('SELECT master_row,column_id,value,status,provenance_json FROM cells'))
    coverage = Counter(row for row, _, value, status, _ in cell_rows if value is not None and status != 'unrecorded_zero')
    old_selections = {}
    if con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='conflict_resolutions'").fetchone()[0]:
        old_selections = {(row, col): provider for row, col, provider in
                          con.execute('SELECT master_row,column_id,selected_provider FROM conflict_resolutions')}
    cells = defaultdict(list)
    for row, col, value, status, provenance in cell_rows:
        if status == 'unrecorded_zero':
            continue
        origins = json.loads(provenance)
        provider = old_selections.get((row, col))
        if not provider:
            provider = next((p['provider'] for p in origins if 'selection' in p), None)
        if not provider:
            provider = min((p['provider'] for p in origins), key=provider_rank)
        cells[row].append({'column': col, 'value': value, 'status': status, 'origins': origins,
                           'provider': provider, 'original_row': row, 'coverage': coverage[row]})
    aliases, merged_players, merged_cells, audit, statuses = [], [], [], [], Counter()
    selected_sources = Counter()
    for group in sorted(groups, key=lambda g: min(r['row'] for r in g)):
        anchor = min(group, key=lambda r: (min(provider_rank(s.split(':', 1)[0]) for s in r['sources']),
                                            -coverage[r['row']], r['row']))
        target = anchor['row']
        names = sorted({n for r in group for n in r['names']})
        sources = sorted({s for r in group for s in r['sources']})
        merged_players.append((target, anchor['league'], json.dumps(names), json.dumps(sources)))
        for r in group:
            aliases.append((r['row'], target, anchor['league'], VERSION))
        by_column = defaultdict(list)
        for r in group:
            for cell in cells[r['row']]:
                by_column[cell['column']].append(cell)
        for col, candidates in by_column.items():
            selected = choose_cell(candidates)
            if selected is None:
                value, status, provider = None, 'unavailable', None
            else:
                value, provider = selected['value'], selected['provider']
                disagree = any(c['value'] is not None and not math.isclose(value, c['value'], rel_tol=1e-6, abs_tol=1e-6)
                               for c in candidates)
                status = 'resolved_by_priority' if disagree or selected['status'] == 'resolved_by_priority' else 'observed'
                selected_sources[provider] += 1
            origins = [dict(p, original_master_row=c['original_row']) for c in candidates for p in c['origins']]
            if len(candidates) > 1:
                entry = {'master_row': target, 'column_id': col, 'selected_provider': provider,
                         'selected_value': value, 'selected_original_row': selected['original_row'] if selected else None,
                         'candidates': [{k: c[k] for k in ('original_row', 'provider', 'value', 'status')} for c in candidates],
                         'same_provider_disagreement': bool(selected and any(c['provider'] == provider and c['value'] is not None
                             and not math.isclose(c['value'], value, rel_tol=1e-6, abs_tol=1e-6) for c in candidates))}
                audit.append(entry)
                origins.append({'provider': provider, 'selection': entry, 'policy_version': VERSION})
            merged_cells.append((target, col, value, status, json.dumps(origins, ensure_ascii=False), provider))
            statuses[status] += 1
    # A recoverable transaction preserves the prior master tables. Raw
    # observations keep their original IDs, exposed through a canonical view.
    with con:
        con.execute('CREATE TABLE players_pre_name_merge AS SELECT * FROM players')
        con.execute('CREATE TABLE cells_pre_name_merge AS SELECT * FROM cells')
        con.execute('''CREATE TABLE player_aliases(original_master_row TEXT PRIMARY KEY,
                       master_row TEXT, league TEXT, policy_version TEXT)''')
        con.executemany('INSERT INTO player_aliases VALUES(?,?,?,?)', aliases)
        con.execute('DELETE FROM players')
        con.executemany('INSERT INTO players VALUES(?,?,?,?)', merged_players)
        if 'selected_provider' not in {r[1] for r in con.execute('PRAGMA table_info(cells)')}:
            con.execute('ALTER TABLE cells ADD COLUMN selected_provider TEXT')
        con.execute('DELETE FROM cells')
        con.executemany('INSERT INTO cells(master_row,column_id,value,status,provenance_json,selected_provider) VALUES(?,?,?,?,?,?)', merged_cells)
        con.execute('''CREATE VIEW observations_canonical AS SELECT o.provider,o.player_id,o.league,o.season,
                       COALESCE(a.master_row,o.master_row) AS master_row,o.master_row AS original_master_row,
                       o.field,o.scope,o.sample,o.status,o.value_json
                       FROM observations o LEFT JOIN player_aliases a ON o.master_row=a.original_master_row''')
        con.execute('''CREATE TABLE identity_merge_audit(master_row TEXT,column_id TEXT,audit_json TEXT,
                       PRIMARY KEY(master_row,column_id))''')
        con.executemany('INSERT INTO identity_merge_audit VALUES(?,?,?)',
                        [(r['master_row'], r['column_id'], json.dumps(r, ensure_ascii=False)) for r in audit])
    assert con.execute('SELECT COUNT(*) FROM players').fetchone()[0] == len(groups)
    assert con.execute('SELECT COUNT(*) FROM cells WHERE master_row NOT IN (SELECT master_row FROM players)').fetchone()[0] == 0
    # Names/league aliases must not remain spread across separate masters.
    recheck = [{'row': r[0], 'league': r[1], 'names': json.loads(r[2])} for r in merged_players]
    assert len(identity_groups(recheck)) == len(merged_players)
    summary = {'version': VERSION, 'created_at': datetime.now(UTC).isoformat(), 'rows_before': len(players),
               'rows_after': len(groups), 'duplicates_removed': len(players)-len(groups),
               'merged_groups': sum(len(g)>1 for g in groups), 'overlapping_cells': len(audit),
               'same_provider_disagreements': sum(r['same_provider_disagreement'] for r in audit),
               'cell_status': dict(statuses), 'selected_sources': dict(selected_sources),
               'priority': list(PRIORITY), 'code_sha256': checksum(__file__),
               'identity_rule': 'Same normalized name (case/accent/spacing-insensitive), same league; user-authorized.',
               'same_provider_tie_rule': 'Prefer existing row with more populated cells, then stable original row ID; never sum.',
               'aliases': [{'original_row': old, 'master_row': new, 'league': league} for old, new, league, _ in aliases]}
    return SnapshotChange({k: v for k, v in summary.items() if k != 'aliases'}, 'identity-merge.json', audit=summary,
        metadata={'name_merge': {k: v for k, v in summary.items() if k != 'aliases'}},
        limitations=('Same normalized name and league are assumed to identify one player by user instruction; homonyms can be merged.',))
