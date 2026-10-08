# CB Attributes

**Status: implemented provisional registry v1 — 8 October 2026.**

Weights are loaded from [position_rating_weights_config.yaml](position_rating_weights_config.yaml). A registry does not guarantee every player has enough evidence or peers for a rating.

**Performance season:** 2025/26. **Research/inventory date:** 7 October 2026.

Centre-back: aerial and ground contests, interventions and useful build-up. LCB/RCB grouped; left-foot suitability stays separate.

All weights below are provisional Scout design judgments, not fitted results or proprietary EA coefficients. Left/right variants have identical weights and a shared peer population; foot preference, side experience and tactical fit remain separate.

## Six abilities and overall weights

| Ability | Card label | OVR weight |
|---|---|---:|
| Ground Defending | GRD | 24% |
| Aerial Defending | AIR | 22% |
| Reading / Interventions | INT | 18% |
| Build-Up Passing | PAS | 16% |
| Carrying / Control | CAR | 10% |
| Discipline | DIS | 10% |

**Overall weights sum to 100%.** Standardize each ability before combining them, then re-standardize OVR. Display `max(1, 50 + 15 × z)` with no upper cap. See [shared calculation and source rules](position_attribute_methods.md).

## Feature definitions and weights

Each table sums to 100% **within that ability**. `+` means higher is preferable; `−` means lower is preferable after stabilization. `/90` uses matched provider exposure, not a different source’s season minutes.

### 1. Ground Defending — 24% of OVR

Use contest outcomes and interceptions; counts alone cannot establish isolation defending.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Ground duel win share | `ground_duels_won`, `ground_duels` | `100 × ground_duels_won / ground_duels` | + | 50% |
| Ground duels won /90 | `ground_duels_won` | `90 × ground_duels_won / minutes` | + | 20% |
| Tackles /90 | `tackles` | `90 × tackles / minutes` | + | 20% |
| Interceptions /90 | `interceptions` | `90 × interceptions / minutes` | + | 10% |

Interpretation:

- **Ground duel win share:** Pair matched outcomes/attempts from Opta. This is not tackle/dribbled-past success.
- **Ground duels won /90:** Opta ground duels are broad contests, not exclusively defensive 1v1 challenges.
- **Tackles /90:** Activity proxy. Opta tackles include won/lost possession outcomes; not attempted challenges or tackle success.
- **Interceptions /90:** Reading/action activity; opportunities depend on opposition possession.

### 2. Aerial Defending — 22% of OVR

Win share dominates volume to limit low-block/opportunity bias.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Aerial duel win share | `aerial_duels_won`, `aerial_duels` | `100 × aerial_duels_won / aerial_duels` | + | 70% |
| Aerial duels won /90 | `aerial_duels_won` | `90 × aerial_duels_won / minutes` | + | 30% |

Interpretation:

- **Aerial duel win share:** Use Opta pair. PitchAPI fallback uses aerial_duels_won / (aerial_duels_won + aerial_duels_lost), with its own minutes.
- **Aerial duels won /90:** Successful aerial involvement; height itself is excluded.

### 3. Reading / Interventions — 18% of OVR

Interceptions and recovery plus limited blocks/clearances.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Interceptions /90 | `interceptions` | `90 × interceptions / minutes` | + | 35% |
| Recoveries /90 | `recoveries` | `90 × recoveries / minutes` | + | 25% |
| Shot blocks /90 | `blocks` | `90 × blocks / minutes` | + | 25% |
| Clearances /90 | `clearances` | `90 × clearances / minutes` | + | 15% |

Interpretation:

- **Interceptions /90:** Reading/action activity; opportunities depend on opposition possession.
- **Recoveries /90:** Ball recovery activity; not a measured pressing-success rate.
- **Shot blocks /90:** Use Opta shot-block scope. A fallback must confirm the same definition; do not assume blocked passes/crosses are equivalent.
- **Clearances /90:** Emergency/box intervention volume; low-block context can inflate it, so its weight is limited.

### 4. Build-Up Passing — 16% of OVR

Retain and advance circulation; modest volume contribution.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Pass completion | `successful_passes`, `passes` | `100 × successful_passes / passes` | + | 35% |
| Successful final-third passes /90 | `successful_final_third_passes` | `90 × successful_final_third_passes / minutes` | + | 30% |
| Final-third pass completion | `successful_final_third_passes`, `total_final_third_passes` | `100 × successful_final_third_passes / total_final_third_passes` | + | 15% |
| Successful through balls /90 | `successful_through_balls` | `90 × successful_through_balls / minutes` | + | 10% |
| Successful passes /90 | `successful_passes` | `90 × successful_passes / minutes` | + | 10% |

Interpretation:

- **Pass completion:** Same-provider denominator. Ordinary completion is a limited retention proxy, not vision or pressured-pass quality.
- **Successful final-third passes /90:** Provider final-third passing category. Do not rename as progressive passes or entries until start/end-zone semantics are verified.
- **Final-third pass completion:** Completion within the same provider category; no pressure inference.
- **Successful through balls /90:** Prefer successful deliveries to attempted-volume alone.
- **Successful passes /90:** Small-weight circulation activity; heavily team-style dependent.

