# Ability Visualization Rules

**Purpose:** Define the visual and interaction system for player ability charts and feature distributions.

**Design goal:** The interface should feel **dimensional, tactile, interactive, and visually engaging** while remaining statistically informative and easy to read.

The visualization hierarchy should mirror the scoring hierarchy:

```text
PLAYER
   ↓
ROLE RATING
   ↓
SUMMARY ABILITIES
   ↓
RADAR CHART
   ↓ click ability
ABILITY DETAIL
   ↓
UNDERLYING FEATURES
   ↓
DISTRIBUTION CHARTS
   ↓ hover
RAW VALUE + PEER AVERAGE + PERCENTILE + SD GAP
```

---

# 1. Core Visualization Principles

1. **Summary first, evidence second.**
2. The radar shows **high-level abilities only**.
3. Clicking an ability reveals the features used to build that ability.
4. Each feature has its own population distribution.
5. Every chart is tied to the currently selected role.
6. Use the **ability rating** for radar geometry.
7. Use **percentile** as supporting ranking information.
8. Show exact raw values in the feature-detail layer.
9. Preserve the visual meaning of the base-50 rating system.
10. Depth and animation should reinforce hierarchy and interaction, not obstruct analysis.
11. Do not use decorative motion that makes values harder to compare.
12. Every interactive state must have a clear analytical purpose.

---

# 2. Main Layout

Recommended desktop structure:

```text
┌─────────────────────────────────────────────────────────────┐
│ Player Header                                               │
│ Name · Club · Position · Role selector · Primary Rating     │
├───────────────────────────────┬─────────────────────────────┤
│                               │                             │
│        RADAR / ABILITIES      │   SELECTED ABILITY DETAIL   │
│                               │                             │
│   Summary role profile        │   Feature distributions     │
│   Peer-average reference      │   Raw values                │
│                               │   Percentiles               │
│                               │   SD gaps                   │
│                               │                             │
└───────────────────────────────┴─────────────────────────────┘
```

On narrower screens:

```text
Player header
    ↓
Radar
    ↓
Selected ability
    ↓
Feature distributions
```

---

# 3. Radar Chart Purpose

The radar chart is for **summary abilities**, not raw metrics.

Example ST radar:

```text
Finishing
Box Threat
Link-Up / Creation
Carrying / 1v1
Physicality
Defensive Activity
```

Recommended maximum:

```text
5–8 axes
```

Do not place 12–20 raw metrics on the radar.

---

# 4. Radar Rating Scale

Use the same scale as the rating system.

```text
20
35
50   ← peer-average reference
65
80
95
```

Interpretation:

```text
50 = role average
65 = +1 SD
80 = +2 SD
95 = +3 SD
```

The **50 ring must be visually distinct**.

This makes the radar analytically meaningful:

```text
inside 50   = below role average
outside 50  = above role average
```

---

# 5. Radar Visual Layers

The radar should have visible depth.

Use three conceptual layers:

```text
Layer 1 — recessed background plane
Layer 2 — radial reference rings / peer-average plane
Layer 3 — player polygon + interactive nodes
```

### Background plane

Use:

```text
deep charcoal
very dark green undertone
subtle pitch-like texture or fine noise
soft vignette
```

Avoid a completely flat black background.

### Reference rings

Use:

```text
thin low-contrast silver/gray lines
slightly raised visual treatment
50 ring brighter than other rings
```

### Player polygon

Use:

```text
semi-transparent fill
clear illuminated edge
subtle inner gradient
soft drop shadow
light local glow
```

The polygon should feel slightly elevated above the reference plane.

---

# 6. Radar Depth

Depth should be subtle but noticeable.

Recommended effects:

```text
soft polygon shadow
inner glow
slight highlight along upper edge
very small vertical separation from grid
subtle pointer-driven parallax
```

Do not use strong perspective distortion.

The chart must remain geometrically readable.

### Pointer parallax

Optional:

```text
max rotation: very small
max translation: a few pixels
```

The chart may respond slightly to pointer position, but labels and values should remain stable.

---

# 7. Ability Nodes

Each radar axis should terminate in an interactive ability node.

At rest:

```text
FINISHING
91
```

On hover:

```text
FINISHING
91
P98 · +2.73 SD
```

On selection:

```text
FINISHING
91
P98 · +2.73 SD
8 underlying metrics
```

### Node behavior

Rest:

```text
normal opacity
small anchor point
```

Hover:

