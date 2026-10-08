# Rating & Ranking System

**Active position models (8 October 2026):** ST, LW/RW, LM/RM, CM, CAM, CDM, CB, RB/LB and GK are implemented with separate six-ability registries. Editable within-ability and OVR weights are in [position_rating_weights_config.yaml](position_rating_weights_config.yaml). All peers pool the top five leagues by position; GK is separate. A model can exist without enough eligible data: no LM/RM cohort is currently verified. Keeper appearance-derived features require matched season exposure; partial windows are retained but not scored as full seasons. See [configuration guide](position_weights_implementation.md).

**Current display policy (7 October 2026):** Ability and OVR ratings have no upper cap.
Use `max(1, 50 + 15 × z)`; genuine scores above 99 remain visible. Percentiles
remain bounded at 0–100. Radar domains expand to include the displayed scores.
This supersedes earlier display-clipping examples below.

**Purpose:** Convert role-specific football performance into a transparent **0–100 player rating** while preserving real performance gaps between players.

**Core design**
- **Rating** = magnitude of performance relative to the role population.
- **Percentile** = rank within the role population.
- **Base rating = 50** for an average player in the comparison population.
- Do **not** use percentile as the rating itself.
- Do **not** percentile-transform individual metrics before aggregation.

---

# 1. System Overview

```text
RAW METRICS
    ↓
data validation + sample-size stabilization
    ↓
context-adjusted metrics
    ↓
STANDARD Z-SCORES
    ↓
weighted QUALITY composites
    ↓
re-standardize each quality
    ↓
QUALITY RATINGS (0–100, base 50)
    ↓
role-specific quality weighting
    ↓
ROLE COMPOSITE
    ↓
re-standardize role composite
    ├──────────────────────────┐
    ↓                          ↓
ROLE RATING                PERCENTILE
0–100, base 50             relative rank
magnitude-sensitive        rank-sensitive
```

The system deliberately keeps **rating** and **percentile** separate.

---

# 2. Comparison Population

Every rating must be calculated relative to an appropriate comparison cohort.

Recommended cohort definition:

```text
same role
same season / evaluation window
minimum minutes threshold
same competition level OR league-strength-adjusted population
```

Example:

```text
Advanced Forward
2026–27
minimum 900 minutes
top-flight competitions
```

A player should not be standardized against unrelated positions.

---

# 3. Data Quality Before Normalization

Normalization should happen only after obvious data problems are handled.

## Minimum exposure

Recommended initial thresholds:

```text
Season rating:
minimum 900 minutes

Rolling / shorter-window rating:
use reliability shrinkage
```

Do not allow a player with 90 minutes and one exceptional match to define the top of the rating distribution.

---

# 4. Sample-Size Stabilization

For rate statistics, use **reliability shrinkage** before standardization when the sample is small.

General form:

\[
x_i^*
=
r_i x_i
+
(1-r_i)\mu
\]

where:

\[
r_i = \frac{n_i}{n_i+k}
\]

and:

```text
x_i      = observed player metric
x_i*     = stabilized metric
μ        = role-population mean
n_i      = exposure for the metric
k        = shrinkage strength
```

Examples of exposure:

```text
Goals / shots metrics       → shots
Take-on success             → take-on attempts
Aerial duel win %           → aerial duel attempts
Pass completion %           → pass attempts
Per-90 volume metrics       → minutes
```

### Behavior

High exposure:

```text
n >> k
r ≈ 1
```

The player's actual value is preserved.

Low exposure:

```text
n << k
r is small
```

The value is pulled toward the role average because the estimate is uncertain.

This prevents small-sample noise from looking like a genuine elite gap.

---

# 5. Normalization Method

Use **standard z-score normalization** on the stabilized/context-adjusted metrics.

\[
z_{ij}
=
\frac{x_{ij}-\mu_j}{\sigma_j}
\]

where:

```text
xij = player i's value for metric j
μj  = mean of metric j in the comparison population
σj  = standard deviation of metric j in the comparison population
```

## Why standard z-score is the default

The goal is to preserve **magnitude differences**.

If:

```text
Player A = +3.0 SD
Player B = +2.9 SD
Player C = +1.8 SD
```

the model preserves:

```text
A vs B gap = 0.1 SD
B vs C gap = 1.1 SD
```

Percentile ranking alone would largely hide that difference.

Standard z-scores also allow genuine elite outliers to remain elite rather than deliberately compressing them.

---

# 6. Do Not Use Percentile Normalization on Features

Do not transform:

```text
npxG / 90
xA / 90
duel win %
box touches / 90
...
```

into percentiles before aggregation.

Example:

```text
Player A metric = 0.91
Player B metric = 0.90
Player C metric = 0.62
```

A percentile transformation could produce something like:

