**Active weights (8 October 2026):** See [editable configuration](position_rating_weights_config.yaml). Physicality now excludes fouls won; its five weights are 10/30/10/25/25%. The engine uses the current rating_ranking_system.md normalization, which supersedes older examples below.

# ST Attributes

**Position:** Striker (ST)
**Target:** Free/publicly accessible football data with real numeric values that can be retrieved and normalized by the scouting engine.

---

# 1. Primary Data Sources

## FotMob

Use FotMob primarily for:

- Goals
- xG / npxG
- Shots
- Shots on target
- Shots inside the box
- Headed shots
- Assists
- xA
- Chances created
- Duels won
- Duel win %
- Aerial duels won
- Aerial duel win %
- Fouls won
- Dispossessed
- Recoveries
- Interceptions
- Minutes

Player pages:

```text
https://www.fotmob.com/players/{player_id}/{player_slug}
```

---

## FBref

Use FBref primarily for:

- Touches in attacking penalty area
- Take-ons attempted / successful
- Carrying metrics
- Miscontrols
- Dispossessions
- Key passes
- Passes into penalty area
- Through balls
- Shot-creating actions
- Interceptions
- Recoveries
- Blocks
- Fouls drawn
- Offsides
- Aerial duels

Relevant table families:

```text
https://fbref.com/en/comps/{competition_id}/possession/
https://fbref.com/en/comps/{competition_id}/passing/
https://fbref.com/en/comps/{competition_id}/passing_types/
https://fbref.com/en/comps/{competition_id}/gca/
https://fbref.com/en/comps/{competition_id}/defense/
https://fbref.com/en/comps/{competition_id}/misc/
```

---

# 2. Normalization

Store raw totals and minutes whenever possible.

Calculate per-90 metrics internally:

\[
\text{Metric per 90}
=
\frac{\text{Metric}}{\text{Minutes}}
\times 90
\]

Percentages should also be calculated internally from raw counts when those counts are available.

Example:

\[
\text{Shot-on-target \%}
=
\frac{\text{Shots on Target}}{\text{Shots}}
\times 100
\]

---

# 3. Suggested ST Quality Weighting

Recommended starting weights for an overall striker rating:

| Quality | Suggested Weight |
|---|---:|
| Finishing | 27% |
| Box Threat | 20% |
| Link-Up / Creation | 17% |
| Carrying / 1v1 | 14% |
| Physicality | 12% |
| Defensive Activity | 10% |

These should later be adjusted by striker archetype.

---

# 4. Finishing

**Suggested quality weight: 27%**

| Feature | Source | Calculation | Suggested within-quality weight |
|---|---|---|---:|
| Non-penalty goals / 90 | FotMob / FBref | `NPG / minutes * 90` | 16.176471% |
| Non-penalty xG / 90 | FotMob / FBref | `npxG / minutes * 90` | 15% |
| NPG - npxG / 90 | Derived | `(NPG - npxG) / minutes * 90` | 30% |
| Shots / 90 | FotMob / FBref | `shots / minutes * 90` | 6.470588% |
| Shots on target / 90 | FotMob / FBref | `SoT / minutes * 90` | 8.088235% |
| Shot-on-target % | FotMob / FBref | `SoT / shots` | 8.088235% |
| Goals per shot | Derived / FBref | `NPG / non_penalty_shots` or `goals / shots` | 8.088235% |
| npxG per shot | Derived / FBref | `npxG / non_penalty_shots` | 8.088235% |

### Finishing total

```text
100%
```

---

# 5. Box Threat

**Suggested quality weight: 20%**

| Feature | Source | Calculation | Suggested within-quality weight |
|---|---|---|---:|
| Shots inside penalty area / 90 | FotMob | `inside_box_shots / minutes * 90` | 24% |
| Open-play xG / 90 | FotMob shot/event data | `sum(open_play_xG) / minutes * 90` | 28% |
| Headed shots / 90 | FotMob | `headed_shots / minutes * 90` | 10% |
| Touches in opposition penalty area / 90 | FotMob / FBref `Att Pen` | `box_touches / minutes * 90` | 28% |
| Offsides / 90 | FBref `Off` | `offsides / minutes * 90` | 10% |

### Direction

```text
Shots inside box                positive
Open-play xG                    positive
Headed shots                    positive
Touches in opposition box       positive
Offsides                        context-dependent / weak negative
```

For offsides, avoid treating every offside as strongly negative. A high value can also reflect frequent attempts to attack the defensive line.

---

# 6. Link-Up / Creation

**Suggested quality weight: 17%**

| Feature | Source | Calculation | Suggested within-quality weight |
|---|---|---|---:|
| Assists / 90 | FotMob / FBref | `assists / minutes * 90` | 12% |
| xA / 90 | FotMob | `xA / minutes * 90` | 22% |
| Key passes / chances created / 90 | FBref `KP` / FotMob | `key_passes / minutes * 90` | 20% |
| Shot-creating actions / 90 | FBref `SCA90` | Use published SCA90 or recompute | 18% |
| Passes into penalty area / 90 | FBref `PPA` | `PPA / minutes * 90` | 12% |
| Through balls / 90 | FBref `TB` | `TB / minutes * 90` | 8% |
| Pass completion % | FotMob / FBref | `passes_completed / passes_attempted` | 8% |

