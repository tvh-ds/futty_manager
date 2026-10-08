---
name: Scout
description: Turf squad planning, role-aware ability evidence and a retained technical recruitment dossier.
colors:
  ss-bg: "#111518"
  ss-surface: "#1b2226"
  ss-border: "#354047"
  ss-text: "#edf0ed"
  ss-muted: "#aab6b4"
  ss-gold: "#decda7"
  ss-crimson: "#b83e49"
  ss-crimson-hover: "#cc4d55"
  ss-shirt: "#a9313b"
  ss-keeper: "#c4bd9a"
  ss-turf: "#10251f"
  ss-green-link: "#86b783"
  ss-yellow-link: "#e5c175"
  ss-red-link: "#e78379"
  ss-unknown-link: "#b1b7b3"
  av-champagne: "#e4d6b8"
  av-rating: "#dfceb0"
  av-selected: "#d16b79"
  av-comparison: "#8dcdd9"
  recruitment-ink: "#182d3a"
  recruitment-muted: "#586772"
  recruitment-line: "#d4d9d7"
  recruitment-green: "#235b48"
  recruitment-paper: "#fffefa"
  recruitment-bg: "#f4f3ed"
  recruitment-ochre: "#785618"
typography:
  headline:
    fontFamily: "Source Sans 3, sans-serif"
    fontSize: "34px"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Source Sans 3, sans-serif"
    fontSize: "25px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Source Sans 3, sans-serif"
    fontSize: "14px"
    lineHeight: 1.5
  card-name:
    fontFamily: "Source Sans 3, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.01em"
  rating:
    fontFamily: "Source Sans 3, sans-serif"
    fontSize: "30px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.04em"
  recruitment-wordmark:
    fontFamily: "Newsreader, serif"
    fontSize: "3rem"
    lineHeight: 1
    letterSpacing: "-0.03em"
rounded:
  field: "4px"
  control: "5px"
  panel: "6px"
  pitch: "8px"
  mobile-drawer: "14px 14px 0 0"
spacing:
  tight: "8px"
  control: "12px"
  inset: "20px"
  drawer: "26px"
  desktop-gutter: "36px"
components:
  button-primary:
    backgroundColor: "{colors.ss-crimson}"
    textColor: "#fff2e7"
    rounded: "{rounded.control}"
    padding: "10px 15px"
  button-primary-hover:
    backgroundColor: "{colors.ss-crimson-hover}"
  button-secondary:
    backgroundColor: "#20282b"
    textColor: "{colors.ss-text}"
    rounded: "{rounded.control}"
    padding: "9px 12px"
  input:
    backgroundColor: "#131d19"
    textColor: "{colors.ss-text}"
    rounded: "{rounded.field}"
    padding: "8px 12px"
  player-card:
    backgroundColor: "linear-gradient(145deg,#303a37,#151f1c 68%)"
    rounded: "7px 7px 14px 14px"
    height: "118px"
    width: "132px"
  bench-card:
    backgroundColor: "#202c25"
    rounded: "{rounded.field}"
    padding: "8px"
  recruitment-primary:
    backgroundColor: "{colors.recruitment-green}"
    textColor: "{colors.recruitment-paper}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
  ability-role-select:
    backgroundColor: "#16241e"
    textColor: "#ecf0eb"
    rounded: "{rounded.field}"
    padding: "8px"
    height: "44px"
  ability-evidence-panel:
    backgroundColor: "#112019"
    padding: "16px"
---

# Design System: Scout

## Current Squad Studio revision — 8 October 2026

The [stadium design record](docs/squad-stadium-design.md) supersedes the old flat-turf squad composition. The user's supplied football-game reference governs this route: locally generated stadium backdrop, dark lime position banners, brighter chemistry connections and an upper-left keeper card dock. Their subsequent refinement removes decorative leaves and makes the sculpted, beveled card layout shared across Squad, Bench and Players. Rating-tier metallic finishes, layered shadows, inset name ribbons and a faint OVR-dependent radial glow create depth. Container-relative typography keeps uncapped ratings and six ability values within the frame. Outfield presentation coordinates preserve logical server slots. Desktop fits the eleven within the viewport; mobile uses a scrollable formation canvas. Scoring/evidence rules remain unchanged. The earlier descriptions below remain applicable to unchanged analysis/recruitment surfaces; they are historical for the old squad pitch and old cards.