```text
A = 99th
B = 98th
C = 97th
```

and destroy the actual magnitude information.

Use standardized values for scoring.

Use percentiles **only after the final role score has been calculated**.

---

# 7. Metric Direction

All standardized metrics must point in the same direction:

```text
higher = better
```

For positive metrics:

\[
z^+ = z
\]

For negative metrics:

\[
z^- = -z
\]

Examples of negative metrics:

```text
Miscontrols / 90
Dispossessed / 90
Turnovers / 90
Errors leading to shots
```

Example:

If:

```text
Dispossessed / 90 z-score = +1.4
```

then the model uses:

```text
adjusted z = -1.4
```

---

# 8. Quality Composite Scores

Each quality is built from its standardized feature values.

Example:

\[
Q_{\text{Finishing,raw}}
=
\sum_{j=1}^{m} w_jz_j
\]

where:

```text
wj = feature weight inside the quality
zj = standardized feature value
Σwj = 1
```

Example:

```text
Finishing
├── NPG / 90             20%
├── npxG / 90            18%
├── NPG - npxG / 90      14%
├── Shots / 90            8%
├── SoT / 90             10%
├── SoT %                10%
├── Goals / shot         10%
└── npxG / shot          10%
```

---

## 8.1 Zero-filled feature weight redistribution — effective 7 October 2026

Apply this rule to every feature inside each parent ability, not only fouls won.
It supersedes the former requirement that every weighted feature be recorded.

**Only features explicitly labelled `unrecorded_zero` are excluded.** Never
identify missing evidence by testing whether its numeric value equals zero.
A genuine recorded 0 remains an observed value, keeps its weight share and
participates in stabilization, normalization and scoring normally.

After combining source features and selecting values with
**Opta → PitchAPI → Understat → WhoScored** priority, let `A` contain the
features whose status is not `unrecorded_zero`. For original weights summing
to 1, use:

```text
effective_weight[j] = original_weight[j] / sum(original_weight[k] for k in A)
                     when j is in A
effective_weight[j] = 0 when j is unrecorded_zero
```

This redistributes all excluded weight proportionally and preserves the ratio
between remaining weights. If no feature is excluded, the original weights
remain exactly unchanged. A recorded zero also receives its proportional share
when another feature is excluded; it is never removed because its value is 0.

Example: `5:2:2:1`, where the last feature is zero-filled:

```text
Original weights: 50%, 20%, 20%, 10%
Remaining weight: 90%
Effective weights: 50/90, 20/90, 20/90, 0
                 = 55.5556%, 22.2222%, 22.2222%, 0%
Remaining ratio: 5:2:2
```

For current ST Physicality, when dispossessed alone is explicitly zero-filled:

| Feature | Original weight | Effective weight |
|---|---:|---:|
| Duels won / 90 | 10% | 13.3333% |
| Duel success % | 30% | 40% |
| Aerial duels won / 90 | 10% | 13.3333% |
| Aerial success % | 25% | 33.3333% |
| Dispossessed / 90 — zero-filled only | 25% | 0% |

Fouls won is no longer a scored Physicality input. If dispossessed is an actual recorded zero, the original weights stay 10/30/10/25/25%.

Use effective weights for both the evaluated player and the reference cohort.
Compare peers with matching feature masks, weights, measurement definitions,
role and season/window, pooling peers across the top five European leagues.
Do not restrict peers to the player's league. No league-strength adjustment is
applied in this version. Re-standardize the resulting ability and role
composites as before. Retain the existing 900-minute and 30-compatible-peer
requirements; do not create an artificial missing-data penalty or a new
minimum coverage threshold.

All original feature rows remain inspectable. Store original/effective weights,
excluded feature keys, evidence flags, peer identities and weighting version
the content-versioned weighting identifier from `position_rating_weights_config.yaml`. Excluded features have no
performance percentile, z-score or fabricated reference distribution. Raw
missing measurements are explicitly labelled as zero-filled for this local
scoring policy; source snapshots remain unchanged.

An undefined ratio from recorded zero attempts remains N/A, not an observed 0
and not automatically an `unrecorded_zero`. Invalid records remain invalid.
Context-only features retain zero directional contribution. If every scoring
feature in an ability is zero-filled, that ability remains unavailable; do not
fabricate a score or redistribute its parent-level ST weight. Overall ST rating
still requires all six calibrated abilities and compatible common peers.

---

# 9. Re-Standardize the Quality Composite

A weighted sum of z-scores is not guaranteed to have:

```text
mean = 0
standard deviation = 1
```

because the underlying features are correlated.

Therefore, after calculating the raw quality composite, standardize it again across the role population:

\[
Q_z
=
\frac{Q_{\text{raw}}-\mu_Q}{\sigma_Q}
\]

This gives every quality a common magnitude scale.