```text
node lifts slightly
spoke brightens
local polygon region brightens
label expands
cursor indicates interaction
```

Selected:

```text
selected accent
other nodes reduce to ~50% opacity
selected spoke remains emphasized
detail panel updates
```

---

# 8. Ability Selection

Clicking an ability should:

```text
1. Lock the ability as selected.
2. Emphasize the corresponding radar sector.
3. Reduce visual weight of unselected sectors.
4. Update the detail panel.
5. Animate the feature distributions into view.
```

Recommended timing:

```text
hover transitions: 150–220 ms
selection transitions: 180–280 ms
panel content transition: 250–400 ms
```

Avoid bouncing or arcade-like motion.

---

# 9. Visual Connection Between Radar and Detail Panel

The selected radar ability should visually connect to the detail panel.

Use one or more:

```text
matching accent state
aligned highlight
subtle directional light trail
small animated transition from node toward panel
```

Do not use a heavy permanent connector line.

The relationship should be obvious without clutter.

---

# 10. Ability Detail Header

Example:

```text
FINISHING

91
98th percentile
+2.73 SD vs Advanced Forward peers
```

Optional metadata:

```text
8 component features
Population: 246 players
Minimum minutes: 900
```

Use the large rating as the dominant element.

---

# 11. Feature Detail List

When an ability is selected, show every feature used to build it.

Example:

```text
NPG / 90
npxG / 90
NPG - npxG / 90
Shots / 90
Shots on Target / 90
Shot-on-Target %
Goals / Shot
npxG / Shot
```

Each row should include:

```text
feature name
raw player value
peer average
percentile
optional model weight
distribution chart
```

Recommended structure:

```text
NPG / 90             0.72       P95       weight 20%
[distribution chart]
```

---

# 12. Distribution Chart Purpose

Each feature distribution should communicate:

```text
where the player sits
how concentrated the peer population is
whether the player is a genuine outlier
distance from average
percentile position
raw metric value
```

The distribution is not decorative.

---

# 13. Distribution Chart Form

Preferred:

```text
smoothed density ridge
```

Alternative:

```text
compact histogram
```

Fallback:

```text
box plot + player marker
```

For the main UI, use the smoothed density ridge.

Example:

```text
                         PLAYER
                           ▼
                ╭──────────●
          ╭─────╯████████████╲
─────────╯████████████████████╲─────────
                population
```

---

# 14. Distribution Chart Depth

The distribution should look like a small data landscape.

Use:

```text
dark neutral base
soft vertical or radial shading
slight ridge highlight
subtle lower shadow
player marker above the ridge
```

The high-density area should appear visually fuller.

Do not distort the actual density shape for aesthetic purposes.

---

# 15. Distribution Color System

Do not use a rainbow gradient by default.

Recommended:

```text
population density     dark silver / graphite
upper-performance area soft warm tint
player marker          bright champagne / pale accent
average marker         cool silver
selected state         restrained crimson
comparison marker      contrasting cyan or crimson outline
```

The color system should remain readable in dark mode.

---

# 16. Player Marker

The player marker should be clearly anchored to the distribution.

Recommended forms:

```text
small illuminated dot
thin vertical beam
triangle pointer
```

Example:

```text
                       ▼
───────────────╭──────●──────╮──────────────
```

Hovering the marker should reveal:

```text
Player value
Role average
Difference
Percentile
Standard deviation gap
Population size
```

Example tooltip:

```text
npxG / 90

Player             0.71
Role average       0.42
Difference         +0.29
Standardized       +1.84 SD
Percentile         95.1
Population         246
```

---

# 17. Average Marker

Every feature distribution should show the comparison-population average.

Recommended:

```text
thin muted vertical line
small AVG label on hover
```

Do not let the average marker visually compete with the player marker.

---

# 18. Gap Visualization

Because the rating system explicitly preserves magnitude gaps, display the player-to-average gap visually.

Example:

```text
AVG                              PLAYER
 │────────────────────────────────│
50                                 86
```

For feature-level charts:

```text
average marker
       │
       │──────────── distance ─────────────│
                                          player
```

On hover:

```text
+0.29 raw units
+1.84 SD
95th percentile
```

---

# 19. Distribution Hover Interaction

The distribution itself should be explorable.

As the pointer moves across the density:

```text
vertical scanner line follows pointer
current x-value displayed
local density displayed
approximate percentile displayed
```

Example:

```text
0.60–0.70 npxG / 90
14 players
Top 11% of comparison population
```

This interaction should remain secondary.

