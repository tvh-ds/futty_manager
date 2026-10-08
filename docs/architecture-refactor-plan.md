# Three implemented architecture improvements

Status: implemented locally, 8 October 2026. All three design decisions below were approved. The proposal sections retain the reasoning and preserved contracts; the implementation record below describes the delivered behavior.

## Implementation record

- **Master revisions:** `src/scout/master_snapshot.py` owns the OS writer lock, SQLite backup, staging markers, export generation, checksums, validation and completed revision rename. Priority, identity and missing-value modules now supply transformation policies. Commands return `revision_path`; the combined merge command threads it through every subsequent transformation. Failed stages retain diagnostics and leave the input unchanged. Retries reuse a validated completed revision.
- **Calibration:** `src/scout/calibration.py` owns shrinkage, directional standardization and weighted ability/overall composition. Catalogue and role adapters still choose their respective eligible peers. Frozen pre-refactor fixtures verify numerical parity, including recorded zeros and zero-filled redistribution. Calibration code is included in scoring checksums.
- **Lineup workflow:** `frontend/src/lineupPlanner.ts` owns accepted edits, history, persistence, recovery and asynchronous operation ownership. `useLineupPlanner.ts` connects storage, HTTP and TanStack Query. Both lineup and evidence versions guard displayed evaluations; superseded formation/import results cannot overwrite edits. Rendering retains the existing pitch and drawers. Closing a detail drawer restores card focus.

### Using master revisions

Existing transformation command names remain available. Read `revision_path` from their JSON output and pass that folder to the next command or downstream reader. Do not keep using the input folder expecting in-place updates. `merge-master-data` does this chaining internally. The review-only position specification writer accepts `--master <revision-directory>`; its default remains the original snapshot used for those documents.

Completed revisions contain a checksummed manifest with transition status `complete`. Incomplete stages have `STAGING.json`; ordinary failures also retain `FAILED.json`. They must not be consumed as completed snapshots. There is no automatic serving-release activation or cleanup. SQLite copies and retained stages consume local disk space; review retained stages before manually removing them. The lock coordinates writers on this local filesystem, not distributed storage. Directory finalization does not make several independent output files a cross-system transaction.

### Validation evidence

- 66 focused backend tests passed, covering calibration parity, ratings, catalogue and master transformations. After final lifecycle changes, all 17 snapshot/master tests passed again.
- All 19 frontend unit tests passed, including delayed evaluations, superseded operations, storage recovery and malformed responses. The production frontend build and scoped Python Ruff checks passed.
- Updated Squad Studio browser suite: nine desktop/mobile checks passed; mobile pointer dragging was intentionally skipped because mobile uses the tap journey. Existing recruitment workbench's three browser checks passed. Final desktop/mobile full-journey confirmation passed after the evidence-version guards were added.

The active real-data master/catalogue was not rebuilt or activated. No crawling, weights, cohort selection, dependency additions, cloud deployment or visual redesign was included. `continue_strictly_mainplan.md` remains untouched.

## 1. Master snapshot transitions

### Existing problem

`resolve_master`, `merge_names` and `fill_missing` independently coordinate database changes, backup files, CSV exports, audit reports and manifest checksums. Their SQLite transactions finish before all related files finish. An interrupted write can leave representations of one snapshot inconsistent.

### Recommended design

Introduce a master snapshot module that owns the complete revision lifecycle:

1. Validate the input snapshot and acquire a single-writer guard for its transition.
2. Create a sibling staging directory and copy the required inputs. Use SQLite's backup operation rather than copying an open database file.
3. Apply the selected transformation to the staged revision. Preserve raw observations, aliases and per-cell provenance.
4. Generate stable-ID and readable exports from the resulting database, rather than patching existing CSV cells independently.
5. Write the transformation audit and checksummed manifest.
6. Validate database integrity, row/column agreement, exports and manifest checksums.
7. Finalize the staged directory under a new revision name. Return its path and summary to the caller.

A failure leaves the input revision usable. Incomplete staging directories are explicitly distinguishable from completed snapshots. A successful revision is reusable after a retry; a revision with conflicting contents is rejected. Do not claim that a sequence of file replacements is one atomic transaction.

Keep source priority, identity merging and zero-fill rules as separate policies inside the implementation. They must not own export ordering, backup naming or manifest completion. Existing command names should remain available as adapters; their output must identify the new revision path so downstream steps consume the correct snapshot.

### Preserved rules

- Merge features before selecting conflicting values.
- Priority: Opta, PitchAPI, Understat, WhoScored.
- User-authorized normalized-name and league identity matching remains distinct from the catalogue's stronger corroboration policy.
- Unrecorded numeric values become zero with `unrecorded_zero` evidence; observed zeros retain their provenance.
- No database migration, source crawling or automatic application activation as part of this refactor.

