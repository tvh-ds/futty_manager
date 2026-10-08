# Striker data: 90% coverage audit

Checked 2026-10-06. Performance window: completed 2025/26 season.

Subsequent update: the user confirmed Opta consent and supplied a historical season
link. Five historical public feeds have now been collected. They support 20/37
features; 17 pass 90% in their validated positive-minute population. See
[the Opta audit](opta-analyst-coverage.md) for exact counts, population differences
and the fields still unavailable. The earlier Opta permission blocker below is
superseded for this user-authorized source.

## Acceptance and implementation

Each of the 37 required features must have a computable value for at least 90% of the collected player/league rows. This is feature-level coverage, not a claim that 90% of players have complete profiles. Missing measurements and mathematically undefined rates both count as unavailable, with separate counts in the report. No missing value is converted to zero.

`scout audit-pitchapi SOURCE OUTPUT --threshold 90` writes global, per-league and minimum-900-minute diagnostics. The canonical PitchAPI rating import now requires the collection's 90% feature gate to pass, in addition to existing season completeness, identity, measurement-version and calibration gates. It does not accept a missing coverage report.

The collected population contains all positions, including goalkeepers, and is not an independently approved striker eligibility cohort. The 900-minute subset is a diagnostic, not a silent change to the user's requested denominator. Players appearing in different leagues can contribute separate rows. Inventory completeness remains independently blocked by five quarantined matches.

## PitchAPI result

The full cached backfill has 2,770 player/league rows. **27/37 features pass 90%; none of the rows have all 37 features.** The 1,584 rows with at least 900 minutes pass 31/37 features.

| Failing feature, all collected players | Coverage | Missing measurement | Undefined denominator |
|---|---:|---:|---:|
| Shots on target % | 82.71% | 0 | 479 |
| Non-penalty goals / shot | 82.71% | 0 | 479 |
| Non-penalty xG / shot | 82.71% | 0 | 479 |
| Offsides / 90 | 0.14% | 2,766 | 0 |
| Expected assists / 90 | 7.29% | 2,568 | 0 |
| Take-on success % | 78.81% | 217 | 370 |
| Duels won / 90 | 17.73% | 2,279 | 0 |
| Duel success % | 8.45% | 2,536 | 0 |
| Fouls won / 90 | 1.73% | 2,722 | 0 |
| Attacking-third tackles / 90 | 0.00% | 2,770 | 0 |

Pooled coverage can conceal league gaps:

| League | Player/league rows | Features passing 90% |
|---|---:|---:|
| England | 537 | 27 |
| France | 550 | 27 |
| Germany | 499 | 17 |
| Italy | 586 | 27 |
| Spain | 598 | 27 |

## Fresh crawling results

Made 40 fresh authenticated PitchAPI requests across ten matches: two match windows per league. For each match, requested base players, advanced players, half statistics and an individual player detail response. All requests succeeded; all ten base responses remained unchanged. The tested individual details supplied no non-null recovery of the missing fields.

Half statistics expose additional duel/foul values but are not a safe automatic replacement. Across the sample, summed half values conflicted with available full-match duel wins in 98 comparisons and duel attempts in 126. Eighteen of 314 half-stat player records had different summed minutes. Fouls-won sums agreed in the 150 comparable observations, but this small sample does not establish season-wide coverage or semantic equivalence. No half-stat values were merged into the release. Half responses did not recover numeric xA or offsides in the inspected sample.

[PitchAPI documentation](https://pitchapi.dev/) describes optional-field omissions, period-specific statistics and that half totals need not exactly reproduce full-match statistics. Its advanced xAG field is not silently substituted for xA. The publicly exposed timeline is not a complete defensive action stream suitable for deriving attacking-third tackles.

Evidence: `data/pitchapi/recheck-20261006/coverage-90.json`, `recheck.json` and immutable `snapshots/`. Original full backfill: `data/pitchapi/live-probe-2025/`.

## Alternative sources

| Source | Verified evidence | Decision |
|---|---|---|
| Understat | Fresh five-league 2025/26 probe: 2,775 validated rows, no quarantine; seven aggregate features, including source xA, present for every row in every league. | A promising xA source; not a solution for the remaining defensive/familiarity fields. Cross-provider identities, model definitions and publication permission remain unapproved. No automatic merge. |
| Football Leagues / Yuvron | Official schema includes nullable `expectedAssists` and detailed-appearance coverage. Public stats routes returned 401 without a separate key. Player list returns identities; stats require player detail calls; expected-assists leaderboard is capped at 100. Free tier advertises 500 requests/month. | Not verified numerically. The free quota cannot refresh roughly 2,700 individual player detail records monthly. Inspected player-stat schema does not supply the missing duel, foul, offside and attacking-third tackle set. |
| Big Balls Sports Data | Free access is current-season focused; historical player leaderboard/xG/xA access is advertised in paid tiers. | Does not establish strictly free 2025/26 missing-feature coverage. |
| foot.io | Invite-only keys; free current-season access; historical access paid. Docs exclude shot/xG redistribution and restrict event/lineup coverage. | Not a verified replacement for this completed-season feature registry. |
| Opta Analyst | Public advanced-stat displays exist; Stats Perform site terms restrict reuse on other websites without written consent. | No approved, free, complete batch source established. |
| Statbunker data feed | Advertised commercial feed with a time-limited free trial. | Not an ongoing strictly free source. |

Primary references: [Understat](https://understat.com/), [Football Leagues FAQ](https://football-api.yuvron.online/faq), [OpenAPI](https://football-api.yuvron.online/openapi.json), [free-tier quota](https://football-api.yuvron.online/), [Big Balls API](https://bigballsdata.com/soccer-api), [foot.io documentation](https://foot.io/docs), [Stats Perform terms](https://www.statsperform.com/terms-and-conditions/), [Statbunker feed](https://www.statbunker.com/competitions/FootballDataFeed).

Fresh Understat evidence: `data/striker-source-probes/understat-recheck-20261006/coverage.json` and per-league snapshots. Alternative schema/access evidence: `data/pitchapi/alternatives-20261006/`. No PitchAPI credentials were sent to alternative providers.

## Remaining work

No verified, approved, strictly free source combination currently provides all 37 features at the requested coverage. The real rating release therefore stays blocked.

1. Obtain explicit, consistently defined season counts for duels, fouls won and offsides, and spatial defensive actions for attacking-third tackles. A larger crawl of the same unchanged base schema cannot establish absent measurements.
2. Verify Understat xA semantics and reuse permissions, then review cross-provider identity/stint mappings before any versioned integration.
3. Resolve zero-attempt rates through an explicitly approved eligible-population policy or a changed feature definition. Additional crawling cannot make a genuine zero denominator valid; no such policy change has been applied.
4. Resolve the five quarantined match records and validate season inventories before publication.

Existing demonstration ratings remain labelled. No source fallback, imputation, feature omission or changed scoring weight has been used to claim the 90% requirement is met.

Verification: 52 focused ingestion, coverage and scoring tests passed; Ruff passed for the affected modules, scripts and tests. Tests cover the exact 90% boundary, missing versus undefined rates, empty populations and rejection of missing/failed coverage reports alongside existing integration/scoring regressions.