## Previous shared card revision — 7 October 2026

The [card design and browser annotation record](docs/player-card-design.md) is
the current contract for shared player cards and the squad header/pitch. It
supersedes earlier collectible-card captions, Rating settings, persistent
three-action menus and upper-capped rating descriptions below. Ratings retain
a floor of 1 and no upper cap; chemistry remains illustrative.

Five raw-OVR material bands use graphite, bronze, silver, gold and amethyst.
Sourced flags and crests sit below position; unavailable identity assets use
explicit placeholders. All eleven pitch cards fit the reviewed desktop
viewport. Card clicks open details; hover/focus shows Sub and Explore. Feature
panels and calculation/source disclosures are compact, with full evidence
available on demand and in exports.

Finish review: accepted for the requested desktop revision after one visual
inspection, a batched viewport-fit correction and final confirmation. Production
build and five focused frontend checks passed. Mobile visual verification is
still outstanding because the browser viewport override did not take effect.

## Overview

**Creative North Star: "Training and selection studio"**

Squad Studio is Scout's landing surface at `/`. Its world is a graphite football-management studio: a full-width deep-turf pitch carries eleven authored shirt cards, with crimson identity details, champagne ratings and silver lettering. The pitch owns attention; bench management and evidence inspection appear when requested. Striker analysis extends this world with a recessed six-axis radar, role-aware density ridges and inline feature evidence. This code-led system is extracted from `frontend/src/SquadStudio.tsx`, `frontend/src/squad.css`, `frontend/src/AbilityView.tsx` and `frontend/src/ability.css`, using the approved direction in `docs/squad-studio-design.md` and `Rating System/ui_ability_visualization_rules.md`. The implemented code determines which optional visual effects actually ship.

The technical scouting dossier remains at `/scout`. Its editable brief, ruled candidate ledger and expandable evidence pane retain warm off-white paper, navy ink, forest-green selection and ochre for unverified evidence. Both surfaces share legible Source Sans 3, tabular figures, explicit uncertainty and disciplined alignment, while retaining their own material language.

**Key Characteristics:**

- Direct lineup operations on a full-width SVG pitch.
- Authored SVG shirts and initials; no shipping raster assets.
- Sourced Liverpool 2026/27 identities, snapshot 2026-10-06; illustrative measurements and familiarity inputs.
- Responsive controls and a scrollable mobile formation canvas.
- Six striker abilities show base-50 magnitude; percentile remains a separate rank statistic.
- One optional comparison outline, raw feature distributions and keyboard-accessible inline evidence.
- Retained recruitment dossier with auditable player evidence.

## Colors

The studio pairs low-light graphite and deep turf with warm numeric emphasis; recruitment retains paper and ink. Frontmatter is the normative token layer; values from each surface stay scoped.

### Primary

- **Studio crimson:** decisive substitution actions and their brighter hover state. Shirt crimson and narrow card trim identify the authored kit.
- **Recruitment forest:** selection, actions and metric emphasis in the dossier.

### Secondary

- **Champagne:** ratings, emphasized evidence and the studio text caret; distinct from silver identity text without implying certainty.
- **Ability champagne:** the player polygon, nodes and distribution markers; a nearby warm rating tone emphasizes role and ability totals.
- **Deep turf:** pitch ground with an SVG light gradient and subtle mowing stripes.

### Tertiary

- **Familiarity green / yellow / red:** link bands with a numeric legend; **unknown silver** is dashed.
- **Recruitment ochre:** unverified evidence and synthetic caution.
- **Restrained ability crimson:** selected radar spoke and temporary distribution scanner.
- **Comparison cyan:** a single dashed outline and matching distribution marker, never a second filled polygon.

### Neutral

- **Graphite background / surface / divider:** shell, menus and ruled separation.
- **Silver / muted silver:** main content and supporting information.
- **Recruitment navy / muted ink / line / paper / warm background:** ledger hierarchy.

**The Evidence Separation Rule.** Sourced identities and manually assigned planning roles remain distinct from illustrative ratings, chemistry and measurements in cards, drawers and exports.