### Link-Up / Creation total

```text
100%
```

---

# 7. Carrying / 1v1

**Suggested quality weight: 14%**

| Feature | Source | Calculation | Suggested within-quality weight |
|---|---|---|---:|
| Take-ons attempted / 90 | FBref `Att` | `attempted_takeons / minutes * 90` | 8% |
| Successful take-ons / 90 | FBref `Succ` / FotMob | `successful_takeons / minutes * 90` | 14% |
| Take-on success % | FBref `Succ%` / FotMob | `successful_takeons / attempted_takeons` | 20% |
| Carries into penalty area / 90 | FBref `CPA` | `CPA / minutes * 90` | 20% |
| Carries into final third / 90 | FBref `1/3` | `final_third_carries / minutes * 90` | 12% |
| Progressive carry distance / 90 | FBref `PrgDist` | `progressive_distance / minutes * 90` | 10% |
| Miscontrols / 90 | FBref `Mis` | `miscontrols / minutes * 90` | 8% negative |
| Dispossessed / 90 | FBref `Dis` / FotMob | `dispossessed / minutes * 90` | 8% negative |

### Carrying / 1v1 total

```text
100%
```

---

# 8. Physicality

**Suggested quality weight: 12%**

Height and weight are intentionally excluded.

| Feature | Source | Calculation | Suggested within-quality weight |
|---|---|---|---:|
| Duels won / 90 | FotMob | `duels_won / minutes * 90` | 10% |
| Duel win % | FotMob | `duels_won / duels_attempted` | 30% |
| Aerial duels won / 90 | FotMob / FBref | `aerial_won / minutes * 90` | 10% |
| Aerial duel win % | FotMob / FBref | `aerial_won / (aerial_won + aerial_lost)` | 25% |

| Dispossessed / 90 | FotMob / FBref | `dispossessed / minutes * 90` | 25% negative |

### Physicality total

```text
100%
```

### Important implementation note

Overall duel metrics and aerial duel metrics overlap.

Do not treat:

```text
Duels won / 90
Duel win %
Aerial duels won / 90
Aerial duel win %
```

as completely independent signals when training a model.

For a manually weighted scouting score, the weights above intentionally keep aerial metrics below the combined overall-duel contribution.

---

# 9. Defensive Activity

**Suggested quality weight: 10%**

| Feature | Source | Calculation | Suggested within-quality weight |
|---|---|---|---:|
| Interceptions / 90 | Opta / verified provider counts | `interceptions / minutes * 90` | 3/13 = 23.077% |
| Recoveries / 90 | Opta / verified provider counts | `recoveries / minutes * 90` | 7/13 = 53.846% |
| Blocks / 90 | Opta / verified provider counts | `blocks / minutes * 90` | 3/13 = 23.077% |

Revision approved 6 October 2026: remove attacking-third tackles. Divide the
remaining original weights (15%, 35%, 15%) by their 65% total, preserving their
relative emphasis. Defensive Activity retains its 10% broad-ST weight. This
ability describes defensive actions and ball recovery, not measured pressing
effectiveness. Registry: `striker-features-v2`; weights: `striker-weights-v2`.

### Defensive Activity total

```text
100%
```

---

# 10. Final ST Feature Set

## Finishing — 8

```text
1. Non-penalty goals / 90
2. Non-penalty xG / 90
3. NPG - npxG / 90
4. Shots / 90
5. Shots on target / 90
6. Shot-on-target %
7. Goals per shot
8. npxG per shot
```

## Box Threat — 5

```text
9.  Shots inside penalty area / 90
10. Open-play xG / 90
11. Headed shots / 90
12. Touches in opposition penalty area / 90
13. Offsides / 90
```

## Link-Up / Creation — 7

```text
14. Assists / 90
15. xA / 90
16. Key passes / chances created / 90
17. Shot-creating actions / 90
18. Passes into penalty area / 90
19. Through balls / 90
20. Pass completion %
```

## Carrying / 1v1 — 8

```text
21. Take-ons attempted / 90
22. Successful take-ons / 90
23. Take-on success %
24. Carries into penalty area / 90
25. Carries into final third / 90
26. Progressive carry distance / 90
27. Miscontrols / 90
28. Dispossessed / 90
```

## Physicality — 6

```text
29. Duels won / 90
30. Duel win %
31. Aerial duels won / 90
32. Aerial duel win %
33. Fouls won / 90
34. Dispossessed / 90
```

## Defensive Activity — 3

```text
35. Interceptions / 90
36. Recoveries / 90
37. Blocks / 90
```

**Total: 37 feature slots, 36 unique features, across 6 ST qualities.**

`Dispossessed / 90` is referenced by both Carrying / 1v1 and Physicality.

Store it only once in the canonical model feature table.

---

# 11. Canonical Raw Storage

Recommended raw schema:

