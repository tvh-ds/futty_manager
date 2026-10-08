# Opta Analyst: completed 2025/26 feature audit

Collected 2026-10-06 with user-confirmed consent. No release was activated.

Later registry update: the user removed attacking-third tackles. The active
registry now has **36 unique features; 35 are supported across the combined
sources, and fouls won remains the only unsupported feature**. The earlier
37-feature audit below remains a dated account of the source inspection.
See `docs/striker-scoring.md` for the updated Defensive Activity weights.

## Updated N/A policy and combined coverage

The user subsequently approved counting verified zero-shot ratios as supported
features, with their values remaining N/A. The same zero-attempt rule applies to
other attempt-based ratios; unknown or contradictory counts do not qualify.
Numeric-value coverage and evidence coverage are now separate audit fields.
Zero-minute season rates still do not qualify as explained feature evidence.

Under this policy, PitchAPI passes 31/37 features in its pooled audited population,
and Opta passes 20/37 in its positive-minute population. Their feature-level union
is **35/37**. Earlier Understat aggregates and inspected shot data overlap with this
union and do not add another feature. The two remaining gaps are fouls won and
attacking-third tackles. The original API-Football adapter has a schema mapping
for fouls won but no collected live evidence, so it adds no verified feature.

This is the union of source capabilities, not an already merged dataset. Player,
team, season and metric-definition reconciliation remain required before claiming
90% coverage across one common player population. Germany's lower PitchAPI
advanced-field coverage also remains visible in the per-league audit.

Updated evidence: `data/pitchapi/recheck-20261006/coverage-90-na.json` and
`data/opta-analyst/season-2025-20261006/appearance-coverage-na.json`. Earlier
numeric-coverage results below are preserved as the pre-policy audit. The ratio
values and rating release have not been replaced with zeros or fabricated scores.
Verification after this policy update: 14 focused tests passed; Ruff passed.

## Findings

**20 of the 37 requested features are supported by the inspected public feeds**, using raw counts and transparent derivations. This is a statement about these downloaded feeds, not all Opta licensed products.

Across 2,577 validated player/team records with positive minutes, **17/37 pass the 90% computable-value threshold**. Every league individually passes these same 17 features. The three remaining supported shooting ratios each have 88.63% pooled coverage because of zero shot attempts. Among 1,471 validated records with at least 900 minutes, all 20 supported features pass 90%. These cohorts are diagnostics and have not replaced the requested acceptance population.

| Supported feature | Coverage, positive-minute records |
|---|---:|
| Non-penalty goals / 90 | 100% |
| Non-penalty xG / 90 | 100% |
| Goals above non-penalty xG / 90 | 100% |
| Shots / 90 | 100% |
| Shots on target / 90 | 100% |
| Shots on target % | 88.63% |
| Non-penalty goals / non-penalty shot | 88.63% |
| Non-penalty xG / non-penalty shot | 88.63% |
| Offsides / 90 | 100% |
| Assists / 90 | 100% |
| Expected assists / 90 | 100% |
| Through balls / 90 | 100% |
| Pass completion % | 99.15% |
| Duels won / 90 | 100% |
| Duel success % | 98.10% |
| Aerial duels won / 90 | 100% |
| Aerial success % | 93.60% |
| Interceptions / 90 | 100% |
| Recoveries / 90 | 100% |
| Blocks / 90 | 100% |

The other 17 requested features remain unavailable: shots inside the box, open-play xG, headed shots, opposition box touches, key passes, shot-creating actions, passes into the penalty area, attempted take-ons, successful take-ons, take-on success %, carries into the penalty area, carries into the final third, progressive carry distance, miscontrols, dispossessions, fouls won and attacking-third tackles.

The source offers `chances_created`, but it has not been substituted for the requested key-pass definition. `fouls_commited` is not fouls won. The source's `progressive_distance` contains negative observations; it has not been mapped to the requested unsigned progressive carry distance. Source rounded percentages do not replace undefined ratios. Aggregate duels use ground plus aerial counts with a separate measurement version requiring definition review before calibration or cross-provider merging.

## Population and validation

The feed has 3,051 raw player/team records, including 472 validated records with zero minutes. Two additional records are quarantined for inconsistent exposure across reports. Quarantined records count as unavailable in the full-inventory coverage audit rather than being dropped to inflate coverage. On that full inventory, **no per-feature computable coverage reaches 90%**, mainly because zero-minute records cannot have valid per-90 values. Raw count presence must not be confused with computable season features.

| League | Valid positive-minute records | Features passing 90% |
|---|---:|---:|
| England | 496 | 17 |
| Spain | 561 | 17 |
| Germany | 469 | 17 |
| Italy | 540 | 17 |
| France | 511 | 17 |

This inventory differs from PitchAPI's 2,770 player/league appearance records. Completeness, transfers, player identities and league aggregation need reconciliation. It is not valid to assume that 100% within Opta's returned population means 100% of the entire PitchAPI population can be filled. No name-only joins have been performed.

## Source discovery and reproduction

The user supplied [the Premier League 2025/26 page](https://optaplayerstats.statsperform.com/en_GB/soccer/premier-league-2025-2026/51r6ph2woavlbbpk8f29nynf8/opta-player-stats). The public competition catalogue and season-select menus supplied the other four historical IDs. Analyst's published stats-page JavaScript established the public feed path `https://dataviz.theanalyst.com/project-data/soccer/{season_id}/player-stats.json`.

| League | Verified 2025/26 identifier |
|---|---|
| England | `51r6ph2woavlbbpk8f29nynf8` |
| Spain | `80zg2v1cuqcfhphn56u4qpyqc` |
| Germany | `2bchmrj23l9u42d68ntcekob8` |
| Italy | `emdmtfr1v8rey2qru3xzfwges` |
| France | `dbxs75cag7zyip5re0ppsanmc` |

Code: `src/scout/opta_analyst_probe.py`. Command: `scout probe-opta-analyst NEW_OUTPUT_DIRECTORY --season 2025`. Output directories must be new; snapshots are bounded, checksum recorded, redirects rejected, hosts fixed, and no provider credentials are transmitted. Consent is recorded in the probe report.

Evidence: `data/opta-analyst/season-2025-20261006/coverage.json` and per-league `bronze.json`, `measurements.json`, `quarantine.json`. Discovery evidence: `data/opta-analyst/probe-20261006/` and the public season menus. The historical JSON feeds responded successfully without credentials. A separate public player-information endpoint returned 401 and was not retried or bypassed.

Next integration work is explicit identity/stint reconciliation, resolving the two source conflicts, versioned metric-definition review, and finding the remaining fields. Consent removes the previously unapproved-reuse blocker for this source; it does not remove statistical quality gates.

Verification: 13 focused Opta/coverage tests passed; Ruff passed. Tests cover identity/team joins, count arithmetic, missing fields, zero attempts/exposure, conflicting reports, duplicate inventories, unsafe URLs and preservation of release isolation.