**The Comparison Outline Rule.** Fill the current player only when every ability is calibrated; keep the role-average reference neutral and dashed, and one compatible comparison player cyan and outline-only. Withhold the comparison outline and markers when evidence, season, competition, observation window, reference population or scoring versions differ.

## Typography

**Display Font:** Source Sans 3, sans-serif in Squad Studio; Newsreader, serif for the retained recruitment wordmark.

**Body Font:** Self-hosted Source Sans 3, sans-serif. Comparisons use tabular figures. Source Sans 3 is the authored studio display choice, not a system display fallback.

**Character:** Compact, legible and operational. Silver names sit below larger champagne ratings; descriptive evidence uses quieter text with reading line height.

### Hierarchy

- **Headline:** club title with season smaller and lighter; reduces to (27px) on narrow screens.
- **Title:** analysis drawer heading; reduces to (23px) on narrow screens. Section headings use (18px).
- **Body:** drawer evidence at (14px), line-height (1.5); supporting paragraphs commonly use (13px).
- **Card name / rating:** frontmatter records desktop values. Tablet names use (12px). Final mobile overrides keep names (12px), ratings (27px), position labels (11px) and identity/demo text (9px).
- **Operational labels:** uppercase catalogue and coverage labels vary by context; they are not a decorative headline tier.
- **Ability analysis:** the role total leads at (56px), falling to (44px) below the analysis breakpoint. Selected ability totals use (44px); feature titles and raw values use (17px) and (23px). Supporting evidence uses (12–14px) text with tabular numbers. These values support the analysis hierarchy rather than a new global display face.

**The Stable Card Hierarchy Rule.** Keep rating and assigned position above the shirt, with surname and explicit demo evidence beneath. Preserve mobile legibility through scrolling rather than card compression.

## Layout

Squad Studio has centered content up to (1800px), side gutters (36px), a compact header (66px), club/catalogue row, wrapping toolbar and lineup summary. The pitch spans the available width, with eleven positioned cards above familiarity links. Stage height is `clamp(740px, 54vw, 780px)` with (740px) minimum.

At (1100px) and below, gutters become (22px), cards (116px) wide and the bench grid changes from three columns to two. At (600px) and below, gutters become (12px), header (54px), controls and summaries wrap, and the pitch is (690px) tall in a keyboard-focusable horizontal scroll region. Final mobile overrides establish a (640px) minimum canvas and (100px) cards at (118px) high; a visible pan instruction explains access to the formation. Earlier small-card declarations are superseded and are not the design contract. The (380px) breakpoint tightens toolbar spacing without overriding these final card sizes.

The bench is a fixed, nonmodal bottom drawer: desktop inset follows content gutters, bottom offset (12px), maximum height `min(48svh, 440px)`. Mobile sits at the viewport bottom at maximum height (58svh), with one column and rounded top corners. It scrolls independently while pitch operations remain available. Player, link and rating-settings analysis use native modal dialogs: a right drawer up to (560px) wide, becoming full-width below (600px) with a (24px) top offset.

Striker analysis widens the same modal to `min(1180px, 96vw)` and keeps its close header sticky. Two wrapping selectors precede the role summary and explicit measurement notice. The analysis grid uses `minmax(300px, .9fr)` and `minmax(380px, 1.1fr)` columns with a (28px) gap; the radar stays sticky at (12px). At (760px) and below, analysis stacks radar before selected feature evidence, uses a (24px) gap and removes radar stickiness. Selectors retain (44px) minimum height and (200px) minimum width. Inline evidence uses a two-column definition list and full-width range scanner.

Recruitment retains the brief and ranked candidates in its first viewport, with Recruitment, Compare, Squad and Data navigation. Desktop adds an evidence pane on selection; mobile stacks brief, ledger and details. Ruled tables and aligned tabular figures support comparisons. Original grounded alternatives were match analysis notebook, transfer ledger, team selection sheet, broadcast statistics desk, technical scouting dossier, coaching board and Nordic public archive; the technical dossier remains its established direction.

**The Pitch Access Rule.** Preserve mobile legibility with horizontal canvas scrolling, visible instructions and tap/keyboard alternatives; never require pointer dragging to manage the lineup.

## Elevation & Depth

