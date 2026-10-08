# Four-source master dataset — 2025/26

The private master combines the collected **Opta, PitchAPI, Understat and WhoScored** snapshots. It does not change the serving database, source permissions, ratings or public application release.

Run from the repository root:

```powershell
scout merge-master-data --output data/master/2025-26-new
```

Use a new output directory for a subsequent build. Completed and interrupted snapshots are preserved rather than overwritten.

The completed build is in **`data/master/2025-26-v2/`**. The original interrupted build's three-source observations are retained in `data/master/2025-26/master.sqlite.pending`. The corrected build reused that checkpoint:

```powershell
scout merge-master-data --output data/master/2025-26-v2 --resume-observations data/master/2025-26/master.sqlite.pending
```

## Files

- `data/master/2025-26-v2/master_players.csv`: the readable master player-season dataset, with actual feature names as headers. Text that could be interpreted as a spreadsheet formula is escaped.
- `data/master/2025-26-v2/master.sqlite`: indexed master players, numeric cells, source observations and column dictionary.
- `data/master/2025-26-v2/players.csv`: one row per resolved player/league/season; unresolved identities remain source-local rows. Stable column IDs map to names and source members in `columns.json`.
- `data/master/2025-26-v2/columns.json`: master column names, IDs and contributing provider fields.
- `data/master/2025-26-v2/manifest.json`: input checksums, output checksums, identity decisions, duplicate-column comparisons, conflicts, counts and limitations.

The master retains all native observations from the accepted cached audit inventories, including categorical identities, match statistics and shot-event attributes. Its wide CSV is a numeric **season view**, not a flattened mixture of match events and season totals. Zero-minute roster identities found in the normalized inputs can appear without numeric observations.

## Completed merge counts

The current master contains **3,561 player/league/season rows**, **227 numeric columns**, and **7,969,444 preserved source observations**. There are **256,272 ordinary numeric cells**, **2,372 cells resolved using priority/tie rules**, and **549,703 unrecorded cells labelled 0**. All **808,347 numeric intersections** now have a value. This row count follows the requested same-name/league rule; it is not a verified count of distinct footballers.

The name merge removed **887 rows** from the prior 4,448 rows, across **673 merged groups**, combining **3,191 overlapping cells**. Source priority is Opta → PitchAPI → Understat → WhoScored. **60 cells** disagreed within the same preferred source; these retain the row with more populated features, then use the original row ID as a deterministic tie-breaker. Competing values are stored in `identity_merge_audit`.

The rule also merges homonyms. Two Spain records named **David López** have different Opta IDs and age values **23.32** and **36.65**. They are merged under the requested rule; both original profiles remain preserved for reversal or a later identity policy.

Exact matching removed 15 duplicate columns. The comparison audit records 17 exact-name pair decisions because three-source groups have more than one pair. Uncertain candidates produced 44 comparisons with differing values and 101 with insufficient overlap; **no uncertain alias was promoted**. Matching zeros or similar spelling alone did not justify a merge.

Only **11 of the 69 captured WhoScored IDs** passed the original name-plus-exposure corroboration; additional identities are now joined by the requested name/league rule. Uncertain columns remain separate pending stronger evidence or definition review.

## Player alignment

The existing catalogue's corroborated links supply initial identities. A final user-authorized pass merges rows sharing a normalized name within the same league. Normalization ignores casing, accents, spaces and punctuation. Different leagues remain separate; existing name aliases connect groups transitively.

WhoScored's initial matching used names plus matching minutes and appearances. The final pass merges remaining same-name/league rows without an exposure requirement, as requested. `identity-merge.json` records the policy and original-to-current row mappings.

WhoScored contributes only the **69 captured IDs** from the browser samples. The site's displayed 2,842 entries have not all been crawled or deduplicated. No values are invented for uncollected pages.

## Duplicate columns

1. Exact, case-sensitive column labels coalesce after removing provider namespaces. Their original native field paths remain in observation/provenance records.
2. A documented abbreviation/synonym list and spelling similarity nominate uncertain pairs; these are candidates, not assumed equivalences.
3. Compare numeric observations for the **same resolved player and league**. Require at least 20 comparable rows, at least 10 nonzero rows, four distinct values on each side, and 100% agreement within absolute/relative tolerance `1e-6` before merging an uncertain pair.
4. Candidate groups must also agree with every other group member; transitive chains cannot bypass these checks.
5. Distinct totals and per-game columns stay separate. No fitted scaling, per-90 conversion or averaging is used to force a match.