---

# 10. Convert Quality Scores to 0–100

Use the same display transformation for every quality.

Recommended initial transformation:

\[
\boxed{
Q_{\text{rating}}
=
50 + 15Q_z
}
\]

Then clip only for display:

\[
Q_{\text{display}}
=
\max(1,Q_{\text{rating}})
\]

### Interpretation

| Standardized quality | Display rating |
|---:|---:|
| -3.0 | 5 |
| -2.5 | 12.5 |
| -2.0 | 20 |
| -1.5 | 27.5 |
| -1.0 | 35 |
| -0.5 | 42.5 |
| 0.0 | **50** |
| +0.5 | 57.5 |
| +1.0 | 65 |
| +1.5 | 72.5 |
| +2.0 | 80 |
| +2.5 | 87.5 |
| +3.0 | 95 |

The engine should retain the unbounded `Q_z` internally.

---

# 11. Why the Base Rating Is 50

Use:

\[
\boxed{z=0 \rightarrow rating=50}
\]

because 50 represents the center of the comparison population.

This makes the scale symmetric:

```text
0 ---------------- 50 ---------------- 100
                   average
```

Interpretation:

```text
50   average for the role
60   clearly above average
70   very strong
80   elite
90+  exceptional
<50  below role average
```

Using 70 as the average would waste much of the lower half of the scale and make the rating less statistically interpretable.

---

# 12. Role Composite Score

Do **not** calculate the final role rating from the displayed 0–100 quality ratings.

Use the underlying standardized quality scores.

Example for a striker role:

\[
S_{\text{raw}}
=
0.27F_z
+
0.20B_z
+
0.17L_z
+
0.14C_z
+
0.12P_z
+
0.10D_z
\]

where:

```text
Fz = Finishing quality z-score
Bz = Box Threat quality z-score
Lz = Link-Up quality z-score
Cz = Carrying / 1v1 quality z-score
Pz = Physicality quality z-score
Dz = Defensive Activity quality z-score
```

Role weights should sum to:

\[
1.00
\]

---

# 13. Re-Standardize the Role Composite

Because the qualities are correlated, re-standardize the final role composite across the role population:

\[
S_z
=
\frac{S_{\text{raw}}-\mu_S}{\sigma_S}
\]

`S_z` is the main latent performance score.

This is the value that should drive:

- player ordering,
- performance-gap calculations,
- comparison logic,
- final rating transformation.

---

# 14. Final Role Rating

Convert the standardized role score to the same base-50 scale:

\[
\boxed{
R
=
50 + 15S_z
}
\]

Display:

\[
R_{\text{display}}
=
\max(1,R)
\]

Store both:

```text
role_z_score
role_rating_unclipped
role_rating_display
```

Example:

```text
Player A
role_z_score          = +2.80
unclipped rating      = 92.0
display rating        = 92

Player B
role_z_score          = +2.10
unclipped rating      = 81.5
display rating        = 82
```

Gap:

\[
2.80 - 2.10 = 0.70\sigma
\]

and approximately:

\[
0.70 \times 15 = 10.5
\]

rating points.

---

# 15. Percentile Ranking

After `S_z` has been calculated, compute the player's empirical percentile within the role population.

Recommended definition:

