# Operating Scout

## Start and readiness

Run migrations for PostgreSQL with `alembic upgrade head`, then seed a synthetic development release or publish an approved bundle. `/health/live` reports process availability. `/health/ready` checks a loaded active release, and refuses synthetic data when `SCOUT_ALLOW_SYNTHETIC=false`. Keep that false for an actual real-data deployment; an explicitly labelled synthetic demonstration can opt in.

If readiness fails, inspect the active pointer, data availability, schema version and synthetic policy. Keep exception logs free of tokens/provider keys. The public API cannot activate releases.

Squad Studio's curated/demo endpoints are independent of candidate readiness: `/squads/liverpool-men` and `/formations` can load with no active recruitment release. `/health/ready` still describes recruitment readiness; its success does not certify real squad statistics. Check `/squads/liverpool-men`, then evaluate its default lineup to smoke-test the dashboard separately. It must return the expected snapshot and `evidence: synthetic`.

Lineups/notes are browser-local. For damaged storage, export the preserved original, then explicitly recover or import a validated backup; do not erase it during an automatic restart. A new roster snapshot gets its own storage key. Details, rating settings and chemistry use modal drawers; the bench uses a nonmodal bottom drawer. At small widths, pan the pitch horizontally to retain readable cards. See `docs/squad-studio.md` for formulas, source limitations and recovery behaviour.

## Publish and recover

1. Produce an immutable bundle and checksum with a unique release ID.
2. Validate source/coverage/publication gates and analytical versions; review evaluation artifacts.
3. Run `scout publish path/to/bundle.json`. Validation precedes the database transaction.
4. Check readiness and the returned release ID; smoke-test recommendations/scenarios.
5. On failure, run `scout rollback PREVIOUS_RELEASE_ID`, then repeat readiness and a representative request.

Tests demonstrate checksum rejection preserving the previous release and transactionally switching/rolling back the pointer. A production promotion gate with external API smoke-test rollback and full artifact/model signatures remains outstanding. Retain previous validated bundles privately.

## Database backup and restore

Use a PostgreSQL custom-format dump (`pg_dump --format=custom`) before schema changes. Store it privately in the ADLS backups container, record checksum/schema/release IDs, and bound retention. Restore into a **separate empty database**, run migrations/checks, validate active release checksums and compare representative API outputs before changing the serving connection. Do not overwrite the live database to test recovery. No backup/restore drill has yet run in a cloud environment.

## Batch failures

Quota exhaustion exits ingestion with code 75 and leaves its checkpoint. Resume after the UTC quota reset; do not bypass budget checks. Run one ingestion writer at a time. Invalid records go to quarantine. Failed batch validation cannot activate a new release. Schema changes, interrupted transport, refresh policy and snapshot integrity require further hardening.

## Monitoring and credits

Monitor API error/latency, readiness, active release, candidate freshness/coverage, missingness, batch failures, quotas and cloud consumption. Application Insights configuration is sampled with bounded telemetry caps; runtime instrumentation and alert delivery are unverified.

Cloud workflows require `CLOUD_ENABLED=true`, configured production environment/OIDC and a recent manual portal credit attestation. The guard rejects missing/stale attestations, unconfirmed spending protection, less than €5 reserve or expiry within three days. This is **not a live balance API**. Budget notifications do not stop spending. The scheduled guard disables public API ingress on failure; min replicas remain zero. Storage/telemetry may still consume credits. Review the portal, preserve subscription spending protection and never convert to paid billing automatically.
