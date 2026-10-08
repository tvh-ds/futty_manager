# CM Attributes

**Status: implemented provisional registry v1 — 8 October 2026.**

Weights are loaded from [position_rating_weights_config.yaml](position_rating_weights_config.yaml). A registry does not guarantee every player has enough evidence or peers for a rating.

**Performance season:** 2025/26. **Research/inventory date:** 7 October 2026.

Central midfielder: balanced circulation, advancement, creation and recovery. LCM/RCM share the same role.

All weights below are provisional Scout design judgments, not fitted results or proprietary EA coefficients. Left/right variants have identical weights and a shared peer population; foot preference, side experience and tactical fit remain separate.

## Six abilities and overall weights

| Ability | Card label | OVR weight |
|---|---|---:|
| Ball Progression | PRO | 24% |
| Retention / Circulation | RET | 20% |
| Chance Creation | CRE | 18% |
| Ball Recovery | REC | 18% |
| Duel Contribution | DUE | 12% |
| Goal Threat | SCO | 8% |

**Overall weights sum to 100%.** Standardize each ability before combining them, then re-standardize OVR. Display `max(1, 50 + 15 × z)` with no upper cap. See [shared calculation and source rules](position_attribute_methods.md).

## Feature definitions and weights

Each table sums to 100% **within that ability**. `+` means higher is preferable; `−` means lower is preferable after stabilization. `/90` uses matched provider exposure, not a different source’s season minutes.

### 1. Ball Progression — 24% of OVR

Reward carrying and territorial passing; do not claim unavailable line-breaking pass counts.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Successful final-third passes /90 | `successful_final_third_passes` | `90 × successful_final_third_passes / minutes` | + | 30% |
| Progressive carries /90 | `progressive_carries` | `90 × progressive_carries / minutes` | + | 25% |
| Progressive carry distance /90 | `progressive_distance` | `90 × progressive_distance / minutes` | + | 20% |
| Carries into final third /90 | `carries_into_final_third` | `90 × carries_into_final_third / minutes` | + | 15% |
| Successful through balls /90 | `successful_through_balls` | `90 × successful_through_balls / minutes` | + | 10% |

Interpretation:

- **Successful final-third passes /90:** Provider final-third passing category. Do not rename as progressive passes or entries until start/end-zone semantics are verified.
- **Progressive carries /90:** Opta progressive-carry criterion; preserve definition/version.
- **Progressive carry distance /90:** Opta carries.overall.progressive_distance, not progressive passing distance. Signed observations are retained; do not force absolute values. PitchAPI progressive_carry_distance is not automatically equivalent.
- **Carries into final third /90:** Field advancement; not proof of beating a defensive line.
- **Successful through balls /90:** Prefer successful deliveries to attempted-volume alone.

### 2. Retention / Circulation — 20% of OVR

Control losses matter more than uncontextualized completion.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Miscontrols /90 | `miscontrols` | `90 × miscontrols / minutes` | − | 30% |
| Dispossessed /90 | `dispossessed` | `90 × dispossessed / minutes` | − | 30% |
| Pass completion | `successful_passes`, `passes` | `100 × successful_passes / passes` | + | 20% |
| Final-third pass completion | `successful_final_third_passes`, `total_final_third_passes` | `100 × successful_final_third_passes / total_final_third_passes` | + | 10% |
| Successful passes /90 | `successful_passes` | `90 × successful_passes / minutes` | + | 10% |

Interpretation:

- **Miscontrols /90:** Recorded control losses; low counts can also reflect limited receiving responsibility.
- **Dispossessed /90:** Loss while in possession; use carrying/role context and do not infer pressure resistance directly.
- **Pass completion:** Same-provider denominator. Ordinary completion is a limited retention proxy, not vision or pressured-pass quality.
- **Final-third pass completion:** Completion within the same provider category; no pressure inference.
- **Successful passes /90:** Small-weight circulation activity; heavily team-style dependent.

### 3. Chance Creation — 18% of OVR

