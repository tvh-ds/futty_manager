# Striker ratings and monthly evidence refresh

Implemented locally on 6 October 2026. This extends Squad Studio; the recruitment recommendation algorithm remains separate.

The authoritative specifications are the four files in `Rating System/`. Where the striker attribute file suggests percentile preprocessing, `rating_ranking_system.md` takes precedence: percentiles never enter the rating calculation.

## Implemented scoring

- 36 unique measurements appear in 37 weighted slots across Finishing, Box Threat, Link-Up / Creation, Carrying / 1v1, Physicality and Defensive Activity. Dispossessed intentionally appears twice.
- User-approved v2 removes attacking-third tackles. Defensive Activity now uses recoveries `7/13` (53.846%), interceptions `3/13` (23.077%) and blocks `3/13` (23.077%). Its broad-ST weight remains 10%; all other within-ability and role weights are unchanged. This proportionally redistributes the removed 35% without inventing a new skill proxy. It does not measure pressing effectiveness.
- Registries are versioned as `striker-features-v2` / `striker-weights-v2`. The prior 37-feature registry and weights remain archived in `config/feature-registries/striker-features-v1.json`; existing source snapshots and release artifacts are not rewritten. The new demo population has a distinct v2 identifier.
- Totals and denominators are retained; per-90 and percentages are recomputed. Percentages use 0–100. Non-penalty goals/shot always requires non-penalty shots; total shots are not substituted. Missing event context does not become estimated open-play xG.
- Reliability shrinkage precedes conventional mean/SD standardization. Abilities and final role composites are standardized again against the same frozen eligible peer population.
- Rating is `50 + 15 × latent z`; only the display is capped at 1–99. A player equal to a completely tied reference yields z=0 and percentile=50. A different value cannot be standardized against that zero-variance reference and is unavailable, rather than assigned an average rating. Empirical midrank percentile, rank and adjacent latent gaps are retained separately.
- Broad ST weights are exactly `.27 / .20 / .17 / .14 / .12 / .10` in the supplied ability order. Six tactical archetypes have separately evaluated, explicitly provisional weights. The user authorized these initial parameters.
- Every eligible role is independently evaluated; the primary role is selected by latent score. Pitch ST cards show the broad position rating, rather than the best tactical archetype or an average of roles. A ST/W player receives different ST and W planning evaluations. Other positions still use provisional existing metrics; their rigorous feature registries have not been supplied.
- Hybrid advanced-forward/false-nine combines latent scores from independently fitted role models, aligns shared peer identities, then re-standardizes against the joint eligible cohort. At least 30 common identities are required. It does not average displayed ratings.
- Versatility is separate: `100 × (.4 breadth + .4 secondary quality + .2 consistency)`. Breadth is the fraction of eligible secondary tactical roles at z≥0; quality is their mean clipped `(z+1)/3`; consistency is mean `max(0,1−abs(primary_z−secondary_z)/3)`. This provisional descriptive index needs at least two tactical roles; it does not reduce the primary rating.
- Offsides remain visible and keep the supplied `.10` slot, but have zero directional contribution until attacking-run context is defined. They are not treated as a strong negative. Re-standardization preserves the magnitude scale. This decision is explicit in profile limitations.
- An ability requires all of its nonzero-direction weighted features. An incomplete ability makes the aggregate role unavailable. This stricter rule avoids substituting incomparable feature subsets for the new rigorous model; the earlier dashboard 70%/50% rule applies only to other provisional positions.

Initial shrinkage k: minutes450; shots/non-penalty shots30; pass attempts200; take-ons30; overall duels50; aerial duels30. These are versioned starting priors, not fitted or validated optimal values. No hidden league-strength or demographic bonus is applied.

Provisional archetype ability weights, in the order above:

| Role | Finishing | Box | Link-up | Carrying | Physical | Defensive |
|---|---:|---:|---:|---:|---:|---:|
| Poacher | .36 | .30 | .10 | .08 | .10 | .06 |
| Advanced forward | .30 | .24 | .12 | .18 | .10 | .06 |
| Target forward | .25 | .25 | .14 | .06 | .24 | .06 |
| Complete forward | .23 | .19 | .19 | .16 | .14 | .09 |
| False nine | .18 | .12 | .30 | .22 | .08 | .10 |
| Pressing forward | .22 | .17 | .14 | .14 | .13 | .20 |