```text
player_id
player_name
team_id
team_name
competition_id
competition_name
season
position
minutes

non_penalty_goals
npxg
shots
shots_on_target
shots_inside_box
headed_shots
open_play_xg
touches_opposition_box
offsides

assists
xa
key_passes
sca
passes_into_penalty_area
through_balls
passes_completed
passes_attempted

take_ons_attempted
take_ons_successful
carries_into_penalty_area
carries_into_final_third
progressive_carry_distance
miscontrols
dispossessed

duels_won
duels_attempted
aerial_duels_won
aerial_duels_lost
fouls_won

interceptions
recoveries
blocks
```

---

# 12. Validation Rules

```text
1. Match player identity across sources.
2. Match competition and season exactly.
3. Store source URL/source identifier.
4. Store retrieval timestamp.
5. Store minutes with every aggregate record.
6. Never silently convert missing values to zero.
7. Keep missing and true zero separate.
8. Recalculate /90 metrics internally.
9. Validate percentages are between 0 and 100.
10. Validate shots_on_target <= shots.
11. Validate successful_takeons <= attempted_takeons.
12. Validate aerial_duels_won <= aerial_duels_won + aerial_duels_lost.
13. Reject records with inconsistent season/team mappings.
```

---

# 13. Overall ST Score

Suggested starting formula:

\[
ST =
0.27F
+
0.20B
+
0.17L
+
0.14C
+
0.12P
+
0.10D
\]

where:

```text
F = Finishing
B = Box Threat
L = Link-Up / Creation
C = Carrying / 1v1
P = Physicality
D = Defensive Activity
```

Each quality should first be normalized against comparable players.

Recommended comparison group:

```text
same position
same competition
same season
minimum minutes threshold
```

Use percentile ranks or standardized z-scores before applying the weighting system.

---

# 14. Archetype Weighting

The overall weights above are only a default ST profile.

Later, use different weights for:

```text
Poacher
Advanced Forward
Target Forward
Complete Forward
False 9
Pressing Forward
```

For example:

```text
Target Forward
Physicality           ↑
Box Threat            ↑
Carrying / 1v1        ↓

False 9
Link-Up / Creation    ↑
Carrying / 1v1        ↑
Physicality           ↓

Poacher
Finishing             ↑
Box Threat            ↑
Link-Up / Creation    ↓
```

Keep the raw feature definitions unchanged and modify only the scoring weights.

---

# 15. Real Data Sources and Import Contract

The current three-source stack is **Opta Analyst, PitchAPI and Understat**.
Performance observations use completed **2025/26**, separately from Liverpool's
2026/27 squad membership. The local schema and importer are implemented in
`src/scout/real_data.py`; operational details are in `docs/real-data-import.md`.

| Source | Role in the feature stack | Current evidence and limitation |
|---|---|---|
| [Opta Analyst](https://optaplayerstats.statsperform.com/en_GB/soccer/premier-league-2025-2026/51r6ph2woavlbbpk8f29nynf8/opta-player-stats) | NPG/npxG, shots/on-target, assists/xA, offsides, passing, ground/aerial duels, interceptions, recoveries and blocks | 3,239 valid player/team records after offline goalkeeper-report reprocessing; user consent confirmed; two exposure conflicts quarantined |
| [PitchAPI](https://api.pitchapi.dev) | Match/shot aggregation plus advanced carries, take-ons, possession losses, box actions and creation features | 2,770 player/league records; free access/reuse rights confirmed; five match feeds quarantined, season backfill remains incomplete |
| [Understat](https://understat.com) | Independent NPG/npxG, shots, assists/xA and key-pass measurements; fallback and comparison | 2,775 player/league records across all five leagues; private local intake only; publication permission unverified |

After removing attacking-third tackles, the registry has **36 unique features**.
The sources collectively support the definitions of **35/36**; **fouls won**
remains missing. This is a capability count, not proof that 90% of players have
every feature. The import report records actual support per provider and league.
Zero-attempt ratios are N/A, counted as supported, and never fabricated as zero.

The current database import stores all 8,784 provider records and all 36 calculated feature
slots per record, including explicit missingness. Provider records are not a
deduplicated player population. Identity matches require documented review.
Automatic name suggestions do not authorize merging.

For a reviewed combined identity the provisional intake preference is
**Opta → PitchAPI → Understat**, choosing an available measurement and preserving
alternatives. Calculate each ratio/per-90 value using that provider's own
numerator and denominator. Do not mix Understat xG/xA with another provider's
shots/minutes, add overlapping source totals, or equate different SCA/carry/duel
definitions without reconciliation. Source versions, URLs, retrieval dates and
aggregation scope accompany the calculated value.

The feature engine and private Players catalogue are available locally. The
catalogue uses corroborated identity matches and strict compatible-cohort ST
scoring; Liverpool cards now show these historical attributes, with unavailable
scores retained. Chemistry remains illustrative. See `docs/player-catalogue.md`.
This does not activate a public recruitment release: reviewed identities,
definition reconciliation and publication/coverage gates remain necessary.
