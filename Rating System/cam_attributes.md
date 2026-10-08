# CAM Attributes

**Status: implemented provisional registry v1 — 8 October 2026.**

Weights are loaded from [position_rating_weights_config.yaml](position_rating_weights_config.yaml). A registry does not guarantee every player has enough evidence or peers for a rating.

**Performance season:** 2025/26. **Research/inventory date:** 7 October 2026.

Central attacking midfielder: chance creation and combination play first; carrying and scoring remain substantial.

All weights below are provisional Scout design judgments, not fitted results or proprietary EA coefficients. Left/right variants have identical weights and a shared peer population; foot preference, side experience and tactical fit remain separate.

## Six abilities and overall weights

| Ability | Card label | OVR weight |
|---|---|---:|
| Chance Creation | CRE | 30% |
| Combination / Retention | LNK | 18% |
| Carrying / 1v1 | CAR | 18% |
| Scoring | SCO | 16% |
| Penalty-Area Threat | BOX | 10% |
| Defensive Support | DEF | 8% |

**Overall weights sum to 100%.** Standardize each ability before combining them, then re-standardize OVR. Display `max(1, 50 + 15 × z)` with no upper cap. See [shared calculation and source rules](position_attribute_methods.md).

## Feature definitions and weights

Each table sums to 100% **within that ability**. `+` means higher is preferable; `−` means lower is preferable after stabilization. `/90` uses matched provider exposure, not a different source’s season minutes.

### 1. Chance Creation — 30% of OVR

Prioritize expected output and repeatable chance delivery.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Open-play xA /90 | `op_xa` | `90 × op_xa / minutes` | + | 35% |
| Open-play chances created /90 | `op_chances_created` | `90 × op_chances_created / minutes` | + | 25% |
| Passes into penalty area /90 | `passes_into_penalty_area` | `90 × passes_into_penalty_area / minutes` | + | 20% |
| Successful through balls /90 | `successful_through_balls` | `90 × successful_through_balls / minutes` | + | 10% |
| Shot-creating actions /90 | `sca` | `90 × sca / minutes` | + | 10% |

Interpretation:

- **Open-play xA /90:** Open-play creation reduces set-piece responsibility bias. Total xa/xA is a separately labelled fallback, not an identical feature.
- **Open-play chances created /90:** Opta chance-creation definition; do not silently equate with every provider key_passes.
- **Passes into penalty area /90:** Spatial delivery; establish completion/cross-inclusion contract before activation.
- **Successful through balls /90:** Prefer successful deliveries to attempted-volume alone.
- **Shot-creating actions /90:** PitchAPI SCA definition must be retained; includes overlapping creation signals and potentially dead-ball actions.

### 2. Combination / Retention — 18% of OVR

Maintain involvement in attacks without repeatedly losing the ball.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Miscontrols /90 | `miscontrols` | `90 × miscontrols / minutes` | − | 25% |
| Dispossessed /90 | `dispossessed` | `90 × dispossessed / minutes` | − | 25% |
| Pass completion | `successful_passes`, `passes` | `100 × successful_passes / passes` | + | 20% |
| Final-third pass completion | `successful_final_third_passes`, `total_final_third_passes` | `100 × successful_final_third_passes / total_final_third_passes` | + | 15% |
| xGBuildup /90 | `xGBuildup` | `90 × xGBuildup / Understat time` | + | 15% |

Interpretation:

- **Miscontrols /90:** Recorded control losses; low counts can also reflect limited receiving responsibility.
- **Dispossessed /90:** Loss while in possession; use carrying/role context and do not infer pressure resistance directly.
- **Pass completion:** Same-provider denominator. Ordinary completion is a limited retention proxy, not vision or pressured-pass quality.
- **Final-third pass completion:** Completion within the same provider category; no pressure inference.
- **xGBuildup /90:** Understat possession-chain involvement before shot/assist; team-dependent, private-use evidence, not OBV or xT.

### 3. Carrying / 1v1 — 18% of OVR

Carry into central danger and beat opponents.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Successful take-ons /90 | `take_ons_successful` | `90 × take_ons_successful / minutes` | + | 25% |
| Take-on success | `take_ons_successful`, `take_ons_attempted` | `100 × take_ons_successful / take_ons_attempted` | + | 20% |
| Carries into penalty area /90 | `carries_into_penalty_area` | `90 × carries_into_penalty_area / minutes` | + | 25% |
| Carries into final third /90 | `carries_into_final_third` | `90 × carries_into_final_third / minutes` | + | 15% |
| Progressive carry distance /90 | `progressive_distance` | `90 × progressive_distance / minutes` | + | 15% |

Interpretation:

- **Successful take-ons /90:** On-ball opponent beating, not sprint speed.
- **Take-on success:** Shrink using take-on attempts; zero attempts produce N/A.
- **Carries into penalty area /90:** Territorial carrying; overlaps successful take-ons only partially.
- **Carries into final third /90:** Field advancement; not proof of beating a defensive line.
- **Progressive carry distance /90:** Opta carries.overall.progressive_distance, not progressive passing distance. Signed observations are retained; do not force absolute values. PitchAPI progressive_carry_distance is not automatically equivalent.