## Interactive ability view

Open Alexander Isak or another manually listed striker's Details. Six rating axes sit beside actual feature-density shapes on desktop, and above them on mobile. Select an ability by click/tap or keyboard arrows and Enter. The 50 average ring is dashed and distinct; feature x axes retain natural raw direction even for lower-is-better measurements.

Role selection changes the rating, reference cohort, averages, percentile, SD gaps and distributions. One optional comparison uses an outline radar polygon and dashed cyan markers. Feature evidence buttons expose raw value, mean, raw gap, SD, percentile, N and comparison gaps, with a keyboard/tap range scanner. Marker and radar geometry interpolate for 400ms; reduced motion snaps immediately. Exports retain full latent scores and provenance.

Each calibrated feature shows a visible average-to-player bracket and signed raw gap, separately from its directional SD gap. Unavailable abilities have no player marker; a partial radar has no complete player polygon. Without a calibrated reference, no density or scanner is drawn. Comparison overlays require matching evidence, season, competition, observation window, reference population and scoring versions. Keyboard/tap scanner choices persist when the pointer leaves the chart. These behaviors are covered by desktop/mobile contract-fixture journeys; fixtures are not observations about a real player.

Numeric data are currently **demonstration measurements**. The fixture uses 420 fictional broad-striker peers (84 per league), with smaller deterministic archetype subsets, seed191026. All peers have illustrative exposure≥900 minutes. This is a role-specific replacement for the earlier all-outfield percentile scoring fixture, not an assertion of real Liverpool statistics or tactical eligibility.

API: `GET /squads/liverpool-men/players/{player_id}/abilities`. Non-striker planning identities receive422; unknown identities404. Backend evaluation remains authoritative. An activated observed profile uses a separate checksummed release path; corruption yields an error, not a demo fallback for that record.

## Monthly pipeline and publication gate

Run `uv run scout refresh-strikers`. Default `config/striker-source.json` is disabled and keys remain placeholders. The command writes `data/strikers/refresh-status.json` even when no live source is configured. The GitHub monthly workflow is defined at `.github/workflows/striker-monthly.yml`; it has not executed on a remote repository or deployed a data release here.

For a permitted canonical input: `uv run scout refresh-strikers --import-path path/to/records.json`. Input is limited to20MB/10,000 records and validated by `StrikerRecord`. Every available raw value needs a source citation, timezone-aware availability/retrieval dates, reviewed provider identity, detailed role eligibility, same-season/league membership and publication approval. Invalid observations are quarantined. Duplicate identities require reviewed stint consolidation.

Artifacts: immutable bronze input JSON, silver raw-total Parquet, gold derived-feature Parquet, profile evaluations, manifest with checksums/code hash, then an atomic active pointer. Replaying identical input preserves artifacts; it can activate after rights approval if all gates pass. An incomplete, quarantined, stale-retrieval (>45 days) or incompatible release preserves the previous pointer. Observed rating cohorts require≥30 complete, same-league, same-season, same-observation-window peers with≥900 minutes. No arbitrary cross-league multiplier is used. Serving verifies the profile checksum and caches the immutable parsed artifact.

Publication also requires at least30 calibrated broad-ST players in **each** of the five leagues, one common season/observation cutoff and agreement with the configured target season. The report records per-league counts and explicit publication errors. For the ongoing season, the sporting observation cutoff must be no older than45 days independently of retrieval freshness. A newly downloaded old dataset cannot pass that gate. Deliberately imported completed historical seasons use their actual season cutoff, not today's retrieval date. Observation cutoffs must fall within the broad declared-season sanity window, July1 of the start year through July31 of the next year; this is a validation bound, not an inferred league schedule.

The exact four artifact names, checksums, scoring/code versions, identity set and observed-profile provenance are verified before replay activation. Source configuration is typed: enabled/publication flags cannot be strings or integers. Malformed configuration/imports produce a redacted failure status and nonzero CLI exit without replacing the previous pointer. Shot subsets and open-play xG cannot exceed their corresponding parent totals.

Source record/object order does not create a new release. Canonical bronze retains every original value/record, including rejected records, in a stable order; quarantine indices refer to that retained order. Fitted peers use stable player-ID order and eligible roles use registry order, so pagination or role-list order cannot change arithmetic or break role ties differently. Silver uses the entire raw registry, retaining measurements from later rows even when the first record is partial. Missing values remain null.