Final delivery and involvement earlier in scoring possessions.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Open-play xA /90 | `op_xa` | `90 × op_xa / minutes` | + | 30% |
| Open-play chances created /90 | `op_chances_created` | `90 × op_chances_created / minutes` | + | 25% |
| Passes into penalty area /90 | `passes_into_penalty_area` | `90 × passes_into_penalty_area / minutes` | + | 20% |
| Successful through balls /90 | `successful_through_balls` | `90 × successful_through_balls / minutes` | + | 10% |
| xGBuildup /90 | `xGBuildup` | `90 × xGBuildup / Understat time` | + | 15% |

Interpretation:

- **Open-play xA /90:** Open-play creation reduces set-piece responsibility bias. Total xa/xA is a separately labelled fallback, not an identical feature.
- **Open-play chances created /90:** Opta chance-creation definition; do not silently equate with every provider key_passes.
- **Passes into penalty area /90:** Spatial delivery; establish completion/cross-inclusion contract before activation.
- **Successful through balls /90:** Prefer successful deliveries to attempted-volume alone.
- **xGBuildup /90:** Understat possession-chain involvement before shot/assist; team-dependent, private-use evidence, not OBV or xT.

### 4. Ball Recovery — 18% of OVR

Balanced recovery and interception activity.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Recoveries /90 | `recoveries` | `90 × recoveries / minutes` | + | 40% |
| Interceptions /90 | `interceptions` | `90 × interceptions / minutes` | + | 35% |
| Tackles /90 | `tackles` | `90 × tackles / minutes` | + | 25% |

Interpretation:

- **Recoveries /90:** Ball recovery activity; not a measured pressing-success rate.
- **Interceptions /90:** Reading/action activity; opportunities depend on opposition possession.
- **Tackles /90:** Activity proxy. Opta tackles include won/lost possession outcomes; not attempted challenges or tackle success.

### 5. Duel Contribution — 12% of OVR

Ground contribution receives most emphasis; aerial play is supplementary.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Ground duel win share | `ground_duels_won`, `ground_duels` | `100 × ground_duels_won / ground_duels` | + | 40% |
| Ground duels won /90 | `ground_duels_won` | `90 × ground_duels_won / minutes` | + | 30% |
| Aerial duel win share | `aerial_duels_won`, `aerial_duels` | `100 × aerial_duels_won / aerial_duels` | + | 20% |
| Aerial duels won /90 | `aerial_duels_won` | `90 × aerial_duels_won / minutes` | + | 10% |

Interpretation:

- **Ground duel win share:** Pair matched outcomes/attempts from Opta. This is not tackle/dribbled-past success.
- **Ground duels won /90:** Opta ground duels are broad contests, not exclusively defensive 1v1 challenges.
- **Aerial duel win share:** Use Opta pair. PitchAPI fallback uses aerial_duels_won / (aerial_duels_won + aerial_duels_lost), with its own minutes.
- **Aerial duels won /90:** Successful aerial involvement; height itself is excluded.

### 6. Goal Threat — 8% of OVR

Secondary scoring responsibility avoids rewarding only attacking eights.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Non-penalty xG /90 | `np_xg` | `90 × np_xg / minutes` | + | 40% |
| Non-penalty goals /90 | `np_goals` | `90 × np_goals / minutes` | + | 25% |
| Non-penalty shots on target /90 | `np_shots_on_target` | `90 × np_shots_on_target / minutes` | + | 20% |
| Opposition box touches /90 | `touches_opposition_box` | `90 × touches_opposition_box / minutes` | + | 15% |

Interpretation:

- **Non-penalty xG /90:** Chance production, not pure finishing technique. Alternatives: PitchAPI npxg; Understat npxG, with their own model definitions.
- **Non-penalty goals /90:** Realized scoring; noisy at low shot exposure. Compatible alternatives: PitchAPI non_penalty_goals; Understat npg.
- **Non-penalty shots on target /90:** Shot production; do not substitute all-shot on-target totals without preserving the different scope.
- **Opposition box touches /90:** Box involvement proxy, not tracking-based off-ball movement.