The studio uses tonal layers, subtle gradients and soft shadows to lift cards above turf. Thin markings and links recede beneath players. Bench sits above the pitch; modal analysis carries a dimmed, lightly blurred backdrop. Recruitment retains flatter paper surfaces and ruled separation.

### Shadow Vocabulary

- **Pitch ambient:** `0 20px 50px #0004`.
- **Player rest:** `0 8px 10px #0006, inset 0 0 0 3px #232e28`.
- **Player hover / focus / selected:** `0 12px 16px #0007, 0 0 0 1px #dbc9a755`, with (4px) lift unless reduced motion is requested.
- **Bench:** `0 -15px 60px #0009`.
- **Analysis:** `-20px 0 80px #0005`.
- **Radar plane:** `0 12px 30px #060b0880`, beneath a subtle dark-green radial vignette.

These diffuse shadows express stacked football materials; hard offset shadows are outside this world's depth vocabulary.

## Shapes

Controls have restrained corners, fields tighter corners and panels softer edges. Player cards have unequal top/bottom curvature; narrow crimson trim, shirt silhouettes and numeric hierarchy are the recurring signature. The club mark uses an authored shield silhouette rather than a raster crest.

Pitch and shirts are authored inline SVG. Turf uses perspective field edges, light gradient, low-opacity stripes and fine markings; shirts use a consistent silhouette, seams, sleeve trim and squad number. Goalkeepers use champagne kit. Keep these assets code-native; no generated faces, copied game artwork or unlicensed portraits ship.

Ability geometry is also inline SVG. Its recessed radar plane has (12px) corners; thin concentric hexagons and spokes preserve the magnitude scale. A fully calibrated player polygon has a translucent champagne-to-crimson gradient and a clear warm edge. Density ridges retain their actual supplied shape, a muted baseline, dashed average line and vertical player marker with a small triangle. A thin champagne bracket below the ridge spans the peer mean and player marker, with endpoint ticks; its length represents the raw-value distance. No pointer parallax or heavy connector is implemented.

## Components

### Buttons

Operational and compact. Secondary controls use graphite fill, thin border, (5px) corners and (40px) minimum height. Toolbar actions are transparent at rest; active bench state gains green-gray fill. Primary substitution confirmation is crimson. Studio focus is a champagne outline (2px), offset (4px). Disabled controls inherit lower opacity and disabled cursor.

### Cards / Containers

The player card carries identity and assigned-role rating. Insufficient evidence is a dash; pending authoritative evaluation is dots. Role mismatch has a warning; no hidden penalty or chemistry bonus alters the rating. Hover, focus and selection reveal Details, Sub and Explore. A persistent selected-player bar supplies tap and keyboard actions independently of hover. Drag handles supplement keyboard sensors and explicit position swap.

Bench rows retain shirt, name, role, demo evidence and rating. Without a selected slot, scores use natural-role ratings; selecting a pitch slot previews that assigned position's ratings. Substitution preview exposes score/link changes, coverage and mismatch before confirmation.

### Inputs / Fields

Dark green-black fields, fine green-gray stroke and (4px) corners. Search and role filter narrow the bench. Notes are resizable and browser-local. Studio and dialog carets are champagne, overriding recruitment's forest caret. Keep visible keyboard outlines and descriptive labels; range controls use warm evidence emphasis.

### Navigation

Studio links Squad to `/` and Recruitment to `/scout`; active navigation has a crimson bottom rule. Snapshot metadata hides on narrow screens. Recruitment keeps its original navigation and serif wordmark.

### Evidence and familiarity

DEMO tags accompany cards and summary scores; sourced identity links and limitations stay accessible. The first player identity block prominently distinguishes demonstration ratings and fictional measurements. The ability notice repeats that no live player statistics are active. The observed-evidence branch is supported, but the source pipeline remains unconfigured and no real performance records are activated. Coverage remains separate from rating; unavailable measurements/contributions remain visible. Details distinguishes assigned and natural roles.

