# Striker implementation acceptance audit — 6 October 2026

The four documents in `Rating System/` remain authoritative. This audit describes implemented behavior and actual evidence; it does not declare the live-data goal complete. Archetype weights and shrinkage constants use the user's approved, documented provisional defaults. Broad ST weights retain the supplied specification.

| Requirement | Implemented and verified locally | Outstanding acceptance evidence |
|---|---|---|
| Striker feature registry | 37 unique metrics, 38 weighted slots and six abilities; raw totals/denominators, directions, units, derivation and missing rows are retained. Invalid/coerced/overflowing records are rejected or quarantined. | Actual permitted current measurements for the full registry, exact provider semantics, reviewed real identity/stint mappings and public-display rights. No real numeric records are activated. |
| Rating method | Reliability shrinkage, conventional feature z scores, ability re-standardization and independently calibrated role composites. Display magnitude, midrank percentile, rank and latent gaps are separate. Tied and missing populations do not fabricate ratings. Arithmetic/cohort/zero-variance failures are tested. | Empirical calibration of provisional shrinkage/archetype parameters and adequacy of real same-league/window peer populations. |
| Multi-role rules | Eligible roles evaluated independently, primary chosen by latent score, jointly calibrated hybrid and separate versatility. Assigned ST pitch rating uses the broad position model. Unsupported calibration is explicitly unavailable. | Reviewed real eligibility and real independent cohorts. Other positions retain the existing provisional registry; rigorous additional position models await their specifications. |
| Monthly pipeline | Quota-aware collection adapter, guarded canonical import, immutable bronze/silver/gold/profile manifests, checksums, freshness gate, redacted quarantine/status, failed-refresh preservation and atomic activation are tested. Monthly GitHub workflow is defined. | Enabled permitted source, adequate daily quota/backfill, actual remote schedule, actual current rated release and observed freshness/recovery runs. A workflow file is not run evidence. |
| Durable runner state | Private Azure archive restore/save implementation, content and release integrity, bounded archives, safe paths, empty-directory restoration and conditional ETag protection. Local recovery and mocked SDK failure/concurrency tests pass. No raw GitHub caches/artifacts. | Actual configured OIDC identity/private container, Azure restore/save roundtrip, storage cost/lifecycle review and remote recovery drill. Cloud accounts remain placeholders. |
| Ability interface | Six-axis rating radar, raw-direction densities, explicit average ring, visible raw gap bracket, signed raw/SD gaps, role switching, compatible one-player comparisons, raw evidence and keyboard/tap scanner. Missing ratings, distributions and cross-cohort overlays are withheld. Responsive/reduced-motion behavior retains the existing design. | Real measured profiles and real cohort inspection. Optional benchmark selector, top-ten view and decorative parallax/glow are not implemented. |
| Existing product | Recruitment ranking remains separate; squad management, evidence labels and usable demo exploration are preserved. API and frontend both return HTTP200 locally. | Main-plan current candidate release, PostgreSQL/Databricks/cloud execution and deployed portfolio evidence remain open in the progress ledger. |

Verification at this audit:

- Full Python regression: **103 passed, 1 Spark skip**; Ruff passed. An upstream Starlette/httpx deprecation warning remains.
- Frontend production TypeScript/Vite build and **5 Vitest tests** passed.
- Fresh focused AbilityView Playwright run: **4 passed**, desktop and mobile. Earlier whole-suite evidence: 17 passed and one intentional mobile pointer-only skip; that broader run predates this final UI change.
- Fresh visual finish review shipped the changed ability surface without material fixes after twelve viewport captures. Unrated captures use an intercepted contract fixture, not real player measurements.
- Native npm audit reported zero advisories. The locked application/cloud Python profile audit covered 88 dependencies and reported zero advisories. These results apply to the checked dependency versions and advisory databases.
- Monthly YAML parsed with ten steps. Live source remains disabled, publication approval remains false and no `data/strikers/active.json` exists. No Azure, GitHub Actions or Databricks execution occurred.

The previous run was marked blocked after three turns with missing live-data/remote prerequisites. A resumed audit found additional local publication gaps: a single-league release could activate, and the provider adapter used retrieval time as its sporting cutoff. These are now corrected; the preceding test counts describe the earlier review, not the resumed work below. Completing real-data acceptance still requires external source/account availability; fixtures or mock cloud tests cannot supply it. Keep secrets in environment variables or protected secret stores.

## Resumed publication audit