## What is actually in the master

The inspected private master has **3,561 player/league rows and 227 wide columns**. Counts below are recorded input cells, including recorded zeros, excluding `unrecorded_zero`. They include low-minute players and all roles; they are **not** eligible-role counts or guaranteed derived-feature coverage. No 90% gate is applied.

| Season-column input | Recorded master rows | Zero-filled rows | Selected sources |
|---|---:|---:|---|
| `aerial_duels` | 2,576 | 985 | opta |
| `aerial_duels_won` | 2,918 | 643 | opta, pitchapi |
| `carries_into_final_third` | 2,553 | 1,008 | pitchapi |
| `dispossessed` | 2,769 | 792 | pitchapi |
| `ground_duels` | 2,576 | 985 | opta |
| `ground_duels_won` | 2,576 | 985 | opta |
| `interceptions` | 2,918 | 643 | opta, pitchapi |
| `miscontrols` | 2,553 | 1,008 | pitchapi |
| `np_goals` | 2,576 | 985 | opta |
| `np_shots_on_target` | 2,576 | 985 | opta |
| `np_xg` | 2,576 | 985 | opta |
| `op_chances_created` | 2,576 | 985 | opta |
| `op_xa` | 2,576 | 985 | opta |
| `passes` | 2,576 | 985 | opta |
| `passes_into_penalty_area` | 2,553 | 1,008 | pitchapi |
| `progressive_carries` | 2,576 | 985 | opta |
| `progressive_distance` | 2,576 | 985 | opta |
| `recoveries` | 2,917 | 644 | opta, pitchapi |
| `successful_final_third_passes` | 2,576 | 985 | opta |
| `successful_passes` | 2,576 | 985 | opta |
| `successful_through_balls` | 2,576 | 985 | opta |
| `tackles` | 2,576 | 985 | opta |
| `total_final_third_passes` | 2,576 | 985 | opta |
| `touches_opposition_box` | 2,573 | 988 | pitchapi |
| `xGBuildup` | 2,774 | 787 | understat |
## Role-specific limits and review decisions

- Detailed position evidence must distinguish CM, CAM and CDM. Do not infer the role from whichever weighted score is highest.
- Build-up xG is possession-chain involvement, not marginal action value. Completion is a modest proxy; it cannot establish vision, press resistance or ball speed.
- Correlated inputs (e.g. goals/xG; take-on wins/success share; duel wins/share) are intentionally limited to a parent/family budget. Review correlations and weight sensitivity before implementation; do not add totals and /90 forms as extra abilities.
- Repeated inputs across different parents are stored once. Overall influence is the parent-weight × feature-weight path before standardization; overlapping standardized composites still need empirical sensitivity checks.
- Exclude provider overall ratings, age, nationality, fee, height, weight and unverified pace/stamina/strength guesses from performance scoring.
- Review: approve the six parent names and OVR weights; then approve feature semantics, within-parent weights and each contextual proxy. No engine, UI or data-release changes are made by this document.

## Research basis

EA’s published attribute families inform the six-part presentation, but Scout uses retrievable performance observations. Pace, reflexes and pure strength cannot be reconstructed from the current aggregate event data. [EA official attribute families (legacy chemistry-style reference)](https://media.contentapi.ea.com/content/dam/fifa/en-us/images-migrated/2018/09/chemistry-styles.pdf).

The proposed feature allocation is Scout’s inference from role duties and the local inventory, not a copied commercial rating formula. [Opta event definitions](https://www.statsperform.com/opta-event-definitions/) supplies event-meaning checks. Detailed shared research notes are in [the review index](position_attributes_review.md).

Role templates support balancing production, creation, carrying and defensive context: [Hudl StatsBomb positional radar methodology](https://blogarchive.statsbomb.com/articles/soccer/new-statsbomb-radars-2023-update/).

**Feature slots:** 26. **Distinct proposed metrics:** 25. Repeated inputs are not additional raw features.