### 4. Scoring — 16% of OVR

Attacking-midfield shooting production and execution.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Non-penalty xG /90 | `np_xg` | `90 × np_xg / minutes` | + | 15% |
| Non-penalty goals /90 | `np_goals` | `90 × np_goals / minutes` | + | 25% |
| Goals above non-penalty xG /90 | `np_goals_vs_xg` | `90 × np_goals_vs_xg / minutes` | + | 30% |
| Non-penalty shots on target /90 | `np_shots_on_target` | `90 × np_shots_on_target / minutes` | + | 15% |
| Non-penalty on-target share | `np_shots_on_target`, `np_shots` | `100 × np_shots_on_target / np_shots` | + | 15% |

Interpretation:

- **Non-penalty xG /90:** Chance production, not pure finishing technique. Alternatives: PitchAPI npxg; Understat npxG, with their own model definitions.
- **Non-penalty goals /90:** Realized scoring; noisy at low shot exposure. Compatible alternatives: PitchAPI non_penalty_goals; Understat npg.
- **Goals above non-penalty xG /90:** Signed residual; shrink strongly. Validate against same-provider np_goals − np_xg.
- **Non-penalty shots on target /90:** Shot production; do not substitute all-shot on-target totals without preserving the different scope.
- **Non-penalty on-target share:** Uses all non-penalty attempts consistently, including blocked attempts. This is a Scout ratio, not Opta shooting accuracy, which excludes blocked shots.

### 5. Penalty-Area Threat — 10% of OVR

Late arrivals and box involvement measured through actions.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Opposition box touches /90 | `touches_opposition_box` | `90 × touches_opposition_box / minutes` | + | 45% |
| Shots inside box /90 | `shots_inside_box` | `90 × shots_inside_box / minutes` | + | 30% |
| Open-play xG /90 | `open_play_xg` | `90 × open_play_xg / minutes` | + | 25% |

Interpretation:

- **Opposition box touches /90:** Box involvement proxy, not tracking-based off-ball movement.
- **Shots inside box /90:** PitchAPI aggregate; verify shot scope and complete match coverage.
- **Open-play xG /90:** PitchAPI open-play shot context; not interchangeable with non-penalty xG including set pieces.

### 6. Defensive Support — 8% of OVR

Secondary recovery contribution without invented pressure data.

| Feature | Master input | Calculation | Direction | Within-ability weight |
|---|---|---|:---:|---:|
| Recoveries /90 | `recoveries` | `90 × recoveries / minutes` | + | 45% |
| Interceptions /90 | `interceptions` | `90 × interceptions / minutes` | + | 30% |
| Tackles /90 | `tackles` | `90 × tackles / minutes` | + | 25% |

Interpretation:

- **Recoveries /90:** Ball recovery activity; not a measured pressing-success rate.
- **Interceptions /90:** Reading/action activity; opportunities depend on opposition possession.
- **Tackles /90:** Activity proxy. Opta tackles include won/lost possession outcomes; not attempted challenges or tackle success.

## What is actually in the master

The inspected private master has **3,561 player/league rows and 227 wide columns**. Counts below are recorded input cells, including recorded zeros, excluding `unrecorded_zero`. They include low-minute players and all roles; they are **not** eligible-role counts or guaranteed derived-feature coverage. No 90% gate is applied.

| Season-column input | Recorded master rows | Zero-filled rows | Selected sources |
|---|---:|---:|---|
| `carries_into_final_third` | 2,553 | 1,008 | pitchapi |
| `carries_into_penalty_area` | 2,553 | 1,008 | pitchapi |
| `dispossessed` | 2,769 | 792 | pitchapi |
| `interceptions` | 2,918 | 643 | opta, pitchapi |
| `miscontrols` | 2,553 | 1,008 | pitchapi |
| `np_goals` | 2,576 | 985 | opta |
| `np_goals_vs_xg` | 2,576 | 985 | opta |
| `np_shots` | 2,576 | 985 | opta |
| `np_shots_on_target` | 2,576 | 985 | opta |
| `np_xg` | 2,576 | 985 | opta |
| `op_chances_created` | 2,576 | 985 | opta |
| `op_xa` | 2,576 | 985 | opta |
| `open_play_xg` | 2,769 | 792 | pitchapi |
| `passes` | 2,576 | 985 | opta |
| `passes_into_penalty_area` | 2,553 | 1,008 | pitchapi |
| `progressive_distance` | 2,576 | 985 | opta |
| `recoveries` | 2,917 | 644 | opta, pitchapi |
| `sca` | 2,553 | 1,008 | pitchapi |
| `shots_inside_box` | 2,769 | 792 | pitchapi |
| `successful_final_third_passes` | 2,576 | 985 | opta |
| `successful_passes` | 2,576 | 985 | opta |
| `successful_through_balls` | 2,576 | 985 | opta |
| `tackles` | 2,576 | 985 | opta |
| `take_ons_attempted` | 2,553 | 1,008 | pitchapi |
| `take_ons_successful` | 2,553 | 1,008 | pitchapi |
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

**Feature slots:** 26. **Distinct proposed metrics:** 26. Repeated inputs are not additional raw features.
