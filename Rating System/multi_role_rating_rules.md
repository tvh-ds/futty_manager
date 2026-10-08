# Multi-Role Rating Rules

**Purpose:** Define how to score players who can perform multiple roles without distorting specialists, double-counting ability, or averaging incompatible role ratings.

---

# 1. Core Rule

Do **not** average all displayed role ratings to create one overall rating.

Example:

```text
Advanced Forward     91
Poacher              87
Inside Forward       89
False 9              81
Target Forward       68
```

Simple average:

```text
83.2
```

This is misleading because the player may be elite in one role and poor in another.

A weak secondary role should not reduce the player's headline ability.

---

# 2. Every Player Can Have Multiple Role Ratings

Each role is scored independently using that role's own:

```text
feature set
quality weights
role weights
comparison population
normalization
```

Example:

```text
Player X

Advanced Forward     91
Inside Forward       89
Poacher              87
False 9              81
Target Forward       68
```

Each role rating answers:

> How strong is this player when evaluated specifically for this role?

---

# 3. Primary Rating

The player's headline rating should normally be their **best valid role rating**.

Internally, choose the role using the latent role score:

\[
Z_{\text{primary}}
=
\max(Z_1,Z_2,\dots,Z_n)
\]

Then display the calibrated rating associated with that role.

Example:

```text
Advanced Forward     91
Inside Forward       89
Poacher              87
False 9              81
```

Result:

```text
Primary Rating       91
Primary Role         Advanced Forward
```

## Important

Do not choose the best role by rounded display rating when latent scores are available.

Use:

```text
role_z_score
```

rather than:

```text
display_rating
```

to determine the strongest role.

---

# 4. Specialists Must Not Be Penalized

Example:

```text
Advanced Forward     94
Poacher              88
False 9              72
Inside Forward       69
```

Do not calculate:

\[
(94+88+72+69)/4
\]

as the player's overall ability.

Correct interpretation:

```text
Primary Rating       94
Primary Role         Advanced Forward
Versatility          lower
```

A specialist can be an elite player even if they fit relatively few roles.

---

# 5. Versatility Is Separate From Ability

Versatility answers:

> How many roles can this player perform at a strong level?

It should be calculated separately from the primary rating.

Example specialist:

```text
Advanced Forward     94
Poacher              88
False 9              72
Inside Forward       69

Primary Rating       94
Versatility          63
```

Example versatile attacker:

```text
Advanced Forward     88
Poacher              86
False 9              87
Inside Forward       89

Primary Rating       89
Versatility          91
```

The versatile player is not automatically "better" overall.

The specialist is better at their best role.

---

# 6. Suggested Versatility Calculation

Use role ratings only from **relevant/eligible roles**.

Do not include unrelated roles such as:

```text
GK
CB
DM
```

when evaluating an attacking player's versatility.

A simple starting method:

```text
1. Select relevant roles.
2. Convert their latent role z-scores to a common reference.
3. Reward both:
   - number of roles above a quality threshold
   - closeness of secondary roles to the primary role
```

Suggested concept:

\[
V
=
w_1(\text{breadth})
+
w_2(\text{secondary-role quality})
+
w_3(\text{consistency across roles})
\]

Versatility should not replace any role rating.

---

# 7. Hybrid Roles

A hybrid role combines multiple tactical roles.

Examples:

```text
Advanced Forward / Inside Forward
False 9 / CAM
Wing Back / Full Back
Ball-Winning Midfielder / Deep-Lying Playmaker
```

Do not average the displayed role ratings directly.

Incorrect:

\[
R_H
=
\frac{R_A+R_B}{2}
\]

Preferred method:

\[
H_{\text{raw}}
=
w_AZ_A
+
w_BZ_B
\]

where:

```text
ZA = latent standardized score for role A
ZB = latent standardized score for role B
wA + wB = 1
```

Example:

\[
H_{\text{raw}}
=
0.60Z_{\text{Inside Forward}}
+
0.40Z_{\text{Advanced Forward}}
\]

---

# 8. Hybrid Recalibration

After calculating hybrid scores for all eligible players, standardize the hybrid population:

\[
H_z
=
\frac{H_{\text{raw}}-\mu_H}{\sigma_H}
\]

Then convert to the standard rating scale:

\[
\boxed{
R_{\text{Hybrid}}
=
50+15H_z
}
\]

Display bounds:

\[
R_{\text{display}}
=
\min(99,\max(1,R_{\text{Hybrid}}))
\]

The hybrid rating should therefore be treated as its own role-like evaluation.

---

# 9. Why Hybrid Ratings Can Exceed Both Component Ratings

Example:

