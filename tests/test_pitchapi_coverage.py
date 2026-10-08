import pytest

from scout.pitchapi import canonical_records
from scout.pitchapi_coverage import audit, coverage


def test_exact_90_percent_boundary_and_undefined_ratio():
    rows = [{'competition': 'England', 'totals': {'minutes': 1000.0, 'shots': 1.0,
             'shots_on_target': 0.0}} for _ in range(10)]
    rows[-1]['totals']['shots_on_target'] = None
    result = coverage(rows)
    assert result['features']['sot90']['coverage_pct'] == 90.0
    assert result['features']['sot90']['accepted']
    rows[-2]['totals']['shots_on_target'] = None
    assert not coverage(rows)['features']['sot90']['accepted']
    rows[0]['totals']['shots'] = 0.0
    ratio = coverage(rows)['features']['sot_pct']
    assert ratio['missing_measurement'] == 2
    assert ratio['undefined_zero_denominator'] == 1
    assert ratio['available'] == 7
    assert ratio['not_applicable_zero_attempts'] == 1
    assert ratio['evidence_coverage_pct'] == 80


def test_known_zero_attempts_count_as_na_but_not_missing_or_invalid_counts():
    rows = [{'competition': 'England', 'totals': {'minutes': 1000, 'shots': 0,
             'shots_on_target': 0}} for _ in range(10)]
    rows[-1]['totals']['shots_on_target'] = None
    ratio = coverage(rows)['features']['sot_pct']
    assert ratio['coverage_pct'] == 0 and ratio['evidence_coverage_pct'] == 90
    assert ratio['accepted'] and ratio['not_applicable_zero_attempts'] == 9
    rows[0]['totals']['shots_on_target'] = 1  # Contradictory counts are not a valid N/A.
    assert not coverage(rows)['features']['sot_pct']['accepted']
    assert coverage([{'totals': {'minutes': 0, 'shots': 0}}])['features']['shots90']['evidence_coverage_pct'] == 0


def test_empty_and_exposure_populations():
    assert coverage([])['features']['shots90']['coverage_pct'] is None
    assert not coverage([])['all_features_accepted']
    result = audit([{'competition': 'England', 'totals': {'minutes': 800.0, 'shots': 0.0}},
                    {'competition': 'Spain', 'totals': {'minutes': 950.0, 'shots': 2.0}}])
    assert result['all_players']['players'] == 2
    assert result['minimum_900_minutes']['players'] == 1
    assert set(result['by_league']) == {'England', 'Spain'}
    with pytest.raises(ValueError):
        coverage([], 101)


def test_missing_or_failed_coverage_never_enters_rating_import():
    assert canonical_records([{}], {'complete': True}, {}) == []
    assert canonical_records([{}], {'complete': True,
        'feature_coverage': {'all_features_accepted': False}}, {}) == []