The player's actual marker must always remain visible.

---

# 20. Radar ↔ Feature Linking

Hover interactions should work in both directions.

### Radar to feature list

Hovering:

```text
FINISHING
```

may softly emphasize all Finishing feature rows.

### Feature list to radar

Hovering:

```text
npxG / 90
```

should:

```text
highlight Finishing node
brighten Finishing spoke
softly emphasize the corresponding radar sector
```

This makes the scoring hierarchy visually explainable.

---

# 21. Role Awareness

All visualizations must use the currently selected role.

Example:

```text
Selected Role:
Advanced Forward
```

Then:

```text
radar ability scores
feature z-scores
feature percentiles
peer averages
distribution populations
role rating
```

must all be based on:

```text
Advanced Forward comparison population
```

If the role changes to:

```text
False 9
```

the entire visualization recalculates and animates to the new values.

---

# 22. Role Switching Animation

When changing role:

```text
1. Polygon smoothly morphs to new shape.
2. Ability values count/morph to new ratings.
3. Peer reference updates.
4. Selected feature panel updates.
5. Distribution markers animate to new locations.
```

Recommended duration:

```text
300–450 ms
```

The animation should communicate that the same player is being viewed through a different tactical lens.

---

# 23. Comparison Mode

Allow one optional comparison player.

Default state:

```text
Current Player
vs
Role Average
```

Comparison state:

```text
Current Player
vs
Selected Player
vs
Role Average
```

### Radar rendering

Use:

```text
current player     filled polygon
peer average       thin dashed/neutral outline
comparison player  outline only
```

Do not use two strong overlapping filled polygons.

---

# 24. Comparison Distribution Markers

When comparing two players:

```text
Player A marker
Player B marker
Average marker
```

Example:

```text
      Player A ▼                 Player B ▼
──────────●──────────────────────────●──────────
                     │
                    AVG
```

Hovering a marker should show that player's exact data.

---

# 25. Comparison Interaction

On radar hover:

```text
ability
Player A rating
Player B rating
gap in rating
gap in SD
```

Example:

```text
FINISHING

Player A       91
Player B       83
Gap            +8
Latent gap     +0.53 SD
```

---

# 26. Player Card Integration

The chart should visually connect to the player's main card.

Suggested hierarchy:

```text
Player Name
Role
Primary / Role Rating
Percentile
Radar
```

Example:

```text
HARRY KANE

Advanced Forward

91
P98
```

Then the radar sits directly below or beside this information.

---

# 27. Typography

Use **Source Sans 3** for:

```text
labels
controls
raw metrics
percentiles
tooltips
filters
axis values
```

Hierarchy:

```text
Role rating        very large
Ability rating     large
Ability name       medium / bold
Feature name       medium
Raw metric         medium / numerical
Metadata           small
```

Numerical alignment should be consistent.

Use tabular numerals where available.

---

# 28. Depth Through Typography

Use depth sparingly:

```text
large rating appears visually forward
secondary metadata appears flatter
feature labels remain crisp and neutral
```

Avoid heavy text shadows.

A soft local glow or subtle contrast lift is enough for selected numerical values.

---

# 29. Motion Rules

Motion should indicate:

```text
selection
comparison
role change
focus
data movement
```

Avoid:

```text
constant looping pulse
continuous bouncing
excessive glow animation
decorative particle motion
```

Recommended timing:

```text
micro hover         120–180 ms
node selection      180–250 ms
panel transition    250–400 ms
role switch         300–450 ms
player comparison   300–450 ms
```

Use easing that feels smooth and responsive.

---

# 30. Interactive Depth States

Every interactive chart element should have:

```text
rest
hover
selected
comparison
disabled
keyboard focus
```

Example node behavior:

```text
REST
normal depth

HOVER
+ slight elevation
+ brighter edge
+ local glow

SELECTED
+ persistent accent
+ strongest depth
+ detail panel link

UNSELECTED WHILE ACTIVE
reduced opacity
```

---

# 31. Negative Metrics

Some features are worse when higher.

Examples:

```text
Dispossessed / 90
Miscontrols / 90
Turnovers / 90
```

The UI must communicate this.

Use:

```text
"Lower is better"
small downward direction icon
negative-direction tooltip
```

The distribution should show the raw value normally.

Do not reverse the x-axis.

The scoring engine may invert the standardized value internally, but the chart should preserve the metric's natural numerical direction.

---

# 32. Feature Weight Visibility

Feature weights may be shown as secondary information.

Example:

