"""Feature coverage acceptance, separating missing measurements from undefined rates."""
from scout.striker_features import FEATURES, derive


def coverage(rows, threshold=90.0):
    if not 0 < threshold <= 100:
        raise ValueError('Coverage threshold must be greater than zero and at most 100')
    counts = {}
    for feature in FEATURES:
        available = undefined = missing = not_applicable = 0
        for row in rows:
            raw = dict(row['totals'])
            raw['finishing_delta'] = (raw['non_penalty_goals'] - raw['npxg']
                if raw.get('non_penalty_goals') is not None and raw.get('npxg') is not None else None)
            raw['aerial_duels_attempted'] = (raw['aerial_duels_won'] + raw['aerial_duels_lost']
                if raw.get('aerial_duels_won') is not None and raw.get('aerial_duels_lost') is not None else None)
            if derive(row['totals'])[feature.key] is not None:
                available += 1
            elif raw.get(feature.numerator) is not None and raw.get(feature.denominator) == 0:
                undefined += 1
                # Observed zero attempts establish N/A, not absent source evidence.
                # Zero exposure never establishes a usable season rate.
                if feature.denominator != 'minutes' and raw.get(feature.numerator) == 0:
                    not_applicable += 1
            else:
                missing += 1
        percent = 100 * available / len(rows) if rows else None
        accounted = 100 * (available + not_applicable) / len(rows) if rows else None
        counts[feature.key] = {'label': feature.label, 'available': available, 'missing_measurement': missing,
            'undefined_zero_denominator': undefined, 'total': len(rows), 'coverage_pct': percent,
            'not_applicable_zero_attempts': not_applicable, 'evidence_coverage_pct': accounted,
            'accepted': accounted is not None and accounted >= threshold}
    return {'threshold_pct': threshold, 'population': 'player/league rows across all positions',
        'coverage_policy': 'observed-zero-attempts-na-v2',
        'players': len(rows), 'accepted_features': sum(v['accepted'] for v in counts.values()),
        'all_features_accepted': all(v['accepted'] for v in counts.values()), 'features': counts}


def audit(rows, threshold=90.0):
    leagues = sorted({row['competition'] for row in rows})
    return {'all_players': coverage(rows, threshold),
        'minimum_900_minutes': coverage([r for r in rows if (r['totals'].get('minutes') or 0) >= 900], threshold),
        'by_league': {league: coverage([r for r in rows if r['competition'] == league], threshold)
                      for league in leagues},
        'activated': False,
        'limitations': ['Coverage does not establish complete season inventories, eligible roles or calibrated ratings.',
                       'Observed zero-attempt ratios stay N/A and count as explained evidence; missing counts do not.',
                       'Zero minutes remain unavailable and do not count as explained feature evidence.']}
