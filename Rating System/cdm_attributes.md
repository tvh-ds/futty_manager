# CDM Attributes

**Status: implemented provisional registry v1 — 8 October 2026.**

Weights are loaded from [position_rating_weights_config.yaml](position_rating_weights_config.yaml). A registry does not guarantee every player has enough evidence or peers for a rating.

**Performance season:** 2025/26. **Research/inventory date:** 7 October 2026.

Holding midfielder: screening, retention and progression; LDM/RDM share the same role.

All weights below are provisional Scout design judgments, not fitted results or proprietary EA coefficients. Left/right variants have identical weights and a shared peer population; foot preference, side experience and tactical fit remain separate.

## Six abilities and overall weights

| Ability | Card label | OVR weight |
|---|---|---:|
| Screening / Recovery | SCR | 24% |
| Ground Duels | DUE | 18% |
| Ball Retention | RET | 20% |
| Build-Up / Progression | PRO | 20% |
| Aerial Contribution | AIR | 10% |
| Discipline | DIS | 8% |

**Overall weights sum to 100%.** Standardize each ability before combining them, then re-standardize OVR. Display `max(1, 50 + 15 × z)` with no upper cap. See [shared calculation and source rules](position_attribute_methods.md).

## Feature definitions and weights

Each table sums to 100% **within that ability**. `+` means higher is preferable; `−` means lower is preferable after stabilization. `/90` uses matched provider exposure, not a different source’s season minutes.

### 1. Screening / Recovery — 24% of OVR

Pass interception and recovery with some tackling activity.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Interceptions /90 | `interceptions` | `90 × interceptions / minutes` | + | 40% |
| Recoveries /90 | `recoveries` | `90 × recoveries / minutes` | + | 35% |
| Tackles /90 | `tackles` | `90 × tackles / minutes` | + | 15% |
| Shot blocks /90 | `blocks` | `90 × blocks / minutes` | + | 10% |

Interpretation:

- **Interceptions /90:** Reading/action activity; opportunities depend on opposition possession.
- **Recoveries /90:** Ball recovery activity; not a measured pressing-success rate.
- **Tackles /90:** Activity proxy. Opta tackles include won/lost possession outcomes; not attempted challenges or tackle success.
- **Shot blocks /90:** Use Opta shot-block scope. A fallback must confirm the same definition; do not assume blocked passes/crosses are equivalent.

### 2. Ground Duels — 18% of OVR

Ground contest outcomes, not unobserved pure tackling success.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Ground duel win share | `ground_duels_won`, `ground_duels` | `100 × ground_duels_won / ground_duels` | + | 60% |
| Ground duels won /90 | `ground_duels_won` | `90 × ground_duels_won / minutes` | + | 40% |

Interpretation:

- **Ground duel win share:** Pair matched outcomes/attempts from Opta. This is not tackle/dribbled-past success.
- **Ground duels won /90:** Opta ground duels are broad contests, not exclusively defensive 1v1 challenges.

### 3. Ball Retention — 20% of OVR

A pivot must limit control losses; safe passing alone is insufficient.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Miscontrols /90 | `miscontrols` | `90 × miscontrols / minutes` | − | 30% |
| Dispossessed /90 | `dispossessed` | `90 × dispossessed / minutes` | − | 30% |
| Pass completion | `successful_passes`, `passes` | `100 × successful_passes / passes` | + | 25% |
| Successful passes /90 | `successful_passes` | `90 × successful_passes / minutes` | + | 15% |

Interpretation:

- **Miscontrols /90:** Recorded control losses; low counts can also reflect limited receiving responsibility.
- **Dispossessed /90:** Loss while in possession; use carrying/role context and do not infer pressure resistance directly.
- **Pass completion:** Same-provider denominator. Ordinary completion is a limited retention proxy, not vision or pressured-pass quality.
- **Successful passes /90:** Small-weight circulation activity; heavily team-style dependent.

### 4. Build-Up / Progression — 20% of OVR

Advance and connect possessions without needing to make the final assist.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Successful final-third passes /90 | `successful_final_third_passes` | `90 × successful_final_third_passes / minutes` | + | 30% |
| Progressive carries /90 | `progressive_carries` | `90 × progressive_carries / minutes` | + | 20% |
| Progressive carry distance /90 | `progressive_distance` | `90 × progressive_distance / minutes` | + | 15% |
| Successful through balls /90 | `successful_through_balls` | `90 × successful_through_balls / minutes` | + | 15% |
| xGBuildup /90 | `xGBuildup` | `90 × xGBuildup / Understat time` | + | 20% |

Interpretation:

- **Successful final-third passes /90:** Provider final-third passing category. Do not rename as progressive passes or entries until start/end-zone semantics are verified.
- **Progressive carries /90:** Opta progressive-carry criterion; preserve definition/version.
- **Progressive carry distance /90:** Opta carries.overall.progressive_distance, not progressive passing distance. Signed observations are retained; do not force absolute values. PitchAPI progressive_carry_distance is not automatically equivalent.
- **Successful through balls /90:** Prefer successful deliveries to attempted-volume alone.
- **xGBuildup /90:** Understat possession-chain involvement before shot/assist; team-dependent, private-use evidence, not OBV or xT.

### 5. Aerial Contribution — 10% of OVR