Striker rating describes standardized magnitude: `50 + 15 × z`, clipped to (1–99), with unclipped latent z retained for ordering. Reliability-shrunk feature values are standardized; ability composites and role composites are each standardized again against the applicable cohort. Percentile and cohort rank remain supporting statistics and do not determine radar geometry. Other positions retain visibly provisional standardized raw-metric composites with the same base-50 display; their rigorous ability definitions have not been supplied. The legacy role multiplier applies only to those provisional positions and does not alter striker weights.

Chemistry is explicitly a familiarity proxy. Lines show green (6.67–10), yellow (3.34–6.66), red (0–3.33) or dashed unknown. Hover/focus reveals a value; activation opens evidence. Other links dim on player selection. All familiarity inputs are illustrative, including nationality, language, age, overlap and minutes; they make no claim about real people or tactical compatibility.

### Drawers and state

Bench is a nonmodal section. Analysis drawers use native `showModal()`, autofocus the close button and support Escape and backdrop dismissal. Detailed player, familiarity and provenance information lives here rather than in a permanent sidebar. Keep loading, retry, evaluation failures, pending results and recoverable storage explicit. Recruitment selection still opens its nonmodal evidence pane with role metrics, posterior ranges, evidence labels and replacement differences; changed weights mark results outdated until rerun and comparison remains capped at four players.

### Striker ability radar and feature evidence

Six summary abilities are Finishing, Box Threat, Link-Up / Creation, Carrying / 1v1, Physicality and Defensive Activity. The radar shows rating rings at (20, 35, 50, 65, 80, 95), with a brighter dashed average ring at (50). Select an axis by pointer, Enter or Space; arrow keys move focus and selection between axes. Axis labels, SVG titles and accessible names retain rating, percentile and SD context. Selecting an ability updates every feature in its detail list; hovering a feature dims unrelated radar labels to half opacity while the selected spoke remains emphasized.

Unavailable ability ratings retain their selectable labels and a dash, with no player node at a substituted average. If any player ability is unavailable, the complete player polygon is withheld and an insufficient-evidence notice explains why; the dashed (50) ring remains a reference, never a replacement score. A comparison polygon is likewise withheld unless all its abilities are calibrated.

Evaluation-role selection changes the applicable scores, cohort, peer averages and distributions together. One optional striker comparison adds a cyan dashed radar outline and corresponding distribution markers only when both profiles share evidence kind, season, competition, observed-through boundary, reference population and feature, weighting and normalization versions. Incompatible profiles display a cohort warning and contribute no comparison geometry or readout. The role summary keeps primary role and versatility separate from position rating. Comparison loading and failure remain visible. Complete ability evidence can be exported from the scoring/cohort disclosure.

Feature rows expose raw value and unit, peer average, performance percentile, directional SD gap, weight and direction. Raw x-values always increase left to right, including lower-is-better metrics; the direction label explains performance meaning. When player value and peer mean both exist, the below-ridge bracket shows their raw distance, while the footer and accessible description show the signed raw gap and directional SD separately. Pointer movement scans local density and approximate raw percentile while the player marker stays visible. The explicit Inspect evidence button expands raw gaps, cohort size and comparison gaps inline; its labelled range control and polite readout provide touch and keyboard access to the same scanner. A range or keyboard selection persists when the pointer leaves the feature; pointer scanning returns to a transient state. Missing measurements display unavailable text and are excluded rather than silently becoming zero. An absent density withholds the entire distribution chart and its markers, disables the range scanner, and explains that no calibrated reference is available.

**The Magnitude and Rank Rule.** Use rating for radar distance and SD for magnitude gaps; show percentile separately as rank. Preserve natural raw-value direction in density charts.

**The Inline Evidence Rule.** Keep each feature's measurements and gaps accessible through its explicit evidence button and labelled range scanner; preserve range and keyboard selections when the pointer leaves. Hover is supplementary.

**The Calibrated Geometry Rule.** Missing scores and distributions remain visibly unavailable. Never draw a player polygon, node, distribution marker or active scanner using a substituted average or invented reference.

### Motion

Formation positions transition (350ms) with `cubic-bezier(.2,.7,.25,1)`. Card/toggle state changes use (120ms); bench and analysis entry (200ms) ease-out; drag drop (220ms) ease-out. Motion clarifies reassignment or entry. Reduced motion removes transitions/animations, disables card lift and drop animation, and uses automatic scrolling.

