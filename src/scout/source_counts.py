"""Simple source player/column inventories, without coverage eligibility gates."""
import json
import re
from datetime import UTC, datetime

from scout.source_audit import EXTERNAL, LEAGUES, md_table

POLICY = ('Empty or dash cells in an existing numeric column are zero under the user-specified policy. '
          'Original snapshots are preserved. Absent rows/columns, failed requests, explicit N/A, '
          'identity text and unavailable calculated features are not manufactured as zeros. No 90% gate applies.')


def browser_inventory(root):
    files = sorted((root / 'browser-whoscored-20261007').glob('*.json'))
    players, columns, totals, snapshots = set(), set(), {}, []
    for path in files:
        doc = json.loads(path.read_text(encoding='utf-8'))
        if doc.get('season') != '2025/2026':
            continue
        league = path.name.split('-')[0].title()
        for panel in doc['panels']:
            total = re.search(r'Page \d+/\d+ \| Showing \d+ - \d+ of (\d+)', panel['text'])
            if total and panel.get('all_players_selected'):
                totals[league] = int(total[1])
            category = next((s['value'] for s in panel.get('selectors', []) if s['id'] == 'category'), None)
            for table in panel['tables']:
                for header in table['headers']:
                    if not header:
                        continue
                    if category and header not in {'Player', 'Apps', 'Mins', 'Rating'}:
                        header = f'{category}.{header}'
                    elif header == 'Drb':
                        header = f"{panel['id'].rsplit('-', 1)[-1]}.Drb"
                    columns.add(header)
                for row in table['rows']:
                    if row.get('player'):
                        players.add(re.search(r'/players/(\d+)', row['player'])[1])
        snapshots.append({'file': str(path), 'url': doc['url'], 'retrieved_at': doc['retrieved_at']})
    return {'sample_unique_ids': len(players), 'columns': sorted(columns), 'displayed_league_rows': totals,
            'snapshots': snapshots, 'complete': False}