Numerical equivalence is empirical evidence, not certification that two providers' definitions are identical. Low-overlap and different-value candidates remain separate, with comparison counts, differences and examples in the manifest. Provider ratings retain their own labels; a similarly named score is not automatically equivalent.

When exact duplicates disagree, select the first available numeric observation using **Opta → PitchAPI → Understat → WhoScored**. Zero is a valid observation and does not trigger fallback. The selected cell has `resolved_by_priority` status. Missing/N/A values do not override a lower-priority numeric observation. Disagreement within a single preferred provider needs separate reconciliation; provider priority alone cannot decide it.

The existing dataset's 1,414 conflicts were resolved in place, with original exports and manifest preserved as `.pre-priority` backups. The SQLite `conflict_resolutions` table and `conflict-resolution.json` record the selected source/value and all competing values. Original source observations are unchanged. Uncertain column aliases remain separate: priority resolves values within merged columns, not the meaning of an ambiguous column.

```powershell
scout resolve-master-conflicts --folder data/master/2025-26-v2
```

New master builds use the same priority automatically. Priority selection represents a declared source preference, not an averaging or verification of the chosen number.

## Name deduplication and recovery

```powershell
scout deduplicate-master-players --folder data/master/2025-26-v2
```

New CLI master builds perform this pass automatically. Repeating it without new duplicates is a no-op. The database preserves `players_pre_name_merge` and `cells_pre_name_merge`, plus `.pre-name-merge` CSV/manifest files. `player_aliases` maps every original row to its current row. Raw `observations` keep original row IDs; use **`observations_canonical`** for current merged IDs. Column membership and original observation counts do not change.

## Missing cells and granularity

The current user-requested policy labels **all unrecorded numeric master values as 0**, applied **after feature union and source-priority selection**. Both existing unavailable cells and absent player/column intersections receive `unrecorded_zero` status and no selected provider. Recorded zeros retain their observed status/source. This does not allow a generated zero from Opta to override an actual value from a lower-priority source.

```powershell
scout zero-fill-master-values --folder data/master/2025-26-v2
```

New CLI master builds apply this final step automatically. `zero-fill.json` and the manifest record the transformation. `.pre-zero-fill` CSV/manifest backups and the database `missing_cells_before_zero` table preserve the previous state. Raw source evidence, including explicit N/A and missing observations, remains unchanged. Numeric zeros in the final master therefore include user-labelled unrecorded values; they do not all establish an observed event absence.

- Present empty native numeric cells follow the earlier cell policy. Final master gaps are now labelled 0 under the new policy.
- Calculated unavailable PitchAPI season totals remain missing in original evidence, with `unrecorded_zero` in the final numeric master.
- Source ratios and rates are not recomputed using another provider's numerators or denominators.
- PitchAPI's existing validated season totals contribute to the season view; their partial-season status is retained in provenance.
- Unknown match-rate fields and shot events stay in `observations`; they are not blindly summed into season totals.
- Opta multi-team samples remain in observations when no single comparable season value is established.

## Inspection

Example read-only SQLite queries:

```sql
SELECT COUNT(*) FROM players;
SELECT label, members_json FROM columns ORDER BY label;
SELECT status, COUNT(*) FROM cells GROUP BY status;
SELECT selected_provider, COUNT(*) FROM conflict_resolutions GROUP BY selected_provider;
SELECT provider, scope, COUNT(*) FROM observations GROUP BY provider, scope;
SELECT * FROM player_aliases WHERE original_master_row != master_row;
SELECT p.names_json, c.label, x.value, x.status
FROM cells x JOIN players p USING (master_row)
JOIN columns c USING (column_id)
WHERE c.label LIKE '%Fouled%';
```

The dataset includes Understat private-use evidence and WhoScored preview data; public redistribution remains unapproved. All original snapshots stay intact. `continue_strictly_mainplan.md` is untouched.