```text
Advanced Forward     91
Inside Forward       89
Hybrid               93
```

This is valid.

The hybrid score is recalibrated against players competing for that specific hybrid profile.

A player who is unusually strong in both component roles may rank even better within the hybrid population.

Therefore:

```text
Hybrid rating
```

does not have to mathematically sit between the two displayed component ratings.

---

# 10. Do Not Average Display Ratings Across Different Role Populations

Role ratings may be calibrated against different comparison groups.

Example:

```text
Advanced Forward 90
False 9          80
```

These mean:

```text
90 = very strong relative to Advanced Forwards
80 = strong relative to False 9s
```

They should not automatically be treated as directly additive raw measurements.

Use the underlying standardized role scores for:

```text
hybrids
gap calculations
role blending
cross-role modeling
```

---

# 11. Recommended Player Outputs

Each player should expose:

```text
Primary Rating
Primary Role

Role Ratings
Role Percentiles

Hybrid Ratings
Hybrid Percentiles

Versatility Score
```

Example:

```text
PLAYER X

PRIMARY
Rating                 91
Role                   Advanced Forward

ROLE RATINGS
Advanced Forward       91
Inside Forward         89
Poacher                87
False 9                81
Target Forward         68

HYBRID RATINGS
AF / Inside Forward    93
AF / Poacher           90

VERSATILITY            86
```

---

# 12. Recommended Data Fields

Store:

```text
player_id

primary_role_id
primary_role_z
primary_rating

role_id
role_z_score
role_rating_unclipped
role_rating_display
role_percentile
role_rank

hybrid_role_id
hybrid_raw_score
hybrid_z_score
hybrid_rating_unclipped
hybrid_rating_display
hybrid_percentile

versatility_score
versatility_components

rating_version
weighting_version
normalization_version
calculation_timestamp
```

---

# 13. Role Eligibility

Not every player should automatically receive every role rating.

Use role eligibility rules.

Possible eligibility criteria:

```text
recorded position
minutes played in relevant position
event profile
touch map
formation usage
coach/scout classification
```

Example:

```text
ST / LW player
```

can reasonably receive:

```text
Poacher
Advanced Forward
False 9
Inside Forward
Pressing Forward
```

but should not automatically receive:

```text
Center Back
Goalkeeper
Deep-Lying Playmaker
```

unless there is evidence the player actually performs those roles.

---

# 14. Position Rating vs Role Rating

Keep these concepts separate.

## Position Rating

Answers:

> How good is the player at this position overall?

Example:

```text
ST Rating = 88
```

It may combine several relevant striker qualities using broad position weights.

## Role Rating

Answers:

> How good is the player in this specific tactical role?

Example:

```text
Advanced Forward = 91
False 9          = 83
Poacher          = 88
```

## Primary Rating

Default:

```text
best valid role rating
```

unless the product later chooses to display position rating as the headline instead.

---

# 15. Multi-Role Player Rule

For players with multiple valid roles:

```text
1. Calculate every valid role independently.
2. Keep all role ratings visible.
3. Use the strongest valid role as Primary Rating.
4. Never average all role ratings into one ability score.
5. Calculate Versatility separately.
6. Use latent standardized role scores for hybrids.
7. Recalibrate each hybrid against its own eligible population.
```

---

# 16. Recommended Final Architecture

```text
RAW METRICS
      ↓
QUALITY SCORES
      ↓
ROLE-SPECIFIC MODELS
      ↓
┌──────────────────────────────────┐
│ Advanced Forward                 │
│ Poacher                          │
│ False 9                          │
│ Inside Forward                   │
│ Target Forward                   │
│ etc.                             │
└──────────────────────────────────┘
      ↓
ROLE Z-SCORES
      │
      ├──────────────→ PRIMARY RATING
      │                best valid role
      │
      ├──────────────→ VERSATILITY
      │                breadth of strong roles
      │
      └──────────────→ HYBRID MODELS
                       weighted role-z combinations
                              ↓
                       hybrid recalibration
                              ↓
                       HYBRID RATINGS
```

---

# 17. Final Rules

```text
Primary Rating:
best valid role rating

Role Rating:
independent evaluation for a specific tactical role

Hybrid Rating:
weighted combination of latent role z-scores,
then recalibrated against the hybrid population

Versatility:
separate score measuring breadth of strong role fit

Do not:
average all role ratings

Do not:
use weak secondary roles to reduce primary ability

Do not:
blend displayed 0–100 ratings when latent role scores are available

Always:
preserve all role ratings individually
```

This structure allows specialists, versatile players, and hybrid tactical profiles to be represented accurately without collapsing them into a misleading single average.