def render(folder, output, result, digest):
    browser = result.get('browser_whoscored', browser_inventory(output))
    rows = []
    for provider, report in result['providers'].items():
        native = {k: f for k, f in report['fields'].items() if f['group'] != 'calculated'}
        performance = {k: f for k, f in native.items() if f['kind'] == 'metric'}
        events = {k: f for k, f in native.items() if f['kind'] == 'event'}
        rows.append([provider, report['unique_players'], len(native), len(performance), len(events), 'complete cached inventory; retained records'])
        text = [f'# {provider.title()} — player and feature counts', '', '**Performance season: 2025/26.**', '',
            f"Distinct provider player IDs: **{report['unique_players']}**. Player/league records: **{report['player_league_rows']}**. "
            f"Player/team or normalized records: **{report['player_team_or_league_records']}**.", '',
            f'Native player-field paths: **{len(native)}**; season/match performance columns: **{len(performance)}**; '
            f'event-attribute paths: **{len(events)}**. Identity, exposure, formatting and provider-rating fields remain in the native total. '
            'Scout-calculated columns are excluded from source feature totals.', '', POLICY, '', '## Player counts by league', '',
            md_table(['League', 'Distinct source players'], [[league, next(iter(report['fields'].values()))['leagues'][league]['players']] for league in LEAGUES]),
            '## All native player columns', '',
            'Cells count distinct players with numeric observations, including existing empty numeric cells interpreted as zero. '
            'Categorical fields have their recorded-player count in the last column. Zeros include the stated cell policy; '
            'they are not proof of a measured event absence.', '',
            md_table(['Native column', 'Type', *LEAGUES, 'Total numeric players', 'Recorded players', 'Zero players', 'Engine'],
                [[f'`{key}`', f['kind'], *[f['leagues'][league]['numeric'] for league in LEAGUES], f['all']['numeric'],
                    f['all']['recorded'], f['all']['zero'], 'imported/used' if f['imported'] else 'raw only'] for key, f in native.items()]),
            '## Season and freshness', '', md_table(['League', 'Recorded metadata'], [[league, json.dumps(facts, ensure_ascii=True)] for league, facts in report['freshness'].items()]),
            '## Non-player fields', '', 'These do not contribute player or performance-feature counts.', '',
            *[f"- {group}: " + ', '.join(f'`{key}`' for key in keys) for group, keys in report['context_fields'].items()], '',
            'Rights: ' + ('private local use; public reuse unverified' if provider == 'understat' else 'existing user-confirmed source permission retained'), '',
            'Full schema/provenance is retained in the content-addressed audit snapshot. No rating or application release is changed.', '']
        (folder / f'{provider}.md').write_text('\n'.join(text), encoding='utf-8')
    for source, info in EXTERNAL.items():
        probe = result['access_probes'].get(source, {})
        fields = result['additional_tables'].get(source, {}).get('fields', {})
        count, features, metrics, events = 'unknown', 'unknown', 'unknown', 'unknown'
        notes = info['note']
        extra = []
        if source == 'whoscored' and browser['columns']:
            count = f"{sum(browser['displayed_league_rows'].values())} displayed entries; {browser['sample_unique_ids']} captured IDs; full unique total not yet deduplicated"
            features = len(browser['columns'])
            metrics = len(set(browser['columns']) - {'Player', 'Apps', 'Mins', 'Rating'})
            events = 0
            notes = ('Rendered browser tables are accessible, including 2025/26 Fouled. The previous static-HTML check '
                     'missed dynamic tables. Displayed totals are source player/team rows, not deduplicated IDs. '
                     'All 16 Detailed categories and their enabled subdivisions were inspected in England. '
                     'Captured columns are a minimum across the site; remaining player pages and league-specific schema differences are not exhaustively collected.')
            extra = ['## Browser observations', '', 'These totals use the verified All players filter. Transfer stints may repeat player IDs; all pages have not been collected for deduplication.', '', md_table(['League', 'Displayed player-table rows (All players)'],
                [[league, browser['displayed_league_rows'].get(league, 'not yet observed')] for league in LEAGUES]),
                'Captured columns: ' + ', '.join(f'`{key}`' for key in browser['columns']), '',
                md_table(['Snapshot', 'Source URL', 'Retrieved UTC'], [[s['file'], s['url'], s['retrieved_at']] for s in browser['snapshots']])]
        elif source == 'statbunker':
            features = len(fields)
            metrics = sum(f['kind'] != 'identity' for f in fields.values())
            events = 0
            notes = ('Captured historical columns are inventoried below. Player IDs are not consistently supplied, '
                     'so no verified distinct-player total is claimed. These endpoint/column counts may include '
                     'representations of the same measurement. Some league pages failed.')
            extra = ['## All captured historical columns', '', md_table(['Column', 'Type', *LEAGUES, 'Total numeric records'],
                [[f'`{key}`', f['kind'], *[f['leagues'][league]['numeric'] for league in LEAGUES],
                    sum(f['leagues'][league]['numeric'] for league in LEAGUES)] for key, f in sorted(fields.items())])]
        elif source == 'fotmob':
            sample = result['fotmob_sample']
            count = f"{sample['sample_player_ids']} captured IDs in one team sample; full total unknown"
            features, metrics, events = len(sample['fields']), 2, 0
            extra = ['## Captured sample and advertised selectors', '',
                f"Native sample columns: {len(sample['fields'])}. Advertised statistic selectors: {len(sample['advertised_fields'])}; these are not collected features.", '',
                md_table(['Native player field', 'Sample numeric players'], [[key, c['numeric']] for key, c in sample['fields'].items()]),
                md_table(['Selector', 'Title'], [[f['name'], f.get('title','')] for f in sample['advertised_fields']])]
        elif source == 'statsbomb':
            count, features, metrics, events = 0, 0, 0, 0
        rows.append([source, count, features, metrics, events, 'partial/blocked/nonqualifying; see source report'])
        text = [f'# {source.title()} — player and feature counts', '', '**Performance season: 2025/26, senior men, top five leagues.**', '',
            f'Players: **{count}**. Captured native player columns: **{features}**. Performance columns: **{metrics}**. Event fields: **{events}**.', '',
            POLICY, '', notes, '', f"Access probe: `{probe.get('status', probe.get('error','unknown'))}`; retrieved `{probe.get('retrieved_at','unknown')}`. "
            'Provider update time remains unknown unless supplied.', '', *extra, '', '## References', '',
            *[f'- [{url}]({url})' for url in info['references']], '']
        (folder / f'{source}.md').write_text('\n'.join(text), encoding='utf-8')
    summary = md_table(['Source', 'Players', 'Native player fields', 'Performance columns', 'Event attributes', 'Scope'], rows)
    index = ['# Football source counts — 2025/26', '', f"Updated 7 October 2026; generated UTC {datetime.now(UTC).isoformat()}.", '', POLICY, '', summary, '',
        'Native totals count collected source columns, not independent abilities. They include identity and context; '
        'Scout-calculated columns are excluded. Player totals are distinct provider IDs unless explicitly labelled as sample IDs or displayed rows. '
        'Unknown means not measured, not zero. StatsBomb zero means no qualifying target-season competition.', '',
        '## Source reports', '', *[f'- [{row[0].title()}]({row[0]}.md)' for row in rows], '',
        '[Four-source master dataset and merge rules](master-dataset.md).', '',
        '## Reproduce', '', '```powershell', 'scout audit-data-sources', 'scout collect-source-tables --budget 160', '```', '',
        'Browser observations are kept separately in `data/source-audit/2025-26/browser-whoscored-20261007/`. '
        'Static collection alone does not capture the WhoScored browser tables. No database migration, source activation or rating change occurs.', '']
    (folder / 'README.md').write_text('\n'.join(index), encoding='utf-8')
    (folder / 'source-selection.md').write_text('# Source stack status\n\n' + POLICY + '\n\n' + summary +
        '\nOpta and PitchAPI remain the existing core; Understat remains private. This update inventories counts rather than '
        'ranking sources by coverage. WhoScored is now confirmed browser-accessible and supplies a Fouled column. '
        'Full collection, player identity mapping and public reuse remain separate implementation work.\n', encoding='utf-8')
    (folder / 'coverage-matrix.md').write_text('# Source feature inventory\n\n' + POLICY + '\n\n' + summary +
        '\nPer-column counts and full collected column lists are in the individual source reports. The prior coverage thresholds '
        'are retained only in immutable historical audit snapshots.\n', encoding='utf-8')
    return {'reports': str(folder), 'audit': str(output / f'audit-{digest}.json'), 'source_counts': rows, 'coverage_gate': None}
