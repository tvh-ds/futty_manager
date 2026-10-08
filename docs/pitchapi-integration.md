# PitchAPI integration

Implemented 6 October 2026. The user confirmed free API access and reuse rights.
The private key is read from `SCOUT_PITCHAPI_KEY` in `.env` or the process environment,
masked by the settings model, and sent only as `X-API-KEY` to the fixed HTTPS host.
No subscription or cloud resource is created.

## Live verification

The authenticated 2025/26 catalogue lists the expected completed inventories:
England 380, Spain 380, Germany 306, Italy 380, France 306: 1,752 matches.
The first three matches per league were collected and parsed successfully:
15 matches, 462 distinct player/league observations. These are sample totals,
not season ratings. The full backfill then fetched all 1,752 matches: 1,747
passed validation and five were quarantined (one Spanish, four French), each
for an unmatched shot actor. It retained 2,770 player/league rows across all
positions. These totals exclude invalid matches and are not a complete season
release. All advanced endpoints were reachable, but some individual advanced
player entries and basic optional measurements are absent.

Private evidence lives in `data/pitchapi/live-probe-2025/`:
`snapshots/`, `measurements.json`, `coverage.json`, `collection-progress.json`.
Snapshot bodies have wire and canonical JSON checksums, URL, query and retrieval time.
The snapshot contains no request headers or credentials. Coverage and progress expose
counts and sanitized failures, not provider error bodies.

## Run locally

```powershell
.venv/Scripts/scout.exe collect-pitchapi --output data/pitchapi/live-probe-2025 --season 2025 --max-requests 60 --matches-per-league 3
.venv/Scripts/scout.exe collect-pitchapi --output data/pitchapi/live-probe-2025 --season 2025 --max-requests 6000
.venv/Scripts/scout.exe refresh-strikers --config-path config/striker-source.pitchapi.json --pitchapi-cache data/pitchapi/live-probe-2025
```

Repeated collection with the same output reuses validated immutable snapshots.
Request limits count network attempts, including retries; a budget exhaustion keeps
the cache and cannot activate a partial release. Timeouts, capped response sizes,
three-attempt retries, bounded backoff and disabled redirects protect the boundary.
Use a new dated output directory when deliberately fetching revised provider data;
cached retrieval dates are never relabelled as fresh.

Invalid match records are quarantined and excluded in full, while other matches
continue collecting. Twenty invalid matches halt collection to bound repeated schema
failures. Any quarantine prevents the season-completeness flag and canonical scoring;
the missing appearance is never silently treated as a zero. The first full backfill
encountered a Spanish shot referencing `p_2mYiIC`, absent from basic appearances and
advanced players, with an empty source name. That identity was not guessed or repaired.

Final quarantine: `m_23nGBe`, `m_4YrxSl`, `m_2c4ZLn`, `m_1GY5OE`, `m_0Dz3Fs`.
The raw responses are retained for investigation or corrected source snapshots.

The opt-in refresh config retains its provider cache under
`data/strikers/provider/pitchapi/2025/YYYY-MM/`. A new month fetches fresh snapshots;
repeated runs in the same month resume existing snapshots. The opt-in PitchAPI config
allows at most 6,000 network attempts per run, sufficient for the base 5,262 endpoints
and bounded retries. Collection and refresh share the same adapter,
but separate output directories do not share caches. `--pitchapi-cache` lets the local
refresh reuse the verified backfill without copying snapshots. Initial full-season staging can
be performed directly in that refresh cache directory to avoid duplicate downloads.
Default cloud/monthly configuration remains disabled until Azure private state is configured.
The workflow supports `SCOUT_PITCHAPI_KEY` as a GitHub secret; the local `.env` is not uploaded.

## Evidence rules and remaining limits

- Stable source keys are mapped, not localized display labels. Raw passing and aerial
  fractions are used; rounded accuracy percentages never reconstruct raw counts.
- Live match stats establish `touches_opp_box`, `Offsides`, `was_fouled`,
  `duel_won`, `duel_lost`, `ShotsOnTarget`, and `expected_assists`.
  Absent optional values stay unknown, including an omitted offsides entry.
- Complete shot arrays support shot counts, non-penalty goals/xG, body part,
  box location and open-play classifications. Without explicit blocked-shot flags,
  shot-derived SOT stays unknown unless the base feed provides a SOT count.
- Unused named substitutes with no statistics, advanced appearances or shots are excluded.
  Basic appearance minutes take precedence; advanced minutes can include stoppage time.
- Carries are inferred by the provider; its SCA/interception/block definitions differ
  from some reference definitions. xAG is never substituted for xA.
- Attacking-third tackles are not supplied by the inspected endpoints. Match timelines
  are not full defensive action feeds. No proxy or zero is substituted.
- A season total is unknown if its required value is missing in any appearance.
  Zero denominators produce unavailable rates, not invented success percentages.
- Full inventories are required before canonical scoring imports. Explicit reviewed
  player IDs, striker roles and all observed team IDs must be added to `identities`.
  Generic forward metadata cannot automatically establish ST/archetype eligibility.
- Raw-field citations identify a contributing endpoint; `source_documents` retains
all contributing match endpoint URLs in the immutable record.
- PitchAPI measurement definitions have a distinct version and calibration cohorts.
  Mixed measurement versions cannot publish together.

The existing 900-minute, 30-complete-peer-per-league and complete-feature gates remain.
With the currently missing attacking-third tackles, full requested striker ratings
cannot publish. The interface's existing demonstration release remains in place;
this integration does not silently replace it with partial or synthetic real-player ratings.

The completed cache contains 5,262 snapshots. Of 2,770 player/league rows, 1,584
have at least 900 minutes, but zero have the complete requested feature registry.
Running the opt-in refresh against that cache performed zero network requests,
reported `MatchValidationFailed`, created no rated release and retained the active
release pointer. Exposure alone does not close the feature or identity gates.

Official schema reference: [PitchAPI documentation](https://pitchapi.dev/).

## 90% feature acceptance update — 2026-10-06

Canonical imports now additionally require every required feature to pass 90%
coverage. The new `audit-pitchapi` command reports missing measurements separately
from undefined zero-denominator rates, globally and by league. The existing cache
passes 27/37 features across 2,770 player/league rows. A bounded fresh 40-request
recheck did not recover the missing base measurements; no half-stat values were
merged. See [the coverage audit and alternative-source findings](striker-coverage-90.md).

## Verification

Ruff passes. The full regression suite passed 149 tests with one skipped before the
quarantine refinement; the final focused integration/scoring suite passed 49 tests.
Tests cover request-budget resumption, checksums, secret masking, strict source shapes,
unknown evidence, unused substitutes, differing minute definitions, quarantined actors,
reviewed identity mappings, failed-refresh preservation and separated measurement cohorts.