### 5. Carrying / Control — 10% of OVR

Step forward with the ball without penalizing through a fictional position penalty.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Progressive carries /90 | `progressive_carries` | `90 × progressive_carries / minutes` | + | 30% |
| Progressive carry distance /90 | `progressive_distance` | `90 × progressive_distance / minutes` | + | 25% |
| Carries into final third /90 | `carries_into_final_third` | `90 × carries_into_final_third / minutes` | + | 15% |
| Miscontrols /90 | `miscontrols` | `90 × miscontrols / minutes` | − | 15% |
| Dispossessed /90 | `dispossessed` | `90 × dispossessed / minutes` | − | 15% |

Interpretation:

- **Progressive carries /90:** Opta progressive-carry criterion; preserve definition/version.
- **Progressive carry distance /90:** Opta carries.overall.progressive_distance, not progressive passing distance. Signed observations are retained; do not force absolute values. PitchAPI progressive_carry_distance is not automatically equivalent.
- **Carries into final third /90:** Field advancement; not proof of beating a defensive line.
- **Miscontrols /90:** Recorded control losses; low counts can also reflect limited receiving responsibility.
- **Dispossessed /90:** Loss while in possession; use carrying/role context and do not infer pressure resistance directly.

### 6. Discipline — 10% of OVR

Rare damaging actions matter but need heavy stabilization.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Fouls committed /90 | `fouls_commited` | `90 × fouls_commited / minutes` | − | 40% |
| Penalties conceded /90 | `pens_conceded` | `90 × pens_conceded / minutes` | − | 30% |
| Red cards /90 | `reds` | `90 × reds / minutes` | − | 20% |
| Yellow cards /90 | `yellows` | `90 × yellows / minutes` | − | 10% |

Interpretation:

- **Fouls committed /90:** Native spelling retained. Tactical foul context and referee effects require caution.
- **Penalties conceded /90:** Rare damaging events; not goalkeeping penalty-save ability.
- **Red cards /90:** Rare events; heavy stabilization and review of second-yellow semantics required.
- **Yellow cards /90:** Discipline proxy; do not imply aggression or effort is intrinsically bad.

## What is actually in the master

The inspected private master has **3,561 player/league rows and 227 wide columns**. Counts below are recorded input cells, including recorded zeros, excluding `unrecorded_zero`. They include low-minute players and all roles; they are **not** eligible-role counts or guaranteed derived-feature coverage. No 90% gate is applied.

| Season-column input | Recorded master rows | Zero-filled rows | Selected sources |
|---|---:|---:|---|
| `aerial_duels` | 2,576 | 985 | opta |
| `aerial_duels_won` | 2,918 | 643 | opta, pitchapi |
| `blocks` | 2,918 | 643 | opta, pitchapi |
| `carries_into_final_third` | 2,553 | 1,008 | pitchapi |
| `clearances` | 2,576 | 985 | opta |
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
| `total_final_third_passes` | 2,576 | 985 | opta |
| `yellows` | 2,576 | 985 | opta |
## Role-specific limits and review decisions

- Defensive volume depends on opposition possession, territory and tactical assignment. These are transparent provisional production scores, not a claim of isolated defensive quality.
- High-line recovery pace, marking, coordination and pressured receiving need spatial/tracking evidence. They are not measured by tackles, interceptions or carrying metres.
- Correlated inputs (e.g. goals/xG; take-on wins/success share; duel wins/share) are intentionally limited to a parent/family budget. Review correlations and weight sensitivity before implementation; do not add totals and /90 forms as extra abilities.
- Repeated inputs across different parents are stored once. Overall influence is the parent-weight × feature-weight path before standardization; overlapping standardized composites still need empirical sensitivity checks.
- Exclude provider overall ratings, age, nationality, fee, height, weight and unverified pace/stamina/strength guesses from performance scoring.
- Review: approve the six parent names and OVR weights; then approve feature semantics, within-parent weights and each contextual proxy. No engine, UI or data-release changes are made by this document.

## Research basis

EA’s published attribute families inform the six-part presentation, but Scout uses retrievable performance observations. Pace, reflexes and pure strength cannot be reconstructed from the current aggregate event data. [EA official attribute families (legacy chemistry-style reference)](https://media.contentapi.ea.com/content/dam/fifa/en-us/images-migrated/2018/09/chemistry-styles.pdf).

The proposed feature allocation is Scout’s inference from role duties and the local inventory, not a copied commercial rating formula. [Opta event definitions](https://www.statsperform.com/opta-event-definitions/) supplies event-meaning checks. Detailed shared research notes are in [the review index](position_attributes_review.md).

Defender activity and style must be separated from pure quality: [StatsBomb centre-back scouting approach](https://blogarchive.statsbomb.com/articles/soccer/how-do-you-scout-for-centre-backs-statistically/).

**Feature slots:** 24. **Distinct proposed metrics:** 23. Repeated inputs are not additional raw features.