```text
npxG / 90        0.68   P93        18%
```

Weight styling should be subtle.

Weights explain the model but should not visually dominate actual performance.

---

# 33. Peer Population Information

Every detailed view should make the comparison population inspectable.

Example:

```text
Compared against:
Advanced Forwards
Top-flight leagues
2026–27
Minimum 900 minutes
N = 246
```

This can live in:

```text
tooltip
info popover
secondary footer
```

---

# 34. Selected Benchmark Controls

Default benchmark:

```text
Role Average
```

Optional benchmark selector:

```text
Role Average
Top 10% Benchmark
Selected Player
Team Average
League Average
```

The default should remain **Role Average**.

---

# 35. Top-10% Benchmark

Optional:

```text
Top 10% role benchmark
```

can be shown as a faint secondary reference.

Do not show it by default if it creates visual clutter.

It is useful in advanced scouting mode.

---

# 36. Radar Label Rules

Radar labels must remain readable at all times.

Use:

```text
short ability names
rating directly beside/below name
no rotated text where avoidable
```

Example:

```text
FINISHING
91
```

instead of long curved labels around the chart.

---

# 37. Mobile Behavior

On mobile:

```text
Radar remains fully visible.
Only one comparison polygon at a time.
Feature detail opens below radar.
Distribution rows become full width.
Hover interactions become tap interactions.
```

Ability tap:

```text
first tap = select
second tap / detail control = expand
```

---

# 38. Accessibility

Support:

```text
keyboard ability navigation
visible focus state
screen-reader labels
reduced-motion preference
color-independent distinction
```

Do not rely only on color for:

```text
selected state
comparison player
positive/negative meaning
```

Use line style, icons, labels, or shape differences as well.

---

# 39. Performance

Charts should feel immediate.

Target:

```text
smooth interaction
minimal layout shift
no expensive redraw on simple hover
```

Use SVG or canvas depending on implementation scale.

For a normal player-detail view with a small number of charts, SVG is preferable for:

```text
crisp labels
interaction
accessibility
responsive scaling
```

---

# 40. Recommended Visual Identity

Base environment:

```text
deep charcoal surroundings
dark green analytical surfaces
silver / cool-gray typography
warm champagne rating numerals
restrained crimson selection states
```

The system should feel:

```text
interactive
dimensional
alive
football-specific
analytical
```

It does not need to feel luxurious or formal.

---

# 41. Avoid

Do not use:

```text
heavy fake 3D perspective
rainbow gradients without meaning
constant neon glows
overlapping filled comparison polygons
too many radar axes
raw metrics on the radar
hidden numerical values
decorative animation that blocks reading
different scales between players
percentile as radar geometry
```

---

# 42. Recommended ST Example

Default:

```text
HARRY KANE

Advanced Forward
Role Rating: 91
Percentile: P98

RADAR
├── Finishing            93
├── Box Threat           90
├── Link-Up              86
├── Carrying / 1v1       74
├── Physicality          82
└── Defensive Activity   58
```

Click:

```text
FINISHING
```

Detail:

```text
FINISHING                   93
Percentile                 P99
Gap to average          +2.87 SD

NPG / 90
0.74
P97
[distribution]

npxG / 90
0.69
P95
[distribution]

NPG - npxG / 90
+0.05
P78
[distribution]

Shots / 90
4.21
P91
[distribution]

...
```

---

# 43. Final Interaction Model

```text
OPEN PLAYER
      ↓
see role rating + summary radar
      ↓
hover ability
      ↓
quick rating + percentile + SD
      ↓
click ability
      ↓
ability locks as selected
      ↓
feature panel opens
      ↓
distribution ridges animate in
      ↓
hover feature
      ↓
radar ability highlights
      ↓
hover distribution
      ↓
raw value + average + percentile + SD gap
      ↓
optional compare player
      ↓
second radar outline + second distribution marker
```

---

# 44. Final Rule Set

```text
Radar:
summary abilities only

Radar value:
ability rating, not percentile

Default benchmark:
role average

Ability selection:
opens underlying feature distributions

Distribution:
population density + player marker + average marker

Hover information:
raw value + peer average + percentile + SD gap

Depth:
layered surfaces + subtle elevation + restrained glow

Motion:
short, informative, state-driven

Role switching:
recalculate and morph all visuals

Comparison:
one additional player, outline only on radar

Negative metrics:
keep natural axis direction and label "lower is better"

Primary design objective:
make the system visually engaging without hiding analytical meaning
```