- Releases now require30 calibrated ST players per league, all five leagues, one common observation cutoff/season and the configured target season. Ongoing-season observation freshness and retrieval freshness are checked independently. Completed historical seasons must retain their actual season cutoff.
- Source configuration uses strict booleans/season and an explicit reviewed sporting cutoff for live collection. Provider identities need reviewed team mappings. Invalid configuration/imports report failure without disclosing rejected input or replacing the active pointer.
- Immutable replay verifies an exact bounded artifact set, checksums, scoring/code versions and profile provenance before parsing/activation. Code hashes now include contract/role definitions. Derived measurements and cohort membership are computed once per refresh rather than rebuilt for each player.
- A150-player, five-league fixture verified activation, replay, restoration and failed-refresh preservation. A single-league fixture verified refusal. Freshness, mismatched season/window, team/cutoff mapping and invalid input tests pass.
- Latest full Python result: **116 passed,1 Spark skip**, with the same upstream deprecation warning. Focused ability/private-state suite:47 passed. Ruff passed. The default CLI refresh ran with zero records and no activation. No frontend changes occurred in this resumed turn.

Actual permitted numeric coverage and remote scheduling are still unverified. The resumed audit is progress toward the original goal, not a completion claim or a new real-data release.

## Reproduction audit

Canonical source ordering, stable peer IDs and registry-ordered role evaluation now preserve exact scores, ranks, hybrids and versatility when rows/metric keys/eligible-role lists are reversed. Input and runtime fingerprints are recorded in manifests, along with one batch calculation timestamp. Non-finite JSON constants are rejected before artifact construction.

The new offline `reproduce-strikers` command recalculates all four artifacts from retained bronze and the recorded epoch, compares every checksum and reproduces the manifest without activation. The150-player five-league fixture matched every file byte-for-byte. Separate CLI tests prove corrupt-source refusal, preservation of existing destinations and unavailable/partial measurement handling. Silver now includes the complete raw schema instead of depending on the first row's available fields, which could previously omit later observations.

The focused ability/private-state/reproduction suite passed52 tests; the full Python suite passed121 tests with1 Spark skip and the existing upstream deprecation warning. Ruff passed. No frontend changes or actual observed-data release were made. Code/runtime drift is explicitly refused rather than called a successful reproduction; cross-platform native numerical portability remains unproven.

Related records: `docs/striker-scoring.md`, `docs/striker-data-feasibility.md`, `docs/deployment.md`, `DESIGN.md` and `continue_strictly_mainplan.md`.

## External acceptance recheck — third resumed turn

Current configuration still has live collection disabled, publication approval false and no reviewed sporting cutoff. No provider key, Azure subscription or Databricks workspace is present in the checked process environment. There is no Git repository/remote configured in this workspace and no observed active release. The last actual default refresh contains0 records and reports no activation. The API/frontend remain available locally.

The first resumed turn corrected publication/freshness/mapping gates; the second implemented deterministic scoring and exact offline release reproduction. Both were concrete progress. This third turn rechecked the authoritative configuration, workflow, specifications and evidence ledger. The same external condition remains: no configured, verified, permitted current numeric dataset covering the registry, and no configured remote execution. No further required independent local work was identified in this bounded audit. Completion remains unproven; the goal is blocked pending that external change, rather than completed around fixtures.

To resume real acceptance, supply a permitted complete canonical dataset or configure a source whose actual responses and publication rights establish the required fields/cohorts. Remote acceptance also needs a configured repository/runner and private cloud identity/storage. Existing source/account placeholders are preserved; no account creation, spending or change to the free-data scope is authorized by this audit. Empirical evaluation of the approved provisional parameters then requires the real data.


## Actual numeric-source progress — 6 October 2026

The previous source blocker has narrowed: the public Understat interface now produced actual validated five-league numeric snapshots, with 2,121 player records for2026/27 and2,775 for2025/26. These are all-position records, not approved ST cohorts. The user selected completed2025/26 performance data; configuration now targets2025, independently of2026/27 squad membership.

A tested, bounded single-player shot adapter reconciles exact league/season fixture membership, shot counts, non-penalty goals and summed npxG before deriving four additional features. Alexander Isak's17 shots/717minutes and Cody Gakpo's87 shots/2,758minutes were checked against league totals. Eleven of37 requested features are numerically verified for these samples. Unknown result/coordinate definitions remain withheld. Both sources remain private, without role inference, rating activation or scheduling.

The remaining26 features require a permitted source/export, followed by reviewed identities, complete same-league eligible cohorts and collection/public-display approval. Full real ratings and a real monthly production run remain incomplete. Detailed evidence and commands are in `docs/striker-data-feasibility.md`. The requested main-plan progress file was not updated.

Verification: full Python suite139 passed,1 Spark skip; dedicated source/shot adapter suite18 passed. Ruff passed. No frontend or cloud deployment changes were made in this source-verification work.