Manifests record the canonical input SHA256, Python/NumPy/SciPy/Pydantic/PyArrow versions and one calculation timestamp for the batch. Runtime-version changes produce a different release ID. Reusing an existing release retains its recorded timestamp and artifacts.

Offline reproduction: `uv run scout reproduce-strikers data/strikers/releases/RELEASE_ID artifacts/striker-reproduction/RELEASE_ID`. The destination must be new. This verifies source files/code/runtime/provenance, recomputes bronze/silver/gold/profiles using the recorded calculation timestamp, compares every checksum and copies the manifest only after all four artifacts match. It never activates a release or accesses a provider/cloud account. Corrupt source files and existing destinations are refused. A mismatch retains a diagnostic in the new reproduction directory and cannot change the published pointer. Exact bitwise reproduction is verified in the tested local runtime; portability across differing native numerical builds is not claimed.

Unrated profile artifacts retain all six abilities, every available derived measurement and every missing row. Below900 minutes or without30 complete eligible peers, aggregate ratings and reference statistics remain null; no fictional distribution or cohort is supplied. Such artifacts are inspectable locally but cannot activate as a rated release. Import validation rejects duplicate roles, coerced approval flags, boolean measurements and non-finite derived values or denominators.

Previous-release retention is verified on persistent local storage and through a bounded local archive recovery drill. The monthly workflow now restores/saves runner history from an **existing private Azure `backups` container** via OIDC and the Azure CLI credential. Raw snapshots and release artifacts are excluded from GitHub caches/artifacts; only redacted refresh status is uploaded there. Failed collection retains quota checkpoints and the previous active pointer. Archive path/checksum/size validation precedes restoration into an empty directory. Immutable content-addressed snapshots are uploaded before a conditional ETag pointer update; stale writers cannot replace newer state.

No remote execution is claimed. Configure the protected `batch` environment's `CLOUD_ENABLED`, `AZURE_STORAGE_ACCOUNT`, existing Azure identity/subscription/tenant variables and recent `CREDIT_RECORD` only when accounts are ready. The existing credit guard runs before Azure authentication; no resources or billing settings are created. The batch identity needs appropriately scoped Blob Data Contributor access to `backups`. Set `STRIKER_STATE_BOOTSTRAP=true` only for an intentionally empty first run, then remove it; a missing established pointer otherwise fails restoration. A real restore/save/recovery drill, storage lifecycle/cost review and remote monthly run are still required. The archive currently has a256MB/25,000-file bound and refuses to discard historical data silently when full.

Manual configured commands: `uv run --extra cloud scout striker-state restore ACCOUNT` before refresh, then `uv run --extra cloud scout striker-state save ACCOUNT`. First bootstrap needs `--allow-empty`. Restoration records a local generation token under `.cache`; save requires that token and the same account. Never overwrite an existing nonempty local state directory with this command. HTTP/schema failures write a redacted failure report and make the refresh CLI exit nonzero.

When explicitly enabled, the existing quota-budgeted API-Football ingester refreshes raw snapshots and a conservative adapter maps only supported totals for reviewed identities. It leaves xG, SCA, carrying and other absent fields unavailable. The daily90-request limit can interrupt a backfill; rerun on following days within the same month. A monthly invocation alone does not guarantee a complete five-league backfill under a free quota.

Enabling that adapter requires an explicitly reviewed, timezone-aware `observed_through` cutoff in source configuration; it is never copied from snapshot retrieval time. Each provider identity mapping also needs verified `team_ids` alongside its `player_id`, eligible `roles` and boolean `reviewed` flag. A row from an unreviewed team is quarantined. A configured cutoff does not by itself prove that paginated provider totals share that cutoff: source-window consistency still needs actual provider evidence before approval, and automatic cutoff discovery is not claimed. Canonical imports supply their own actual observation/retrieval dates. The adapter remains disabled and incomplete for the supplied registry.

**Still outstanding:** a permitted current source covering the registry; verified actual numeric responses and freshness across all five leagues; reviewed real striker identity/role mappings; publication rights; adequate same-window real cohorts; empirical parameter calibration; observed release activation; executed remote monthly runs; Azure/Databricks deployment. No live data, cloud or scheduled-run success is claimed by this local implementation.
