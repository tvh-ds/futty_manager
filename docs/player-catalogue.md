# Source-backed Players and Liverpool cards

`/players` browses imported 2025/26 snapshots. Liverpool 2026/27 remains the only
planning squad. Membership and performance season are separate. Nothing here
claims live statistics.

## Current local snapshot

- Import `evidence-8241da43bbc86529fba9bf4af3e2dce9`: 8,784 source records
  (Opta 3,239; PitchAPI 2,770; Understat 2,775).
- Catalogue `catalogue-6b73d3a9aae774788a053e7ceb5d8d9e`: 4,308 profiles,
  five leagues, 2,757 sourced portrait URLs and 158 calibrated ST overall ratings.
- Liverpool: 26 of 31 identities mapped. Jaros, Davies, Chambers, Koumas and
  Danns lack a matching historical top-five-league profile.
- Ratings now use proportional redistribution only for explicitly zero-filled unrecorded features; recorded zeros retain their weight shares. Earlier strict-cohort releases remain preserved.

Profiles are not a verified count of unique footballers. Unresolved identities
and cross-league transfers can appear separately. Provider team aliases remain
visible. These limitations are disclosed in the interface.

Offline Opta reprocessing added 190 goalkeeper records from its separate
goalkeeper report in already retrieved snapshots; no new requests were made.
Saves, goals conceded and xGOT conceded are retained in source records. They
do not constitute a goalkeeper rating model.

## Mapping and evidence

Opta IDs anchor profiles. Cross-provider matching requires normalized full name,
league, compatible positive minutes and at least two agreeing attack counts.
Goalkeepers instead require name, league, compatible minutes and matching club
metadata. Explicit Liverpool aliases are versioned. Ambiguous records remain
separate. This is algorithmic corroboration, not human-reviewed certification.

For multi-stint Opta players, the highest-minute aggregate is selected
deterministically; transfers are not summed. Available features use
Opta → PitchAPI → Understat preference with alternatives retained. Every ratio
keeps its provider's numerator, denominator, measurement version and source URL.
Different provider definitions remain a calibration/publication limitation.

Portraits use exact URLs from checksum-verified cached PitchAPI metadata.
The frontend CSP permits only its image CDN. Failed/missing portraits show
an authored shirt and initials. Cards use an original visual design. Cached team
crests and available sourced country labels populate the shared cards;
missing identities use explicit placeholders. See the [card design and
annotation record](player-card-design.md).

## Scoring with zero-filled feature redistribution

The six displayed abilities are the supplied ST model: Finishing, Box Threat,
Link-Up / Creation, Carrying / 1v1, Physicality and Defensive Activity.
Other positions have unavailable fields until their registries are defined.

Calibration pools all five leagues rather than grouping by league. There is no
league-strength adjustment. The player's own league remains identity metadata
and a catalogue filter. Of 360 ST profiles, 158 have full ratings, 172 are below
900 minutes and 30 have remaining evidence or compatible-cohort gaps.

Each scored ability requires at least one recorded direction-bearing feature, 900 player minutes
and at least 30 eligible ST peers pooled across the top five leagues with the same effective weights and compatible provider/measurement
signatures. Explicit `unrecorded_zero` features have weight 0 and their original weight
is distributed proportionally among remaining features. Genuine recorded zeros keep their shares.
Direction-zero offsides stay context only. Versioned provisional
shrinkage defaults are retained. Weighted standardized composites display as
`max(1, 50 + 15 × z)`, with no upper cap. Details retain decimals and peer evidence.

OVR requires all six abilities and a compatible common peer cohort. An ability
with no recorded scoring features prevents OVR. There is no hidden missing-data
penalty or invented score. Zero-attempt ratios show N/A, count as
supported evidence and remain non-numeric. The legacy role multiplier is
inactive in observed mode. Chemistry remains demonstration data.

## UI and serving

`/players` supports name, league, team, position, OVR bounds, rating availability,
sorting and pagination. Every card has a portrait/fallback and six ability fields;
its drawer exposes all 36 selected feature slots and source alternatives.
Liverpool pitch and bench cards reuse the component and mapped attributes.
ST detail drawers on both pages share `AbilityView`: the six-axis radar selects
an ability's raw-feature distributions, peer averages, evidence inspector and
keyboard-accessible scanner. Catalogue comparisons use other ST cards on the
current results page and require compatible scoring cohorts. All raw source
attributes remain available in a collapsed section below the analysis.
Unmapped roster members never fall back to fictional measurements.
The existing fictional `/scout` workflow remains separate.

APIs: `GET /catalogue`, `GET /catalogue/players`,
`GET /catalogue/players/{id}`, `GET /catalogue/players/{id}/abilities`.
SQL filters are parameterized and pagination bounded. Alembic revision `0003`
adds versioned catalogue tables. Completed builds activate transactionally,
preserving earlier imports and the active fictional candidate release.

Endpoints require `SCOUT_SERVE_PRIVATE_EVIDENCE=true`; default deployment keeps
them disabled. Understat publication rights remain unverified. Local scoring
does not establish public release approval or universal 90% feature coverage.

## Reproduce from cached data

```powershell
.venv/Scripts/scout.exe reprocess-opta data/opta-analyst/season-2025-20261006 data/opta-analyst/season-2025-with-gk-20261006
.venv/Scripts/scout.exe import-real-data data/pitchapi/live-probe-2025 data/opta-analyst/season-2025-with-gk-20261006 data/striker-source-probes/understat-recheck-20261006 --output data/real-data/import-with-gk-report.json
.venv/Scripts/scout.exe build-player-catalogue --output data/real-data/catalogue-uncapped-report.json
```

Focused tests cover corroboration, zero-filled redistribution, recorded zeros, private API boundaries,
filters, GK inventory, unmapped handling and portrait failures. Existing lineup
state and recruitment contracts retain their regression checks.
