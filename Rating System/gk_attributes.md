# GK Attributes

**Status: implemented provisional registry v1 — 8 October 2026.**

Weights are loaded from [position_rating_weights_config.yaml](position_rating_weights_config.yaml). A registry does not guarantee every player has enough evidence or peers for a rating.

**Performance season:** 2025/26. **Research/inventory date:** 7 October 2026.

Goalkeeper: separate peer population; use measured shot stopping, claims, interventions and distribution rather than fake speed/reflex ratings.

All weights below are provisional Scout design judgments, not fitted results or proprietary EA coefficients. Left/right variants have identical weights and a shared peer population; foot preference, side experience and tactical fit remain separate.

## Six abilities and overall weights

| Ability | Card label | OVR weight |
|---|---|---:|
| Shot Stopping | STP | 40% |
| Claims / Aerial Control | CLM | 15% |
| Sweeping / Interventions | SWP | 10% |
| Build-Up Distribution | BLD | 15% |
| Long Distribution | LNG | 10% |
| Ball Security | SEC | 10% |

**Overall weights sum to 100%.** Standardize each ability before combining them, then re-standardize OVR. Display `max(1, 50 + 15 × z)` with no upper cap. See [shared calculation and source rules](position_attribute_methods.md).

## Feature definitions and weights

Each table sums to 100% **within that ability**. `+` means higher is preferable; `−` means lower is preferable after stabilization. `/90` uses matched provider exposure, not a different source’s season minutes.

### 1. Shot Stopping — 40% of OVR

Chance-adjusted prevention is primary; save percentage is supplementary.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Goals prevented /90 | `goals_prevented` | `90 × goals_prevented / keeper minutes` | + | 75% |
| Save percentage | `save_perc` | `Use provider save_perc; validate its attempts contract` | + | 25% |

Interpretation:

- **Goals prevented /90:** Opta signed shot-stopping residual; confirm xGOT, own-goal and penalty conventions. Do not replace with raw conceded goals.
- **Save percentage:** Less chance-adjusted than goals prevented; includes shot-difficulty and team effects.

### 2. Claims / Aerial Control — 15% of OVR

Successful claim outcomes and limited activity weighting.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Claim success | raw appearance: `advanced.goalkeeping.claims_won`, `advanced.goalkeeping.claims` | `100 × Σclaims_won / Σclaims` | + | 75% |
| Successful claims /90 | raw appearance: `advanced.goalkeeping.claims_won` | `90 × Σclaims_won / matched keeper minutes` | + | 25% |

Interpretation:

- **Claim success:** Claim attempts and successful outcomes; not crosses-claimed/opponent-crosses unless the provider establishes that denominator.
- **Successful claims /90:** Activity proxy, not chance-adjusted command of area. Do not add stats.keeper_high_claim to overlapping claims_won.

### 3. Sweeping / Interventions — 10% of OVR

A provisional intervention profile; exact sweeping success/location remain missing.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Sweeper actions /90 | raw appearance: `advanced.goalkeeping.sweeper_actions` | `90 × Σsweeper_actions / matched keeper minutes` | + | 70% |
| Keeper clearances /90 | raw appearance: `stats.clearances.value` | `90 × Σkeeper clearances / matched keeper minutes` | + | 20% |
| Keeper interceptions /90 | raw appearance: `stats.interceptions.value` | `90 × Σkeeper interceptions / matched keeper minutes` | + | 10% |

Interpretation:

- **Sweeper actions /90:** Outside-goal intervention activity; higher frequency does not establish safer decision-making.
- **Keeper clearances /90:** Only verified GK appearances. Not automatically outside-area clearances; context and location needed.
- **Keeper interceptions /90:** Only verified GK appearances; broad intervention proxy, not exact sweeping quality.

### 4. Build-Up Distribution — 15% of OVR

Completion and small-weight circulation volume, without claiming short/pressured passing isolation.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Pass completion | raw appearance: `stats.accurate_passes.value`, `stats.accurate_passes.total` | `100 × Σaccurate_passes.value / Σaccurate_passes.total` | + | 60% |
| Distribution completion | raw appearance: `advanced.goalkeeping.distribution_accuracy`, `advanced.goalkeeping.distributions` | `Σ(match accuracy × distributions) / Σdistributions, after verifying percentage unit` | + | 25% |
| Successful passes /90 | raw appearance: `stats.accurate_passes.value` | `90 × Σaccurate_passes.value / matched keeper minutes` | + | 15% |

Interpretation:

- **Pass completion:** Keeper-specific appearances; use common match window and verify numerator/denominator metadata.
- **Distribution completion:** Weighted completion, never mean of match percentages. Recover exact numerator where available; rounded percentages can only give an approximate aggregate.
- **Successful passes /90:** Small style-dependent build-up involvement signal, not a pure quality measure.

### 5. Long Distribution — 10% of OVR

Completion dominates launch volume; distance/launch propensity is descriptive only.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Long-ball completion | raw appearance: `stats.long_balls_accurate.value`, `stats.long_balls_accurate.total` | `100 × Σaccurate long balls / Σattempted long balls` | + | 80% |
| Accurate long balls /90 | raw appearance: `stats.long_balls_accurate.value` | `90 × Σaccurate long balls / matched keeper minutes` | + | 20% |