Second-ball and aerial-contest outcomes, without height scoring.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Aerial duel win share | `aerial_duels_won`, `aerial_duels` | `100 × aerial_duels_won / aerial_duels` | + | 65% |
| Aerial duels won /90 | `aerial_duels_won` | `90 × aerial_duels_won / minutes` | + | 35% |

Interpretation:

- **Aerial duel win share:** Use Opta pair. PitchAPI fallback uses aerial_duels_won / (aerial_duels_won + aerial_duels_lost), with its own minutes.
- **Aerial duels won /90:** Successful aerial involvement; height itself is excluded.

### 6. Discipline — 8% of OVR

Constrain avoidable damaging infringements; stabilize rare outcomes.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Fouls committed /90 | `fouls_commited` | `90 × fouls_commited / minutes` | − | 45% |
| Yellow cards /90 | `yellows` | `90 × yellows / minutes` | − | 15% |
| Red cards /90 | `reds` | `90 × reds / minutes` | − | 20% |
| Penalties conceded /90 | `pens_conceded` | `90 × pens_conceded / minutes` | − | 20% |

Interpretation:

- **Fouls committed /90:** Native spelling retained. Tactical foul context and referee effects require caution.
- **Yellow cards /90:** Discipline proxy; do not imply aggression or effort is intrinsically bad.
- **Red cards /90:** Rare events; heavy stabilization and review of second-yellow semantics required.
- **Penalties conceded /90:** Rare damaging events; not goalkeeping penalty-save ability.

## What is actually in the master

The inspected private master has **3,561 player/league rows and 227 wide columns**. Counts below are recorded input cells, including recorded zeros, excluding `unrecorded_zero`. They include low-minute players and all roles; they are **not** eligible-role counts or guaranteed derived-feature coverage. No 90% gate is applied.

| Season-column input | Recorded master rows | Zero-filled rows | Selected sources |
|---|---:|---:|---|
| `aerial_duels` | 2,576 | 985 | opta |
| `aerial_duels_won` | 2,918 | 643 | opta, pitchapi |
| `blocks` | 2,918 | 643 | opta, pitchapi |
| `dispossessed` | 2,769 | 792 | pitchapi |
| `fouls_commited` | 2,576 | 985 | opta |
| `ground_duels` | 2,576 | 985 | opta |
| `ground_duels_won` | 2,576 | 985 | opta |
| `interceptions` | 2,918 | 643 | opta, pitchapi |
| `miscontrols` | 2,553 | 1,008 | pitchapi |
| `passes` | 2,576 | 985 | opta |
| `pens_conceded` | 2,576 | 985 | opta |
| `progressive_carries` | 2,576 | 985 | opta |
| `progressive_distance` | 2,576 | 985 | opta |
| `recoveries` | 2,917 | 644 | opta, pitchapi |
| `reds` | 2,576 | 985 | opta |
| `successful_final_third_passes` | 2,576 | 985 | opta |
| `successful_passes` | 2,576 | 985 | opta |
| `successful_through_balls` | 2,576 | 985 | opta |
| `tackles` | 2,576 | 985 | opta |
| `xGBuildup` | 2,774 | 787 | understat |
| `yellows` | 2,576 | 985 | opta |
## Role-specific limits and review decisions

- Detailed position evidence must distinguish CM, CAM and CDM. Do not infer the role from whichever weighted score is highest.
- Build-up xG is possession-chain involvement, not marginal action value. Completion is a modest proxy; it cannot establish vision, press resistance or ball speed.
- Defensive volume depends on opposition possession, territory and tactical assignment. These are transparent provisional production scores, not a claim of isolated defensive quality.
- High-line recovery pace, marking, coordination and pressured receiving need spatial/tracking evidence. They are not measured by tackles, interceptions or carrying metres.
- Correlated inputs (e.g. goals/xG; take-on wins/success share; duel wins/share) are intentionally limited to a parent/family budget. Review correlations and weight sensitivity before implementation; do not add totals and /90 forms as extra abilities.
- Repeated inputs across different parents are stored once. Overall influence is the parent-weight × feature-weight path before standardization; overlapping standardized composites still need empirical sensitivity checks.
- Exclude provider overall ratings, age, nationality, fee, height, weight and unverified pace/stamina/strength guesses from performance scoring.
- Review: approve the six parent names and OVR weights; then approve feature semantics, within-parent weights and each contextual proxy. No engine, UI or data-release changes are made by this document.

## Research basis

EA’s published attribute families inform the six-part presentation, but Scout uses retrievable performance observations. Pace, reflexes and pure strength cannot be reconstructed from the current aggregate event data. [EA official attribute families (legacy chemistry-style reference)](https://media.contentapi.ea.com/content/dam/fifa/en-us/images-migrated/2018/09/chemistry-styles.pdf).

The proposed feature allocation is Scout’s inference from role duties and the local inventory, not a copied commercial rating formula. [Opta event definitions](https://www.statsperform.com/opta-event-definitions/) supplies event-meaning checks. Detailed shared research notes are in [the review index](position_attributes_review.md).

Role templates support balancing production, creation, carrying and defensive context: [Hudl StatsBomb positional radar methodology](https://blogarchive.statsbomb.com/articles/soccer/new-statsbomb-radars-2023-update/).

**Feature slots:** 21. **Distinct proposed metrics:** 21. Repeated inputs are not additional raw features.