\[
P_i
=
100
\times
\frac{\#(S_j < S_i)+0.5\#(S_j=S_i)}
{N}
\]

This handles ties cleanly.

Example output:

```text
Role Rating:       92
Percentile:        98.7
Role z-score:      +2.80
```

Percentile answers:

> Where does this player rank?

Rating answers:

> How far above or below the role population is this player?

---

# 16. Why Rating and Percentile Must Stay Separate

Consider:

```text
Player A    z = +3.0
Player B    z = +2.9
Player C    z = +1.8
```

Possible percentiles:

```text
A   99.8
B   99.4
C   99.0
```

Percentile gaps:

```text
A → B = 0.4
B → C = 0.4
```

But actual standardized gaps:

```text
A → B = 0.1 SD
B → C = 1.1 SD
```

Using the base-50 rating:

```text
A = 95.0
B = 93.5
C = 77.0
```

Now the displayed rating reflects the real magnitude difference.

---

# 17. Gap Metrics

Store explicit gap information.

## Gap to next player

\[
Gap_{z}
=
S_{z,i}
-
S_{z,i+1}
\]

Approximate rating gap before clipping:

\[
Gap_R = 15 \times Gap_z
\]

Example:

```text
#1 Player A
z = 3.10
rating = 96.5

#2 Player B
z = 2.95
rating = 94.25

gap = 0.15 SD
rating gap = 2.25
```

versus:

```text
#1 Player A
z = 3.10
rating = 96.5

#2 Player B
z = 2.30
rating = 84.5

gap = 0.80 SD
rating gap = 12.0
```

The ranking is still `#1` and `#2` in both cases, but the gap is correctly visible.

---

# 18. Preserve Unclipped Latent Scores

The UI may cap ratings at:

```text
1–99
```

but the engine must never discard the underlying value.

Example:

```text
Player A
z = +3.8
raw rating = 107
display rating = 99

Player B
z = +3.2
raw rating = 98
display rating = 98
```

For ranking and gap calculations use:

```text
3.8 vs 3.2
```

not:

```text
99 vs 98
```

This prevents the display cap from destroying information about extreme outliers.

---

# 19. Treatment of Genuine Outliers

Do not automatically use robust scaling to suppress elite outliers.

If:

```text
Player A = genuinely +4 SD
```

the model should preserve that information.

Default:

```text
standard z-score
```

not:

```text
robust z-score
percentile transformation
min-max scaling
```

Robust methods should be used only when diagnostics show that the distribution is being distorted by:

- data errors,
- tiny samples,
- pathological tails,
- source inconsistencies.

The preferred approach is:

```text
data validation
→ sample-size stabilization
→ contextual adjustment
→ standard z-score
```

rather than weakening genuine elite performances.

---

# 20. Skewed Metrics

Standard z-scores do not require the metric itself to be perfectly normally distributed.

However, extremely skewed metrics should be inspected.

Recommended decision order:

```text
1. Check for data errors.
2. Apply minimum exposure.
3. Apply sample-size stabilization.
4. Inspect the distribution.
5. Keep standard z-score if the remaining extremes are genuine.
6. Transform only metrics whose raw scale creates pathological behavior.
```

Do not automatically log-transform every metric.

Any transformation changes the meaning of player-to-player gaps.

---

# 21. Avoid Min-Max Scaling

Do not use:

\[
R_i
=
100
\frac{x_i-x_{\min}}
{x_{\max}-x_{\min}}
\]

for the primary rating.

Min-max scaling makes every player's score depend too heavily on the single highest and lowest observations.

If a new extreme player enters the dataset, everybody else's rating changes substantially even if their performance does not.

Use distribution-based standardization instead.

---

# 22. Recommended Stored Fields

For every player-role evaluation store:

```text
player_id
role_id
season
competition
minutes

quality_raw_scores
quality_z_scores
quality_display_ratings

role_composite_raw
role_z_score
role_rating_unclipped
role_rating_display

role_percentile
role_rank
role_population_size

gap_to_next_z
gap_to_previous_z

reference_population_id
normalization_version
weighting_version
calculation_timestamp
```

---

# 23. UI Recommendation

Player card:

```text
        92
ADVANCED FORWARD

98.7th percentile
```

Expanded analytical view:

```text
ROLE RATING                  92
ROLE PERCENTILE            98.7
ROLE Z-SCORE              +2.80
ROLE RANK                   #3
POPULATION                 286

Finishing                    94
Box Threat                   91
Link-Up                      77
Carrying / 1v1               84
Physicality                  69
Defensive Activity           71

Gap to next player        +0.31 SD
Gap to role average       +2.80 SD
```

---

# 24. Final Formula Summary

## Metric standardization

\[
z_j
=
\frac{x_j-\mu_j}{\sigma_j}
\]

## Negative metric

\[
z_j^*=-z_j
\]

## Quality composite

\[
Q_{\text{raw}}
=
\sum_j w_jz_j
\]

## Quality re-standardization

\[
Q_z
=
\frac{Q_{\text{raw}}-\mu_Q}{\sigma_Q}
\]

## Quality rating

\[
Q_R
=
50+15Q_z
\]

## Role composite

\[
S_{\text{raw}}
=
\sum_k a_kQ_{z,k}
\]

## Role re-standardization

\[
S_z
=
\frac{S_{\text{raw}}-\mu_S}{\sigma_S}
\]

## Role rating

\[
\boxed{
R=50+15S_z
}
\]

## Display rating

\[
R_{\text{display}}
=
\max(1,R)
\]

## Percentile

\[
P_i
=
100
\times
\frac{\#(S_j<S_i)+0.5\#(S_j=S_i)}
{N}
\]

---

# 25. Recommended Default

Use the following as the initial production rule:

```text
Normalization:
standard z-score

Outlier policy:
preserve genuine outliers

Small-sample policy:
reliability shrinkage before standardization

Quality scale:
50 + 15 × quality_z

Role scale:
50 + 15 × role_z

Rating bounds:
1–99 for display only

Ranking:
empirical percentile of final role_z

Gap measurement:
difference in latent role_z

Comparison population:
same role + same evaluation period + adequate minutes

Percentile use:
ranking only, never primary magnitude score
```

This keeps the system statistically interpretable while preserving genuine differences between players.
