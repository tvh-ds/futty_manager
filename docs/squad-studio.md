> Current scoring update (6 October 2026): the original percentile-weighted rating described below is superseded by [striker scoring](striker-scoring.md). ST now uses six abilities and base-50 magnitude scores with separate percentile rank. Other positions have provisional magnitude scoring. The source/chemistry/management sections remain applicable. See [source feasibility](striker-data-feasibility.md) for the unactivated real-data gate.

# Squad Studio — local implementation

Implemented on 6 October 2026. `/` is the dashboard; `/scout` retains recruitment. This feature does not activate a candidate data release.

## Sources and evidence

The curated snapshot `liverpool-men-2026-27-20261006-v1` contains 31 men's first-team-listed identities: 5 goalkeepers, 10 defenders, 7 midfielders and 9 forwards. The separate academy/U21 roster is excluded; first-team-listed young players remain included. Names, jersey numbers, country tags and broad categories follow the men's profile pages, including their Other Players lists. Fine-grained roles/sides are **manual planning metadata**. Country tags do not establish complete citizenship records. Squad membership here is not a matchday availability, loan, injury or registration certification.

Primary sources checked for this snapshot:

- [Registered Premier League squad, September 2026](https://www.liverpoolfc.com/news/liverpool-submit-premier-league-squad-list-2026-27?amp=1).
- [Goalkeepers: Alisson profile and men's Other Players section](https://www.liverpoolfc.com/teams/mens-team/alisson-becker).
- [Defenders: Ronald Araujo profile and men's Other Players section](https://www.liverpoolfc.com/teams/mens-team/ronald-araujo).
- [Midfielders: Alexis Mac Allister profile and men's Other Players section](https://www.liverpoolfc.com/teams/mens-team/alexis-mac-allister).
- [Forwards: Victor Munoz profile and men's Other Players section](https://www.liverpoolfc.com/teams/mens-team/victor-munoz).

The registered list alone excludes eligible under-21 players and therefore is not used as the entire first-team roster. These official public identity facts are transcribed in `src/scout/squads.py`. No official images are redistributed. Authored SVG shirts/initials substitute for portraits; the crest-shaped LFC marker is an original text/shield treatment. No game artwork or generated faces ship.

All skill values and chemistry components are seeded demonstration fixtures, never actual player measurements. Chemistry demographic inputs use abstract demo tokens; even the sourced country tags are not used to make factual chemistry claims. Observation windows, versions and limitations are included in API responses and exports. There is no live source refresh, and upstream roster changes require a new reviewed snapshot/version.

## Ratings and chemistry

The reference population uses NumPy seed 810 (outfield) / 811 (GK), 420 fictional outfield peers and 100 fictional goalkeepers per league. Feature keys derive from the existing eight-role registry, versioned as `demo-skills-v1`. All outfield positions share one comparison population; goalkeepers have their own. Midrank percentile: `100 × (lower + 0.5 × tied) / valid peers`, inverted for lower-is-better features.

Assigned-role ratings average available percentiles, weighting emphasized skills by the configured multiplier (default 1.5) and others by 1.0. No second normalization, exposure penalty or chemistry bonus is added. Scores require 70% defined-feature coverage and 50% role-feature coverage. The XI score requires eleven available position ratings. More rigorous feature families, observation reliability and league adjustments await the user's specification and evaluation.

Familiarity equally averages available nationality, overlapping tenure, shared language, age-proximity and concurrent teammate-minute components. At least three must be known; otherwise the link is grey/dashed. Scores round half-up to two decimals before red ≤3.33 / yellow ≤6.66 / green ≥6.67. Unknown absence stays unknown; language is never inferred from nationality. Pure interval helpers merge duplicate same-club tenure overlaps and concurrent playing intervals. In this release they are tested utilities; actual career/lineup intervals have not been ingested. The visible graph follows formation rows and nearest neighbours, with GK connected to two central defenders. Team chemistry averages scored visible links, accompanied by coverage.

## Contracts and operation

Endpoints:

| Method | Path | Result |
|---|---|---|
| GET | `/squads` | Supported snapshot catalogue |
| GET | `/squads/liverpool-men` | Curated roster, demo skills, defaults and provenance |
| GET | `/formations` | Five stable slot sets, role mappings and topology |
| POST | `/squads/liverpool-men/evaluate` | Authoritative rating/chemistry evaluation |
| POST | `/squads/liverpool-men/formation` | Deterministic same-player reassignment |
| GET | `/squads/liverpool-men/position-ratings?role=ST&multiplier=1.5` | Authoritative substitution ratings for compatible population |

Strict Pydantic inputs reject unknown fields, stale snapshots, unsupported formations, unknown identities, duplicates and goalkeeper/outfield exchanges. Clients supply assignments/settings, never trusted scores. Rating queries identify their exact lineup; stale responses cannot become current. Multiplier requests debounce by 200 ms. Position-rating queries are keyed by role and multiplier.

Formation reassignment uses linear-sum assignment with ordered costs for supported roles, manually planned sides, previous coordinates and stable identifiers. The algorithm does not choose substitutes or impose an arbitrary mismatch rating penalty. Reserves are the unassigned squad pool, while bench substitutions return the outgoing player to the incoming bench location. A reserve substitution returns the outgoing player to the reserve pool; reserve locations are not numbered.

Browser imports are bounded to 1 MB, notes to 5,000 characters/player, and accepted inputs are copied from the documented schema. Unknown exported scores are discarded. The server validates imported assignments before adoption. Invalid storage is not overwritten automatically; export the original before explicit recovery. If browser persistence fails, keep working and export before leaving. Undo is limited to the most recent 30 planning states in the current session; it retains scouting notes. Reset restores the default XI/settings and retains notes.

The native modal details/settings/pair drawers trap focus and support Escape. The bench is a nonmodal bottom drawer to allow drag targets on the pitch. Pointer dragging uses `@dnd-kit/react` 0.5.0; keyboard and click/tap alternatives remain available. On small screens, a horizontally scrollable 640px canvas preserves readable player names/positions and formation geometry; the page itself does not overflow. CSS removes spatial transitions under reduced motion. No additional asset-generation service or external LLM is needed.

## Verification and limits

- Python: 69 passed, 1 skipped (Spark); standalone dashboard API and boundary tests included. After the final position-rating assertions, all 13 squad tests passed again.
- Vitest: 5 passed, including malformed/stale imports, uniqueness, substitutions and goalkeeper constraints.
- Playwright: 15 passed, 1 intentionally skipped mobile pointer-only case; mobile tap journeys run separately. After the responsive/bottom-drawer changes, desktop/mobile management/export/import and desktop drag checks passed again. The final review corrections were rebuilt and regression-tested.
- Frontend production build and Ruff passed; route splitting keeps recruitment and dashboard code in separate chunks.
- Bounded visual review captured desktop 1440×1000, mobile 390×844 and in-app width 700×704, plus desktop/mobile drawers. No certification of all devices, assistive technologies or cloud cold starts is implied.
- The independent finish reviewer requested readable mobile card text, removal of above-heading decorative labels and visible dark-input carets. The reviewer scored all three resolved after recapture and returned **ship**, scoped to those fixes. The initial detector's callout-border warning was corrected; no second detector run was used.

The main plan's real five-league candidate release, cloud deployment, real position-specific skill model, learned chemistry and current performance feed remain future work. Existing account placeholders are preserved.