### Focused verification

Test through the snapshot transition interface: successful feature union and priority selection, observed-zero preservation, interruption during exports, failed validation, concurrent writers and retry after interruption. Assert that failed transitions leave the original snapshot unchanged. Adapt existing master tests to read the returned revision.

### Decision to settle

Use immutable new revisions rather than updating an existing master folder in place? Recommended: yes. This changes the output-location contract of transformation commands, so consumers must be updated together.

## 2. Shared ability calibration

### Existing problem

`player_catalogue.score_catalogue` and `ability_engine.evaluate_role` independently implement shrinkage, directional standardization, weighted ability composition and ability standardization. Their cohort policies differ; replacing one whole scorer with the other would change behaviour.

### Recommended design

Introduce a numerical calibration module beneath both existing scorers. Its interface accepts compatible observations, exposures, directions, effective weights and a frozen reference population, and returns calibrated feature evidence and ability results. Keep representation conversion outside the numerical implementation.

The catalogue adapter retains per-ability grouping by provider, measurement definition and effective feature weights. The role adapter retains its frozen role population. Overall scoring retains explicit alignment of shared peer identities; the numerical module must not choose peers implicitly.

Remove repeated numerical loops from both callers. Avoid an extra helper that leaves the two full implementations intact. Catalogue evidence reconstruction should reuse the returned calibration evidence rather than recalculate a second formula.

### Preserved rules

- Top-five pooled role peers, existing exposure requirements and compatible measurement definitions.
- Only `unrecorded_zero` removes a feature's weight, with proportional redistribution.
- Recorded zeros stay scored; zero-attempt ratios remain N/A.
- Existing reliability priors and feature directions.
- Weighted latent scores are standardized; display remains `max(1, 50 + 15 × z)` with no upper cap.
- All six calibrated abilities and aligned eligible peers are required for overall ratings.
- Synthetic recruitment ranking is outside this refactor.

### Focused verification

Capture representative outputs from both existing paths before changing them. Test shared calibration on recorded zeros, zero filling, tied peers, lower-is-better metrics, missing exposure and insufficient evidence. Compare each adapter's before/after ratings, eligibility, weights and explanations. Use identical evidence for numerical parity; do not assert equivalence between differently selected cohorts.

### Decision to settle

Make this a behaviour-preserving refactor, leaving formula, weights and cohort policies unchanged? Recommended: yes. Any numerical discrepancy should be reported separately rather than silently treated as an improvement.

## 3. Lineup planning workflow

### Existing problem

`Studio` combines rendering with persisted lineup state, history, validation, asynchronous formation changes, import recovery and evaluation freshness. Tests of `squadState` cover individual edits but cannot fully exercise the coordination. Some existing browser tests still reference removed controls.

### Recommended design

Introduce one lineup planning module owning validated edits, undo history, import/export recovery and asynchronous request ownership. Rendering retains drawer selection, filters, pitch sizing and animation.

Expose current planning state and supported operations through one interface. Keep the existing HTTP and browser storage adapters; use controlled adapters for tests. Retain TanStack Query for request caching and authoritative evaluation, with snapshot and request identity included wherever they affect results.

Every asynchronous formation/import operation records the planning revision it started from. A response can commit only if that revision is still current. Authoritative scores are shown only for the current lineup; preview scores are shown only for the current substitution preview. Pending and failed scores remain explicit.

### Preserved rules

- Unique player identities across pitch and bench.
- Goalkeeper/outfield restrictions.
- Eleven players preserved across formation changes.
- Bench substitutions return the outgoing player to the correct location.
- Corrupted stored data is preserved until explicit recovery.
- Undo, notes, import/export and existing pointer/keyboard interactions remain available.
- The visual design and recruitment workflow remain unchanged.

### Focused verification

Test the workflow interface with controlled storage and delayed responses: successful edits and undo, invalid goalkeeper exchanges, corrupt storage, failed imports, edits during formation/import requests, and out-of-order evaluations. Update browser expectations for current card-click details and hover/focus substitution controls; do not restore removed Rating settings just to satisfy obsolete tests.

### Decision to settle

Keep the current visual behaviour while consolidating workflow state and updating obsolete tests? Recommended: yes. No dashboard redesign is needed for this improvement.

## Delivery order

1. Snapshot lifecycle and its command consumers.
2. Calibration implementation and both scoring adapters.
3. Lineup workflow and its current interaction tests.

Verify each separately before moving to the next. Document completed behaviour and material limitations. Leave `continue_strictly_mainplan.md` untouched.
