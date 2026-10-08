# Local combined real-data import

Implemented on 2026-10-06. The local SQLite database now has the same SQLAlchemy
evidence schema available to the PostgreSQL deployment. Cloud services are not
needed for this workflow.

## What is loaded

Completed **2025/26** measurements collected earlier on 2026-10-06:

| Source | Valid provider records | Scope |
|---|---:|---|
| Opta Analyst | 3,049 | Player/team/season, including 472 unused squad members |
| PitchAPI | 2,770 | Player/league/season, potentially multiple clubs |
| Understat | 2,775 | Player/league/season, potentially multiple clubs |
| Total | 8,594 | Source records, **not unique players** |

Each source covers England, Spain, Germany, Italy and France. The source
inventories differ. This does not establish complete coverage of every player
in those leagues. Existing collection quarantine is retained: five PitchAPI
match feeds and two Opta player exposure conflicts. This import adds no numeric
imputation and does not turn a partial PitchAPI backfill into a complete season.

The importer recalculates **309,384 feature slots** (8,594 × the current 36 ST
definitions), storing values or explicit missing/N/A states. These are feature
slots, not 309,384 available measurements. Cached feature numbers are not trusted.
Raw source totals, provider identifiers, aggregation scope, URLs, timestamps,
measurement version and available Opta birth-date/club identity facts persist.
The evidence catalogue includes keepers; ST feature calculations for a keeper
do not represent a rigorous goalkeeper rating.

## Database and transaction

- `evidence_imports`: immutable content-addressed import manifests and coverage.
- `source_records`: versioned provider identity and raw totals/provenance.
- `source_features`: SQL-queryable, calculated feature values, numerators,
  denominators, units and availability reasons.
- `evidence_identity_links`: explicitly reviewed canonical identity mappings.
- `active_evidence`: an independent local evidence pointer.

Alembic revision `0002` creates these tables. The existing development database
had the original four tables but no recorded revision. Its columns/types,
nullability and primary keys were checked, a SQLite backup was created in
`data/backups`, and the original schema was stamped `0001` before upgrading.
Fresh databases use `alembic upgrade head` normally.

All inserts and local activation share one transaction. Failure rolls back the
whole import. Identical inputs and transform versions produce the same import
ID and no duplicate rows. New imports preserve earlier evidence versions.
The published candidate `active_release` pointer is never changed by this command.

## Reproduce and query

From the repository root, using the existing `.env` database settings:

```powershell
.venv/Scripts/alembic.exe upgrade head
.venv/Scripts/scout.exe import-real-data data/pitchapi/live-probe-2025 data/opta-analyst/season-2025-20261006 data/striker-source-probes/understat-recheck-20261006
```

Output: `data/real-data/import-report.json`. It includes input checksums, source
collection status, per-provider/per-league feature coverage for positive-minute
records, import quarantine and identity candidates. Each candidate is an
**unreviewed name suggestion**, not a merged player. Bronze snapshots for Opta
and Understat must match their collection-report checksums.

For local API access set `SCOUT_SERVE_PRIVATE_EVIDENCE=true` in `.env` and restart
the API bound to `127.0.0.1`. Default deployments leave this setting false.

```text
GET /data/import
GET /data/players?provider=opta&league=England&name=Gakpo&limit=50
GET /data/players/{source_record_id}/features
GET /data/players/{reviewed_canonical_id}/features
```

The SQL-backed `RealDataEngine` serves the actual imported numbers. It returns
up to 100 catalogue records per request, with explicit source-record counts.
Feature responses expose raw evidence, calculated numbers, missingness and
source alternatives. They never silently substitute the fictional population.

## Reviewed combined identities

Copy the format of `config/real-data-identities.example.json`. Replace its example
IDs with imported IDs. For each provider record supply a stable canonical ID,
reviewer and meaningful verification evidence. Re-run the import with
`--identities path/to/reviewed-identities.json`.

Names alone are insufficient. Check stable provider IDs, club/season, available
birth dates and corroborating facts. The importer prohibits a combined profile
containing two aggregates from the same provider or different leagues. Transfers
need an explicit reconciliation stage before those records can be combined.

Combined profiles select available features in **Opta → PitchAPI → Understat**
order; this is a documented intake default, not an assertion that definitions
are equivalent. They retain every alternative. Each selected ratio keeps the
numerator and denominator from the same source. Differences in xG, xA, minutes
or action definitions remain visible. No cross-provider total is added or
averaged. Provider-definition harmonisation remains required before model
calibration or publication.

## Availability and publication boundaries

Observed zero attempts with zero numerator give N/A and count as supported in
feature availability. Zero minutes do not count as supported per-90 observations.
Missing measurements never become zero. Positive successes with zero attempts
or successes greater than attempts are rejected. Missing `fouls_won90` remains
explicit.

**35/36 is source capability, not proven merged-player coverage at 90%.** Actual
per-league support is recorded in the import report. Identity review, harmonised
definitions, eligible role/exposure cohorts and full scoring acceptance remain
necessary before publishing combined ratings.

Understat remains private with unverified publication rights. Imported profiles
have `publication_approved=false`, `overall_rating=null` and
`rating_status=not_calibrated`. The fictional recruitment release remains
separate. A private local catalogue now maps corroborated historical evidence
onto Liverpool, with strict ST ability scores where eligible and no synthetic
fallback. See [player-catalogue.md](player-catalogue.md) for current counts,
mapping rules and remaining identity/publication limitations.

## Verification

Focused tests cover arithmetic/N/A/missingness, invalid measurements, idempotent
imports, preservation of the existing release, transaction rollback, bronze
tampering, reviewed source combination, bounded API filters, private endpoint
opt-in and fresh Alembic migration.
