import json

import pytest

from scout.master_dataset import column_groups, compare_values, match_ws, resolve_cell, ws_records
from scout.master_export import safe_cell
from scout.master_priority import select_priority


def test_source_priority_selects_zero_and_falls_back_only_when_unavailable():
    candidates = [{'provider': 'whoscored', 'value': 30}, {'provider': 'understat', 'value': 25},
                  {'provider': 'pitchapi', 'value': 20}, {'provider': 'opta', 'value': 0}]
    assert select_priority(candidates)['value'] == 0
    candidates[-1]['value'] = None
    assert select_priority(candidates)['provider'] == 'pitchapi'
    candidates[-2]['value'] = None
    assert select_priority(candidates)['provider'] == 'understat'


def test_priority_does_not_arbitrarily_resolve_same_provider_disagreement():
    with pytest.raises(ValueError, match='within opta'):
        select_priority([{'provider': 'opta', 'value': 20}, {'provider': 'opta', 'value': 21}])


def test_readable_export_preserves_signed_numbers_and_escapes_formulas():
    assert safe_cell('-0.48') == '-0.48'
    assert safe_cell('=HYPERLINK("example")').startswith("'")
    assert safe_cell('0') == '0'


def test_exact_columns_merge_but_conflicting_values_remain_unavailable():
    groups, decisions = column_groups({('opta', 'shots'): {'p': 20}, ('pitchapi', 'shots'): {'p': 18}})
    assert len(groups) == 1
    assert decisions[0]['reason'] == 'exact_name'
    assert resolve_cell([20, 18]) == (None, 'source_conflict')
    assert resolve_cell([None, 0, 0]) == (0, 'observed')


def test_aliases_need_varied_matched_nonzero_values_and_no_scale_conversion():
    a = {str(i): i for i in range(25)}
    assert compare_values(a, a)['status'] == 'empirical_equivalent'
    assert compare_values(a, {k: v / 10 for k, v in a.items()})['status'] == 'different_values'
    zero = {str(i): 0 for i in range(50)}
    assert compare_values(zero, zero)['status'] == 'insufficient_overlap'
    groups, _ = column_groups({('opta', 'mins_played'): a, ('whoscored', 'Mins'): a})
    assert len(groups) == 1
    assert compare_values({'p': 10}, {'other': 10})['matched_rows'] == 0


def test_alias_merge_cannot_use_transitive_insufficient_evidence():
    a = {str(i): i for i in range(30)}
    groups, _ = column_groups({('opta', 'goals'): a, ('pitchapi', 'goals'): {'0': 0},
                              ('whoscored', 'Goals'): a})
    assert len(groups) == 2


def test_ws_identity_requires_both_exposure_fields_and_unique_candidate():
    identities = {'p': {'league': 'England', 'names': {'Test Player'}, 'sources': set()}}
    records = [{'league': 'England', 'id': '123', 'name': 'Test Player',
                'fields': {'Mins': ('numeric', 900, '900'), 'Apps': ('numeric', 10, '10')}}]
    vectors = {('opta', 'mins_played'): {'p': 900}, ('opta', 'apps'): {'p': 10}}
    assert match_ws(records, identities, vectors)[0][('England', '123')] == 'p'
    vectors[('opta', 'apps')]['p'] = 11
    assert match_ws(records, identities, vectors)[1][0]['status'] == 'unresolved'


def test_ws_blank_is_zero_and_total_category_preserved(tmp_path):
    doc = {'season': '2025/2026', 'url': 'https://www.whoscored.com/statistics', 'retrieved_at': '2026-10-07',
           'panels': [{'id': 'stage-top-player-stats-detailed',
                       'selectors': [{'id': 'category', 'value': 'shots'}, {'id': 'statsAccumulationType', 'value': '2'}],
                       'tables': [{'headers': ['Player', '', 'Apps', 'Mins', 'Total'],
                                   'rows': [{'player': '/players/123/show/test', 'team': '/teams/1/show/team',
                                             'cells': ['1\nTest Player\nTeam, 24, FW', '', '1', '90', '']}]}]}]}
    (tmp_path/'england-shots.json').write_text(json.dumps(doc))
    records, _ = ws_records(tmp_path)
    assert records[0]['fields']['shots.Total'] == ('numeric', 0, '')
    assert records[0]['name'] == 'Test Player'
    doc['panels'][0]['selectors'][1]['value'] = '0'
    (tmp_path/'england-shots.json').write_text(json.dumps(doc))
    records, _ = ws_records(tmp_path)
    assert records[0]['fields']['per_game.shots.Total'] == ('numeric', 0, '')
    assert 'shots.Total' not in records[0]['fields']