Ability polygons, displayed axis ratings and density markers interpolate through `requestAnimationFrame` over (400ms) with cubic ease-out. Axis opacity changes use (180ms); feature-detail entry uses (260ms) ease-out and a small (5px) rise. Reduced motion assigns target geometry immediately and removes ability transitions and entry animation. The rAF interpolation is the implemented geometry motion; the incidental CSS `points` transition is not a reusable animation mechanism.

## Do's and Don'ts

### Do:

- **Do** keep the two route palettes and materials scoped to their surfaces.
- **Do** preserve eleven identities across formations and expose explicit slot operations.
- **Do** distinguish sourced identities, manual roles, illustrative measurements and evidence coverage.
- **Do** keep the mobile canvas at least 640px wide, cards 100px wide and names 12px, with horizontal access explained.
- **Do** retain keyboard focus, reduced motion, loading, empty, error and storage recovery in the same hierarchy.
- **Do** retain recruitment's disciplined ledger alignment, explicit uncertainty and synthetic labels in surfaces and exports.
- **Do** preserve the distinct 50 average ring and keep role rating, percentile, latent SD and coverage separately labelled.
- **Do** retain natural raw-value axes, direction labels and inline keyboard/touch scanning alongside pointer scanning.
- **Do** show the raw average-to-player distance and signed gap separately from directional SD, and preserve keyboard scanner selections after pointer departure.
- **Do** keep observed-release capability distinct from activation; the current player measurements remain demonstration data.

### Don't:

- **Don't** treat chemistry as tactical compatibility, a match forecast or a hidden rating bonus.
- **Don't** replace unknown evidence with zero or present illustrative performance as measured Liverpool data.
- **Don't** add generated faces, copied game artwork, unlicensed portraits or raster replacements for authored shirts and pitch.
- **Don't** introduce a permanent analytics sidebar into Squad Studio's pitch-centered operation.
- **Don't** make decorative kickers a reusable headline tier; the unused eyebrow rule is not canonized.
- **Don't** substitute dance notation, ticket routing, a media feed or split-flap uncertainty animation for recruitment's dossier.
- **Don't** use percentile as radar radius, reverse raw density axes for negative metrics or fill the comparison polygon.
- **Don't** substitute an average for an unavailable ability, draw a distribution without reference evidence or compare incompatible scoring cohorts.
- **Don't** present other positions as having the supplied rigorous striker ability model.

The incumbent squad finish evidence remains `.impeccable/review/desktop.png`, `mobile.png`, `user-700.png`, `desktop-bench.png`, `mobile-bench.png`, `desktop-details.png`, `mobile-details.png`. The earlier ability finish review returned **ship limited to three material fixes, all resolved** against nine ability captures. That scoped review history remains distinct from the current evidence update.

The fresh finish review returned **ship for the changed striker ability surface**, with no material fixes required within `frontend/src/AbilityView.tsx` and `frontend/src/ability.css`. Its five contract sections were reviewed against all twelve current `.impeccable/review/{desktop,mobile,user-700}-abilities{,-radar,-distribution,-unrated}.png` captures, at desktop (1440 × 1000), mobile (390 × 844) and user viewport (700 × 704). The unrated captures use an intercepted contract-test fixture and do not represent actual player data. The detector returned `[]` once; four focused AbilityView E2E journeys passed across desktop and mobile after the scanner fix. The TypeScript/Vite production build and all five Vitest tests passed. This scoped disposition does not certify real-data coverage, remote refresh scheduling or every feature. Source code remains authority over intentions and this descriptive record. Sourced identities and fictional measurements remain unchanged; no roster or source changes belong to this design refresh.

Not canonized: the unused decorative eyebrow rule and incidental CSS `points` transition are not reusable system guidance; optional parallax, polygon glow and connector effects from the visualization reference are not implemented.


### Smooth shared player cards — 8 October 2026
The latest user reference governs all player faces: arched crest crown, curved shoulders, tapered point, no bordered rim. Light graphite, bronze, silver and gold materials carry dark text; elite uses luminous gold. Printed crosses and flowing foil ribbons provide surface depth. The integrated uppercase name and two centered ability columns replace the beveled frame and inset panels. Shared component: PlayerCardFace; all data, score tiers and interactions are preserved.