Interpretation:

- **Long-ball completion:** Keeper-only appearances. No claim that launch_pct measures accuracy; launch_pct measures propensity.
- **Accurate long balls /90:** Successful long distribution volume; tactical responsibility strongly affects opportunities.

### 6. Ball Security — 10% of OVR

Conservative control-loss proxy; cannot stand in for catching/handling or positioning.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Keeper miscontrols /90 | raw appearance: `advanced.carrying.miscontrols` | `90 × Σkeeper miscontrols / matched keeper minutes` | − | 60% |
| Keeper dispossessions /90 | raw appearance: `advanced.carrying.dispossessed` | `90 × Σkeeper dispossessed / matched keeper minutes` | − | 40% |

Interpretation:

- **Keeper miscontrols /90:** Rare control-loss signal; absence of pressure exposure limits interpretation.
- **Keeper dispossessions /90:** Rare on-ball loss; only complete known windows support zero-event interpretation.

## What is actually in the master

The inspected private master has **3,561 player/league rows and 227 wide columns**. Counts below are recorded input cells, including recorded zeros, excluding `unrecorded_zero`. They include low-minute players and all roles; they are **not** eligible-role counts or guaranteed derived-feature coverage. No 90% gate is applied.

| Season-column input | Recorded master rows | Zero-filled rows | Selected sources |
|---|---:|---:|---|
| `goals_prevented` | 190 | 3,371 | opta |
| `save_perc` | 190 | 3,371 | opta |

### Raw-match inputs retained in the master

These exist in `observations`, not the 227-column wide season view. Numeric player/league counts include recorded zeros; generic passing/control fields include outfield players. GK-only counts for those fields need a verified position join. Counts are neither complete-season coverage nor a merged-player total.

| PitchAPI native path | Numeric observations | Provider player/league records |
|---|---:|---:|
| `advanced.carrying.dispossessed` | 53,938 | 2,761 |
| `advanced.carrying.miscontrols` | 53,938 | 2,761 |
| `advanced.goalkeeping.claims` | 3,494 | 188 |
| `advanced.goalkeeping.claims_won` | 3,494 | 188 |
| `advanced.goalkeeping.distribution_accuracy` | 3,494 | 188 |
| `advanced.goalkeeping.distributions` | 3,494 | 188 |
| `advanced.goalkeeping.sweeper_actions` | 3,494 | 188 |
| `stats.accurate_passes.total` | 54,183 | 2,770 |
| `stats.accurate_passes.value` | 54,183 | 2,770 |
| `stats.clearances.value` | 54,183 | 2,770 |
| `stats.interceptions.value` | 54,183 | 2,770 |
| `stats.long_balls_accurate.total` | 37,921 | 2,545 |
| `stats.long_balls_accurate.value` | 37,921 | 2,545 |

**GK implementation boundary:** Shot Stopping has wide season inputs for 190 master rows. The other five ability templates require a new GK aggregation/mapping path over captured appearances. A numeric raw path does not authorize a full-season sum. Confirm match deduplication, actual keeper exposure, units, attempts and complete windows first. Missing whole abilities cannot be replaced by zeros or silently dropped from OVR.

Ball Security and Sweeping are deliberately labelled provisional proxies. If their stabilized reference variance is zero, withhold the affected ability and OVR; do not award every goalkeeper a high score for a flat zero population. Save technique, reflex time, positioning error, claimable-cross opportunity, sweeping success and one-on-one shot context remain unmeasured. These are future investigations, not hidden scored features.

## Role-specific limits and review decisions

- Correlated inputs (e.g. goals/xG; take-on wins/success share; duel wins/share) are intentionally limited to a parent/family budget. Review correlations and weight sensitivity before implementation; do not add totals and /90 forms as extra abilities.
- Repeated inputs across different parents are stored once. Overall influence is the parent-weight × feature-weight path before standardization; overlapping standardized composites still need empirical sensitivity checks.
- Exclude provider overall ratings, age, nationality, fee, height, weight and unverified pace/stamina/strength guesses from performance scoring.
- Review: approve the six parent names and OVR weights; then approve feature semantics, within-parent weights and each contextual proxy. No engine, UI or data-release changes are made by this document.

## Research basis

EA’s published attribute families inform the six-part presentation, but Scout uses retrievable performance observations. Pace, reflexes and pure strength cannot be reconstructed from the current aggregate event data. [EA official attribute families (legacy chemistry-style reference)](https://media.contentapi.ea.com/content/dam/fifa/en-us/images-migrated/2018/09/chemistry-styles.pdf).

The proposed feature allocation is Scout’s inference from role duties and the local inventory, not a copied commercial rating formula. [Opta event definitions](https://www.statsperform.com/opta-event-definitions/) supplies event-meaning checks. Detailed shared research notes are in [the review index](position_attributes_review.md).

Keep shot stopping, claims, interventions and distribution distinct, while avoiding an invented positioning score: [StatsBomb goalkeeper radar measures](https://blogarchive.statsbomb.com/articles/soccer/introducing-goalkeeper-radars/).

**Feature slots:** 14. **Distinct proposed metrics:** 14. Repeated inputs are not additional raw features.
